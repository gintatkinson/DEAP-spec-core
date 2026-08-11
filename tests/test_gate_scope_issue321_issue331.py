"""Regression tests for issues #321 and #331 — validation gate scope.

These are one defect seen from opposite sides.

#331 says the gate is too permissive: `create_issue.sh` invoked the linter with
`--allow-missing-specs`, so incomplete coverage never blocked a filing.

#321 says it is too strict: `reconcile_backlog.py` requires a global pass over the
whole `docs/` tree, so one incomplete work-in-progress draft blocks synchronisation of
every finished, unrelated one.

Both follow from the gate's scope being the entire tree when it should be the item
under work. Fixing either alone makes the other worse, so they are fixed together on
two different axes:

* `--only <path>` narrows *what is reported* for a single-item invocation. Whole-corpus
  invariants still run — uniqueness and cross-references cannot be checked per file —
  but only findings naming the target are reported. That makes strictness affordable,
  which is what lets #331's permissive flag go.
* The reconciler stops aborting wholesale. It skips the items that fail, syncs the rest,
  and still exits non-zero, so nothing invalid publishes and finished work is no longer
  held hostage to an unrelated draft.
"""

import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINTER = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "verify_model_coverage.py"
)
RECONCILER = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "reconcile_backlog.py"
)
CREATE_ISSUE = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "create_issue.sh"
)


def _source(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_the_scripts_under_test_exist():
    """Guard: every assertion below reads one of these."""
    for path in (LINTER, RECONCILER, CREATE_ISSUE):
        assert os.path.isfile(path), f"{path} missing; the suite would prove nothing"


def test_linter_accepts_an_only_scope_argument_issue331():
    """A single-item invocation must be able to say which item it is filing."""
    result = subprocess.run(
        [sys.executable, LINTER, "--help"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert "--only" in result.stdout, (
        "the linter has no --only flag, so create_issue.sh cannot scope the gate to "
        f"the file it is filing and must stay permissive globally. Help was:\n{result.stdout}"
    )


def test_only_scope_suppresses_findings_about_other_files_issue321(tmp_path):
    """Scoping to one item must stop reporting a different item's problems.

    Asserted as suppression rather than "a clean file now passes": the corpus-wide
    padding-consistency finding names every file in the directory, so no specification
    is unmentioned and a clean-file probe cannot be built from this corpus.
    """
    unscoped = subprocess.run(
        [sys.executable, LINTER, "--spec-only"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=180,
    )
    target, other = "feat-13-zero-codegen-grid.md", "feat-28-traceability-gate.md"
    cwd_dir = REPO_ROOT
    if unscoped.returncode == 0:
        import json
        rules_path = os.path.abspath(os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json"))
        with open(rules_path, "r", encoding="utf-8") as f:
            rdata = json.load(f)
        os.makedirs(tmp_path / ".pipeline" / "logical-ui", exist_ok=True)
        os.makedirs(tmp_path / "docs" / "features", exist_ok=True)
        with open(tmp_path / ".pipeline" / "logical-ui" / "codebase_rules.json", "w", encoding="utf-8") as f:
            json.dump(rdata, f)

        target, other = "feat-01-first.md", "feat-02-second.md"
        with open(tmp_path / "docs" / "features" / target, "w", encoding="utf-8") as f:
            f.write("# Feature 1\n```mermaid\nclass A {\n  +bad: invalid\n}\n```\n")
        with open(tmp_path / "docs" / "features" / other, "w", encoding="utf-8") as f:
            f.write("# Feature 2\n```mermaid\nclass B {\n  +bad: invalid\n}\n```\n")

        cwd_dir = str(tmp_path)
        unscoped = subprocess.run(
            [sys.executable, LINTER, "--spec-only"],
            capture_output=True, text=True, cwd=cwd_dir, timeout=180,
        )

    assert unscoped.returncode != 0, (
        "the live corpus is expected to fail the unscoped gate; if it now passes this "
        "test can no longer distinguish scoping from a clean tree"
    )

    before = unscoped.stdout.count(other)
    assert before >= 1, (
        f"{other} is expected to appear in unscoped output; found {before}"
    )

    scoped = subprocess.run(
        [sys.executable, LINTER, "--spec-only", "--only", target],
        capture_output=True, text=True, cwd=cwd_dir, timeout=180,
    )
    after = scoped.stdout.count(other)
    assert after < before, (
        f"scoping to {target} did not suppress findings about {other} "
        f"({before} mentions before, {after} after), so an unrelated draft still "
        f"blocks this item (#321)"
    )
    assert scoped.stdout.count(target) > 0, (
        "scoping suppressed the target's own findings, which would make the gate "
        "vacuous rather than scoped"
    )


def test_create_issue_scopes_the_gate_to_the_file_it_files_issue331():
    """With scoping available, the permissive flag is no longer needed."""
    text = _source(CREATE_ISSUE)
    assert "--only" in text, (
        "create_issue.sh does not scope the gate to the item being filed, so it must "
        "either stay permissive (#331) or block on unrelated drafts (#321)"
    )
    invocation = [ln for ln in text.splitlines()
                  if "$LINTER" in ln and not ln.strip().startswith("#")]
    assert invocation, "no linter invocation found in create_issue.sh"
    assert not any("--allow-missing-specs" in ln for ln in invocation), (
        "create_issue.sh still passes the permissive flag. With --only scoping the "
        f"gate to the filed item, strictness is affordable (#331). Lines: {invocation}"
    )


def test_reconciler_does_not_abort_the_whole_sync_on_one_bad_draft_issue321():
    """The reconciler must skip what fails and publish what does not."""
    text = _source(RECONCILER)
    assert "Aborting backlog reconciliation" not in text, (
        "the reconciler still aborts the entire run when the linter fails, so one "
        "incomplete draft blocks synchronisation of every finished specification (#321)"
    )
    assert "blocked_specs" in text, (
        "the reconciler has no notion of a per-item skip set, so it cannot sync the "
        "valid items while withholding the invalid ones"
    )


def test_reconciler_still_reports_failure_when_items_were_skipped_issue321():
    """Skipping must not become silent tolerance — the run must still fail."""
    text = _source(RECONCILER)
    assert re.search(r"blocked_specs[\s\S]{0,2000}?sys\.exit\(1\)", text), (
        "the reconciler skips invalid specifications but never exits non-zero, so a "
        "broken corpus would report success and the gate would be gone"
    )
