import os
import logging
import re
import requests
from functools import wraps
from flask import render_template, session, redirect, flash

from dotenv import load_dotenv
import json

# Load environment variables from the .env file
load_dotenv()
logger = logging.getLogger(__name__)


def _env(name):
    value = os.getenv(name, "")
    return value.strip()


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
    finnhub_key = _env("FINNHUB_API_KEY")
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
        except Exception:
            logger.exception("Finnhub API lookup failed for symbol %s", symbol)

    # Try Alpha Vantage API as fallback
    alpha_vantage_key = _env("ALPHA_VANTAGE_API_KEY")
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
        except Exception:
            logger.exception("Alpha Vantage lookup failed for symbol %s", symbol)
    
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
    except Exception:
        logger.exception("Yahoo Finance lookup failed for symbol %s", symbol)

    # If all APIs fail, return None
    flash(f"Unable to fetch data for symbol {symbol}. Please try again later.")
    return None


def get_stock_suggestions(query):
    """Get stock symbol suggestions using multiple APIs."""
    suggestions = []
    
    # Try Finnhub symbol search first
    finnhub_key = _env("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            url = f"https://finnhub.io/api/v1/search?q={query}&token={finnhub_key}"
            response = requests.get(url, timeout=5).json()
            
            if response.get("result"):
                suggestions = [item["symbol"] for item in response["result"][:10]]
                return suggestions
        except Exception:
            logger.exception("Finnhub symbol search failed for query %s", query)
    
    # Try Alpha Vantage as fallback
    alpha_vantage_key = _env("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_key:
        try:
            url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={alpha_vantage_key}"
            response = requests.get(url, timeout=5).json()
            
            if "bestMatches" in response:
                suggestions = [match['1. symbol'] for match in response['bestMatches'][:10]]
                return suggestions
        except Exception:
            logger.exception("Alpha Vantage symbol search failed for query %s", query)
    
    return suggestions


def _format_market_context(market_context):
    if not market_context:
        return "Market data is not available right now."

    parts = []
    for name, details in market_context.items():
        direction = "up" if details.get("change", 0) >= 0 else "down"
        parts.append(
            f"{name} {direction} {abs(details.get('change_percent', 0)):.2f}% "
            f"at {details.get('price', 0):,.2f}"
        )
    return "; ".join(parts)


def _format_portfolio_context(portfolio_context):
    if not portfolio_context:
        return "No portfolio context available."

    cash = portfolio_context.get("cash", 0)
    total_value = portfolio_context.get("total_value", cash)
    positions = portfolio_context.get("positions", [])

    if not positions:
        return f"User has no open positions and ${cash:,.2f} in cash."

    top_positions = sorted(positions, key=lambda item: item.get("value", 0), reverse=True)[:3]
    summary = ", ".join(
        f"{item.get('symbol')} ({item.get('shares')} shares, value ${item.get('value', 0):,.2f})"
        for item in top_positions
    )
    return (
        f"User has {len(positions)} positions, ${cash:,.2f} cash, and total portfolio value "
        f"of ${total_value:,.2f}. Largest positions: {summary}."
    )


def _rule_based_finance_response(message, portfolio_context=None, market_context=None):
    text = message.lower().strip()
    portfolio_context = portfolio_context or {}
    positions = portfolio_context.get("positions", [])
    symbols = [position.get("symbol", "").upper() for position in positions]

    if any(phrase in text for phrase in ["my portfolio", "my holdings", "what do i own", "summarize my account"]):
        if not positions:
            return (
                f"You currently have no open positions and {usd(portfolio_context.get('cash', 0))} in cash. "
                "A simple next move is to research 2-3 stocks or ETFs and start with a small, diversified first buy."
            )

        top_position = max(positions, key=lambda item: item.get("value", 0))
        total_value = portfolio_context.get("total_value", 0)
        cash = portfolio_context.get("cash", 0)
        return (
            f"You have {len(positions)} open positions worth {usd(total_value)} overall, including {usd(cash)} in cash. "
            f"Your largest holding is {top_position['symbol']} at about {usd(top_position['value'])}. "
            "If you want, ask me for diversification ideas, risk review, or thoughts on a specific holding."
        )

    if any(phrase in text for phrase in ["market", "how is the market", "market today", "indices"]):
        return f"Current market snapshot: {_format_market_context(market_context)}."

    if any(phrase in text for phrase in ["diversification", "diversify"]):
        if len(positions) <= 2:
            return (
                "Your portfolio looks concentrated. A practical way to diversify is to add exposure across sectors "
                "or use a broad-market ETF so one stock does not dominate your results."
            )
        return (
            "Diversification means not letting one position or one sector drive your whole outcome. "
            "A balanced mix of broad ETFs plus selective stock picks is often easier to manage than many overlapping bets."
        )

    if any(phrase in text for phrase in ["risk", "too risky", "safe"]):
        concentration_hint = ""
        if positions:
            largest = max(positions, key=lambda item: item.get("value", 0))
            total_value = portfolio_context.get("total_value", 0) or 1
            pct = largest.get("value", 0) / total_value * 100
            concentration_hint = (
                f" Right now your largest position is {largest.get('symbol')} at roughly {pct:.1f}% of the portfolio."
            )
        return (
            "Portfolio risk usually comes from concentration, volatility, and time horizon mismatch."
            f"{concentration_hint} A good rule is to size positions so one bad week in a single stock does not wreck the account."
        )

    if any(phrase in text for phrase in ["etf", "index fund", "index"]):
        return (
            "ETFs are useful because they bundle many stocks into one trade. "
            "Broad-market ETFs can reduce single-stock risk, while sector ETFs let you take a focused view with more diversification than owning one company."
        )

    matching_symbols = [symbol for symbol in symbols if symbol and symbol.lower() in text]
    if matching_symbols:
        symbol = matching_symbols[0]
        return (
            f"{symbol} is already in your portfolio. A smart next question is whether you want help reviewing position size, "
            f"cost basis, or whether it fits your diversification plan."
        )

    if re.search(r"\b(buy|sell)\b", text):
        return (
            "Before buying or selling, check three things: your time horizon, how large the position will be in the portfolio, "
            "and whether the move improves or worsens concentration risk."
        )

    return (
        "I can help with portfolio review, diversification, ETFs, market context, risk, and stock questions. "
        "Try asking things like 'summarize my portfolio', 'how risky is my account?', or 'how is the market today?'."
    )


def get_finance_response(message, portfolio_context=None, market_context=None):
    """Generate finance-related responses using AI with a strong local fallback."""

    groq_key = _env("GROQ_API_KEY")
    if groq_key:
        try:
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }

            portfolio_summary = _format_portfolio_context(portfolio_context)
            market_summary = _format_market_context(market_context)

            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a sharp finance copilot inside a stock portfolio app. "
                            "Be practical, concise, and personalized when portfolio context is available. "
                            "Do not mention missing tools or API issues. Keep answers under 140 words and end with one useful next step when appropriate."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Portfolio context: {portfolio_summary}\n"
                            f"Market context: {market_summary}\n"
                            f"User question: {message}"
                        ),
                    },
                ],
                "model": "llama-3.1-8b-instant",
                "max_tokens": 300,
                "temperature": 0.4,
            }

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content:
                return content
        except Exception:
            logger.exception("Groq finance response generation failed")

    return _rule_based_finance_response(message, portfolio_context=portfolio_context, market_context=market_context)


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
