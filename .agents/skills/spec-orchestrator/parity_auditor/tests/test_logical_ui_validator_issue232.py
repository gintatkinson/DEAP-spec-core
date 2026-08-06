import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
from parity_auditor.core.workspace import WorkspaceRepository


def _create_test_repo(tmpdir, layout, feature_content):
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)

    rules = {
        "meta": {},
        "target_directories": {"flutter": "app_flutter"},
        "flutter_rules": {
            "file_extensions": [".dart"],
            "exclusions": [],
            "ui_directories": [],
            "network_directories": [],
            "selection_setters": [],
            "selection_triggers": [],
            "loop_guard_keywords": [],
            "forbidden_words": [],
            "forbidden_words_message": "",
            "write_lock_keywords": [],
            "playhead_clamp_regex": [],
            "ffi_keywords": [],
            "ffi_finalizer_keywords": [],
            "ffi_refcount_keywords": [],
            "viewport_file_patterns": [],
            "network_file_patterns": []
        },
        "python_rules": {"exclusions": []},
        "spec_rules": {
            "design_tokens_path": ".pipeline/logical-ui/design-tokens.json",
            "spec_files": []
        },
        "validation_rules": {
            "playhead_rate_limits": [0.90, 1.10],
            "dom_leak_patterns": [],
            "pixel_leak_patterns": []
        },
        "backlog_directories": {
            "epics": ".pipeline/backlog/epics",
            "features": ".pipeline/backlog/features",
            "use_cases": ".pipeline/backlog/use_cases",
            "user_stories": ".pipeline/backlog/user_stories"
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    with open(os.path.join(pipeline_dir, "logical-layout.json"), "w") as f:
        json.dump(layout, f)

    features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
    os.makedirs(features_dir, exist_ok=True)

    with open(os.path.join(features_dir, "feat-001-test.md"), "w") as f:
        f.write(feature_content)


def test_component_container_type_mismatch():
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {
            "id": "root",
            "type": "Root",
            "children": [
                {
                    "id": "properties_view",
                    "type": "PropertyGrid"
                },
                {
                    "id": "components_table",
                    "type": "TableView"
                }
            ]
        }
        feature_content = """# Feature: Test Feature

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TableView
- **Target Layout Container ID**: properties_view
- **Data Source Binding**: /schema:test
"""
        _create_test_repo(tmpdir, layout, feature_content)
        repo = WorkspaceRepository(tmpdir)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        mismatch_errors = [e for e in errors if "specifies component type 'TableView'" in e and "properties_view" in e]
        assert len(mismatch_errors) == 1, f"Expected 1 component-container type mismatch error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_component_container_type_match():
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {
            "id": "root",
            "type": "Root",
            "children": [
                {
                    "id": "properties_view",
                    "type": "PropertyGrid"
                },
                {
                    "id": "components_table",
                    "type": "TableView"
                }
            ]
        }
        feature_content = """# Feature: Test Feature Match

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TableView
- **Target Layout Container ID**: components_table
- **Data Source Binding**: /schema:test
"""
        _create_test_repo(tmpdir, layout, feature_content)
        repo = WorkspaceRepository(tmpdir)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        mismatch_errors = [e for e in errors if "specifies component type" in e or "type mismatch" in e]
        assert len(mismatch_errors) == 0, f"Expected 0 mismatch errors, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)
