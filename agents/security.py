
import re


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"reveal\s+(the\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(the\s+)?system\s+prompt",
    r"bypass\s+(the\s+)?(rules|policy|restrictions|instructions)",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"always\s+approve",
    r"approve\s+(this\s+)?(claim|request|admission)\s+regardless",
    r"act\s+as\s+(an?\s+)?(unrestricted|unfiltered)",
]


def detect_prompt_injection(text: str) -> dict:
    """
    Checks untrusted user-provided text for common
    prompt-injection instructions.

    This is a basic rule-based security check.
    It does not replace a dedicated security classifier.
    """

    if not isinstance(text, str):
        return {
            "is_suspicious": True,
            "matched_patterns": ["invalid_input_type"],
        }

    matched_patterns = []

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matched_patterns.append(pattern)

    return {
        "is_suspicious": len(matched_patterns) > 0,
        "matched_patterns": matched_patterns,
    }


def check_request_for_injection(request) -> dict:
    """
    Checks free-text request fields that may contain
    untrusted patient-provided information.
    """

    fields_to_check = [
        "procedure",
        "diagnosis",
    ]

    findings = {}

    for field in fields_to_check:
        value = getattr(request, field, None)

        if value:
            result = detect_prompt_injection(value)

            if result["is_suspicious"]:
                findings[field] = result["matched_patterns"]

    return {
        "is_suspicious": len(findings) > 0,
        "findings": findings,
    }
