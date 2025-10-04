from flask import request, g

# Simulated database/state - shared across examples
db = {
    "users": {
        "alice": {
            "password": "123456",
            "messages": [
                {"from": "kevin", "message": "Hi Alice, you're fired!"},
            ],
        },
        "bob": {
            "password": "mypassword",
            "messages": [
                {
                    "from": "kevin",
                    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!",
                },
                {
                    "from": "michael",
                    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!",
                },
            ],
        },
        "spongebob@krusty-krab.sea": {
            "password": "bikinibottom",
            "messages": [],
        },
        "squidward@krusty-krab.sea": {
            "password": "the-best-manager",
            "messages": [
                {
                    "from": "plankton@chum-bucket.sea",
                    "message": "Hey Squidward, I'll pay you $1000 if you just happen to 'accidentally' leave the formula where I can see it. You deserve better than working for that cheap crab!"
                }
            ],
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
                    "message": "Congratulations Plankton! You've completed 'Email Hacking 101'."
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
                    "message": "I am updating the safe password to '123456'. Do not tell anyone!"
                }
            ]
        },
        "managers@krusty-krab.sea": {
            "users": [
                { "role": "member", "user": "squidward@krusty-krab.sea" },
                { "role": "admin", "user": "mr.krabs@krusty-krab.sea" }
            ],
            "messages": [
                {
                    "from": "mr.krabs@krusty-krab.sea",
                    "message": "Meeting with the board of directors tomorrow at 10 AM. Be on time!"
                }
            ]
        },
        "staff@chum-bucket.sea": {
            "users": [
                { "role": "admin", "user": "plankton@chum-bucket.sea" }
            ],
            "messages": [
                {
                    "from": "plankton@chum-bucket.sea",
                    "message": "To my future self, don't forget to steal the formula!"
                }
            ]
        }
    }
}


# Example 8 helpers
def get_messages_ex8(user):
    messages = db["users"].get(user, {}).get("messages", None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate_ex8():
    """Authenticate the user, based solely on the request query string."""
    user = request.args.get("user", None)
    password = request.args.get("password", None)

    if password is None or password != db["users"].get(user, {}).get("password", None):
        return False
    return True


def get_user_ex8():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


# Examples 14-15 helpers
def authenticate_ex14(user, password):
    """Authenticate the user."""
    if user is None or password is None:
        return False

    if password != db["users"].get(user, {}).get("password", None):
        return False
    return True


def is_group_member(user, group):
    """Check if the user is a member of the given group."""
    group_members = db["groups"].get(group, {}).get("users", [])
    for member in group_members:
        if member["user"] == user:
            return True
    return False

def get_user_messages(user):
    return db["users"].get(user, {}).get("messages", [])

def get_group_messages(group):
    return db["groups"].get(group, {}).get("messages", [])
