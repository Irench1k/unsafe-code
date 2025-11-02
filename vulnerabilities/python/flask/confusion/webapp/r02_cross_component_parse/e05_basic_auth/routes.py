"""Basic Authentication example with query parameter bug."""

from flask import Blueprint, g, jsonify, request

from .auth import cross_account_access_control, require_auth
from .db import get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("cross_component_basic_auth", __name__, url_prefix="/example5")


# @unsafe[block]
# id: 5
# title: Basic Authentication with Query Parameter Bug
# notes: |
#   Modernized authentication using HTTP Basic Auth via Authorization header. Most
#   endpoints correctly use g.user, but profile/view reads username from query string
#   instead, enabling authenticated users to view any profile by specifying a different
#   username in the URL.
# @/unsafe


@bp.get("/messages/list")
@require_auth
def list_messages():
    """Lists messages using g.user from decorator."""
    try:
        messages = get_messages(g.user)
        return jsonify({"user": g.user, "messages": messages}), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve messages"}), 500


@bp.patch("/profile/<username>/edit")
@require_auth
def edit_profile(username):
    """Edits authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        update_profile(display_name=display_name, bio=bio)
        return jsonify({"status": "updated", "user": g.user}), 200
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500


@bp.get("/profile/<username>/view")
@require_auth
def view_profile(username):
    """
    View profile data. We only check authentication by design, the users ARE allowed to view other users' profiles.
    """
    try:
        cross_account_access_control(username)

        profile = get_profile()
        if not profile:
            return jsonify({"error": "User not found"}), 404

        return jsonify(sanitize_profile(profile)), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve profile"}), 500


# @/unsafe[block]
