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
        return redirect(url_for("auth.login"))
    
    token = google.authorize_access_token()
    userinfo_endpoint = google.server_metadata['userinfo_endpoint']
    resp = google.get(userinfo_endpoint)
    user_info = resp.json()

    email = user_info.get('email')

    if not email.endswith("@colby.edu"):
        flash("You must use a Colby email address to register.", "danger")
        return redirect(url_for("auth.login"))

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

@auth_blueprint.get("/register")
def register():
    return render_template("register.html", user=current_user)

@auth_blueprint.get("/login")
def login():
    return render_template("login.html", user=current_user)

@auth_blueprint.post("/api/v1/login")
def api_login():
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return render_template(
            "login.html",
            user=current_user,
            error_code=401,
            error_message="Invalid email or password."
        )
    
    login_user(user)
    return render_template(
        "home.html",
        user=current_user,
        success_code=200,
        success_message="Logged in successfully!"
    )

@auth_blueprint.post("/api/v1/register")
def api_register():
    user = (request.form.get("user") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    role = (request.form.get("role") or "").strip()

    if not user or not email or not password or not role:
        return render_template(
            "register.html",
            user=current_user,
            error_code=400,
            error_message="Please fill in all fields."
        )
    
    if User.query.filter_by(email=email).first():
        return render_template(
            "register.html",
            user=current_user,
            error_code=400,
            error_message="Email already registered!"
        )
    
    new_user = User(name=user, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return render_template(
        "login.html",
        user=current_user,
        success_code=201,
        success_message="Account created successfully! You can now log in."
    )

@auth_blueprint.post("/api/v1/logout")
@login_required
def api_logout():
    logout_user()
    return render_template(
        "home.html",
        user=current_user,
        success_code=200,
        success_message="You have been logged out."
    )