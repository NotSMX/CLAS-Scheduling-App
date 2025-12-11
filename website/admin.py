from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from .models import db, Session, Event, Room
from datetime import datetime, timedelta
from functools import wraps
from .scheduler import Scheduler


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
    building = request.args.get('building') or None
    room_id = request.args.get('room_id', type=int)
    status = request.args.get('status') or None

    # base query with joins so we can filter by room / event fields
    query = (
        Session.query
        .options(
            db.joinedload(Session.event),
            db.joinedload(Session.room),
            db.joinedload(Session.user),
        )
        .join(Room, Session.room_id == Room.id)
        .join(Event, Session.submission_id == Event.id)
    )

    if building:
        query = query.filter(Room.building_name == building)
    if room_id:
        query = query.filter(Session.room_id == room_id)
    if status:
        query = query.filter(Event.status == status)

    sessions = query.order_by(
        Room.building_name,
        Room.room_number,
        Session.start_time
    ).all()

    # all rooms once, used for filters + JS map
    all_rooms = Room.query.order_by(Room.building_name, Room.room_number).all()
    buildings = sorted({r.building_name for r in all_rooms})

    if building:
        rooms = [r for r in all_rooms if r.building_name == building]
    else:
        rooms = all_rooms

    # map: building -> list of {id, room_number}
    rooms_by_building = {}
    for r in all_rooms:
        rooms_by_building.setdefault(r.building_name, []).append(
            {"id": r.id, "room_number": r.room_number}
        )

    return render_template(
        "admin.html",
        sessions=sessions,
        buildings=buildings,
        rooms=rooms,
        selected_building=building,
        selected_room_id=room_id,
        selected_status=status,
        rooms_by_building=rooms_by_building,
    )


@admin_blueprint.post('/sessions/update/<int:session_id>')
@login_required
@admin_required
def update_session(session_id):
    session_obj = Session.query.get_or_404(session_id)
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    status_input = request.form.get('status')


    start_input = parse_time(start_time_str) if start_time_str else session_obj.start_time
    end_input   = parse_time(end_time_str) if end_time_str else session_obj.end_time

    event = session_obj.event
    duration = timedelta(minutes=event.session_length)

    start_changed = start_input != session_obj.start_time
    end_changed   = end_input != session_obj.end_time

    if start_changed and not end_changed:
        new_start = start_input
        base_dt = datetime.combine(datetime.today(), new_start)
        new_end = (base_dt + duration).time()
        status = 'draft'
    elif end_changed and not start_changed:
        new_end = end_input
        base_dt = datetime.combine(datetime.today(), new_end)
        new_start = (base_dt - duration).time()
        status = 'draft'
    elif start_changed and end_changed:
        new_start = start_input
        new_end = end_input
        status = 'draft'
    else:
        new_start = session_obj.start_time
        new_end = session_obj.end_time
        status = status_input

    if status == 'approved':
        scheduler = Scheduler()

        conflicts = scheduler._get_room_conflicts(
            room_id=session_obj.room_id,
            start_time=new_start,
            end_time=new_end,
            exclude_session_id=session_obj.id
        )

        if conflicts:
            conflict_list = ", ".join([
                f"{c.event.session_title} ({c.start_time.strftime('%I:%M %p')}–{c.end_time.strftime('%I:%M %p')})"
                for c in conflicts
            ])

            flash(
                f"Cannot approve: conflicts with approved session(s): {conflict_list}",
                "error"
            )
            return redirect(url_for('admin.view_sessions'))

    session_obj.start_time = new_start
    session_obj.end_time = new_end

    if status in ['draft', 'approved', 'rejected']:
        session_obj.event.status = status

    db.session.commit()
    flash("Session updated successfully.", "success")
    return redirect(url_for('admin.view_sessions'))

def parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except ValueError:
        return datetime.strptime(value, "%H:%M").time()

@admin_blueprint.post('/sessions/delete/<int:session_id>')
@login_required
@admin_required
def delete_session(session_id):
    session_obj = Session.query.get_or_404(session_id)
    db.session.delete(session_obj)
    db.session.commit()
    flash("Session deleted successfully.", "success")
    return redirect(url_for('admin.view_sessions'))
