import pytest
from parity_auditor.validators.mermaid_syntax_validator import check_mermaid_text

def test_unprefixed_members():
    text = """```mermaid
classDiagram
    class User {
        String name
        +int age
        -String email
        ~boolean isActive
    }
```"""
    errors = check_mermaid_text(text)
    assert not errors, f"Expected no errors, got {errors}"

def test_quoted_node_names_with_spaces():
    text = """```mermaid
flowchart TD
    "Node 1" --> "Node 2" : "trans 1"
```"""
    errors = check_mermaid_text(text)
    # The quoting of "trans 1" is checked by another test? The logic fixes the regex to match quoted node names.
    assert not any("mermaid-missing" in str(e) for e in errors)
    assert not any("unquoted Mermaid relationship label" in str(e) for e in errors)

def test_empty_block_headers():
    text = """```mermaid
%% comment only
```"""
    errors = check_mermaid_text(text)
    assert any(e.rule_id == "mermaid-missing-diagram-header" for e in errors)

def test_trailing_comment_empty_classes():
    text = """```mermaid
classDiagram
    class User {} %% empty class
```"""
    errors = check_mermaid_text(text)
    assert any(e.rule_id == "mermaid-no-single-line-empty-class-body" for e in errors)

def test_unclosed_double_quotes():
    text = """```mermaid
graph TD
    A --> B : "label
```"""
    errors = check_mermaid_text(text)
    assert any(e.rule_id == "mermaid-unclosed-quotes" for e in errors)

def test_diagram_scoping_for_brackets():
    # Brackets should be allowed in classDiagram without quoting
    text_class = """```mermaid
classDiagram
    class User {
        List<String> tags
    }
```"""
    errors_class = check_mermaid_text(text_class)
    assert not any(e.rule_id == "mermaid-diagram-unquoted-brackets-forbidden" for e in errors_class)

    # Brackets should trigger an error in graph
    text_graph = """```mermaid
graph TD
    A --> B : label < 5
```"""
    errors_graph = check_mermaid_text(text_graph)
    assert any(e.rule_id == "mermaid-diagram-unquoted-brackets-forbidden" for e in errors_graph)
