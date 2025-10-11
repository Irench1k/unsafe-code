# Simulated database - authentication examples
db = {
    "passwords": {"spongebob": "bikinibottom", "squidward": "clarinet123"},
    "messages": {
        "spongebob": [
            {"from": "patrick", "message": "Hey SpongeBob, wanna go jellyfishing?"},
        ],
        "squidward": [
            {
                "from": "plankton",
                "message": "Squidward, I'll pay you handsomely to 'accidentally' share the secret formula. You deserve better than that dead-end cashier job!",
            },
        ],
    },
}


def authenticate(user, password):
    """Authenticate the user based on username and password."""
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_messages(user):
    """Retrieve messages for a user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"mailbox": user, "messages": messages}
