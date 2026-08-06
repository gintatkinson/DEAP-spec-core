"""Regression tests for issue #283.

``schema-specification-engineering/SKILL.md`` documented the linter's rejection
threshold as ``len(schema_containers) != 2`` while ``SchemaCardinalityValidator``
accepts only exactly one entry. A subagent following the instruction literally
emitted two containers and was rejected by the very gate the sentence described.

The cause was a truncated blockquote: the sentence ended at ``!=`` and absorbed the
ordinal of the following list item, so ``2. **Epic File Structure / Template:**``
was both swallowed into the note and read as the numeral completing the comparison.

These tests derive the accepted count from the validator **behaviourally** rather
than hardcoding 1, so if the enforced rule ever changes the documentation assertion
follows it instead of silently going stale.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402
from parity_auditor.validators.cardinality_validator import (  # noqa: E402
    SchemaCardinalityValidator,
)

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
SKILL = os.path.join(
    REPO_ROOT, "skills", "schema-specification-engineering", "SKILL.md"
)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _feature(n_containers):
    entries = "\n".join(
        f'  - path: "mod:root/child{i}"\n    node_type: container'
        for i in range(n_containers)
    )
    body = "---\ntitle: \"F\"\ntype: \"feature\"\n"
    body += f"schema_containers:\n{entries}\n" if n_containers else "schema_containers: []\n"
    body += "---\n\n# Feature: F\n"
    return body


def _accepted_counts(tmp_path, candidates=(0, 1, 2, 3)):
    """Behaviourally determine which container counts the validator accepts."""
    accepted = []
    for n in candidates:
        ws = tmp_path / f"ws{n}"
        (ws / "schema").mkdir(parents=True)
        (ws / "schema" / "model.yang").write_text("module m {}", encoding="utf-8")
        feats = ws / "docs" / "features"
        feats.mkdir(parents=True)
        (feats / "feat-01-x.md").write_text(_feature(n), encoding="utf-8")
        repo = WorkspaceRepository(workspace_dir=str(ws))
        if not SchemaCardinalityValidator().validate(repo):
            accepted.append(n)
    return accepted


# --------------------------------------------------------------------------- #
# Guard + behavioural baseline
# --------------------------------------------------------------------------- #

def test_skill_file_is_discoverable():
    assert os.path.isfile(SKILL), f"skill file not found: {SKILL}"


def test_validator_accepts_exactly_one_container(tmp_path):
    accepted = _accepted_counts(tmp_path)
    assert accepted == [1], (
        f"expected the validator to accept exactly one container, it accepted {accepted}. "
        "If this changed deliberately, the documented threshold must change with it."
    )


# --------------------------------------------------------------------------- #
# #283 - documentation must match the enforced threshold
#
# Both assertions in this file were disabled by commit 368a0e4: the one above was
# inverted from ``accepted == [1]`` to "accept multiple containers", contradicting this
# module's own docstring, the test's own name, both worker skills ("Multi-container
# Features are forbidden -- the linter gate will reject files with
# len(schema_containers) != 1") and the schema-container-consolidation-forbidden
# contract in tests/rule_contracts.py; and the one below was replaced with ``pass``.
#
# The validator had lost its len > 1 check, and the tests were bent to fit rather than
# the check restored. Restoring them is what makes the documented rule and the enforced
# rule the same rule again, which is the entire premise of #283.
# --------------------------------------------------------------------------- #

def test_documented_threshold_matches_enforced_threshold_issue283(tmp_path):
    accepted = _accepted_counts(tmp_path)
    assert len(accepted) == 1, "baseline broken, see the test above"
    enforced = accepted[0]

    content = _read(SKILL)
    stated = re.findall(r"len\(schema_containers\)\s*!=\s*(\d+)", content)
    assert stated, (
        "no 'len(schema_containers) != N' threshold found in the skill. The sentence "
        "was truncated at '!=' in the original defect, so absence is itself a failure."
    )
    bad = [s for s in stated if int(s) != enforced]
    assert not bad, (
        f"documentation states a rejection threshold of != {bad} but the validator "
        f"accepts exactly {enforced} container(s). A subagent following the docs would "
        f"be rejected by the gate the sentence purports to describe."
    )


def test_epic_template_heading_is_a_top_level_item_issue283():
    """The swallowed heading must be restored to the numbered list, not left inside
    the blockquote where it renders as part of a note."""
    lines = _read(SKILL).splitlines()
    hits = [
        l for l in lines
        if re.match(r"^\s*\d+\.\s+\*\*Epic File Structure\s*/\s*Template", l)
    ]
    assert hits, (
        "'Epic File Structure / Template' must appear as a top-level numbered list "
        "item. It was absorbed into the Container Traceability blockquote."
    )
    assert not any(h.lstrip().startswith(">") for h in hits), (
        f"the Epic template heading is still inside a blockquote: {hits}"
    )


def test_step4_numbered_list_has_no_duplicate_ordinals_issue283():
    content = _read(SKILL)
    step4 = re.search(r"^## Step 4.*?(?=^## Step 5)", content, re.S | re.M)
    assert step4, "Step 4 section not found"
    ordinals = [
        int(m.group(1))
        for m in re.finditer(r"^(\d+)\.\s+\*\*", step4.group(0), re.M)
    ]
    assert len(ordinals) >= 4, f"expected several top-level items, found {ordinals}"
    dupes = sorted({n for n in ordinals if ordinals.count(n) > 1})
    assert not dupes, (
        f"Step 4 numbered list repeats ordinals {dupes} (full sequence {ordinals}); "
        "an inserted item did not renumber its successors"
    )
    assert ordinals == sorted(ordinals), (
        f"Step 4 ordinals are not monotonic: {ordinals}"
    )
