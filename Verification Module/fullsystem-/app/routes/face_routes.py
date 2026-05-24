from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.face_service import verify_face

router = APIRouter(
    prefix="/face",
    tags=["Face Verification"]
)


@router.post("/verify")
async def face_verify(
    unique_id: str = Form(...),
    masked_aadhaar: str = Form(...),
    photo: UploadFile = File(...)
):

    try:

        result = verify_face(
            unique_id,
            masked_aadhaar,
            await photo.read()
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )