import os
import sys
import tempfile
import subprocess

# Ensure skills/spec-orchestrator/scripts is in sys.path
SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import extract_epic_from_body, main

def test_extract_epic_from_body_markdown_link():
    content = (
        "# Feature 01: Ingestion\n\n"
        "## Description\n"
        "Some details about [Epic 01](../epics/epic-01-geo-location.md) linkage.\n"
    )
    assert extract_epic_from_body(content) == "epic-01-geo-location"

def test_extract_epic_from_body_parent_epic_section_issue_id():
    content = (
        "# Feature 01: Ingestion\n\n"
        "## Parent Epic\n"
        "- [ ] #101\n"
    )
    assert extract_epic_from_body(content) == "#101"

def test_extract_epic_from_body_parent_epic_section_placeholder_with_link():
    content = (
        "# Feature 01: Ingestion\n\n"
        "## Parent Epic\n"
        "- [ ] #[EpicID] - [Epic Title](../epics/epic-02-core.md) (semantic linkage justification)\n"
    )
    assert extract_epic_from_body(content) == "epic-02-core"

def test_extract_epic_from_body_explicit_text_pattern():
    content = (
        "# Feature 01: Ingestion\n\n"
        "Parent Epic: epic-03-types\n"
    )
    assert extract_epic_from_body(content) == "epic-03-types"

def test_extract_epic_from_body_parent_epic_section_no_headers():
    content = (
        "# Feature 01: Ingestion\n\n"
        "- **Parent Epic**: [Epic 01](https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/epics/epic-01.md)\n"
    )
    assert extract_epic_from_body(content) == "epic-01"

def test_reconcile_backlog_fallback_integration(monkeypatch):
    mock_issues = [
        {
            "number": 101,
            "title": "Epic 01: Geo Location Framework",
            "labels": ["epic"],
            "state": "OPEN"
        },
        {
            "number": 102,
            "title": "Feature 01: Tracker Ingestion",
            "labels": ["feature"],
            "state": "OPEN"
        },
        {
            "number": 103,
            "title": "User Story 01: Tracker Story",
            "labels": ["user-story"],
            "state": "OPEN"
        },
        {
            "number": 104,
            "title": "Use Case 01: Tracker Use Case",
            "labels": ["use-case"],
            "state": "OPEN"
        }
    ]

    monkeypatch.setattr("reconcile_backlog.get_all_issues", lambda rules: mock_issues)

    def mock_run(cmd, *args, **kwargs):
        # Intercept the linter execution and other tracker commands
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")
    
    monkeypatch.setattr(subprocess, "run", mock_run)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mocked backlog structure in tmpdir
        epics_dir = os.path.join(tmpdir, "epics")
        features_dir = os.path.join(tmpdir, "features")
        stories_dir = os.path.join(tmpdir, "user-stories")
        usecases_dir = os.path.join(tmpdir, "use-cases")

        os.makedirs(epics_dir)
        os.makedirs(features_dir)
        os.makedirs(stories_dir)
        os.makedirs(usecases_dir)

        # Write Epic 01 (Checklist is initially empty/TBD)
        epic_content = (
            "# Epic 01: Geo Location Framework\n\n"
            "## 2. Requirements & Checklist\n"
            "- *To be populated*\n\n"
            "### Associated Use Cases & User Stories\n\n"
            "#### Associated Use Cases\n"
            "- *To be populated*\n\n"
            "#### Associated User Stories\n"
            "- *To be populated*\n"
        )
        epic_path = os.path.join(epics_dir, "epic-01-geo-location.md")
        with open(epic_path, "w", encoding="utf-8") as f:
            f.write(epic_content)

        # Write Feature 01 with NO frontmatter 'epic' key but parent epic in body text
        feat_content = (
            "---\n"
            "title: \"Feature 01: Tracker Ingestion\"\n"
            "---\n"
            "# Feature 01: Tracker Ingestion\n\n"
            "## Parent Epic\n"
            "- [ ] #101 - [Epic 01](../epics/epic-01-geo-location.md)\n"
        )
        feat_path = os.path.join(features_dir, "feat-01.md")
        with open(feat_path, "w", encoding="utf-8") as f:
            f.write(feat_content)

        # Write Story 01 with NO frontmatter 'epic' key but parent epic in body text
        story_content = (
            "---\n"
            "title: \"User Story 01: Tracker Story\"\n"
            "---\n"
            "# User Story 01: Tracker Story\n\n"
            "## Parent Epic\n"
            "- [ ] #101 - [Epic 01](../epics/epic-01-geo-location.md)\n"
            "\n"
            "References [feat-01](../features/feat-01.md)\n"
        )
        story_path = os.path.join(stories_dir, "us-01.md")
        with open(story_path, "w", encoding="utf-8") as f:
            f.write(story_content)

        # Write Use Case 01 with NO frontmatter 'epic' key but parent epic in body text
        usecase_content = (
            "---\n"
            "title: \"Use Case 01: Tracker Use Case\"\n"
            "---\n"
            "# Use Case 01: Tracker Use Case\n\n"
            "## Parent Epic\n"
            "- [ ] #101 - [Epic 01](../epics/epic-01-geo-location.md)\n"
            "\n"
            "References [feat-01](../features/feat-01.md) and [us-01](../user-stories/us-01.md)\n"
        )
        usecase_path = os.path.join(usecases_dir, "uc-01.md")
        with open(usecase_path, "w", encoding="utf-8") as f:
            f.write(usecase_content)

        # Mock sys.argv to point to tmpdir
        monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])

        # Run the reconciler
        main()

        # Check that the Epic 01 checklist was updated correctly by resolving references and mapping
        with open(epic_path, "r", encoding="utf-8") as f:
            updated_epic_content = f.read()

        # The checklist should now contain references to Feature 102, Story 103, and Use Case 104
        assert "#102" in updated_epic_content
        assert "#103" in updated_epic_content
        assert "#104" in updated_epic_content
        assert "feat-01.md" in updated_epic_content
        assert "us-01.md" in updated_epic_content
        assert "uc-01.md" in updated_epic_content
