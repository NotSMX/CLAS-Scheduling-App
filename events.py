from flask import Blueprint, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Event, Session
from datetime import time

events_blueprint = Blueprint("events", __name__)

@events_blueprint.get("/events")
@login_required
def events_page():
    events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template("eventlist.html", user=current_user, events=events)

@events_blueprint.get("/events/new")
@login_required
def event_create_page():
    return render_template("eventcreate.html", user=current_user)

@events_blueprint.get("/events/<int:event_id>/edit")
@login_required
def event_edit_page(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template("eventedit.html", user=current_user, event=event)

@events_blueprint.post("/api/v1/events")
@login_required
def api_create_event():
    # Collect form data
    clas_type = request.form.get('clas_type', '').strip()
    format = request.form.get('format', '').strip()
    department = request.form.get('department', '').strip()
    course_number = request.form.get('course_number', '').strip()
    course_title = request.form.get('course_title', '').strip()
    session_title = request.form.get('session_title', '').strip()
    room_request = request.form.get('room_request', '').strip()
    special_request = request.form.get('special_request', '').strip()

    action = request.form.get('action')
    status = 'submitted' if action == 'submit' else 'draft'

    # Handle numeric fields
    try:
        num_entries = int(request.form.get('num_entries')) if request.form.get('num_entries') else None
        num_students = int(request.form.get('num_students')) if request.form.get('num_students') else None
        session_length = int(request.form.get('session_length')) if request.form.get('session_length') else None
        individual_entry_length = int(request.form.get('individual_entry_length')) if request.form.get('individual_entry_length') else None
    except ValueError:
        flash("Numeric fields must be valid numbers.", "error")
        return redirect(url_for('events.eventcreate'))

    # Validate required fields for submitted events
    if status == "submitted":
        required_fields = [
            clas_type, format, department, course_number, course_title,
            session_title, num_entries, num_students, session_length, individual_entry_length
        ]
        if any(f is None or f == "" for f in required_fields):
            return render_template(
                "eventcreate.html",
                user=current_user,
                error_code=400,
                error_message="All fields must be filled to submit the event. Please double-check all required fields, or save as a draft."
            )
        
    # Assign a temporary name if session_title is blank (for drafts)
    if not session_title:
        # Count existing drafts for the current user
        draft_count = Event.query.filter_by(user_id=current_user.id, status="draft").count()
        session_title = f"New Event {draft_count + 1}"

    # Create and save event
    new_event = Event(
        user_id=current_user.id,
        clas_type=clas_type,
        format=format,
        department=department,
        course_number=course_number,
        course_title=course_title,
        num_entries=num_entries if num_entries is not None else 0,
        num_students=num_students if num_students is not None else 0,
        session_title=session_title,
        session_length=session_length if session_length is not None else 0,
        individual_entry_length=individual_entry_length if individual_entry_length is not None else 0,
        room_request=room_request,
        special_request=special_request,
        status=status
    )
    db.session.add(new_event)
    db.session.commit()

    events = Event.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "eventlist.html",
        user=current_user,
        events=events,
        success_code=201,
        success_message=f'{"Draft" if status=="draft" else "Event"} "{session_title.capitalize()}" saved successfully!'
    )

@events_blueprint.get("/api/v1/events")
@login_required
def api_get_events():
    events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template('eventlist.html', user=current_user, success_code=200, events=events)

@events_blueprint.post("/api/v1/events/<int:event_id>/submit")
@login_required
def api_submit_event(event_id):
    print("Submitting event:", event_id)
    event = Event.query.get_or_404(event_id)
    
    # Check if session already exists for this event
    if event.status == "submitted":
        events = Event.query.filter_by(user_id=current_user.id).all()
        return render_template(
            "eventlist.html",
            user=current_user,
            events=events,
            error_code=400,
            error_message=f'Event "{event.session_title}" has already been submitted.'
        )
    
    required_fields = [
        event.clas_type, event.format, event.department, event.course_number,
        event.course_title, event.num_entries, event.num_students,
        event.session_title, event.session_length, event.individual_entry_length
    ]
    if any(f is None or f == "" for f in required_fields):
        events = Event.query.filter_by(user_id=current_user.id).all()
        return render_template(
            "eventlist.html",
            user=current_user,
            events=events,
            error_code=400,
            error_message="All fields must be filled to submit the event. Please double check you have filled out all the required fields. Or, you can save this as a draft and come back to it later."
        )
    event.status = "submitted"
    db.session.commit()

    # Create a new session for this event
    from datetime import datetime, timedelta
    
    # Example: default start_time as now, end_time based on session_length (assuming minutes)
    start_time = datetime.now().time()
    end_time_dt = (datetime.combine(datetime.today(), start_time) + timedelta(minutes=event.session_length)).time()
    
    new_session = Session(
        user_id=current_user.id,
        submission_id=event.id,
        room_id=event.room_id if hasattr(event, "room_id") else 1,  # fallback room
        start_time=start_time,
        end_time=end_time_dt
    )
    db.session.add(new_session)
    db.session.commit()
    
    events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "eventlist.html",
        user=current_user,
        events=events,
        success_code=200,
        success_message=f'Event "{event.session_title}" submitted successfully!'
    )

@events_blueprint.post("/api/v1/events/<int:event_id>/edit")
@login_required
def api_edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != current_user.id:
        return render_template(
            "eventlist.html",
            user=current_user,
            error_code=403,
            error_message="You don't have permission to edit this event."
        )

    action = request.form.get('action')

    event.clas_type = request.form.get("clas_type", event.clas_type)
    event.format = request.form.get("format", event.format)
    event.department = request.form.get("department", event.department)
    event.course_number = request.form.get("course_number", event.course_number)
    event.course_title = request.form.get("course_title", event.course_title)
    event.num_entries = request.form.get("num_entries", type=int) or event.num_entries
    event.num_students = request.form.get("num_students", type=int) or event.num_students
    event.session_title = request.form.get("session_title", event.session_title)
    event.session_length = request.form.get("session_length", event.session_length)
    event.individual_entry_length = request.form.get("individual_entry_length", event.individual_entry_length)
    event.room_request = request.form.get("room_request", event.room_request)
    event.special_request = request.form.get("special_request", event.special_request)

    if action == "draft":
        event.status = "draft"
        db.session.commit()
        return render_template(
            "eventedit.html",
            user=current_user,
            event=event,
            success_code=200,
            success_message=f'Draft "{event.session_title}" saved successfully!'
        )
    if action == "submit":
        required_fields = [
            event.clas_type, event.format, event.department, event.course_number,
            event.course_title, event.num_entries, event.num_students,
            event.session_title, event.session_length, event.individual_entry_length
        ]
        if any(f is None or f == "" for f in required_fields):
            if any(f is None or f == "" for f in required_fields):
                return render_template(
                    "eventedit.html",
                    user=current_user,
                    event=event,
                    error_code=400,
                    error_message="All fields must be filled to submit the event. Please double check you have filled out all the required fields. Or, you can save this as a draft and come back to it later."
                )

        event.status = "submitted"

    db.session.commit()
    return render_template(
        "eventedit.html",
        user=current_user,
        event=event,
        success_code=200,
        success_message=f'Event "{event.session_title}" updated successfully!'
    )

@events_blueprint.post("/api/v1/events/<int:event_id>/delete")
@login_required
def api_delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != current_user.id:
        return render_template(
            "eventlist.html",
            user=current_user,
            error_code=403,
            error_message="You don't have permission to delete this event."
        )

    db.session.delete(event)
    db.session.commit()
    events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "eventlist.html",
        user=current_user,
        events=events,
        success_code=200,
        success_message=f'Event "{event.session_title}" deleted successfully!'
    )