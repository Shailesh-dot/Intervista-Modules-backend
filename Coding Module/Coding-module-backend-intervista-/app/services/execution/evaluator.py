"""
Evaluator Engine — v5
---------------------
Runs each test case separately through Judge0.
Each call: source_code → Judge0, stdin = test_case.input

Handles:
  - Compilation errors  (short-circuit all remaining cases)
  - Runtime errors      (stderr present, mark failed)
  - Wrong answer        (stdout != expected_output)
  - Correct output      (normalized comparison)
  - Hidden TC masking   (input/expected shown as **hidden**)
"""

from typing import List, Tuple
from app.schemas.question_schema import Question, TestCase
from app.schemas.submission_schema import TestCaseResult, SubmissionResult
from app.services.execution.code_builder import build_code
from app.services.judge0_service import run_code
from app.utils.formatter import normalize_output
from app.utils.id_generator import generate_id
from app.utils.time_utils import utc_now
from app.constants import (
    STATUS_COMPILE_ERROR,
    VERDICT_ACCEPTED,
    VERDICT_WRONG_ANSWER,
    VERDICT_COMPILE_ERROR,
    VERDICT_RUNTIME_ERROR,
    VERDICT_PARTIAL,
)
from app.core.logger import logger


def evaluate_submission(
    question: Question,
    source_code: str,
    language: str,
    language_id: int,
    candidate_id: str = "anonymous",
) -> SubmissionResult:
    """
    Run all visible + hidden test cases, one per Judge0 call.
    stdin = test_case.input for each call.
    """
    final_code = build_code(source_code)

    visible: List[Tuple[TestCase, bool]] = [(tc, False) for tc in question.visible_test_cases]
    hidden:  List[Tuple[TestCase, bool]] = [(tc, True)  for tc in question.hidden_test_cases]
    all_cases = visible + hidden

    test_case_results: List[TestCaseResult] = []
    compile_output = ""
    passed = 0

    for i, (tc, is_hidden) in enumerate(all_cases):
        label = f"TC {i + 1}/{'hidden' if is_hidden else 'visible'}"
        logger.info(f"Running {label} | lang={language}")

        # Each test case: send full source_code, pass test input as stdin
        result = run_code(
            source_code=final_code,
            language_id=language_id,
            stdin=tc.input,
        )

        # ── Compilation error → short-circuit all remaining ────────────────
        if result["status_id"] == STATUS_COMPILE_ERROR:
            compile_output = result["compile_output"]
            logger.warning(f"Compile error at {label}: {compile_output[:100]}")
            for j, (rem_tc, rem_hidden) in enumerate(all_cases):
                if j < i:
                    continue
                test_case_results.append(_make_result(
                    index=j + 1, tc=rem_tc, actual="", stderr="",
                    passed=False, status="Compilation Error", is_hidden=rem_hidden,
                ))
            break

        actual   = normalize_output(result["stdout"])
        expected = normalize_output(tc.expected_output)
        stderr   = result.get("stderr", "").strip()

        # ── Runtime error → stderr present, mark failed ────────────────────
        if stderr and result["status_id"] not in (3, 4):
            is_correct = False
            status_label = result["status"]  # e.g. "Runtime Error (NZEC)"
        else:
            is_correct   = (actual == expected)
            status_label = result["status"]

        if is_correct:
            passed += 1

        # Mask hidden TC details
        display_input    = "**hidden**" if is_hidden else tc.input
        display_expected = "**hidden**" if is_hidden else expected
        display_actual   = actual if not is_hidden else ("✓" if is_correct else "✗")
        display_stderr   = "" if is_hidden else stderr

        test_case_results.append(TestCaseResult(
            test_case_index=i + 1,
            input=display_input,
            expected_output=display_expected,
            actual_output=display_actual,
            passed=is_correct,
            status=status_label,
            stderr=display_stderr,
            is_hidden=is_hidden,
        ))

    total = len(all_cases)
    score = round((passed / total) * 100, 2) if total > 0 else 0.0

    if compile_output:
        verdict = VERDICT_COMPILE_ERROR
    elif passed == total:
        verdict = VERDICT_ACCEPTED
    elif passed == 0:
        verdict = VERDICT_WRONG_ANSWER
    else:
        verdict = f"{VERDICT_PARTIAL} ({passed}/{total} passed)"

    return SubmissionResult(
        submission_id=generate_id(),
        question_id=question.id,
        candidate_id=candidate_id,
        language=language,
        total_test_cases=total,
        passed_test_cases=passed,
        score=score,
        verdict=verdict,
        test_case_results=test_case_results,
        compile_output=compile_output,
        submitted_at=utc_now(),
    )


def _make_result(index, tc, actual, stderr, passed, status, is_hidden) -> TestCaseResult:
    return TestCaseResult(
        test_case_index=index,
        input="**hidden**" if is_hidden else tc.input,
        expected_output="**hidden**" if is_hidden else tc.expected_output,
        actual_output=actual,
        passed=passed,
        status=status,
        stderr="" if is_hidden else stderr,
        is_hidden=is_hidden,
    )
