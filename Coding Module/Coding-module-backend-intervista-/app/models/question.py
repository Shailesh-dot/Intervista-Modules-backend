from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from app.db.base import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, default="Medium")
    
    # Store lists/dicts as JSONB in PostgreSQL
    examples = Column(JSONB, default=[])
    constraints = Column(JSONB, default=[])
    boilerplates = Column(JSONB, default={})
    metadata_obj = Column(JSONB, default={})
    allowed_languages = Column(JSONB, default=["python"])

    created_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    test_cases = relationship("TestCase", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="difficulty_check"),
    )
