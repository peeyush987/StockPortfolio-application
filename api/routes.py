from flask import Blueprint, jsonify, request
from flask import session

from extensions import db
from helpers import get_finance_response, get_market_data, login_required, lookup
from models import Portfolio, User, ensure_portfolios_populated


api_bp = Blueprint("api", __name__)


@api_bp.route("/chatbot", methods=["POST"])
@login_required
def chatbot():
    """Handle chatbot requests"""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"response": "Please ask me a question about finance!"})

        ensure_portfolios_populated(session["user_id"])
        user = User.query.get(session["user_id"])
        holdings = Portfolio.query.filter_by(user_id=session["user_id"]).order_by(Portfolio.symbol.asc()).all()
        market_data = get_market_data()

        positions = []
        invested_value = 0
        for holding in holdings:
            positions.append(
                {
                    "symbol": holding.symbol,
                    "shares": holding.shares,
                    "cost_basis": holding.total_cost_basis,
                    "value": holding.total_cost_basis,
                }
            )
            invested_value += holding.total_cost_basis

        portfolio_context = {
            "cash": user.cash if user else 0,
            "total_value": (user.cash if user else 0) + invested_value,
            "positions": positions,
        }

        response = get_finance_response(
            message,
            portfolio_context=portfolio_context,
            market_context=market_data,
        )
        return jsonify({"response": response})
    except Exception:
        return jsonify({"response": "Sorry, I encountered an error. Please try again later."})


@api_bp.route("/api/quote/<symbol>")
@login_required
def api_quote(symbol):
    """Get stock quote via API endpoint"""
    try:
        quote = lookup(symbol.upper())
        if quote:
            return jsonify(
                {
                    "symbol": quote["symbol"],
                    "name": quote["name"],
                    "price": quote["price"],
                    "success": True,
                }
            )
        return jsonify({"error": "Symbol not found", "success": False}), 404
    except Exception:
        return jsonify({"error": "Unable to fetch quote", "success": False}), 500


@api_bp.route("/api/market-data")
@login_required
def market_data():
    """Get market data for dashboard"""
    try:
        data = get_market_data()
        return jsonify(data)
    except Exception:
        return jsonify({"error": "Unable to fetch market data"})
