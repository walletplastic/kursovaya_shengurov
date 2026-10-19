
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    login = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    full_name_encrypted = db.Column(
        db.Text,
        nullable=False
    )

    phone_encrypted = db.Column(
        db.Text,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="client"
    )
