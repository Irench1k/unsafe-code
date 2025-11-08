"""Baseline example with verbose inline authentication."""

from flask import Blueprint, jsonify, request

from .auth import cross_account_access_control
from .db import authenticate, create_message, get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("baseline", __name__, url_prefix="/example1")


# @unsafe[block]
# id: 1
# title: Secure Baseline with Verbose Inline Authentication
# notes: |
#   Demonstrates secure but repetitive authentication. Every endpoint validates
#   credentials inline with 4 lines of identical logic before executing business
#   operations. This verbose pattern creates pressure to refactor into middleware
#   or decorators, as shown in subsequent examples.
#
#   Check out the full routes.py file to see all four endpoints defined there and how
#   much code is duplicated here. Pay attention to lack of standardization – even the
#   user identity gets extracted in multiple ways:
#
#   - request.form.get("user")
#   - request.form.get("sender")
#   - request.view_args("username")
#
#   There are no vulnerabilities here, and the code is relatively straightforward to
#   review, but the large amount of repetition and inconsistencies make it hard to
#   maintain, which typically gets addressed by refactoring into middleware or decorators.
# @/unsafe
@bp.post("/messages/list")
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Inline authentication (repeated in all endpoints)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            # Note that although Flask will automatically convert *some*
            # data types to JSON like dictionaries, there are some other
            # data types that don't get converted automatically, so it's
            # best to always use jsonify() to ensure the response is a
            # valid JSON with proper headers set.
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic
        messages = get_messages(user)
        return jsonify({"user": user, "messages": messages}), 200
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
        sender = request.form.get("sender")
        password = request.form.get("password")

        if not authenticate(sender, password):
            return jsonify({"error": "Invalid credentials"}), 401

        recipient = request.form.get("recipient")
        text = request.form.get("text", "")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(sender=sender, recipient=recipient, text=text)
        return (
            jsonify({"message_id": msg_id, "sender": sender, "recipient": recipient}),
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
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

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


@bp.patch("/profile/<username>/edit")
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        password = request.form.get("password")

        if not authenticate(username, password):
            return jsonify({"error": "Invalid credentials"}), 401

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
