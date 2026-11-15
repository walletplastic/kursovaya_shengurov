
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    key = current_app.config["FERNET_KEY"].encode()
    return Fernet(key)


def encrypt_data(data):
    return get_fernet().encrypt(data.encode()).decode()


def decrypt_data(encrypted_data):
    return get_fernet().decrypt(encrypted_data.encode()).decode()
