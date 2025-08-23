from flask import Flask, render_template_string, request, redirect, url_for
from markupsafe import escape
import os

app = Flask(__name__)

# Basic example, minimal page from tutorial
@app.route("/")
def index():
    return "Index Page: go check out /submit and other pages"


# Various ways of defining routes:


# Trailing Slash:
@app.route("/about/")  # Note the trailing slash
def about():
    return f"About Page, Route: {request.path}"


# Basic Routing: /first, /first/second
@app.route("/first")
def first():
    return "First Page"


@app.route("/first/second")
def second():
    return "Second Page"


# Dynamic Routing: Route Variables -> /<username>, /user/<username>
@app.route("/<username>")
def show_username(username):
    return f"User: {escape(username)}, Route: {request.path}"


@app.route("/user/<username>")
def show_user_profile(username):
    return f"User: {escape(username)}, Route: {request.path}"


# Dynamic Routing: Data Types in Routes -> /user/<int:user_id>
@app.route("/user/<int:user_id>")
def show_user_id(user_id):
    return f"User ID: {user_id}, Route: {request.path}"


# Route with both username and user_id
@app.route("/user/<username>/<int:user_id>")
def show_user_details(username, user_id):
    return f"Username: {escape(username)}, User ID: {user_id}, Route: {request.path}"


# HTTP Methods: GET and POST
@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        # Process the form data
        form_data = request.form
        name = form_data.get("name", "No Name")
        return redirect(url_for("show_user_profile", username=name))
    else:
        # Display the form
        return render_template_string(
            """
            <form method="post">
                <label for="name">Name:</label><br>
                <input type="text" id="name" name="name"><br><br>
                <input type="submit" value="Submit">
            </form>
            <p>Route: /submit (GET)</p>
        """
        )


# Handle query parameters: /user?id=123&type=admin
# This code is vulnerable, such a thing can work: /user?id=123&type=<script>alert(1)</script>
@app.route("/user")
def show_user_with_params():
    user_id = request.args.get("id")
    user_type = request.args.get("type")
    return f"User ID: {user_id}, User Type: {user_type}, Route: {request.path}"


# POST /sign-in
#   data in the body: {'username': 'irina', 'password': 'secret'}


@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    password_db = {"irina": "secret", "david": "p=np"}

    user = request.values.get("username", None)
    if user and (password_db[user] == request.values.get("password", None)):
        # User successfully authenticated!
        return f"Here you go, get the sign-in token for: {request.form['username']}\n"
    else:
        # Fail!
        return f"Wrong password or username!\n"


##
## Confusion vulnerabilities
##
## Examples of insecure / confusing API design patterns
## where the request data is accessed in a way that masks
## where the data actually comes from.
##


@app.route("/test/<username>")
def testing(username):
    # return f"Hello, {username}!"

    # return f"Hello, {request.view_args['username']}"
    # return f"Hello, {request.url_rule}"
    # return f"Hello, {request.endpoint}"

    # Investigate this `blueprint` business, looks very suspicious
    # return f"Hello, {request.blueprint}"

    # The parsed URL parameters (the part in the URL after the question mark).
    # return f"Hello, {request.args.get("a", None)}"
    # /?a=b     -> b
    # /?a=b&a=c -> b     (returns the first value, unless ImmutableMultiDict overriten)
    # /?a&a=b   -> ""
    # /

    # By overwriting the parameter storage class, it will merge all values into a single dict
    # resulting in the *last* value being returned.
    # request.parameter_storage_class = dict
    # return f"Hello, {request.args.get("a", None)}"
    # /?a=1&a=2 -> 2

    # return f"Hello, {request.args.getlist("a", None)}"

    # val = [x for x in request.args.items(True)]
    # return f"Hello, {val}"
    # /?a=1&a=2 -> [('a', '1')]

    # val = [x for x in request.args.items(True)]
    # return f"Hello, {val}"
    # /?a=1&a=2 -> [('a', '1'), ('a', '2')]

    # val = [x for x in request.args.lists()]
    # return f"Hello, {val}"
    # /?a=1&a=2 -> Hello, [('a', ['1', '2'])]

    # val = [x for x in request.args.values()]
    # return f"Hello, {val}"
    # /?a=1&a=2 -> ['1']

    # val = [x for x in request.args.listvalues()]
    # return f"Hello, {val}"
    # /?a=1&a=2 -> [['1', '2']]

    # return f"Hello, {request.args.to_dict()}"
    # ?a=1&a=2&b=3&b=4 -> {'a': '1', 'b': '3'}
    # return f"Hello, {request.args.to_dict(False)}"
    # ?a=1&a=2&b=3&b=4 -> {'a': ['1', '2'], 'b': ['3', '4']}

    # return f"Hello, {request.args.get("a", None)}"

    return f"Hello, {request.values.get("a", None)}"


@app.route("/confusion", methods=["GET"])
def confusion():
    # return f"Hello, {request.values.get("a", None)}"
    # takes from the merged dict of form and args, where args have priority

    # return f"Hello, {request.values.get("a", None)}"
    # curl '127.0.0.1:8000/confusion?a=a&a=b' --data 'a=&a=z&a=c'
    # Hello, ['a', 'b', '', 'z', 'c']

    # return f"Hello, {request.form.get("a", None)}"
    # request.form is available even in GET requests!

    return f"want_form_data_parsed: {request.want_form_data_parsed}"
    # returns True even in GET requests (both form and json)


@app.post("/test/<username>")
def test_post(username):
    # curl '127.0.0.1:8000/test/smth' --json '{"a":"b"}'
    val = request.get_json()
    # {"a": "b"}
    return f"Hello, {val.get("a", None)}"
    # {"a": "b"} -> "b"

    # this returns the last value
    # '{"a":"b", "a":"c", "a":"d"}' -> "d"

    # this can also be used as:
    #   val = request.json    # same as request.get_json()


@app.get("/querystring")
def querystring():
    qs = request.query_string.decode("utf-8")
    # return f"Hello, {qs}"
    # /querystring?test&a=b&a=c -> test&a=b&a=c%

    import urllib.parse

    # return f"Hello, {urllib.parse.parse_qs(qs)}"
    # {'a': ['b', 'c']}

    return f"Hello, {urllib.parse.parse_qsl(qs)}"



