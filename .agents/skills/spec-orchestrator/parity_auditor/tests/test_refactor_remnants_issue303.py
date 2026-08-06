"""Regression tests for issue #303 - three F841 refactor remnants baselined in #293.

Finding 1 (cli.py `has_parseable_schemas` / `has_alternative_schemas`): vestigial.
The probe loop that computed them has no consumer; the equivalent guard is the
`all_definitions` check later in the same function. Covered structurally, because a
behavioural test cannot drive the removal of code that has no observable effect.

Finding 2 (sync_validator.py `spec_type`): a lost consumer. The epic/feature
distinction is computed from the issue labels but never stored, so `tracker_specs`
and `local_specs` are keyed on the normalised title alone. Two defects follow, and
both are driven by tests here.
"""

import json
import os
import re
import subprocess
import sys

import pytest

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PACKAGE_ROOT, "src"))

from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402
from parity_auditor.validators.sync_validator import SyncValidator  # noqa: E402

CLI_PATH = os.path.join(PACKAGE_ROOT, "src", "parity_auditor", "cli.py")
PYPROJECT_PATH = os.path.join(PACKAGE_ROOT, "pyproject.toml")


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_spec(directory, filename, title):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("---\ntitle: \"%s\"\n---\n\n# %s\n" % (title, title))
    return path


def _make_workspace(tmp_path, monkeypatch, issues):
    """Build an offline workspace whose tracker command replays `issues` as JSON."""
    workspace = str(tmp_path / "ws")
    epics_dir = os.path.join(workspace, "docs", "epics")
    features_dir = os.path.join(workspace, "docs", "features")
    os.makedirs(epics_dir)
    os.makedirs(features_dir)

    rules = {
        "backlog_directories": {"epics": "docs/epics", "features": "docs/features"},
        "tracker_rules": {
            "labels": {"epic": "epic", "feature": "feature"},
            # Offline stub: echoes the issue payload back on stdout. No network, no `gh`.
            "commands": {
                "list_issues": [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write(sys.argv[1])",
                    json.dumps(issues),
                ]
            },
        },
    }
    rules_path = os.path.join(workspace, "codebase_rules.json")
    with open(rules_path, "w", encoding="utf-8") as handle:
        json.dump(rules, handle)
    monkeypatch.setenv("CODEBASE_RULES_PATH", rules_path)
    return workspace, epics_dir, features_dir


def _issue(number, title, label):
    return {"number": number, "title": title, "labels": [{"name": label}]}


@pytest.fixture(autouse=True)
def _tracker_stub_is_runnable():
    """Fixture guard: the offline tracker stub must actually produce output."""
    probe = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write(sys.argv[1])", "[]"],
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0 and probe.stdout == "[]", (
        "offline tracker stub did not run; the sync tests would pass vacuously"
    )


# --- Finding 2: the epic/feature distinction must be stored ------------------


def test_sync_validator_reports_missing_epic_when_only_a_feature_file_matches_issue303(
    tmp_path, monkeypatch
):
    """An epic-labelled issue is not satisfied by a same-titled feature spec file."""
    issues = [_issue(4001, "Epic 1: Payments", "epic")]
    workspace, epics_dir, features_dir = _make_workspace(tmp_path, monkeypatch, issues)

    feature_file = _write_spec(features_dir, "feature-1-payments.md", "Feature 1: Payments")
    assert os.path.exists(feature_file)
    assert os.listdir(epics_dir) == [], "the epics directory must be empty for this probe"

    errors = SyncValidator().validate(WorkspaceRepository(workspace))

    assert any("#4001" in err for err in errors), (
        "epic issue #4001 has no epic specification file, but the feature file "
        "'Feature 1: Payments' satisfied it because the epic/feature distinction "
        "(spec_type) is discarded. Errors were: %r" % (errors,)
    )


def test_sync_validator_does_not_let_a_feature_issue_mask_an_epic_issue_issue303(
    tmp_path, monkeypatch
):
    """Two issues normalising to the same title must both be checked, not collapsed."""
    issues = [
        _issue(4001, "Epic 1: Payments", "epic"),
        _issue(4002, "Feature 1: Payments", "feature"),
    ]
    workspace, epics_dir, features_dir = _make_workspace(tmp_path, monkeypatch, issues)

    epic_file = _write_spec(epics_dir, "epic-1-payments.md", "Epic 1: Payments")
    assert os.path.exists(epic_file)
    assert os.listdir(features_dir) == [], "the features directory must be empty here"

    errors = SyncValidator().validate(WorkspaceRepository(workspace))

    assert any("#4002" in err for err in errors), (
        "feature issue #4002 has no feature specification file, but it shares a "
        "normalised title with epic issue #4001 and was overwritten in tracker_specs. "
        "Errors were: %r" % (errors,)
    )
    assert not any("#4001" in err for err in errors), (
        "epic issue #4001 has its epic file and must not be reported: %r" % (errors,)
    )


def test_sync_validator_stays_silent_when_both_spec_types_are_present_issue303(
    tmp_path, monkeypatch
):
    """Positive control: type-aware matching must not invent errors."""
    issues = [
        _issue(4001, "Epic 1: Payments", "epic"),
        _issue(4002, "Feature 1: Payments", "feature"),
    ]
    workspace, epics_dir, features_dir = _make_workspace(tmp_path, monkeypatch, issues)

    _write_spec(epics_dir, "epic-1-payments.md", "Epic 1: Payments")
    _write_spec(features_dir, "feature-1-payments.md", "Feature 1: Payments")
    assert os.listdir(epics_dir) and os.listdir(features_dir)

    errors = SyncValidator().validate(WorkspaceRepository(workspace))

    assert errors == [], "no issue is missing its specification file: %r" % (errors,)


def test_sync_validator_still_detects_index_collisions_issue303(tmp_path, monkeypatch):
    """Regression guard: the index-collision check survives the type-aware keys."""
    issues = [_issue(4003, "Feature 2: Payments", "feature")]
    workspace, _epics_dir, features_dir = _make_workspace(tmp_path, monkeypatch, issues)

    _write_spec(features_dir, "feature-2-refunds.md", "Feature 2: Refunds")
    assert os.listdir(features_dir)

    errors = SyncValidator().validate(WorkspaceRepository(workspace))

    assert any("Index collision" in err and "#4003" in err for err in errors), (
        "local feature index 2 ('refunds') collides with registered issue #4003 "
        "('payments') and must still be reported by number: %r" % (errors,)
    )


# --- Finding 1: the dead schema-probe loop must be gone ---------------------


def test_cli_has_no_dead_schema_probe_flags_issue303():
    """The superseded probe loop and both flags it computed are removed."""
    source = _read(CLI_PATH)
    assert source.strip(), "cli.py is empty; this check would pass vacuously"
    for name in ("has_parseable_schemas", "has_alternative_schemas"):
        assert name not in source, (
            "%s is a refactor remnant superseded by the all_definitions guard "
            "and must not reappear in cli.py" % name
        )


# --- All three: the ruff baseline must be lifted ----------------------------


def test_pyproject_no_longer_baselines_f841_issue303():
    """The per-file-ignores entries that suppressed the three findings are gone."""
    source = _read(PYPROJECT_PATH)
    match = re.search(
        r"^\[tool\.ruff\.lint\.per-file-ignores\]\s*$(.*?)(?=^\[|\Z)",
        source,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "per-file-ignores section not found in pyproject.toml"
    section = match.group(1)
    assert section.strip(), "per-file-ignores section is empty; check would be vacuous"

    active = [
        line
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert active, "per-file-ignores has no active entries; check would be vacuous"
    offenders = [line for line in active if "F841" in line]
    assert not offenders, (
        "issue #303 resolves the three F841 remnants, so their baseline entries "
        "must be deleted: %r" % (offenders,)
    )
