from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    session_id = Column(String, primary_key=True)
    candidate_id = Column(String, index=True, nullable=False)
    
    status = Column(String, default="active") # active, completed, expired
    
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    # Relationships
    submissions = relationship("Submission", back_populates="session", cascade="all, delete-orphan")
