"""Regression tests for issue #323 — install-time tracker label provisioning.

Labels were created just-in-time, at the moment the first issue of a given type was
filed. They arrived eventually, but a freshly installed downstream repository showed an
empty "Filter by labels" dropdown until an orchestrator run had filed one issue of every
type — and a partial run left only `user-story` showing, which reads as a broken
installation rather than an incomplete one.

The taxonomy is known at install time, so discovering it lazily buys nothing.

The just-in-time path in `create_issue.sh` is deliberately kept. It is idempotent and
remains the fallback for a repository provisioned before this script existed, or one
where a label was deleted by hand. Removing it would trade a cosmetic defect for a
functional one, so a test asserts it survives.
"""

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOOTSTRAP = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "bootstrap_tracker_labels.py"
)
CREATE_ISSUE = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "create_issue.sh"
)
README = os.path.join(REPO_ROOT, "README.md")
RULES = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json")


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_the_bootstrap_script_exists_and_is_executable_issue323():
    """Guard, and #282: an executable in a scripts dir needs a shebang."""
    assert os.path.isfile(BOOTSTRAP), f"{BOOTSTRAP} missing"
    assert os.access(BOOTSTRAP, os.X_OK), "bootstrap script is not executable"
    with open(BOOTSTRAP, "rb") as fh:
        assert fh.read(2) == b"#!", "executable script lacks a shebang (#282)"


def test_bootstrap_provisions_every_configured_label_issue323():
    """The whole taxonomy, in one invocation, before any issue is filed."""
    result = subprocess.run(
        [sys.executable, BOOTSTRAP, "--dry-run"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert result.returncode == 0, f"dry run failed: {result.stderr}"

    with open(RULES, "r", encoding="utf-8") as fh:
        configured = json.load(fh)["tracker_rules"]["labels"]
    assert configured, "guard: no labels configured, so this test would be vacuous"

    for name in configured.values():
        assert f"gh label create {name}" in result.stdout, (
            f"label {name!r} is configured but the bootstrap does not provision it. "
            f"Output was:\n{result.stdout}"
        )


def test_label_names_come_from_configuration_not_constants_issue323():
    """A downstream project that renames its taxonomy must get its own names."""
    source = _read(BOOTSTRAP)
    assert "tracker_rules" in source and "labels" in source, (
        "the bootstrap does not read tracker_rules.labels, so a renamed taxonomy "
        "would be provisioned under this repository's names"
    )
    # The four structural names must not be baked into the command construction.
    assert 'create", "epic"' not in source and "create', 'epic'" not in source, (
        "a label name is hardcoded into the gh invocation"
    )


def test_creation_is_idempotent_issue323():
    """It runs at install time and again whenever a tracker needs repairing."""
    result = subprocess.run(
        [sys.executable, BOOTSTRAP, "--dry-run"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if "gh label create" in ln]
    assert lines, "guard: no creation commands emitted"
    for line in lines:
        assert "--force" in line, (
            f"label creation is not idempotent, so a second run errors on every "
            f"existing label: {line}"
        )


def test_install_instructions_run_the_bootstrap_issue323():
    """A script nobody runs fixes nothing."""
    readme = _read(README)
    assert "bootstrap_tracker_labels.py" in readme, (
        "the Direct Copy Installation block does not run the bootstrap, so a fresh "
        "downstream repository still starts with an empty label filter"
    )
    # It must come after the copy step that puts the script on disk.
    assert readme.index("cp -RP ./.tmp-pipeline/skills") < readme.rindex(
        "bootstrap_tracker_labels.py"
    ), "the bootstrap is invoked before the script has been copied into place"


def test_the_just_in_time_fallback_survives_issue323():
    """Keeping it is the point: install-time provisioning is not a replacement."""
    text = _read(CREATE_ISSUE)
    assert "gh label create" in text, (
        "the just-in-time label creation in create_issue.sh was removed. It is the "
        "fallback for repositories provisioned before the bootstrap existed, and for "
        "labels deleted by hand; removing it trades a cosmetic defect for a functional "
        "one."
    )
