import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    FERNET_KEY = os.getenv("FERNET_KEY")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Включить для сайта, работающего по HTTPS.
    SESSION_COOKIE_SAMESITE = "Lax"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
