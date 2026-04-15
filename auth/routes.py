import os
import re
import secrets

import requests
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User


auth_bp = Blueprint("auth", __name__)

PASSWORD_REQUIREMENTS = (
    "Use at least 8 characters and include uppercase, lowercase, a number, "
    "and a special character."
)


def validate_password_strength(password):
    if len(password) < 8:
        return PASSWORD_REQUIREMENTS
    if not re.search(r"[A-Z]", password):
        return PASSWORD_REQUIREMENTS
    if not re.search(r"[a-z]", password):
        return PASSWORD_REQUIREMENTS
    if not re.search(r"\d", password):
        return PASSWORD_REQUIREMENTS
    if not re.search(r"[^A-Za-z0-9]", password):
        return PASSWORD_REQUIREMENTS
    return None


def google_oauth_enabled():
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


def build_register_context(error=None):
    return {
        "error": error,
        "google_oauth_enabled": google_oauth_enabled(),
        "password_requirements": PASSWORD_REQUIREMENTS,
        "form_data": {
            "username": request.form.get("username", "").strip(),
        },
    }


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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            return render_template("register.html", **build_register_context("Please enter a username."))
        if not password:
            return render_template("register.html", **build_register_context("Please enter a password."))
        if not confirmation:
            return render_template("register.html", **build_register_context("Please confirm your password."))
        if password != confirmation:
            return render_template("register.html", **build_register_context("Passwords do not match."))

        password_error = validate_password_strength(password)
        if password_error:
            return render_template("register.html", **build_register_context(password_error))

        user = User.query.filter_by(username=username).first()
        if user:
            return render_template("register.html", **build_register_context("That username is already taken."))

        new_user = User(
            username=username,
            hash=generate_password_hash(password, method="pbkdf2:sha256"),
        )

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        flash("Registration successful! Welcome to FinanceHub!")
        return redirect("/")

    return render_template("register.html", **build_register_context())


@auth_bp.route("/register/google")
def google_register():
    if not google_oauth_enabled():
        flash("Google sign-up is not configured yet.")
        return redirect(url_for("auth.register"))

    state = secrets.token_urlsafe(24)
    session["google_oauth_state"] = state

    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": url_for("auth.google_callback", _external=True),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    query = "&".join(f"{key}={requests.utils.quote(str(value), safe='')}" for key, value in params.items())
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@auth_bp.route("/auth/google/callback")
def google_callback():
    expected_state = session.pop("google_oauth_state", None)
    incoming_state = request.args.get("state")

    if not expected_state or expected_state != incoming_state:
        flash("Google sign-up session expired. Please try again.")
        return redirect(url_for("auth.register"))

    code = request.args.get("code")
    if not code:
        flash("Google did not return an authorization code.")
        return redirect(url_for("auth.register"))

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_for("auth.google_callback", _external=True),
        },
        timeout=10,
    )

    if token_response.status_code != 200:
        flash("Google sign-up could not be completed. Please try again.")
        return redirect(url_for("auth.register"))

    access_token = token_response.json().get("access_token")
    if not access_token:
        flash("Google sign-up could not be completed. Please try again.")
        return redirect(url_for("auth.register"))

    profile_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    if profile_response.status_code != 200:
        flash("We couldn't fetch your Google profile. Please try again.")
        return redirect(url_for("auth.register"))

    profile = profile_response.json()
    email = (profile.get("email") or "").strip().lower()
    if not email:
        flash("Your Google account did not provide an email address.")
        return redirect(url_for("auth.register"))

    user = User.query.filter_by(username=email).first()
    if user is None:
        user = User(
            username=email,
            hash=generate_password_hash(secrets.token_urlsafe(32), method="pbkdf2:sha256"),
        )
        db.session.add(user)
        db.session.commit()
        flash("Your Google account is ready. Welcome to FinanceHub!")
    else:
        flash("Signed in with Google.")

    session["user_id"] = user.id
    return redirect(url_for("portfolio.index"))
