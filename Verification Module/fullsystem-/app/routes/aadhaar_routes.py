from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.aadhaar_service import process_aadhaar

router = APIRouter(prefix="/aadhaar", tags=["Aadhaar"])


@router.post("/upload")
async def upload_aadhaar(
    file: UploadFile = File(...),
    share_code: str = Form(...),
    last4: str = Form(...)
):

    try:

        unique_id, data = process_aadhaar(file.file, share_code, last4)

        return {
            "unique_id": unique_id,
            "aadhaar_details": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )