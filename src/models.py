from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(200), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    profile_image = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    spotify_token = db.Column(db.String(500), nullable=True)
    spotify_refresh_token = db.Column(db.String(500), nullable=True)
    spotify_token_expiry = db.Column(db.DateTime, nullable=True)
