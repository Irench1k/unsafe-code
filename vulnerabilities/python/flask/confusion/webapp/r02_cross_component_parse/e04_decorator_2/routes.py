"""Baseline example with verbose inline authentication."""

from flask import Blueprint, g, jsonify, request

from .auth import cross_account_access_control, require_auth
from .db import create_message, get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("decorator_2", __name__, url_prefix="/example4")


# @unsafe[block]
# id: 4
# title: Decorator with Incomplete Fix
# notes: |
#   In this example we attempted to fix the vulnerability by replacing the 
#   `request.values` method in the decorator with the `request.form` method.
#
#   When we test the previous vulnerability, we see that now it is fixed, which is good news.
#
#   However, the fix inadvertently introduced a new vulnerability because the existing code in 
#   the `/message/list` endpoint accesses the `user` from the combined dictionary `request.values`. 
#   The attacker can now view victim's messages by sending attacker's credentials via
#   the body form (used in `@require_auth`), and the victim's username via the query string 
#   (used to access the messages).
# @/unsafe
@bp.post("/messages/list")
@require_auth
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Business logic
        messages = get_messages(request.values.get("user"))
        return jsonify({"user": g.user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500


# @/unsafe[block]


@bp.post("/messages/new")
@require_auth
def create_new_message():
    """Creates a new message from the authenticated user."""
    try:
        recipient = request.form.get("recipient")
        text = request.form.get("text", "")
        user = request.form.get("user")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(user, recipient, text)
        return (
            jsonify({"message_id": msg_id, "sender": user, "recipient": recipient}),
            201,
        )
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to create message"}), 500


@bp.post("/profile/<username>/view")
@require_auth
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


@bp.patch("/profile/<username>/edit")
@require_auth
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(g.user, display_name, bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": g.user}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500
