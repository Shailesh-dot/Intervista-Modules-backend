from app.schemas.code_schema import CodeRunRequest


def validate_code_input(data: CodeRunRequest):
    if not data.source_code or not data.source_code.strip():
        raise ValueError("source_code cannot be empty")
    if not data.language_id:
        raise ValueError("language_id is required")


def validate_language_id(language_id: int):
    valid_ids = [50, 54, 62, 63, 71, 72, 73, 74, 76, 78, 79, 80, 81]
    if language_id not in valid_ids:
        raise ValueError(f"Unsupported language_id: {language_id}")
