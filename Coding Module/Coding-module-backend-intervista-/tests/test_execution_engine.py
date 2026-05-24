"""
Execution engine tests — v5

v5 design: boilerplate is admin-defined, code_builder just returns source_code as-is.
Tests verify: code_builder passthrough, boilerplate retrieval, language resolution.
"""
from app.services.execution.code_builder import build_code, get_boilerplate_for_language
from app.utils.languages import get_language_id, is_supported, LANGUAGE_MAP
from app.schemas.question_schema import Question, TestCase, LanguageBoilerplate


# ── code_builder tests ─────────────────────────────────────────────────────────

def test_build_code_returns_unchanged():
    code = "a,b=map(int,input().split());print(a+b)"
    assert build_code(code) == code


def test_build_code_preserves_whitespace():
    code = "def solve():\n    return 42\nprint(solve())\n"
    assert build_code(code) == code


def test_build_code_multiline():
    code = "x = int(input())\nfor i in range(x):\n    print(i)"
    assert build_code(code) == code


# ── language config tests ──────────────────────────────────────────────────────

def test_language_id_python():
    assert get_language_id("python") == 71


def test_language_id_java():
    assert get_language_id("java") == 62


def test_language_id_cpp():
    assert get_language_id("cpp") == 54


def test_language_id_javascript():
    assert get_language_id("javascript") == 63


def test_language_id_unknown():
    assert get_language_id("brainfuck") is None


def test_is_supported_known():
    assert is_supported("python") is True
    assert is_supported("java") is True


def test_is_supported_unknown():
    assert is_supported("brainfuck") is False


def test_language_map_has_required_languages():
    for lang in ["python", "java", "cpp", "javascript", "c", "csharp", "typescript"]:
        assert lang in LANGUAGE_MAP, f"{lang} missing from LANGUAGE_MAP"


# ── boilerplate retrieval tests ────────────────────────────────────────────────

def _make_question(boilerplates: dict) -> Question:
    bps = {
        lang: LanguageBoilerplate(template=data["template"], language_id=data["language_id"])
        for lang, data in boilerplates.items()
    }
    return Question(
        id="test_q",
        title="Test",
        description="Test",
        boilerplates=bps,
        allowed_languages=list(bps.keys()),
        visible_test_cases=[TestCase(input="1", expected_output="1")],
    )


def test_get_boilerplate_known_language():
    q = _make_question({
        "python": {"template": "def solve(): pass", "language_id": 71}
    })
    template = get_boilerplate_for_language(q, "python")
    assert template == "def solve(): pass"


def test_get_boilerplate_unknown_language_fallback():
    q = _make_question({
        "python": {"template": "def solve(): pass", "language_id": 71}
    })
    template = get_boilerplate_for_language(q, "rust")
    assert "rust" in template   # fallback contains language name


def test_get_boilerplate_multiple_languages():
    q = _make_question({
        "python": {"template": "def fn(): pass", "language_id": 71},
        "java":   {"template": "class Solution {}", "language_id": 62},
    })
    assert "def fn" in get_boilerplate_for_language(q, "python")
    assert "class Solution" in get_boilerplate_for_language(q, "java")
