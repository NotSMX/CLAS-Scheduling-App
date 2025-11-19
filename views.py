from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Session, Event, Room
import re

main_blueprint = Blueprint("main", __name__)

@main_blueprint.get("/")
def landing():
    return render_template("base.html")

@main_blueprint.get("/home")
def home():
    return render_template("home.html", user=current_user)

@main_blueprint.get("/schedule")
def schedule():
    sessions = (
        Session.query
        .join(Event, Session.submission_id == Event.id)
        .join(Room, Session.room_id == Room.id)
        .add_columns(
            Session.start_time, 
            Session.end_time, 
            Event.session_title,
            Event.department,
            Event.format,
            Room.building_name,
            Room.room_number
        )
        .all()
    )
    
    # Format sessions for display
    session_list = []
    for s in sessions:
        session_obj = s[0]
        start_time = s[1]
        end_time = s[2]
        title = s[3]
        dept = s[4]
        format_type = s[5]
        building = s[6]
        room_num = s[7]
        
        # Determine session type for display
        session_type = "Open"
        if "Closed" in format_type or "closed" in (session_obj.Event.special_request or "").lower():
            session_type = "Closed"
        elif "Family" in (session_obj.Event.special_request or ""):
            session_type = "Family Friendly"
        
        session_list.append({
            'title': title,
            'dept': dept,
            'building': building,
            'room': room_num,
            'start_time': start_time.strftime("%I:%M %p") if start_time else "",
            'end_time': end_time.strftime("%I:%M %p") if end_time else "",
            'type': session_type,
            'description': session_obj.Event.course_title or title
        })
    
    return render_template("schedule.html", sessions=session_list, user=current_user if current_user.is_authenticated else None)

@main_blueprint.get("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@main_blueprint.get("/settings")
@login_required
def settings_page():
    return render_template("settings.html", user=current_user)

@main_blueprint.get('/admin')
@login_required
def admin_redirect():
    return redirect(url_for('admin.view_sessions'))

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
        if len(new_password) < 8:
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must be at least 8 characters."
            )
        if len(new_password) > 100:
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must be at most 100 characters."
            )
        if not any(ch.isdigit() for ch in new_password):
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must include at least one number."
            )
        
        if not any(re.match(r"[^\w]", ch) for ch in new_password):
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must include at least one special character."
            )
        if new_password == new_password.lower():
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must have at least one uppercase letter."
            )
        if new_password == new_password.upper():
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must have at least one lowercase letter."
            )
        char_counter = dict()
        for i in new_password:
            if i in char_counter:
                char_counter[i] += 1
            else:
                char_counter[i] = 1
        if len(char_counter) < len(new_password) // 2:
            return render_template(
                "register.html",
                error_code=400,
                error_message="Password must include more unique characters."
            )
        current_user.set_password(new_password)

    db.session.commit()
    return render_template(
        "settings.html",
        user=current_user,
        success_code=200,
        success_message="Settings updated successfully."
    )