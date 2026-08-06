import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.codebase import CodebaseValidator
from parity_auditor.core.workspace import WorkspaceRepository

def test_codebase_validator_color_constants():
    # Set up temp workspace outside the repository
    tmpdir = tempfile.mkdtemp()
    try:
        pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
        os.makedirs(pipeline_dir, exist_ok=True)
        
        # Write codebase_rules.json
        rules = {
            "meta": {},
            "target_directories": {
                "flutter": "app_flutter"
            },
            "flutter_rules": {
                "file_extensions": [".dart"],
                "exclusions": [],
                "ui_directories": [],
                "network_directories": [],
                "selection_setters": [],
                "selection_triggers": [],
                "loop_guard_keywords": [],
                "forbidden_words": [],
                "forbidden_words_message": "UI widget/screen but references forbidden libraries directly.",
                "write_lock_keywords": [],
                "playhead_clamp_regex": [],
                "ffi_keywords": [],
                "ffi_finalizer_keywords": [],
                "ffi_refcount_keywords": [],
                "viewport_file_patterns": [],
                "network_file_patterns": []
            },
            "python_rules": {
                "exclusions": []
            },
            "spec_rules": {
                "design_tokens_path": ".pipeline/logical-ui/design-tokens.json",
                "spec_files": []
            },
            "validation_rules": {
                "playhead_rate_limits": [0.90, 1.10],
                "dom_leak_patterns": [],
                "pixel_leak_patterns": []
            }
        }
        with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
            json.dump(rules, f)
            
        # Write design-tokens.json
        tokens = {
            "global": {
                "color": {
                    "white": {
                        "$value": "#ffffff",
                        "$type": "color"
                    }
                }
            }
        }
        with open(os.path.join(pipeline_dir, "design-tokens.json"), "w") as f:
            json.dump(tokens, f)
            
        # Create app_flutter directory
        flutter_dir = os.path.join(tmpdir, "app_flutter")
        os.makedirs(flutter_dir, exist_ok=True)
        
        # Write a file containing a real violation (0xffffffff)
        with open(os.path.join(flutter_dir, "violation.dart"), "w") as f:
            f.write("const color = 0xffffffff;\n")
            
        # Write a file containing a 64-bit constant (0xffffffff00000000) which should NOT be flagged
        with open(os.path.join(flutter_dir, "valid_64bit.dart"), "w") as f:
            f.write("const val = 0xffffffff00000000;\n")
            
        repo = WorkspaceRepository(tmpdir)
        validator = CodebaseValidator()
        errors = validator.validate(repo)
        
        # We expect only the violation.dart file to fail, not valid_64bit.dart
        assert any("violation.dart" in err for err in errors), f"Expected violation in violation.dart, got errors: {errors}"
        assert not any("valid_64bit.dart" in err for err in errors), f"Did not expect any violations in valid_64bit.dart, got errors: {errors}"
    finally:
        shutil.rmtree(tmpdir)
