import pytest
from website.scheduler import Scheduler, build_schedule_suggestions
from datetime import time, datetime, timedelta
from website.models import db
from website.models import Session

def test_build_schedule_suggestions(setup_db):
    sessions = []

    # Assign start/end times and room IDs to sessions
    for i, event in enumerate(setup_db['events'][:2]):
        s = event.session
        s.start_time = time(9 + i, 0)
        s.end_time = time(10 + i, 0)
        s.room_id = i + 1
        sessions.append(s)
    db.session.commit()

    schedule = build_schedule_suggestions(sessions)

    assert len(schedule) == 1
    assert schedule[0]['day'] == "Unscheduled"
    assert len(schedule[0]['rooms']) == 2
    assert schedule[0]['rooms'][0]['events'][0].event.session_title == "Session 1"


def test_generate_schedule_options(setup_db, app):
    events = setup_db['events']
    scheduler = Scheduler()

    for e in events:
        e.room_request = None

    event_id = events[0].id
    options = scheduler.generate_schedule_options(event_id, max_options=3)

    assert options
    assert 'room' in options[0]
    assert options[0]['is_preferred'] in [True, False]

def test_generate_schedule_options_past_end(setup_db):
    """Event that would end after 5 PM should be skipped."""
    scheduler = Scheduler()
    event = setup_db['events'][0]
    event.status = "submitted"
    event.session_length = 120  # 2 hours
    db.session.commit()

    # Manipulate time slots to force last slot to go past 5 PM
    scheduler.time_slots = [time(16, 30)]  # 16:30 + 2h = 18:30 → past 17:00

    options = scheduler.generate_schedule_options(event.id)
    assert options == []  # Should skip because it ends after 5 PM

def test_schedule_event(setup_db, app):
    events = setup_db['events']
    rooms = setup_db['rooms']
    scheduler = Scheduler()

    event_id = events[0].id
    room_id = rooms[0].id
    start_time = time(9, 0)

    event = setup_db['events'][0]
    event.status = "submitted"
    db.session.commit()

    # Remove existing session if any
    s = Session.query.filter_by(submission_id=event.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()

    session, message = scheduler.schedule_event(event_id, start_time=start_time, room_id=room_id)

    assert session is not None
    assert session.room_id == room_id
    assert session.start_time == start_time
    assert message == "Event scheduled successfully"

def test_schedule_event_already_scheduled(setup_db):
    scheduler = Scheduler()
    event = setup_db['events'][0]
    event.status = "submitted"
    db.session.commit()

    room = setup_db['rooms'][0]
    # First schedule
    scheduler.schedule_event(event.id, start_time=time(9,0), room_id=room.id)
    # Attempt second schedule
    session, message = scheduler.schedule_event(event.id, start_time=time(10,0), room_id=setup_db['rooms'][1].id)
    assert session is None
    assert message == "Event is already scheduled"

def test_schedule_event_room_unavailable(setup_db):
    scheduler = Scheduler()
    event_to_schedule = setup_db['events'][0]
    blocking_event = setup_db['events'][1]

    # Both events must be submitted
    event_to_schedule.status = "submitted"
    blocking_event.status = "submitted"

    # Remove any existing sessions
    for e in [event_to_schedule, blocking_event]:
        s = Session.query.filter_by(submission_id=e.id).first()
        if s:
            db.session.delete(s)
    db.session.commit()

    # Create a session for blocking_event and mark it APPROVED
    blocking_session = Session(
        user_id=blocking_event.user_id,
        submission_id=blocking_event.id,
        room_id=setup_db['rooms'][0].id,
        start_time=time(9,0),
        end_time=(datetime.combine(datetime.today(), time(9,0)) + timedelta(minutes=blocking_event.session_length)).time()
    )
    db.session.add(blocking_session)
    db.session.commit()

    blocking_event.status = "approved"
    db.session.commit()

    # Attempt to schedule event_to_schedule in the same room/time
    session, message = scheduler.schedule_event(
        event_to_schedule.id,
        start_time=time(9,0),
        room_id=setup_db['rooms'][0].id
    )

    assert session is None
    assert message == "Selected time slot is not available"

def test_schedule_event_end_time_past_5(setup_db):
    scheduler = Scheduler()
    event = setup_db['events'][0]
    event.status = "submitted"
    event.session_length = 120
    db.session.commit()

    # Remove any existing session
    s = Session.query.filter_by(submission_id=event.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()

    # Only late slots left
    scheduler.time_slots = [time(16,30)]
    session, message = scheduler.schedule_event(event.id)
    assert session is None
    assert message == "No available time slots or rooms found"

def test_schedule_event_no_rooms(setup_db):
    scheduler = Scheduler()
    event = setup_db['events'][0]
    event.status = "submitted"
    event.num_students = 999  # impossible
    db.session.commit()

    # Remove any existing session
    s = Session.query.filter_by(submission_id=event.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()

    session, message = scheduler.schedule_event(event.id)
    assert session is None
    assert message == "No available time slots or rooms found"

def test_schedule_all_events(setup_db, app):
    scheduler = Scheduler()
    for e in setup_db['events']:
        # Ensure events have no session yet
        s = Session.query.filter_by(submission_id=e.id).first()
        if s:
            db.session.delete(s)
    db.session.commit()

    results = scheduler.schedule_all_events()

    assert len(results) == len(setup_db['events'])
    for result in results:
        assert result['success'] is True
        assert "scheduled successfully" in result['message']

def test_reschedule_event(setup_db, app):
    scheduler = Scheduler()
    event = setup_db['events'][0]
    event.status = "submitted"
    db.session.commit()

    # Remove existing session
    s = Session.query.filter_by(submission_id=event.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()

    session, _ = scheduler.schedule_event(event.id, start_time=time(9,0), room_id=setup_db['rooms'][0].id)

    
    new_time = time(10,0)

    session, message = scheduler.reschedule_event(session.id, new_start_time=new_time)

    assert session.start_time == new_time
    assert "rescheduled successfully" in message

def test_reschedule_event_not_found(setup_db, app):
    scheduler = Scheduler()
    session, message = scheduler.reschedule_event(session_id=9999, new_start_time=time(10,0))
    assert session is None
    assert message == "Session not found"

def test_reschedule_event_slot_not_available(setup_db):
    scheduler = Scheduler()
    event_to_reschedule = setup_db['events'][0]
    blocking_event = setup_db['events'][1]

    # Both events must be submitted
    event_to_reschedule.status = "submitted"
    blocking_event.status = "submitted"

    # Remove any existing sessions
    for e in [event_to_reschedule, blocking_event]:
        s = Session.query.filter_by(submission_id=e.id).first()
        if s:
            db.session.delete(s)
    db.session.commit()

    # Schedule event_to_reschedule first
    session_to_reschedule, _ = scheduler.schedule_event(
        event_to_reschedule.id,
        start_time=time(9,0),
        room_id=setup_db['rooms'][0].id
    )

    # Create a session for blocking_event at the conflicting new time and mark APPROVED
    blocking_session = Session(
        user_id=blocking_event.user_id,
        submission_id=blocking_event.id,
        room_id=session_to_reschedule.room_id,
        start_time=time(10,0),
        end_time=(datetime.combine(datetime.today(), time(10,0)) + timedelta(minutes=blocking_event.session_length)).time()
    )
    db.session.add(blocking_session)
    db.session.commit()

    blocking_event.status = "approved"
    db.session.commit()

    # Attempt to reschedule session_to_reschedule into blocked slot
    res_session, message = scheduler.reschedule_event(
        session_to_reschedule.id,
        new_start_time=time(10,0)
    )

    assert res_session is None
    assert message == "Time slot not available"

def test_find_suitable_rooms(setup_db, app):
    scheduler = Scheduler()
    event = setup_db['events'][0]

    event.room_request = "Lovejoy"
    event.num_students = 20

    start_time = time(9, 0)
    end_time = time(10, 0)

    suitable_rooms = scheduler._find_suitable_rooms(event, start_time, end_time)

    assert len(suitable_rooms) > 0
    assert any("Lovejoy" in room.building_name for room in suitable_rooms)

    for room in suitable_rooms:
        assert room.capacity >= event.num_students

def test_generate_schedule_options_none(setup_db, app):
    scheduler = Scheduler()

    options = scheduler.generate_schedule_options(event_id=9999)
    assert options == []

    event = setup_db['events'][0]
    event.status = "draft"
    db.session.commit()

    options = scheduler.generate_schedule_options(event_id=event.id)
    assert options == []

def test_schedule_not_found_event(setup_db, app):
    scheduler = Scheduler()
    fake_event_id = 9999

    session, message = scheduler.schedule_event(fake_event_id)

    assert session is None
    assert message == "Event not found"

def test_schedule_unsubmitted_event(setup_db, app):
    scheduler = Scheduler()
    event = setup_db['events'][0]

    event.status = "draft"
    with app.app_context():
        db.session.commit()

    session, message = scheduler.schedule_event(event.id)

    assert session is None
    assert message == "Event must be submitted before scheduling"