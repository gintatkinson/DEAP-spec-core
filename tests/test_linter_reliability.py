import os
import sys
import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from parity_auditor.core.workspace import WorkspaceRepository
from parity_auditor.validators.schema_mapping_validator import SchemaMappingValidator
from parity_auditor.validators.profile_scoping_validator import ProfileScopingValidator
from parity_auditor.cli import main

@pytest.fixture
def base_config():
    return {
        "meta": {
            "version": "1.0.0",
            "description": "Minimal configuration for testing",
            "upstream_repository": "gintatkinson/digital-pipeline-repo"
        },
        "backlog_directories": {
            "epics": "docs/epics",
            "features": "docs/features",
            "user_stories": "docs/user-stories",
            "use_cases": "docs/use-cases",
            "schemas": "schema"
        },
        "target_directories": {
            "flutter": "app_flutter"
        },
        "flutter_rules": {
            "file_extensions": [".dart"],
            "exclusions": ["build", ".git"],
            "ui_directories": ["widgets", "screens"]
        },
        "validation_rules": {
            "schema_exclude_keywords": ["description", "reference"],
            "schema_patterns": {
                ".yang": {
                    "name_regex": "\\bmodule\\s+([a-zA-Z0-9_\\-]+)",
                    "patterns": [
                        "\\btypedef\\s+([a-zA-Z0-9_\\-]+)",
                        "\\bleaf\\s+([a-zA-Z0-9_\\-]+)",
                        "\\bcontainer\\s+([a-zA-Z0-9_\\-]+)",
                        "\\blist\\s+([a-zA-Z0-9_\\-]+)",
                        "\\brpc\\s+([a-zA-Z0-9_\\-]+)",
                        "\\baction\\s+([a-zA-Z0-9_\\-]+)",
                        "\\bfeature\\s+([a-zA-Z0-9_\\-]+)"
                    ]
                }
            },
            "alternative_schema_extensions": []
        }
    }

def setup_workspace(tmp_path, config, schemas=None, flutter_files=None):
    ws_dir = tmp_path / "test_workspace"
    os.makedirs(ws_dir, exist_ok=True)
    
    # Write codebase_rules.json
    rules_dir = ws_dir / ".pipeline" / "logical-ui"
    os.makedirs(rules_dir, exist_ok=True)
    with open(rules_dir / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(config, f)
        
    # Write schemas
    schema_dir = ws_dir / "schema"
    os.makedirs(schema_dir, exist_ok=True)
    if schemas:
        for name, content in schemas.items():
            with open(schema_dir / name, "w", encoding="utf-8") as f:
                f.write(content)
                
    # Write Flutter codebase files
    flutter_dir = ws_dir / "app_flutter"
    os.makedirs(flutter_dir, exist_ok=True)
    if flutter_files:
        for rel_path, content in flutter_files.items():
            filepath = flutter_dir / rel_path
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                
    return ws_dir

def test_comment_only_bypass(tmp_path, base_config):
    # 1. Define a feature spec with class 'Location' in schema
    schemas = {
        "location.yang": """
        module location {
            container Location {
                leaf id { type string; }
            }
        }
        """
    }
    # 2. Mock codebase containing only a comment '// Location class info'
    flutter_files = {
        "widgets/location_view.dart": "// Location class info"
    }
    
    ws_dir = setup_workspace(tmp_path, base_config, schemas=schemas, flutter_files=flutter_files)
    repo = WorkspaceRepository(str(ws_dir))
    
    validator = SchemaMappingValidator()
    errors = validator.validate(repo)
    
    # Assert that validator fails and flags Location as missing
    assert any("Location" in err for err in errors), f"Expected Location to be flagged as missing, but got errors: {errors}"

def test_unrelated_variable_bypass(tmp_path, base_config):
    # 1. Define a spec with method 'increment' in schema
    schemas = {
        "math.yang": """
        module math {
            rpc increment {
                input { leaf value { type int32; } }
            }
        }
        """
    }
    # 2. Codebase file containing a variable 'var increment = 5;'
    flutter_files = {
        "widgets/math_controller.dart": "var increment = 5;"
    }
    
    ws_dir = setup_workspace(tmp_path, base_config, schemas=schemas, flutter_files=flutter_files)
    repo = WorkspaceRepository(str(ws_dir))
    
    validator = SchemaMappingValidator()
    errors = validator.validate(repo)
    
    # Assert that validator fails
    assert any("increment" in err for err in errors), f"Expected increment to be flagged as missing/invalid, but got errors: {errors}"

def test_empty_directory_bypass(tmp_path, base_config):
    # Empty codebase directory
    ws_dir = setup_workspace(tmp_path, base_config)
    repo = WorkspaceRepository(str(ws_dir))
    
    schema_mapping_validator = SchemaMappingValidator()
    profile_scoping_validator = ProfileScopingValidator()
    
    # Assert that both fail rather than returning success
    sm_errors = schema_mapping_validator.validate(repo)
    ps_errors = profile_scoping_validator.validate(repo)
    
    assert len(sm_errors) > 0, "SchemaMappingValidator should fail for empty codebase"
    assert len(ps_errors) > 0, "ProfileScopingValidator should fail for empty codebase"

def test_missing_spec(tmp_path, base_config):
    # Setup workspace with open issue #42 but no spec file locally
    ws_dir = setup_workspace(tmp_path, base_config)
    
    # Create empty docs/features/ directory
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    
    # Mock gh CLI response to return open issue 42 with label 'feature'
    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.returncode = 0
    mock_process.stdout = json.dumps([
        {"number": 42, "title": "Implement authentication"}
    ])
    mock_process.stderr = ""
    
    old_cwd = os.getcwd()
    os.chdir(ws_dir)
    old_argv = sys.argv
    sys.argv = ["parity-auditor", "--spec-only"]
    
    try:
        with patch("subprocess.run", return_value=mock_process) as mock_run:
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0
            
            # Verify the command was run
            assert mock_run.call_count >= 1
            first_call_args = mock_run.call_args_list[0][0]
            assert "gh" in first_call_args[0]
            assert "issue" in first_call_args[0]
            assert "list" in first_call_args[0]
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)

def test_regex_parser_features_and_duplicates(tmp_path, base_config):
    schemas = {
        "geo.yang": """
        module geo {
            feature alternate-systems;
            grouping geo-location {
                leaf lat { type decimal64; }
            }
            container geo-location {
                leaf lon { type decimal64; }
            }
        }
        """
    }
    flutter_files = {
        "widgets/geo_view.dart": """
        const bool alternateSystems = true;
        class GeoLocation {
            double lat;
            double lon;
        }
        """
    }
    
    ws_dir = setup_workspace(tmp_path, base_config, schemas=schemas, flutter_files=flutter_files)
    repo = WorkspaceRepository(str(ws_dir))
    
    validator = SchemaMappingValidator()
    errors = validator.validate(repo)
    
    assert not errors, f"Expected no validation errors, but got: {errors}"

def test_spec_only_coverage_validation(tmp_path, base_config):
    schemas = {
        "geo.yang": """
        module geo {
            container GeoLocation {
                leaf lat { type decimal64; }
            }
        }
        """
    }
    ws_dir = setup_workspace(tmp_path, base_config, schemas=schemas)
    
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    with open(ws_dir / "docs" / "features" / "feat-01-geo.md", "w", encoding="utf-8") as f:
        f.write("# Feature 1: Geolocation\n\n## UML Class Diagram\n```mermaid\nclassDiagram\nclass EmptyClass {}\n```\n")
        
    old_cwd = os.getcwd()
    os.chdir(ws_dir)
    old_argv = sys.argv
    sys.argv = ["parity-auditor", "--spec-only", "--allow-missing-specs"]
    
    try:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)

def test_ignore_issues_filtering(tmp_path, base_config):
    from parity_auditor.cli import parse_ignore_issues
    assert parse_ignore_issues("14,16-18,20") == {14, 16, 17, 18, 20}
    assert parse_ignore_issues("12") == {12}
    assert parse_ignore_issues("") == set()

def test_ignore_issues_integration(tmp_path, base_config, monkeypatch, capsys):
    ws_dir = setup_workspace(tmp_path, base_config)
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    
    def mock_get_open_feature_issues():
        return [
            {"number": 14, "title": "Defect: Perf"},
            {"number": 15, "title": "Bug: verify"}
        ]
    import parity_auditor.cli
    monkeypatch.setattr(parity_auditor.cli, "get_open_feature_issues", mock_get_open_feature_issues)
    
    old_cwd = os.getcwd()
    os.chdir(ws_dir)
    old_argv = sys.argv
    sys.argv = ["parity-auditor", "--spec-only", "--ignore-issues", "14,15"]
    
    try:
        with pytest.raises(SystemExit):
            main()
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        
    captured = capsys.readouterr()
    assert "Missing local specification files for open feature issues" not in captured.out

def test_reconcile_backlog_frontmatter_resolution(tmp_path, base_config):
    ws_dir = tmp_path / "workspace"
    os.makedirs(ws_dir / ".pipeline" / "logical-ui", exist_ok=True)
    with open(ws_dir / ".pipeline" / "logical-ui" / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(base_config, f)
        
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    feat_path = ws_dir / "docs" / "features" / "feat-01-geo.md"
    with open(feat_path, "w", encoding="utf-8") as f:
        f.write("---\ntitle: \"Feature 1: Geolocation\"\nissue_id: #[IssueID]\n---\n# Feature 1: Geolocation\n")
        
    sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))))
    import reconcile_backlog
    
    feature_titles = {"geolocation": 42}
    reconcile_backlog.resolve_issue_ids_in_file(
        str(feat_path),
        epic_titles={},
        feature_titles=feature_titles,
        story_titles={},
        usecase_titles={},
        rules=base_config
    )
    
    with open(feat_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "issue_id: #42" in content

def test_extend_arrow_false_positives(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    os.makedirs(ws_dir / "docs" / "use-cases", exist_ok=True)
    uc_path = ws_dir / "docs" / "use-cases" / "uc-01-register.md"
    with open(uc_path, "w", encoding="utf-8") as f:
        f.write("""---
title: "Use Case 1: Register"
type: "use-case"
spec_source: "Standard"
---
# Use Case: Register

## UML Diagrams
### Use Case Diagram
```mermaid
graph TB
    subgraph boundary ["System Boundary"]
        UC1["Register (Context)"]
        UC2["Edit (Texture)"]
        UC1 -->|extend| UC2
    end
```
""")
    
    repo = WorkspaceRepository(str(ws_dir))
    from parity_auditor.validators.uml import UmlValidator
    validator = UmlValidator()
    errors = validator.validate(repo)
    extend_errors = [e for e in errors if "extend arrow" in e]
    assert not extend_errors, f"Expected no extend arrow errors, but got: {extend_errors}"

def test_logical_ui_validator(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    
    # 1. Create a dummy logical-layout.json in .pipeline/logical-ui/
    layout_dir = ws_dir / ".pipeline" / "logical-ui"
    os.makedirs(layout_dir, exist_ok=True)
    layout_data = {
        "layout": {
            "root_container": {
                "type": "SidebarLayout",
                "id": "main_shell",
                "children": [
                    {
                        "type": "TopographicalView",
                        "id": "topology_pane"
                    }
                ]
            }
        }
    }
    with open(layout_dir / "logical-layout.json", "w", encoding="utf-8") as f:
        json.dump(layout_data, f)
        
    # 2. Write valid feature file
    features_dir = ws_dir / "docs" / "features"
    os.makedirs(features_dir, exist_ok=True)
    
    with open(features_dir / "feat-valid.md", "w", encoding="utf-8") as f:
        f.write("""---
title: "Valid Feature"
type: "feature"
---
# Valid Feature

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TopographicalView
- **Target Layout Container ID**: topology_pane
""")

    # Write non-ui feature file without logical ui section
    with open(features_dir / "feat-api.md", "w", encoding="utf-8") as f:
        f.write("""---
title: "API Feature"
type: "feature"
interface_type: "api"
---
# API Feature
""")

    # Write topology map alias feature file
    with open(features_dir / "feat-topology-map.md", "w", encoding="utf-8") as f:
        f.write("""---
title: "Topology Map Feature"
type: "feature"
---
# Topology Map Feature

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TopologyMap
- **Target Layout Container ID**: topology_pane
""")
        
    # 3. Write feature file with invalid component/container
    with open(features_dir / "feat-invalid.md", "w", encoding="utf-8") as f:
        f.write("""---
title: "Invalid Feature"
type: "feature"
---
# Invalid Feature

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: NonExistentView
- **Target Layout Container ID**: non_existent_pane
""")

    # 4. Write feature file with coordinate keywords and N/A component
    with open(features_dir / "feat-coord-invalid.md", "w", encoding="utf-8") as f:
        f.write("""---
title: "Coordinate Invalid Feature"
type: "feature"
---
# Coordinate Invalid Feature

We track latitude and longitude coordinates.

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: N/A
- **Target Layout Container ID**: N/A
""")

    repo = WorkspaceRepository(str(ws_dir))
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    validator = LogicalUiValidator()
    errors = validator.validate(repo)
    
    # Assert errors for feat-invalid.md (both invalid component and invalid container)
    invalid_comp_err = [e for e in errors if "feat-invalid.md" in e and "specifies invalid component type" in e]
    invalid_container_err = [e for e in errors if "feat-invalid.md" in e and "specifies invalid container ID" in e]
    assert len(invalid_comp_err) == 1
    assert len(invalid_container_err) == 1
    
    # Assert coordinate errors for feat-coord-invalid.md
    coord_err = [e for e in errors if "feat-coord-invalid.md" in e and ("contains spatial/geodetic" in e or "contains geodetic/coordinate" in e)]
    assert len(coord_err) == 1
    
    # Assert no errors for feat-valid.md, feat-api.md, feat-topology-map.md
    valid_err = [e for e in errors if "feat-valid.md" in e]
    assert len(valid_err) == 0
    api_err = [e for e in errors if "feat-api.md" in e]
    assert len(api_err) == 0
    topmap_err = [e for e in errors if "feat-topology-map.md" in e]
    assert len(topmap_err) == 0

def test_programmatic_epics_dir_override(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    repo = WorkspaceRepository(str(ws_dir))
    custom_epics_dir = tmp_path / "custom_epics"
    os.makedirs(custom_epics_dir, exist_ok=True)
    with open(custom_epics_dir / "epic_valid.md", "w", encoding="utf-8") as f:
        f.write("# Epic 1\n\n## UML Diagrams\n```mermaid\nclassDiagram\nclass CustomClass {}\n```\n")
        
    from parity_auditor.validators.uml import UmlValidator
    validator = UmlValidator()
    global_classes = validator.build_global_classes(repo, os.path.join(ws_dir, "docs/features"), str(custom_epics_dir))
    assert "CustomClass" in global_classes

def test_unbracketed_return_multiplicity(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    repo = WorkspaceRepository(str(ws_dir))
    features_dir = ws_dir / "docs" / "features"
    os.makedirs(features_dir, exist_ok=True)
    with open(features_dir / "feat-methods.md", "w", encoding="utf-8") as f:
        f.write("# Feature: Methods\n## UML Diagrams\n```mermaid\nclassDiagram\n    class MyService {\n        +void doWork()\n        +Node fetchNode()\n    }\n```\n")
    from parity_auditor.validators.uml import UmlValidator
    validator = UmlValidator()
    errors = validator.validate(repo, epics_dir=str(ws_dir / "docs/epics"))
    mult_errors = [e for e in errors if "missing a multiplicity" in e]
    assert not mult_errors, f"Expected no multiplicity errors on unbracketed returns, but got: {mult_errors}"

def test_common_word_coverage_context(tmp_path, base_config):
    schemas = {
        "user.yang": "\n        module user {\n            container User {\n                leaf id { type string; }\n                leaf name { type string; }\n            }\n        }\n        "
    }
    flutter_files_invalid = {
        "widgets/user_card.dart": "// This is comment containing id and name"
    }
    ws_dir_invalid = setup_workspace(tmp_path / "invalid", base_config, schemas=schemas, flutter_files=flutter_files_invalid)
    repo_invalid = WorkspaceRepository(str(ws_dir_invalid))
    validator = SchemaMappingValidator()
    errors_invalid = validator.validate(repo_invalid)
    assert any("id" in err or "name" in err for err in errors_invalid)

    flutter_files_valid = {
        "widgets/user_card.dart": "class User { final String id; final String name; User({required this.id, required this.name}); }"
    }
    ws_dir_valid = setup_workspace(tmp_path / "valid", base_config, schemas=schemas, flutter_files=flutter_files_valid)
    repo_valid = WorkspaceRepository(str(ws_dir_valid))
    errors_valid = validator.validate(repo_valid)
    assert not errors_valid, f"Expected no errors, but got: {errors_valid}"

def test_mermaid_prose_dotted_link(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    repo = WorkspaceRepository(str(ws_dir))
    features_dir = ws_dir / "docs" / "features"
    os.makedirs(features_dir, exist_ok=True)
    with open(features_dir / "feat-prose.md", "w", encoding="utf-8") as f:
        f.write("# Feature: Prose\nPlease refer to this: A-.->|label|B for description.\n\n## UML Diagrams\n```mermaid\nclassDiagram\n    class A\n    class B\n    A ..> B : dependency\n```\n")
    from parity_auditor.validators.uml import UmlValidator
    validator = UmlValidator()
    errors = validator.validate(repo, epics_dir=str(ws_dir / "docs/epics"))
    link_errors = [e for e in errors if "dotted link" in e]
    assert not link_errors, f"Expected no link errors from prose, but got: {link_errors}"



def test_epic_only_uml_validation(tmp_path, base_config):
    ws_dir = setup_workspace(tmp_path, base_config)
    os.makedirs(ws_dir / "docs" / "epics", exist_ok=True)
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    
    with open(ws_dir / "docs" / "epics" / "epic_invalid.md", "w", encoding="utf-8") as f:
        f.write("""---
generation_mode: subagent
title: "Invalid Epic"
type: "epic"
---
# Invalid Epic

## 1. Executive Summary
## 2. Requirements & Checklist
## 3. UML Diagrams
```mermaid
classDiagram
    class InvalidClass {
        +String myAttr { invalid }
    }
```
""")

    old_cwd = os.getcwd()
    os.chdir(ws_dir)
    old_argv = sys.argv
    sys.argv = ["parity-auditor", "--spec-only", "--allow-missing-specs"]
    
    try:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)


def test_reconcile_epic_checklist_preserves_custom_content(tmp_path, base_config):
    ws_dir = tmp_path / "workspace"
    config = base_config.copy()
    config["tracker_rules"] = {
        "numeric_prefix": "#",
        "issue_id_placeholder": "#[IssueID]"
    }
    
    os.makedirs(ws_dir / ".pipeline" / "logical-ui", exist_ok=True)
    with open(ws_dir / ".pipeline" / "logical-ui" / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(config, f)
        
    os.makedirs(ws_dir / "docs" / "epics", exist_ok=True)
    epic_path = ws_dir / "docs" / "epics" / "epic-01-sample.md"
    
    initial_content = """---
generation_mode: subagent
title: "Epic 1: Sample Epic"
type: "epic"
---
# Epic 1: Sample Epic

## 1. Executive Summary
Some summary here.

## 2. Requirements & Checklist

#### Associated Use Cases
- [ ] #[IssueID] - [Use Case 1: First Usecase](https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/use-cases/uc-01.md) (justification)

#### Associated User Stories
- [ ] #[IssueID] - [User Story 1: First Story](https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/user-stories/us-01.md) (justification)

### Custom Heading
This is custom content between the end of the user stories checklist and the next H2 header.
- A custom list item that must be preserved.

## 3. Architecture
Some architecture notes.
"""
    with open(epic_path, "w", encoding="utf-8") as f:
        f.write(initial_content)
        
    if str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))) not in sys.path:
        sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))))
    import reconcile_backlog
    
    epic_titles = {"epic 1: sample epic": 100}
    feature_titles = {}
    story_titles = {"first story": 101, "second story": 102}
    usecase_titles = {"first usecase": 103}
    
    child_features = []
    child_stories = [("us-01", "User Story 1: First Story"), ("us-02", "User Story 2: Second Story")]
    child_usecases = [("uc-01", "Use Case 1: First Usecase")]
    
    reconcile_backlog.reconcile_epic_checklists(
        str(epic_path),
        child_features,
        child_stories,
        child_usecases,
        epic_titles,
        feature_titles,
        story_titles,
        usecase_titles,
        config
    )
    
    with open(epic_path, "r", encoding="utf-8") as f:
        updated_content = f.read()
        
    # Check that the custom content is completely preserved
    assert "### Custom Heading" in updated_content
    assert "This is custom content between the end of the user stories checklist and the next H2 header." in updated_content
    assert "- A custom list item that must be preserved." in updated_content
    
    # Verify that the checklist was updated correctly
    assert "us-02" in updated_content
    assert "#102" in updated_content
    assert "## 3. Architecture" in updated_content


def test_reconcile_backlog_frontmatter_resolution_variations(tmp_path, base_config):
    ws_dir = tmp_path / "workspace"
    os.makedirs(ws_dir / ".pipeline" / "logical-ui", exist_ok=True)
    with open(ws_dir / ".pipeline" / "logical-ui" / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(base_config, f)
        
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    
    variations = [
        ("issue-id: #[IssueID]", "issue-id: #42"),
        ("issueid: #[IssueID]", "issueid: #42"),
        ("Issue-Id: #[IssueID]", "Issue-Id: #42"),
        ("issue_id: #[IssueID]", "issue_id: #42"),
    ]
    
    if str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))) not in sys.path:
        sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))))
    import reconcile_backlog
    
    feature_titles = {"geolocation": 42}
    
    for idx, (line_variation, expected_line) in enumerate(variations):
        feat_path = ws_dir / "docs" / "features" / f"feat-{idx}-geo.md"
        with open(feat_path, "w", encoding="utf-8") as f:
            f.write(f"---\ntitle: \"Feature 1: Geolocation\"\n{line_variation}\n---\n# Feature 1: Geolocation\n")
            
        reconcile_backlog.resolve_issue_ids_in_file(
            str(feat_path),
            epic_titles={},
            feature_titles=feature_titles,
            story_titles={},
            usecase_titles={},
            rules=base_config
        )
        
        with open(feat_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert expected_line in content, f"Expected '{expected_line}' to be in resolved content, but got:\n{content}"


def test_yaml_multiline_frontmatter_block_parsing(tmp_path, base_config):
    # Test for Bug #182: Reconciler naive line-splitting on colons erases multiline YAML block descriptions
    # Check that WorkspaceRepository.load_feature_files parses labels correctly even with multiline/complex frontmatter.
    from parity_auditor.core.workspace import WorkspaceRepository
    from parity_auditor.validators.uml import UmlValidator

    ws_dir = tmp_path / "workspace"
    os.makedirs(ws_dir / ".pipeline" / "logical-ui", exist_ok=True)
    with open(ws_dir / ".pipeline" / "logical-ui" / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(base_config, f)
        
    os.makedirs(ws_dir / "docs" / "features", exist_ok=True)
    
    # Create feature file with complex multiline YAML frontmatter containing colons
    feat_path = ws_dir / "docs" / "features" / "feat-complex.md"
    with open(feat_path, "w", encoding="utf-8") as f:
        f.write("""---
title: "Complex Feature"
labels: ["label-1", "label-2"]
generation_mode: subagent
description: |
  This is a multiline description:
  - Part 1: Details here
  - Part 2: More details
---
# Complex Feature

## UML Class Diagram
```mermaid
classDiagram
class DummyClass {}
```
""")
    
    # 1. Test workspace.py label parsing
    repo = WorkspaceRepository(str(ws_dir))
    feature_files = repo.get_feature_files(str(ws_dir / "docs" / "features"))
    assert len(feature_files) == 1
    assert feature_files[0].labels == ["label-1", "label-2"]
    
    # 2. Test uml.py frontmatter tag / interface_type parsing
    # First test UmlValidator's subagent isolation verification
    validator = UmlValidator()
    errors = []
    validator._validate_subagent_isolation(feature_files[0].content, "Feature", feature_files[0].filename, errors)
    assert not errors, f"Expected no subagent isolation errors, got: {errors}"


def test_convert_frontmatter_to_table_escaping(tmp_path, base_config):
    if str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))) not in sys.path:
        sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "spec-orchestrator", "scripts"))))
    import reconcile_backlog
    
    content = """---
title: "Pipe | Test"
description: |
  Line 1
  Line 2
---
# Main Content"""
    
    result = reconcile_backlog.convert_frontmatter_to_table(content)
    # Check that Pipe was escaped
    assert "Pipe \\|" in result
    # Check that newlines were replaced with <br> in description
    assert "Line 1<br>Line 2" in result


