from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from .models import db, Notification
from datetime import datetime

notifications_blueprint = Blueprint("notifications", __name__)

@notifications_blueprint.get("/notifications")
@login_required
def notifications_page():
    notifications = Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all()
    return render_template("notifications.html", user=current_user, notifications=notifications)

@notifications_blueprint.get("/notifications/create")
@login_required
def create_notification_page():
    if current_user.role != "admin":
        return render_template(
            "notifications.html",
            user=current_user,
            notifications=Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all(),
            error_code=403,
            error_message="You don't have permission to create notifications."
        )
    return render_template("notification_create.html", user=current_user)

@notifications_blueprint.post("/api/v1/notifications")
@login_required
def api_create_notification():
    if current_user.role != "admin":
        return render_template(
            "notifications.html",
            user=current_user,
            notifications=Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all(),
            error_code=403,
            error_message="You don't have permission to create notifications."
        )
    
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    priority = request.form.get('priority', 'normal')
    deadline_str = request.form.get('deadline', '').strip()
    
    if not title or not message:
        return render_template(
            "notification_create.html",
            user=current_user,
            error_code=400,
            error_message="Title and message are required."
        )
    
    # Parse deadline if provided
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return render_template(
                "notification_create.html",
                user=current_user,
                error_code=400,
                error_message="Invalid deadline format."
            )
    
    new_notification = Notification(
        title=title,
        message=message,
        created_by=current_user.id,
        priority=priority,
        deadline=deadline
    )
    
    db.session.add(new_notification)
    db.session.commit()
    
    notifications = Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all()
    return render_template(
        "notifications.html",
        user=current_user,
        notifications=notifications,
        success_code=201,
        success_message=f'Notification "{title}" created successfully!'
    )

@notifications_blueprint.post("/api/v1/notifications/<int:notification_id>/delete")
@login_required
def api_delete_notification(notification_id):
    if current_user.role != "admin":
        return render_template(
            "notifications.html",
            user=current_user,
            notifications=Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all(),
            error_code=403,
            error_message="You don't have permission to delete notifications."
        )
    
    notification = Notification.query.get_or_404(notification_id)
    notification.is_active = False
    db.session.commit()
    
    notifications = Notification.query.filter_by(is_active=True).order_by(Notification.created_at.desc()).all()
    return render_template(
        "notifications.html",
        user=current_user,
        notifications=notifications,
        success_code=200,
        success_message="Notification deleted successfully!"
    )