import os
from bottle import route, run, template, get, post, request, redirect, abort

host = os.environ.get("APP_HOST", "localhost")
port = int(os.environ.get("APP_PORT", 8080))


@route("/")
def root():
    return "This is a root page, please go to /submit to see user pages :)"


@route("/user")
@route("/user/")
def get_user():
    return "Try to write a name, like this: `/user/my-name"


# To access urls with `/` at the end, you need to declare your route like this:
@route("/user/<username>")
@route("/user/<username>/")
def get_username(username="String"):
    return template("Hello, {{name}}", name=username)


# Parameters with types
@route("/user/<username>/<user_id:int>")
@route("/user/<username>/<user_id:int>/")
def get_userid(username="String", user_id=int):
    return template("Hello, {{name}}! Your ID is: {{id}}", name=username, id=user_id)


# Use case 1: /user/irina/action/login -> User: irina, Action: login
# Use case 2: /user/irina/action/view/profile -> User: irina, Action: view/profile
# Use case 3: /user/bob/action/edit/post/123 -> User: bob, Action: edit/post/123
@route("/user/<username>/action/<action_path:path>")
@route("/user/<username>/action/<action_path:path>/")
def user_action(username, action_path):
    return template(
        "User: {{name}}, Action: {{action}}", name=username, action=action_path
    )


# Predefined values using REGEX FILTER
@route("/models/<model_name:re:alexnet|resnet|lenet>")
@route("/models/<model_name:re:alexnet|resnet|lenet>/")
def get_model(model_name):
    if model_name == "alexnet":
        return template(
            "Model name: {{name}}, <p>Deep Learning FTW!<p>", name=model_name
        )
    elif model_name == "resnet":
        return template(
            "Model name: {{name}}, <p>LeCNN all the images<p>", name=model_name
        )
    else:
        return template(
            "Model name: {{name}}, <p>Have some residuals<p>", name=model_name
        )


# Enforce a strict format using regular expression
# Below example would allow a username with letters, numbers, and underscores, but nothing else.
@route("/special-user/<username:re:[a-zA-Z0-9_]+>")
@route("/special-user/<username:re:[a-zA-Z0-9_]+>/")
def show_name(username):
    return f"<h1>Showing profile for: {username}</h1>"


# Optional Query Parameter
@route("/items/<item_id:int>")
def read_item_optional(item_id):
    q = request.query.get("q")
    if q:
        return template(
            "Your item ID is: {{item_id}}, and your q is: {{q_value}}",
            item_id=item_id,
            q_value=q,
        )

    return template("Your item ID is: {{item_id}}", item_id=item_id)


# Optional Path Parameters
@route("/items")
@route("/items/")
@route("/items/<status:re:[a-z]+>")
@route("/items/<status:re:[a-z]+>/")
def list_users(status="all"):
    return template("Showing items with status: {{status}}", status=status)


# Required Parameter "needy"
# Example: /items-new/123?needy=456
@route("/items-new/<item_id:int>")
def read_user_item2(item_id):
    needy = request.query.get("needy")
    if not needy:
        abort(400, "Missing required query parameter: 'needy'")

    return template(
        "Here is your item ID: {{item_id}}, and needy is: {{needy}}",
        item_id=item_id,
        needy=needy,
    )


# Submit Page
@get("/submit")  # or @route('/submit')
@get("/submit/")
def submit():
    return """
            <form action='/submit' method='POST'>
                Username: <input name="username" type="text" />
                <input value="Submit" type="submit" />
            </form> 
    """


@post("/submit")  # or @route('/login', method='POST')
@post("/submit/")
def do_submit():
    username = request.forms.username
    if username:
        return redirect(f"/user/{username}")
    else:
        return "Please go back and enter a username."


if __name__ == "__main__":
    run(host=host, port=port, debug=True, reloader=True)
