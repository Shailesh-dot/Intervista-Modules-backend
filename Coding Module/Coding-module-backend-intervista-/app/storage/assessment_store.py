from app.models.assessment_session import AssessmentSession
from app.schemas.assessment_schema import AssessmentSessionCreate
from app.db.session import db_session
from app.utils.id_generator import generate_id
from datetime import datetime, timezone, timedelta
from typing import Optional

def create_session(candidate_id: str, duration_minutes: int) -> AssessmentSession:
    with db_session() as db:
        session_id = f"sess_{generate_id()}"
        start = datetime.now(timezone.utc)
        end = start + timedelta(minutes=duration_minutes)
        
        session = AssessmentSession(
            session_id=session_id,
            candidate_id=candidate_id,
            status="active",
            start_time=start,
            end_time=end,
            duration_minutes=duration_minutes
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

def get_session(session_id: str) -> Optional[AssessmentSession]:
    with db_session() as db:
        return db.query(AssessmentSession).filter(AssessmentSession.session_id == session_id).first()

def complete_session(session_id: str, status: str = "completed") -> bool:
    with db_session() as db:
        session = db.query(AssessmentSession).filter(AssessmentSession.session_id == session_id).first()
        if session:
            session.status = status
            db.commit()
            return True
        return False
