from flask import g, request

# Simulated database/state
db = {
    "users": {
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


def authenticate(user, password):
    """Authenticate the user, based solely on the request query string."""
    if user is None or password is None:
        return False
    
    if password != db["users"].get(user, {}).get("password", None):
        return False
    return True


def is_group_member(user, group):
    """Check if the user is an admin of the given group."""
    group_members = db["groups"].get(group, {}).get("users", [])
    for member in group_members:
        if member["user"] == user:
            return True
    return False

def get_user_messages(user):
    return db["users"].get(user, {}).get("messages", [])

def get_group_messages(group):
    return db["groups"].get(group, {}).get("messages", [])
