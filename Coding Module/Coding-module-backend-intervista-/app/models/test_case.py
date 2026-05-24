from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    
    input_data = Column(String, nullable=False)
    expected_output = Column(String, nullable=False)
    
    is_sample = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=True)
    weight = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to Question
    question = relationship("Question", back_populates="test_cases")

    __table_args__ = (
        CheckConstraint(
            "(is_sample = TRUE AND is_hidden = FALSE) OR (is_sample = FALSE AND is_hidden = TRUE)",
            name="sample_hidden_check"
        ),
    )
