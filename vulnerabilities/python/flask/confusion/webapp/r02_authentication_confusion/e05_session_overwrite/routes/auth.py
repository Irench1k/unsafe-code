import logging
import re

from flask import Blueprint, g, jsonify, request, session

from ..auth.authenticators import CustomerAuthenticator
from ..auth.helpers import verify_user_registration
from ..database.repository import find_user_by_id
from ..database.services import apply_signup_bonus, create_user
from ..errors import CheekyApiError
from ..utils import get_email_from_token, send_verification_email

bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@bp.before_request
def protect_registration_flow():
    """Authenticate user via email verification flow during the registration process."""
    token = request.is_json and request.json.get("token")
    if token and verify_user_registration(token):
        email_from_token = get_email_from_token(token)
        if not find_user_by_id(email_from_token):
            g.email = email_from_token
            g.email_confirmed = True
        else:
            g.email = None
            g.email_confirmed = False
    else:
        # The token is expired, or maybe this isn't even a registration request
        g.email_confirmed = False


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
    email = request.json.get("email")
    password = request.json.get("password")
    if not email or not password:
        raise CheekyApiError("Email and password are required")

    # Some older users stil haven't assigned email address,
    # our user_id -> email transition is over, ask them to contact support
    if not re.match(r"^[^@]+@[^@]+$", email):
        raise CheekyApiError("Please contact support to get your email address verified!")

    # Only check credentials through the new authenticator, to avoid unsafe password handling
    authenticator = CustomerAuthenticator()
    if not authenticator.authenticate():
        raise CheekyApiError("Invalid email or password")

    # Initiate cookie session on successful authentication
    session["email"] = email

    return jsonify({"message": "Login successful", "email": g.email}), 200


@bp.post("/logout")
def logout_user():
    """Logs out the user."""
    authenticator = CustomerAuthenticator()

    if not authenticator.authenticate():
        raise CheekyApiError("You are not logged in!")

    session.pop("email", None)
    return jsonify({"message": "Logout successful"}), 200
