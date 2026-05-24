class QuestionNotFoundError(Exception):
    """Raised when a question ID does not exist in the store."""
    def __init__(self, question_id: str):
        self.question_id = question_id
        super().__init__(f"Question '{question_id}' not found")


class SubmissionError(Exception):
    """Raised when submission evaluation fails unexpectedly."""
    pass


class Judge0Error(Exception):
    """Raised when Judge0 returns an unexpected error or times out."""
    pass


class DuplicateQuestionError(Exception):
    """Raised when a question with the same ID already exists."""
    def __init__(self, question_id: str):
        self.question_id = question_id
        super().__init__(f"Question '{question_id}' already exists")


class InvalidInputError(Exception):
    """Raised when input data fails business-logic validation."""
    pass
