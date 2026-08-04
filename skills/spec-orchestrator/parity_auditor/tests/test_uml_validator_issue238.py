"""Tests for UmlValidator empty subsystem component detection (Issue #238)."""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.uml import UmlValidator
from parity_auditor.core.workspace import WorkspaceRepository


def _setup_workspace(class_diagram_body):
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean", "void"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    user_stories_dir = os.path.join(tmpdir, "user_stories")
    use_cases_dir = os.path.join(tmpdir, "use_cases")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(user_stories_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)

    md_content = """---
generation_mode: subagent
title: Test Component
interface_type: ui
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + class_diagram_body + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(md_content)
    return tmpdir


def test_empty_subsystem_component_class_flagged():
    """Empty <<component>> class without attributes or methods should be flagged."""
    diagram = """classDiagram
    class SubsystemComponent {
        <<component>>
    }
    class InterfaceClass {
        +String attr [1]
    }
    SubsystemComponent -- InterfaceClass : uses"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        component_errors = [e for e in errors if "SubsystemComponent" in e and "empty" in e]
        assert len(component_errors) >= 1, f"Expected empty component error for SubsystemComponent, got errors: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_non_empty_subsystem_component_class_accepted():
    """<<component>> class with attributes or methods should pass validation."""
    diagram = """classDiagram
    class SubsystemComponent {
        <<component>>
        +String status [1]
        +void process() [1]
    }
    class InterfaceClass {
        +String attr [1]
    }
    SubsystemComponent -- InterfaceClass : uses"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        component_errors = [e for e in errors if "SubsystemComponent" in e and "empty" in e]
        assert len(component_errors) == 0, f"Expected 0 empty component errors for valid component, got: {component_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)
