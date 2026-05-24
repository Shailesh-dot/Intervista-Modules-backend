from pydantic import BaseModel, field_validator, ConfigDict
from typing import Dict, List, Optional, Any

class TestCaseBase(BaseModel):
    input: str
    expected_output: str

class TestCaseCreate(TestCaseBase):
    pass

class QuestionCreate(BaseModel):
    id: str
    title: str
    description: str
    difficulty: Optional[str] = "Medium"
    examples: Optional[List[dict]] = []
    constraints: Optional[List[str]] = []
    
    sample_test_cases: List[TestCaseCreate] = []
    hidden_test_cases: List[TestCaseCreate] = []
    
    boilerplates: Dict[str, Any] = {}
    allowed_languages: List[str] = ["python"]

    @field_validator("difficulty")
    @classmethod
    def difficulty_must_be_valid(cls, v):
        if v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v

class QuestionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None

    @field_validator("difficulty")
    @classmethod
    def difficulty_must_be_valid(cls, v):
        if v and v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v

class QuestionResponse(BaseModel):
    """Safe response object that guarantees hidden test cases are stripped."""
    id: str
    title: str
    description: str
    difficulty: str
    examples: List[dict]
    constraints: List[str]
    boilerplates: Dict[str, Any]
    allowed_languages: List[str]
    
    sample_test_cases: List[dict] = []

    model_config = ConfigDict(from_attributes=True)

class QuestionAdminResponse(QuestionResponse):
    """Admin response that includes hidden test cases."""
    hidden_test_cases: List[dict] = []
