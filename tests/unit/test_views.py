import io
import os
import pytest
from website.models import User, Session, Event, Room, db
from datetime import time

# ---- Test landing and home ----
def test_landing_redirect(client):
    rv = client.get("/")
    assert rv.status_code == 302
    assert "/home" in rv.location
    from datetime import time
from website.models import Event, Session, db

def test_home_page(client, setup_db):
    user = setup_db['user']
    room = setup_db['rooms'][0]

    # Add Closed and Family Friendly events
    event_closed = Event(
        user_id=user.id,
        clas_type="Lecture",
        format="Closed",
        department="History",
        course_number="101",
        course_title="History 101",
        session_title="Closed Session",
        num_entries=10,
        num_students=20,
        session_length=60,           # required
        individual_entry_length=15,  # required
        status="approved"
    )

    event_family = Event(
        user_id=user.id,
        clas_type="Lecture",
        format="In-person",
        department="Music",
        course_number="201",
        course_title="Music 201",
        session_title="Family Session",
        special_request="family",
        num_entries=10,
        num_students=20,
        session_length=60,           # required
        individual_entry_length=15,  # required
        status="approved"
    )

    db.session.add_all([event_closed, event_family])
    db.session.commit()

    # Create sessions for these events
    session_closed = Session(
        user_id=user.id,
        submission_id=event_closed.id,
        room_id=room.id,
        start_time=time(9, 0),
        end_time=time(10, 0)
    )
    session_family = Session(
        user_id=user.id,
        submission_id=event_family.id,
        room_id=room.id,
        start_time=time(10, 0),
        end_time=time(11, 0)
    )
    db.session.add_all([session_closed, session_family])
    db.session.commit()

    # Request /home
    rv = client.get("/home")
    assert rv.status_code == 200

    # All approved events appear
    all_events = setup_db['events'] + [event_closed, event_family]
    for event in all_events:
        if event.status == "approved":
            assert bytes(event.session_title, "utf-8") in rv.data


def test_schedule_page(client, setup_db):
    user = setup_db['user']
    room = setup_db['rooms'][0]

    # Add Closed and Family Friendly events
    event_closed = Event(
        user_id=user.id,
        clas_type="Lecture",
        format="Closed",
        department="History",
        course_number="101",
        course_title="History 101",
        session_title="Closed Session",
        num_entries=10,
        num_students=20,
        session_length=60,
        individual_entry_length=15,
        status="approved"
    )

    event_family = Event(
        user_id=user.id,
        clas_type="Lecture",
        format="In-person",
        department="Music",
        course_number="201",
        course_title="Music 201",
        session_title="Family Session",
        special_request="family",
        num_entries=10,
        num_students=20,
        session_length=60,
        individual_entry_length=15,
        status="approved"
    )

    db.session.add_all([event_closed, event_family])
    db.session.commit()

    # Create sessions
    session_closed = Session(
        user_id=user.id,
        submission_id=event_closed.id,
        room_id=room.id,
        start_time=time(9, 0),
        end_time=time(10, 0)
    )
    session_family = Session(
        user_id=user.id,
        submission_id=event_family.id,
        room_id=room.id,
        start_time=time(10, 0),
        end_time=time(11, 0)
    )

    db.session.add_all([session_closed, session_family])
    db.session.commit()

    rv = client.get("/schedule")
    assert rv.status_code == 200

    all_events = setup_db['events'] + [event_closed, event_family]
    for event in all_events:
        if event.status == "approved":
            assert bytes(event.session_title, "utf-8") in rv.data


# ---- Test profile & settings ----
def test_profile_requires_login(client):
    rv = client.get("/profile")
    assert rv.status_code == 302

def test_profile_page(admin_client):
    rv = admin_client.get("/profile")
    assert rv.status_code == 200
    assert b"Admin" in rv.data

def test_settings_page(admin_client):
    rv = admin_client.get("/settings")
    assert rv.status_code == 200
    assert b"Settings" in rv.data

# ---- Test admin redirect ----
def test_admin_redirect(admin_client):
    rv = admin_client.get("/admin")
    assert rv.status_code == 302
    assert "/admin/sessions" in rv.location  # match current app

# ---- API profile ----
def test_api_profile(admin_client):
    rv = admin_client.get("/api/v1/profile")
    assert rv.status_code == 200
    assert b"Admin" in rv.data

# ---- API settings: update name ----
def test_api_settings_name(admin_client):
    rv = admin_client.post("/api/v1/settings", data={"name": "New Name"})
    assert b"Settings updated successfully" in rv.data
    user = User.query.filter_by(email="admin@colby.edu").first()
    assert user.name == "New Name"

# ---- API settings: upload file ----
def test_api_settings_file_upload(admin_client, tmp_path):
    user = User.query.filter_by(email="admin@colby.edu").first()
    os.makedirs("static/uploads/profile_pics", exist_ok=True)
    old_path = "static/uploads/profile_pics/old.png"
    with open(old_path, "wb") as f:
        f.write(b"old pic")
    user.profile_pic_url = "/static/uploads/profile_pics/old.png"
    db.session.commit()

    file_path = tmp_path / "test.png"
    file_path.write_bytes(b"PNGDATA")
    with open(file_path, "rb") as f:
        data = {"profile_picture": (f, "test.png")}
        rv = admin_client.post("/api/v1/settings", data=data, content_type="multipart/form-data")
    assert b"Settings updated successfully" in rv.data


# ---- API settings: password validation ----
@pytest.mark.parametrize("password,error", [
    ("short", b"Password must be at least 8 characters."),
    ("alllowercase1!", b"Password must have at least one uppercase letter."),
    ("ALLUPPERCASE1!", b"Password must have at least one lowercase letter."),
    ("NoNumber!", b"Password must include at least one number."),
    ("NoSpecial1", b"Password must include at least one special character."),
    ("aaaaAAA111!!", b"Password must include more unique characters."),
])
def test_api_settings_password_validation(admin_client, password, error):
    rv = admin_client.post("/api/v1/settings", data={
        "new_password": password,
        "confirm_password": password
    })
    assert error in rv.data

def test_api_settings_successful_password(admin_client):
    rv = admin_client.post("/api/v1/settings", data={
        "new_password": "Valid1!Password",
        "confirm_password": "Valid1!Password"
    })
    assert b"Settings updated successfully" in rv.data
