import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor import cli

@patch("parity_auditor.cli.get_open_feature_issues")
@patch("argparse.ArgumentParser.parse_args")
@patch("parity_auditor.cli.WorkspaceRepository")
def test_cli_offline_github_does_not_fail(mock_repo_cls, mock_parse_args, mock_get_issues):
    # Mock parse_args to return arguments for specification-only run
    mock_args = MagicMock()
    mock_args.schema_dir = None
    mock_args.features_dir = None
    mock_args.spec_only = True
    mock_args.allow_missing_specs = True
    mock_args.ignore_issues = None
    mock_args.scope_all = False
    mock_parse_args.return_value = mock_args

    # Mock WorkspaceRepository and dynamic configuration loading
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
    mock_repo_cls.return_value = mock_repo

    # Set get_open_feature_issues to return None (simulating offline mode)
    mock_get_issues.return_value = None

    # Patch os.path.exists and builtins.open selectively
    def mock_exists_fn(path):
        p = str(path)
        if any(target in p for target in ["codebase_rules.json", "logical-layout.json", "docs/features", "schema"]):
            return True
        return False

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
         
        # Execute the main implementation
        cli._main_impl()
        
        # Verify that sys.exit was not called with exit code 1
        for call in mock_exit.call_args_list:
            assert call[0][0] != 1
