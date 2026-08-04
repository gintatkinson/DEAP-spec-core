import os
from unittest.mock import patch, MagicMock
from parity_auditor.validators.cardinality_validator import SchemaCardinalityValidator
from parity_auditor.core.workspace import WorkspaceRepository

def test_sysml_coverage_validation():
    repo = MagicMock(spec=WorkspaceRepository)
    repo.workspace_dir = "/dummy"
    rules = MagicMock()
    rules.backlog_directories.schemas = "schemas"
    rules.backlog_directories.features = "features"
    repo.get_codebase_rules.return_value = rules

    with patch('os.path.exists', return_value=True), \
         patch('os.listdir', side_effect=lambda d: ['test.sysml'] if 'schemas' in d else ['feat.md']), \
         patch('builtins.open') as mock_open:
         
        mock_file = MagicMock()
        # The first open is for sysml, the second for markdown
        mock_file.__enter__.side_effect = [
            MagicMock(read=lambda: "part def MyPart {} attribute def MyAttr {}"),
            MagicMock(read=lambda: "This feature implements MyPart.")
        ]
        mock_open.return_value = mock_file
        
        validator = SchemaCardinalityValidator()
        errors = validator.validate(repo, is_sysml=True)
        
        # MyAttr should be missing
        assert len(errors) == 1
        assert "MyAttr" in errors[0]
        assert "MyPart" not in errors[0]
