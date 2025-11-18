from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Session, Event

main_blueprint = Blueprint("main", __name__)

@main_blueprint.get("/")
def landing():
    return render_template("base.html")

@main_blueprint.get("/home")
def home():
    return render_template("home.html", user=current_user)

@main_blueprint.get("/schedule")
def schedule():
    return render_template("schedule.html", user=current_user)

@main_blueprint.get("/register")
def register():
    return render_template("register.html", user=current_user)

@main_blueprint.get("/login")
def login():
    return render_template("login.html", user=current_user)

@main_blueprint.get("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@main_blueprint.get("/settings")
@login_required
def settings_page():
    return render_template("settings.html", user=current_user)

@main_blueprint.post("/api/v1/login")
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

@main_blueprint.post("/api/v1/register")
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

@main_blueprint.get("/api/v1/schedule")
def api_schedule():
    sessions = (
        Session.query
        .join(Event, Session.submission_id == Event.id)
        .add_columns(Session.start_time, Session.end_time, Event.session_title)
        .all()
    )

   # Sort sessions by start time first
    sessions = sorted(sessions, key=lambda s: s[1])  # s[1] is start_time

    lanes = []
    session_list = []

    for s in sessions:
        session_obj = s[0]
        start_time = s[1]
        end_time = s[2]
        title = s[3]

        start = start_time.hour * 60 + start_time.minute
        end = end_time.hour * 60 + end_time.minute

        # If end < start, it means the session goes past midnight
        if end < start:
            end += 24 * 60  # add 1440 minutes

        placed = False
        for i, lane in enumerate(lanes):
            # Check if session overlaps with any session in lane
            overlap = any(not (end <= other["start_minutes"] or start >= other["end_minutes"]) for other in lane)
            if not overlap:
                lane.append({"session": session_obj, "start_minutes": start, "end_minutes": end, "title": title})
                session_list.append({"session": session_obj, "lane": i, "start_minutes": start, "end_minutes": end, "title": title})
                placed = True
                break

        if not placed:
            # No lane could fit it, create new lane
            lanes.append([{"session": session_obj, "start_minutes": start, "end_minutes": end, "title": title}])
            session_list.append({"session": session_obj, "lane": len(lanes)-1, "start_minutes": start, "end_minutes": end, "title": title})

    num_lanes = len(lanes)
    return render_template(
        "schedule.html",
        sessions=session_list,
        num_lanes=num_lanes,
        user=current_user if current_user.is_authenticated else None
    )



# Profile
@main_blueprint.get("/api/v1/profile")
@login_required
def api_profile():
    return render_template(
        "profile.html",
        user=current_user,
        success_code=200
    )

# Settings
@main_blueprint.post("/api/v1/settings")
@login_required
def api_settings():
    name = (request.form.get("name") or "").strip()
    role = (request.form.get("role") or "").strip()
    photo = (request.form.get("profile_pic_url") or "").strip()
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if name:
        current_user.name = name
    if role:
        current_user.role = role
    if photo:
        current_user.profile_pic_url = photo
    
    if new_password or confirm_password:
        if new_password != confirm_password:
            return render_template(
                "settings.html",
                user=current_user,
                error_code=400,
                error_message="Passwords do not match."
            )
        if len(new_password) < 6:
            return render_template(
                "settings.html",
                user=current_user,
                error_code=400,
                error_message="Password must be at least 6 characters."
            )
        current_user.set_password(new_password)

    db.session.commit()
    return render_template(
        "settings.html",
        user=current_user,
        success_code=200,
        success_message="Settings updated successfully."
    )

@main_blueprint.post("/api/v1/logout")
@login_required
def api_logout():
    logout_user()
    return render_template(
        "home.html",
        user=current_user,
        success_code=200,
        success_message="You have been logged out."
    )