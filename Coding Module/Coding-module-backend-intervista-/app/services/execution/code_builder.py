"""
Code Builder — v5
-----------------
The key design decision in v5:

  Boilerplate already contains input handling, function signature,
  and any language-specific structure. The admin defines it per language.

  So the code builder's ONLY job is:
    → Return user_code as-is.

  We do NOT inject drivers, parse inputs, or modify the code in any way.
  The candidate's source_code (which was scaffolded from the boilerplate)
  is sent directly to Judge0 with the test case input as stdin.

This eliminates the #1 source of bugs in the previous version.
"""


def build_code(source_code: str) -> str:
    """
    Return source_code unchanged.
    Input handling is already part of the boilerplate the candidate coded against.
    """
    return source_code


def get_boilerplate_for_language(question, language: str) -> str:
    """
    Return the boilerplate source code for a specific language from the question.
    Falls back to a generic stub if the language isn't in the question's boilerplates.
    """
    bp = question.boilerplates.get(language)
    if bp:
        if isinstance(bp, dict):
            return bp.get("code") or bp.get("source_code") or bp.get("template", "")
        else:
            return getattr(bp, "code", getattr(bp, "source_code", getattr(bp, "template", "")))

    # Fallback: generic stub with language name
    return f"# {language} — write your solution here\n"
