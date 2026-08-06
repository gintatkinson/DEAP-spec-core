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
