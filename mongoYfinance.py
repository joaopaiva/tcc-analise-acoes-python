import sys, os
import re
import csv
import json
from datetime import datetime, date, time, timedelta
from itertools import zip_longest
import numpy as np
import pytz
import yfinance as yf
import ast
import copy

from flask import jsonify
from pymongo import *
from pandas_datareader import data as pdr


class mongoYfinance:
    mongoClient = None
    yfdb = None
    verbose = False

    #
    # Used to print messages only if the verbose flag was enabled
    #
    def sprint(self, msg):
        if self.verbose:
            print(msg)


    #
    # Generic function to check all user input dates
    # The format must be dd/mm/yyyy and cannot be a date in the future.
    # In case of error the execution of the application is stopped.
    #
    def __checkDate(self, date):
        try:
            inputDate = datetime.strptime(date, "%Y/%m/%d")
            currentTime = datetime.now()
            if (inputDate > currentTime):
                self.sprint("Error: provided date (" + date + ") is in the future")
                exit()
        except ValueError:
            self.sprint("Error: invalid provided date format (expected yyyy/mm/dd)")
            exit()


    #
    # Given a symbol document in the mongodb this returns the date it contains.
    #
    def __getFormattedDate(self, symbol):
        try:
            # print(symbol['Datetime'])
            # return datetime.date(symbol['Datetime'], "%Y-%m-%d")
            return symbol['_id']['Datetime']
        except ValueError:
            self.sprint("Error: invalid provided date format (expected yyyy/mm/dd)")


    #
    # Initialises the ddbb
    #
    def __init__(self, user="admin", password="", hostname="localhost", database="yfmongo", verbose=True):
        userAndPass = ""
        if user and password:
            userAndPass = user + ":" + str(password) + "@"
        url = "mongodb+srv://" + userAndPass + hostname
        self.mongoClient = MongoClient(url)
        self.yfdb = self.mongoClient[database];
        self.verbose = verbose


    #
    # Removes all content in the database (Caution!)
    #
    def clear(self, keepSymbols=False):
        if keepSymbols:
            self.sprint("Removing data ... done")
            self.yfdb.timeline.delete_many({});
        else:
            self.sprint("Removing all collections [symbols and timeline] ... done")
            self.yfdb.timeline.delete_many({});
            self.yfdb.symbols.delete_many({});


    def add(self, symbol, startDate=None, endDate=None):

        exists = self.yfdb.symbols.count_documents({'_id.sym': symbol})

        if not exists:
            quote = yf.Ticker(symbol)

            if "shortName" not in quote.info:
                return {'symbolExists': False, 'added': False, 'message': 'Symbol ' + symbol + ' not found in API'}

            self.yfdb.symbols.replace_one({'_id': {'sym': symbol}}, {'_id': {'sym': symbol}, 'shortName': quote.info['shortName']}, upsert=True)
            self.sprint("'" + symbol + "'" + " added to the database")
            oldestDate = datetime.today() - timedelta(days=6)
            self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                               date.today().strftime("%Y/%m/%d"),
                               symbol=symbol)

            result = {'symbolExists': True, 'added': True, 'message': 'Symbol ' + symbol + ' was successfully added', 'sym': symbol, 'shortName': quote.info['shortName']}
        else:
            symbols = self.yfdb.symbols.find({'_id.sym': symbol})
            for s in symbols:
                result = {'symbolExists': True, 'added': False, 'message': 'Symbol ' + symbol + ' is already in database',
                          'sym': symbol, 'shortName': s['shortName']}

        if startDate != None:
            if endDate != None:
                self.fetchInterval(startDate, endDate, symbol)
            else:
                self.fetch(startDate, symbol)

        return result

    #
    # Removes a symbol from the ddbb, including all timeline entries
    #
    def remove(self, symbol):
        if not symbol:
            return {'removed': False, 'message': 'Missing symbol name'}
        exists = self.yfdb.symbols.count_documents({'_id.sym': symbol})
        if not exists:
            self.sprint("Error: symbol'" + symbol + "' not in the database")
            return {'removed': False, 'message': 'Symbol ' + symbol + ' not found in database'}
        else:
            self.yfdb.symbols.delete_many({'_id.sym': symbol})
            self.yfdb.timeline.delete_many({'_id.sym': symbol})
            self.sprint("'" + symbol + "'" + " removed from the database")
            return {'removed': True, 'message': symbol + ' removed from the database'}


    #
    # Prints information regarding the admin info (start and end dates)
    # and the symbols contained in the database
    #
    def info(self):
        symbols = self.yfdb.symbols.find();
        for symb in symbols:
            print(symb['sym'])
        print("Timeline size: " + str(self.yfdb.timeline.find().count()))
        print("Symbols: " + str(symbols.count()))
        dates = []
        symbols = self.yfdb.timeline.find()
        for symb in symbols:
            date = self.__getFormattedDate(symb)
            dates.append(date)
        if dates:
            print("Oldest record: " + min(dates).strftime("%Y/%m/%d"))
            print("Most recent record: " + max(dates).strftime("%Y/%m/%d"))


    def listSymbols(self):
        symbols = self.yfdb.symbols.find()
        symList = {}
        count = 0

        for s in symbols:
            print(s)
            symList[count] = {'sym': s['_id']['sym'], 'shortName': s['shortName']}
            count += 1

        return symList


    #
    # Updates the database fetching data for all symbols since last
    # date in the data until today
    #
    def update(self):
        tickers = self.yfdb.symbols.find()
        for ticker in tickers:
            tickerTimeline = list(self.yfdb.timeline.find({'_id.sym': ticker["_id"]["sym"]}))
            if len(tickerTimeline) > 0:
                # print(tickerTimeline)
                oldestDate = max(map(lambda s: self.__getFormattedDate(s), tickerTimeline))
                print(oldestDate)
                if oldestDate is not None:
                    self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                       date.today().strftime("%Y/%m/%d"),
                                       symbol=ticker["_id"]["sym"])
            else:
                oldestDate = datetime.today() - timedelta(days=6)
                self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                   date.today().strftime("%Y/%m/%d"),
                                   symbol=ticker["_id"]["sym"])

    # Fetches symbol data for the interval between startDate and endDate
    # If the symbol is set None, all symbols found in the database are
    # updated.
    def fetchInterval(self, startDate, endDate, symbol=None, interval='1m'):
        timezone = pytz.timezone("UTC")

        if symbol is None:
            symbols = self.yfdb.symbols.find()
        else:
            symbols = self.yfdb.symbols.find(({'_id.sym': symbol}))
        for symbol in symbols:
            # download dataframe
            quote = yf.Ticker(symbol['_id']['sym'])
            # data = quote.history(start=startDate.replace("/", "-"), end=endDate.replace("/", "-"), interval=interval)
            data = quote.history(start=startDate.replace("/", "-"), interval=interval)

            # set index to column in pandas DataFrame
            data.reset_index(inplace=True)

            if "Datetime" in data:
                lastTicker = self.getLastTicker(symbol['_id']['sym'])
                tickersNotRounded = data[data['Datetime'].dt.second > 0].index
                data.drop(tickersNotRounded, inplace=True)

                # update already exists in database
                if lastTicker:
                    storedData = timezone.localize(self.getLastTicker(symbol['sym']))
                    apiData = data["Datetime"].iat[-1].to_pydatetime().astimezone(timezone)

                    print(apiData.timestamp() - storedData.timestamp())

                    if len(data) > 0 and apiData.timestamp() - storedData.timestamp() > 120:
                        self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                                    + symbol['sym'] + "' (" + str(len(data)) + " entries)")
                        dictData = data.to_dict(orient='records')

                        for data in dictData:
                            data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": data["Datetime"]}
                            data.pop('Datetime', None)

                        ids = [dt.pop("_id") for dt in dictData]

                        operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                                      zip(ids, dictData)]

                        self.yfdb.timeline.bulk_write(operations)

                # insert new data
                else:
                    if len(data) > 0:
                        self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                                    + symbol['_id']['sym'] + "' (" + str(len(data)) + " entries)")
                        dictData = data.to_dict(orient='records')

                        for data in dictData:
                            data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": data["Datetime"]}
                            data.pop('Datetime', None)

                        ids = [dt.pop("_id") for dt in dictData]

                        operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                                      zip(ids, dictData)]

                        self.yfdb.timeline.bulk_write(operations)


    def getTicker(self, symbol):
        # self.add(symbol)
        self.update()

        symbols = self.yfdb.timeline.find({'_id.sym': symbol})
        volume = {}
        close = {}
        cleanSymbols = {}

        for s in symbols:
            datetimeStock = int(s['_id']['Datetime'].timestamp() * 1000)
            volume[datetimeStock] = s['Volume']
            close[datetimeStock] = s['Close']

        cleanSymbols["Close"] = close
        cleanSymbols["Volume"] = volume
        return cleanSymbols


    def getLastTicker(self, symbol):
        symbols = self.yfdb.timeline.find({'_id.sym': symbol}).sort('_id', -1).limit(1);
        symbolsList = list(symbols)

        if len(symbolsList) == 0:
            return None
        elif 'Datetime' in symbolsList[0]:
            return symbolsList[0]['_id']['Datetime']
        else:
            return None
