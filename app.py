from flask import Flask, request, render_template, jsonify
import yfinance as yf
import pandas as pd
import sys

# instantiate the Flask app.
app = Flask(__name__)

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

	#return the object via the HTTP Response
	return jsonify(quote.info)

# API route for pulling the stock history
@app.route("/history")
def display_history():
	#get the query string parameters
	symbol = request.args.get('symbol', default="AAPL")
	period = request.args.get('period', default="60d")
	interval = request.args.get('interval', default="30m")

	#pull the quote
	quote = yf.Ticker(symbol)
	#use the quote to pull the historical data from Yahoo finance
	hist = quote.history(period=period, interval=interval)
	#convert the historical data to JSON
	data = hist.to_json()
	
	#return the JSON in the HTTP response
	return data

# This is the / route, or the main landing page route.
@app.route("/")
def home():
	# we will use Flask's render_template method to render a website template.
    return render_template("home.html")

# run the flask app.
if __name__ == "__main__":
	app.run(debug=True)
