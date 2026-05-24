from typing import List, Optional
from app.schemas.submission_schema import SubmissionStatusResponse, TestCaseResult
from app.models.submission import Submission as DBSubmission
from app.models.submission_result import SubmissionResult as DBSubmissionResult
from app.db.session import db_session

def _to_response(db_s: DBSubmission) -> SubmissionStatusResponse:
    tc_results = []
    for r in db_s.results:
        tc_results.append(TestCaseResult(
            test_case_id=r.test_case_id,
            status=r.status or "Pending",
            execution_time=r.execution_time,
            stdout=r.stdout,
            stderr=r.stderr,
            compile_output=r.compile_output,
            is_hidden=r.test_case.is_hidden if r.test_case else False
        ))

    return SubmissionStatusResponse(
        submission_id=db_s.submission_id,
        question_id=db_s.question_id,
        candidate_id=db_s.candidate_id,
        language=db_s.language,
        status=db_s.status,
        job_status=db_s.job_status,
        total_test_cases=db_s.total_test_cases,
        passed_test_cases=db_s.passed_test_cases,
        score=db_s.score,
        execution_time=db_s.execution_time,
        memory=db_s.memory,
        compile_output=db_s.compile_output,
        test_case_results=tc_results
    )

def store_submission_enqueue(sub_id: str, question_id: str, candidate_id: str, language: str, code: str) -> None:
    with db_session() as db:
        db_s = DBSubmission(
            submission_id=sub_id,
            candidate_id=candidate_id,
            question_id=question_id,
            language=language,
            source_code=code,
            status="Pending",
            job_status="queued"
        )
        db.add(db_s)
        db.commit()

def update_submission_status(sub_id: str, updates: dict) -> None:
    with db_session() as db:
        s = db.query(DBSubmission).filter(DBSubmission.submission_id == sub_id).first()
        if s:
            for k, v in updates.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            db.commit()

def store_submission_results(sub_id: str, test_case_results: List[dict]) -> None:
    with db_session() as db:
        s = db.query(DBSubmission).filter(DBSubmission.submission_id == sub_id).first()
        if not s:
            return
        
        # Clear existing old results if this is a retry/overwrite
        db.query(DBSubmissionResult).filter(DBSubmissionResult.submission_id == sub_id).delete()
        
        for r in test_case_results:
            tr = DBSubmissionResult(
                submission_id=sub_id,
                test_case_id=r.get("test_case_id"),
                status=r.get("status"),
                execution_time=r.get("execution_time"),
                stdout=r.get("stdout"),
                stderr=r.get("stderr"),
                compile_output=r.get("compile_output")
            )
            s.results.append(tr)
        db.commit()

def get_submission(submission_id: str) -> Optional[SubmissionStatusResponse]:
    with db_session() as db:
        s = db.query(DBSubmission).filter(DBSubmission.submission_id == submission_id).first()
        return _to_response(s) if s else None

def get_submissions_by_candidate(candidate_id: str) -> List[SubmissionStatusResponse]:
    with db_session() as db:
        subs = db.query(DBSubmission).filter(DBSubmission.candidate_id == candidate_id).all()
        return [_to_response(s) for s in subs]

def get_submissions_by_question(question_id: str) -> List[SubmissionStatusResponse]:
    with db_session() as db:
        subs = db.query(DBSubmission).filter(DBSubmission.question_id == question_id).all()
        return [_to_response(s) for s in subs]

def list_all_submissions() -> List[SubmissionStatusResponse]:
    with db_session() as db:
        subs = db.query(DBSubmission).all()
        return [_to_response(s) for s in subs]

def count_submissions() -> int:
    with db_session() as db:
        return db.query(DBSubmission).count()
