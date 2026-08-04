"""Regression tests for issue #333 — colons in Mermaid relationship labels.

`rules/platform-independence.md` grouped colons with spaces as characters that
double-quoting makes safe. That is true of spaces and false of colons: Mermaid parses
`:` as a statement separator wherever it appears, so `"augments nw:node"` ends the
statement mid-label and GitHub reports
`Parse error on line N: Expecting 'NEWLINE', 'EOF', got 'LABEL'`.

The label satisfied the documented rule, so the offline gate passed it and nothing
caught the defect until a renderer refused the diagram. The gate enforces documented
rules rather than the Mermaid grammar — `.pipeline/upstream/pipeline-tooling.md`
§ *Validation Gates* forbids calling a remote renderer as a blocking gate — so a wrong
rule is invisible by construction. That is the failure this test closes.
"""

import os
import sys

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parity_auditor.validators.mermaid_syntax_validator import (  # noqa: E402
    check_mermaid_text,
)

RULES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                 "rules", "platform-independence.md")
)


def _diagram(relationship):
    return (
        "```mermaid\nclassDiagram\n"
        "    class Nw {\n    }\n"
        "    class Node {\n    }\n"
        f"    {relationship}\n"
        "```\n"
    )


def test_quoted_colon_label_is_rejected_issue333():
    """The exact shape that passed the gate and then failed to render."""
    errors = check_mermaid_text(
        _diagram('Nw *-- Node : "augments nw:node"'), source="epic-06.md"
    )
    assert errors, (
        "a quoted relationship label containing a colon was accepted. Quoting does "
        "not make a colon safe — Mermaid ends the statement at it."
    )
    assert any(
        getattr(e, "rule_id", "") == "mermaid-no-colon-in-relationship-label"
        for e in errors
    ), errors


def test_unquoted_colon_label_is_rejected_issue333():
    errors = check_mermaid_text(
        _diagram("Nw *-- Node : augments nw:node"), source="epic-06.md"
    )
    assert errors
    assert any(
        getattr(e, "rule_id", "") == "mermaid-no-colon-in-relationship-label"
        for e in errors
    ), errors


def test_quoted_multiword_label_without_a_colon_is_still_accepted_issue333():
    """Positive control: quoting genuinely does fix spaces, and must keep working."""
    assert check_mermaid_text(
        _diagram('Nw *-- Node : "contains a nested container"'), source="epic-06.md"
    ) == []


def test_single_word_label_is_still_accepted_issue333():
    assert check_mermaid_text(
        _diagram("Nw *-- Node : references"), source="epic-06.md"
    ) == []


def test_unquoted_multiword_label_is_still_rejected_issue333():
    """The original rule was right about spaces; that half must not regress."""
    errors = check_mermaid_text(
        _diagram("Nw *-- Node : contains a nested container"), source="epic-06.md"
    )
    assert any(
        getattr(e, "rule_id", "") == "mermaid-relationship-label-must-be-quoted"
        for e in errors
    ), errors


def test_the_rule_no_longer_claims_quoting_makes_colons_safe_issue333():
    """The documented rule is the thing that was wrong; assert it was corrected."""
    assert os.path.isfile(RULES), f"{RULES} missing; this assertion would be vacuous"
    with open(RULES, encoding="utf-8") as fh:
        text = fh.read()
    assert "Mermaid Relationship Label Colon Rules" in text, (
        "the corrected rule is absent. A subagent reads rules/, so a gate without the "
        "rule text tells the generator nothing about why its output is rejected."
    )
    assert "Relationship labels containing spaces or colons MUST be enclosed" not in text, (
        "the original wording survives, which still instructs authors that quoting "
        "makes a colon acceptable"
    )
