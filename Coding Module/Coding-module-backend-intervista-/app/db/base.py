from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from app.config import DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment or config.")

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

Base = declarative_base()
