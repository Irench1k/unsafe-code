import logging
import re

from flask import Blueprint, g, request, session

from ..auth.authenticators import CustomerAuthenticator
from ..auth.helpers import verify_user_registration
from ..database.repository import find_user_by_email
from ..database.services import apply_signup_bonus, create_user
from ..utils import (
    created_response,
    error_response,
    get_email_from_token,
    require_condition,
    success_response,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@bp.before_request
def protect_registration_flow():
    """Authenticate user via email verification flow during the registration process."""
    token = request.is_json and request.json.get("token")
    if token and verify_user_registration(token):
        email_from_token = get_email_from_token(token)
        if not find_user_by_email(email_from_token):
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

        require_condition(unvalidated_email, "email is required")
        require_condition(not find_user_by_email(unvalidated_email), "email already taken")

        return success_response({"status": "verification_email_sent", "email": unvalidated_email})
    elif g.email_confirmed:
        # Second step, token gets verified in middleware, setting trusted g.email based on it
        create_user(g.email, request.json.get("password"), request.json.get("name"))
        apply_signup_bonus(g.email)
        return created_response({"status": "user_created", "email": g.email})

    return error_response("Registration failed, don't try again!")


@bp.post("/login")
def login_user():
    """Login endpoint for website - accepts JSON credentials."""
    email = request.json.get("email")
    password = request.json.get("password")

    require_condition(email, "email is required")
    require_condition(password, "password is required")

    # Some older users stil haven't assigned email address,
    # our user_id -> email transition is over, ask them to contact support
    require_condition(
        re.match(r"^[^@]+@[^@]+$", email),
        "Please contact support to get your email address verified!",
    )

    # Only check credentials through the new authenticator, to avoid unsafe password handling
    authenticator = CustomerAuthenticator()
    require_condition(authenticator.authenticate(), "Invalid email or password")

    # Initiate cookie session on successful authentication
    session["email"] = g.email

    return success_response({"message": f"Login successful for user {g.email}"})


@bp.post("/logout")
def logout_user():
    """Logs out the user."""
    authenticator = CustomerAuthenticator()
    require_condition(authenticator.authenticate(), "You are not logged in!")

    session.pop("email", None)
    return success_response({"message": "Logout successful"})
