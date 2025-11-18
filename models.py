from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    profile_pic_url = db.Column(db.String(255), nullable=True, default=None)

    events = db.relationship('Event', backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False  # Google user with no password
        return check_password_hash(self.password_hash, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clas_type = db.Column(db.String(80), nullable=False)
    format = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    course_number = db.Column(db.String(10), nullable=False)
    course_title = db.Column(db.String(80), nullable=False)
    num_entries = db.Column(db.Integer, nullable=False)
    num_students = db.Column(db.Integer, nullable=False)
    session_title = db.Column(db.String(80), nullable=False)
    session_length = db.Column(db.Integer, nullable=False)
    individual_entry_length = db.Column(db.Integer, nullable=False)
    room_request = db.Column(db.String(160))
    special_request = db.Column(db.String(160))
    status = db.Column(db.String(20), default='draft')

    session = db.relationship('Session', backref='Event', uselist=False, cascade='all, delete-orphan', passive_deletes=True)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False, unique=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    
    user = db.relationship('User', backref='sessions')
    room = db.relationship('Room', backref='sessions')

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building_name = db.Column(db.String(80), nullable=False)
    room_number = db.Column(db.Integer)
    capacity = db.Column(db.Integer)
    special_features = db.Column(db.String(160))
