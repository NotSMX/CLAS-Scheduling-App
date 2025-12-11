import pytest
from website import create_app
from website.models import User, Room, Event, Session, db
from datetime import time

@pytest.fixture
def app():
    app = create_app()

    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "testdev",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "ADMIN_EMAILS": ["admin@colby.edu"],
        "FACULTY_EMAILS": ["prof@colby.edu"],
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

class MockFlow:
    def authorize_redirect(self, redirect_uri):
        return "mock_redirect"

    def authorize_access_token(self):
        return {"access_token": "mock_token"}

    @property
    def server_metadata(self):
        return {"userinfo_endpoint": "mock_endpoint"}

    def get(self, endpoint):
        class MockResponse:
            def json(self):
                return {
                    "email": "admin@colby.edu",
                    "name": "Admin User",
                    "picture": "https://example.com/pic.jpg"
                }
        return MockResponse()

@pytest.fixture
def google_client(app):
    from website import oauth_client

    oauth_client.google = MockFlow()

    with app.app_context():
        with app.test_client() as test_client:
            yield test_client

@pytest.fixture
def setup_db(app):
    with app.app_context():
        db.create_all()

        user = User(email="test_sched@colby.edu", name="Test User", role="admin")
        db.session.add(user)
        db.session.commit()

        room1 = Room(building_name="Lovejoy", room_number=100, capacity=30)
        room2 = Room(building_name="Diamond", room_number=101, capacity=25)
        db.session.add_all([room1, room2])
        db.session.commit()

        # Events
        event1 = Event(
            user_id=user.id,
            clas_type="Lecture",
            format="In-person",
            department="CS",
            course_number="101",
            course_title="Intro to CS",
            session_title="Session 1",
            num_entries=10,
            num_students=20,
            session_length=60,
            individual_entry_length=15,
            status="submitted"
        )
        event2 = Event(
            user_id=user.id,
            clas_type="Seminar",
            format="Online",
            department="Math",
            course_number="201",
            course_title="Algebra",
            session_title="Session 2",
            num_entries=10,
            num_students=10,
            session_length=45,
            individual_entry_length=15,
            status="submitted"
        )

        db.session.add_all([event1, event2])
        db.session.commit()

        # Create Sessions for each Event
        session1 = Session(
            user_id=user.id,
            submission_id=event1.id,
            room_id=room1.id,
            start_time=time(9,0),
            end_time=time(10,0)
        )
        session2 = Session(
            user_id=user.id,
            submission_id=event2.id,
            room_id=room2.id,
            start_time=time(10,0),
            end_time=time(10,45)
        )
        db.session.add_all([session1, session2])
        db.session.commit()

        yield dict(user=user, rooms=[room1, room2], events=[event1, event2], sessions=[session1, session2])

        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_client(app):
    with app.app_context():
        user = User.query.filter_by(email="admin@colby.edu").first()
        if not user:
            user = User(email="admin@colby.edu", name="Test Admin", role="admin")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

        client = app.test_client()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

        yield client

@pytest.fixture
def professor_client(app):
    with app.app_context():
        user = User.query.filter_by(email="professor@colby.edu").first()
        if not user:
            user = User(email="professor@colby.edu", name="Test Professor", role="faculty")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

        client = app.test_client()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

        yield client