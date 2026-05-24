"""
Thin compatibility wrapper.
All evaluation logic is in app/services/execution/evaluator.py
"""
from app.services.execution.evaluator import evaluate_submission
__all__ = ["evaluate_submission"]
