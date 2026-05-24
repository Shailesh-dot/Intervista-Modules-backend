from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class RunRequest(BaseModel):
    """Used by the Run button — executes code with custom stdin, no test case eval."""
    question_id: str
    language: str        
    source_code: str
    stdin: str = ""
    candidate_id: str = "anonymous"

class SubmissionRequest(BaseModel):
    """Used by the Submit button to enqueue a submission."""
    question_id: str
    language: str        # e.g. "python", "java"
    source_code: str
    candidate_id: str = "anonymous"
    session_id: Optional[str] = None

class SubmissionEnqueueResponse(BaseModel):
    """Immediate response returning the polling ID."""
    submission_id: str
    status: str = "processing"

class TestCaseResult(BaseModel):
    """Safe test case result that masks input/output for hidden cases natively."""
    test_case_id: Optional[int] = None
    status: Optional[str] = None
    execution_time: Optional[float] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    is_hidden: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

class SubmissionStatusResponse(BaseModel):
    """Polling response object."""
    submission_id: str
    question_id: str
    session_id: Optional[str] = None
    candidate_id: Optional[str] = None
    language: str
    status: str
    job_status: str
    
    total_test_cases: int
    passed_test_cases: int
    score: float
    
    execution_time: Optional[float] = None
    memory: Optional[float] = None
    compile_output: Optional[str] = None
    
    test_case_results: List[TestCaseResult] = []
    
    model_config = ConfigDict(from_attributes=True)
