import logging
import re

from flask import Blueprint, g, request, session

from ..auth.authenticators import CustomerAuthenticator
from ..database.repository import find_user_by_email
from ..database.services import apply_signup_bonus, create_user
from ..utils import (
    created_response,
    error_response,
    require_condition,
    send_user_verification_email,
    success_response,
    verify_and_decode_token,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@bp.before_request
def protect_user_verification_flow():
    """
    Verify user verification token during registration.
    """
    token = request.json.get("token") if request.is_json else None

    g.email_confirmed = False
    g.email = None

    if not token:
        # The rest of the checks only apply to requests with a token
        return

    claims = verify_and_decode_token(token, "user_verification")
    require_condition(claims, "Invalid or expired token")

    user = find_user_by_email(claims["email"])
    require_condition(not user, "User already registered")

    g.email = claims["email"]
    g.email_confirmed = True



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
        send_user_verification_email(unvalidated_email)

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

    return success_response({"message": "Login successful", "email": g.email})


@bp.post("/logout")
def logout_user():
    """Logs out the user."""
    authenticator = CustomerAuthenticator()
    require_condition(authenticator.authenticate(), "You are not logged in!")

    session.pop("email", None)
    return success_response({"message": "Logout successful"})
