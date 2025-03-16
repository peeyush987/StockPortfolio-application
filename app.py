import os
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd
from flask_sqlalchemy import SQLAlchemy 
from flask_session import Session
from datetime import datetime
import requests
from dotenv import load_dotenv # type: ignore

# Load environment variables from the .env file
load_dotenv()


app = Flask(__name__)

app.jinja_env.filters["usd"] = usd

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///finance.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    hash = db.Column(db.String(120), nullable=False)
    cash = db.Column(db.Float, default=10000) 

    trades = db.relationship('Trade', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Trade(db.Model):
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Trade {self.symbol} {self.shares} shares at {self.price}>'
    
def get_stock_suggestions(query):
    """Fetch stock symbol suggestions based on the user input."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={api_key}"
    response = requests.get(url).json()

    if "bestMatches" in response:
        suggestions = [match['1. symbol'] for match in response['bestMatches']]
        return suggestions
    else:
        return []

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.session.query(
        Trade.symbol,
        db.func.sum(Trade.shares).label('total_shares')
    ).filter(Trade.user_id == session["user_id"])\
     .group_by(Trade.symbol).having(db.func.sum(Trade.shares) > 0)\
     .order_by(Trade.symbol.asc()).all()

    user = User.query.get(session["user_id"])
    cash = user.cash
    total_value = cash

    stocks_info = []  

    for stock in stocks:
        quote = lookup(stock.symbol)
        if quote: 
            stock_info = {
                "symbol": stock.symbol,
                "name": quote["name"],
                "price": quote["price"],
                "total_shares": stock.total_shares,
                "value": quote["price"] * stock.total_shares
            }
            stocks_info.append(stock_info)
            total_value += stock_info["value"]

    return render_template("index.html", stocks_info=stocks_info, cash=usd(cash), total_value=usd(total_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if not symbol:
            return apology("MISSING SYMBOL", 400)
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Must provide shares greater than 0", 400)

        quote = lookup(symbol)

        if quote is None:
            return apology("Symbol not found", 400)

        price = quote["price"]
        total_cost = int(shares) * price
        user = User.query.get(session["user_id"])
        cash = user.cash

        if cash < total_cost:
            return apology("Cannot afford to purchase", 400)

        user.cash -= total_cost
        db.session.commit()

        new_trade = Trade(user_id=session["user_id"], symbol=symbol, shares=int(shares), price=price)
        db.session.add(new_trade)
        db.session.commit()

        flash(f"Bought { shares } shares of { symbol } for { usd(total_cost) }!")
        return redirect("/")

    else:
        query = request.args.get('query')
        if query:
            symbols = get_stock_suggestions(query)
            return jsonify({'symbols': symbols})
        
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = Trade.query.filter_by(user_id=session["user_id"])\
                              .order_by(Trade.timestamp.desc()).all()

    return render_template("history.html", transactions=transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        user = User.query.filter_by(username=request.form.get("username")).first()

        if user is None or not check_password_hash(user.hash, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = user.id
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()

        if not symbol:
            return apology("must provide a stock symbol", 400)

        quote = lookup(symbol.upper())
        if not quote:
            return apology("stock symbol not found", 400)

        return render_template("quote.html", quote=quote)

    else:
        query = request.args.get('query')
        if query:
            symbols = get_stock_suggestions(query)
            return jsonify({'symbols': symbols})
        
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        user = User.query.filter_by(username=request.form.get("username")).first()
        if user:
            return apology("username already exists", 400)

        new_user = User(
            username=request.form.get("username"),
            hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256')
        )

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id

        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("MISSING SYMBOL", 400)
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Must provide shares greater than 0", 400)

        stock = db.session.query(
            db.func.sum(Trade.shares).label('total_shares')
        ).filter(Trade.user_id == session["user_id"], Trade.symbol == symbol).first()

        total_shares = stock.total_shares

        if total_shares is None or total_shares < int(shares):
            return apology("You do not have enough shares to sell", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Unable to fetch stock data. Please try again later.", 400)

        price = quote["price"]
        total_revenue = int(shares) * price

        user = User.query.get(session["user_id"])
        user.cash += total_revenue
        db.session.commit()

        new_trade = Trade(user_id=session["user_id"], symbol=symbol, shares=-int(shares), price=price)
        db.session.add(new_trade)
        db.session.commit()

        flash("Sold!")
        return redirect("/")

    else:
        stocks = db.session.query(
            Trade.symbol,
            db.func.sum(Trade.shares).label('total_shares')
        ).filter(Trade.user_id == session["user_id"])\
         .group_by(Trade.symbol).having(db.func.sum(Trade.shares) > 0).all()

        return render_template("sell.html", stocks=stocks)



if __name__ == "__main__":
    app.run(debug=True) 
