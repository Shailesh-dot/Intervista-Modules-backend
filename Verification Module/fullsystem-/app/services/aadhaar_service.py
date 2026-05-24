import os
import json
import cv2

from app.utils.unzipper import extract_zip
from app.utils.parser import parse_aadhaar_xml
from app.utils.id_generator import generate_unique_id
from app.utils.cloudinary_utils import upload_to_cloudinary


AADHAAR_STORAGE = "app/storage/aadhaar"


def process_aadhaar(zip_file, share_code, expected_last4):
    # Upload Original ZIP to Cloudinary
    if hasattr(zip_file, 'seek'):
        zip_file.seek(0)
    zip_url = upload_to_cloudinary(zip_file, folder="aadhaar_zips")
    data = {} # Initialize data dictionary here to allow adding zip_url
    data["aadhaar_zip_url"] = zip_url

    # Reset seek pointer for unzipping
    if hasattr(zip_file, 'seek'):
        zip_file.seek(0)

    xml_file = extract_zip(zip_file, share_code)

    data.update(parse_aadhaar_xml(xml_file)) # Update data with parsed XML content

    # Validate last 4 digits
    actual_last4 = data["masked_aadhaar"][-4:]
    if str(actual_last4) != str(expected_last4):
        raise Exception(f"Aadhaar verification failed: Entered last 4 digits ({expected_last4}) do not match the ZIP file data.")

    reference_id = data["reference_id"]

    unique_id = generate_unique_id(reference_id)

    user_folder = f"{AADHAAR_STORAGE}/{unique_id}"

    os.makedirs(user_folder, exist_ok=True)

    # Save Aadhaar Image Locally
    aadhaar_path = f"{user_folder}/aadhaar.jpg"

    with open(aadhaar_path, "wb") as f:
        f.write(data["photo"])

    # Upload Photo to Cloudinary
    photo_url = upload_to_cloudinary(aadhaar_path, folder="aadhaar_photos")
    data["aadhaar_photo_url"] = photo_url
    data["zip_url"] = zip_url # Keep this for backward compatibility and DB storage

    # Remove photo from json (binary data)
    del data["photo"]

    # Save Aadhaar details locally
    json_path = f"{user_folder}/data.json"

    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)

    return unique_id, data