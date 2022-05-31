# Inspired in
# https://github.com/grizzlypeaksoftware/Flask-Stock-Widget
# https://github.com/rubenafo/yfMongo

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

            self.yfdb.symbols.replace_one({'_id': {'sym': symbol}},
                                          {'_id': {'sym': symbol}, 'shortName': quote.info['shortName']}, upsert=True)
            self.sprint("'" + symbol + "'" + " added to the database")
            oldestDate = datetime.today() - timedelta(days=6)
            self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                               symbol=symbol)

            result = {'symbolExists': True, 'added': True, 'message': 'Symbol ' + symbol + ' was successfully added',
                      'sym': symbol, 'shortName': quote.info['shortName']}
        else:
            symbols = self.yfdb.symbols.find({'_id.sym': symbol})
            for s in symbols:
                result = {'symbolExists': True, 'added': False,
                          'message': 'Symbol ' + symbol + ' is already in database',
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
                dateToday = datetime.today()
                oldestDate = max(map(lambda s: self.__getFormattedDate(s), tickerTimeline))
                delta = dateToday - oldestDate

                endDate = oldestDate
                week_period = delta.days // 6
                day_period = delta.days % 6
                if week_period > 0:
                    for i in range(1, week_period):
                        if oldestDate is not None:
                            endDate = endDate+timedelta(days=6)

                            print("oldestDate:", oldestDate, "endDate:", endDate, "week_period:", week_period)
                            self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                               endDate.strftime("%Y/%m/%d"),
                                               symbol=ticker["_id"]["sym"])

                if week_period > 0 and day_period > 0:
                    if oldestDate is not None:
                        endDate = endDate + timedelta(days=day_period)
                        print("oldestDate:", oldestDate, "endDate:", endDate, "day_period:", day_period)
                        self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                           endDate.strftime("%Y/%m/%d"),
                                           symbol=ticker["_id"]["sym"])

                # print(tickerTimeline)
                oldestDate = max(map(lambda s: self.__getFormattedDate(s), tickerTimeline))
                print(oldestDate)
                if oldestDate is not None:
                    self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                       None,
                                       symbol=ticker["_id"]["sym"])
            else:
                oldestDate = datetime.today() - timedelta(days=6)
                self.fetchInterval(oldestDate.strftime("%Y/%m/%d"),
                                   None,
                                   symbol=ticker["_id"]["sym"])

    # Fetches symbol data for the interval between startDate and endDate
    # If the symbol is set None, all symbols found in the database are
    # updated.
    def fetchInterval(self, startDate, endDate=None, symbol=None, interval='1m'):
        timezone = pytz.timezone("UTC")

        if symbol is None:
            symbols = self.yfdb.symbols.find()
        else:
            symbols = self.yfdb.symbols.find(({'_id.sym': symbol}))
        for symbol in symbols:
            # download dataframe
            quote = yf.Ticker(symbol['_id']['sym'])
            # data = quote.history(start=startDate.replace("/", "-"), end=endDate.replace("/", "-"), interval=interval)
            if endDate is not None:
                data = quote.history(start=startDate.replace("/", "-"), end=endDate.replace("/", "-"), interval=interval)
            else:
                data = quote.history(start=startDate.replace("/", "-"), interval=interval)
            # set index to column in pandas DataFrame
            data.reset_index(inplace=True)

            data.dropna(inplace=True)

            self.sprint(data)

            if "Datetime" in data:
                lastTicker = self.getLastTicker(symbol['_id']['sym'])
                tickersNotRounded = data[data['Datetime'].dt.second > 0].index
                data.drop(tickersNotRounded, inplace=True)

                if len(data) > 0:
                    # self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                    #             + symbol['_id']['sym'] + "' (" + str(len(data)) + " entries)")
                    dictData = data.to_dict(orient='records')

                    for data in dictData:
                        data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": data["Datetime"]}
                        data.pop('Datetime', None)

                    ids = [dt.pop("_id") for dt in dictData]

                    operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                                  zip(ids, dictData)]

                    self.yfdb.timeline.bulk_write(operations)

            if "Date" in data:
                if len(data) > 0:
                    # self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                    #             + symbol['_id']['sym'] + "' (" + str(len(data)) + " entries)")
                    dictData = data.to_dict(orient='records')

                    for data in dictData:
                        date = datetime.combine(data["Date"], datetime.min.time())
                        data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": date}
                        data.pop('Date', None)

                    self.sprint(data)

                    ids = [dt.pop("_id") for dt in dictData]

                    operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                                  zip(ids, dictData)]

                    self.yfdb.timeline.bulk_write(operations)

                # update already exists in database
                # if lastTicker:
                #     # storedData = timezone.localize(self.getLastTicker(symbol['sym']))
                #     # apiData = data["Datetime"].iat[-1].to_pydatetime().astimezone(timezone)
                #
                #     print(apiData.timestamp() - storedData.timestamp())
                #
                #     if len(data) > 0 and apiData.timestamp() - storedData.timestamp() > 120:
                #         # self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                #         #             + symbol['sym'] + "' (" + str(len(data)) + " entries)")
                #         dictData = data.to_dict(orient='records')
                #
                #         for data in dictData:
                #             data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": data["Datetime"]}
                #             data.pop('Datetime', None)
                #
                #         ids = [dt.pop("_id") for dt in dictData]
                #
                #         operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                #                       zip(ids, dictData)]
                #
                #         self.yfdb.timeline.bulk_write(operations)
                #
                # # insert new data
                # else:
                #     if len(data) > 0:
                #         # self.sprint("Adding '[" + startDate + ", " + endDate + "]' data for symbol '"
                #         #             + symbol['_id']['sym'] + "' (" + str(len(data)) + " entries)")
                #         dictData = data.to_dict(orient='records')
                #
                #         for data in dictData:
                #             data["_id"] = {"sym": symbol['_id']['sym'], "Datetime": data["Datetime"]}
                #             data.pop('Datetime', None)
                #
                #         ids = [dt.pop("_id") for dt in dictData]
                #
                #         operations = [UpdateOne({"_id": idn}, {'$set': dt}, upsert=True) for idn, dt in
                #                       zip(ids, dictData)]
                #
                #         self.yfdb.timeline.bulk_write(operations)

    def getTicker(self, symbol):
        # self.add(symbol)
        self.update()

        symbols = self.yfdb.timeline.find({'_id.sym': symbol}).sort('_id.Datetime', 1)
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

    def periodInterval(self, x):
        """
            Return two variables with interval and period to be fetched from API
            Parameters:
              x - interval from each close
            Return:
              interval - interval in minutes to calculate the indicators
              days - period in days to fetch data from API
        """
        match x:
            # case 'period':
            #     return period in minutes, interval in days to be fetched
            case '1m':
                return 1, 6
            case '5m':
                return 5, 59
            case '15m':
                return 15, 59
            case '30m':
                return 30, 59
            case '1hr':
                return 60, 300
            case '2hr':
                return 2 * 60, 300
            case '4hr':
                return 4 * 60, 300
            case '12hr':
                return 12 * 60, 300
            case '1d':
                return 1 * 24 * 60, 300
            case '5d':
                return 5 * 24 * 60, 1500
            case '1wk':
                return 7 * 24 * 60, 2100
            case '1mo':
                return 30 * 24 * 60, 9000
            case _:
                return 5, 59   # 5, 59 is the default case if x is not found

    # https://www.mongodb.com/developer/article/time-series-macd-rsi/
    def getIndicators(self, symbol, interval='5m'):

        intervalInMinutes, days = self.periodInterval(interval)
        self.sprint(intervalInMinutes)
        self.sprint(days)
        self.sprint(1000 * 60 * intervalInMinutes)

        date = datetime.today() - timedelta(days=days)
        self.fetchInterval(date.strftime("%Y/%m/%d"), None, symbol, interval)

        indicators = self.yfdb.timeline.aggregate([
            {
                "$match": {
                    "_id.sym": symbol,
                }
            },
            {
                "$group": {
                    "_id": {
                        "sym": "$_id.sym",
                        "Datetime": {
                            "$subtract": [
                                {"$toLong": "$_id.Datetime"},
                                {"$mod": [{"$toLong": "$_id.Datetime"}, 1000 * 60 * intervalInMinutes]}
                            ]
                        }
                    },
                    "close": {"$last": "$Close"},
                    "volume": {"$last": "$Volume"},
                },
            },
            {
                "$sort": {
                    "_id.Datetime": 1,
                },
            },
            {
                "$project": {
                    "_id": 1,
                    "price": "$close",
                    "volume": "$volume"
                }
            },
            {
                "$setWindowFields": {
                    "partitionBy": "$id.sym",
                    "sortBy": {"quantity": -1},
                    "output": {
                        "count": {
                            "$documentNumber": {}
                        }
                    }
                }
            },
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "ema_10": {
                            "$expMovingAvg": {"input": "$price", "N": 10},
                        },
                        "ema_20": {
                            "$expMovingAvg": {"input": "$price", "N": 20},
                        },
                        "ema_50": {
                            "$expMovingAvg": {"input": "$price", "N": 50},
                        },
                        "ema_100": {
                            "$expMovingAvg": {"input": "$price", "N": 100},
                        },
                        "ema_200": {
                            "$expMovingAvg": {"input": "$price", "N": 200},
                        },
                        "ema_12": {
                            "$expMovingAvg": {"input": "$price", "N": 12},
                        },
                        "ema_26": {
                            "$expMovingAvg": {"input": "$price", "N": 26},
                        },
                    },
                },
            },
            {"$addFields": {
                "ema_10": {
                    "$cond": {
                        "if": {"$gte": ["$count", 10]},
                        "then": "$ema_10",
                        "else": None
                    }
                },
                "ema_20": {
                    "$cond": {
                        "if": {"$gte": ["$count", 20]},
                        "then": "$ema_20",
                        "else": None
                    }
                },
                "ema_12": {
                    "$cond": {
                        "if": {"$gte": ["$count", 12]},
                        "then": "$ema_12",
                        "else": None
                    }
                },
                "ema_26": {
                    "$cond": {
                        "if": {"$gte": ["$count", 26]},
                        "then": "$ema_26",
                        "else": None
                    }
                },
                "ema_50": {
                    "$cond": {
                        "if": {"$gte": ["$count", 50]},
                        "then": "$ema_50",
                        "else": None
                    }
                },
                "ema_100": {
                    "$cond": {
                        "if": {"$gte": ["$count", 100]},
                        "then": "$ema_100",
                        "else": None
                    }
                },
                "ema_200": {
                    "$cond": {
                        "if": {"$gte": ["$count", 200]},
                        "then": "$ema_200",
                        "else": None
                    }
                },
            }},
            {"$addFields": {"macdLine": {"$subtract": ["$ema_12", "$ema_26"]}}},
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "macdSignal": {
                            "$expMovingAvg": {"input": "$macdLine", "N": 9},
                        },
                    },
                },
            },
            {
                "$addFields": {"macdHistogram": {"$subtract": ["$macdLine", "$macdSignal"]}},
            }, {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "previousPrice": {"$shift": {"by": -1, "output": "$price"}},
                    },
                },
            },

            # MACD Indicator
            # NOR, Safwan Mohd; WICKREMASINGHE, Guneratne. The profitability of
            # MACD and RSI trading rules in the Australian stock market.
            # Investment management and financial innovations,
            # n. 11, Iss. 4 (contin.), p. 196, 2014.
            {
                "$addFields": {
                    "macd_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$macdLine", None]},
                                            {"$eq": ["$macdSignal", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$gt": ["$macdLine", "$macdSignal"]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$lt": ["$macdLine", "$macdSignal"]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                },
            },
            # End MACD Indicator

            {
                "$addFields": {
                    "diff": {
                        "$subtract": ["$price", {"$ifNull": ["$previousPrice", "$price"]}],
                    },
                },
            },
            {
                "$addFields": {
                    "gain": {"$cond": {"if": {"$gte": ["$diff", 0]}, "then": "$diff", "else": 0}},
                    "loss": {
                        "$cond": {
                            "if": {"$lte": ["$diff", 0]}, "then": {"$abs": "$diff"}, "else": 0
                        },
                    },
                },
            },
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "avgGain": {
                            "$avg": "$gain",
                            "window": {"documents": [-14, 0]},
                        },
                        "avgLoss": {
                            "$avg": "$loss",
                            "window": {"documents": [-14, 0]},
                        },
                    },
                },
            },
            {
                "$addFields": {
                    "relativeStrength": {
                        "$cond": {
                            "if": {
                                "$gt": ["$avgLoss", 0],
                            },
                            "then": {
                                "$cond": [
                                    {"$eq": ["$avgLoss", -1]},
                                    "$avgGain",
                                    {"$divide": ["$avgGain", "$avgLoss"]}
                                ]
                            },
                            "else": "$avgGain",
                        },
                    },
                },
            },
            {
                "$addFields": {
                    "rsi": {
                        "$cond": {
                            "if": {"$gt": ["$count", 14]},
                            "then": {
                                "$cond": [  # Avoid division by zero
                                    {"$eq": ["$relativeStrength", -1]},
                                    None,
                                    {
                                        "$subtract": [
                                            100,
                                            {"$divide": [100, {"$add": [1, "$relativeStrength"]}]},
                                        ]
                                    }
                                ]
                            },
                            "else": None,
                        },
                    },
                },
            },
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "previousRsi": {"$shift": {"by": -1, "output": "$rsi"}},
                    },
                },
            },

            # Chande Momentum Oscillator
            # CHANDE, Tushar S.; KROLL, Stanley.
            # The new technical trader: boost your profit by plugging into the latest indicators.
            # John Wiley & Sons Incorporated, p. 100, 1994.
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "cmoUp": {
                            "$sum": "$gain",
                            "window": {"documents": [-9, 0]},
                        },
                        "cmoDown": {
                            "$sum": "$loss",
                            "window": {"documents": [-9, 0]},
                        },
                    },
                },
            },
            {
                "$addFields": {
                    "cmo_9": {
                        "$cond": {
                            "if": {"$gt": ["$count", 9]},
                            "then": {
                                "$cond": [  # Avoid division by zero
                                    {
                                        "$eq": [
                                            {"$add": ["$cmoUp", "$cmoDown"]}, 0
                                        ]
                                    },
                                    None,
                                    {
                                        "$multiply": [100,
                                                      {
                                                          "$divide": [
                                                              {"$subtract": ["$cmoUp", "$cmoDown"]},
                                                              {"$add": ["$cmoUp", "$cmoDown"]}
                                                          ]
                                                      },
                                                      ]
                                    }
                                ]
                            },
                            "else": None,
                        },
                    },
                },
            },
            {
                "$addFields": {
                    "cmo_9_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$eq": ["$cmo_9", None]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$and": [
                                            {"$lt": ["$cmo_9", -70]},
                                            {"$ifNull": ["$cmo_9", False]}
                                        ]},
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$and": [
                                            {"$gt": ["$cmo_9", 70]},
                                            {"$ifNull": ["$cmo_9", False]}
                                        ]},
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                },
            },
            # End Chande Momentum Oscillator

            # EMA's Indicators
            # DI LORENZO, Renato. Basic technical analysis of financial markets.
            # Milan, Italy: Springer, p. 58, 2013.
            {
                "$addFields": {
                    "ema_10_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$ema_20", None]},
                                            {"$eq": ["$ema_10", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$lt": ["$ema_20", "$ema_10"]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$gt": ["$ema_20", "$ema_10"]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                    "ema_20_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$ema_50", None]},
                                            {"$eq": ["$ema_20", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$lt": ["$ema_50", "$ema_20"]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$gt": ["$ema_50", "$ema_20"]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                    "ema_50_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$ema_100", None]},
                                            {"$eq": ["$ema_50", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$lt": ["$ema_100", "$ema_50"]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$gt": ["$ema_100", "$ema_50"]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                    "ema_100_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$ema_200", None]},
                                            {"$eq": ["$ema_100", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$lt": ["$ema_200", "$ema_100"]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                                {
                                    "case": {
                                        "$gt": ["$ema_200", "$ema_100"]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                },
            },
            # End EMA's Indicators

            # RSI Indicator
            # ANDERSON, Bing; LI, Shuyun. An investigation of the relative strength index.
            # Banks & bank systems, n. 10, Iss. 1, p. 92-96, 2015.
            # "Surprisingly, the trading simulation with RSI at 40 and
            # 60 being the buy/sell threshold performs the best
            # among all the parameter combinations we have tested
            # so far. The total profit is 5206 pips. There are 125
            # trades in total. The trade with the biggest loss has a
            # loss of 1876 pips."
            {
                "$addFields": {
                    "rsi_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$rsi", None]},
                                            {"$eq": ["$previousRsi", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$and": [
                                            {"$gt": ["$rsi", 60]},
                                            {"$gt": ["$previousRsi", "$rsi"]}
                                        ]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}},
                                {
                                    "case": {
                                        "$and": [
                                            {"$lt": ["$rsi", 40]},
                                            {"$lt": ["$previousRsi", "$rsi"]}
                                        ]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}
                                },
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    },
                },
            },
            #End RSI Oscillator

            # Stochastic RSI Oscillator
            # CHANDE, Tushar S.; KROLL, Stanley.
            # The new technical trader: boost your profit by plugging into the latest indicators.
            # John Wiley & Sons Incorporated, p. 124, 1994.
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "rsi_stoch_low": {
                            "$min": "$rsi",
                            "window": {"documents": [-14, 0]},
                        },
                        "rsi_stoch_high": {
                            "$max": "$rsi",
                            "window": {"documents": [-14, 0]},
                        },
                    },
                },
            },
            {
                "$addFields": {
                    "rsi_stoch": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$gt": ["$count", 14]},
                                    {"$gt": [{"$subtract": ["$rsi_stoch_high", "$rsi_stoch_low"]}, 0]}
                                ]
                            },
                            "then": {
                                "$cond": [  # Avoid division by zero
                                    {
                                        "$eq": [{"$subtract": ["$rsi_stoch_high", "$rsi_stoch_low"]}, 0]
                                    },
                                    None,
                                    {
                                        "$divide": [
                                            {"$subtract": ["$rsi", "$rsi_stoch_low"]},
                                            {"$subtract": ["$rsi_stoch_high", "$rsi_stoch_low"]},
                                        ]
                                    }
                                ]
                            },
                            "else": None,
                        },
                    }
                },

            },
            {
                "$setWindowFields": {
                    "partitionBy": "$_id.sym",
                    "sortBy": {"_id.Datetime": 1},
                    "output": {
                        "previousRsiStoch": {"$shift": {"by": -1, "output": "$rsi_stoch"}},
                    },
                },
            },
            {
                "$addFields": {
                    "rsi_stoch_indicator": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$or": [
                                            {"$eq": ["$rsi_stoch", None]},
                                            {"$eq": ["$previousRsiStoch", None]}
                                        ]
                                    },
                                    "then": {"weight": None, "recommendation": None}
                                },
                                {
                                    "case": {
                                        "$and": [
                                            {"$gt": ["$rsi_stoch", 0.8]},
                                            {"$gt": ["$previousRsiStoch", "$rsi_stoch"]},
                                            {"$ifNull": ["$rsi_stoch", False]}
                                        ]
                                    },
                                    "then": {"weight": -1, "recommendation": "Sell"}},
                                {
                                    "case": {
                                        "$and": [
                                            {"$lt": ["$rsi_stoch", 0.2]},
                                            {"$lt": ["$previousRsiStoch", "$rsi_stoch"]},
                                            {"$ifNull": ["$rsi_stoch", False]}
                                        ]
                                    },
                                    "then": {"weight": 1, "recommendation": "Buy"}},
                            ],
                            "default": {"weight": 0, "recommendation": "Neutral"}
                        }
                    }
                },
            },
            # End Stochastic RSI Oscillator

            {
                "$addFields": {
                    "indicators_tendency":
                        {
                            "$sum": [
                                "$macd_indicator.weight",
                                "$cmo_9_indicator.weight",
                                "$ema_10_indicator.weight",
                                "$ema_20_indicator.weight",
                                "$ema_50_indicator.weight",
                                "$ema_100_indicator.weight",
                                "$rsi_indicator.weight",
                                "$rsi_stoch_indicator.weight",
                            ]
                        }
                },
            },
            {
                "$addFields": {
                    "indicators_recommendation": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$gt": ["$indicators_tendency", 4]
                                    },
                                    "then": "Strong Buy"
                                },
                                {
                                    "case": {
                                        "$gt": ["$indicators_tendency", 0]
                                    },
                                    "then": "Buy"
                                },
                                {
                                    "case": {
                                        "$lt": ["$indicators_tendency", -4]
                                    },
                                    "then": "Strong Sell"
                                },
                                {
                                    "case": {
                                        "$lt": ["$indicators_tendency", 0]
                                    },
                                    "then": "Sell"
                                },
                            ],
                            "default": "Neutral"
                        }
                    },
                },
            },
            {
                "$addFields": {
                    "indicators_up": {
                        "$sum": [
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$macd_indicator.weight", 0]},
                                            {"$ifNull": ["$macd_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$cmo_9_indicator.weight", 0]},
                                            {"$ifNull": ["$cmo_9_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$ema_10_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_10_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$ema_20_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_20_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$ema_50_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_50_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$ema_100_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_100_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$rsi_indicator.weight", 0]},
                                            {"$ifNull": ["$rsi_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$gt": ["$rsi_stoch_indicator.weight", 0]},
                                            {"$ifNull": ["$rsi_stoch_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                        ]
                    },
                    "indicators_down": {
                        "$sum": [
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$macd_indicator.weight", 0]},
                                            {"$ifNull": ["$macd_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$cmo_9_indicator.weight", 0]},
                                            {"$ifNull": ["$cmo_9_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$ema_10_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_10_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$ema_20_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_20_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$ema_50_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_50_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$ema_100_indicator.weight", 0]},
                                            {"$ifNull": ["$ema_100_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$rsi_indicator.weight", 0]},
                                            {"$ifNull": ["$rsi_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$and": [
                                            {"$lt": ["$rsi_stoch_indicator.weight", 0]},
                                            {"$ifNull": ["$rsi_stoch_indicator.weight", False]}
                                        ]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                        ]
                    },
                    "indicators_neutral": {
                        "$sum": [
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$macd_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$cmo_9_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$ema_10_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$ema_20_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$ema_50_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$ema_100_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$rsi_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                            {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$rsi_stoch_indicator.weight", 0]
                                    },
                                    "then": 1, "else": 0
                                }
                            },
                        ]
                    },
                },
            }
        ])

        # self.sprint(list(indicators))

        return list(indicators)

#
# -6  Strong Sell
#
# -3 Sell
#
# 0 Neutral
#
# + 3 Buy
#
# + 6 Strong Buy