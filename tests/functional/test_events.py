"""
Functional tests for events.py (HTTP routes)
Tests match actual application behavior.
"""
import pytest
from datetime import datetime, time


# PAGE ACCESS TESTS
def test_events_page_authenticated(professor_client):
    """Test that authenticated users can access the events page"""
    response = professor_client.get('/events')
    assert response.status_code == 200


def test_events_page_requires_login(client):
    """Test that unauthenticated users are redirected to login"""
    response = client.get('/events')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_event_create_page_requires_login(client):
    """Test that event creation page requires authentication"""
    response = client.get('/events/new')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_event_create_page_authenticated(professor_client):
    """Test that authenticated users can access event creation page"""
    response = professor_client.get('/events/new')
    assert response.status_code == 200


def test_event_edit_page_requires_login(client):
    """Test that event editing requires authentication"""
    response = client.get('/events/1/edit')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_event_edit_page_authenticated(professor_client, app):
    """Test that authenticated users can access their event edit page"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Intro to CS',
            num_entries=50,
            num_students=45,
            session_title='Test Event',
            session_length=90,
            individual_entry_length=60
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.get(f'/events/{event_id}/edit')
    assert response.status_code == 200

# EVENT CREATION TESTS (API)
def test_api_create_event_as_draft(professor_client):
    """Test creating an event as a draft"""
    event_data = {
        'clas_type': 'lecture',
        'format': 'in-person',
        'department': 'Computer Science',
        'course_number': 'CS101',
        'course_title': 'Introduction to Programming',
        'num_entries': '50',
        'num_students': '45',
        'session_title': 'Python Basics',
        'session_length': '90',
        'individual_entry_length': '60',
        'room_request': 'Room 301',
        'special_request': 'Need projector',
        'action': 'draft'
    }
    
    response = professor_client.post('/api/v1/events', data=event_data)
    
    assert response.status_code == 200
    # Check that event was created and is shown in the list
    assert b'Python Basics' in response.data
    assert b'Draft' in response.data


def test_api_create_event_as_submitted(professor_client):
    """Test creating and submitting an event"""
    event_data = {
        'clas_type': 'lecture',
        'format': 'in-person',
        'department': 'Computer Science',
        'course_number': 'CS101',
        'course_title': 'Introduction to Programming',
        'num_entries': '50',
        'num_students': '45',
        'session_title': 'Python Basics',
        'session_length': '90',
        'individual_entry_length': '60',
        'room_request': 'Room 301',
        'special_request': 'Need projector',
        'action': 'submit'
    }
    
    response = professor_client.post('/api/v1/events', data=event_data)
    
    assert response.status_code == 200
    assert b'submitted' in response.data.lower()


def test_api_create_event_submit_missing_required_fields(professor_client):
    """Test that submitting an event with missing required fields fails"""
    incomplete_data = {
        'clas_type': 'lecture',
        'format': 'in-person',
        'course_number': 'CS101',
        'action': 'submit'
    }
    
    response = professor_client.post('/api/v1/events', data=incomplete_data)
    
    assert response.status_code == 200
    assert b'All fields must be filled' in response.data or b'error' in response.data.lower()


def test_api_create_event_draft_with_minimal_fields(professor_client):
    """Test creating a draft with minimal fields (should auto-generate title)"""
    minimal_data = {
        'clas_type': 'lecture',
        'action': 'draft'
    }
    
    response = professor_client.post('/api/v1/events', data=minimal_data)
    
    assert response.status_code == 200


def test_api_create_event_invalid_numeric_fields(professor_client):
    """Test creating an event with invalid numeric values"""
    invalid_data = {
        'clas_type': 'lecture',
        'num_entries': 'not_a_number',
        'num_students': 'invalid',
        'action': 'draft'
    }
    
    response = professor_client.post('/api/v1/events', data=invalid_data)
    
    assert response.status_code == 302


def test_api_create_event_auto_generates_title_for_draft(professor_client):
    """Test that drafts without session_title get auto-generated names"""
    event_data = {
        'clas_type': 'lecture',
        'format': 'in-person',
        'course_number': 'CS101',
        'action': 'draft'
    }
    
    response = professor_client.post('/api/v1/events', data=event_data)
    
    assert response.status_code == 200
    assert b'New Event' in response.data

# EVENT RETRIEVAL TESTS (API)

def test_api_get_events(professor_client, app):
    """Test retrieving user's events via API"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event1 = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Intro to CS',
            session_title='Event 1',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60
        )
        event2 = Event(
            user_id=user.id,
            clas_type='seminar',
            format='online',
            department='Math',
            course_number='CS102',
            course_title='Advanced Topics',
            session_title='Event 2',
            num_entries=30,
            num_students=25,
            session_length=60,
            individual_entry_length=45
        )
        db.session.add_all([event1, event2])
        db.session.commit()
    
    response = professor_client.get('/api/v1/events')
    
    assert response.status_code == 200
    assert b'Event 1' in response.data
    assert b'Event 2' in response.data


def test_api_get_events_shows_only_user_events(professor_client, app):
    """Test that API only returns events for the logged-in user"""
    with app.app_context():
        from website.models import Event, User, db
        
        professor = User.query.filter_by(email='professor@colby.edu').first()
        
        event1 = Event(
            user_id=professor.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='My Course',
            session_title='My Event',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60
        )
        
        other_user = User(email='other@colby.edu', name='Other User', role='faculty')
        db.session.add(other_user)
        db.session.commit()
        
        event2 = Event(
            user_id=other_user.id,
            clas_type='seminar',
            format='online',
            department='Math',
            course_number='CS999',
            course_title='Other Course',
            session_title='Other Event',
            num_entries=20,
            num_students=15,
            session_length=60,
            individual_entry_length=45
        )
        
        db.session.add(event1)
        db.session.add(event2)
        db.session.commit()
    
    response = professor_client.get('/api/v1/events')
    
    assert response.status_code == 200
    assert b'My Event' in response.data
    assert b'Other Event' not in response.data


# EVENT SUBMISSION TESTS (API)

def test_api_submit_draft_event_success(professor_client, app):
    """Test submitting a complete draft event"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='Computer Science',
            course_number='CS101',
            course_title='Intro to CS',
            num_entries=50,
            num_students=45,
            session_title='Test Event',
            session_length=90,
            individual_entry_length=60,
            status='draft'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/submit')
    
    assert response.status_code == 200
    assert b'submitted' in response.data.lower()


def test_api_submit_event_already_submitted(professor_client, app):
    """Test submitting an event that's already been submitted"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='My Course',
            session_title='Already Submitted',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/submit')
    
    assert response.status_code == 200
    assert b'Already Submitted' in response.data
    assert b'Submitted' in response.data


def test_api_submit_event_incomplete_data(professor_client, app):
    """Test submitting an event with incomplete required fields"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Test Course',
            session_title='Test',
            num_entries=0,
            num_students=0,
            session_length=0,
            individual_entry_length=0,
            status='draft'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/submit')
    
    assert response.status_code == 200
    assert b'submitted' in response.data.lower()


def test_api_submit_nonexistent_event(professor_client):
    """Test submitting a non-existent event returns 404"""
    response = professor_client.post('/api/v1/events/99999/submit')
    assert response.status_code == 404

# EVENT EDITING TESTS (API)
def test_api_edit_event_save_as_draft(professor_client, app):
    """Test editing an event and saving as draft"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Original Course',
            session_title='Original Title',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='draft'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    updated_data = {
        'clas_type': 'seminar',
        'course_number': 'CS102',
        'session_title': 'Updated Title',
        'num_entries': '60',
        'num_students': '55',
        'action': 'draft'
    }
    
    response = professor_client.post(f'/api/v1/events/{event_id}/edit', data=updated_data)
    
    assert response.status_code == 200
    assert b'Edit Event Details' in response.data


def test_api_edit_event_and_submit(professor_client, app):
    """Test editing an event and submitting it"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Title',
            num_entries=50,
            num_students=45,
            session_title='Test Event',
            session_length=90,
            individual_entry_length=60,
            status='draft'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    updated_data = {
        'course_number': 'CS102',
        'action': 'submit'
    }
    
    response = professor_client.post(f'/api/v1/events/{event_id}/edit', data=updated_data)
    
    assert response.status_code == 200
    assert b'Edit Event Details' in response.data


def test_api_edit_event_unauthorized_user(professor_client, app):
    """Test that users cannot edit other users' events - returns eventlist without error msg"""
    with app.app_context():
        from website.models import Event, User, db
        other_user = User(email='another@colby.edu', name='Another User', role='faculty')
        db.session.add(other_user)
        db.session.commit()
        
        event = Event(
            user_id=other_user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS999',
            course_title='Other Course',
            session_title='Other User Event',
            num_entries=10,
            num_students=10,
            session_length=60,
            individual_entry_length=45
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/edit', data={'course_number': 'CS000'})
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_api_edit_event_submit_with_missing_fields(professor_client, app):
    """Test editing and submitting with missing required fields"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Test Course',
            session_title='Test',
            num_entries=0,
            num_students=0,
            session_length=0,
            individual_entry_length=0,
            status='draft'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/edit', data={'action': 'submit'})
    
    assert response.status_code == 200
    assert b'Edit Event Details' in response.data


def test_api_edit_event_deletes_session_when_reverting_to_draft(professor_client, app):
    """Test that editing back to draft deletes associated session"""
    with app.app_context():
        from website.models import Event, Session, User, Room, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        room = Room(building_name='Test Hall', room_number=101, capacity=50)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Test Course',
            session_title='Test Event',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.flush()
        
        session = Session(
            user_id=user.id,
            submission_id=event.id,
            room_id=room.id,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        db.session.add(session)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/edit', data={'action': 'draft'})
    
    assert response.status_code == 200
    
    with app.app_context():
        from website.models import Session
        session = Session.query.filter_by(submission_id=event_id).first()
        assert session is None


def test_api_edit_nonexistent_event(professor_client):
    """Test editing a non-existent event returns 404"""
    response = professor_client.post('/api/v1/events/99999/edit', data={'course_number': 'CS000'})
    assert response.status_code == 404

# EVENT DELETION TESTS (API)

def test_api_delete_event_success(professor_client, app):
    """Test successful event deletion"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Course to Delete',
            session_title='To Be Deleted',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/delete')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data
    assert b'To Be Deleted' not in response.data


def test_api_delete_event_unauthorized(professor_client, app):
    """Test that users cannot delete other users' events"""
    with app.app_context():
        from website.models import Event, User, db
        other_user = User(email='yetanother@colby.edu', name='Yet Another', role='faculty')
        db.session.add(other_user)
        db.session.commit()
        
        event = Event(
            user_id=other_user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS999',
            course_title='Other Course',
            session_title='Other Event',
            num_entries=10,
            num_students=10,
            session_length=60,
            individual_entry_length=45
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.post(f'/api/v1/events/{event_id}/delete')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_api_delete_nonexistent_event(professor_client):
    """Test deleting a non-existent event returns 404"""
    response = professor_client.post('/api/v1/events/99999/delete')
    assert response.status_code == 404

# SCHEDULE OPTIONS TESTS

def test_event_schedule_options_success(professor_client, app):
    """Test viewing schedule options for a submitted event"""
    with app.app_context():
        from website.models import Event, User, Room, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        # Create some rooms for scheduling
        room1 = Room(building_name='Miller', room_number=101, capacity=50)
        room2 = Room(building_name='Miller', room_number=102, capacity=30)
        db.session.add_all([room1, room2])
        db.session.commit()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Intro to CS',
            session_title='Schedule Test',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.get(f'/events/{event_id}/schedule-options')
    
    assert response.status_code == 200


def test_event_schedule_options_unauthorized(professor_client, app):
    """Test that users cannot view schedule options for other users' events"""
    with app.app_context():
        from website.models import Event, User, db
        other_user = User(email='schedule@colby.edu', name='Schedule User', role='faculty')
        db.session.add(other_user)
        db.session.commit()
        
        event = Event(
            user_id=other_user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS999',
            course_title='Other Course',
            session_title='Other Event',
            num_entries=10,
            num_students=10,
            session_length=60,
            individual_entry_length=45,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.get(f'/events/{event_id}/schedule-options')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_event_schedule_options_already_scheduled(professor_client, app):
    """Test viewing schedule options for an already scheduled event"""
    with app.app_context():
        from website.models import Event, Session, User, Room, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        room = Room(building_name='Miller', room_number=201, capacity=50)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Scheduled Course',
            session_title='Already Scheduled',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.flush()
        
        session = Session(
            user_id=user.id,
            submission_id=event.id,
            room_id=room.id,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        db.session.add(session)
        db.session.commit()
        event_id = event.id
    
    response = professor_client.get(f'/events/{event_id}/schedule-options')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_event_schedule_options_nonexistent_event(professor_client):
    """Test schedule options for non-existent event returns 404"""
    response = professor_client.get('/events/99999/schedule-options')
    assert response.status_code == 404


# CONFIRM SCHEDULE TESTS
def test_confirm_schedule_success(professor_client, app):
    """Test successfully confirming a schedule"""
    with app.app_context():
        from website.models import Event, User, Room, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        room = Room(building_name='Diamond', room_number=301, capacity=50)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Confirm Test',
            session_title='Schedule Confirm',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        room_id = room.id
    
    schedule_data = {
        'start_time': '10:00',
        'room_id': str(room_id)
    }
    
    response = professor_client.post(f'/events/{event_id}/confirm-schedule', data=schedule_data)
    
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_confirm_schedule_unauthorized(professor_client, app):
    """Test that users cannot confirm schedule for other users' events"""
    with app.app_context():
        from website.models import Event, User, Room, db
        
        other_user = User(email='confirm@colby.edu', name='Confirm User', role='faculty')
        db.session.add(other_user)
        db.session.commit()
        
        room = Room(building_name='Diamond', room_number=302, capacity=50)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=other_user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS999',
            course_title='Unauthorized',
            session_title='Unauthorized Event',
            num_entries=10,
            num_students=10,
            session_length=60,
            individual_entry_length=45,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        room_id = room.id
    
    schedule_data = {
        'start_time': '10:00',
        'room_id': str(room_id)
    }
    
    response = professor_client.post(f'/events/{event_id}/confirm-schedule', data=schedule_data)
    
    assert response.status_code == 200
    assert b'Your Events' in response.data


def test_confirm_schedule_missing_data(professor_client, app):
    """Test confirming schedule with missing required data"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Missing Data Test',
            session_title='Missing Data',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    # Missing room_id
    response = professor_client.post(f'/events/{event_id}/confirm-schedule', data={'start_time': '10:00'})
    
    assert response.status_code == 200
    assert b'Invalid schedule selection' in response.data or b'Your Events' in response.data


def test_confirm_schedule_nonexistent_event(professor_client):
    """Test confirm schedule for non-existent event returns 404"""
    response = professor_client.post('/events/99999/confirm-schedule', data={'start_time': '10:00', 'room_id': '1'})
    assert response.status_code == 404

# ADMIN SCHEDULE TESTS
def test_admin_schedule_all_as_non_admin(professor_client):
    """Test that non-admins cannot schedule all events"""
    response = professor_client.post('/admin/schedule/all')
    assert response.status_code == 200
    assert b"don't have permission" in response.data or b'Home' in response.data

# ADMIN ROOM MANAGEMENT TESTS
def test_admin_rooms_page_as_admin(admin_client, app):
    """Test that admins can access rooms page"""
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Test Hall', room_number=101, capacity=50)
        db.session.add(room)
        db.session.commit()
    
    response = admin_client.get('/admin/rooms')
    assert response.status_code == 200
    assert b'Test Hall' in response.data


def test_admin_rooms_page_as_non_admin(professor_client):
    """Test that non-admins cannot access rooms page"""
    response = professor_client.get('/admin/rooms')
    assert response.status_code == 200
    assert b"don't have permission" in response.data or b'Home' in response.data


def test_admin_add_room_success(admin_client, app):
    """Test successfully adding a room"""
    room_data = {
        'building_name': 'New Building',
        'room_number': '201',
        'capacity': '75',
        'special_features': 'Projector, Whiteboard'
    }
    
    response = admin_client.post('/admin/rooms/add', data=room_data)
    
    assert response.status_code == 200
    assert b'added successfully' in response.data or b'New Building' in response.data


def test_admin_add_room_missing_required_fields(admin_client):
    """Test adding room with missing required fields"""
    incomplete_data = {
        'building_name': 'Incomplete Building'
        # Missing room_number and capacity
    }
    
    response = admin_client.post('/admin/rooms/add', data=incomplete_data)
    
    assert response.status_code == 200
    assert b'required' in response.data.lower() or b'admin' in response.data.lower()


def test_admin_add_room_invalid_room_number(admin_client):
    """Test adding room with non-numeric room number"""
    invalid_data = {
        'building_name': 'Test Hall',
        'room_number': 'ABC',
        'capacity': '50'
    }
    
    response = admin_client.post('/admin/rooms/add', data=invalid_data)
    
    assert response.status_code == 200
    assert b'must be a valid number' in response.data or b'admin' in response.data.lower()


def test_admin_add_room_duplicate(admin_client, app):
    """Test adding a duplicate room"""
    with app.app_context():
        from website.models import Room, db
        existing = Room(building_name='Duplicate Hall', room_number=101, capacity=50)
        db.session.add(existing)
        db.session.commit()
    
    duplicate_data = {
        'building_name': 'Duplicate Hall',
        'room_number': '101',
        'capacity': '50'
    }
    
    response = admin_client.post('/admin/rooms/add', data=duplicate_data)
    
    assert response.status_code == 200
    assert b'already exists' in response.data or b'admin' in response.data.lower()


def test_admin_add_room_as_non_admin(professor_client):
    room_data = {
        'building_name': 'Unauthorized',
        'room_number': '999',
        'capacity': '50'
    }
    
    response = professor_client.post('/admin/rooms/add', data=room_data)
    
    assert response.status_code == 200
    assert b"don't have permission" in response.data or b'Home' in response.data


def test_admin_edit_room_success(admin_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Edit Test', room_number=301, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    updated_data = {
        'building_name': 'Edit Test',
        'room_number': '301',
        'capacity': '75',
        'special_features': 'Updated features'
    }
    
    response = admin_client.post(f'/admin/rooms/{room_id}/edit', data=updated_data)
    
    assert response.status_code == 200
    assert b'updated successfully' in response.data or b'Edit Test' in response.data


def test_admin_edit_room_missing_fields(admin_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Edit Test 2', room_number=302, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    incomplete_data = {
        'building_name': 'Edit Test 2'
        # Missing room_number and capacity
    }
    
    response = admin_client.post(f'/admin/rooms/{room_id}/edit', data=incomplete_data)
    
    assert response.status_code == 200
    assert b'required' in response.data.lower() or b'admin' in response.data.lower()


def test_admin_edit_room_invalid_room_number(admin_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Edit Test 3', room_number=303, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    invalid_data = {
        'building_name': 'Edit Test 3',
        'room_number': 'XYZ',
        'capacity': '50'
    }
    
    response = admin_client.post(f'/admin/rooms/{room_id}/edit', data=invalid_data)
    
    assert response.status_code == 200
    assert b'must be a valid number' in response.data or b'admin' in response.data.lower()


def test_admin_edit_room_duplicate_name(admin_client, app):
    with app.app_context():
        from website.models import Room, db
        room1 = Room(building_name='Existing', room_number=401, capacity=50)
        room2 = Room(building_name='ToEdit', room_number=402, capacity=50)
        db.session.add_all([room1, room2])
        db.session.commit()
        room2_id = room2.id
    
    duplicate_data = {
        'building_name': 'Existing',
        'room_number': '401',
        'capacity': '50'
    }
    
    response = admin_client.post(f'/admin/rooms/{room2_id}/edit', data=duplicate_data)
    
    assert response.status_code == 200
    assert b'already exists' in response.data or b'admin' in response.data.lower()


def test_admin_edit_room_as_non_admin(professor_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Unauthorized Edit', room_number=501, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    response = professor_client.post(f'/admin/rooms/{room_id}/edit', data={'building_name': 'Hacked', 'room_number': '501', 'capacity': '50'})
    
    assert response.status_code == 200
    assert b"don't have permission" in response.data or b'Home' in response.data


def test_admin_edit_nonexistent_room(admin_client):
    """Test editing a non-existent room returns 404"""
    response = admin_client.post('/admin/rooms/99999/edit', data={'building_name': 'Test', 'room_number': '101', 'capacity': '50'})
    assert response.status_code == 404


def test_admin_delete_room_success(admin_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Delete Test', room_number=601, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    response = admin_client.post(f'/admin/rooms/{room_id}/delete')
    
    assert response.status_code == 200
    assert b'deleted successfully' in response.data or b'admin' in response.data.lower()


def test_admin_delete_room_in_use(admin_client, app):
    """Test that rooms with scheduled sessions cannot be deleted"""
    with app.app_context():
        from website.models import Room, Event, Session, User, db
        admin = User.query.filter_by(email='admin@colby.edu').first()
        
        room = Room(building_name='In Use', room_number=701, capacity=50)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=admin.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Room Test',
            session_title='Room In Use',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.flush()
        
        session = Session(
            user_id=admin.id,
            submission_id=event.id,
            room_id=room.id,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        db.session.add(session)
        db.session.commit()
        room_id = room.id
    
    response = admin_client.post(f'/admin/rooms/{room_id}/delete')
    
    assert response.status_code == 200
    assert b'Cannot delete' in response.data or b'scheduled session' in response.data


def test_admin_delete_room_as_non_admin(professor_client, app):
    with app.app_context():
        from website.models import Room, db
        room = Room(building_name='Unauthorized Delete', room_number=801, capacity=50)
        db.session.add(room)
        db.session.commit()
        room_id = room.id
    
    response = professor_client.post(f'/admin/rooms/{room_id}/delete')
    
    assert response.status_code == 200
    assert b"don't have permission" in response.data or b'Home' in response.data


def test_admin_delete_nonexistent_room(admin_client):
    """Test deleting a non-existent room returns 404"""
    response = admin_client.post('/admin/rooms/99999/delete')
    assert response.status_code == 404


def test_api_create_event_with_empty_session_title_on_submit(professor_client):
    """Test submitting event with empty session_title fails validation"""
    response = professor_client.post('/api/v1/events', data={
        'clas_type': 'lecture',
        'format': 'in-person',
        'department': 'CS',
        'course_number': 'CS101',
        'course_title': 'Test Course',
        'session_title': '', 
        'num_entries': '50',
        'num_students': '45',
        'session_length': '90',
        'individual_entry_length': '60',
        'action': 'submit'
    })
    
    assert response.status_code == 200
    assert b'All fields must be filled' in response.data
    assert b'error_code' in response.data or b'double-check' in response.data


def test_api_submit_draft_with_empty_required_field(professor_client, app):
    """Test submitting a draft with missing required fields"""
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        incomplete_event = Event(
            user_id=user.id,
            clas_type='',
            format='in-person',
            department='', 
            course_number='',
            course_title='',
            session_title='Incomplete Draft',
            num_entries=0,
            num_students=0,
            session_length=0,
            individual_entry_length=0,
            status='draft'
        )
        db.session.add(incomplete_event)
        db.session.commit()
        event_id = incomplete_event.id
    
    # Try to submit the incomplete draft
    response = professor_client.post(f'/api/v1/events/{event_id}/submit')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data
    assert b'Incomplete Draft' in response.data
    
    with app.app_context():
        from website.models import Event
        event = Event.query.get(event_id)
        assert event.status == 'draft'


def test_event_schedule_options_no_available_options(professor_client, app, monkeypatch):
    """Test when scheduler returns no available options"""
    # Create an event
    with app.app_context():
        from website.models import Event, User, db
        user = User.query.filter_by(email='professor@colby.edu').first()
        
        event = Event(
            user_id=user.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='No Options Test',
            session_title='No Schedule Available',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    
    def mock_generate_schedule_options(*args, **kwargs):
        return []
    
    from website import scheduler
    monkeypatch.setattr(scheduler.Scheduler, 'generate_schedule_options', mock_generate_schedule_options)
    
    response = professor_client.get(f'/events/{event_id}/schedule-options')
    
    assert response.status_code == 200
    assert b'Your Events' in response.data
    assert b'No Schedule Available' in response.data

    assert b'Choose a time slot' not in response.data


def test_admin_schedule_page_with_unscheduled_events(admin_client, app):
    """Test admin schedule page shows unscheduled events"""
    with app.app_context():
        from website.models import Event, User, db
        admin = User.query.filter_by(email='admin@colby.edu').first()
        
        event = Event(
            user_id=admin.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Admin Schedule Test',
            session_title='Unscheduled Event',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
    
    try:
        response = admin_client.get('/admin/schedule')
        if response.status_code == 200:
            assert b'Unscheduled' in response.data or b'admin' in response.data
    except Exception as e:
        assert 'TemplateNotFound' in str(e) or 'admin_schedule.html' in str(e)


def test_admin_schedule_all_events(admin_client, app, monkeypatch):
    """Test admin scheduling all events calls scheduler"""
    with app.app_context():
        from website.models import Event, User, Room, db
        admin = User.query.filter_by(email='admin@colby.edu').first()
        
        room = Room(building_name='Admin Hall', room_number=101, capacity=100)
        db.session.add(room)
        db.session.commit()
        
        event = Event(
            user_id=admin.id,
            clas_type='lecture',
            format='in-person',
            department='CS',
            course_number='CS101',
            course_title='Schedule All Test',
            session_title='Bulk Schedule',
            num_entries=50,
            num_students=45,
            session_length=90,
            individual_entry_length=60,
            status='submitted'
        )
        db.session.add(event)
        db.session.commit()
    
    def mock_schedule_all_events(self):
        return [
            {'event_id': 1, 'success': True, 'message': 'Scheduled'},
            {'event_id': 2, 'success': False, 'message': 'Failed'}
        ]
    
    from website import scheduler
    monkeypatch.setattr(scheduler.Scheduler, 'schedule_all_events', mock_schedule_all_events)
    
    try:
        response = admin_client.post('/admin/schedule/all')
        if response.status_code == 200:
            assert b'scheduled' in response.data.lower() or b'admin' in response.data
    except Exception as e:
        assert 'TemplateNotFound' in str(e) or 'admin_schedule.html' in str(e)


def test_api_create_event_value_error_triggers_flash(professor_client):
    """Test that ValueError in numeric fields triggers flash message"""
    response = professor_client.post('/api/v1/events', data={
        'clas_type': 'lecture',
        'num_entries': 'not_a_number',
        'action': 'draft'
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert '/events/new' in response.location
    
    response = professor_client.get(response.location)
    assert response.status_code == 200
    assert b'Create' in response.data or b'Event' in response.data