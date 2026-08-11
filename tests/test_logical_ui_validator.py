import json
import os
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

LOGICAL_UI_PATH = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "logical-layout.json")
FLUTTER_ASSETS_PATH = os.path.join(REPO_ROOT, "app_flutter", "assets", "logical-layout.json")


def _find_container_by_id(node, target_id):
    if isinstance(node, dict):
        if node.get("id") == target_id:
            return node
        for val in node.values():
            res = _find_container_by_id(val, target_id)
            if res:
                return res
    elif isinstance(node, list):
        for item in node:
            res = _find_container_by_id(item, target_id)
            if res:
                return res
    return None


@pytest.mark.parametrize("layout_file_path", [LOGICAL_UI_PATH, FLUTTER_ASSETS_PATH])
def test_workspace_split_axis_is_vertical_and_has_no_nested_splitters(layout_file_path):
    assert os.path.exists(layout_file_path), f"Layout file does not exist: {layout_file_path}"
    with open(layout_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    workspace_split = _find_container_by_id(data, "workspace_split")
    assert workspace_split is not None, f"workspace_split container not found in {layout_file_path}"

    props = workspace_split.get("props", {})
    axis = props.get("axis")
    assert axis == "vertical", f"workspace_split axis is '{axis}', expected 'vertical' in {layout_file_path}"

    children = workspace_split.get("children", [])
    child_ids = [child.get("id") for child in children if isinstance(child, dict)]
    child_types = [child.get("type") for child in children if isinstance(child, dict)]

    # Assert no nested SplitWorkspace or ResizableSplitter exists inside workspace_split
    nested_splitters = [t for t in child_types if t in ("SplitWorkspace", "ResizableSplitter")]
    assert len(nested_splitters) == 0, f"Found nested splitters {nested_splitters} inside workspace_split in {layout_file_path}"
    assert "lower_split" not in child_ids, f"Found nested lower_split container in {layout_file_path}"

    # Assert workspace_split contains flattened items: topology_pane, elements_view, details_and_relations_tab
    assert "topology_pane" in child_ids, f"topology_pane missing from workspace_split in {layout_file_path}"
    assert "elements_view" in child_ids, f"elements_view missing from workspace_split in {layout_file_path}"
    assert "details_and_relations_tab" in child_ids, f"details_and_relations_tab missing from workspace_split in {layout_file_path}"


def _collect_token_prefixed_strings(data, path=""):
    findings = []
    if isinstance(data, dict):
        for k, v in data.items():
            current_path = f"{path}.{k}" if path else k
            findings.extend(_collect_token_prefixed_strings(v, current_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            findings.extend(_collect_token_prefixed_strings(item, current_path))
    elif isinstance(data, str):
        if data.startswith("token:"):
            findings.append((path, data))
    return findings


@pytest.mark.parametrize("layout_file_path", [LOGICAL_UI_PATH, FLUTTER_ASSETS_PATH])
def test_logical_layout_contains_zero_token_indirection_prefixes(layout_file_path):
    assert os.path.exists(layout_file_path), f"Layout file does not exist: {layout_file_path}"
    with open(layout_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    token_findings = _collect_token_prefixed_strings(data)
    assert len(token_findings) == 0, (
        f"Found {len(token_findings)} 'token:' indirection prefixes in {layout_file_path}:\n"
        + "\n".join(f"  - {path}: {val}" for path, val in token_findings)
    )


def _create_lumi_test_repo(tmpdir, layout):
    import tempfile
    import shutil
    from parity_auditor.core.workspace import WorkspaceRepository

    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "target_directories": {"flutter": "app_flutter"},
        "flutter_rules": {},
        "python_rules": {"exclusions": []},
        "spec_rules": {},
        "validation_rules": {},
        "backlog_directories": {
            "epics": ".pipeline/backlog/epics",
            "features": ".pipeline/backlog/features",
            "use_cases": ".pipeline/backlog/use_cases",
            "user_stories": ".pipeline/backlog/user_stories"
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)
    features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")
    os.makedirs(features_dir, exist_ok=True)
    with open(os.path.join(pipeline_dir, "logical-layout.json"), "w") as f:
        json.dump(layout, f)
    return WorkspaceRepository(tmpdir)


def test_lumi_multi_interface_binding_table_parsing():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Multi-Interface LUMI Feature"
interface_type: ["gui", "mcp"]
---
## Logical UI & Interface Bindings

| Interface Channel | Category | Target Component / Handler | Target Container / Endpoint | Data Source Binding |
| --- | --- | --- | --- | --- |
| gui | Visual GUI | StringInputField | elements_view | /schema:path |
| mcp | M2M API | MCPToolHandler | /mcp/tool | /schema:path |
"""
        with open(os.path.join(features_dir, "feat-lumi-table.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert not errors, f"Expected no validation errors for valid LUMI table, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_multi_interface_missing_channel_error():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Missing Channel LUMI Feature"
interface_type: ["gui", "mcp"]
---
## Logical UI & Interface Bindings

| Interface Channel | Category | Target Component / Handler | Target Container / Endpoint | Data Source Binding |
| --- | --- | --- | --- | --- |
| gui | Visual GUI | StringInputField | elements_view | /schema:path |
"""
        with open(os.path.join(features_dir, "feat-lumi-missing.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert any(err.rule_id == "logical-ui-missing-interface-channel-row" for err in errors), f"Expected missing channel error for mcp, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_rejection_of_raw_na_fallback_strings():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Raw NA LUMI Feature"
interface_type: "gui"
---
## Logical UI & Interface Bindings
- **Target LUI Component:** N/A
- **Target Layout Container ID:** N/A
- **Data Source Binding:** N/A
"""
        with open(os.path.join(features_dir, "feat-lumi-na.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert any("contains raw 'N/A' fallback string" in str(err) for err in errors), f"Expected raw N/A rejection error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_unbound_deferred_to_implementation_profile_is_valid():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Unbound LUMI Feature"
interface_type: "gui"
---
## Logical UI & Interface Bindings
- **Target LUI Component:** Unbound (Deferred to Implementation Profile)
- **Target Layout Container ID:** Unbound (Deferred to Implementation Profile)
- **Data Source Binding:** Unbound (Deferred to Implementation Profile)
"""
        with open(os.path.join(features_dir, "feat-lumi-unbound.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert not errors, f"Expected no validation errors for Unbound (Deferred to Implementation Profile), got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_unbound_short_form_is_valid():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Unbound Short Form Feature"
interface_type: "gui"
---
## Logical UI & Interface Bindings
- **Target LUI Component:** Unbound
- **Target Layout Container ID:** Unbound
- **Data Source Binding:** Unbound
"""
        with open(os.path.join(features_dir, "feat-lumi-unbound-short.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert not errors, f"Expected no validation errors for Unbound, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_placeholder_strings_rejected():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "StringInputField", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Placeholder String Feature"
interface_type: "gui"
---
## Logical UI & Interface Bindings
- **Target LUI Component:** Deferred to Feature #X Task Y
- **Target Layout Container ID:** elements_view
- **Data Source Binding:** /schema:path
"""
        with open(os.path.join(features_dir, "feat-lumi-placeholder.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert any(err.rule_id == "logical-ui-prohibit-placeholder-string" for err in errors), f"Expected placeholder rejection error, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)


def test_lumi_authoritative_schema_path_data_source_binding_is_valid():
    import tempfile
    import shutil
    from parity_auditor.validators.logical_ui_validator import LogicalUiValidator
    tmpdir = tempfile.mkdtemp()
    try:
        layout = {"type": "PropertyGrid", "id": "elements_view"}
        repo = _create_lumi_test_repo(tmpdir, layout)
        features_dir = os.path.join(tmpdir, ".pipeline", "backlog", "features")

        content = """---
title: "Authoritative Schema Path Feature"
interface_type: "gui"
---
## Logical UI & Interface Bindings
- **Target LUI Component:** PropertyGrid
- **Target Layout Container ID:** elements_view
- **Data Source Binding:** /nwi:network-inventory/nil:locations/nil:location/nil:geo-location/nil:reference-frame
"""
        with open(os.path.join(features_dir, "feat-lumi-authoritative.md"), "w") as f:
            f.write(content)

        validator = LogicalUiValidator()
        errors = validator.validate(repo)
        assert not errors, f"Expected no validation errors for authoritative schema path, got: {errors}"
    finally:
        shutil.rmtree(tmpdir)




