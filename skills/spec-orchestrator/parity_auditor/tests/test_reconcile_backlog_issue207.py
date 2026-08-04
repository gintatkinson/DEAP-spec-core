import os
import sys
import tempfile

# Ensure skills/spec-orchestrator/scripts is in sys.path
SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import normalize_title, reconcile_epic_checklists

def test_normalize_title_issue207():
    # Test title normalization with various epic reference formats
    assert normalize_title("Epic 01: Geo Location Framework") == "geo location framework"
    assert normalize_title("epic-01-geo-location-framework") == "geo location framework"
    assert normalize_title("epic-01") == "epic 01"
    assert normalize_title("Epic 01") == "epic 01"
    assert normalize_title('epic: "epic-01"') == "epic 01"
    assert normalize_title("feat-02: User Authentication") == "user authentication"
    assert normalize_title("US-03") == "us 03"
    assert normalize_title("uc-04-device-state") == "device state"

def test_reconcile_epic_checklists_placeholder_stripping():
    epic_content = (
        "# Epic 01: Geo Location Framework\n\n"
        "## 1. Executive Summary\n"
        "Summary text.\n\n"
        "## 2. Requirements & Checklist\n\n"
        "*To be populated after Phase 2*\n\n"
        "#### Associated Use Cases\n\n"
        "- *To be populated after Phase 2*\n\n"
        "#### Associated User Stories\n\n"
        "*(To be populated after Phase 3)*\n\n"
        "## 3. Architecture & Design\n"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        epic_path = os.path.join(tmpdir, "epic-01-geo-location-framework.md")
        with open(epic_path, "w", encoding="utf-8") as f:
            f.write(epic_content)

        child_features = [("feat-01-location", "Location Tracking Feature")]
        child_stories = [("us-01-coords", "Coordinate Reporting Story")]
        child_usecases = [("uc-01-gps", "GPS Signal Ingestion Use Case")]

        rules = {
            "tracker_rules": {
                "numeric_prefix": "#",
                "issue_id_placeholder": "#[IssueID]"
            }
        }

        reconcile_epic_checklists(
            epic_path,
            child_features,
            child_stories,
            child_usecases,
            epic_titles={},
            feature_titles={},
            story_titles={},
            usecase_titles={},
            rules=rules
        )

        with open(epic_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        # Placeholders under populated sections must be removed
        assert "*To be populated after Phase 2*" not in updated_content
        assert "*(To be populated after Phase 3)*" not in updated_content
        assert "- *To be populated after Phase 2*" not in updated_content

        # Child artifacts must be listed
        assert "feat-01-location.md" in updated_content
        assert "us-01-coords.md" in updated_content
        assert "uc-01-gps.md" in updated_content

def test_placeholder_regex_patterns():
    import re

    PLACEHOLDER_PATTERNS = [
        re.compile(r'^\s*[-*]*\s*\(?\s*\*?To be populated.*?\*?\)?\s*$', re.IGNORECASE),
        re.compile(r'^\s*[-*]*\s*\*?TBD\*?\s*$', re.IGNORECASE),
        re.compile(r'^\s*[-*]*\s*\*?N/A\*?\s*$', re.IGNORECASE),
    ]

    test_samples = [
        "*To be populated after Phase 2*",
        "*To be populated after Phase 3*",
        "- *To be populated after Phase 2*",
        "*(To be populated after Phase 3)*",
        "*To be populated during Phase 2*",
        "*To be populated in Phase 2*",
        "*TBD*",
        "*N/A*",
    ]

    for sample in test_samples:
        assert any(p.match(sample) for p in PLACEHOLDER_PATTERNS), f"Failed to match placeholder: {sample}"
