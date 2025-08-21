import cherrypy
import random
import string
import os


class MyApp(object):
    @cherrypy.expose
    def hello(self):
        return "Hello world!"

    @cherrypy.expose
    def index(self):
        return """<html>
          <head></head>
          <body>
            <form method="get" action="generate">
              <input type="text" value="" name="length" />
              <button type="submit">Give it now!</button>
            </form>
          </body>
        </html>"""

    @cherrypy.expose
    def generate(self, length=8):
        return "".join(random.sample(string.hexdigits, int(length)))

    @cherrypy.expose
    def show_user_profile(self, username):
        return f"User: {username}, Route: /user/{username}"

    @cherrypy.expose
    def show_user_id(self, user_id):
        return f"User ID: {user_id}, Route: /user/{user_id}"

    @cherrypy.expose
    def show_user_details(self, username, user_id):
        return f"Username: {username}, User ID: {user_id}, Route: /user/{username}/{user_id}"

    @cherrypy.expose
    def submit(self, name=None):
        if cherrypy.request.method == "POST":
            if name is None:
                name = "No Name"
            raise cherrypy.HTTPRedirect(f"/show_user_profile?username={name}")
        else:
            return """
                <form method="post">
                    <label for="name">Name:</label><br>
                    <input type="text" id="name" name="name"><br><br>
                    <input type="submit" value="Submit">
                </form>
                <p>Route: /submit (GET)</p>
            """

    @cherrypy.expose
    def show_user_with_params(self, **params):
        user_id = params.get("id")
        user_type = params.get("type")
        return f"User ID: {user_id}, User Type: {user_type}, Route: /user"

    @cherrypy.expose
    def sign_in(self, username=None, password=None):
        password_db = {"irina": "secret", "david": "p=np"}

        if username and (password_db.get(username) == password):
            # User successfully authenticated!
            return f"Here you go, get the sign-in token for: {username}\n"
        else:
            # Fail!
            return f"Wrong password or username!\n"


if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable CherryPy's built-in auto-reloader in development when requested
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    cherrypy.config.update(
        {
            "server.socket_host": host,
            "server.socket_port": port,
            "engine.autoreload.on": debug
        }
    )
    cherrypy.quickstart(MyApp())
