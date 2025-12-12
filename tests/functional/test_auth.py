"""
Functional tests for website/auth.py
Tests all route handlers with Flask test client
"""
import pytest
from website import oauth_client
from authlib.integrations.base_client.errors import MismatchingStateError


class TestAuthPages:

    def test_register_page(self, client):
        # GIVEN: A Flask test client
        # WHEN: GET request to /register
        response = client.get("/register")
        
        # THEN: Page loads with register content
        assert response.status_code == 200
        assert b"Register" in response.data

    def test_login_page(self, client):
        # GIVEN: A Flask test client
        # WHEN: GET request to /login
        response = client.get("/login")
        
        # THEN: Page loads with login content
        assert response.status_code == 200
        assert b"Log in" in response.data


class TestManualLogin:

    def test_invalid_login_wrong_password(self, client, app):
        # GIVEN: An existing user with a password
        from website.models import User, db
        
        with app.app_context():
            existing = User.query.filter_by(email="professor@colby.edu").first()
            if not existing:
                user = User(
                    name="Professor",
                    email="professor@colby.edu",
                    role="faculty"
                )
                user.set_password("correctpassword")
                db.session.add(user)
                db.session.commit()
        
        # WHEN: Login attempted with wrong password
        response = client.post("/api/v1/login", data={
            "email": "professor@colby.edu",
            "password": "wrongpassword"
        })
        
        # THEN: Login fails with error message
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_invalid_login_nonexistent_user(self, client):
        # GIVEN: A Flask test client
        # WHEN: Login attempted with non-existent email
        response = client.post("/api/v1/login", data={
            "email": "nonexistent@colby.edu",
            "password": "password"
        })
        
        # THEN: Login fails with error message
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_valid_login_success(self, client, app):
        # GIVEN: A user with valid credentials
        from website.models import User, db
        
        with app.app_context():
            User.query.filter_by(email="testuser@colby.edu").delete()
            db.session.commit()
            
            user = User(
                name="Test User",
                email="testuser@colby.edu",
                role="faculty"
            )
            user.set_password("testpassword123")
            db.session.add(user)
            db.session.commit()
        
        # WHEN: Login attempted with correct credentials
        response = client.post("/api/v1/login", data={
            "email": "testuser@colby.edu",
            "password": "testpassword123"
        })
        
        # THEN: Login succeeds and home page loads
        assert response.status_code == 200
        assert b"Welcome, Test User!" in response.data or b"CLAS" in response.data

    def test_disabled_manual_register(self, client):
        # GIVEN: A Flask test client
        # WHEN: Registration attempted via POST
        response = client.post("/api/v1/register", data={
            "email": "user@colby.edu",
            "password": "password"
        })
        
        # THEN: Registration is disabled with error message
        assert response.status_code == 200
        assert b"Manual registration is disabled" in response.data


class TestGoogleOAuth:

    def test_login_google_redirect_success(self, google_client):
        # GIVEN: A mocked Google OAuth client
        # WHEN: GET request to /login/google
        response = google_client.get("/login/google")
        
        # THEN: Redirects to Google OAuth
        assert response.data == b"mock_redirect"

    def test_login_google_exception_handling(self, client, monkeypatch):
        # GIVEN: Google OAuth service is unavailable
        def mock_authorize_redirect(_):
            raise Exception("OAuth service unavailable")
        
        monkeypatch.setattr(oauth_client.google, "authorize_redirect", mock_authorize_redirect)
        
        # WHEN: GET request to /login/google
        response = client.get("/login/google")
        
        # THEN: Returns 500 error with message
        assert response.status_code == 500
        assert b"Error during Google login" in response.data


class TestGoogleAuthorize:

    def test_authorize_google_error_parameter(self, client):
        # GIVEN: A Flask test client
        # WHEN: OAuth callback with error parameter
        response = client.get("/authorize/google?error=access_denied")
        
        # THEN: Shows error message on login page
        assert response.status_code == 200
        assert b"Google login was denied" in response.data

    def test_authorize_google_mismatching_state(self, app, monkeypatch):
        # GIVEN: OAuth state mismatch error
        class MockFlow:
            def authorize_access_token(self):
                raise MismatchingStateError()

        monkeypatch.setattr(oauth_client, "google", MockFlow())

        # WHEN: GET request to /authorize/google
        with app.test_client() as client:
            response = client.get("/authorize/google", follow_redirects=False)
            
            # THEN: Redirects back to login
            assert response.status_code == 302
            assert response.headers["Location"].endswith("/login/google")

    def test_authorize_google_new_user_success(self, google_client):
        # GIVEN: A mocked Google OAuth client
        # WHEN: OAuth callback for new user
        response = google_client.get("/authorize/google", follow_redirects=True)
        
        # THEN: User is created and redirected to home
        assert response.status_code == 200
        assert b"home" in response.data.lower() or b"Home" in response.data

    def test_authorize_google_unauthorized_non_colby(self, app, google_client):
        # GIVEN: Non-Colby email from Google OAuth
        class MockResponse:
            def json(self):
                return {
                    "email": "student@gmail.com",
                    "name": "Student User",
                    "picture": "pic.jpg"
                }

        oauth_client.google.get = lambda endpoint: MockResponse()
        oauth_client.google.authorize_access_token = lambda: {"access_token": "mock_token"}

        # WHEN: OAuth callback with non-Colby email
        resp = google_client.get("/authorize/google")
        
        # THEN: Access is denied
        assert resp.status_code == 200
        assert b"Only verified Colby faculty/admin can log in" in resp.data

    def test_authorize_google_unauthorized_student_email(self, app, google_client):
        # GIVEN: Colby student email (with numbers) from Google OAuth
        class MockResponse:
            def json(self):
                return {
                    "email": "student123@colby.edu",
                    "name": "Student User",
                    "picture": "pic.jpg"
                }

        oauth_client.google.get = lambda endpoint: MockResponse()
        oauth_client.google.authorize_access_token = lambda: {"access_token": "mock_token"}

        # WHEN: OAuth callback with student email
        resp = google_client.get("/authorize/google")
        
        # THEN: Access is denied
        assert resp.status_code == 200
        assert b"Only verified Colby faculty/admin can log in" in resp.data

    def test_authorize_google_existing_user_role_update(self, app, google_client):
        # GIVEN: Existing user with incorrect role
        from website.models import User, db
        
        class MockResponse:
            def json(self):
                return {
                    "email": "professor@colby.edu",
                    "name": "Professor Name",
                    "picture": "new_pic.jpg"
                }
        
        oauth_client.google.get = lambda endpoint: MockResponse()
        oauth_client.google.authorize_access_token = lambda: {"access_token": "mock"}
        
        with app.app_context():
            existing_user = User.query.filter_by(email="professor@colby.edu").first()
            if not existing_user:
                existing_user = User(
                    name="Old Name",
                    email="professor@colby.edu",
                    role="admin"
                )
                db.session.add(existing_user)
                db.session.commit()
            else:
                existing_user.role = "admin"
                db.session.commit()
        
        # WHEN: OAuth callback for existing user
        response = google_client.get("/authorize/google", follow_redirects=True)
        
        # THEN: User role is updated to correct value
        assert response.status_code == 200
        with app.app_context():
            user = User.query.filter_by(email="professor@colby.edu").first()
            assert user is not None
            assert user.role == "faculty"

    def test_authorize_google_admin_email(self, app, monkeypatch):
        # GIVEN: Admin email in ADMIN_EMAILS config
        from website.models import User, db
        
        class MockResponse:
            def json(self):
                return {
                    "email": "admin@colby.edu",
                    "name": "Admin User",
                    "picture": "admin_pic.jpg"
                }
        
        class MockGoogle:
            server_metadata = {"userinfo_endpoint": "mock_endpoint"}
            
            def authorize_access_token(self):
                return {"access_token": "mock_token"}
            
            def get(self, endpoint):
                return MockResponse()
        
        monkeypatch.setattr(oauth_client, "google", MockGoogle())
        
        class MockApp:
            config = {
                "ADMIN_EMAILS": ["admin@colby.edu"],
                "FACULTY_EMAILS": []
            }
            logger = app.logger
        
        with app.app_context():
            User.query.filter_by(email="admin@colby.edu").delete()
            db.session.commit()
        
        import website.auth
        original_app = website.auth.current_app
        website.auth.current_app = MockApp()
        
        # WHEN: OAuth callback for admin email
        try:
            with app.test_client() as client:
                response = client.get("/authorize/google", follow_redirects=True)
                
                # THEN: User is created with admin role
                assert response.status_code == 200
                with app.app_context():
                    user = User.query.filter_by(email="admin@colby.edu").first()
                    assert user is not None
                    assert user.role == "admin"
        finally:
            website.auth.current_app = original_app

    def test_authorize_google_faculty_from_config(self, app, monkeypatch):
        # GIVEN: Faculty email in FACULTY_EMAILS config
        from website.models import User, db
        
        class MockResponse:
            def json(self):
                return {
                    "email": "special@colby.edu",
                    "name": "Special Faculty",
                    "picture": "pic.jpg"
                }
        
        class MockGoogle:
            server_metadata = {"userinfo_endpoint": "mock_endpoint"}
            
            def authorize_access_token(self):
                return {"access_token": "mock_token"}
            
            def get(self, endpoint):
                return MockResponse()
        
        monkeypatch.setattr(oauth_client, "google", MockGoogle())
        
        class MockApp:
            config = {
                "ADMIN_EMAILS": [],
                "FACULTY_EMAILS": ["special@colby.edu"]
            }
            logger = app.logger
        
        with app.app_context():
            User.query.filter_by(email="special@colby.edu").delete()
            db.session.commit()
        
        import website.auth
        original_app = website.auth.current_app
        website.auth.current_app = MockApp()
        
        # WHEN: OAuth callback for faculty email
        try:
            with app.test_client() as client:
                response = client.get("/authorize/google", follow_redirects=True)
                
                # THEN: User is created with faculty role
                assert response.status_code == 200
                with app.app_context():
                    user = User.query.filter_by(email="special@colby.edu").first()
                    assert user is not None
                    assert user.role == "faculty"
        finally:
            website.auth.current_app = original_app


class TestLogout:

    def test_logout_get_request(self, admin_client):
        # GIVEN: An authenticated admin user
        # WHEN: GET request to /logout
        response = admin_client.get("/logout", follow_redirects=True)
        
        # THEN: User is logged out and redirected
        assert response.status_code == 200
        assert (
            b"You have been logged out" in response.data
            or b"Home" in response.data
            or b"Welcome" in response.data
        )

    def test_logout_post_request(self, admin_client):
        # GIVEN: An authenticated admin user
        # WHEN: POST request to /logout
        response = admin_client.post("/logout", follow_redirects=True)
        
        # THEN: User is logged out and redirected
        assert response.status_code == 200
        assert (
            b"You have been logged out" in response.data
            or b"Home" in response.data
            or b"Welcome" in response.data
        )

    def test_logout_requires_authentication(self, client):
        # GIVEN: An unauthenticated user
        # WHEN: GET request to /logout
        response = client.get("/logout", follow_redirects=False)
        
        # THEN: User is redirected to login
        assert response.status_code == 302 or response.status_code == 401