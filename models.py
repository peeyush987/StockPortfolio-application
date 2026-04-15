from datetime import datetime

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    hash = db.Column(db.String(120), nullable=False)
    cash = db.Column(db.Float, default=10000)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    trades = db.relationship("Trade", backref="user", lazy=True)
    portfolios = db.relationship("Portfolio", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


class Trade(db.Model):
    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Trade {self.symbol} {self.shares} shares at {self.price}>"


class Portfolio(db.Model):
    __tablename__ = "portfolios"
    __table_args__ = (db.UniqueConstraint("user_id", "symbol", name="uq_portfolios_user_symbol"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False, default=0)
    total_cost_basis = db.Column(db.Float, nullable=False, default=0.0)

    @property
    def avg_purchase_price(self):
        return self.total_cost_basis / self.shares if self.shares > 0 else 0.0

    def __repr__(self):
        return f"<Portfolio {self.symbol} {self.shares} shares>"


def rebuild_portfolios(user_id=None):
    query = Trade.query.order_by(Trade.user_id.asc(), Trade.symbol.asc(), Trade.timestamp.asc(), Trade.id.asc())
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    portfolios = {}

    for trade in query.all():
        key = (trade.user_id, trade.symbol)
        holding = portfolios.setdefault(
            key,
            {
                "shares": 0,
                "total_cost_basis": 0.0,
            },
        )

        if trade.shares > 0:
            holding["shares"] += trade.shares
            holding["total_cost_basis"] += trade.shares * trade.price
            continue

        shares_to_sell = abs(trade.shares)
        if holding["shares"] <= 0:
            continue

        avg_cost = holding["total_cost_basis"] / holding["shares"] if holding["shares"] > 0 else 0.0
        holding["shares"] -= shares_to_sell
        holding["total_cost_basis"] -= avg_cost * shares_to_sell

        if holding["shares"] <= 0:
            holding["shares"] = 0
            holding["total_cost_basis"] = 0.0

    portfolio_query = Portfolio.query
    if user_id is not None:
        portfolio_query = portfolio_query.filter_by(user_id=user_id)
    portfolio_query.delete(synchronize_session=False)

    for (portfolio_user_id, symbol), holding in portfolios.items():
        if holding["shares"] <= 0:
            continue
        db.session.add(
            Portfolio(
                user_id=portfolio_user_id,
                symbol=symbol,
                shares=holding["shares"],
                total_cost_basis=holding["total_cost_basis"],
            )
        )


def ensure_portfolios_populated(user_id):
    has_portfolios = Portfolio.query.filter_by(user_id=user_id).first() is not None
    has_trades = Trade.query.filter_by(user_id=user_id).first() is not None

    if not has_portfolios and has_trades:
        rebuild_portfolios(user_id=user_id)
        db.session.commit()
