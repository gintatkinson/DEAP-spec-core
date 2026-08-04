import os
import sys
import subprocess
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor import cli

def test_reproduce_issue353_subprocess_network_timeout_and_silent_bypass(monkeypatch, capsys):
    """
    Reproduction test for Issue #353:
    - cli.py invokes subprocess calls to `gh issue list` directly over the network during runs without offline detection fallback.
    - When `gh` CLI subprocess calls time out or return non-zero (offline envs), get_open_feature_issues returns None after 30s.
    - cli.py:352 catches open_issues is None, prints a warning, and resets open_issues = [], silently bypassing issue verification assertions.
    """
    # Step 1: Demonstrate get_open_feature_issues subprocess timeout behavior
    monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)

    def mock_subprocess_run_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

    monkeypatch.setattr("subprocess.run", mock_subprocess_run_timeout)

    issues = cli.get_open_feature_issues()
    assert issues is None, "get_open_feature_issues() should return None when subprocess times out"

    # Step 2: Demonstrate silent assertion bypass in _main_impl()
    mock_args = MagicMock()
    mock_args.schema_dir = None
    mock_args.features_dir = None
    mock_args.spec_only = True
    mock_args.allow_missing_specs = False  # Strict mode where missing specs should fail!
    mock_args.ignore_issues = None
    mock_args.only = None
    mock_args.scope_all = True
    
    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: mock_args)

    mock_repo = MagicMock()
    mock_repo.workspace_dir = "/fake/workspace"
    mock_repo.get_codebase_rules_path.return_value = "/fake/workspace/.pipeline/logical-ui/codebase_rules.json"
    
    mock_rules = MagicMock()
    mock_rules.backlog_directories.schemas = "schema"
    mock_rules.backlog_directories.features = "docs/features"
    mock_rules.backlog_directories.epics = "docs/epics"
    mock_rules.validation_rules.alternative_schema_extensions = []
    mock_rules.tracker_rules = {}
    mock_repo.get_codebase_rules.return_value = mock_rules
    mock_repo.get_feature_files.return_value = []
    
    monkeypatch.setattr("parity_auditor.cli.WorkspaceRepository", lambda workspace_dir=None: mock_repo)
    monkeypatch.setattr("parity_auditor.cli.get_open_feature_issues", lambda workspace_dir=None: None)

    def mock_exists_fn(path):
        p = str(path)
        return any(target in p for target in ["codebase_rules.json", "logical-layout.json", "docs/features", "schema"])

    original_open = open
    def mock_open_fn(file, *args, **kwargs):
        if "/fake/workspace" in str(file):
            m = MagicMock()
            m.read.return_value = '{"meta": {"upstream_repository": "test/repo"}}'
            m.__enter__.return_value = m
            return m
        return original_open(file, *args, **kwargs)

    with patch("os.path.exists", mock_exists_fn), \
         patch("os.listdir", return_value=[]), \
         patch("builtins.open", mock_open_fn), \
         patch("json.load", return_value={"meta": {"upstream_repository": "test/repo"}}), \
         patch("sys.exit") as mock_exit:
        
        cli._main_impl()
        
        # Verify that exit(1) was called (failure gate triggered) when get_open_feature_issues fails under strict mode
        mock_exit.assert_called_once_with(1)

        captured = capsys.readouterr()
        assert "[!] ERROR: Could not fetch open feature issues from GitHub while --no-allow-missing-specs is enabled." in captured.err
