import os
import json
import sys
import subprocess
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_install_pipeline_sh_structure_and_features():
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "install_pipeline.sh")
    assert os.path.exists(script_path), "scripts/install_pipeline.sh must exist"
    assert os.access(script_path, os.X_OK), "scripts/install_pipeline.sh must be executable"
    
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Upstream check
    assert "upstream" in content
    assert "if [ -e ./.pipeline/upstream ]; then" in content
    assert "REFUSING: this is the pipeline repository, not a downstream project." in content

    # Cloning and file updates
    assert "git clone https://github.com/gintatkinson/DEAP-spec-core.git ./.tmp-pipeline" in content
    assert "rm -rf ./skills ./rules ./.pipeline ./.agents ./scripts" in content
    assert "cp -RP ./.tmp-pipeline/skills ./" in content
    assert "cp -RP ./.tmp-pipeline/rules ./" in content
    assert "cp -RP ./.tmp-pipeline/.pipeline ./" in content
    assert "rm -rf ./.pipeline/upstream" in content
    assert "cp -RP ./.tmp-pipeline/.agents ./" in content
    assert "cp -RP ./.tmp-pipeline/scripts ./" in content

    # Hooks and bootstrapping
    assert "python3 scripts/setup_git_hooks.py || true" in content
    assert "python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py || true" in content
    assert "==> Digital Pipeline Installation Complete. 0 manual steps remaining." in content


def test_readme_contains_turnkey_onboarding():
    """
    Verify README.md documents turnkey 1-line onboarding commands.
    """
    readme_file = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "curl -sSL https://raw.githubusercontent.com/gintatkinson/DEAP-spec-core/main/scripts/install_pipeline.sh | bash" in content
    assert "bash scripts/install_pipeline.sh" in content
