"""Regression tests for issues #315 and #313 — `sync_issue_body_to_tracker` sends an
incomplete update.

Both defects are the same call site omitting part of the payload:

* **#315 — title desync.** The `edit_issue` template is
  `gh issue edit {number} --body-file {temp_path}`. It never carries `--title`, so a
  tracker issue keeps whatever generic title it was created with (e.g.
  "Feature: Geo Location") while the YAML frontmatter `title` evolves. The two drift
  apart permanently, and every title-normalized fallback match downstream inherits the
  drift.
* **#313 — structural labels never applied.** `.pipeline/constitution.md:93-95`
  § *Labeling Taxonomy* mandates exactly four label types — `epic`, `feature`,
  `user-story`, `use-case` — "or as defined by the issue tracker configuration", and
  requires that "Labels are bootstrapped via the configured label bootstrap command to
  ensure idempotency". The reconciler bootstrapped that way for `status:fixed-resolved`
  only (#309) and applied no structural label at all, so a downstream tracker carries no
  architectural tier on any generated issue.

What the fix must guarantee, and what each test below pins:

* the frontmatter title reaches the tracker;
* it is sent only when it actually differs from the tracker's current title, because the
  reconciler runs before every merge per `AGENTS.md` § *Backlog Reconciliation Mandate*
  and an unconditional edit would churn the tracker on every run;
* each item type gets its configured structural label — Epic, Feature, User Story and
  Use Case alike;
* label names are read from `tracker_rules.labels`, never hardcoded;
* the label is bootstrapped through the configured `create_label` command *before* it is
  applied, since applying a label a fresh downstream repository does not have fails;
* re-applying a label the issue already carries issues no tracker call at all;
* #309 survives: no run here may close an issue.

The tracker is stubbed throughout. `.pipeline/upstream/pipeline-tooling.md` §
*Validation Gates* forbids network egress in a blocking gate, so no test here may shell
out to `gh`.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
RULES_PATH = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json")

import reconcile_backlog  # noqa: E402
from reconcile_backlog import main  # noqa: E402


def _rules():
    with open(RULES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _spec(directory, name, title, issue_id):
    lines = [
        "---",
        f'title: "{title}"',
        f"issue_id: {issue_id}",
        "---",
        f"# {title}",
        "",
        "## Description",
        title,
        "",
    ]
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


class _TrackerStub:
    """Stands in for subprocess.run; records every command issued."""

    def __init__(self):
        self.commands = []

    def __call__(self, cmd, *args, **kwargs):
        cmd = list(cmd)
        self.commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def flat(self):
        return [" ".join(str(p) for p in c) for c in self.commands]

    def edits_for(self, number):
        """Every recorded command that targets `number` on the tracker."""
        return [c for c in self.commands if str(number) in [str(p) for p in c]]


# Four issues, one per structural tier, each carrying the generic creation title #315
# describes and — per #313 — no structural label at all.
TIERED_ISSUES = [
    {"number": 801, "title": "Epic: Generic Placeholder", "labels": [], "state": "OPEN"},
    {"number": 802, "title": "Feature: Geo Location", "labels": [], "state": "OPEN"},
    {"number": 803, "title": "User Story: Generic Placeholder", "labels": [], "state": "OPEN"},
    {"number": 804, "title": "Use Case: Generic Placeholder", "labels": [], "state": "OPEN"},
]

# The refined frontmatter titles the specs actually carry.
TIERED_SPECS = [
    ("epics", "epic-01-location-awareness.md", "Location Awareness Platform", 801),
    ("features", "feat-01-geo-location.md", "Geo Location Capture And Refinement", 802),
    ("user-stories", "us-01-operator-views-position.md", "Operator Views Live Position", 803),
    ("use-cases", "uc-01-operator-requests-position.md", "Operator Requests A Position Fix", 804),
]

EXPECTED_LABEL_BY_NUMBER = {
    "801": "epic",
    "802": "feature",
    "803": "user-story",
    "804": "use-case",
}


def _run_reconcile(monkeypatch, tmpdir, issues, specs):
    """Reconcile `specs` against a stubbed tracker holding `issues`."""
    monkeypatch.setattr(
        "reconcile_backlog.get_all_issues", lambda rules: copy.deepcopy(issues)
    )
    tracker = _TrackerStub()
    monkeypatch.setattr(subprocess, "run", tracker)

    for sub in ("epics", "features", "user-stories", "use-cases"):
        os.makedirs(os.path.join(tmpdir, sub), exist_ok=True)
    for sub, name, title, issue_id in specs:
        _spec(os.path.join(tmpdir, sub), name, title, issue_id)

    # Fixture guard: main() discovers spec files by listing each directory. A run that
    # discovered nothing would satisfy every assertion below vacuously.
    discovered = [
        os.path.join(sub, f)
        for sub in ("epics", "features", "user-stories", "use-cases")
        for f in os.listdir(os.path.join(tmpdir, sub))
        if f.endswith(".md")
    ]
    assert len(discovered) == len(specs), (
        f"fixture guard: expected {len(specs)} specs on disk, found {discovered}"
    )

    monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])
    main()

    assert tracker.commands, "guard: the stub captured no tracker commands at all"
    return tracker


# --------------------------------------------------------------------------- #
# #315 — the frontmatter title must reach the tracker.
# --------------------------------------------------------------------------- #


def test_frontmatter_title_is_pushed_to_the_tracker_issue315(monkeypatch):
    """Every tier's refined title must be sent; before the fix none of them were."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, TIERED_ISSUES, TIERED_SPECS)

    for (_, _, title, number) in TIERED_SPECS:
        titled = [
            c for c in tracker.edits_for(number)
            if "--title" in c and c[c.index("--title") + 1] == title
        ]
        assert titled, (
            f"no title update carrying {title!r} was issued for issue {number}; "
            f"commands were {tracker.flat()}"
        )


def test_title_is_not_resent_when_it_already_matches_issue315(monkeypatch):
    """An unchanged title must produce no title edit.

    The reconciler runs before every merge (`AGENTS.md` § *Backlog Reconciliation
    Mandate*), so an unconditional `--title` would rewrite the same value on every run.
    """
    issues = [
        {"number": 802, "title": "Geo Location Capture And Refinement", "labels": [], "state": "OPEN"},
    ]
    specs = [("features", "feat-01-geo-location.md", "Geo Location Capture And Refinement", 802)]
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, issues, specs)

    assert not [c for c in tracker.commands if "--title" in c], (
        "the tracker title already equals the frontmatter title, so no title edit "
        f"should have been issued; commands were {tracker.flat()}"
    )


# --------------------------------------------------------------------------- #
# #313 — structural labels.
# --------------------------------------------------------------------------- #


def test_structural_label_is_applied_per_item_type_issue313(monkeypatch):
    """Epic, Feature, User Story and Use Case each receive their configured label."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, TIERED_ISSUES, TIERED_SPECS)

    for number, label in EXPECTED_LABEL_BY_NUMBER.items():
        applied = [
            c for c in tracker.edits_for(number)
            if "--add-label" in c and c[c.index("--add-label") + 1] == label
        ]
        assert applied, (
            f"issue {number} never received its structural label {label!r}; "
            f"commands were {tracker.flat()}"
        )


def test_structural_label_is_bootstrapped_before_it_is_applied_issue313(monkeypatch):
    """A fresh downstream repository has no such label, and applying one that does not
    exist fails. #309 already added `create_label` with `--force` for exactly this; the
    structural labels must reuse it rather than invent a second mechanism."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, TIERED_ISSUES, TIERED_SPECS)

    flat = tracker.flat()
    for number, label in EXPECTED_LABEL_BY_NUMBER.items():
        create_at = [
            i for i, c in enumerate(tracker.commands)
            if "label" in [str(p) for p in c] and "create" in [str(p) for p in c] and label in [str(p) for p in c]
        ]
        assert create_at, (
            f"label {label!r} was never bootstrapped before use; commands were {flat}"
        )
        assert any("--force" in tracker.commands[i] for i in create_at), (
            f"the {label!r} bootstrap must be idempotent (--force); commands were {flat}"
        )
        apply_at = [
            i for i, c in enumerate(tracker.commands)
            if "--add-label" in c
            and c[c.index("--add-label") + 1] == label
            and str(number) in [str(p) for p in c]
        ]
        assert apply_at, f"label {label!r} was never applied to issue {number}"
        assert min(create_at) < min(apply_at), (
            f"label {label!r} was applied before it was bootstrapped; commands were {flat}"
        )


def test_reapplying_a_label_the_issue_already_has_is_a_no_op_issue313(monkeypatch):
    """Idempotency. The reconciler runs before every merge, so a second run over an
    already-labelled issue must issue no label traffic at all."""
    issues = [
        {"number": 802, "title": "Feature: Geo Location", "labels": [{"name": "feature"}], "state": "OPEN"},
    ]
    specs = [("features", "feat-01-geo-location.md", "Geo Location Capture And Refinement", 802)]
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, issues, specs)

    assert not [c for c in tracker.commands if "--add-label" in c], (
        f"issue 802 already carries 'feature'; no label edit was needed: {tracker.flat()}"
    )
    assert not [
        c for c in tracker.commands
        if "label" in [str(p) for p in c] and "create" in [str(p) for p in c]
    ], f"no bootstrap was needed either: {tracker.flat()}"


def test_label_names_come_from_configuration_not_hardcoded_issue313():
    """`tracker_rules.labels` is the single source of the taxonomy.

    The constitution permits a tracker to define its own names ("or as defined by the
    issue tracker configuration"), so a renamed label must flow through untouched.
    """
    rules = _rules()
    rules["tracker_rules"]["labels"] = {
        "epic": "tier:epic",
        "feature": "tier:feature",
        "user_story": "tier:user-story",
        "use_case": "tier:use-case",
        "resolved": "status:fixed-resolved",
    }
    resolved = {
        item_type: reconcile_backlog.get_structural_label(item_type, rules)
        for item_type in ("Epic", "Feature", "User Story", "Use Case")
    }
    assert resolved == {
        "Epic": "tier:epic",
        "Feature": "tier:feature",
        "User Story": "tier:user-story",
        "Use Case": "tier:use-case",
    }, f"configured label names were not honoured: {resolved}"


def test_structural_label_map_matches_the_shipped_configuration_issue313():
    """The four constitutional tiers must all be resolvable from the shipped rules."""
    rules = _rules()
    configured = rules["tracker_rules"]["labels"]
    assert configured, "fixture guard: tracker_rules.labels is empty in codebase_rules.json"
    assert reconcile_backlog.get_structural_label("Epic", rules) == configured["epic"]
    assert reconcile_backlog.get_structural_label("Feature", rules) == configured["feature"]
    assert reconcile_backlog.get_structural_label("User Story", rules) == configured["user_story"]
    assert reconcile_backlog.get_structural_label("Use Case", rules) == configured["use_case"]


# --------------------------------------------------------------------------- #
# #309 — the reconciler still never closes an issue.
# --------------------------------------------------------------------------- #


def test_title_and_label_sync_never_closes_an_issue_issue315(monkeypatch):
    """`.pipeline/constitution.md` makes `Closed` unreachable without Product Owner
    validation. Adding traffic to this call site must not smuggle a close in."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_reconcile(monkeypatch, tmpdir, TIERED_ISSUES, TIERED_SPECS)

    for line in tracker.flat():
        assert "issue close" not in line, f"reconciler issued a close: {line}"
        assert "--state closed" not in line.lower(), f"reconciler closed an issue: {line}"
