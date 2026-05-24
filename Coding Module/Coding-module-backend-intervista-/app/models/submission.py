from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Submission(Base):
    __tablename__ = "submissions"

    submission_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, index=True, nullable=True) # candidate_id maps easily
    question_id = Column(String, ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id = Column(String, ForeignKey("assessment_sessions.session_id", ondelete="CASCADE"), nullable=True)
    language = Column(String, nullable=False)
    
    source_code = Column(String, nullable=False)
    status = Column(String, default="Pending") # Overall verdict (Accepted, WA, etc.)
    job_status = Column(String, default="queued") # queued, running, completed
    judge0_token = Column(String, nullable=True) # Used for batch API token
    
    total_test_cases = Column(Integer, default=0)
    passed_test_cases = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    
    execution_time = Column(Float, nullable=True)
    memory = Column(Float, nullable=True)
    compile_output = Column(String, nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    results = relationship("SubmissionResult", back_populates="submission", cascade="all, delete-orphan")
    session = relationship("AssessmentSession", back_populates="submissions")
