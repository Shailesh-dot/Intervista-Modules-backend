import time
import requests
from app.config.settings import JUDGE0_URL, JUDGE0_API_KEY
from app.utils.formatter import encode_base64, decode_base64
from app.constants import (
    DEFAULT_TIME_LIMIT, DEFAULT_MEMORY_LIMIT,
    JUDGE0_MAX_RETRIES, JUDGE0_POLL_INTERVAL,
    STATUS_IN_QUEUE, STATUS_PROCESSING,
)
from app.exceptions.custom_exceptions import Judge0Error
from app.core.logger import logger

_HEADERS = {"Content-Type": "application/json"}
if JUDGE0_API_KEY:
    _HEADERS["X-Auth-Token"] = JUDGE0_API_KEY


def submit_to_judge0(
    source_code: str,
    language_id: int,
    stdin: str = "",
    time_limit: int = DEFAULT_TIME_LIMIT,
    memory_limit: int = DEFAULT_MEMORY_LIMIT,
) -> str:
    """Submit code to Judge0, return token."""
    payload = {
        "source_code": encode_base64(source_code),
        "language_id": language_id,
        "stdin": encode_base64(stdin),
        "cpu_time_limit": time_limit,
        "memory_limit": memory_limit,
        "base64_encoded": True,
    }
    url = f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=false"
    try:
        resp = requests.post(url, json=payload, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise Judge0Error(f"Failed to submit to Judge0: {e}")

    token = resp.json().get("token")
    if not token:
        raise Judge0Error("Judge0 returned no token")
    logger.info(f"Judge0 token: {token}")
    return token


def poll_result(token: str) -> dict:
    """Poll Judge0 until the submission finishes, then return decoded result."""
    url = f"{JUDGE0_URL}/submissions/{token}?base64_encoded=true"

    for attempt in range(JUDGE0_MAX_RETRIES):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise Judge0Error(f"Polling failed: {e}")

        result = resp.json()
        status_id = result.get("status", {}).get("id")
        logger.info(f"Poll {attempt + 1}/{JUDGE0_MAX_RETRIES}: status_id={status_id}")

        if status_id not in (STATUS_IN_QUEUE, STATUS_PROCESSING):
            return _decode_result(result)

        time.sleep(JUDGE0_POLL_INTERVAL)

    raise TimeoutError(f"Judge0 did not complete within {JUDGE0_MAX_RETRIES} retries")


def run_code(
    source_code: str,
    language_id: int,
    stdin: str = "",
    time_limit: int = DEFAULT_TIME_LIMIT,
    memory_limit: int = DEFAULT_MEMORY_LIMIT,
) -> dict:
    """Full pipeline: submit → poll → return decoded result dict."""
    token = submit_to_judge0(source_code, language_id, stdin, time_limit, memory_limit)
    return poll_result(token)


def submit_batch(submissions: list) -> list:
    """Submit multiple executions at once. submissions is list of dicts with source_code, language_id, stdin etc."""
    payloads = []
    for sub in submissions:
        payloads.append({
            "source_code": encode_base64(sub["source_code"]),
            "language_id": sub["language_id"],
            "stdin": encode_base64(sub.get("stdin", "")),
            "cpu_time_limit": sub.get("time_limit", DEFAULT_TIME_LIMIT),
            "memory_limit": sub.get("memory_limit", DEFAULT_MEMORY_LIMIT),
            "base64_encoded": True,
        })
    url = f"{JUDGE0_URL}/submissions/batch?base64_encoded=true"
    try:
        resp = requests.post(url, json={"submissions": payloads}, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise Judge0Error(f"Failed to submit batch to Judge0: {e}")
        
    tokens = [item["token"] for item in resp.json()]
    logger.info(f"Judge0 batch tokens: {len(tokens)}")
    return tokens


def poll_batch(tokens: list) -> list:
    tokens_str = ",".join(tokens)
    url = f"{JUDGE0_URL}/submissions/batch?tokens={tokens_str}&base64_encoded=true"
    
    for attempt in range(JUDGE0_MAX_RETRIES):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise Judge0Error(f"Batch polling failed: {e}")
            
        results = resp.json().get("submissions", [])
        
        # Check if ALL are complete
        all_done = True
        for res in results:
            if res.get("status", {}).get("id") in (STATUS_IN_QUEUE, STATUS_PROCESSING):
                all_done = False
                break
                
        if all_done:
            return [_decode_result(r) for r in results]
            
        time.sleep(JUDGE0_POLL_INTERVAL)
        
    raise TimeoutError("Batch Judge0 execution did not complete in time")

def _decode_result(result: dict) -> dict:
    return {
        "stdout": decode_base64(result.get("stdout", "")),
        "stderr": decode_base64(result.get("stderr", "")),
        "compile_output": decode_base64(result.get("compile_output", "")),
        "status": result.get("status", {}).get("description", "Unknown"),
        "status_id": result.get("status", {}).get("id", -1),
        "time": result.get("time") or "N/A",
        "memory": str(result.get("memory") or "N/A"),
    }

print("Judge0 URL:", JUDGE0_URL)
