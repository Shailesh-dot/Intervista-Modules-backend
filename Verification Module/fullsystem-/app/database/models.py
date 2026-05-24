from sqlalchemy import Column, Integer, String
from app.database.db import Base


class IdentityVerification(Base):
    """Mirrors the C# knitnet-verification-api IdentityVerification model.
    Table: identity_verifications (created/managed by Entity Framework)."""

    __tablename__ = "identity_verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    unique_id = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    aadhaar_last4 = Column(String, nullable=True)
    aadhaar_zip_url = Column(String, nullable=True)
    passport_photo_url = Column(String, nullable=True)
    share_code = Column(String, nullable=True)


class UserProfile(Base):
    """Maps to the C# knitnet-user-api user_profiles table."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    college = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    gender = Column(String, nullable=True)


class User(Base):
    """Mirrors the .NET users table."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    role = Column(String)