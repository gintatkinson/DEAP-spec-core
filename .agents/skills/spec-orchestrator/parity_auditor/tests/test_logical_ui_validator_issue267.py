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


def test_malformed_yaml_frontmatter_in_feature_reports_error():
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {
            "id": "root",
            "type": "Root",
            "children": []
        }
        _create_test_repo(tmpdir, layout)
        
        # Create a feature spec with invalid YAML in its frontmatter
        feat_path = os.path.join(tmpdir, ".pipeline", "backlog", "features", "feat-01.md")
        with open(feat_path, "w") as f:
            f.write(
                "---\n"
                "interface_type: : malformed yaml :\n"
                "---\n"
                "# Feature 1\n"
            )
            
        repo = WorkspaceRepository(tmpdir)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        
        # Verify that a YAML parsing error is present in errors list
        yaml_errors = [e for e in errors if "Failed to parse frontmatter YAML" in e]
        assert len(yaml_errors) == 1, f"Expected 1 YAML parsing error, got: {yaml_errors}"
        assert "feat-01.md" in yaml_errors[0]
    finally:
        shutil.rmtree(tmpdir)
