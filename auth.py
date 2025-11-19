from flask import Blueprint, render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Session, Event
from oauth_client import google

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/login/google')
def login_google():
    try:
        redirect_uri = url_for('auth.authorize_google', _external=True)
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        auth_blueprint.logger.error(f"Google login error: {e}")
        return "Error during Google login.", 500


@auth_blueprint.route('/authorize/google')
def authorize_google():
    if 'error' in request.args:
        flash("Google login was denied.", "danger")
        return redirect(url_for("main.login"))
    
    token = google.authorize_access_token()
    userinfo_endpoint = google.server_metadata['userinfo_endpoint']
    resp = google.get(userinfo_endpoint)
    user_info = resp.json()

    email = user_info.get('email')

    if not email.endswith("@colby.edu"):
        flash("You must use a Colby email address to register.", "danger")
        return redirect(url_for("main.login"))

    user = User.query.filter_by(email=email).first()
    picture = user_info.get("picture")
    if not user:
        # Create a new user if not exists
        user = User(
            name=user_info.get('name', 'Google User'),
            email=email,
            role='admin',  # Default role
            profile_pic_url=picture
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)

    return redirect(url_for('main.home'))