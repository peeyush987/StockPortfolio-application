from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from helpers import apology
from models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        if not request.form.get("password"):
            return apology("must provide password", 403)

        user = User.query.filter_by(username=request.form.get("username")).first()

        if user is None or not check_password_hash(user.hash, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        if not request.form.get("password"):
            return apology("must provide password", 400)
        if not request.form.get("confirmation"):
            return apology("must confirm password", 400)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        user = User.query.filter_by(username=request.form.get("username")).first()
        if user:
            return apology("username already exists", 400)

        new_user = User(
            username=request.form.get("username"),
            hash=generate_password_hash(request.form.get("password"), method="pbkdf2:sha256"),
        )

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        flash("Registration successful! Welcome to FinanceHub!")
        return redirect("/")

    return render_template("register.html")
