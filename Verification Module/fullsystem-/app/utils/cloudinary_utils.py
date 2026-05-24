import cloudinary
import cloudinary.uploader
from app.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def upload_to_cloudinary(file_path, folder="verification"):
    """
    Uploads a file to Cloudinary and returns the secure URL.
    file_path can be a local path or a file-like object.
    """
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type="auto"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None
