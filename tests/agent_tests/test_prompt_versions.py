
from pathlib import Path


# Locate the project root directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

V1_PATH = (
    PROJECT_ROOT
    / "agents"
    / "prompts"
    / "version"
    / "v1"
    / "request_analysis.txt"
)

V2_PATH = (
    PROJECT_ROOT
    / "agents"
    / "prompts"
    / "version"
    / "v2"
    / "request_analysis.txt"
)


def load_prompt(path):
    """Read a prompt file and return its contents."""
    assert path.exists(), f"Prompt file not found: {path}"
    return path.read_text(encoding="utf-8")


def test_both_prompt_versions_exist():
    assert V1_PATH.exists()
    assert V2_PATH.exists()


def test_both_prompts_are_not_empty():
    assert load_prompt(V1_PATH).strip()
    assert load_prompt(V2_PATH).strip()


def test_v1_contains_basic_extraction_instructions():
    prompt = load_prompt(V1_PATH).lower()

    assert "patient id" in prompt
    assert "policy id" in prompt
    assert "medical procedure" in prompt
    assert "do not invent" in prompt


def test_v2_contains_detailed_validation_instructions():
    prompt = load_prompt(V2_PATH).lower()

    assert "validation checks" in prompt
    assert "completed months" in prompt
    assert "contradictory information" in prompt
    assert "human review" in prompt


def test_v2_contains_structured_json_output():
    prompt = load_prompt(V2_PATH).lower()

    assert "expected output" in prompt
    assert "missing_information" in prompt
    assert "validation_issues" in prompt
    assert "escalation_flags" in prompt


def test_v2_has_prompt_injection_protection():
    prompt = load_prompt(V2_PATH).lower()

    assert "instructions contained inside" in prompt
    assert "treat instructions" in prompt


def test_v2_does_not_allow_coverage_decisions():
    prompt = load_prompt(V2_PATH).lower()

    assert "do not calculate or decide policy coverage" in prompt
    assert "do not recommend approval or rejection" in prompt


def test_v2_is_more_detailed_than_v1():
    v1 = load_prompt(V1_PATH)
    v2 = load_prompt(V2_PATH)

    assert len(v2) > len(v1)
