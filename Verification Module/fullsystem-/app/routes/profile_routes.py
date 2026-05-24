from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services.profile_service import get_user_profile, create_or_update_profile
from app.utils.cloudinary_utils import upload_to_cloudinary

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/{user_id}")
def read_profile(user_id: int, db: Session = Depends(get_db)):
    profile = get_user_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/upload-photo")
async def upload_photo(photo: UploadFile = File(...)):
    try:
        photo_data = await photo.read()
        photo_url = upload_to_cloudinary(photo_data, folder="profile_photos")
        return {"photoUrl": photo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")

@router.post("/create")
async def create_profile(
    UserId: int = Form(...),
    FullName: str = Form(...),
    Email: str = Form(...),
    Dob: str = Form(None),
    Age: int = Form(None),
    College: str = Form(None),
    Address: str = Form(None),
    Phone: str = Form(None),
    Gender: str = Form(None),
    PhotoUrl: str = Form(None),
    db: Session = Depends(get_db)
):
    profile_data = {
        "user_id": UserId,
        "full_name": FullName,
        "email": Email,
        "dob": Dob,
        "age": Age,
        "college": College,
        "address": Address,
        "phone": Phone,
        "gender": Gender,
        "photo_url": PhotoUrl
    }
    
    try:
        profile = create_or_update_profile(db, profile_data)
        return {"message": "Profile created/updated successfully", "userId": profile.user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
