from flask import Flask, render_template_string, request, redirect, url_for
from markupsafe import escape

app = Flask(__name__)

# Basic example, minimal page from tutorial
@app.route('/')
def index():
    return 'Index Page: go check out /submit and other pages'

# Various ways of defining routes:

# Trailing Slash: 
@app.route('/about/')  # Note the trailing slash
def about():
    return f'About Page, Route: {request.path}'

# Basic Routing: /first, /first/second
@app.route('/first')
def first():
    return 'First Page'

@app.route('/first/second')
def second():
    return 'Second Page'

# Dynamic Routing: Route Variables -> /<username>, /user/<username>
@app.route('/<username>')
def show_username(username):
    return f'User: {escape(username)}, Route: {request.path}'

@app.route('/user/<username>')
def show_user_profile(username):
    return f'User: {escape(username)}, Route: {request.path}'

# Dynamic Routing: Data Types in Routes -> /user/<int:user_id>
@app.route('/user/<int:user_id>')
def show_user_id(user_id):
    return f'User ID: {user_id}, Route: {request.path}'

# Route with both username and user_id
@app.route('/user/<username>/<int:user_id>')
def show_user_details(username, user_id):
    return f'Username: {escape(username)}, User ID: {user_id}, Route: {request.path}'

# HTTP Methods: GET and POST
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        # Process the form data
        form_data = request.form
        name = form_data.get('name', 'No Name')
        return redirect(url_for('show_user_profile', username=name))
    else:
        # Display the form
        return render_template_string('''
            <form method="post">
                <label for="name">Name:</label><br>
                <input type="text" id="name" name="name"><br><br>
                <input type="submit" value="Submit">
            </form>
            <p>Route: /submit (GET)</p>
        ''')

# Handle query parameters: /user?id=123&type=admin
# This code is vulnerable, such a thing can work: /user?id=123&type=<script>alert(1)</script>
@app.route('/user')
def show_user_with_params():
    user_id = request.args.get('id')
    user_type = request.args.get('type')
    return f'User ID: {user_id}, User Type: {user_type}, Route: {request.path}'

if __name__ == "__main__":
    app.run(debug=True)