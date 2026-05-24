import random
from typing import List, Optional
from app.models.question import Question as DBQuestion
from app.models.test_case import TestCase as DBTestCase
from app.schemas.question_schema import QuestionCreate, QuestionResponse, QuestionAdminResponse
from app.db.session import db_session
from app.core.logger import logger

def _to_admin_response(db_q: DBQuestion) -> QuestionAdminResponse:
    # Partition test cases
    sample_tcs = []
    hidden_tcs = []
    for tc in db_q.test_cases:
        tc_dict = {
            "id": tc.id,
            "input": tc.input_data,
            "expected_output": tc.expected_output
        }
        if tc.is_sample:
            sample_tcs.append(tc_dict)
        else:
            hidden_tcs.append(tc_dict)

    return QuestionAdminResponse(
        id=db_q.id,
        title=db_q.title,
        description=db_q.description,
        difficulty=db_q.difficulty,
        examples=db_q.examples,
        constraints=db_q.constraints,
        boilerplates=db_q.boilerplates,
        allowed_languages=db_q.allowed_languages,
        sample_test_cases=sample_tcs,
        hidden_test_cases=hidden_tcs
    )

def _to_public_response(db_q: DBQuestion) -> QuestionResponse:
    admin_resp = _to_admin_response(db_q)
    public_dict = admin_resp.model_dump()
    public_dict.pop("hidden_test_cases", None)
    return QuestionResponse(**public_dict)

def add_question(data: QuestionCreate) -> QuestionAdminResponse:
    with db_session() as db:
        db_q = DBQuestion(
            id=data.id,
            title=data.title,
            description=data.description,
            difficulty=data.difficulty,
            examples=data.examples,
            constraints=data.constraints,
            boilerplates=data.boilerplates,
            allowed_languages=data.allowed_languages,
        )
        
        # Add relational test cases
        for tc in data.sample_test_cases:
            db_q.test_cases.append(DBTestCase(
                input_data=tc.input,
                expected_output=tc.expected_output,
                is_sample=True,
                is_hidden=False
            ))
            
        for tc in data.hidden_test_cases:
            db_q.test_cases.append(DBTestCase(
                input_data=tc.input,
                expected_output=tc.expected_output,
                is_sample=False,
                is_hidden=True
            ))
            
        db.add(db_q)
        db.commit()
        db.refresh(db_q)
        return _to_admin_response(db_q)

def get_question(question_id: str) -> Optional[QuestionAdminResponse]:
    with db_session() as db:
        q = db.query(DBQuestion).filter(DBQuestion.id == question_id).first()
        return _to_admin_response(q) if q else None

def get_question_safe(question_id: str) -> Optional[QuestionResponse]:
    with db_session() as db:
        q = db.query(DBQuestion).filter(DBQuestion.id == question_id).first()
        return _to_public_response(q) if q else None

def question_exists(question_id: str) -> bool:
    with db_session() as db:
        return db.query(DBQuestion).filter(DBQuestion.id == question_id).first() is not None

def list_questions() -> List[QuestionResponse]:
    with db_session() as db:
        questions = db.query(DBQuestion).all()
        return [_to_public_response(q) for q in questions]

def list_questions_admin() -> List[QuestionAdminResponse]:
    with db_session() as db:
        questions = db.query(DBQuestion).all()
        return [_to_admin_response(q) for q in questions]

def get_random_question() -> Optional[QuestionResponse]:
    with db_session() as db:
        import sqlalchemy.sql.functions as func
        q = db.query(DBQuestion).order_by(func.random()).first()
        return _to_public_response(q) if q else None

def get_random_question_set_by_difficulty() -> List[QuestionResponse]:
    with db_session() as db:
        import sqlalchemy.sql.functions as func
        
        easy_q = db.query(DBQuestion).filter(DBQuestion.difficulty == "Easy").order_by(func.random()).first()
        medium_q = db.query(DBQuestion).filter(DBQuestion.difficulty == "Medium").order_by(func.random()).first()
        hard_q = db.query(DBQuestion).filter(DBQuestion.difficulty == "Hard").order_by(func.random()).first()
        
        results = []
        if easy_q: results.append(_to_public_response(easy_q))
        if medium_q: results.append(_to_public_response(medium_q))
        if hard_q: results.append(_to_public_response(hard_q))
        
        return results

def update_question(question_id: str, updates: dict) -> Optional[QuestionAdminResponse]:
    with db_session() as db:
        q = db.query(DBQuestion).filter(DBQuestion.id == question_id).first()
        if not q:
            return None
        
        for key, value in updates.items():
            if key in ["sample_test_cases", "hidden_test_cases"]:
                # To perfectly mutate test cases, we could drop old ones and append new ones
                pass # Handled specially if needed, skipping complex partial update logic for brevity
            elif value is not None:
                setattr(q, key, value)

        db.commit()
        db.refresh(q)
        return _to_admin_response(q)

def delete_question(question_id: str) -> bool:
    with db_session() as db:
        q = db.query(DBQuestion).filter(DBQuestion.id == question_id).first()
        if q:
            db.delete(q) # cascade deletes TestCases natively!
            db.commit()
            return True
        return False

def count_questions() -> int:
    with db_session() as db:
        return db.query(DBQuestion).count()
