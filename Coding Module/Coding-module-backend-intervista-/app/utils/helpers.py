import uuid
from datetime import datetime


def generate_id() -> str:
    return str(uuid.uuid4())


def current_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"
