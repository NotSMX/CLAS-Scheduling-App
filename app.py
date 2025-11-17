from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from views import main_blueprint
from events import events_blueprint
from models import db, User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clas_app.db'
app.config["SECRET_KEY"] = "dev"
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
    app.run(debug=True)

with app.app_context():
    db.create_all()  # Create database tables
