import uuid


def generate_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def generate_short_id(prefix: str = "") -> str:
    """Generate a short 8-char ID, optionally prefixed. E.g. 'q_a3f9b1c2'"""
    short = uuid.uuid4().hex[:8]
    return f"{prefix}{short}" if prefix else short
