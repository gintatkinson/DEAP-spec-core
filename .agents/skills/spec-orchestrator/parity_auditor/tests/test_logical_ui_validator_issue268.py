import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
from parity_auditor.core.workspace import WorkspaceRepository


def _create_test_repo(tmpdir, layout):
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

    features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
    os.makedirs(features_dir, exist_ok=True)

    with open(os.path.join(pipeline_dir, "logical-layout.json"), "w") as f:
        json.dump(layout, f)

    return WorkspaceRepository(tmpdir)


def test_issue268_unnumbered_header_no_error():
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "TableView", "id": "table1"}
        repo = _create_test_repo(tmpdir, layout)

        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
        os.path.join(".pipeline", "backlog", "features", "feat-unnumbered.md")

        content = """---
title: "Unnumbered Header UI Feature"
interface_type: ui
---
## Logical UI & Layout Bindings
- **Target LUI Component:** TableView
- **Target Layout Container ID:** table1
"""
        with open(os.path.join(features_dir, "feat-unnumbered.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        # No errors should be reported for this valid unnumbered feature file
        assert not errors, f"Expected no validation errors, but got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_issue268_unnumbered_header_geodetic_validation():
    tmpdir = tempfile.mkdtemp()
    try:
        # Create a layout without the spatial view components, or mapping to a non-spatial component
        layout = {"type": "CustomWidget", "id": "widget1"}
        repo = _create_test_repo(tmpdir, layout)

        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
        rel_path = os.path.join(".pipeline", "backlog", "features", "feat-geodetic.md")

        # Has geodetic keyword "latitude" but maps to "CustomWidget" which is NOT in VALID_SPATIAL_COMPONENTS
        content = """---
title: "Geodetic Unnumbered Feature"
interface_type: ui
---
## Logical UI & Layout Bindings
- **Target LUI Component:** CustomWidget
- **Target Layout Container ID:** widget1

This feature contains a field for latitude coordinates.
"""
        with open(os.path.join(features_dir, "feat-geodetic.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        # It should trigger the spatial/geodetic validation check and report the compliance error
        expected_err = f"Logical UI Compliance: Feature '{rel_path}' contains spatial/geodetic attributes but fails to map to a spatial view component ('TopologyMap', 'TopographicalView', 'GeoSpatialViewer', 'PropertyGrid', or 'TableView')."
        assert any(expected_err in err for err in errors), f"Expected spatial validation error, got errors: {errors}"
    finally:
        shutil.rmtree(tmpdir)

def test_issue265_unnumbered_non_ui_type_validates_bindings():
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "TableView", "id": "table1"}
        repo = _create_test_repo(tmpdir, layout)

        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
        os.path.join(".pipeline", "backlog", "features", "feat-api.md")

        content = """---
title: "API Feature with Bindings"
interface_type: api
---
## Logical UI & Layout Bindings
- **Target LUI Component:** InvalidComponent
- **Target Layout Container ID:** table1
"""
        with open(os.path.join(features_dir, "feat-api.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        assert any("invalid component type 'InvalidComponent'" in err for err in errors), f"Expected invalid component error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)
