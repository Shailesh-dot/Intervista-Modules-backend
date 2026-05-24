from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from app.db.base import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session():
    """Context manager for non-route functions to use DB session cleanly."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
