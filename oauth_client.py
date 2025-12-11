from authlib.integrations.flask_client import OAuth
import os

oauth = OAuth()
google = None  # will be set in init_oauth


def init_oauth(app):
    global google

    oauth.init_app(app)

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    app.logger.debug(f"DEBUG CLIENT_ID = {client_id}")
    app.logger.debug(f"DEBUG CLIENT_SECRET is None? {client_secret is None}")

    google = oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        },
    )
