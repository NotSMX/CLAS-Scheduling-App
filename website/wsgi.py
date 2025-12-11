from website import create_app

app = create_app()

# Expose the Flask app as a WSGI application
application = app