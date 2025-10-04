# Simulated database/state
db = {
    "users": [
        {
            "name": "spongebob@krusty-krab.sea",
            "password": "bikinibottom",
            "messages": [],
        },
        {
            "name": "squidward@krusty-krab.sea",
            "password": "the-best-manager",
            "messages": [
                {
                    "from": "plankton@chum-bucket.sea",
                    "message": "Hey Squidward, I'll pay you $1000 if you just happen to 'accidentally' leave the formula where I can see it. You deserve better than working for that cheap crab!",
                }
            ],
        },
        {
            "name": "mr.krabs@krusty-krab.sea",
            "password": "$$$money$$$",
            "messages": [],
        },
        {
            "name": "plankton@chum-bucket.sea",
            "password": "burgers-are-yummy",
            "messages": [
                {
                    "from": "hackerschool@deepweb.sea",
                    "message": "Congratulations Plankton! You've completed 'Email Hacking 101'.",
                }
            ],
        },
    ],
    "groups": [
        {
            "name": "staff@krusty-krab.sea",
            "users": [
                {"role": "member", "user": "spongebob@krusty-krab.sea"},
                {"role": "member", "user": "squidward@krusty-krab.sea"},
                {"role": "admin", "user": "mr.krabs@krusty-krab.sea"},
            ],
            "messages": [
                {
                    "from": "mr.krabs@krusty-krab.sea",
                    "message": "I am updating the safe password to '123456'. Do not tell anyone!",
                }
            ],
        },
        {
            "name": "managers@krusty-krab.sea",
            "users": [
                {"role": "member", "user": "squidward@krusty-krab.sea"},
                {"role": "admin", "user": "mr.krabs@krusty-krab.sea"},
            ],
            "messages": [
                {
                    "from": "mr.krabs@krusty-krab.sea",
                    "message": "Meeting with the board of directors tomorrow at 10 AM. Be on time!",
                }
            ],
        },
        {
            "name": "staff@chum-bucket.sea",
            "users": [{"role": "admin", "user": "plankton@chum-bucket.sea"}],
            "messages": [
                {
                    "from": "plankton@chum-bucket.sea",
                    "message": "To my future self, don't forget to steal the formula!",
                }
            ],
        },
    ]
}

# helpers
def get_user(username):
    for user in db["users"]:
        if user["name"] == username:
            return user
    return None

# @unsafe[block]
# id: 19
# part: 2
# @/unsafe
def get_group(groupname):
    matching_group = None
    for group in db["groups"]:
        # Compare group names case insensitively
        if group["name"].lower() == groupname.lower():
            matching_group = group
    return matching_group
# @/unsafe[block]


def authenticate(username, password):
    """Authenticate the user."""
    if username is None or password is None:
        return False
    
    user = get_user(username)
    if password != user["password"]:
        return False
    return True


def is_group_member(username, groupname):
    """Check if the user is an admin of the given group."""
    group = get_group(groupname)
    
    group_members = group["users"]
    for member in group_members:
        if member["user"] == username:
            return True
    return False


def get_group_messages(groupname):
    group = get_group(groupname)
    return group["messages"]


def add_group(groupname, members, messages):
    if type(groupname) != str:
        raise Exception("Group name should be string!")
    
    # We reconstruct the users and messages from scratch here, in order to
    # avoid passing on unvalidated garbage, as at this point both
    # `members` and `messages` are coming from the request body.
    users_safe = []
    for member in members:
        role = member.get("role", None)
        if role is None or role not in ["member", "admin"]:
            raise Exception("Role should be member or admin!")
        
        username = member.get("user", None)
        user = get_user(username)
        if user is None:
            raise Exception("User does not exist!")
        
        users_safe.append({"role": role, "user": username})
        
    messages_safe = []    
    for message in messages:
        from_ = message.get("from", None)
        if type(from_) != str:
            raise Exception("From field should be of the type of string!")
        
        text = message.get("message", None)
        if type(text) != str:
            raise Exception('Message should be the type of string!')
        
        messages_safe.append({"from": from_, "message": text})
        
    group_to_add = {"name": groupname, "users": users_safe, "messages": messages_safe}
    
    for group in db["groups"]:
        if groupname == group["name"]:
            raise Exception("Group names should be unique!")
        
    db["groups"].append(group_to_add)
    