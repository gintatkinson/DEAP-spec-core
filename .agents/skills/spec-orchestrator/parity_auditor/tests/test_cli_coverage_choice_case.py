import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor import cli

@patch("parity_auditor.cli.get_open_feature_issues")
@patch("argparse.ArgumentParser.parse_args")
@patch("parity_auditor.cli.WorkspaceRepository")
@patch("parity_auditor.cli.parse_schema_file")
def test_cli_coverage_choice_case(mock_parse_schema, mock_repo_cls, mock_parse_args, mock_get_issues, capsys):
    mock_args = MagicMock()
    mock_args.schema_dir = "schema"
    mock_args.features_dir = "docs/features"
    mock_args.spec_only = True
    mock_args.allow_missing_specs = True
    mock_args.ignore_issues = None
    mock_args.scope_all = False
    mock_parse_args.return_value = mock_args

    mock_repo = MagicMock()
    mock_repo.workspace_dir = "/fake/workspace"
    mock_repo.get_codebase_rules_path.return_value = "codebase_rules.json"
    
    mock_rules = MagicMock()
    mock_rules.meta.upstream_repository = "gintatkinson/digital-pipeline-repo"
    mock_rules.backlog_directories.schemas = "schema"
    mock_rules.backlog_directories.features = "docs/features"
    mock_rules.backlog_directories.epics = "docs/epics"
    mock_rules.validation_rules.alternative_schema_extensions = []
    mock_rules.tracker_rules = {}
    mock_repo.get_codebase_rules.return_value = mock_rules
    
    mock_feature = MagicMock()
    mock_feature.frontmatter = {
        "schema_containers": [
            {"path": "ietf-geo-location:geo-location/location/ellipsoid"},
            {"path": "ietf-geo-location:geo-location/location/cartesian"}
        ]
    }
    mock_feature.content = (
        "---\n"
        "schema_containers:\n"
        "  - path: ietf-geo-location:geo-location/location/ellipsoid\n"
        "  - path: ietf-geo-location:geo-location/location/cartesian\n"
        "---\n"
        "```mermaid\n"
        "classDiagram\n"
        "class GeoLocation {\n"
        "}\n"
        "```\n"
    )
    mock_repo.get_feature_files.return_value = [mock_feature]
    mock_repo_cls.return_value = mock_repo

    mock_get_issues.return_value = []

    mock_parse_schema.return_value = (
        "ietf-geo-location", 
        {
            "ietf-geo-location:geo-location/location/ellipsoid": {"type": "case"},
            "ietf-geo-location:geo-location/location/cartesian": {"type": "case"}
        }
    )

    def mock_exists_fn(path):
        p = str(path)
        if any(target in p for target in ["codebase_rules.json", "docs/features", "schema"]):
            return True
        return False

    with patch("os.path.exists", mock_exists_fn), \
         patch("os.listdir", return_value=["test.yang"]), \
         patch("builtins.open", MagicMock()), \
         patch("json.load", return_value={}), \
         patch("sys.exit"):
         
        cli._main_impl()
        
        captured = capsys.readouterr()
        assert "Success: 100% spec-only model coverage verified across all specification files." in captured.out
