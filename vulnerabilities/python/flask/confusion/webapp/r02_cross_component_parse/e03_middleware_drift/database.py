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
            {
                "from": "mr.krabs",
                "message": "Squidward, the new safe combination is 4-2-0-6-9. Don't write it down anywhere!",
            },
        ],
    },
}


def authenticate(user, password):
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_user(request):
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"mailbox": user, "messages": messages}
