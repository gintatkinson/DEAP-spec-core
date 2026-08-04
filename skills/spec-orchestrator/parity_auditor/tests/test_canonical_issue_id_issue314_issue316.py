"""Regression tests for issues #314 and #316 — canonical `issue_id` must be the
primary selector when resolving a local spec file to its tracker issue.

`.pipeline/constitution.md:57-59` § *Unique Backlog Identifiers*:

    - All local specification files MUST include a permanent unique identifier
      (`issue_id: <int>`) in their YAML frontmatter, mapped directly to their remote
      issue number.
    - Matching by title normalization is prohibited as a primary selector.

`reconcile_backlog.py` did the opposite. It built four lookup dictionaries keyed on
normalized issue titles (#314) and consulted them *before* the frontmatter `issue_id`
(#316), reaching the canonical identifier only when the title lookup missed. A
dictionary keyed on a title keeps whichever issue the tracker listed last, so two
specifications sharing a title both resolved to the same issue number and
`sync_issue_body_to_tracker` overwrote one body with the other's — the corruption #316
reports, raising no error while doing it.

The two issues are one defect: #316 is the precedence half of #314's lookup.

What the fix must guarantee, and what each test below pins:

* frontmatter `issue_id` wins outright when the issue exists — no title lookup consulted;
* title normalization survives only for a spec that has no `issue_id` yet, and emits a
  visible warning naming the file when it is used, because the constitution prohibits it
  as a *primary* selector;
* an `issue_id` naming an issue absent from the tracker is a hard error, never a silent
  fall-through to title matching — falling through is precisely how #316 corrupts bodies;
* two spec files may never resolve to one issue number; that fails loudly with both paths.

The resolver is reached as `reconcile_backlog.resolve_spec_issue_number` rather than
imported by name, so that during the RED phase the end-to-end reproduction below fails
on the behaviour it is written for instead of on a collection-time ImportError.

The tracker is stubbed throughout. `.pipeline/upstream/pipeline-tooling.md` §
*Validation Gates* forbids network egress in a blocking gate, so no test here may shell
out to `gh`.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

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


def _issue_dict(issues):
    """Mirror the dual int/str keying main() builds, so lookups match production."""
    out = {}
    for issue in issues:
        num = issue["number"]
        out[num] = issue
        out[str(num)] = issue
    return out


def _spec(directory, name, title, issue_id=None, marker=""):
    lines = ["---", f'title: "{title}"']
    if issue_id is not None:
        lines.append(f"issue_id: {issue_id}")
    lines += ["---", f"# {title}", "", "## Description", marker or title, ""]
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def _backlog_tree(tmpdir):
    for sub in ("epics", "features", "user-stories", "use-cases"):
        os.makedirs(os.path.join(tmpdir, sub))
    return os.path.join(tmpdir, "features")


class _TrackerStub:
    """Stands in for subprocess.run; records commands and captures synced bodies.

    `sync_issue_body_to_tracker` writes the body to a temp file and deletes it in a
    `finally`, so the body has to be read while the call is in flight.
    """

    def __init__(self):
        self.commands = []
        self.bodies = {}

    def __call__(self, cmd, *args, **kwargs):
        cmd = list(cmd)
        self.commands.append(cmd)
        if cmd[:3] == ["gh", "issue", "edit"] and "--body-file" in cmd:
            body_path = cmd[cmd.index("--body-file") + 1]
            with open(body_path, "r", encoding="utf-8") as fh:
                self.bodies[str(cmd[3])] = fh.read()
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def flat(self):
        return [" ".join(str(p) for p in c) for c in self.commands]


COLLIDING_ISSUES = [
    {"number": 902, "title": "Feature 01: Geo Location", "labels": ["feature"], "state": "OPEN"},
    {"number": 903, "title": "Feature 02: Geo Location", "labels": ["feature"], "state": "OPEN"},
]


# --------------------------------------------------------------------------- #
# #316 — the overwrite reproduction, end to end through main().
# --------------------------------------------------------------------------- #


def _run_colliding_titles(monkeypatch, tmpdir):
    """Two Features, one title, two `issue_id`s, reconciled against a stub tracker."""
    monkeypatch.setattr("reconcile_backlog.get_all_issues", lambda rules: COLLIDING_ISSUES)
    tracker = _TrackerStub()
    monkeypatch.setattr(subprocess, "run", tracker)

    features_dir = _backlog_tree(tmpdir)
    _spec(features_dir, "feat-01-geo-location.md", "Geo Location", 902, "MARKER-ALPHA")
    _spec(features_dir, "feat-02-geo-location.md", "Geo Location", 903, "MARKER-BETA")

    # Fixture guard: main() discovers spec files by listing the directory. A run that
    # discovered nothing would satisfy the assertions downstream vacuously.
    discovered = [f for f in os.listdir(features_dir) if f.endswith(".md")]
    assert len(discovered) == 2, f"fixture guard: expected 2 specs, found {discovered}"

    monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])
    main()
    return tracker


def test_identical_titles_sync_to_their_own_issues_issue316(monkeypatch):
    """Each body must reach its own issue.

    Before the fix both files resolved through `feature_titles["geo location"]`, which
    holds whichever issue the tracker listed last, so one body overwrote the other and
    the second issue was never touched at all.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_colliding_titles(monkeypatch, tmpdir)

    assert set(tracker.bodies) == {"902", "903"}, (
        "each spec must sync to its own issue; got edits for "
        f"{sorted(tracker.bodies)} in {tracker.flat()}"
    )
    assert "MARKER-ALPHA" in tracker.bodies["902"]
    assert "MARKER-BETA" not in tracker.bodies["902"]
    assert "MARKER-BETA" in tracker.bodies["903"]
    assert "MARKER-ALPHA" not in tracker.bodies["903"]


def test_identical_titles_run_never_closes_an_issue_issue316(monkeypatch):
    """#309's guarantee must survive the precedence change: no close, ever."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = _run_colliding_titles(monkeypatch, tmpdir)

    assert tracker.commands, "guard: the stub captured no tracker commands at all"
    for line in tracker.flat():
        assert "issue close" not in line, f"reconciler issued a close: {line}"


# --------------------------------------------------------------------------- #
# #314 / #316 — the resolver's contract, unit level.
# --------------------------------------------------------------------------- #


def test_frontmatter_issue_id_outranks_the_title_map_issue316():
    """The precedence inversion itself. A matching title must not be consulted."""
    issue_dict = _issue_dict(
        [
            {"number": 901, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"},
            {"number": 999, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"},
        ]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _spec(tmpdir, "feat-01.md", "Geo Location", 901)
        resolved = reconcile_backlog.resolve_spec_issue_number(
            path, "Geo Location", {"geo location": 999}, issue_dict,
            rules=_rules(), item_type="Feature",
        )
    assert str(resolved) == "901", f"title map won over canonical issue_id: got {resolved}"


def test_string_issue_id_resolves_against_the_tracker_issue314():
    """Frontmatter may quote the id; YAML then yields a str. It is still canonical."""
    issue_dict = _issue_dict(
        [{"number": 901, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"}]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _spec(tmpdir, "feat-01.md", "Geo Location", '"901"')
        resolved = reconcile_backlog.resolve_spec_issue_number(
            path, "Geo Location", {"geo location": 999}, issue_dict,
            rules=_rules(), item_type="Feature",
        )
    assert str(resolved) == "901"


def test_missing_issue_id_falls_back_to_title_and_warns_issue314(capsys):
    """First registration has no id yet. The fallback survives — but must announce itself."""
    issue_dict = _issue_dict(
        [{"number": 907, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"}]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _spec(tmpdir, "feat-07-geo.md", "Geo Location")
        resolved = reconcile_backlog.resolve_spec_issue_number(
            path, "Geo Location", {"geo location": 907}, issue_dict,
            rules=_rules(), item_type="Feature",
        )
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert str(resolved) == "907"
    assert "feat-07-geo.md" in out, f"the warning must name the file; got: {out!r}"
    assert "issue_id" in out and "title" in out.lower(), (
        f"the warning must say why title matching is a last resort; got: {out!r}"
    )


def test_stale_issue_id_is_fatal_not_a_title_fallback_issue314():
    """An `issue_id` the tracker does not have is a hard error.

    Falling through to the title map here would reintroduce #316 exactly: the title
    below matches a *different* issue, and syncing to it overwrites an unrelated body.
    """
    issue_dict = _issue_dict(
        [{"number": 907, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"}]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _spec(tmpdir, "feat-09-geo.md", "Geo Location", 555)
        with pytest.raises(SystemExit) as excinfo:
            reconcile_backlog.resolve_spec_issue_number(
                path, "Geo Location", {"geo location": 907}, issue_dict,
                rules=_rules(), item_type="Feature",
            )
    assert excinfo.value.code != 0


def test_two_specs_may_not_claim_one_issue_issue316(capsys):
    """The backstop. Whatever the route, one issue belongs to exactly one file."""
    issue_dict = _issue_dict(
        [{"number": 901, "title": "Geo Location", "labels": ["feature"], "state": "OPEN"}]
    )
    claimed = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        first = _spec(tmpdir, "feat-01-geo.md", "Geo Location", 901)
        second = _spec(tmpdir, "feat-02-geo.md", "Geo Location", 901)
        reconcile_backlog.resolve_spec_issue_number(
            first, "Geo Location", {}, issue_dict, rules=_rules(),
            item_type="Feature", claimed=claimed,
        )
        with pytest.raises(SystemExit) as excinfo:
            reconcile_backlog.resolve_spec_issue_number(
                second, "Geo Location", {}, issue_dict, rules=_rules(),
                item_type="Feature", claimed=claimed,
            )
        captured = capsys.readouterr()
        out = captured.out + captured.err
        assert "feat-01-geo.md" in out and "feat-02-geo.md" in out, (
            f"both conflicting paths must be named; got: {out!r}"
        )
    assert excinfo.value.code != 0


def test_unresolvable_spec_returns_none_issue314():
    """No id and no title match: still a warning-and-skip at the call site, not a crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _spec(tmpdir, "feat-11-orphan.md", "Nothing Matches This")
        assert reconcile_backlog.resolve_spec_issue_number(
            path, "Nothing Matches This", {}, _issue_dict([]),
            rules=_rules(), item_type="Feature",
        ) is None


def test_resolver_is_wired_into_every_spec_type_issue314():
    """Epics, Features, User Stories and Use Cases all resolve through one path.

    Four near-identical copies of the resolution block is how #316 came to be reported
    against one of them; this pins that they share the resolver instead.
    """
    source_path = os.path.join(SCRIPT_DIR, "reconcile_backlog.py")
    with open(source_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    assert source, "fixture guard: reconcile_backlog.py read as empty"
    assert source.count("resolve_spec_issue_number(") >= 5, (
        "expected the resolver definition plus four call sites, found "
        f"{source.count('resolve_spec_issue_number(')}"
    )
    for item_type in ("Epic", "Feature", "User Story", "Use Case"):
        assert f'item_type="{item_type}"' in source, f"{item_type} does not use the resolver"
