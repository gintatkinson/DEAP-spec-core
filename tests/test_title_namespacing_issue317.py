"""Regression tests for issue #317 — generated item titles are not namespaced.

Item subagents draft one specification each from one schema node, with no sight of the
other items in the run (that isolation is mandated, and enforced, by #278). A node name
reused across modules — ``geo-location``, ``status``, ``interface`` are the standard
examples — therefore produces the same title twice, and neither subagent is in a
position to notice. Nothing in the orchestrator's dispatch payload told them to
namespace the title, so identical titles were the expected output rather than an
accident.

**Where the rule lives.** ``rules/platform-independence.md`` section *Normative home &
enforcement* sets the convention: a rule gets one normative home, and a skill that must
observe it references that home instead of restating a subset. The four fragmented
Mermaid statements it was written for are the cautionary case. Title namespacing is a
constraint on backlog identity — the same subject as the ``issue_id`` mandate and the
ordinal-collision rule — so its home is ``rules/tracker-source-of-truth.md``, and
``skills/spec-orchestrator/SKILL.md`` points the item subagent at it exactly as it
already points at ``rules/platform-independence.md`` for Mermaid.

**What is enforced, and what is not.** The *effect* of namespacing — no two
specifications of one type normalising to the same title — is enforced offline by
``validators/spec_title_uniqueness_validator.py`` (issue #318). The *shape* of the
prefix is deliberately not shape-checked; see
``rule_contracts.KNOWN_UNREGISTERED_FAMILIES['generated-title-prefix-shape']`` for why,
recorded there rather than left as a silent gap. What these tests enforce is the half
that was actually missing in #317: that the constraint is stated normatively and
reaches the drafting subagent.

Messages are prefixed ``namespacing-gate:`` so the contract registry can anchor on
them, matching the ``isolation-gate:`` convention in
``tests/test_subagent_isolation_contract_issue278.py``.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRACKER_RULE = os.path.join(REPO_ROOT, "rules", "tracker-source-of-truth.md")
ORCHESTRATOR = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "SKILL.md")

ISOLATION_HEADING = "## Item-Level Subagent Context Isolation"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _isolation_section(text):
    """The dispatch section of the orchestrator skill, heading to next heading."""
    start = text.find(ISOLATION_HEADING)
    if start < 0:
        return ""
    end = text.find("\n## ", start + len(ISOLATION_HEADING))
    return text[start:] if end < 0 else text[start:end]


# --------------------------------------------------------------------------- #
# Fixture guards. Every assertion below reads these two files.
# --------------------------------------------------------------------------- #

def test_governed_documents_are_discoverable_issue317():
    for path in (TRACKER_RULE, ORCHESTRATOR):
        assert os.path.isfile(path), f"governance document not found: {path}"
    section = _isolation_section(_read(ORCHESTRATOR))
    assert len(section) > 500, (
        "the Item-Level Subagent Context Isolation section was not located in "
        "skills/spec-orchestrator/SKILL.md, so the dispatch-payload assertions below "
        "would pass vacuously. The heading was probably renamed."
    )


# --------------------------------------------------------------------------- #
# The rule must have a normative home.
# --------------------------------------------------------------------------- #

def test_tracker_rule_states_the_namespacing_constraint_issue317():
    text = _read(TRACKER_RULE)
    assert "Generated Item Titles Must Be Namespaced To Their Source Module" in text, (
        "namespacing-gate: the tracker rule omits the title namespacing constraint. "
        "rules/tracker-source-of-truth.md is the normative home for backlog identity "
        "rules; without the statement there, the constraint the orchestrator passes to "
        "each subagent points at nothing."
    )
    assert re.search(r"bracket", text, re.I), (
        "namespacing-gate: the tracker rule omits the title namespacing constraint. "
        "The statement must describe the prefix concretely enough to be followed, not "
        "merely assert that titles should be distinguishable."
    )


def test_tracker_rule_records_what_enforces_the_constraint_issue317():
    """An unenforced MUST is orphan documentation — the #289 defect class.

    The uniqueness half is mechanically enforced and the prefix-shape half is not, so
    the rule has to say which is which. Stating both as though both were gated is how
    a reader comes to trust a check that does not exist.
    """
    text = _read(TRACKER_RULE)
    assert "spec_title_uniqueness_validator.py" in text, (
        "namespacing-gate: the tracker rule does not name the check that enforces it. "
        "The uniqueness gate added for #318 is what makes the namespacing rule "
        "observable; a rule with no named enforcement is indistinguishable from advice."
    )
    assert re.search(r"not.{0,40}shape", text, re.I), (
        "namespacing-gate: the tracker rule does not name the check that enforces it. "
        "It must also record that the prefix *shape* is deliberately not checked, or "
        "the unenforced half reads as enforced."
    )


# --------------------------------------------------------------------------- #
# The rule must reach the subagent that drafts the title.
# --------------------------------------------------------------------------- #

def test_drafting_dispatch_passes_the_namespacing_constraint_issue317():
    section = _isolation_section(_read(ORCHESTRATOR))
    assert re.search(r"namespac", section, re.I), (
        "namespacing-gate: the drafting step omits the title namespacing constraint. "
        "Issue #317's defect is precisely that the dispatch payload never mentioned it, "
        "so an item subagent drafting one node in isolation could not have complied."
    )
    assert "rules/tracker-source-of-truth.md" in section, (
        "namespacing-gate: the drafting step omits the title namespacing constraint. "
        "It must cite the normative home rather than restate the rule, per "
        "rules/platform-independence.md section Normative home & enforcement."
    )


def test_orchestrator_does_not_fork_the_rule_issue317():
    """The skill may point at the rule; it may not become a second statement of it.

    Four disjoint restatements of the Mermaid rules is what issue #289 had to undo, and
    the convention exists so that is not re-created one skill at a time.
    """
    section = _isolation_section(_read(ORCHESTRATOR))
    assert "Generated Item Titles Must Be Namespaced To Their Source Module" not in section, (
        "namespacing-gate: the drafting step restates the rule instead of citing it. "
        "Copying the normative heading into the skill forks the rule; reference "
        "rules/tracker-source-of-truth.md and pass that file to the subagent instead."
    )
