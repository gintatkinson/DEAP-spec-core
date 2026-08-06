import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.docstring_validator import DocstringValidator
from parity_auditor.core.workspace import WorkspaceRepository


def test_docstring_validator_detects_missing_docstrings():
    tmpdir = tempfile.mkdtemp()
    try:
        pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
        os.makedirs(pipeline_dir, exist_ok=True)
        rules = {
            "meta": {"upstream_repository": "gintatkinson/digital-pipeline-repo"},
            "target_directories": {
                "flutter": "app_flutter"
            },
            "flutter_rules": {
                "file_extensions": [".dart"],
                "exclusions": []
            },
            "python_rules": {
                "file_extensions": [".py"],
                "exclusions": []
            },
            "react_rules": {
                "file_extensions": [".ts"],
                "exclusions": []
            }
        }
        with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w", encoding="utf-8") as f:
            json.dump(rules, f)

        app_dir = os.path.join(tmpdir, "app_flutter")
        os.makedirs(app_dir, exist_ok=True)

        # File with missing DartDoc
        with open(os.path.join(app_dir, "undocumented.dart"), "w", encoding="utf-8") as f:
            f.write("class UndocumentedClass {}\n")

        # File with DartDoc
        with open(os.path.join(app_dir, "documented.dart"), "w", encoding="utf-8") as f:
            f.write("/// Documented class\nclass DocumentedClass {}\n")

        repo = WorkspaceRepository(tmpdir)
        validator = DocstringValidator()
        errors = validator.validate(repo)

        assert any("UndocumentedClass" in err for err in errors)
        assert not any("DocumentedClass" in err for err in errors)
    finally:
        shutil.rmtree(tmpdir)
