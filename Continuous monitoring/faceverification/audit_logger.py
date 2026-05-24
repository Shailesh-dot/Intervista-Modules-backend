"""
audit_logger.py
---------------
Structured JSON audit trail for every authorisation decision.
Writes one JSON line per event to a rotating log file AND to the
Python logging system (for aggregators like ELK / Splunk).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import time
from pathlib import Path
from typing import Optional

from face_engine import FaceAuthResult, AuthStatus

logger = logging.getLogger(__name__)

_AUDIT_LOGGER_NAME = "face_auth.audit"


class AuditLogger:
    """
    Append-only, structured audit logger.

    Parameters
    ----------
    log_dir : str | Path
        Directory where audit logs are written.
    max_bytes : int
        Rotate log file when it exceeds this size.
    backup_count : int
        Number of rotated files to keep.
    actor_id : str, optional
        An identifier for the system / gate / door running this engine.
    """

    def __init__(
        self,
        log_dir: str | Path = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 10,
        actor_id: str = "default-gate",
    ) -> None:
        self.actor_id = actor_id
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / "face_auth_audit.jsonl"

        # Dedicated audit logger (separate from root logger)
        self._audit = logging.getLogger(_AUDIT_LOGGER_NAME)
        self._audit.setLevel(logging.INFO)
        self._audit.propagate = False  # don't double-log to root

        handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._audit.addHandler(handler)

        logger.info("AuditLogger initialised → %s", log_file)

    def log(
        self,
        result: FaceAuthResult,
        source: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        """
        Record an authorisation result.

        Parameters
        ----------
        result : FaceAuthResult
        source : str, optional
            Image path / camera ID / stream URL.
        extra : dict, optional
            Any additional metadata to include in the audit record.
        """
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(result.timestamp)),
            "actor_id": self.actor_id,
            "status": result.status.name,
            "authorised": result.authorised,
            "faces_detected": result.faces_detected,
            "confidence": result.confidence,
            "latency_ms": result.latency_ms,
            "message": result.message,
            "source": source,
        }
        if extra:
            record.update(extra)

        line = json.dumps(record, separators=(",", ":"))
        self._audit.info(line)

        # Mirror to root logger at appropriate level
        lvl = logging.INFO if result.authorised else logging.WARNING
        logging.log(lvl, "[AUDIT] %s | %s", result.status.name, result.message)
