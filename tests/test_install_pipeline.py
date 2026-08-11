import os
import json
import sys
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


def test_install_pipeline_sh_exists_and_executable():
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "install_pipeline.sh")
    assert os.path.exists(script_path), "scripts/install_pipeline.sh must exist"
    assert os.access(script_path, os.X_OK), "scripts/install_pipeline.sh must be executable"
    
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'upstream' in content
    assert "rm -rf ./.pipeline/upstream" not in content
    assert "git clone" in content
    assert ".tmp-pipeline-install" in content
    assert "skills/" in content
    assert "rules/" in content
    assert ".pipeline/" in content
    assert ".agents/" in content
    assert "scripts/" in content
    assert "app_flutter/" not in content
    assert "web_react/" not in content
    assert "AGENTS.md" in content
    assert ".gitignore" in content
    assert "setup_git_hooks.py" in content
    assert "bootstrap_tracker_labels.py" in content

