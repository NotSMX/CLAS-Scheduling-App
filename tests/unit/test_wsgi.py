from website import wsgi

def test_wsgi_application():
    assert hasattr(wsgi, "application")
    assert wsgi.application is not None