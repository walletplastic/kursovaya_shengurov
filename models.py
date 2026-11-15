from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
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


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    depth = db.Column(db.Numeric(8, 2), nullable=False)
    latitude = db.Column(db.Numeric(8, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)

    client = db.relationship("User", backref=db.backref("orders", lazy=True))
