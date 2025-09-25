import os
import requests
from functools import wraps
from flask import render_template, session, redirect, flash

from dotenv import load_dotenv
import json

# Load environment variables from the .env file
load_dotenv()


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

    """Lookup stock symbol using multiple free APIs as fallbacks."""
    
    # Try Finnhub API first (best free API for stocks)
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            # Get current price
            price_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}"
            price_response = requests.get(price_url, timeout=10).json()
            
            # Get company profile for name
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={finnhub_key}"
            profile_response = requests.get(profile_url, timeout=10).json()
            
            if price_response.get("c") and price_response.get("c") > 0:  # 'c' is current price
                return {
                    "symbol": symbol.upper(),
                    "name": profile_response.get("name", symbol.upper()),
                    "price": float(price_response["c"])
                }
        except Exception as e:
            print(f"Finnhub API error: {e}")

    # Try Alpha Vantage API as fallback
    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_key:
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
            response = requests.get(url, timeout=10).json()
            
            if "Global Quote" in response and response["Global Quote"]:
                quote = response["Global Quote"]
                price = float(quote["05. price"])
                
                return {
                    "symbol": symbol.upper(),
                    "name": symbol.upper(),  # Alpha Vantage doesn't provide company name in this endpoint
                    "price": price
                }
        except Exception as e:
            print(f"Alpha Vantage API error: {e}")
    
    # Try Yahoo Finance alternative (via yfinance-like API)
    try:
        # Using a free Yahoo Finance API alternative
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10).json()
        
        if response.get("chart") and response["chart"]["result"]:
            result = response["chart"]["result"][0]
            price = result["meta"]["regularMarketPrice"]
            name = result["meta"].get("longName", symbol.upper())
            
            return {
                "symbol": symbol.upper(),
                "name": name,
                "price": float(price)
            }
    except Exception as e:
        print(f"Yahoo Finance API error: {e}")

    # If all APIs fail, return None
    flash(f"Unable to fetch data for symbol {symbol}. Please try again later.")
    return None


def get_stock_suggestions(query):
    """Get stock symbol suggestions using multiple APIs."""
    suggestions = []
    
    # Try Finnhub symbol search first
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            url = f"https://finnhub.io/api/v1/search?q={query}&token={finnhub_key}"
            response = requests.get(url, timeout=5).json()
            
            if response.get("result"):
                suggestions = [item["symbol"] for item in response["result"][:10]]
                return suggestions
        except Exception as e:
            print(f"Finnhub search error: {e}")
    
    # Try Alpha Vantage as fallback
    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_key:
        try:
            url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={alpha_vantage_key}"
            response = requests.get(url, timeout=5).json()
            
            if "bestMatches" in response:
                suggestions = [match['1. symbol'] for match in response['bestMatches'][:10]]
                return suggestions
        except Exception as e:
            print(f"Alpha Vantage search error: {e}")
    
    return suggestions


def get_finance_response(message):
    """Generate finance-related responses using free AI APIs."""
    
    # Try Groq API first (fastest and most reliable free option)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""You are a helpful finance assistant. Provide accurate, educational information about finance, investing, and stock market topics. Keep responses concise and helpful.

User question: {message}

Response (keep it under 150 words):"""

            payload = {
                "messages": [
                    {"role": "system", "content": "You are a knowledgeable finance assistant providing educational information about investing, stocks, and personal finance."},
                    {"role": "user", "content": prompt}
                ],
                "model": "llama3-8b-8192",
                "max_tokens": 300,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"Groq API error: {e}")
    
    # Fallback to predefined responses for common questions
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["diversification", "diversify"]):
        return "Diversification means spreading your investments across different assets to reduce risk. Don't put all your eggs in one basket - consider investing in various sectors, company sizes, and even asset classes like stocks, bonds, and REITs."
    
    elif any(word in message_lower for word in ["portfolio", "allocation"]):
        return "A balanced portfolio typically includes a mix of stocks, bonds, and other assets based on your risk tolerance and time horizon. Young investors often favor more stocks (70-90%), while those near retirement might prefer more bonds (40-60%)."
    
    elif any(word in message_lower for word in ["risk", "risky"]):
        return "Investment risk refers to the possibility of losing money or not meeting expected returns. Higher risk often comes with potential for higher returns. Always invest only what you can afford to lose and consider your risk tolerance."
    
    elif any(word in message_lower for word in ["dividend", "dividends"]):
        return "Dividends are payments companies make to shareholders from their profits. Dividend-paying stocks can provide regular income, but companies can cut or eliminate dividends during tough times."
    
    elif any(word in message_lower for word in ["etf", "index"]):
        return "ETFs (Exchange Traded Funds) are baskets of stocks that trade like individual stocks. Index ETFs track market indexes like the S&P 500, offering instant diversification at low cost. They're great for beginners."
    
    elif any(word in message_lower for word in ["buy", "sell", "when"]):
        return "Timing the market is extremely difficult. Consider dollar-cost averaging - investing fixed amounts regularly regardless of market conditions. Focus on long-term investing rather than short-term trading."
    
    else:
        return "I can help you with topics like portfolio diversification, risk management, ETFs, dividends, and basic investment strategies. What specific finance topic would you like to learn about?"


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"



def get_market_data():
    """Get basic market data for major indices."""
    try:
        # Using a free financial API for market data
        indices = ["^GSPC", "^IXIC", "^DJI"]  # S&P 500, NASDAQ, DOW
        market_data = {}
        
        for index in indices:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{index}"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=5).json()
                
                if response.get("chart") and response["chart"]["result"]:
                    result = response["chart"]["result"][0]
                    current_price = result["meta"]["regularMarketPrice"]
                    previous_close = result["meta"]["previousClose"]
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    
                    name_map = {
                        "^GSPC": "S&P 500",
                        "^IXIC": "NASDAQ",
                        "^DJI": "DOW"
                    }
                    
                    market_data[name_map[index]] = {
                        "price": current_price,
                        "change": change,
                        "change_percent": change_percent
                    }
            except:
                continue
                
        return market_data
    except:
        return {}
