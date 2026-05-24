from datetime import datetime, timezone


def utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def timestamp_label() -> str:
    """Human-readable timestamp for logs."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
