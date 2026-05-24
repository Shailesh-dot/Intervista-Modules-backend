from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class SubmissionResult(Base):
    __tablename__ = "submission_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(String, ForeignKey("submissions.submission_id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=True)
    
    status = Column(String, nullable=True) # Passed, Failed, TLE, etc.
    stdout = Column(String, nullable=True)
    stderr = Column(String, nullable=True)
    compile_output = Column(String, nullable=True)
    execution_time = Column(Float, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="results")
    test_case = relationship("TestCase")
