import cherrypy
import random
import string
import os

class UserController(object):
    @cherrypy.expose
    def index(self, username=None, user_id=None, **kwargs):
        """
        Handles the base /user route, including query parameters.
        - /user
        - /user?username=irina&user_id=123
        """
        if username or user_id:
            return f"User details from query params: Username: {username}, User ID: {user_id}, Route: /user"
        return "This is the /user index. Try /user/some_name, /user/123, or /user/some_name/123."

    def _cp_dispatch(self, vpath):
        """
        The dispatch method. It's called by CherryPy when it can't find a
        matching exposed method for the remaining path segments in `vpath`.
        
        `vpath` is a list of path segments. For a request to "/user/irina/123",
        the `vpath` given to this dispatcher would be ['irina', '123'].
        """
        # Case 1: /user/<username>/<user_id>  (e.g., vpath = ['irina', '123'])
        if len(vpath) == 2:
            username = vpath.pop(0)
            user_id = vpath.pop(0)

            cherrypy.request.params['username'] = username
            cherrypy.request.params['user_id'] = user_id
            
            return self.details

        # Case 2: /user/<segment> (e.g., vpath = ['irina'] or vpath = ['123'])
        if len(vpath) == 1:
            segment = vpath.pop(0)
            
            if segment.isdigit():
                cherrypy.request.params['user_id'] = segment
                return self.by_id
            else:
                cherrypy.request.params['username'] = segment
                return self.by_name
        return self

    @cherrypy.expose
    def details(self, username, user_id):
        return f"Username: {username}, User ID: {user_id}, Route: /user/{username}/{user_id}"
    
    @cherrypy.expose
    def by_id(self, user_id):
        return f"User ID: {user_id}, Route: /user/{user_id}"

    @cherrypy.expose
    def by_name(self, username):
        return f"User: {username}, Route: /user/{username}"


class MyApp(object):
    def __init__(self):
        self.user = UserController()

    @cherrypy.expose
    def hello(self):
        return "Hello world!"
    
    @cherrypy.expose
    def index(self):
        return """<html>
          <head></head>
          <body>
            <form method="get" action="generate">
              <input type="text" value="8" name="length" />
              <button type="submit">Give it now!</button>
            </form>
          </body>
        </html>"""
    
    @cherrypy.expose
    def generate(self, length=8):
        return ''.join(random.sample(string.hexdigits, int(length)))
    
    @cherrypy.expose
    def submit(self, name=None):
        if cherrypy.request.method == 'POST':
            if name is None:
                name = "No Name"
            raise cherrypy.HTTPRedirect(f"/user/{name}")
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
    def sign_in(self, username=None, password=None):
        password_db = {
            'irina': 'secret',
            'david': 'p=np'
        }

        if username and (password_db.get(username) == password):
            return f"Here you go, get the sign-in token for: {username}\n"
        else:
            return f"Wrong password or username!\n"


if __name__ == '__main__':
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '8000'))
    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
    })
    cherrypy.quickstart(MyApp())