import os
import logging

from dotenv import load_dotenv
from flask import Flask

from api.routes import api_bp
from auth.routes import auth_bp
from extensions import db, migrate, moment, sess
from helpers import usd
from models import Portfolio, Trade, User
from portfolio.routes import portfolio_bp


load_dotenv()


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Set it in your deployment environment or local .env file."
        )
    return value


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

logger.info("Application startup initiated")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = require_env("SECRET_KEY")
    logger.info("Flask app created")

    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"

    if os.environ.get("DATABASE_URL"):
        uri = os.environ.get("DATABASE_URL")
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
    else:
        uri = "sqlite:///finance.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    moment.init_app(app)
    sess.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    app.jinja_env.filters["usd"] = usd

    @app.after_request
    def after_request(response):
        """Ensure responses aren't cached"""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(api_bp)

    logger.info("Application configured and blueprints registered")
    return app


app = create_app()

__all__ = ["app", "db", "migrate", "Portfolio", "Trade", "User", "create_app"]
