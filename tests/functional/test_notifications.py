"""
Functional tests for website/notifications.py
Tests all route handlers with Flask test client
"""
import pytest
from website.models import Notification, db


class TestNotificationPages:

    def test_notifications_page(self, admin_client):
        # GIVEN: An authenticated admin user
        # WHEN: GET request to /notifications
        response = admin_client.get("/notifications")
        
        # THEN: Notifications page loads
        assert response.status_code == 200
        assert b"Notifications" in response.data

    def test_create_notification_page(self, admin_client):
        # GIVEN: An authenticated admin user
        # WHEN: GET request to /notifications/create
        response = admin_client.get("/notifications/create")
        
        # THEN: Create notification page loads
        assert response.status_code == 200
        assert b"Create Notification" in response.data

    def test_notifications_requires_authentication(self, client):
        # GIVEN: An unauthenticated user
        # WHEN: GET request to /notifications
        response = client.get("/notifications", follow_redirects=False)
        
        # THEN: User is redirected to login
        assert response.status_code == 302

    def test_create_notification_requires_authentication(self, client):
        # GIVEN: An unauthenticated user
        # WHEN: GET request to /notifications/create
        response = client.get("/notifications/create", follow_redirects=False)
        
        # THEN: User is redirected to login
        assert response.status_code == 302


class TestCreateNotification:

    def test_create_notification_success(self, admin_client, app):
        # GIVEN: Valid notification data
        data = {
            "title": "Test Notification",
            "message": "This is a test",
            "priority": "high",
            "deadline": "2030-01-01T12:00"
        }

        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Notification is created successfully
        assert response.status_code == 200
        assert b"Test Notification" in response.data
        assert b"created successfully" in response.data

        with app.app_context():
            notif = Notification.query.filter_by(title="Test Notification").first()
            assert notif is not None
            assert notif.message == "This is a test"
            assert notif.priority == "high"
            assert notif.is_active is True

    def test_create_notification_without_deadline(self, admin_client, app):
        # GIVEN: Notification data without deadline
        data = {
            "title": "No Deadline",
            "message": "This has no deadline",
            "priority": "normal"
        }

        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Notification is created with null deadline
        assert response.status_code == 200
        assert b"created successfully" in response.data

        with app.app_context():
            notif = Notification.query.filter_by(title="No Deadline").first()
            assert notif is not None
            assert notif.deadline is None

    def test_create_notification_missing_title(self, admin_client):
        # GIVEN: Notification data without title
        data = {
            "title": "",
            "message": "Message without title"
        }
        
        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Error message is displayed
        assert response.status_code == 200
        assert b"Title and message are required" in response.data

    def test_create_notification_missing_message(self, admin_client):
        # GIVEN: Notification data without message
        data = {
            "title": "Title without message",
            "message": ""
        }
        
        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Error message is displayed
        assert response.status_code == 200
        assert b"Title and message are required" in response.data

    def test_create_notification_missing_both(self, admin_client):
        # GIVEN: Notification data without title and message
        data = {
            "title": "",
            "message": ""
        }
        
        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Error message is displayed
        assert response.status_code == 200
        assert b"Title and message are required" in response.data

    def test_create_notification_invalid_deadline_format(self, admin_client, app):
        # GIVEN: Notification data with invalid deadline
        data = {
            "title": "Invalid Deadline",
            "message": "This has invalid deadline",
            "priority": "high",
            "deadline": "invalid-deadline"
        }

        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)

        # THEN: Error message is displayed and notification not created
        assert response.status_code == 200
        assert b"Invalid deadline format" in response.data

        with app.app_context():
            notif = Notification.query.filter_by(title="Invalid Deadline").first()
            assert notif is None

    def test_create_notification_whitespace_only(self, admin_client):
        # GIVEN: Notification data with whitespace-only title and message
        data = {
            "title": "   ",
            "message": "   "
        }
        
        # WHEN: POST request to create notification
        response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
        
        # THEN: Error message is displayed
        assert response.status_code == 200
        assert b"Title and message are required" in response.data


class TestDeleteNotification:

    def test_delete_notification_success(self, admin_client, app):
        # GIVEN: An existing active notification
        with app.app_context():
            notif = Notification(
                title="Delete Me",
                message="To be deleted",
                created_by=1
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id

        # WHEN: POST request to delete notification
        response = admin_client.post(
            f"/api/v1/notifications/{notif_id}/delete",
            follow_redirects=True
        )
        
        # THEN: Notification is soft-deleted
        assert response.status_code == 200
        assert b"Notification deleted successfully" in response.data

        with app.app_context():
            notif = Notification.query.get(notif_id)
            assert notif.is_active is False

    def test_delete_nonexistent_notification(self, admin_client):
        # GIVEN: A non-existent notification ID
        # WHEN: POST request to delete notification
        response = admin_client.post(
            "/api/v1/notifications/99999/delete",
            follow_redirects=False
        )
        
        # THEN: 404 error is returned
        assert response.status_code == 404

    def test_delete_notification_requires_authentication(self, client, app):
        # GIVEN: An existing notification and unauthenticated user
        with app.app_context():
            notif = Notification(
                title="Test",
                message="Test message",
                created_by=1
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id

        # WHEN: Unauthenticated POST request to delete notification
        response = client.post(
            f"/api/v1/notifications/{notif_id}/delete",
            follow_redirects=False
        )
        
        # THEN: User is redirected to login
        assert response.status_code == 302