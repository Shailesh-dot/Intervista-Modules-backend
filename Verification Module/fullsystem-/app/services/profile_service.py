from sqlalchemy.orm import Session
from app.database.models import UserProfile

def get_user_profile(db: Session, user_id: int):
    """
    Fetch user profile from the database
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if not profile:
        return None
        
    return {
        "userId": profile.user_id,
        "fullName": profile.full_name,
        "email": profile.email,
        "dob": profile.dob,
        "age": profile.age,
        "college": profile.college,
        "address": profile.address,
        "phone": profile.phone,
        "photoUrl": profile.photo_url,
        "gender": profile.gender
    }

def create_or_update_profile(db: Session, profile_data: dict):
    """
    Create or update a user profile
    """
    user_id = profile_data.get("user_id")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if profile:
        # Update existing
        for key, value in profile_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
    else:
        # Create new
        profile = UserProfile(**profile_data)
        db.add(profile)
    
    db.commit()
    db.refresh(profile)
    return profile
