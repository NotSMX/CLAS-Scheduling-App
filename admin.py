from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, Session, Event, Room
from datetime import datetime
from functools import wraps

admin_blueprint = Blueprint('admin', __name__, url_prefix='/admin')

# Admin-only decorator
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash("Access denied.", "error")
            return redirect(url_for("main.home"))
        return func(*args, **kwargs)
    return wrapper

@admin_blueprint.get('/sessions')
@login_required
@admin_required
def view_sessions():
    # preload event, room, user
    sessions = Session.query.options(
        db.joinedload(Session.event),
        db.joinedload(Session.room),
        db.joinedload(Session.user)
    ).all()
    
    return render_template('admin.html', sessions=sessions)

@admin_blueprint.post('/sessions/update/<int:session_id>')
@login_required
@admin_required
def update_session(session_id):
    session_obj = Session.query.get_or_404(session_id)
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    status = request.form.get('status')

    if start_time:
        session_obj.start_time = datetime.strptime(start_time, "%H:%M").time()
    if end_time:
        session_obj.end_time = datetime.strptime(end_time, "%H:%M").time()
    if status in ['draft', 'approved', 'rejected']:
        session_obj.event.status = status

    db.session.commit()
    flash("Session updated successfully.", "success")
    return redirect(url_for('admin.view_sessions'))

@admin_blueprint.post('/sessions/delete/<int:session_id>')
@login_required
@admin_required
def delete_session(session_id):
    session_obj = Session.query.get_or_404(session_id)
    db.session.delete(session_obj)
    db.session.commit()
    flash("Session deleted successfully.", "success")
    return redirect(url_for('admin.view_sessions'))
