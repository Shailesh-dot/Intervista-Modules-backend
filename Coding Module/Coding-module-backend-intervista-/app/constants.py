from typing import Dict

# ── Language Mappings ─────────────────────────────────────────────────────────
LANGUAGE_MAP: Dict[str, int] = {
    "python": 71,
    "python3": 71,
    "javascript": 63,
    "js": 63,
    "java": 62,
    "cpp": 54,
    "c++": 54,
    "c": 50,
    "typescript": 74,
    "go": 60,
    "rust": 73,
    "ruby": 72,
}

LANGUAGE_ID_MAP: Dict[int, str] = {v: k for k, v in LANGUAGE_MAP.items()}

# ── Judge0 Defaults ───────────────────────────────────────────────────────────
DEFAULT_TIME_LIMIT = 2
DEFAULT_MEMORY_LIMIT = 128000
JUDGE0_POLL_INTERVAL = 1.0
JUDGE0_MAX_RETRIES = 10

# ── Judge0 Status Codes ───────────────────────────────────────────────────────
JUDGE0_STATUS: Dict[int, str] = {
    1: "In Queue",
    2: "Processing",
    3: "Accepted",
    4: "Wrong Answer",
    5: "Time Limit Exceeded",
    6: "Compilation Error",
    7: "Runtime Error (SIGSEGV)",
    8: "Runtime Error (SIGXFSZ)",
    9: "Runtime Error (SIGFPE)",
    10: "Runtime Error (SIGABRT)",
    11: "Runtime Error (NZEC)",
    12: "Runtime Error (Other)",
    13: "Internal Error",
    14: "Exec Format Error",
}

STATUS_IN_QUEUE = 1
STATUS_PROCESSING = 2
STATUS_ACCEPTED = 3
STATUS_WRONG_ANSWER = 4
STATUS_COMPILE_ERROR = 6

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

VERDICT_ACCEPTED = "Accepted"
VERDICT_WRONG_ANSWER = "Wrong Answer"
VERDICT_COMPILE_ERROR = "Compilation Error"
VERDICT_RUNTIME_ERROR = "Runtime Error"
VERDICT_TLE = "Time Limit Exceeded"
VERDICT_PARTIAL = "Partial"
