from flask import Blueprint, g, jsonify, request, session

from ..auth.authenticators import CredentialAuthenticator, CustomerAuthenticator
from ..database.repository import find_user_by_id
from ..database.services import apply_signup_bonus, create_user
from ..errors import CheekyApiError
from ..utils import send_verification_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
def register_user():
    """
    Registers a new user with an email verification.

    The handler gets called twice:

      1. Without a token:
        - Input: `email`
        - Output: `email` and `status` (failure if email is already taken)
        - Sends verification email to the user, with a token & URL

      2. With a token:
        - Input: `token`, `password`, `name`
        - Output: `email` and `status` (failure if the token invalid)
    """
    if not request.json.get("token"):
        # First step: the `email` parameter is UNAUTHENTICATED, do not trust it!
        unvalidated_email = request.json.get("email")
        if not unvalidated_email:
            raise CheekyApiError("email is required")

        if find_user_by_id(unvalidated_email):
            raise CheekyApiError("email already taken")

        return send_verification_email(unvalidated_email)
    elif g.email_confirmed:
        # Second step, token gets verified in middleware, setting trusted g.email based on it
        create_user(g.email, request.json.get("password"), request.json.get("name"))
        apply_signup_bonus(g.email)
        return jsonify({"status": "user_created", "email": g.email}), 200

    raise CheekyApiError("Registration failed, don't try again!")


@bp.post("/login")
def login_user():
    """Login endpoint for website - accepts JSON credentials."""
    authenticator = CredentialAuthenticator.from_json()

    if not authenticator.authenticate():
        raise CheekyApiError("Invalid email or password")

    # Set session for future requests
    session["email"] = g.email

    return jsonify({"message": "Login successful"}), 200


@bp.post("/logout")
def logout_user():
    """Logs out the user."""
    authenticator = CustomerAuthenticator()

    if not authenticator.authenticate():
        raise CheekyApiError("You are not logged in!")

    session.pop("email", None)
    return jsonify({"message": "Logout successful"}), 200
