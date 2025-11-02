"""Baseline example with verbose inline authentication."""

from flask import Blueprint, g, jsonify, request

from .auth import cross_account_access_control
from .db import authenticate, create_message, get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("middleware", __name__, url_prefix="/example2")


# @unsafe[block]
# id: 2
# part: 3
# @/unsafe
@bp.before_request
def authenticate_user():
    """
    Blueprint-level middleware that runs before every request.

    Validates credentials from form body and stores authenticated user in Flask's g
    object (request-scoped global storage).
    """
    user = request.form.get("user")
    password = request.form.get("password")

    if not authenticate(user, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Store authenticated user for handlers to use
    g.user = user


# @/unsafe[block]


# @unsafe[block]
# id: 2
# title: Middleware with Source Precedence Bug
# notes: |
#   This example introduces Flask blueprint middleware to reduce authentication
#   boilerplate. The @bp.before_request decorator runs before every endpoint,
#   validates credentials, and stores the authenticated user in g.user.
#
#   Note that due to lack of standardization, in the e01_baseline we accessed user
#   identity in multiple ways. As we replace the inline authentication with middleware,
#   we standardize on a single way to access the user identity.
#
#   While refactoring, developers need to remove previous authentication logic and
#   replace the user identity with g.user. However, the `/profile/<username>/view`
#   endpoint accepted two usernames - one for authentication (`request.form`) and
#   one for viewing the profile (`request.view_args`). This endpoint was refactored
#   correctly - by just removing the authentication and keeping the `<username>` for
#   profile access. But then the same method was used to refactor the sibling endpoint
#   `/profile/<username>/edit` - introducing a source precedence vulnerability.
#
#   An attacker authenticates with their credentials in the form body, then specifies a
#   victim's username in the path to edit their profile.
# @/unsafe
@bp.post("/messages/list")
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Business logic
        messages = get_messages(g.user)
        return jsonify({"user": g.user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500


# @/unsafe[block]


@bp.post("/messages/new")
def create_new_message():
    """Creates a new message from the authenticated user."""
    try:
        recipient = request.form.get("recipient")
        text = request.form.get("text", "")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(sender=g.user, recipient=recipient, text=text)
        return (
            jsonify({"message_id": msg_id, "sender": g.user, "recipient": recipient}),
            201,
        )
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to create message"}), 500


@bp.post("/profile/<username>/view")
def view_profile(username):
    """Views a user profile. We allow any authenticated user to view any other user's profile."""
    try:
        cross_account_access_control(username)

        profile = get_profile(username)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        return jsonify(sanitize_profile(profile)), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to retrieve profile"}), 500


# @unsafe[block]
# id: 2
# part: 2
# @/unsafe
@bp.patch("/profile/<username>/edit")
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(username, display_name, bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": username}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500


# @/unsafe[block]
