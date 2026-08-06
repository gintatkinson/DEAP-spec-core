"""Governance half of issue #279 - empty Mermaid classes.

#279 reported that the orchestrator's subagent-dispatch context (the bullet list
under *Subagent Dispatch* in ``skills/spec-orchestrator/SKILL.md``) never tells a
generating subagent which Mermaid constraints apply, and asked for a prohibition on
empty classes to be pasted into that list.

Two things are asserted here instead:

1. The rule has a **normative home**, not a local restatement. Per
   ``rules/platform-independence.md`` § *Normative home & enforcement*, a skill that
   restates its own subset is the #289 defect; skills point at the rules file. The
   dispatch context must therefore cite the rules file, and every skill that emits
   Mermaid must do the same.
2. The rule the issue asked for is documented in that home and paired with the code
   that enforces it, so ``tests/rule_contracts.py`` sees it.

The rule itself is narrower than #279 proposed: an attribute-less class is legal and
in places mandated - ancestor container nodes carry the containment path and the
canonical Feature template ships one - so only the single-line ``class X {}``
spelling is prohibited. That form leaves ``parsers/mermaid.py`` with an unclosed
class block and silently reassigns later classes to the wrong namespace.
"""

import os
import re

from rule_contracts import REGISTERED_RULE_IDS

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

RULES_FILE = os.path.join(REPO_ROOT, "rules", "platform-independence.md")
ORCHESTRATOR_SKILL = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "SKILL.md")
NORMATIVE_HOME = "rules/platform-independence.md"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_empty_class_body_rule_is_documented_issue279():
    content = _read(RULES_FILE)
    assert "**Mermaid Empty Class Body Rules**:" in content, (
        "the single-line empty class body prohibition must be stated in the single "
        "normative home for Mermaid rules"
    )
    heading_line = next(
        line for line in content.splitlines()
        if "**Mermaid Empty Class Body Rules**:" in line
    )
    assert "class ParentContainer {}" in heading_line or "class X {}" in heading_line, (
        "the rule must show the prohibited spelling, or an author cannot recognise it"
    )
    # The permitted form must stay explicitly permitted: ancestor container nodes are
    # mandated by schema-specification-engineering and are attribute-less.
    assert "ancestor container" in heading_line.lower(), (
        "the rule must say that attribute-less classes remain legal, or it will be "
        "read as a blanket prohibition and break the canonical Feature template"
    )


def test_documented_rule_is_paired_with_enforcement_issue279():
    """The emitted rule id must be registered, per #299 and #301."""
    from parity_auditor.validators.mermaid_syntax_validator import check_mermaid_text

    text = "```mermaid\nclassDiagram\n    class ParentContainer {}\n```\n"
    findings = [f for f in check_mermaid_text(text) if getattr(f, "rule_id", "")]
    ids = {f.rule_id for f in findings}
    assert ids, "the single-line empty class body must produce a Finding with a rule id"
    unregistered = sorted(ids - REGISTERED_RULE_IDS)
    assert not unregistered, (
        f"rule ids emitted for #279 but absent from the contract registry: {unregistered}"
    )


def test_spec_orchestrator_dispatch_context_cites_the_mermaid_rules_home_issue279():
    content = _read(ORCHESTRATOR_SKILL)
    marker = "2. **Subagent Dispatch**"
    start = content.find(marker)
    assert start != -1, (
        f"could not locate {marker!r} in {ORCHESTRATOR_SKILL}; the assertion below "
        "would be vacuous"
    )
    end = content.find("\n3. ", start)
    assert end > start, "could not delimit the Subagent Dispatch context list"
    section = content[start:end]
    assert len(section.splitlines()) >= 4, "dispatch context list looks truncated"
    assert NORMATIVE_HOME in section, (
        "the context passed to a generating subagent must name "
        f"{NORMATIVE_HOME}, or the subagent cannot comply with rules it is never "
        f"shown (#279). Section was:\n{section}"
    )


def test_mermaid_emitting_skills_cite_the_normative_home_issue279():
    """Every skill shipping a Mermaid template must point at the rules file, not
    restate a subset of it (#289)."""
    emitting = []
    skills_root = os.path.join(REPO_ROOT, "skills")
    for dirpath, _dirnames, filenames in os.walk(skills_root):
        if "SKILL.md" not in filenames:
            continue
        path = os.path.join(dirpath, "SKILL.md")
        content = _read(path)
        if re.search(r"```mermaid", content):
            emitting.append((os.path.relpath(path, REPO_ROOT), content))

    assert len(emitting) >= 3, (
        f"only {len(emitting)} skill(s) with Mermaid templates discovered; the "
        "assertion below would be near-vacuous"
    )
    missing = sorted(rel for rel, content in emitting if NORMATIVE_HOME not in content)
    assert not missing, (
        f"skills emitting Mermaid without citing {NORMATIVE_HOME}: {missing}"
    )
