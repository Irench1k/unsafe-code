"""Baseline example with verbose inline authentication."""

from flask import Blueprint, g, jsonify, request

from .auth import cross_account_access_control, require_auth
from .db import create_message, get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("basic_auth", __name__, url_prefix="/example5")


@bp.get("/messages/list")
@require_auth
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


@bp.post("/messages/new")
@require_auth
def create_new_message():
    """Creates a new message from the authenticated user."""
    try:
        recipient = request.form.get("recipient")
        text = request.form.get("text", "")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(g.user, recipient, text)
        return (
            jsonify({"message_id": msg_id, "sender": g.user, "recipient": recipient}),
            201,
        )
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to create message"}), 500


@bp.get("/profile/<username>/view")
@require_auth
def view_profile(username):
    """Views a user profile. We allow any authenticated user to view any other user's profile."""
    try:
        cross_account_access_control(username)

        profile = get_profile()
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
# id: 5
# title: Basic Authentication with Query Parameter Bug
# notes: |
#   Modernized authentication using HTTP Basic Auth via Authorization header.
#   User identity is now extracted into `g.user` from this header.
#
#   Now the clients won't be sending credentials via the form parameters (HTTP request body)
#   anymore. It means:
#
#   1. We are free to use GET method.
#   2. We remove a footgun by enforcing a single source of truth for identity.
#      Credentials are not mixed with other user input anymore, making it *almost*
#      impossible to introduce source confusion bugs.
#
#   Despite this, the endpoint `/profile/<username>/edit` is vulnerable because the
#   profile it modifies comes from the path argument without verifying that it matches
#   the authenticated user. The vulnerability is hard to spot because it lies deep inside the
#   call stack. `get_profile` is built for convenience: it is used both when we edit the profile
#   and when we view the profile of other users.
# @/unsafe
@bp.patch("/profile/<username>/edit")
@require_auth
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(display_name, bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": g.user}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500


# @/unsafe[block]
