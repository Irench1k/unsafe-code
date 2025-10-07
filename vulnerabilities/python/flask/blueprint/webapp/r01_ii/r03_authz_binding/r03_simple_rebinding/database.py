# Simulated database - SpongeBob universe themed
# Plankton is the evil hacker trying to steal the Krabby Patty secret formula
db = {
    "users": {
        "spongebob@krusty-krab.sea": {
            "password": "bikinibottom",
            "messages": [],
        },
        "squidward@krusty-krab.sea": {
            "password": "clarinet-master",
            "messages": [],
        },
        "mr.krabs@krusty-krab.sea": {
            "password": "$$$money$$$",
            "messages": [],
        },
        "plankton@chum-bucket.sea": {
            "password": "burgers-are-yummy",
            "messages": [
                {
                    "from": "hackerschool@deepweb.sea",
                    "message": "Congratulations Plankton! You've completed 'Social Engineering 201'."
                }
            ],
        },
    },
    "groups": {
        "staff@krusty-krab.sea": {
            "users": [
                { "role": "member", "user": "spongebob@krusty-krab.sea" },
                { "role": "member", "user": "squidward@krusty-krab.sea" },
                { "role": "admin", "user": "mr.krabs@krusty-krab.sea" }
            ],
            "messages": [
                {
                    "from": "mr.krabs@krusty-krab.sea",
                    "message": "Attention employees! Time to vote for Employee of the Month. Reply to this thread with your vote."
                }
            ]
        },
        "managers@krusty-krab.sea": {
            "users": [
                { "role": "member", "user": "squidward@krusty-krab.sea" },
                { "role": "admin", "user": "mr.krabs@krusty-krab.sea" }
            ],
            "messages": []
        },
        "staff@chum-bucket.sea": {
            "users": [
                { "role": "admin", "user": "plankton@chum-bucket.sea" }
            ],
            "messages": []
        }
    }
}


def authenticate(user, password):
    """Authenticate the user with username and password."""
    if user is None or password is None:
        return False

    if password != db["users"].get(user, {}).get("password", None):
        return False
    return True


def is_group_member(user, group):
    """Check if the user is a member of the given group."""
    group_data = db["groups"].get(group, {})
    if not group_data:
        return False

    group_members = group_data.get("users", [])
    for member in group_members:
        if member["user"] == user:
            return True
    return False


def get_group_messages(group):
    """Get messages for a group."""
    return db["groups"].get(group, {}).get("messages", [])


def post_message_to_group(from_user, group, message):
    """
    Post a message to a group with specified sender attribution.

    Args:
        from_user: Email of the message sender (for attribution)
        group: Group identifier
        message: Message content

    Returns:
        bool: True if successful, False if group doesn't exist
    """
    group_data = db["groups"].get(group, {})
    if not group_data:
        return False

    group_data["messages"].append({
        "from": from_user,
        "message": message
    })
    return True
