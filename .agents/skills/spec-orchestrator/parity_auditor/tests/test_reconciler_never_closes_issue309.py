"""Regression tests for issue #309.

`reconcile_backlog.py` closed Epics, User Stories and Use Cases automatically, while
`.pipeline/constitution.md:161` makes `Closed` unreachable without Product Owner
validation. `.agents/AGENTS.md` requires the reconciler run before every merge, so the
violation was mandated to execute rather than merely possible. #306 corrected the skill
documents; this is the enforced-side twin.

The idempotency test below is the one that matters. Closing was doing load-bearing work:
the call sites are guarded by `is_open`, so once an item was closed the next run skipped
it. Removing the close without replacing that guard would re-post the completion comment
on every reconcile, before every merge, forever — trading a constitutional violation for
a spam loop. The guard therefore keys on the resolved label, which `list_issues` already
returns.
"""

import json
import os
import sys

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
RULES_PATH = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json")

import reconcile_backlog
from reconcile_backlog import (
    resolve_issue_on_tracker,
    is_already_resolved,
    get_resolved_label,
)


def _rules():
    with open(RULES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


class _CapturedRun:
    """Stands in for subprocess.run and records every command issued."""

    def __init__(self):
        self.commands = []

    def __call__(self, cmd, **kwargs):
        self.commands.append(list(cmd))

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    def flat(self):
        return [" ".join(c) for c in self.commands]


def test_config_declares_no_close_command_issue309():
    """A close template left in config is a loaded gun for the next contributor."""
    commands = _rules()["tracker_rules"]["commands"]
    assert "close_issue" not in commands, (
        "tracker_rules.commands.close_issue must be removed, not merely unused"
    )
    for required in ("resolve_issue", "comment_issue", "create_label"):
        assert required in commands, f"tracker_rules.commands.{required} is missing"
    assert _rules()["tracker_rules"]["labels"]["resolved"] == "status:fixed-resolved"


def test_resolve_never_emits_a_close_issue309(monkeypatch):
    captured = _CapturedRun()
    monkeypatch.setattr(reconcile_backlog.subprocess, "run", captured)

    resolve_issue_on_tracker(42, "verified: 115 passed", rules=_rules())

    assert captured.commands, "guard: the stub captured no commands at all"
    for line in captured.flat():
        assert "issue close" not in line, f"reconciler issued a close: {line}"


def test_resolve_applies_label_and_comment_issue309(monkeypatch):
    captured = _CapturedRun()
    monkeypatch.setattr(reconcile_backlog.subprocess, "run", captured)

    resolve_issue_on_tracker(42, "verified: 115 passed", rules=_rules())

    assert any(
        "--add-label" in c and "status:fixed-resolved" in c for c in captured.commands
    ), f"no label application found in {captured.flat()}"
    assert any(
        "comment" in c and any("verified: 115 passed" in part for part in c)
        for c in captured.commands
    ), f"no evidence comment found in {captured.flat()}"


def test_label_is_bootstrapped_before_it_is_applied_issue309(monkeypatch):
    """A downstream repository has no status:fixed-resolved label until one is created."""
    captured = _CapturedRun()
    monkeypatch.setattr(reconcile_backlog.subprocess, "run", captured)

    resolve_issue_on_tracker(42, "done", rules=_rules())

    create_at = next(
        (i for i, c in enumerate(captured.commands) if "label" in c and "create" in c),
        None,
    )
    apply_at = next(
        (i for i, c in enumerate(captured.commands) if "--add-label" in c), None
    )
    assert create_at is not None, f"label was never bootstrapped: {captured.flat()}"
    assert apply_at is not None, f"label was never applied: {captured.flat()}"
    assert create_at < apply_at, "label must be created before it is applied"


def test_already_resolved_issue_is_skipped_issue309():
    """The guard that replaces closing. Without it, every run re-comments forever."""
    rules = _rules()
    label = get_resolved_label(rules)

    resolved = {"labels": [{"name": "bug"}, {"name": label}]}
    unresolved = {"labels": [{"name": "bug"}]}

    assert is_already_resolved(resolved, rules) is True
    assert is_already_resolved(unresolved, rules) is False
    assert is_already_resolved({}, rules) is False


def test_already_resolved_accepts_plain_string_labels_issue309():
    """Some tracker payloads return labels as strings rather than objects."""
    rules = _rules()
    label = get_resolved_label(rules)
    assert is_already_resolved({"labels": [label]}, rules) is True
    assert is_already_resolved({"labels": ["bug"]}, rules) is False
