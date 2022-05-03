from flask import Flask, request, render_template, jsonify
import yfinance as yf
from mongoYfinance import *
import pandas as pd
import sys

# instantiate the Flask app.
app = Flask(__name__)
yfdb = mongoYfinance("tccanaliseacoes", "oiDHq8LUtoKUkyIA",
                         "cluster0.qxqqc.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

# API Route for pulling the stock quote
@app.route("/quote")
def display_quote():
    # get a stock ticker symbol from the query string
    # default to AAPL
    symbol = request.args.get('symbol', default="AAPL")

    # pull the stock quote
    quote = yf.Ticker(symbol)

    # pprint(vars(quote))
    # app.logger.info(vars(quote))

    # return the object via the HTTP Response
    return jsonify(quote.info)


# API route for pulling the stock history
@app.route("/history")
def display_history():
    # get the query string parameters
    symbol = request.args.get('symbol', default="AAPL")
    period = request.args.get('period', default="7d")
    interval = request.args.get('interval', default="1m")

    # pull the quote
    quote = yf.Ticker(symbol)
    # use the quote to pull the historical data from Yahoo finance
    hist = quote.history(period=period, interval=interval)
    # convert the historical data to JSON
    data = hist.to_json()

    # return the JSON in the HTTP response
    return data

# API route for pulling the stock history
@app.route("/historydb")
def display_history_db():
    # get the query string parameters
    symbol = request.args.get('symbol', default="AAPL")
    # period = request.args.get('period', default="7d")
    # interval = request.args.get('interval', default="1m")

    # use the quote to pull the historical data from Yahoo finance stored in MongoDB
    hist = yfdb.getTicker(symbol)
    # convert the historical data to JSON
    data = json.dumps(hist)

    # return the JSON in the HTTP response
    return data


# This is the / route, or the main landing page route.
@app.route("/")
def home():
    # we will use Flask's render_template method to render a website template.
    return render_template("home.html")


# run the flask app.
if __name__ == "__main__":
    # yfdb = mongoYfinance("tccanaliseacoes", "oiDHq8LUtoKUkyIA", "cluster0.qxqqc.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
    # print(type(yfdb.getTicker("BTC-USD")))
    app.run(debug=True)