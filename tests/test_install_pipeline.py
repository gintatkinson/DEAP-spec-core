import os
import json
import sys
import subprocess
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.install_pipeline import install

def test_install_pipeline(tmp_path):
    with patch("os.getcwd", return_value=str(tmp_path)):
        os.chdir(str(tmp_path))
        install("backend-api")
        config_path = os.path.join(".pipeline", "profile_config.json")
        assert os.path.exists(config_path)
        with open(config_path, "r") as f:
            data = json.load(f)
            assert data["active_profile"] == "backend-api"


def test_install_pipeline_sh_structure_and_features():
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "install_pipeline.sh")
    assert os.path.exists(script_path), "scripts/install_pipeline.sh must exist"
    assert os.access(script_path, os.X_OK), "scripts/install_pipeline.sh must be executable"
    
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Upstream check
    assert 'upstream' in content
    assert "rm -rf ./.pipeline/upstream" not in content

    # Environment variable fallback
    assert 'DEFAULT_UPSTREAM_REPO="https://github.com/gintatkinson/DEAP-spec-core.git"' in content
    assert 'REPO_URL="${DEAP_UPSTREAM_REPO:-$DEFAULT_UPSTREAM_REPO}"' in content

    # Dynamic CLI argument parsing
    assert "--repo" in content
    assert "--profile" in content
    assert "--with-ui" in content

    # Defensive pre-execution validations
    assert "command -v git" in content
    assert 'git ls-remote --exit-code "$REPO_URL" HEAD' in content

    # Platform profile decoupling & directory selection
    assert 'FORK_DIRS=("skills/" "rules/" ".pipeline/" ".agents/" "scripts/")' in content
    assert 'app_flutter/' in content
    assert 'web_react/' in content
    assert 'WITH_UI' in content

    # Zero-nesting stream extraction
    assert '(cd "$TMP_DIR/$clean_dir" && tar --exclude="./upstream" -cf - .) | (cd "$clean_dir" && tar xf -)' in content

    # File setup & hooks
    assert ".tmp-pipeline-install" in content
    assert "AGENTS.md" in content
    assert ".gitignore" in content
    assert "setup_git_hooks.py" in content
    assert "bootstrap_tracker_labels.py" in content


def test_install_pipeline_sh_help_flag():
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "install_pipeline.sh")
    result = subprocess.run([script_path, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--repo" in result.stdout
    assert "--profile" in result.stdout
    assert "--with-ui" in result.stdout
