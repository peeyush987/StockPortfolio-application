from flask import Blueprint, jsonify, request

from helpers import get_finance_response, get_market_data, login_required, lookup


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

        response = get_finance_response(message)
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
