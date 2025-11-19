from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from views import main_blueprint
from events import events_blueprint
from models import db, User
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.register_blueprint(main_blueprint)
app.register_blueprint(events_blueprint)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
        
        # Import and run seeding
        from seed_rooms import seed_rooms
        seed_rooms()  # automatically seed if needed
    
    app.run(debug=True)