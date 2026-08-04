import pytest
from parity_auditor.validators.mermaid_syntax_validator import (
    validate_mermaid_subgraph_title_quoting,
    validate_mermaid_node_label_quoting,
    validate_mermaid_angle_bracket_escaping,
    check_mermaid_text
)

def test_validate_mermaid_subgraph_title_quoting():
    assert validate_mermaid_subgraph_title_quoting('subgraph "System Boundary"') is None
    assert validate_mermaid_subgraph_title_quoting('subgraph System Boundary') == "System Boundary"
    assert validate_mermaid_subgraph_title_quoting('subgraph System-Boundary') == "System-Boundary"
    assert validate_mermaid_subgraph_title_quoting('subgraph SystemBoundary') is None
    assert validate_mermaid_subgraph_title_quoting('subgraph "System Boundary"') is None

def test_validate_mermaid_node_label_quoting():
    assert not validate_mermaid_node_label_quoting('Node["Save/Restore (Local DB)"]')
    assert not validate_mermaid_node_label_quoting('Node(Label)')
    
    assert validate_mermaid_node_label_quoting('Node[Save/Restore]') == ['Save/Restore']
    assert validate_mermaid_node_label_quoting('Node[Save:Restore]') == ['Save:Restore']
    assert validate_mermaid_node_label_quoting('Node[Save(Restore)]') == ['Save(Restore)']
    assert validate_mermaid_node_label_quoting('Node[Save[Restore]]') == ['Save[Restore']

def test_validate_mermaid_angle_bracket_escaping():
    assert validate_mermaid_angle_bracket_escaping('A --> B : "incrementCounter [value < maxBound]"') is None
    assert validate_mermaid_angle_bracket_escaping('A --> B : incrementCounter [value < maxBound]') == '<'
    assert validate_mermaid_angle_bracket_escaping('<<extend>>') is None
    assert validate_mermaid_angle_bracket_escaping('A ->> B: <<extend>>') is None

def test_check_mermaid_text_universal():
    content = """
```mermaid
graph TD
    subgraph System Boundary
        Node[Save/Restore]
    end
    A --> B: a < b
```
"""
    errors = check_mermaid_text(content, "test.md")
    error_ids = [e.rule_id for e in errors]
    assert "mermaid-subgraph-title-must-be-quoted" in error_ids
    assert "mermaid-node-label-must-be-quoted" in error_ids
    assert "mermaid-diagram-unquoted-brackets-forbidden" in error_ids
