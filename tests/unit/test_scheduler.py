import pytest
from website.scheduler import Scheduler, build_schedule_suggestions
from datetime import time
from website.models import db

def test_build_schedule_suggestions(setup_db):
    events = setup_db['events']

    events[0].day = "Monday"
    events[0].room_id = 1
    events[1].day = "Monday"
    events[1].room_id = 2

    schedule = build_schedule_suggestions(events)

    assert len(schedule) == 1
    assert schedule[0]['day'] == "Monday"
    assert len(schedule[0]['rooms']) == 2
    assert schedule[0]['rooms'][0]['events'][0].session_title == "Session 1"

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


def test_schedule_event(setup_db, app):
    events = setup_db['events']
    rooms = setup_db['rooms']
    scheduler = Scheduler()

    event_id = events[0].id
    room_id = rooms[0].id
    start_time = time(9, 0)

    session, message = scheduler.schedule_event(event_id, start_time=start_time, room_id=room_id)

    assert session is not None
    assert session.room_id == room_id
    assert session.start_time == start_time
    assert message == "Event scheduled successfully"

def test_schedule_all_events(setup_db, app):
    scheduler = Scheduler()
    results = scheduler.schedule_all_events()

    assert len(results) == len(setup_db['events'])
    for result in results:
        assert result['success'] is True
        assert "scheduled successfully" in result['message']

def test_reschedule_event(setup_db, app):
    scheduler = Scheduler()
    event = setup_db['events'][0]
    session, _ = scheduler.schedule_event(event.id, start_time=time(9,0), room_id=setup_db['rooms'][0].id)
    
    new_time = time(10,0)
    session, message = scheduler.reschedule_event(session.id, new_start_time=new_time)

    assert session.start_time == new_time
    assert "rescheduled successfully" in message

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