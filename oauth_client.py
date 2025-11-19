from authlib.integrations.flask_client import OAuth
import os
print("DEBUG CLIENT_ID =", os.getenv("CLIENT_ID"))
print("DEBUG CLIENT_SECRET is None?", os.getenv("CLIENT_SECRET") is None)


oauth = OAuth()
google = None

def init_oauth(app):
    global oauth, google
    oauth.init_app(app)
    # register the google client; uses env vars from the app environment
    google = oauth.register(
        name='google',
        client_id=os.environ.get('CLIENT_ID'),
        client_secret=os.environ.get('CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        },
        redirect_uri='http://127.0.0.1:5000/authorize/google'
    )

