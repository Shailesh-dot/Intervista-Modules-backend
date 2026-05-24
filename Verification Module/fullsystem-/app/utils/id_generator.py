import hashlib


def generate_unique_id(reference_id):

    # Create SHA256 hash
    hash_object = hashlib.sha256(reference_id.encode())

    # Convert to hex
    hash_hex = hash_object.hexdigest()

    # Take first 6 characters
    unique_id = hash_hex[:6].upper()

    return unique_id