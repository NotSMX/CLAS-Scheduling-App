import pytest
from website.models import User, Room, Event, Session, db
from datetime import datetime, time, timedelta
from website.admin import parse_time
from website.scheduler import Scheduler


def test_view_sessions_as_admin(admin_client, setup_db):
    """Admin can access the sessions page."""
    response = admin_client.get('/admin/sessions')
    assert response.status_code == 200
    for e in setup_db['events'][:2]:
        assert e.session.event.session_title.encode() in response.data


def test_view_sessions_as_non_admin(professor_client, setup_db):
    """Non-admin cannot access the sessions page."""
    response = professor_client.get('/admin/sessions', follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data

def test_view_sessions_filters(admin_client, setup_db):
    """Test filtering sessions by building, room_id, and status."""
    rooms = setup_db['rooms']
    events = setup_db['events']
    
    # By building
    building = rooms[0].building_name
    response = admin_client.get(f'/admin/sessions?building={building}')
    assert response.status_code == 200
    for s in events:
        # Only sessions in this building appear
        if s.session.room.building_name == building:
            assert s.session.event.session_title.encode() in response.data
    
    # By room_id
    room_id = rooms[0].id
    response = admin_client.get(f'/admin/sessions?room_id={room_id}')
    assert response.status_code == 200
    for s in events:
        if s.session.room_id == room_id:
            assert s.session.event.session_title.encode() in response.data
    
    # By status
    status = 'approved'
    # mark one session as approved
    events[0].status = status
    db.session.commit()
    response = admin_client.get(f'/admin/sessions?status={status}')
    assert response.status_code == 200
    assert events[0].session.event.session_title.encode() in response.data



def test_update_session_no_change(admin_client, setup_db):
    """Updating a session with no start/end changes keeps status."""
    session = setup_db['events'][0].session
    data = {
        'start_time': session.start_time.strftime("%H:%M"),
        'end_time': session.end_time.strftime("%H:%M"),
        'status': 'draft'
    }
    response = admin_client.post(
        f'/admin/sessions/update/{session.id}', data=data, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Session updated successfully" in response.data


def test_update_session_start_changed(admin_client, setup_db):
    """Changing only start time updates end time automatically and sets status to draft."""
    session = setup_db['events'][0].session
    new_start = "11:00"
    data = {'start_time': new_start, 'end_time': '', 'status': 'approved'}
    response = admin_client.post(
        f'/admin/sessions/update/{session.id}', data=data, follow_redirects=True
    )
    updated = Session.query.get(session.id)
    assert updated.start_time == time(11, 0)
    expected_end = (datetime.combine(datetime.today(), updated.start_time) +
                    timedelta(minutes=session.event.session_length)).time()
    assert updated.end_time == expected_end
    assert updated.event.status == 'draft'


def test_update_session_end_changed(admin_client, setup_db):
    """Changing only end time updates start time automatically and sets status to draft."""
    session = setup_db['events'][0].session
    new_end = "12:00"
    data = {'start_time': '', 'end_time': new_end, 'status': 'approved'}
    response = admin_client.post(
        f'/admin/sessions/update/{session.id}', data=data, follow_redirects=True
    )
    updated = Session.query.get(session.id)
    assert updated.end_time == time(12, 0)
    expected_start = (datetime.combine(datetime.today(), updated.end_time) -
                      timedelta(minutes=session.event.session_length)).time()
    assert updated.start_time == expected_start
    assert updated.event.status == 'draft'


def test_update_session_start_end_changed(admin_client, setup_db):
    """Changing both start and end times sets status to draft."""
    session = setup_db['events'][0].session
    data = {'start_time': "14:00", 'end_time': "15:00", 'status': 'approved'}
    response = admin_client.post(
        f'/admin/sessions/update/{session.id}', data=data, follow_redirects=True
    )
    updated = Session.query.get(session.id)
    assert updated.start_time == time(14, 0)
    assert updated.end_time == time(15, 0)
    assert updated.event.status == 'draft'


def test_update_session_approve_no_conflict(admin_client, setup_db):
    """Approving a session with no conflicts sets status to approved."""
    session = setup_db['events'][0].session
    data = {
        'start_time': session.start_time.strftime("%H:%M"),
        'end_time': session.end_time.strftime("%H:%M"),
        'status': 'approved'
    }
    response = admin_client.post(
        f'/admin/sessions/update/{session.id}', data=data, follow_redirects=True
    )
    updated = Session.query.get(session.id)
    assert updated.event.status == 'approved'

def test_update_session_approve_with_conflict(admin_client, setup_db):
    """Approving a session that conflicts with another approved session shows an error."""
    scheduler = Scheduler()
    events = setup_db['events']
    rooms = setup_db['rooms']

    # Make sure both sessions are in the same room and time overlaps
    session1 = events[0].session
    session2 = events[1].session

    session1.start_time = time(9, 0)
    session1.end_time = time(10, 0)
    session1.room_id = rooms[0].id
    session1.event.status = 'approved'

    session2.start_time = time(9, 30)  # overlapping
    session2.end_time = time(10, 30)
    session2.room_id = rooms[0].id
    session2.event.status = 'draft'

    db.session.commit()

    # Attempt to approve session2, which conflicts with session1
    data = {
        'start_time': session2.start_time.strftime("%H:%M"),
        'end_time': session2.end_time.strftime("%H:%M"),
        'status': 'approved'
    }

    response = admin_client.post(
        f'/admin/sessions/update/{session2.id}',
        data=data,
        follow_redirects=True
    )

    # Should flash error message about conflicts
    assert response.status_code == 200
    assert b"Cannot approve: conflicts with approved session" in response.data

    # Status of session2 should remain 'draft'
    updated = Session.query.get(session2.id)
    assert updated.event.status == 'draft'


def test_delete_session(admin_client, setup_db):
    """Admin can delete a session."""
    session = setup_db['events'][0].session
    response = admin_client.post(
        f'/admin/sessions/delete/{session.id}', follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Session deleted successfully" in response.data
    assert Session.query.get(session.id) is None


# -----------------------
# Extra tests for parse_time
# -----------------------
def test_parse_time_valid_formats():
    assert parse_time("09:30") == time(9, 30)
    assert parse_time("14:45:00") == time(14, 45, 0)


def test_parse_time_empty_or_none():
    assert parse_time("") is None
    assert parse_time(None) is None
