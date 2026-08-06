import os
import json

def test_codebase_rules_details_tabs_no_property_grid():
    rules_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", ".pipeline", "logical-ui", "codebase_rules.json"
    )
    rules_path = os.path.abspath(rules_path)
    assert os.path.exists(rules_path), f"codebase_rules.json not found at {rules_path}"
    
    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    details_tabs = data.get("layout_rules", {}).get("details_tabs", [])
    
    # Assert that PropertyGrid is not present in details_tabs
    property_grid_items = [tab for tab in details_tabs if tab.get("type") == "PropertyGrid"]
    assert len(property_grid_items) == 0, f"details_tabs should not contain PropertyGrid items, found: {property_grid_items}"
    
    # Assert all items in details_tabs are TableView
    non_table_view_items = [tab for tab in details_tabs if tab.get("type") != "TableView"]
    assert len(non_table_view_items) == 0, f"details_tabs contains non-TableView items: {non_table_view_items}"
