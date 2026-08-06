"""Regression tests for issue #284.

``rules/github-source-of-truth.md`` and ``rules/tracker-source-of-truth.md`` were
forked copies of one mandate, structurally identical and subsequently edited
independently. The divergence was not hypothetical: the GitHub-named file carried
the ``issue_id: <int>`` frontmatter mandate and a cross-reference section that the
tracker-named file lacked entirely.

That mandate is load-bearing. ``spec-usecase-engineering/SKILL.md`` resolves
Realization Matrix links by reading the ``issue_id:`` frontmatter field, so an agent
operating from the shorter rule had no instruction to emit the field those lookups
depend on.

Resolution: keep the provider-neutral file, migrate the unique clauses into it, and
delete the duplicate.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DELETED = os.path.join(REPO_ROOT, "rules", "github-source-of-truth.md")
SURVIVOR = os.path.join(REPO_ROOT, "rules", "tracker-source-of-truth.md")

# Historical records are not rewritten - see AGENTS.md:59 and the reasoning in #296.
EXCLUDED_DIRS = {".git", "decisions", "designs", "__pycache__", "node_modules"}

# Files that legitimately name the deleted file because they document the deletion.
# Anything outside this set naming it is a dangling reference.
ALLOWED_MENTIONS = {
    "implementation_plan.md",                      # records the planned deletion
    "rules/tracker-source-of-truth.md",            # records what it superseded
    os.path.join("tests", "test_rules_consolidation_issue284.py"),  # this file
}


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_survivor_exists():
    """Guard: without this, the assertions below could pass against a missing file."""
    assert os.path.isfile(SURVIVOR), f"surviving rule file not found: {SURVIVOR}"


def test_duplicate_rule_file_is_deleted_issue284():
    assert not os.path.exists(DELETED), (
        "rules/github-source-of-truth.md must be deleted. Two near-identical "
        "statements of one mandate drift apart, which is how the issue_id clause "
        "came to exist in only one of them."
    )


def test_issue_id_mandate_survived_the_merge_issue284():
    content = _read(SURVIVOR)
    assert "issue_id" in content, (
        "the issue_id frontmatter mandate existed only in the deleted file and MUST "
        "be migrated. spec-usecase-engineering resolves Realization Matrix links by "
        "reading that field, so losing the mandate breaks those lookups."
    )
    assert re.search(r"issue_id.*<?int>?", content), (
        "the migrated clause should state the type, e.g. 'issue_id: <int>'"
    )


def test_cross_reference_section_survived_the_merge_issue284():
    content = _read(SURVIVOR)
    assert re.search(r"^##\s+Relationship to other rules", content, re.M), (
        "the 'Relationship to other rules' section existed only in the deleted file "
        "and must be migrated"
    )
    for target in ("platform-independence.md", "constitution.md"):
        assert target in content, f"cross-reference to {target} lost in the merge"


def test_authoritative_done_state_clause_survived_issue284():
    content = _read(SURVIVOR)
    assert re.search(r'authoritative.*done', content, re.I | re.S), (
        "the clause stating that the authoritative 'done' state lives in the tracker "
        "rather than in local frontmatter existed only in the deleted file"
    )


def test_no_live_document_references_the_deleted_file_issue284():
    """Historical records under docs/decisions/ and docs/designs/ are excluded, since
    they describe the repository's past state and are not rewritten."""
    offenders = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            if not name.endswith((".md", ".py", ".sh", ".json", ".yml", ".yaml")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, REPO_ROOT)
            if rel in ALLOWED_MENTIONS:
                continue
            try:
                content = _read(path)
            except (OSError, UnicodeDecodeError):
                continue
            if "github-source-of-truth" in content:
                offenders.append(rel)
    assert not offenders, (
        f"live documents still reference the deleted rule file: {offenders}"
    )
