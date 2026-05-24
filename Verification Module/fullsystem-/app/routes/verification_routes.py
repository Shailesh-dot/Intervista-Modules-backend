from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import IdentityVerification, UserProfile

router = APIRouter(prefix="/verification", tags=["Verification"])


class VerificationCreate(BaseModel):
    userId: Optional[int] = None
    userName: Optional[str] = None
    aadhaarLast4: Optional[str] = None
    aadhaarZipUrl: Optional[str] = None
    passportPhotoUrl: Optional[str] = ""
    uniqueId: Optional[str] = None
    shareCode: Optional[str] = None


class VerificationComplete(BaseModel):
    uniqueId: str
    passportPhotoUrl: Optional[str] = ""


@router.post("/create")
def create_verification(model: VerificationCreate, db: Session = Depends(get_db)):
    """Create a pending identity_verifications record in PostgreSQL."""
    try:
        import uuid

        # Fetch user name from user_profile table if user_id is provided
        user_name = model.userName or "User"
        if model.userId:
            profile = db.query(UserProfile).filter(UserProfile.user_id == model.userId).first()
            if profile and profile.full_name:
                user_name = profile.full_name

        record = IdentityVerification(
            user_id=model.userId,
            user_name=user_name,
            aadhaar_last4=model.aadhaarLast4,
            aadhaar_zip_url=model.aadhaarZipUrl or "Manual Upload",
            passport_photo_url=model.passportPhotoUrl or "",
            unique_id=model.uniqueId or str(uuid.uuid4()),
            share_code=model.shareCode,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"message": "Verification created", "uniqueId": record.unique_id, "userName": user_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
def complete_verification(model: VerificationComplete, db: Session = Depends(get_db)):
    """Update passport_photo_url for an existing verification record."""
    if not model.uniqueId:
        raise HTTPException(status_code=400, detail="uniqueId is required")

    record = db.query(IdentityVerification).filter(
        IdentityVerification.unique_id == model.uniqueId
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Verification record not found")

    try:
        record.passport_photo_url = model.passportPhotoUrl or ""
        db.commit()
        return {"message": "Verification completed", "uniqueId": record.unique_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_id}")
def get_verification_status(user_id: int, db: Session = Depends(get_db)):
    """Check if a user has a completed verification (passport_photo_url is non-empty)."""
    record = db.query(IdentityVerification).filter(
        IdentityVerification.user_id == user_id,
        IdentityVerification.passport_photo_url != "",
        IdentityVerification.passport_photo_url.isnot(None),
    ).order_by(IdentityVerification.id.desc()).first()

    if not record:
        return {"verified": False}

    return {
        "verified": True,
        "uniqueId": record.unique_id,
        "photoUrl": record.passport_photo_url,
    }


class ModuleResultSubmit(BaseModel):
    studentId: int
    testCode: str
    moduleType: str  # "aptitude" | "coding" | "interview" | "verbal"
    moduleResult: dict


@router.get("/test-lookup/{test_code}")
def get_test_lookup(test_code: str, db: Session = Depends(get_db)):
    """Looks up a test by its test code, returning active modules and mapping info."""
    from sqlalchemy import text
    import json

    query = text("""
        SELECT t.test_id, t.test_code, t.company_id, t.hr_id,
               t.aptitude_module, t.verbal_module, t.interview_module, t.coding_module,
               c.company_name,
               tm.id AS test_mapping_id,
               am.aptitude_code, am.no_of_questions, am.topics AS aptitude_topics,
               cm.problem_codes AS coding_problem_codes,
               vm.verbal_code,
               im.ai_interview_code
        FROM test_infos t
        LEFT JOIN companies c ON t.company_id = c.uid
        LEFT JOIN test_mappings tm ON t.test_id = tm.test_id
        LEFT JOIN aptitude_mappings am ON tm.id = am.test_mapping_id
        LEFT JOIN coding_mappings cm ON tm.id = cm.test_mapping_id
        LEFT JOIN verbal_mappings vm ON tm.id = vm.test_mapping_id
        LEFT JOIN ai_interview_mappings im ON tm.id = im.test_mapping_id
        WHERE LOWER(t.test_code) = LOWER(:test_code)
    """)

    result = db.execute(query, {"test_code": test_code.strip()}).first()
    if not result:
        raise HTTPException(status_code=404, detail="Test code not found")

    def parse_json_field(val):
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        return val

    return {
        "testId": result.test_id,
        "testCode": result.test_code,
        "companyId": str(result.company_id) if result.company_id else None,
        "hrId": str(result.hr_id) if result.hr_id else None,
        "companyName": result.company_name or "Company",
        "aptitudeModule": bool(result.aptitude_module),
        "verbalModule": bool(result.verbal_module),
        "interviewModule": bool(result.interview_module),
        "codingModule": bool(result.coding_module),
        "testMappingId": result.test_mapping_id,
        "aptitudeMapping": {
            "aptitudeCode": result.aptitude_code,
            "noOfQuestions": result.no_of_questions,
            "topics": parse_json_field(result.aptitude_topics)
        } if result.aptitude_code else None,
        "codingMapping": {
            "problemCodes": parse_json_field(result.coding_problem_codes)
        } if result.coding_problem_codes else None,
        "verbalMapping": {
            "verbalCode": result.verbal_code
        } if result.verbal_code else None,
        "aiInterviewMapping": {
            "aiInterviewCode": result.ai_interview_code
        } if result.ai_interview_code else None
    }


@router.post("/submit-module-result")
def submit_module_result(model: ModuleResultSubmit, db: Session = Depends(get_db)):
    """Inserts or updates test module results in the consolidated PostgreSQL database."""
    from sqlalchemy import text
    import json

    try:
        # 1. Fetch test details using the test code
        test_query = text("""
            SELECT t.test_id, t.company_id, t.hr_id, tm.id AS test_mapping_id
            FROM test_infos t
            LEFT JOIN test_mappings tm ON t.test_id = tm.test_id
            WHERE LOWER(t.test_code) = LOWER(:test_code)
        """)
        test_info = db.execute(test_query, {"test_code": model.testCode}).first()
        if not test_info:
            raise HTTPException(status_code=404, detail="Test not found for code")

        # 2. Check if a ResultBase record already exists
        result_query = text("""
            SELECT id FROM results 
            WHERE student_id = :student_id AND test_id = :test_id
        """)
        existing_result = db.execute(result_query, {
            "student_id": model.studentId,
            "test_id": test_info.test_id
        }).first()

        if existing_result:
            result_base_id = existing_result.id
        else:
            # Create a new results row
            insert_result_query = text("""
                INSERT INTO results (student_id, test_id, test_code, company_id, hr_id, test_mapping_id, total_score, score_secured, created_at)
                VALUES (:student_id, :test_id, :test_code, :company_id, :hr_id, :test_mapping_id, 0.0, 0.0, NOW() AT TIME ZONE 'utc')
                RETURNING id
            """)
            res = db.execute(insert_result_query, {
                "student_id": model.studentId,
                "test_id": test_info.test_id,
                "test_code": model.testCode,
                "company_id": test_info.company_id,
                "hr_id": test_info.hr_id,
                "test_mapping_id": test_info.test_mapping_id
            })
            result_base_id = res.first().id
            db.commit()

        r = model.moduleResult

        # 3. Insert or update the specific module table
        if model.moduleType == "aptitude":
            # Check if aptitude result exists
            apt_exist = db.execute(text('SELECT "Id" FROM aptitude_results WHERE result_base_id = :id'), {"id": result_base_id}).first()
            if apt_exist:
                db.execute(text("""
                    UPDATE aptitude_results
                    SET aptitude_code = :code, module_total_score = :total, module_score_secured = :secured,
                        questions = :questions, user_answers = :u_ans, correct_answers = :c_ans, topics = :topics,
                        correct = :correct, incorrect = :incorrect
                    WHERE result_base_id = :result_base_id
                """), {
                    "code": r.get("aptitudeCode", ""), "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "questions": json.dumps(r.get("questions", [])), "u_ans": json.dumps(r.get("userAnswers", [])),
                    "c_ans": json.dumps(r.get("correctAnswers", [])), "topics": json.dumps(r.get("topics", [])),
                    "correct": int(r.get("correct", 0)), "incorrect": int(r.get("incorrect", 0)),
                    "result_base_id": result_base_id
                })
            else:
                db.execute(text("""
                    INSERT INTO aptitude_results (result_base_id, aptitude_code, module_total_score, module_score_secured, questions, user_answers, correct_answers, topics, correct, incorrect)
                    VALUES (:result_base_id, :code, :total, :secured, :questions, :u_ans, :c_ans, :topics, :correct, :incorrect)
                """), {
                    "result_base_id": result_base_id, "code": r.get("aptitudeCode", ""),
                    "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "questions": json.dumps(r.get("questions", [])), "u_ans": json.dumps(r.get("userAnswers", [])),
                    "c_ans": json.dumps(r.get("correctAnswers", [])), "topics": json.dumps(r.get("topics", [])),
                    "correct": int(r.get("correct", 0)), "incorrect": int(r.get("incorrect", 0))
                })

        elif model.moduleType == "coding":
            # Check if coding result exists
            cod_exist = db.execute(text('SELECT "Id" FROM coding_results WHERE result_base_id = :id'), {"id": result_base_id}).first()
            if cod_exist:
                db.execute(text("""
                    UPDATE coding_results
                    SET coding_code = :code, module_total_score = :total, module_score_secured = :secured,
                        testcase_totals = :totals, testcase_passed = :passed, answers = :answers
                    WHERE result_base_id = :result_base_id
                """), {
                    "code": r.get("codingCode", ""), "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "totals": json.dumps(r.get("testcaseTotals", [])), "passed": json.dumps(r.get("testcasePassed", [])),
                    "answers": json.dumps(r.get("answers", [])), "result_base_id": result_base_id
                })
            else:
                db.execute(text("""
                    INSERT INTO coding_results (result_base_id, coding_code, module_total_score, module_score_secured, testcase_totals, testcase_passed, answers)
                    VALUES (:result_base_id, :code, :total, :secured, :totals, :passed, :answers)
                """), {
                    "result_base_id": result_base_id, "code": r.get("codingCode", ""),
                    "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "totals": json.dumps(r.get("testcaseTotals", [])), "passed": json.dumps(r.get("testcasePassed", [])),
                    "answers": json.dumps(r.get("answers", []))
                })

        elif model.moduleType == "interview":
            # Check if interview result exists
            int_exist = db.execute(text('SELECT "Id" FROM ai_interview_results WHERE result_base_id = :id'), {"id": result_base_id}).first()
            if int_exist:
                db.execute(text("""
                    UPDATE ai_interview_results
                    SET ai_code = :code, module_total_score = :total, module_score_secured = :secured,
                        questions = :questions, answers = :answers, correct_answers = :correct_answers,
                        correct = :correct, wrong = :wrong
                    WHERE result_base_id = :result_base_id
                """), {
                    "code": r.get("aiCode", ""), "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "questions": json.dumps(r.get("questions", [])), "answers": json.dumps(r.get("answers", [])),
                    "correct_answers": json.dumps(r.get("correctAnswers", [])),
                    "correct": int(r.get("correct", 0)), "wrong": int(r.get("wrong", 0)),
                    "result_base_id": result_base_id
                })
            else:
                db.execute(text("""
                    INSERT INTO ai_interview_results (result_base_id, ai_code, module_total_score, module_score_secured, questions, answers, correct_answers, correct, wrong)
                    VALUES (:result_base_id, :code, :total, :secured, :questions, :answers, :correct_answers, :correct, :wrong)
                """), {
                    "result_base_id": result_base_id, "code": r.get("aiCode", ""),
                    "total": float(r.get("moduleTotalScore", 0)), "secured": float(r.get("moduleScoreSecured", 0)),
                    "questions": json.dumps(r.get("questions", [])), "answers": json.dumps(r.get("answers", [])),
                    "correct_answers": json.dumps(r.get("correctAnswers", [])),
                    "correct": int(r.get("correct", 0)), "wrong": int(r.get("wrong", 0))
                })

        elif model.moduleType == "verbal":
            # Map frontend payload: speakingScore, listeningScore, speakingParameters, listeningParameters
            speaking_score  = float(r.get("speakingScore", 0))
            listening_score = float(r.get("listeningScore", 0))
            total_module_score   = float(r.get("moduleTotalScore", 20))
            secured_module_score = speaking_score + listening_score

            # Build metrics dict combining both parameter sets
            metrics = {}
            sp = r.get("speakingParameters", {})
            lp = r.get("listeningParameters", {})
            if isinstance(sp, dict):
                for k, v in sp.items():
                    metrics[f"speaking_{k}"] = float(v) if v is not None else 0.0
            if isinstance(lp, dict):
                for k, v in lp.items():
                    metrics[f"listening_{k}"] = float(v) if v is not None else 0.0

            speaking_list  = [json.dumps(sp)]  if sp else []
            listening_list = [json.dumps(lp)] if lp else []

            vbl_exist = db.execute(text('SELECT "Id" FROM verbal_results WHERE result_base_id = :id'), {"id": result_base_id}).first()
            if vbl_exist:
                db.execute(text("""
                    UPDATE verbal_results
                    SET verbal_code = :code, module_total_score = :total, module_score_secured = :secured,
                        metrics = :metrics, listening = :listening, speaking = :speaking
                    WHERE result_base_id = :result_base_id
                """), {
                    "code": r.get("verbalCode", ""),
                    "total": total_module_score,
                    "secured": secured_module_score,
                    "metrics": json.dumps(metrics),
                    "listening": json.dumps(listening_list),
                    "speaking": json.dumps(speaking_list),
                    "result_base_id": result_base_id
                })
            else:
                db.execute(text("""
                    INSERT INTO verbal_results (result_base_id, verbal_code, module_total_score, module_score_secured, metrics, listening, speaking)
                    VALUES (:result_base_id, :code, :total, :secured, :metrics, :listening, :speaking)
                """), {
                    "result_base_id": result_base_id,
                    "code": r.get("verbalCode", ""),
                    "total": total_module_score,
                    "secured": secured_module_score,
                    "metrics": json.dumps(metrics),
                    "listening": json.dumps(listening_list),
                    "speaking": json.dumps(speaking_list),
                })

        db.commit()

        # 4. Update the aggregate score in results table
        total_score = 0.0
        score_secured = 0.0

        # Check Aptitude
        apt = db.execute(text("SELECT module_total_score, module_score_secured FROM aptitude_results WHERE result_base_id = :id"), {"id": result_base_id}).first()
        if apt:
            total_score += float(apt.module_total_score or 0)
            score_secured += float(apt.module_score_secured or 0)

        # Check Coding
        cod = db.execute(text("SELECT module_total_score, module_score_secured FROM coding_results WHERE result_base_id = :id"), {"id": result_base_id}).first()
        if cod:
            total_score += float(cod.module_total_score or 0)
            score_secured += float(cod.module_score_secured or 0)

        # Check Interview
        intv = db.execute(text("SELECT module_total_score, module_score_secured FROM ai_interview_results WHERE result_base_id = :id"), {"id": result_base_id}).first()
        if intv:
            total_score += float(intv.module_total_score or 0)
            score_secured += float(intv.module_score_secured or 0)

        # Check Verbal
        vbl = db.execute(text("SELECT module_total_score, module_score_secured FROM verbal_results WHERE result_base_id = :id"), {"id": result_base_id}).first()
        if vbl:
            total_score += float(vbl.module_total_score or 0)
            score_secured += float(vbl.module_score_secured or 0)

        db.execute(text("""
            UPDATE results 
            SET total_score = :total, score_secured = :secured
            WHERE id = :id
        """), {"total": total_score, "secured": score_secured, "id": result_base_id})
        
        db.commit()
        return {"status": "success", "resultBaseId": result_base_id, "totalScore": total_score, "scoreSecured": score_secured}

    except Exception as e:
        db.rollback()
        import traceback
        print("[submit-module-result ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database submission failed: {str(e)}")


@router.get("/test-results/{test_id}")
def get_test_results(test_id: str, db: Session = Depends(get_db)):
    """
    Returns all candidate results for a given test_id.
    Used by the Company Dashboard to display real scores, candidate lists,
    and module-level breakdowns.
    """
    from sqlalchemy import text

    # 1. Fetch all results rows for this test
    rows = db.execute(
        text("SELECT id, student_id, test_id, test_code, total_score, score_secured, created_at FROM results WHERE LOWER(test_id) = LOWER(:test_id)"),
        {"test_id": test_id}
    ).fetchall()

    if not rows:
        return []

    output = []

    for row in rows:
        result_base_id = row.id
        student_id = row.student_id

        # 2. Fetch student name & email from user_profiles
        profile = db.execute(
            text("SELECT full_name, email FROM user_profiles WHERE user_id = :uid"),
            {"uid": student_id}
        ).first()

        student_name = profile.full_name if profile and profile.full_name else f"Candidate #{student_id}"
        student_email = profile.email if profile and profile.email else ""

        # 3. Fetch each module result
        apt = db.execute(
            text('SELECT aptitude_code, module_total_score, module_score_secured, questions, user_answers, correct_answers, topics, correct, incorrect FROM aptitude_results WHERE result_base_id = :id'),
            {"id": result_base_id}
        ).first()

        cod = db.execute(
            text('SELECT coding_code, module_total_score, module_score_secured, testcase_totals, testcase_passed, answers FROM coding_results WHERE result_base_id = :id'),
            {"id": result_base_id}
        ).first()

        intv = db.execute(
            text('SELECT ai_code, module_total_score, module_score_secured, questions, answers, correct_answers, correct, wrong FROM ai_interview_results WHERE result_base_id = :id'),
            {"id": result_base_id}
        ).first()

        vbl = db.execute(
            text('SELECT verbal_code, module_total_score, module_score_secured, metrics, listening, speaking FROM verbal_results WHERE result_base_id = :id'),
            {"id": result_base_id}
        ).first()

        def safe(val, fallback=None):
            return val if val is not None else fallback

        entry = {
            "resultBaseId": result_base_id,
            "studentId": student_id,
            "studentName": student_name,
            "studentEmail": student_email,
            "testId": row.test_id,
            "testCode": row.test_code,
            "totalScore": float(row.total_score or 0),
            "scoreSecured": float(row.score_secured or 0),
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "aptitude": {
                "aptitudeCode": safe(apt.aptitude_code, ""),
                "moduleTotalScore": float(apt.module_total_score or 0),
                "moduleScoreSecured": float(apt.module_score_secured or 0),
                "questions": safe(apt.questions, []),
                "userAnswers": safe(apt.user_answers, []),
                "correctAnswers": safe(apt.correct_answers, []),
                "topics": safe(apt.topics, []),
                "correct": int(apt.correct or 0),
                "incorrect": int(apt.incorrect or 0),
            } if apt else None,
            "coding": {
                "codingCode": safe(cod.coding_code, ""),
                "moduleTotalScore": float(cod.module_total_score or 0),
                "moduleScoreSecured": float(cod.module_score_secured or 0),
                "testcaseTotals": safe(cod.testcase_totals, []),
                "testcasePassed": safe(cod.testcase_passed, []),
                "answers": safe(cod.answers, []),
            } if cod else None,
            "aiInterview": {
                "aiCode": safe(intv.ai_code, ""),
                "moduleTotalScore": float(intv.module_total_score or 0),
                "moduleScoreSecured": float(intv.module_score_secured or 0),
                "questions": safe(intv.questions, []),
                "answers": safe(intv.answers, []),
                "correctAnswers": safe(intv.correct_answers, []),
                "correct": int(intv.correct or 0),
                "wrong": int(intv.wrong or 0),
            } if intv else None,
            "verbal": {
                "verbalCode": safe(vbl.verbal_code, ""),
                "moduleTotalScore": float(vbl.module_total_score or 0),
                "moduleScoreSecured": float(vbl.module_score_secured or 0),
                "metrics": safe(vbl.metrics, {}),
                "listening": safe(vbl.listening, []),
                "speaking": safe(vbl.speaking, []),
            } if vbl else None,
        }

        output.append(entry)

    return output
