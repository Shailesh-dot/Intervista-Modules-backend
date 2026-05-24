from typing import List, Optional
from dataclasses import dataclass
from app.db.session import db_session
from app.models.user import User

@dataclass
class UserRecord:
    user_id: str
    email: str
    hashed_password: str
    role: str           # "admin" or "user"
    name: str = ""

def _to_record(u: User) -> UserRecord:
    return UserRecord(
        user_id=u.user_id,
        email=u.email,
        hashed_password=u.hashed_password,
        role=u.role,
        name=u.name or ""
    )

def save_user(user: UserRecord) -> UserRecord:
    with db_session() as db:
        db_user = User(
            user_id=user.user_id,
            email=user.email.lower(),
            hashed_password=user.hashed_password,
            role=user.role,
            name=user.name
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return _to_record(db_user)

def get_user_by_email(email: str) -> Optional[UserRecord]:
    with db_session() as db:
        u = db.query(User).filter(User.email == email.lower()).first()
        return _to_record(u) if u else None

def get_user_by_id(user_id: str) -> Optional[UserRecord]:
    with db_session() as db:
        u = db.query(User).filter(User.user_id == user_id).first()
        return _to_record(u) if u else None

def email_exists(email: str) -> bool:
    with db_session() as db:
        return db.query(User).filter(User.email == email.lower()).first() is not None

def list_users() -> list:
    with db_session() as db:
        users = db.query(User).all()
        return [_to_record(u) for u in users]

def count_users() -> int:
    with db_session() as db:
        return db.query(User).count()
