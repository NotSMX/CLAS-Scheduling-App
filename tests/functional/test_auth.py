import pytest
from website import oauth_client

def test_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Register" in response.data

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Log in" in response.data

def test_invalid_login(client):
    response = client.post("/api/v1/login", data={
        "email": "email@colby.edu",
        "password": "wrongpassword"
    })
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_disabled_register(client):
    response = client.post("/api/v1/register", data={
        "email": "user@colby.edu",
        "password": "password"
    })
    assert response.status_code == 200
    assert b"Manual registration is disabled" in response.data

def test_google_redirect(google_client):
    response = google_client.get("/login/google")
    assert response.data == b"mock_redirect"

def test_google_authorized(google_client):
    response = google_client.get("/authorize/google", follow_redirects=True)
    assert response.status_code == 200
    assert b"home" in response.data.lower() or b"Home" in response.data

def test_google_unauthorized(app, google_client):
    class MockResponse:
        def json(self):
            return {"email": "student@gmail.com", "name": "Student User"}

    oauth_client.google.get = lambda endpoint: MockResponse()
    oauth_client.google.authorize_access_token = lambda: {"access_token": "mock_token"}

    resp = google_client.get("/authorize/google")
    assert resp.status_code == 200
    assert b"Only verified Colby faculty/admin can log in" in resp.data

def test_logout(admin_client):
    response = admin_client.get("/logout", follow_redirects=True)

    assert response.status_code == 200

    assert (
        b"You have been logged out" in response.data
        or b"Home" in response.data
        or b"Welcome" in response.data
    )