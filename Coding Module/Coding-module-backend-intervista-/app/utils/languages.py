"""
Language configuration — single source of truth for all language IDs,
boilerplate templates, and display metadata.

Admin uses language keys (e.g. "python") in question JSON.
Backend resolves them to Judge0 language_id integers here.
"""

from typing import Dict, Optional

# ── Language ID map ───────────────────────────────────────────────────────────
LANGUAGE_MAP: Dict[str, int] = {
    "python":     71,
    "javascript": 63,
    "java":       62,
    "cpp":        54,
    "c":          50,
    "csharp":     51,
    "typescript": 74,
    "r":          80,
    "go":         60,
    "rust":       73,
    "ruby":       72,
    "kotlin":     78,
    "swift":      83,
}

LANGUAGE_ID_TO_NAME: Dict[int, str] = {v: k for k, v in LANGUAGE_MAP.items()}

# ── Display names for frontend dropdowns ──────────────────────────────────────
LANGUAGE_DISPLAY: Dict[str, str] = {
    "python":     "Python 3",
    "javascript": "JavaScript (Node.js)",
    "java":       "Java",
    "cpp":        "C++",
    "c":          "C",
    "csharp":     "C#",
    "typescript": "TypeScript",
    "r":          "R",
    "go":         "Go",
    "rust":       "Rust",
    "ruby":       "Ruby",
    "kotlin":     "Kotlin",
    "swift":      "Swift",
}

# ── Default boilerplate stubs per language ────────────────────────────────────
# Used when admin does NOT provide a custom boilerplate for a language.
# The placeholder {FUNCTION_NAME} is replaced at runtime.
DEFAULT_BOILERPLATES: Dict[str, str] = {
    "python": (
        "def {FUNCTION_NAME}({PARAMS}):\n"
        "    # Write your solution here\n"
        "    pass\n"
    ),
    "javascript": (
        "/**\n"
        " * @param {{{PARAMS}}}\n"
        " * @return {{}}\n"
        " */\n"
        "function {FUNCTION_NAME}({PARAMS}) {\n"
        "    // Write your solution here\n"
        "};\n"
    ),
    "java": (
        "class Solution {{\n"
        "    public Object {FUNCTION_NAME}({PARAMS}) {{\n"
        "        // Write your solution here\n"
        "        return null;\n"
        "    }}\n"
        "}}\n"
    ),
    "cpp": (
        "class Solution {{\n"
        "public:\n"
        "    auto {FUNCTION_NAME}({PARAMS}) {{\n"
        "        // Write your solution here\n"
        "    }}\n"
        "}};\n"
    ),
}


def get_language_id(language: str) -> Optional[int]:
    """Resolve language name string → Judge0 integer ID. Returns None if unknown."""
    return LANGUAGE_MAP.get(language.lower().strip())


def get_language_name(language_id: int) -> Optional[str]:
    """Resolve Judge0 ID → language name string."""
    return LANGUAGE_ID_TO_NAME.get(language_id)


def is_supported(language: str) -> bool:
    return language.lower().strip() in LANGUAGE_MAP
