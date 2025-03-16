import os
import requests
from functools import wraps
from flask import render_template, session, redirect, flash

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """Escape special characters."""
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("You must be logged in to access this page.")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Lookup stock symbol using Alpha Vantage."""
    api_key = os.getenv("AVL2XQV12AU3T64L")

    if not api_key:
        flash("API Key not found. Please set ALPHA_VANTAGE_API_KEY in your environment.")
        return None

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={api_key}"

    try:
        response = requests.get(url).json()

        if "Time Series (1min)" in response:
            last_refreshed = response["Meta Data"]["3. Last Refreshed"]
            data = response["Time Series (1min)"][last_refreshed]

            price = float(data["4. close"])

            return {
                "symbol": symbol,
                "name": symbol,  
                "price": price
            }
        else:
            flash(f"Error: No data found for symbol {symbol}.")
            return None

    except requests.exceptions.RequestException as e:
        flash(f"Error while fetching stock data: {e}")
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
