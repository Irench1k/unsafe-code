import os
from bottle import route, run, template, get, post, request, redirect, abort


@route("/")
def root():
    return "This is a root page, please go to /submit to see user pages :)"


@route("/user")
@route("/user/")
def get_user():
    return "Try to write a name, like this: `/user/my-name"


# Example: /user/irina
@route("/user/<username>")
@route("/user/<username>/")
def get_username(username="String"):
    return template("Hello, {{name}}", name=username)


# Parameters with types
# Example: /user/irina/123
@route("/user/<username>/<user_id:int>")
@route("/user/<username>/<user_id:int>/")
def get_userid(username="String", user_id=int):
    return template("Hello, {{name}}! Your ID is: {{id}}", name=username, id=user_id)


# Example 1: /user/irina/action/login -> User: irina, Action: login
# Example 2: /user/irina/action/view/profile -> User: irina, Action: view/profile
# Example 3: /user/bob/action/edit/post/123 -> User: bob, Action: edit/post/123
@route("/user/<username>/action/<action_path:path>")
@route("/user/<username>/action/<action_path:path>/")
def user_action(username, action_path):
    return template(
        "User: {{name}}, Action: {{action}}", name=username, action=action_path
    )


# Predefined values using REGEX FILTER
# Example 1: /models/alexnet -> works
# Example 2: /models/whatever -> code 404
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
# Example 1: /special-user/irina_123 -> works
# Example 2: /special-user/irina^123 -> code 404
@route("/special-user/<username:re:[a-zA-Z0-9_]+>")
@route("/special-user/<username:re:[a-zA-Z0-9_]+>/")
def show_name(username):
    return f"<h1>Showing profile for: {username}</h1>"


# Optional Query Parameter
# Example of how you can differentiate between items/<item_id> and items/<status>:
# Example 1: /items/123 will return "Your item ID is: 123"
# Example 2: /items/active will return "Showing items with status: active"
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


# Query Parameters
# Example: /products?id=123&name=coca-cola
@route("/products")
def find_product():
    id_str = request.query.get("id")
    name = request.query.get("name")

    if not name:
        abort(400, "Required query parameter 'name' is missing.")

    if not id_str:
        abort(400, "Required query parameter 'item_id' is missing.")

    try:
        id = int(id_str)
    except ValueError:
        abort(400, "Invalid value for 'item_id'. It must be an integer.")

    return template(
        "Product ID is: {{id}}, and product Name is: {{name}}", id=id, name=name
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
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable Bottle's built-in auto-reloader in development when requested
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    run(host=host, port=port, debug=debug, reloader=debug)
