"""Tests for UmlValidator epic-prohibit-unreplaced-placeholder-text lint check (Issue #391)."""

import pytest
from parity_auditor.validators.uml import UmlValidator


EPIC_WITH_SEMANTIC_LINKAGE_JUSTIFICATION = """---
title: "Epic: Test"
type: "epic"
generation_mode: "subagent"
---

# Epic: Test

## 1. Context
Context text.

## 2. Requirements & Checklist
- [ ] #101 - [Feature Title](https://github.com/org/repo/blob/main/docs/features/feat-01.md) (semantic linkage justification and clause references)

## 3. Architecture

### Subsystem Component Definition
```mermaid
classDiagram
    class SubsystemComponent {
        <<component>>
    }
```

## System-Level UML Class Diagram
```mermaid
classDiagram
    class SubsystemComponent {
        <<component>>
    }
```

## System State Machine Diagram
```mermaid
stateDiagram-v2
    [*] --> Active
```

## 4. Operational Considerations
Operational text.

## 5. Security & Governance
Security text.

## 6. Source References
Source text.
"""

EPIC_WITH_POPULATE_TOKEN = """---
title: "Epic: Test"
type: "epic"
generation_mode: "subagent"
---

# Epic: Test

## 1. Context
Context text.

## 2. Requirements & Checklist
- [ ] #101 - [Feature Title](https://github.com/org/repo/blob/main/docs/features/feat-01.md) [POPULATE: concise semantic linkage justification e.g. "defines counter and gauge typedefs"]

## 3. Architecture

### Subsystem Component Definition
```mermaid
classDiagram
    class SubsystemComponent {
        <<component>>
    }
```

## System-Level UML Class Diagram
```mermaid
classDiagram
    class SubsystemComponent {
        <<component>>
    }
```

## System State Machine Diagram
```mermaid
stateDiagram-v2
    [*] --> Active
```

## 4. Operational Considerations
Operational text.

## 5. Security & Governance
Security text.

## 6. Source References
Source text.
"""


def test_epic_prohibit_unreplaced_placeholder_text_semantic_linkage():
    errors = []
    validator = UmlValidator()
    validator._validate_placeholders_and_links(
        EPIC_WITH_SEMANTIC_LINKAGE_JUSTIFICATION,
        "Epic",
        "epic-01-test.md",
        errors,
        r"- \[[ xX]\]",
    )
    finding_ids = [e.rule_id if hasattr(e, "rule_id") else str(e) for e in errors]
    assert "epic-prohibit-unreplaced-placeholder-text" in finding_ids, (
        f"Expected finding 'epic-prohibit-unreplaced-placeholder-text' in {finding_ids}"
    )


def test_epic_prohibit_unreplaced_placeholder_text_populate_token():
    errors = []
    validator = UmlValidator()
    validator._validate_placeholders_and_links(
        EPIC_WITH_POPULATE_TOKEN,
        "Epic",
        "epic-01-test.md",
        errors,
        r"- \[[ xX]\]",
    )
    finding_ids = [e.rule_id if hasattr(e, "rule_id") else str(e) for e in errors]
    assert "epic-prohibit-unreplaced-placeholder-text" in finding_ids, (
        f"Expected finding 'epic-prohibit-unreplaced-placeholder-text' in {finding_ids}"
    )
