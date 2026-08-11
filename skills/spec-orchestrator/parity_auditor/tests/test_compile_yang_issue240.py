import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts"))

from compile_yang import build_attributes
from reconcile_backlog import sanitize_mermaid_diagrams


class MockNode:
    def __init__(self, keyword, arg, children=None, substmts=None):
        self.keyword = keyword
        self.arg = arg
        self.i_children = children or []
        self.substmts = substmts or []
        self.i_is_validated = True

    def search_one(self, keyword):
        for c in (self.i_children or self.substmts):
            if c.keyword == keyword:
                return c
        return None


def test_build_attributes_filters_choice_and_case():
    type_stmt = MockNode("type", "string")
    lat_leaf = MockNode("leaf", "latitude", children=[type_stmt])
    long_leaf = MockNode("leaf", "longitude", children=[type_stmt])

    gps_case = MockNode("case", "gps-case", children=[lat_leaf, long_leaf])
    loc_choice = MockNode("choice", "location-choice", children=[gps_case])
    loc_container = MockNode("container", "location", children=[loc_choice])

    attrs = build_attributes([loc_container])

    # Assert choice and case node names are NOT created as scalar attributes
    # and NOT included in child leaf XPath paths.
    attr_keys = [a["key"] for a in attrs]
    assert "location/latitude" in attr_keys
    assert "location/longitude" in attr_keys

    for a in attrs:
        assert "location-choice" not in a["key"]
        assert "gps-case" not in a["key"]

    assert len(attrs) == 2


def test_sanitize_mermaid_diagrams_fixes_line_wrapped_arrows():
    input_md = (
        "# Spec\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    participant A\n"
        "    participant B\n"
        "    A ->>\n"
        "    B: message\n"
        "    A ->\n"
        "    > B: reply\n"
        "    A --\n"
        "    > B: done\n"
        "```\n"
    )

    sanitized = sanitize_mermaid_diagrams(input_md)

    assert "A ->> B: message" in sanitized
    assert "A ->> B: reply" in sanitized
    assert "A --> B: done" in sanitized
    assert "A ->>\n    B: message" not in sanitized


def test_resolve_type_with_typedef_chain():
    from compile_yang import resolve_type

    # Bottom level: built-in int32 with range constraint
    typedef_base = MockNode("typedef", "my-base-type")
    range_stmt = MockNode("range", "1..10")
    type_stmt_base = MockNode("type", "int32", children=[range_stmt])
    typedef_base.i_children = [type_stmt_base]

    # Mid level: typedef inheriting my-base-type
    typedef_outer = MockNode("typedef", "my-outer-type")
    type_stmt_outer = MockNode("type", "my-base-type")
    type_stmt_outer.i_typedef = typedef_base
    typedef_outer.i_children = [type_stmt_outer]

    # Leaf level: leaf referencing my-outer-type with pattern constraint
    leaf_type = MockNode("type", "my-outer-type")
    leaf_type.i_typedef = typedef_outer
    pattern_stmt = MockNode("pattern", "[0-9]+")
    leaf_type.substmts = [pattern_stmt]

    # Resolve
    res = resolve_type(leaf_type)
    assert res["lui_type"] == "int"
    assert res["minValue"] == 1
    assert res["maxValue"] == 10
    assert res["pattern"] == "[0-9]+"


def test_build_lui_json_uses_normative_names_and_flattened_splitters():
    from compile_yang import build_lui_json

    res = build_lui_json([])
    layout = res["layout"]["root_container"]

    assert layout["type"] == "SidebarLayout"

    sidebar = layout["children"][0]
    assert sidebar["type"] == "HierarchyTree"
    assert sidebar["id"] == "resource_tree"

    workspace = layout["children"][1]
    assert workspace["type"] == "ResizableSplitter"
    assert workspace["id"] == "workspace_split"
    assert workspace["props"]["axis"] == "vertical"

    top_pane = workspace["children"][0]
    assert top_pane["type"] == "TopologyMap"
    assert top_pane["id"] == "topology_pane"

    elements_table = workspace["children"][1]
    assert elements_table["type"] == "DensityTable"
    assert elements_table["id"] == "elements_view"

    tabbed_container = workspace["children"][2]
    assert tabbed_container["type"] == "TabbedContainer"
    assert tabbed_container["id"] == "details_and_relations_tab"


def test_parse_yang_with_only_groupings():
    import tempfile
    from compile_yang import parse_yang, build_lui_json

    yang_content = """module test-grouping-unit {
  yang-version 1.1;
  namespace "urn:ietf:params:xml:ns:yang:test-grouping-unit";
  prefix tgu;

  grouping location-group {
    container location {
      leaf latitude {
        type string;
      }
      leaf longitude {
        type string;
      }
    }
  }
}"""

    with tempfile.NamedTemporaryFile(suffix=".yang", mode="w", delete=False) as f:
        f.write(yang_content)
        temp_path = f.name

    try:
        data_defs = parse_yang(temp_path)
        assert len(data_defs) == 1
        assert data_defs[0].keyword == "container"
        assert data_defs[0].arg == "location"

        lui_json = build_lui_json(data_defs)
        assert len(lui_json["attributes"]) == 2
        assert lui_json["attributes"][0]["key"] == "location/latitude"
        assert lui_json["attributes"][1]["key"] == "location/longitude"
    finally:
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)
