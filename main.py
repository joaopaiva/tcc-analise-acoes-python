from flask import Flask, request, render_template, jsonify
from mongoYfinance import *

# instantiate the Flask app.
app = Flask(__name__)
yfdb = mongoYfinance("tccanaliseacoes", "oiDHq8LUtoKUkyIA",
                     "cluster0.qxqqc.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")


@app.route("/indicators")
def display_indicators_db():
    # get the query string parameters
    symbol = request.args.get('symbol', default="AAPL")
    interval = request.args.get('interval', default="5m")

    # use the quote to pull the historical data from Yahoo finance stored in MongoDB
    hist = yfdb.getIndicators(symbol, interval)
    # convert the historical data to JSON
    # data = json.dumps(hist, indent=4, sort_keys=True, default=str)
    data = jsonify(hist)
    yfdb.sprint(hist)
    # return the JSON in the HTTP response
    return data


@app.route("/lastIndicators")
def display_last_indicators_db():
    # get the query string parameters
    symbol = request.args.get('symbol', default="AAPL")
    # period = request.args.get('period', default="7d")
    # interval = request.args.get('interval', default="1m")

    # use the quote to pull the historical data from Yahoo finance stored in MongoDB
    hist = yfdb.getIndicators(symbol)
    # convert the historical data to JSON
    # data = json.dumps(hist, indent=4, sort_keys=True, default=str)
    data = jsonify(hist[-1])
    yfdb.sprint(hist[-1])
    # return the JSON in the HTTP response
    return data


# API route for remove symbol
@app.route("/list")
def list_symbol_db():
    # get listed symbols stored in MongoDB
    hist = yfdb.listSymbols()
    # convert the return data to JSON
    data = json.dumps(hist)

    # return the JSON in the HTTP response
    return data


# API route for add symbol
@app.route("/get")
def get_symbol_db():
    # get the query string parameters
    symbol = request.args.get('symbol')

    # get return data
    result = yfdb.add(symbol)
    # convert the return data to JSON
    data = json.dumps(result)

    # return the JSON in the HTTP response
    return data


# API route for pulling the stock history
@app.route("/remove")
def remove_symbol_db():
    # get the query string parameters
    symbol = request.args.get('symbol')
    # period = request.args.get('period', default="7d")
    # interval = request.args.get('interval', default="1m")

    # use the quote to pull the historical data from Yahoo finance stored in MongoDB
    hist = yfdb.remove(symbol)
    # convert the return data to JSON
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