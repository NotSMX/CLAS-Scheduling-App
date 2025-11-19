from flask import Blueprint, render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Session, Event
from oauth_client import google
import re

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
        return render_template(
            "login.html",
            user=current_user,
            error_code=401,
            error_message="Google login was denied."
        )
    
    token = google.authorize_access_token()
    userinfo_endpoint = google.server_metadata['userinfo_endpoint']
    resp = google.get(userinfo_endpoint)
    user_info = resp.json()

    email = user_info.get('email')

    if not email.endswith("@colby.edu"):
        return render_template(
            "login.html",
            user=current_user,
            error_code=401,
            error_message="You must use a Colby email address to register."
        )

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

    if len(password) < 8:
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must be at least 8 characters."
        )
    if len(password) > 100:
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must be at most 100 characters."
        )
    if not any(ch.isdigit() for ch in password):
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must include at least one number."
        )
    
    if not any(re.match(r"[^\w]", ch) for ch in password):
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must include at least one special character."
        )
    if password == password.lower():
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must have at least one uppercase letter."
        )
    if password == password.upper():
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must have at least one lowercase letter."
        )
    char_counter = dict()
    for i in password:
        if i in char_counter:
            char_counter[i] += 1
        else:
            char_counter[i] = 1
    if len(char_counter) < len(password) // 2:
        return render_template(
            "register.html",
            error_code=400,
            error_message="Password must include more unique characters."
        )
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