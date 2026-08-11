"""
Test suite for DispatchPreambleValidator.

Verifies that subagent dispatch prompts are programmatically checked for mandatory
governance preamble markers (constitution, §1.9 Zero-Mocking, 3-Layer DoD, RED-GREEN-REFACTOR,
build/test commands, view_file mandate) and that skills/feature-driven-implementation/SKILL.md
documents these requirements and the subagent failure protocol.
"""

import os
import pytest
from parity_auditor.validators.dispatch_preamble_validator import (
    DispatchPreambleValidator,
    validate_dispatch_prompt,
    MANDATORY_PREAMBLE_MARKERS,
)

COMPLIANT_PROMPT = """
You are a context-isolated subagent.
Adopt the feature-driven-implementation skill.
First step: Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1 before doing any file edits.
Obey Section 1.9 Zero-Mocking Live Persistence Mandate.
Adhere strictly to 3-Layer Definition of Done (DoD).
Follow the RED-GREEN-REFACTOR cycle strictly.
Verify using flutter analyze (0 issues), flutter test (all pass).
Implement Micro-Task 1: Create widget model. PROCEED
"""

DEGRADED_PROMPT_MISSING_TDD = """
You are a context-isolated subagent.
Adopt the feature-driven-implementation skill.
First step: Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1 before doing any file edits.
Obey Section 1.9 Zero-Mocking Live Persistence Mandate.
Adhere strictly to 3-Layer Definition of Done (DoD).
Verify using flutter analyze (0 issues), flutter test (all pass).
Implement Micro-Task 1: Create widget model. PROCEED
"""

EMPTY_PROMPT = "Implement Micro-Task 1: Create widget model. PROCEED"


def test_mandatory_markers_constant_completeness():
    """Verify MANDATORY_PREAMBLE_MARKERS contains all 6 required governance markers."""
    assert len(MANDATORY_PREAMBLE_MARKERS) >= 6
    expected_substrings = [
        "feature-driven-implementation",
        "view_file",
        "1.9 Zero-Mocking",
        "3-Layer Definition of Done",
        "RED-GREEN-REFACTOR",
        "flutter analyze",
    ]
    for expected in expected_substrings:
        assert any(expected in marker for marker in MANDATORY_PREAMBLE_MARKERS), (
            f"Expected substring '{expected}' missing from MANDATORY_PREAMBLE_MARKERS"
        )


def test_validate_dispatch_prompt_positive():
    """Compliant prompt with all preamble markers returns empty missing list."""
    missing = validate_dispatch_prompt(COMPLIANT_PROMPT)
    assert missing == [], f"Expected no missing markers, got: {missing}"


def test_validate_dispatch_prompt_negative_degraded():
    """Degraded prompt missing RED-GREEN-REFACTOR returns the missing marker."""
    missing = validate_dispatch_prompt(DEGRADED_PROMPT_MISSING_TDD)
    assert len(missing) == 1
    assert "RED-GREEN-REFACTOR" in missing[0]


def test_validate_dispatch_prompt_negative_empty():
    """Bare prompt missing all preamble markers returns all mandatory markers."""
    missing = validate_dispatch_prompt(EMPTY_PROMPT)
    assert len(missing) == len(MANDATORY_PREAMBLE_MARKERS)


def test_validator_class_structure():
    """DispatchPreambleValidator class instantiates and validates prompt text."""
    validator = DispatchPreambleValidator()
    missing = validator.validate_prompt(COMPLIANT_PROMPT)
    assert missing == []

    missing_degraded = validator.validate_prompt(DEGRADED_PROMPT_MISSING_TDD)
    assert len(missing_degraded) == 1


def test_feature_driven_implementation_skill_documentation():
    """Verify skills/feature-driven-implementation/SKILL.md documents the preamble markers and failure protocol."""
    skill_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../skills/feature-driven-implementation/SKILL.md",
        )
    )
    assert os.path.exists(skill_path), f"Skill file not found at {skill_path}"

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check verbatim markers/terms documented
    assert "Governance Preamble" in content or "governance preamble" in content.lower()
    assert "Zero-Mocking" in content
    assert "3-Layer Definition of Done" in content or "3-Layer DoD" in content
    assert "RED-GREEN-REFACTOR" in content
    assert "view_file" in content
    assert "flutter analyze" in content or "build/test" in content.lower()

    # Check failure protocol documented
    assert "empty result" in content.lower()
    assert "two consecutive failures" in content.lower()
    assert "escalate" in content.lower()


def test_feature_driven_implementation_subagent_retry_limit_guard():
    """Verify skills/feature-driven-implementation/SKILL.md contains bounded retry limit and escalation guard terms."""
    skill_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../skills/feature-driven-implementation/SKILL.md",
        )
    )
    assert os.path.exists(skill_path), f"Skill file not found at {skill_path}"

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Output Integrity Verification" in content
    assert "subagent_dispatch_retry" in content
    assert "RETRY_LIMIT_EXCEEDED" in content
    assert "DONE (integrity verified)" in content or "integrity verified" in content


def test_feature_driven_implementation_preamble_sentinel_and_read_instruction_issue387():
    """Verify skills/feature-driven-implementation/SKILL.md documents Preamble Integrity Sentinel (---GOVERNANCE-END---) and mandatory SKILL.md and profile reading instruction (Issue #387)."""
    skill_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../skills/feature-driven-implementation/SKILL.md",
        )
    )
    assert os.path.exists(skill_path), f"Skill file not found at {skill_path}"

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify Preamble Integrity Sentinel (---GOVERNANCE-END---) token requirement
    assert "---GOVERNANCE-END---" in content, (
        "skills/feature-driven-implementation/SKILL.md must contain '---GOVERNANCE-END---' sentinel token line"
    )
    assert "Preamble Integrity Sentinel" in content, (
        "skills/feature-driven-implementation/SKILL.md must specify 'Preamble Integrity Sentinel'"
    )

    # Verify Mandatory Skill and Profile Read instruction
    assert "Mandatory Skill and Profile Read" in content, (
        "skills/feature-driven-implementation/SKILL.md must state 'Mandatory Skill and Profile Read'"
    )
    assert "active SKILL.md file by explicit path" in content or "SKILL.md" in content
    assert ".pipeline/profiles/" in content


def test_feature_driven_implementation_governance_acknowledgment_issue386():
    """Verify skills/feature-driven-implementation/SKILL.md documents Mandatory Governance Acknowledgment, Governance Adherence Check, and invariant rules (Issue #386)."""
    skill_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../skills/feature-driven-implementation/SKILL.md",
        )
    )
    assert os.path.exists(skill_path), f"Skill file not found at {skill_path}"

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Verify Mandatory Governance Acknowledgment section present
    assert "Mandatory Governance Acknowledgment" in content, (
        "skills/feature-driven-implementation/SKILL.md must contain 'Mandatory Governance Acknowledgment'"
    )

    # 2. Verify 4 governance items required in acknowledgment
    assert "Section 1.9 Zero-Mocking" in content or "Zero-Mocking Live Persistence Mandate" in content, (
        "SKILL.md must mandate acknowledgment of Section 1.9 Zero-Mocking"
    )
    assert "3-layer LUI Definition of Done" in content or "3-layer LUI" in content or "3-layer DoD" in content, (
        "SKILL.md must mandate acknowledgment of 3-layer LUI DoD"
    )
    assert ".pipeline/profiles/" in content, (
        "SKILL.md must mandate acknowledgment of target platform profile"
    )
    assert "TDD RED-GREEN-REFACTOR" in content or "RED-GREEN-REFACTOR" in content, (
        "SKILL.md must mandate acknowledgment of TDD RED-GREEN-REFACTOR cycle"
    )

    # 3. Verify Governance Adherence Check in Stage 1 Spec Compliance Review
    assert "Governance Adherence Check" in content, (
        "skills/feature-driven-implementation/SKILL.md must contain 'Governance Adherence Check' in Stage 1 review"
    )

    # 4. Verify Invariant rule regarding governance acknowledgment
    assert "governance acknowledgment" in content.lower(), (
        "skills/feature-driven-implementation/SKILL.md must state governance acknowledgment rule in invariants"
    )



