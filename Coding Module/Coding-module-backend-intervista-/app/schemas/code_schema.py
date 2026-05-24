from pydantic import BaseModel, field_validator


class CodeRunRequest(BaseModel):
    source_code: str
    language_id: int
    stdin: str = ""

    @field_validator("source_code")
    @classmethod
    def code_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("source_code cannot be empty")
        return v


class CodeRunResponse(BaseModel):
    stdout: str
    stderr: str
    compile_output: str
    status: str
    status_id: int
    time: str
    memory: str
