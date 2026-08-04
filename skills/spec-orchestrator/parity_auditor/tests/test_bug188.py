import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from unittest.mock import MagicMock
from parity_auditor.validators.cardinality_validator import SchemaCardinalityValidator
from parity_auditor.core.models import CodebaseRules, BacklogDirectories

def test_empty_schemas_dir_no_enforcement(tmp_path):
    # Setup test workspace
    workspace_dir = str(tmp_path)
    features_dir = os.path.join(workspace_dir, ".pipeline/backlog/features")
    use_cases_dir = os.path.join(workspace_dir, ".pipeline/backlog/use_cases")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)
    
    # Feature with no schema_containers
    with open(os.path.join(features_dir, "feature_1.md"), "w") as f:
        f.write("---\ntitle: Feature 1\n---\nBody")
        
    repo_mock = MagicMock()
    repo_mock.workspace_dir = workspace_dir
    repo_mock.get_codebase_rules.return_value = CodebaseRules(
        backlog_directories=BacklogDirectories(
            features=".pipeline/backlog/features",
            use_cases=".pipeline/backlog/use_cases",
            epics=".pipeline/backlog/epics",
            user_stories=".pipeline/backlog/user_stories",
            schemas=".pipeline/backlog/schemas"
        )
    )
    # The schemas directory doesn't exist yet, we check the validator's behavior.
    validator = SchemaCardinalityValidator()
    errors = validator.validate(repo_mock)
    
    print("ERRORS:", errors)
    if len(errors) > 0:
        print("Bug reproduced: SchemaCardinalityValidator enforces schema_containers on empty schema directories")

def test_empty_schemas_dir_with_gitkeep_no_enforcement(tmp_path):
    # Setup test workspace
    workspace_dir = str(tmp_path)
    features_dir = os.path.join(workspace_dir, ".pipeline/backlog/features")
    use_cases_dir = os.path.join(workspace_dir, ".pipeline/backlog/use_cases")
    schemas_dir = os.path.join(workspace_dir, ".pipeline/backlog/schemas")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)
    os.makedirs(schemas_dir, exist_ok=True)
    
    with open(os.path.join(schemas_dir, ".gitkeep"), "w") as f:
        f.write("")
        
    # Feature with no schema_containers
    with open(os.path.join(features_dir, "feature_1.md"), "w") as f:
        f.write("---\ntitle: Feature 1\n---\nBody")
        
    repo_mock = MagicMock()
    repo_mock.workspace_dir = workspace_dir
    repo_mock.get_codebase_rules.return_value = CodebaseRules(
        backlog_directories=BacklogDirectories(
            features=".pipeline/backlog/features",
            use_cases=".pipeline/backlog/use_cases",
            epics=".pipeline/backlog/epics",
            user_stories=".pipeline/backlog/user_stories",
            schemas=".pipeline/backlog/schemas"
        )
    )
    validator = SchemaCardinalityValidator()
    errors = validator.validate(repo_mock)
    
    assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}: {errors}"
