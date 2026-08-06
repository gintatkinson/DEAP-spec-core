"""Regression tests for the skip-set scope in `reconcile_backlog.py` (issue #321).

Package N6 stopped the reconciler aborting wholesale: it now skips the specifications
the linter rejected and synchronises the rest. The first implementation built that skip
set with a bare regex over the linter's output, which also matched documents merely
*cited* by a finding. A remediation note reading "see rules/document-references.md" put
`document-references.md` in the skip set, and `constitution.md` with it — files the
reconciler had never been asked to validate and does not synchronise.

Observed live: 27 names in the skip set, of which 6 were not specifications at all.

Over-broad matching is the defect class this whole sprint has been closing — the alias
map claiming a Feature's slug (#319), the label check matching `feature-request` for
`feature` (#332). This is the same shape in the fix for #321, so it gets the same
treatment: intersect with what actually exists rather than trusting a pattern.
"""

import os
import sys

SCRIPTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from reconcile_backlog import blocked_specs_from_linter_output  # noqa: E402

RULES = {"backlog_directories": {
    "epics": "docs/epics", "features": "docs/features",
    "user_stories": "docs/user-stories", "use_cases": "docs/use-cases",
}}


def _workspace(tmp_path, features=(), epics=()):
    for rel, names in (("docs/features", features), ("docs/epics", epics)):
        d = tmp_path / rel
        d.mkdir(parents=True, exist_ok=True)
        for name in names:
            (d / name).write_text("# spec\n")
    return str(tmp_path)


def test_a_rejected_specification_is_blocked(tmp_path):
    """Guard and baseline: the mechanism must actually select something."""
    ws = _workspace(tmp_path, features=["feat-01-geo.md", "feat-02-node.md"])
    out = "  - Feature feat-01-geo.md:14 contains unresolved issue reference token"
    assert blocked_specs_from_linter_output(out, ws, RULES) == {"feat-01-geo.md"}


def test_a_merely_cited_document_is_not_blocked(tmp_path):
    """The defect: a finding's remediation note naming another file.

    `document-references.md` and `constitution.md` are not specifications and are not
    synchronised by the reconciler, so skipping them is meaningless — but it made the
    skip report claim 27 blocked items when 21 were real.
    """
    ws = _workspace(tmp_path, features=["feat-01-geo.md"])
    out = (
        "  - Feature feat-01-geo.md:36: unquoted relationship label. "
        "See rules/document-references.md and .pipeline/constitution.md for the rule."
    )
    blocked = blocked_specs_from_linter_output(out, ws, RULES)
    assert blocked == {"feat-01-geo.md"}, (
        f"documents cited in remediation text entered the skip set: {blocked}"
    )


def test_a_template_placeholder_name_is_not_blocked(tmp_path):
    """`epic-XX-name.md` is the literal placeholder a finding quotes, not a file."""
    ws = _workspace(tmp_path, epics=["epic-01-real.md"])
    out = (
        "  - Epic epic-01-real.md:12 contains unresolved issue reference token: "
        "'- [ ] #[EpicID] - [Epic Title](../epics/epic-XX-name.md)'"
    )
    blocked = blocked_specs_from_linter_output(out, ws, RULES)
    assert blocked == {"epic-01-real.md"}, (
        f"a placeholder filename quoted inside a finding was treated as a real "
        f"specification: {blocked}"
    )


def test_clean_output_blocks_nothing(tmp_path):
    ws = _workspace(tmp_path, features=["feat-01-geo.md"])
    assert blocked_specs_from_linter_output("Success: all checks passed.", ws, RULES) == set()
    assert blocked_specs_from_linter_output("", ws, RULES) == set()


def test_every_backlog_directory_is_considered(tmp_path):
    """A rejected Use Case must be skippable too, not only a Feature."""
    ws = str(tmp_path)
    for rel, name in (("docs/epics", "epic-01-a.md"),
                      ("docs/features", "feat-01-b.md"),
                      ("docs/user-stories", "us-01-c.md"),
                      ("docs/use-cases", "uc-01-d.md")):
        d = tmp_path / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("# spec\n")

    out = "epic-01-a.md bad; feat-01-b.md bad; us-01-c.md bad; uc-01-d.md bad"
    assert blocked_specs_from_linter_output(out, ws, RULES) == {
        "epic-01-a.md", "feat-01-b.md", "us-01-c.md", "uc-01-d.md"
    }
