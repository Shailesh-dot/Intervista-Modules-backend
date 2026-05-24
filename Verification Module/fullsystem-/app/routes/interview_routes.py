from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.interview_service import (
    verify_interview,
    reset_verification,
    get_verification_status
)

router = APIRouter(prefix="/interview", tags=["Interview Verification"])


@router.post("/verify")
async def interview_verification(
    unique_id: str = Form(...),
    webcam_image: UploadFile = File(...)
):
    """
    Main interview verification endpoint
    Processes webcam frames for liveness detection and face verification
    """
    
    try:
        image_bytes = await webcam_image.read()
        
        result = verify_interview(unique_id, image_bytes)
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification error: {str(e)}"
        )


@router.post("/reset")
async def reset_interview_verification(
    unique_id: str = Form(...)
):
    """
    Reset verification for a user
    Useful when user wants to retry after failure
    """
    
    try:
        result = reset_verification(unique_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reset error: {str(e)}"
        )


@router.get("/status/{unique_id}")
async def get_interview_status(unique_id: str):
    """
    Get current verification status without processing a frame
    Useful for checking if verification is complete
    """
    
    try:
        result = get_verification_status(unique_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Status check error: {str(e)}"
        )


# Legacy endpoint for backward compatibility
@router.post("/verify-interview")
async def legacy_interview_verification(
    unique_id: str = Form(...),
    webcam_image: UploadFile = File(...)
):
    """
    Legacy endpoint - redirects to /verify
    Maintained for backward compatibility
    """
    
    try:
        image_bytes = await webcam_image.read()
        result = verify_interview(unique_id, image_bytes)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification error: {str(e)}"
        )