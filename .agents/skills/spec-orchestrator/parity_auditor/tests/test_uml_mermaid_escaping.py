import pytest
from parity_auditor.validators.mermaid_syntax_validator import check_mermaid_text
from parity_auditor.core.findings import Finding

def test_mermaid_state_diagram_escaping():
    valid_content = """
---
generation_mode: subagent
---
# Feature
```mermaid
stateDiagram-v2
    state if_state <<choice>>
    [*] --> Active
    Active --> Active : "increment [value < maxBound]"
    Active --> Inactive : "timeout > 50"
    Inactive --> [*]
```
"""

    invalid_content_1 = """
---
generation_mode: subagent
---
# Feature
```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> Active : increment [value < maxBound]
```
"""

    invalid_content_2 = """
---
generation_mode: subagent
---
# Feature
```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> Inactive : x > 10
```
"""

    invalid_content_3 = """
---
generation_mode: subagent
---
# Feature
```mermaid
stateDiagram-v2
    state A < B as state1
```
"""

    errors_valid = check_mermaid_text(valid_content, "test.md")
    assert not errors_valid
    
    errors_invalid_1 = check_mermaid_text(invalid_content_1, "test.md")
    assert len(errors_invalid_1) == 1
    assert errors_invalid_1[0].rule_id == "mermaid-diagram-unquoted-brackets-forbidden"
    
    errors_invalid_2 = check_mermaid_text(invalid_content_2, "test.md")
    assert len(errors_invalid_2) == 1
    assert errors_invalid_2[0].rule_id == "mermaid-diagram-unquoted-brackets-forbidden"
    
    errors_invalid_3 = check_mermaid_text(invalid_content_3, "test.md")
    assert len(errors_invalid_3) == 1
    assert errors_invalid_3[0].rule_id == "mermaid-diagram-unquoted-brackets-forbidden"
