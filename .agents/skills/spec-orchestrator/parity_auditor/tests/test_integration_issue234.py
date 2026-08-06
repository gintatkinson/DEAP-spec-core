import os
import sys
import tempfile
import json
import shutil

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
from parity_auditor.core.workspace import WorkspaceRepository
from compile_yang import compile_yang


def _create_integration_repo(tmpdir, feature_content, include_properties_view=True):
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)

    rules_src_path = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json")
    with open(rules_src_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    if include_properties_view:
        details_tabs = rules_data.get("layout_rules", {}).get("details_tabs", [])
        if not any(t.get("id") == "properties_view" for t in details_tabs):
            details_tabs.insert(0, {
                "type": "PropertyGrid",
                "id": "properties_view",
                "props": {"label": "Properties"}
            })
        rules_data["layout_rules"]["details_tabs"] = details_tabs

    rules_data["backlog_directories"]["features"] = ".pipeline/backlog/features"

    rules_dest_path = os.path.join(pipeline_dir, "codebase_rules.json")
    with open(rules_dest_path, "w", encoding="utf-8") as f:
        json.dump(rules_data, f, indent=2)

    yang_path = os.path.join(tmpdir, "test-schema.yang")
    yang_content = """module test-schema {
    namespace "urn:test:schema";
    prefix test;

    container system {
        leaf hostname {
            type string;
        }
    }
}
"""
    with open(yang_path, "w", encoding="utf-8") as f:
        f.write(yang_content)

    layout_output_path = os.path.join(pipeline_dir, "logical-layout.json")

    old_cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        compile_yang(yang_path, layout_output_path)
    finally:
        os.chdir(old_cwd)

    features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
    os.makedirs(features_dir, exist_ok=True)

    feat_path = os.path.join(features_dir, "feat-001-test.md")
    with open(feat_path, "w", encoding="utf-8") as f:
        f.write(feature_content)

    return WorkspaceRepository(tmpdir)


def test_compile_yang_clean_integration():
    tmpdir = tempfile.mkdtemp()
    try:
        feature_content = """# Feature: Test Clean Integration

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TableView
- **Target Layout Container ID**: components_table
- **Data Source Binding**: /schema:test/system
"""
        repo = _create_integration_repo(tmpdir, feature_content)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert len(errors) == 0, f"Expected 0 validation errors, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_component_container_type_mismatch_tableview_on_properties_view():
    tmpdir = tempfile.mkdtemp()
    try:
        feature_content = """# Feature: Mismatch TableView on PropertyGrid Container

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TableView
- **Target Layout Container ID**: properties_view
- **Data Source Binding**: /schema:test/system
"""
        repo = _create_integration_repo(tmpdir, feature_content, include_properties_view=True)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        
        mismatch_errors = [
            e for e in errors
            if "specifies component type 'TableView'" in e and "properties_view" in e and "PropertyGrid" in e
        ]
        assert len(mismatch_errors) == 1, f"Expected 1 component-container type mismatch error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_component_container_type_mismatch_propertygrid_on_components_table():
    tmpdir = tempfile.mkdtemp()
    try:
        feature_content = """# Feature: Mismatch PropertyGrid on TableView Container

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: PropertyGrid
- **Target Layout Container ID**: components_table
- **Data Source Binding**: /schema:test/system
"""
        repo = _create_integration_repo(tmpdir, feature_content)
        validator = LogicalUiValidator()
        errors = validator.validate(repo)

        mismatch_errors = [
            e for e in errors
            if "specifies component type 'PropertyGrid'" in e and "components_table" in e and "TableView" in e
        ]
        assert len(mismatch_errors) == 1, f"Expected 1 component-container type mismatch error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_component_container_type_mismatch_topology_map_on_topology_pane():
    tmpdir = tempfile.mkdtemp()
    try:
        # Case A: PropertyGrid specified on topology_pane (which is TopologyMap)
        feature_content_a = """# Feature: Mismatch PropertyGrid on TopologyMap Container

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: PropertyGrid
- **Target Layout Container ID**: topology_pane
- **Data Source Binding**: /schema:test/system
"""
        repo_a = _create_integration_repo(tmpdir, feature_content_a)
        validator = LogicalUiValidator()
        errors_a = validator.validate(repo_a)

        mismatch_errors_a = [
            e for e in errors_a
            if "specifies component type 'PropertyGrid'" in e and "topology_pane" in e and "TopologyMap" in e
        ]
        assert len(mismatch_errors_a) == 1, f"Expected 1 mismatch error for topology_pane, got: {errors_a}"

        # Case B: TopologyMap specified on components_table (which is TableView)
        feat_path = os.path.join(tmpdir, ".pipeline", "backlog", "features", "feat-001-test.md")
        feature_content_b = """# Feature: Mismatch TopologyMap on TableView Container

## 5. Logical UI & Layout Bindings
- **Target LUI Component**: TopologyMap
- **Target Layout Container ID**: components_table
- **Data Source Binding**: /schema:test/system
"""
        with open(feat_path, "w", encoding="utf-8") as f:
            f.write(feature_content_b)

        repo_b = WorkspaceRepository(tmpdir)
        errors_b = validator.validate(repo_b)

        mismatch_errors_b = [
            e for e in errors_b
            if "specifies component type 'TopologyMap'" in e and "components_table" in e and "TableView" in e
        ]
        assert len(mismatch_errors_b) == 1, f"Expected 1 mismatch error for components_table, got: {errors_b}"
    finally:
        shutil.rmtree(tmpdir)
