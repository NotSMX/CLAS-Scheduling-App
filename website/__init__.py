from dotenv import load_dotenv
import os
from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from flask_migrate import Migrate

load_dotenv()

def create_app():
    app = Flask(__name__)
    from .views import main_blueprint
    from .events import events_blueprint
    from .models import db, User, Session, Event, Room
    from .admin import admin_blueprint
    from .oauth_client import init_oauth
    from .notifications import notifications_blueprint
    from .auth import auth_blueprint

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres", "postgresql", 1)
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.register_blueprint(main_blueprint)
    app.register_blueprint(events_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(notifications_blueprint)

    db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize OAuth clients
    init_oauth(app)

    app.register_blueprint(auth_blueprint)

    # list of admin emails in .env
    app.config["ADMIN_EMAILS"] = os.getenv("ADMIN_EMAILS", "").split(",")
    # this is for if we choose to have valid faculty listed in a csv file
    app.config["FACULTY_EMAILS"] = os.getenv("FACULTY_EMAILS", "").split(",")
    # app.config["FACULTY_LIST_PATH"] = "instance/faculty_list.csv"

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory('static', filename)
    
    # # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

# When tesing locally, run on debug mode
if __name__ == '__main__':
    create_app()