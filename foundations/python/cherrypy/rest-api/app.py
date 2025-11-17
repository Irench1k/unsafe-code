import random
import string

import cherrypy


@cherrypy.expose
class StringGeneratorWebService:
    """
    RESTful web service for string generation using HTTP method dispatching.
    
    Uses CherryPy's MethodDispatcher to route HTTP verbs to corresponding methods:
    - GET: Retrieve current string from session
    - POST: Generate new string with optional length parameter
    - PUT: Replace current string with provided value
    - DELETE: Remove string from session
    """

    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        """Retrieve the current string from session."""
        return cherrypy.session.get('mystring', 'No string stored')

    def POST(self, length=8):
        """Generate a new random string and store in session."""
        some_string = ''.join(random.sample(string.hexdigits, int(length)))
        cherrypy.session['mystring'] = some_string
        return some_string

    def PUT(self, another_string):
        """Replace the current string with a new value."""
        cherrypy.session['mystring'] = another_string
        return f"String updated to: {another_string}"

    def DELETE(self):
        """Remove the string from session."""
        old_string = cherrypy.session.pop('mystring', None)
        if old_string:
            return f"Deleted string: {old_string}"
        else:
            return "No string to delete"


# Configuration for the REST API
API_CONFIG = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Content-Type', 'text/plain')],
    }
}

# Export the app and config for use by run.py
app = StringGeneratorWebService()
config = API_CONFIG
