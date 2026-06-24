"""
db/auth.py — password hashing and user management.
"""

import os
import secrets

import bcrypt

from db.database import User, get_session


# ------------------------------------------------------------------
# Secret key (used by SessionMiddleware to sign cookies)
# ------------------------------------------------------------------

def get_secret_key() -> str:
    path = os.path.join(os.path.dirname(__file__), ".secret_key")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w") as f:
        f.write(key)
    return key


# ------------------------------------------------------------------
# User CRUD
# ------------------------------------------------------------------

def user_count() -> int:
    session = get_session()
    try:
        return session.query(User).count()
    finally:
        session.close()


def get_user(username: str) -> User | None:
    session = get_session()
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        session.close()


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(username: str, password: str) -> None:
    session = get_session()
    try:
        user = User(username=username, password_hash=_hash(password))
        session.add(user)
        session.commit()
    finally:
        session.close()


def verify_password(username: str, password: str) -> bool:
    user = get_user(username)
    if user is None:
        return False
    return _verify(password, user.password_hash)


def update_password(username: str, new_password: str) -> None:
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if user:
            user.password_hash = _hash(new_password)
            session.commit()
    finally:
        session.close()
