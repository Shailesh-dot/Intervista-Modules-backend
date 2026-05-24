import sys
import os

# Ensure app is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.base import engine, Base
# Import all models so Base metadata registers them
from app.models.user import User
from app.models.question import Question
from app.models.test_case import TestCase
from app.models.submission import Submission
from app.models.submission_result import SubmissionResult
from app.models.assessment_session import AssessmentSession

def init_db():
    print("Dropping existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
