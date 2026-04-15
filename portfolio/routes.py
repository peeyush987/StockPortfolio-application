from flask import Blueprint, flash, jsonify, redirect, render_template, request, session

from extensions import db
from helpers import apology, get_market_data, get_stock_suggestions, login_required, lookup, usd
from models import Portfolio, Trade, User, ensure_portfolios_populated


portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    ensure_portfolios_populated(session["user_id"])
    stocks = Portfolio.query.filter_by(user_id=session["user_id"]).order_by(Portfolio.symbol.asc()).all()

    user = User.query.get(session["user_id"])
    cash = user.cash
    total_value = cash
    total_cost_basis = 0
    stocks_info = []

    for stock in stocks:
        quote = lookup(stock.symbol)
        if not quote:
            continue

        current_price = quote["price"]
        total_shares = stock.shares
        current_value = current_price * total_shares

        cost_basis = stock.total_cost_basis
        total_cost_basis += cost_basis

        gain_loss = current_value - cost_basis
        gain_loss_percent = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

        stocks_info.append(
            {
                "symbol": stock.symbol,
                "name": quote["name"],
                "price": current_price,
                "total_shares": total_shares,
                "value": current_value,
                "cost_basis": cost_basis,
                "gain_loss": gain_loss,
                "gain_loss_percent": gain_loss_percent,
                "avg_purchase_price": stock.avg_purchase_price,
            }
        )
        total_value += current_value

    if total_cost_basis > 0:
        total_gain_loss = (total_value - cash) - total_cost_basis
        total_return_percent = total_gain_loss / total_cost_basis * 100
    else:
        total_gain_loss = 0
        total_return_percent = 0

    market_data = get_market_data()

    return render_template(
        "index.html",
        stocks_info=stocks_info,
        cash=usd(cash),
        total_value=usd(total_value),
        total_gain_loss=total_gain_loss,
        total_return_percent=total_return_percent,
        market_data=market_data,
    )


@portfolio_bp.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if not symbol:
            return apology("MISSING SYMBOL", 400)
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Must provide shares greater than 0", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Symbol not found", 400)

        price = quote["price"]
        total_cost = int(shares) * price
        user = User.query.get(session["user_id"])
        portfolio = Portfolio.query.filter_by(user_id=session["user_id"], symbol=symbol).first()

        if user.cash < total_cost:
            return apology("Cannot afford to purchase", 400)

        user.cash -= total_cost
        if portfolio is None:
            portfolio = Portfolio(user_id=session["user_id"], symbol=symbol, shares=0, total_cost_basis=0.0)
            db.session.add(portfolio)

        portfolio.shares += int(shares)
        portfolio.total_cost_basis += total_cost

        new_trade = Trade(user_id=session["user_id"], symbol=symbol, shares=int(shares), price=price)
        db.session.add(new_trade)
        db.session.commit()

        flash(f"Successfully bought {shares} shares of {symbol} for {usd(total_cost)}!")
        return redirect("/")

    query = request.args.get("query")
    if query:
        symbols = get_stock_suggestions(query)
        return jsonify({"symbols": symbols})

    return render_template("buy.html")


@portfolio_bp.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = Trade.query.filter_by(user_id=session["user_id"]).order_by(Trade.timestamp.desc()).all()
    return render_template("history.html", transactions=transactions)


@portfolio_bp.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()

        if not symbol:
            return apology("must provide a stock symbol", 400)

        quote_data = lookup(symbol)
        if not quote_data:
            return apology("stock symbol not found", 400)

        return render_template("quote.html", quote=quote_data)

    query = request.args.get("query")
    if query:
        symbols = get_stock_suggestions(query)
        return jsonify({"symbols": symbols})

    return render_template("quote.html")


@portfolio_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("MISSING SYMBOL", 400)
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Must provide shares greater than 0", 400)

        ensure_portfolios_populated(session["user_id"])
        stock = Portfolio.query.filter_by(user_id=session["user_id"], symbol=symbol).first()

        total_shares = stock.shares if stock else None
        if total_shares is None or total_shares < int(shares):
            return apology("You do not have enough shares to sell", 400)

        quote_data = lookup(symbol)
        if quote_data is None:
            return apology("Unable to fetch stock data. Please try again later.", 400)

        price = quote_data["price"]
        total_revenue = int(shares) * price

        user = User.query.get(session["user_id"])
        user.cash += total_revenue

        shares_to_sell = int(shares)
        avg_cost = stock.avg_purchase_price
        stock.shares -= shares_to_sell
        stock.total_cost_basis -= avg_cost * shares_to_sell
        if stock.shares <= 0:
            db.session.delete(stock)
        else:
            stock.total_cost_basis = max(stock.total_cost_basis, 0.0)

        new_trade = Trade(user_id=session["user_id"], symbol=symbol, shares=-shares_to_sell, price=price)
        db.session.add(new_trade)
        db.session.commit()

        flash(f"Successfully sold {shares} shares of {symbol} for {usd(total_revenue)}!")
        return redirect("/")

    ensure_portfolios_populated(session["user_id"])
    stocks = Portfolio.query.filter_by(user_id=session["user_id"]).order_by(Portfolio.symbol.asc()).all()

    return render_template("sell.html", stocks=stocks)
