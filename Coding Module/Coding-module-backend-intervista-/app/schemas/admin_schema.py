from pydantic import BaseModel, field_validator, Field, AliasChoices
from typing import Dict, List, Optional


class TestCaseInput(BaseModel):
    input: str
    expected_output: str


class BoilerplateInput(BaseModel):
    """
    Admin provides boilerplates per language.
    language_id can be omitted — resolved automatically from the language key.
    """
    template: str
    code: Optional[str] = None
    language_id: Optional[int] = None   # auto-filled from LANGUAGE_MAP if missing


class QuestionCreateRequest(BaseModel):
    """
    Admin JSON format for creating a question.

    Example:
    {
      "title": "Two Sum",
      "difficulty": "Easy",
      "boilerplates": {
        "python": {"template": "def twoSum(nums, target):\n    pass"},
        "java":   {"template": "class Solution { ... }"}
      },
      "visible_test_cases": [{"input": "...", "expected_output": "..."}],
      "hidden_test_cases":  [{"input": "...", "expected_output": "..."}]
    }
    """
    id: Optional[str] = Field(default=None, validation_alias=AliasChoices("id", "q_id"))
    title: str
    description: str
    difficulty: str = "Medium"
    constraints: Optional[List[str]] = []
    examples: Optional[List[dict]] = []
    sample_test_cases: List[TestCaseInput]
    hidden_test_cases: List[TestCaseInput]
    boilerplates: Dict[str, BoilerplateInput] = {}
    allowed_languages: Optional[List[str]] = ["python"]

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v

    @field_validator("sample_test_cases")
    @classmethod
    def must_have_at_least_one_sample(cls, v):
        if not v:
            raise ValueError("At least one sample_test_case is required")
        return v

    @field_validator("hidden_test_cases")
    @classmethod
    def must_have_at_least_one_hidden(cls, v):
        if not v:
            raise ValueError("At least one hidden_test_case is required")
        return v

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, v):
        if v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v


class BulkQuestionUploadRequest(BaseModel):
    questions: List[QuestionCreateRequest]


class QuestionUpdateRequest(BaseModel):
    """Partial update — only send the fields you want to change."""
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    constraints: Optional[List[str]] = None
    examples: Optional[List[dict]] = None
    sample_test_cases: Optional[List[TestCaseInput]] = None
    hidden_test_cases: Optional[List[TestCaseInput]] = None
    boilerplates: Optional[Dict[str, BoilerplateInput]] = None
    allowed_languages: Optional[List[str]] = None

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, v):
        if v is not None and v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v
