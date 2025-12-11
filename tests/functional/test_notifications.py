from website.models import Notification, db

def test_notifications_page(admin_client):
    response = admin_client.get("/notifications")
    assert response.status_code == 200
    assert b"Notifications" in response.data

def test_create_notification_page(admin_client):
    response = admin_client.get("/notifications/create")
    assert response.status_code == 200
    assert b"Create Notification" in response.data

def test_create_notification_success(admin_client, app):
    data = {
        "title": "Test Notification",
        "message": "This is a test",
        "priority": "high",
        "deadline": "2030-01-01T12:00"
    }

    response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Test Notification" in response.data
    assert b"created successfully" in response.data

    with app.app_context():
        notif = Notification.query.filter_by(title="Test Notification").first()
        assert notif is not None
        assert notif.message == "This is a test"
        assert notif.priority == "high"
        assert notif.is_active is True

def test_create_notification_invalid(admin_client):
    title = "Test Notification Invalid Deadline"
    data = {
        "title": title,
        "message": "This is a test",
        "priority": "high",
        "deadline": "invalid-deadline"
    }

    response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid deadline format" in response.data

    with admin_client.application.app_context():
        notif = Notification.query.filter_by(title=title).first()
        assert notif is None

def test_delete_notification(admin_client, app):
    with app.app_context():
        notif = Notification(title="Delete Me", message="To be deleted", created_by=1)
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id

    response = admin_client.post(f"/api/v1/notifications/{notif_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Notification deleted successfully" in response.data

    with app.app_context():
        notif = Notification.query.get(notif_id)
        assert notif.is_active is False

def test_missing_title_or_message(admin_client):
    data = {"title": "", "message": "Message"}
    response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
    assert b"Title and message are required" in response.data

def test_invalid_deadline(admin_client):
    data = {"title": "Test", "message": "Msg", "deadline": "invalid"}
    response = admin_client.post("/api/v1/notifications", data=data, follow_redirects=True)
    assert b"Invalid deadline format" in response.data
