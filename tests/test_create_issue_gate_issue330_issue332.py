"""Regression tests for issues #330 and #332 — `create_issue.sh` gate integrity.

#330: when the linter was absent from the computed path the script printed a warning
and filed the issue anyway. A gate that disappears when its checker is missing is not
a gate — the one circumstance in which it must hold is the one in which it yielded.

#332: no idempotency guard. Re-running filed a duplicate issue, and the label
precondition used `grep -Fq`, a substring match, so `feature` was considered already
present when only `feature-request` existed.

Isolation note. The script is always copied into a temp scripts directory and a *stub*
linter is placed beside it, so these tests never depend on the state of the live
`docs/` corpus. That corpus currently fails the real linter, which on a first draft of
this file made the duplicate-title test fail at the gate and prove nothing about
duplicate detection at all. `gh` is stubbed on PATH, so nothing here reaches the
network — `.pipeline/upstream/pipeline-tooling.md` § *Validation Gates* forbids egress
in a blocking gate, and a test that shelled out to the real tracker would be one.
"""

import os
import stat
import subprocess

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts", "create_issue.sh")


def _write_exec(path, body):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def harness(tmp_path):
    """Sandbox: a copy of the script, a stub `gh`, a body file, and a command log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    log = tmp_path / "commands.log"

    script_copy = scripts / "create_issue.sh"
    with open(SCRIPT, "rb") as src:
        script_copy.write_bytes(src.read())
    os.chmod(str(script_copy), 0o755)

    _write_exec(
        str(bin_dir / "gh"),
        "#!/bin/bash\n"
        f'echo "gh $*" >> "{log}"\n'
        'if [ "$1" = "issue" ] && [ "$2" = "list" ]; then\n'
        f'  cat "{tmp_path}/existing_issues.txt" 2>/dev/null || true\n'
        "fi\n"
        'if [ "$1" = "label" ] && [ "$2" = "list" ]; then\n'
        f'  cat "{tmp_path}/existing_labels.txt" 2>/dev/null || true\n'
        "fi\n"
        "exit 0\n",
    )

    body = tmp_path / "feat-01-geo-location.md"
    body.write_text("# Feature: Geo Location\n")

    (tmp_path / "existing_issues.txt").write_text("")
    (tmp_path / "existing_labels.txt").write_text("")

    return {
        "tmp": tmp_path,
        "scripts": scripts,
        "script": script_copy,
        "log": log,
        "body": body,
        "env": {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
    }


def _add_passing_linter(harness):
    """A stub linter that exits 0, so the gate is satisfied and out of the way."""
    _write_exec(
        str(harness["scripts"] / "verify_model_coverage.py"),
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
    )


def _run(harness, title="Feature: Geo Location", label="feature"):
    return subprocess.run(
        [str(harness["script"]), str(harness["body"]), label, title],
        capture_output=True, text=True, env=harness["env"], cwd=str(harness["tmp"]),
        timeout=120,
    )


def _log(harness):
    if not harness["log"].exists():
        return []
    return [ln for ln in harness["log"].read_text().splitlines() if ln.strip()]


def test_the_script_under_test_is_executable_with_a_shebang_issue330():
    """Guard: every assertion below execs a copy of this file."""
    assert os.path.isfile(SCRIPT), f"{SCRIPT} is missing; the suite would prove nothing"
    assert os.access(SCRIPT, os.X_OK), "create_issue.sh is not executable"
    with open(SCRIPT, "rb") as fh:
        assert fh.read(2) == b"#!", "executable script lacks a shebang (#282)"


def test_missing_linter_fails_closed_issue330(harness):
    """A gate whose checker is absent must refuse, not wave the issue through."""
    assert not (harness["scripts"] / "verify_model_coverage.py").exists()

    result = _run(harness)

    assert result.returncode != 0, (
        "create_issue.sh filed an issue with no linter present; the gate must fail "
        f"closed. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    creates = [ln for ln in _log(harness) if ln.startswith("gh issue create")]
    assert not creates, f"an issue was filed despite the gate being absent: {creates}"


def test_present_linter_still_allows_filing_issue330(harness):
    """Positive control: failing closed must not mean failing always."""
    _add_passing_linter(harness)

    result = _run(harness)

    assert result.returncode == 0, (
        f"a passing linter must still permit filing: {result.stdout!r} {result.stderr!r}"
    )
    creates = [ln for ln in _log(harness) if ln.startswith("gh issue create")]
    assert creates, f"no issue was filed on the success path: {_log(harness)}"


def test_duplicate_title_is_not_filed_twice_issue332(harness):
    """Re-running must not manufacture a second issue for the same title."""
    _add_passing_linter(harness)
    (harness["tmp"] / "existing_issues.txt").write_text(
        "42\tFeature: Geo Location\tfeature\tOPEN\n"
    )

    result = _run(harness)

    creates = [ln for ln in _log(harness) if ln.startswith("gh issue create")]
    assert not creates, (
        "an issue titled 'Feature: Geo Location' already exists on the tracker, but "
        f"create_issue.sh filed another. Commands: {_log(harness)}"
    )
    assert result.returncode == 0, (
        "recognising an existing issue is the success path, not an error: "
        f"{result.stdout!r} {result.stderr!r}"
    )


def test_label_precondition_is_not_a_substring_match_issue332(harness):
    """`grep -Fq feature` matched `feature-request`, so the real label was never made."""
    _add_passing_linter(harness)
    (harness["tmp"] / "existing_labels.txt").write_text(
        "feature-request\tSomething else\tededed\n"
    )

    _run(harness, label="feature")

    created = [ln for ln in _log(harness) if ln.startswith("gh label create")]
    assert created, (
        "only 'feature-request' exists on the tracker, so label 'feature' had to be "
        f"created. A substring match saw it as already present. Commands: {_log(harness)}"
    )
