"""
Python Flask WebApp Keycloak integration example
"""
from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

import constants

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

KEYCLOAK_CALLBACK_URL = env.get(constants.KEYCLOAK_CALLBACK_URL)
KEYCLOAK_CLIENT_ID = env.get(constants.KEYCLOAK_CLIENT_ID)
KEYCLOAK_CLIENT_SECRET = env.get(constants.KEYCLOAK_CLIENT_SECRET)
KEYCLOAK_METADATA_URL = env.get(constants.KEYCLOAK_METADATA_URL)

app = Flask(__name__, static_url_path='/public', static_folder='./public')
app.secret_key = constants.SECRET_KEY
app.debug = True

@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response

oauth = OAuth(app)

keycloak = oauth.register(
    'keycloak',
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret=KEYCLOAK_CLIENT_SECRET,
    server_metadata_url=KEYCLOAK_METADATA_URL,
    client_kwargs={
        'scope': 'openid profile email',
    },
)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

# Controllers API
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/callback')
def callback_handling():
    token = keycloak.authorize_access_token()
    userinfo = keycloak.parse_id_token(token)
    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name']
    }
    return redirect('/dashboard')

@app.route('/login')
def login():
    return keycloak.authorize_redirect(redirect_uri=KEYCLOAK_CALLBACK_URL)

@app.route('/logout')
def logout():
    session.clear()
    params = {'redirect_uri': url_for('home', _external=True)}
    return redirect(keycloak.server_metadata['end_session_endpoint']+'?' + urlencode(params))

@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=env.get('PORT', 3000))
