import base64


def normalize_output(output: str) -> str:
    """Strip whitespace and normalize line endings for comparison."""
    return (output or "").strip().replace("\r\n", "\n").replace("\r", "\n")


def decode_base64(value: str) -> str:
    """Safely decode a base64 string from Judge0."""
    if not value:
        return ""
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return value


def encode_base64(value: str) -> str:
    """Encode a plain string to base64 for Judge0."""
    return base64.b64encode((value or "").encode("utf-8")).decode("utf-8")
