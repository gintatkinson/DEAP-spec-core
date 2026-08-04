import pytest
from parity_auditor.validators.mermaid_syntax_validator import check_mermaid_text

def test_missing_header_emits_error():
    text = """
```mermaid
class Feature {
  +String foo
}
```
"""
    errors = check_mermaid_text(text, source="test.md")
    assert any(e.rule_id == "mermaid-missing-diagram-header" for e in errors)

def test_valid_header_no_error():
    text = """
```mermaid
%% comment
classDiagram
class Feature {
  +String foo
}
```
"""
    errors = check_mermaid_text(text, source="test.md")
    assert not any(e.rule_id == "mermaid-missing-diagram-header" for e in errors)

def test_statediagram_v2_header_no_error():
    text = """
```mermaid
stateDiagram-v2
[*] --> State
```
"""
    errors = check_mermaid_text(text, source="test.md")
    assert not any(e.rule_id == "mermaid-missing-diagram-header" for e in errors)
