import os
import sys
import tempfile

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import reconcile_epic_checklists

def test_reconcile_epic_checklists_resolves_issue_0_nested_headers():
    epic_content = (
        "# Epic 01: Geo Location Framework\n\n"
        "## 1. Executive Summary\n"
        "Summary text.\n\n"
        "## 2. Requirements & Checklist\n\n"
        "- [ ] #0 - [Location Tracking Feature](docs/features/feat-01-location.md) (semantic linkage justification)\n\n"
        "### Associated Use Cases & User Stories\n\n"
        "#### Associated Use Cases\n\n"
        "- [ ] #0 - [GPS Signal Ingestion Use Case](docs/use-cases/uc-01-gps.md) (semantic linkage justification)\n\n"
        "#### Associated User Stories\n\n"
        "- [ ] #0 - [Coordinate Reporting Story](docs/user-stories/us-01-coords.md) (semantic linkage justification)\n\n"
        "## 3. Architecture & Design\n"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        epic_path = os.path.join(tmpdir, "epic-01-geo-location-framework.md")
        with open(epic_path, "w", encoding="utf-8") as f:
            f.write(epic_content)

        child_features = [("feat-01-location", "Location Tracking Feature")]
        child_stories = [("us-01-coords", "Coordinate Reporting Story")]
        child_usecases = [("uc-01-gps", "GPS Signal Ingestion Use Case")]

        feature_titles = {"location tracking feature": 101}
        usecase_titles = {"gps signal ingestion use case": 201}
        story_titles = {"coordinate reporting story": 301}

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
            feature_titles=feature_titles,
            story_titles=story_titles,
            usecase_titles=usecase_titles,
            rules=rules
        )

        with open(epic_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        # Assert no #0 placeholder remains anywhere in updated content
        assert "#0" not in updated_content

        # Assert issue numbers 101, 201, 301 are resolved
        assert "#101" in updated_content
        assert "#201" in updated_content
        assert "#301" in updated_content

        # Verify child files listed under appropriate subheadings
        assert "feat-01-location.md" in updated_content
        assert "uc-01-gps.md" in updated_content
        assert "us-01-coords.md" in updated_content
