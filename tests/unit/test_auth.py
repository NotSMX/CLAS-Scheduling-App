import pytest
from website.auth import get_role_from_email, oauth_client, MismatchingStateError
from website import oauth_client
from website.models import User, db

def test_get_role_from_email(app):
    assert get_role_from_email("admin@colby.edu") == "admin"
    assert get_role_from_email("prof@colby.edu") == "faculty"
    assert get_role_from_email("email@gmail.com") is None

def test_get_role_from_email_new(monkeypatch):
    class DummyAppConfig:
        config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
    monkeypatch.setattr("website.auth.current_app", DummyAppConfig)
    assert get_role_from_email("john123@colby.edu") is None
    assert get_role_from_email("jane4@colby.edu") is None

def test_login_google_exception(client, monkeypatch):
    def mock_authorize_redirect(_):
        raise Exception("Something went wrong")
    monkeypatch.setattr(oauth_client.google, "authorize_redirect", mock_authorize_redirect)
    response = client.get("/login/google")
    assert response.status_code == 500
    assert b"Error during Google login" in response.data

def test_google_new_user_login(app):
    class MockFlow:
        def authorize_access_token(self):
            return {"access_token": "mock"}

        @property
        def server_metadata(self):
            return {"userinfo_endpoint": "mock_endpoint"}

        def get(self, url):
            class MockResponse:
                def json(self):
                    return {
                        "email": "admin@colby.edu",
                        "name": "Admin User",
                        "picture": "https://example.com/pic.jpg"
                    }
            return MockResponse()

    oauth_client.google = MockFlow()

    with app.app_context():
        User.query.delete()
        db.session.commit()

        with app.test_client() as client:
            resp = client.get("/authorize/google", follow_redirects=False)

            assert resp.status_code == 302

            user = User.query.filter_by(email="admin@colby.edu").first()
            assert user is not None
            assert user.name == "Admin User"
            assert user.role == "admin"
            assert user.profile_pic_url == "https://example.com/pic.jpg"

            with client.session_transaction() as sess:
                assert "_user_id" in sess
                assert sess["_user_id"] == str(user.id)

def test_authorize_google_mismatch(app, monkeypatch):
    class MockFlow:
        def authorize_access_token(self):
            raise MismatchingStateError()

    monkeypatch.setattr(oauth_client, "google", MockFlow())

    with app.test_client() as client:
        response = client.get("/authorize/google", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login/google")