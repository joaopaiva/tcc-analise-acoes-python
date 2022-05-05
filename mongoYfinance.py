import sys, os
import re
import csv
import json
from datetime import datetime, date, time, timedelta
import numpy as np
import pytz
import yfinance as yf
import ast
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
            return symbol['Datetime']
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
        exists = self.yfdb.symbols.count_documents({'sym': symbol})
        if not exists:
            self.yfdb.symbols.insert_one({'sym': symbol});
            self.sprint("'" + symbol + "'" + " added to the database")
        if startDate != None:
            if endDate != None:
                self.fetchInterval(startDate, endDate, symbol)
            else:
                self.fetch(startDate, symbol)


    #
    # Removes a symbol from the ddbb, including all timeline entries
    #
    def remove(self, value):
        exists = self.yfdb.symbols.find({'sym': value}).count();
        if not exists:
            self.sprint("Error: symbol'" + value + "' not in the database")
        else:
            self.yfdb.symbols.delete_many({'sym': value});
            self.yfdb.timeline.delete_many({'sym': value});
            self.sprint("'" + value + "'" + " removed from the database")


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


    #
    # Updates the database fetching data for all symbols since last
    # date in the data until today
    #
    def update(self):
        tickers = self.yfdb.symbols.find()
        for ticker in tickers:
            tickerTimeline = list(self.yfdb.timeline.find({'ticker': ticker["sym"]}))
            if len(tickerTimeline) > 0:
                # print(tickerTimeline)
                oldestDate = max(map(lambda s: self.__getFormattedDate(s), tickerTimeline))
                print(oldestDate)
                if oldestDate is not None:
                    self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                       date.today().strftime("%Y/%m/%d"),
                                       symbol=ticker["sym"])
            else:
                oldestDate = datetime.today() - timedelta(days=7)
                self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                   date.today().strftime("%Y/%m/%d"),
                                   symbol=ticker["sym"])


    # Fetches symbol data for the interval between startDate and endDate
    # If the symbol is set None, all symbols found in the database are
    # updated.
    def fetchInterval(self, startDate, endDate, symbol=None, interval='1m'):
        timezone = pytz.timezone("UTC")

        if symbol is None:
            symbols = self.yfdb.symbols.find()
        else:
            symbols = self.yfdb.symbols.find({'sym': symbol})
        for symbol in symbols:
            # download dataframe
            quote = yf.Ticker(symbol['sym'])
            # data = quote.history(start=startDate.replace("/", "-"), end=endDate.replace("/", "-"), interval=interval)
            data = quote.history(start=startDate.replace("/", "-"), interval=interval)

            # set index to column in pandas DataFrame
            data.reset_index(inplace=True)

            if "Datetime" in data:
                lastTicker = self.getLastTicker(symbol['sym'])

                # update already exists in database
                if lastTicker:
                    storedData = timezone.localize(self.getLastTicker(symbol['sym']))
                    apiData = data["Datetime"].iat[-1].to_pydatetime().astimezone(timezone)

                    print(apiData.timestamp() - storedData.timestamp())

                    if len(data) > 0 and apiData.timestamp() - storedData.timestamp() > 120:
                        self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                                    + symbol['sym'] + "' (" + str(len(data)) + " entries)")
                        data['ticker'] = symbol['sym']
                        self.yfdb.timeline.insert_many(data.to_dict(orient='records'))

                # insert new data
                else:
                    if len(data) > 0:
                        self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                                    + symbol['sym'] + "' (" + str(len(data)) + " entries)")
                        data['ticker'] = symbol['sym']
                        self.yfdb.timeline.insert_many(data.to_dict(orient='records'))


    def getTicker(self, symbol):
        print(symbol)
        self.add(symbol)
        self.update()

        symbols = self.yfdb.timeline.find({'ticker': symbol})
        volume = {}
        close = {}
        cleanSymbols = {}

        for s in symbols:
            datetimeStock = (int)(s['Datetime'].timestamp() * 1000)
            volume[datetimeStock] = s['Volume']
            close[datetimeStock] = s['Close']

        cleanSymbols["Close"] = close
        cleanSymbols["Volume"] = volume
        return cleanSymbols


    def getLastTicker(self, symbol):
        symbols = self.yfdb.timeline.find({'ticker': symbol}).sort('_id', -1).limit(1);
        symbolsList = list(symbols)

        if len(symbolsList) == 0:
            return None
        elif 'Datetime' in symbolsList[0]:
            return symbolsList[0]['Datetime']
        else:
            return None
