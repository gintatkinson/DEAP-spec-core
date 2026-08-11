import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.validators.mermaid_syntax_validator import check_mermaid_text


def test_sequence_participant_reserved_keyword_link():
    """Verify that participant alias 'link' in sequence diagram is flagged as syntax error."""
    text = """```mermaid
sequenceDiagram
    participant link as Link Service
    participant User as User Agent
    User->>link: Send request
```"""
    errors = check_mermaid_text(text, source="test_spec.md")
    assert len(errors) == 1
    assert getattr(errors[0], "rule_id", "") == "mermaid-reserved-keyword-as-participant-alias"
    assert "reserved keyword 'link' used as sequence diagram participant alias/ID" in str(errors[0])


def test_sequence_actor_reserved_keyword_link():
    """Verify that actor alias 'link' in sequence diagram is flagged as syntax error."""
    text = """```mermaid
sequenceDiagram
    actor link as Link Interface
    participant DB as Database
    link->>DB: Query
```"""
    errors = check_mermaid_text(text, source="test_spec.md")
    assert len(errors) == 1
    assert getattr(errors[0], "rule_id", "") == "mermaid-reserved-keyword-as-participant-alias"
    assert "'link'" in str(errors[0])


def test_sequence_participant_other_reserved_keywords():
    """Verify that other sequence diagram reserved keywords (actor, participant, loop, opt, alt, rect, note, end) are flagged."""
    keywords = ["actor", "participant", "loop", "opt", "alt", "rect", "note", "end", "par", "break", "activate"]
    for kw in keywords:
        text = f"""```mermaid
sequenceDiagram
    participant {kw} as Service
    User->>{kw}: Message
```"""
        errors = check_mermaid_text(text, source="test_spec.md")
        assert any(getattr(e, "rule_id", "") == "mermaid-reserved-keyword-as-participant-alias" for e in errors), f"Failed to flag keyword '{kw}'"


def test_sequence_participant_valid_aliases():
    """Verify that valid participant aliases are not flagged."""
    text = """```mermaid
sequenceDiagram
    participant Client as Client Application
    actor Admin as System Administrator
    participant LinkService as Link Processing Service
    Client->>LinkService: Process link
```"""
    errors = check_mermaid_text(text, source="test_spec.md")
    assert errors == []
