"""Tests for UmlValidator empty *(None registered)* checklist placeholder detection (Issue #239)."""
import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from parity_auditor.validators.uml import UmlValidator
from parity_auditor.core.workspace import WorkspaceRepository


def _setup_workspace(epic_content, has_usecase=True, has_userstory=False):
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {
            "features": "features",
            "user_stories": "user_stories",
            "use_cases": "use_cases",
            "epics": "epics"
        },
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "use_case_flow_limit": 0,
            "use_case_step_limit": 0,
            "use_case_alternate_flows_header": "## 5. Alternate and Exception Flows",
            "use_case_flow_list_regex": r"###\s+Flow.*?(?=\n###\s+Flow|\Z)",
            "use_case_numbered_step_regex": r"^\d+\.",
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean", "void"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "epic": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements & Checklist", "Requirements & Checklist"]
                ],
                "use_case": [
                    ["## 1. Overview", "Overview"]
                ],
                "user_story": [
                    ["## 1. Overview", "Overview"]
                ]
            },
            "required_diagrams": {"epic": [], "use_case": [], "user_story": []}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    user_stories_dir = os.path.join(tmpdir, "user_stories")
    use_cases_dir = os.path.join(tmpdir, "use_cases")
    epics_dir = os.path.join(tmpdir, "epics")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(user_stories_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)
    os.makedirs(epics_dir, exist_ok=True)

    if has_usecase:
        uc_content = """---
generation_mode: subagent
title: Test UC
---
## 1. Overview
Test UC

## 5. Alternate and Exception Flows
### Flow 1: Alt Flow One
1. Step one
2. Step two
3. Step three

### Flow 2: Alt Flow Two
1. Step one
2. Step two
3. Step three
"""
        with open(os.path.join(use_cases_dir, "uc-01-test.md"), "w") as f:
            f.write(uc_content)

    if has_userstory:
        us_content = """---
generation_mode: subagent
title: Test US
---
## 1. Overview
Test US
"""
        with open(os.path.join(user_stories_dir, "us-01-test.md"), "w") as f:
            f.write(us_content)

    with open(os.path.join(epics_dir, "epic-01-test.md"), "w") as f:
        f.write(epic_content)

    return tmpdir


def test_epic_empty_none_registered_checklist_flagged_when_usecase_exists():
    """Epic containing *(None registered)* checklist placeholder should be flagged when Use Cases exist in workspace."""
    epic_content = """---
generation_mode: subagent
title: Test Epic
---

## 1. Overview
Epic overview text.

## 2. Requirements & Checklist
### User Stories / Use Cases
*(None registered)*
"""
    tmpdir = _setup_workspace(epic_content, has_usecase=True, has_userstory=False)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        placeholder_errors = [e for e in errors if "epic-01-test.md" in e and ("None registered" in e or "placeholder" in e)]
        assert len(placeholder_errors) >= 1, f"Expected error for *(None registered)* placeholder in Epic, got errors: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_epic_none_registered_not_flagged_when_no_uc_or_us():
    """Epic containing *(None registered)* should not be flagged when no UC or US exist in workspace."""
    epic_content = """---
generation_mode: subagent
title: Test Epic
---

## 1. Overview
Epic overview text.

## 2. Requirements & Checklist
### User Stories / Use Cases
*(None registered)*
"""
    tmpdir = _setup_workspace(epic_content, has_usecase=False, has_userstory=False)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        placeholder_errors = [e for e in errors if "epic-01-test.md" in e and ("None registered" in e or "placeholder" in e)]
        assert len(placeholder_errors) == 0, f"Did not expect placeholder error when no UC/US exist, got: {placeholder_errors}"
    finally:
        shutil.rmtree(tmpdir)
