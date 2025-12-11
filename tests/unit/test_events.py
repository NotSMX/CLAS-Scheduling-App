import pytest

def test_event_page(professor_client):
    response = professor_client.get("/events")
    assert response.status_code == 200
    assert b"Your Events" in response.data

def test_new_event_page(professor_client):
    response = professor_client.get("/events/new")
    assert response.status_code == 200
    assert b"Create Event Details" in response.data

def test_submit_event(professor_client):
    response = professor_client.post(
        "/api/v1/events",
        data={
            "clas_type": "Lecture",
            "format": "In-person",
            "department": "CS",
            "course_number": "101",
            "course_title": "Intro to CS",
            "session_title": "Session 1",
            "num_entries": 30,
            "num_students": 25,
            "session_length": 60,
            "individual_entry_length": 15,
            "room_request": "Room 101",
            "special_request": "Projector",
            "action": "submit"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b'Session 1' in response.data
    assert b'submitted' in response.data.lower()