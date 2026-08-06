"""Regression tests for issue #279 - empty Mermaid class bodies.

#279 asked for instructions forbidding *all* empty Mermaid classes
(``class Name { }``). Investigation showed that the blanket prohibition would be
wrong and the narrow one is a real defect:

* An attribute-less class is **legitimate and mandated**. Ancestor container nodes
  exist only to carry the containment path (``schema-specification-engineering``
  SKILL.md requires class nodes for every ancestor container), and the canonical
  Feature template in that same skill ships ``class ParentContainer {`` / ``}``.
  Two more live in ``docs/``. Flagging those would reject the repository's own
  template - the false-positive failure the validator's docstring warns about.
* The **single-line** form ``class X {}`` is a genuine defect. It is not caught by
  any existing rule, and it silently corrupts this repository's own class-diagram
  parser: ``parsers/mermaid.py`` opens a class block on ``class X {`` and only
  closes one on a line that is exactly ``}``, so a same-line ``}`` never pops the
  block. A later ``}`` - for instance the one closing a ``namespace`` - pops the
  leaked class block instead, and every following class is silently assigned to
  the wrong namespace with no parse error raised.

So the rule enforced here is narrow: empty bodies stay legal, the single-line
spelling does not. Documented in ``rules/platform-independence.md`` under
*Mermaid Empty Class Body Rules* and registered in
``tests/rule_contracts.py``.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.core.findings import Finding  # noqa: E402
from parity_auditor.validators.mermaid_syntax_validator import (  # noqa: E402
    check_mermaid_text,
)

FENCE = "```"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

RULE_ID = "mermaid-no-single-line-empty-class-body"
ANCHOR = "single-line empty Mermaid class body"

# The canonical Feature template, verbatim in shape from
# skills/schema-specification-engineering/SKILL.md. The empty ancestor container is
# the point: it must stay clean.
CANONICAL_TEMPLATE = """classDiagram
    class ParentContainer {
    }
    class FeatureClassifier {
        +String primaryAttribute "[1]"
        +Boolean doSomething(String param)
    }
    ParentContainer *-- FeatureClassifier : featureClassifier"""

ONE_LINE_EMPTY = """classDiagram
    class ParentContainer {}
    class FeatureClassifier {
        +String primaryAttribute "[1]"
    }
    ParentContainer *-- FeatureClassifier : featureClassifier"""


def _block(body):
    return f"{FENCE}mermaid\n{body}\n{FENCE}\n"


def _empty_class_findings(errors):
    return [e for e in errors if ANCHOR in e]


def test_single_line_empty_class_body_is_rejected_issue279():
    errors = check_mermaid_text(_block(ONE_LINE_EMPTY), source="feat-01.md")
    hits = _empty_class_findings(errors)
    assert hits, (
        "'class ParentContainer {}' must be reported: the same-line closing brace "
        f"never closes the block in parsers/mermaid.py. Got: {list(errors)}"
    )
    assert "feat-01.md:3:" in hits[0], f"finding must carry file and line: {hits[0]!r}"
    assert isinstance(hits[0], Finding) and hits[0].rule_id == RULE_ID, (
        f"finding must carry the registered rule id {RULE_ID!r}"
    )


def test_multi_line_empty_class_body_is_accepted_issue279():
    """The ancestor-container form is mandated elsewhere and must not be flagged."""
    errors = check_mermaid_text(_block(CANONICAL_TEMPLATE), source="feat-01.md")
    assert _empty_class_findings(errors) == [], (
        "an attribute-less class spelled over two lines is the required form for "
        f"ancestor containers and must stay clean. Got: {list(errors)}"
    )


def test_bare_class_declaration_is_accepted_issue279():
    text = _block("classDiagram\n    class Marker\n    Marker --> Other : uses")
    assert _empty_class_findings(check_mermaid_text(text)) == []


def test_embedded_diff_context_line_is_not_flagged_issue279():
    """Docs embed unified diffs; a '-'/'+' marker is not a class declaration."""
    text = (
        "@@ -20,3 +20,3 @@\n"
        "     " + FENCE + "mermaid\n"
        "     classDiagram\n"
        "-    class ParentContainer {}\n"
        "+    class ParentContainer {\n"
        "+    }\n"
        "     " + FENCE + "\n"
    )
    assert _empty_class_findings(check_mermaid_text(text)) == [], (
        "a diff context line must not be read as a class declaration"
    )


def test_canonical_skill_template_stays_clean_issue279():
    """The live template is the false-positive control for this rule."""
    path = os.path.join(
        REPO_ROOT, "skills", "schema-specification-engineering", "SKILL.md"
    )
    assert os.path.isfile(path), f"canonical template skill missing: {path}"
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Fixture guard: the control is only meaningful if the file really contains an
    # empty class body written the permitted way.
    empty_bodies = re.findall(r"class\s+\S+\s*\{\s*\n\s*\}", content)
    assert empty_bodies, (
        "expected at least one multi-line empty class body in the canonical Feature "
        "template; without it this test asserts nothing"
    )

    errors = check_mermaid_text(content, source="skills/schema-specification-engineering/SKILL.md")
    assert _empty_class_findings(errors) == [], (
        f"the canonical template must satisfy our own rule. Got: {list(errors)}"
    )
