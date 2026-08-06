"""Regression tests for issues #319 and #329 — the residual matching defects on the
fallback path.

#314/#316 (package N2) made the frontmatter `issue_id` the primary selector and demoted
normalized-title matching to a warning-only fallback. These two issues are what is still
wrong *on that fallback*, which is why they are sequenced after it: they govern the path
a spec takes when it has no canonical id yet, plus the separate alias map that resolves
cross-references between items.

* **#319 — `epic_alias_map` collision.** The map is built from the epics directory but
  aggressively strips type prefixes, so `epic-07-geo-location.md` also registers the
  type-erased alias `geo location`. Any reference normalising to that string then
  resolves to the Epic — including `feat-07-geo-location`, a *Feature*. A User Story
  whose `epic:` frontmatter names a Feature was therefore silently adopted by an
  unrelated Epic and written into that Epic's checklist. The invariant #319 states is
  namespace isolation by entity type: a reference that declares itself a Feature, User
  Story or Use Case is not an Epic reference and the alias map must not answer it.

  This is also where the map could contradict #314/#316. `resolve_spec_issue_number` is
  now the sole authority on a spec file's *own* identity; the alias map exists only to
  resolve one item's reference *to another*. Letting a type-erased alias claim a
  Feature's slug lets the map assert an identity the resolver never granted.

* **#329 — label equality is exact.** `story_label in labels` compares against exactly
  `"user-story"`, so an issue filed with `"User Story"` lowercases to `"user story"`,
  misses, and is bucketed nowhere. The spec that should have matched it resolves to
  nothing and the issue is orphaned. #313 (package N3) introduced `issue_has_label` with
  deliberately exact matching and recorded case-insensitivity as belonging to this issue;
  both comparison sites are normalised here so the module has one rule, not two.

The tracker is stubbed throughout. `.pipeline/upstream/pipeline-tooling.md` §
*Validation Gates* forbids network egress in a blocking gate, so nothing here shells out
to `gh`.
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


class _TrackerStub:
    """Stands in for subprocess.run; records commands and captures synced bodies."""

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


def _backlog_tree(tmpdir):
    for sub in ("epics", "features", "user-stories", "use-cases"):
        os.makedirs(os.path.join(tmpdir, sub), exist_ok=True)


def _spec(directory, name, title, issue_id=None, epic=None, body=""):
    lines = ["---", f'title: "{title}"']
    if issue_id is not None:
        lines.append(f"issue_id: {issue_id}")
    if epic is not None:
        lines.append(f'epic: "{epic}"')
    lines += ["---", f"# {title}", "", "## Description", body or title, ""]
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


EPIC_SKELETON = (
    "---\n"
    'title: "Epic 07: Geo Location"\n'
    "issue_id: 701\n"
    "---\n"
    "# Epic 07: Geo Location\n"
    "\n"
    "## 2. Requirements & Checklist\n"
    "- *To be populated*\n"
    "\n"
    "### Associated Use Cases & User Stories\n"
    "\n"
    "#### Associated Use Cases\n"
    "- *To be populated*\n"
    "\n"
    "#### Associated User Stories\n"
    "- *To be populated*\n"
)


# --------------------------------------------------------------------------- #
# #319 — the Epic/Feature collision, end to end through main().
# --------------------------------------------------------------------------- #


COLLIDING_TREE_ISSUES = [
    {"number": 701, "title": "Epic 07: Geo Location", "labels": ["epic"], "state": "OPEN"},
    {"number": 702, "title": "Feature 07: Geo Location", "labels": ["feature"], "state": "OPEN"},
    {"number": 703, "title": "Operator Views Position", "labels": ["user-story"], "state": "OPEN"},
]


def _run_colliding_tree(monkeypatch, tmpdir):
    """An Epic and a Feature whose slugs share the suffix `geo-location`.

    The User Story points its `epic:` frontmatter at the *Feature* — the mistake #319
    describes. Both files normalise to `geo location`, so the type-erased alias the Epic
    registered answers for the Feature.
    """
    monkeypatch.setattr(
        "reconcile_backlog.get_all_issues", lambda rules: copy.deepcopy(COLLIDING_TREE_ISSUES)
    )
    tracker = _TrackerStub()
    monkeypatch.setattr(subprocess, "run", tracker)

    _backlog_tree(tmpdir)
    epic_path = os.path.join(tmpdir, "epics", "epic-07-geo-location.md")
    with open(epic_path, "w", encoding="utf-8") as fh:
        fh.write(EPIC_SKELETON)
    _spec(
        os.path.join(tmpdir, "features"), "feat-07-geo-location.md",
        "Feature 07: Geo Location", 702, epic="epic-07-geo-location",
    )
    _spec(
        os.path.join(tmpdir, "user-stories"), "us-07-operator-views-position.md",
        "Operator Views Position", 703, epic="feat-07-geo-location",
    )

    # Fixture guard: every assertion below reads a file main() discovered by listing
    # these directories. A run that discovered nothing would satisfy them vacuously.
    discovered = [
        os.path.join(sub, f)
        for sub in ("epics", "features", "user-stories", "use-cases")
        for f in os.listdir(os.path.join(tmpdir, sub))
        if f.endswith(".md")
    ]
    assert len(discovered) == 3, f"fixture guard: expected 3 specs, found {discovered}"

    monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])
    main()

    with open(epic_path, "r", encoding="utf-8") as fh:
        return tracker, fh.read()


def test_feature_typed_reference_does_not_resolve_to_an_epic_issue319(monkeypatch):
    """The reproduction. A User Story naming a *Feature* must not join an Epic.

    Before the fix `resolve_epic_norm("feat-07-geo-location")` normalised to
    `geo location`, hit the Epic's type-erased alias and returned the Epic's canonical
    title, so `us-07` was written into Epic 07's checklist as if it were a child.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _, epic_content = _run_colliding_tree(monkeypatch, tmpdir)

    assert "## 2. Requirements & Checklist" in epic_content, (
        "guard: the epic skeleton lost its checklist section entirely"
    )
    assert "us-07-operator-views-position.md" not in epic_content, (
        "the User Story declares a Feature as its parent, not an Epic. The alias map "
        "resolved it to Epic 07 through the type-erased alias 'geo location' (#319). "
        f"Epic file was:\n{epic_content}"
    )


def test_epic_typed_reference_still_resolves_issue319(monkeypatch):
    """The fix must segregate namespaces, not disable the map.

    The Feature names its Epic correctly and must still be linked; a fix that simply
    stopped consulting the alias map would pass the test above and break this one.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _, epic_content = _run_colliding_tree(monkeypatch, tmpdir)

    assert "feat-07-geo-location.md" in epic_content, (
        "the Feature declares epic: epic-07-geo-location and must remain a child of "
        f"Epic 07. Epic file was:\n{epic_content}"
    )


def test_colliding_tree_never_closes_an_issue_issue319(monkeypatch):
    """#309 must hold. `.pipeline/constitution.md` reserves `Closed` for the Product
    Owner, and `AGENTS.md` § *Backlog Reconciliation Mandate* runs this script before
    every merge."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker, _ = _run_colliding_tree(monkeypatch, tmpdir)

    assert tracker.commands, "guard: the stub captured no tracker commands at all"
    for line in tracker.flat():
        assert "issue close" not in line, f"reconciler issued a close: {line}"
        assert "--state closed" not in line.lower(), f"reconciler closed an issue: {line}"


# --------------------------------------------------------------------------- #
# #319 — the alias map's contract, unit level.
# --------------------------------------------------------------------------- #


def _write_epic(directory, name, title):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"---\ntitle: \"{title}\"\n---\n\n# {title}\n")
    return path


def test_reference_spec_type_is_detected_only_on_a_boundary_issue319():
    """A type prefix is only a type prefix when a separator or digit follows it.

    `us` inside "User Access Control" is not a User Story marker. Requiring the boundary
    is what keeps namespace segregation from eating ordinary titles.
    """
    spec_type_of = reconcile_backlog.spec_type_of_reference
    assert spec_type_of("epic-07-geo-location") == "epic"
    assert spec_type_of("Epic 07: Geo Location") == "epic"
    assert spec_type_of("feat-07-geo-location") == "feature"
    assert spec_type_of("Feature 07: Geo Location") == "feature"
    assert spec_type_of("us-07-operator") == "user-story"
    assert spec_type_of("uc-04-device-state") == "use-case"
    assert spec_type_of("Use Case 01: Tracker") == "use-case"
    assert spec_type_of("User Access Control") is None
    assert spec_type_of("Geo Location") is None
    assert spec_type_of("#101") is None
    assert spec_type_of("") is None
    assert spec_type_of(None) is None


def test_alias_map_is_not_consulted_for_a_non_epic_reference_issue319():
    """The collision itself, isolated from main()."""
    rules = _rules()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_epic(tmpdir, "epic-07-geo-location.md", "Epic 07: Geo Location")
        assert os.listdir(tmpdir), "fixture guard: no epic file was written"
        alias_map = reconcile_backlog.build_epic_alias_map(tmpdir, rules)

    assert alias_map, "fixture guard: the alias map came back empty"
    assert "geo location" in alias_map, (
        "the type-erased alias is what makes an Epic findable by its bare title; the "
        "fix must gate its use, not delete it"
    )

    resolve = reconcile_backlog.resolve_epic_reference
    assert resolve("epic-07-geo-location", alias_map, {}, rules) == "geo location"
    assert resolve("Geo Location", alias_map, {}, rules) == "geo location"
    assert resolve("feat-07-geo-location", alias_map, {}, rules) is None, (
        "a Feature-typed reference is not an Epic reference (#319)"
    )
    assert resolve("us-07-operator", alias_map, {}, rules) is None
    assert resolve("uc-07-operator", alias_map, {}, rules) is None


def test_non_epic_reference_is_reported_not_silently_dropped_issue319(capsys):
    """Refusing to resolve must be visible: a silently missing parent link reads exactly
    like a spec with no parent at all."""
    rules = _rules()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_epic(tmpdir, "epic-07-geo-location.md", "Epic 07: Geo Location")
        alias_map = reconcile_backlog.build_epic_alias_map(tmpdir, rules)
    reconcile_backlog.resolve_epic_reference("feat-07-geo-location", alias_map, {}, rules)
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "feat-07-geo-location" in out, f"the warning must name the reference; got {out!r}"


def test_ambiguous_alias_claimed_by_two_epics_is_dropped_issue319():
    """Last-writer-wins on a shared alias resolves by `os.listdir` order.

    Two Epics whose stripped slugs both reduce to `geo` are a genuine collision *inside*
    the map. Answering it at all picks a winner by directory-iteration order, which is
    not a resolution rule.
    """
    rules = _rules()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_epic(tmpdir, "epic-01-geo.md", "Epic 01: Geo Location Framework")
        _write_epic(tmpdir, "epic-02-geo.md", "Epic 02: Geo Tracking")
        assert len(os.listdir(tmpdir)) == 2, "fixture guard: expected two epic files"
        alias_map = reconcile_backlog.build_epic_alias_map(tmpdir, rules)

    assert alias_map, "fixture guard: the alias map came back empty"
    assert "geo" not in alias_map, (
        "'geo' is claimed by two different Epics; keeping it makes resolution depend on "
        f"directory order. Map was {alias_map!r}"
    )
    # The unambiguous aliases must survive.
    assert alias_map.get("geo location framework") == "geo location framework"
    assert alias_map.get("geo tracking") == "geo tracking"


# --------------------------------------------------------------------------- #
# #329 — label matching must be case- and separator-insensitive.
# --------------------------------------------------------------------------- #


def test_normalize_label_folds_case_and_separators_issue329():
    normalize_label = reconcile_backlog.normalize_label
    assert normalize_label("User Story") == "user-story"
    assert normalize_label("user story") == "user-story"
    assert normalize_label("USER-STORY") == "user-story"
    assert normalize_label("user_story") == "user-story"
    assert normalize_label("  Use Case  ") == "use-case"
    assert normalize_label("Epic") == "epic"
    # A namespaced label must survive intact — the colon is not a separator here.
    assert normalize_label("status:fixed-resolved") == "status:fixed-resolved"
    assert normalize_label("") == ""
    assert normalize_label(None) == ""


def test_issue_has_label_matches_across_case_variants_issue329():
    """#313 left this exact and named #329 as its owner. One comparison rule, not two."""
    record = {"labels": [{"name": "User Story"}]}
    assert reconcile_backlog.issue_has_label(record, "user-story"), (
        "an issue labelled 'User Story' already carries the user-story label"
    )
    assert reconcile_backlog.issue_has_label({"labels": ["use case"]}, "use-case")
    assert not reconcile_backlog.issue_has_label(record, "feature")
    assert not reconcile_backlog.issue_has_label(record, "")
    assert not reconcile_backlog.issue_has_label(None, "user-story")


def test_already_resolved_matches_across_case_variants_issue329():
    """The resolved-label guard is the same comparison and must fold identically, or a
    second run re-posts the completion comment #309 moved off `Closed`."""
    rules = _rules()
    record = {"labels": [{"name": "Status:Fixed-Resolved"}]}
    assert reconcile_backlog.is_already_resolved(record, rules)


def test_relabelling_an_issue_that_already_has_the_label_is_a_no_op_issue329():
    """Idempotency must survive case drift too: the reconciler runs before every merge."""
    rules = _rules()
    calls = []

    class _Recorder:
        def __call__(self, cmd, *args, **kwargs):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(list(cmd), 0, stdout="", stderr="")

    original = subprocess.run
    subprocess.run = _Recorder()
    try:
        applied = reconcile_backlog.apply_structural_label(
            903, "User Story", rules=rules,
            issue_record={"labels": [{"name": "User Story"}]},
        )
    finally:
        subprocess.run = original

    assert applied is False, "the issue already carries the label in a different casing"
    assert not calls, f"no tracker traffic should have been issued; got {calls}"


ORPHANED_LABEL_ISSUES = [
    # Filed by hand (or by a hallucinating generator) with a spaced, title-cased label.
    {"number": 903, "title": "Operator Views Live Position", "labels": ["User Story"], "state": "OPEN"},
]


def test_unnormalized_label_issue_is_found_on_the_title_fallback_issue329(monkeypatch):
    """The reproduction. The spec has no `issue_id` yet, so it takes the title fallback
    #314 demoted — and that fallback reads a bucket the label check never filled."""
    monkeypatch.setattr(
        "reconcile_backlog.get_all_issues", lambda rules: copy.deepcopy(ORPHANED_LABEL_ISSUES)
    )
    tracker = _TrackerStub()
    monkeypatch.setattr(subprocess, "run", tracker)

    with tempfile.TemporaryDirectory() as tmpdir:
        _backlog_tree(tmpdir)
        _spec(
            os.path.join(tmpdir, "user-stories"), "us-03-operator.md",
            "Operator Views Live Position", body="MARKER-ORPHAN",
        )
        discovered = [
            f for f in os.listdir(os.path.join(tmpdir, "user-stories")) if f.endswith(".md")
        ]
        assert discovered == ["us-03-operator.md"], f"fixture guard: found {discovered}"

        monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])
        main()

    assert "903" in tracker.bodies, (
        "issue 903 is labelled 'User Story', which the exact-match check never bucketed, "
        "so the spec resolved to nothing and the issue stayed orphaned (#329). "
        f"Commands were {tracker.flat()}"
    )
    assert "MARKER-ORPHAN" in tracker.bodies["903"]


def test_unnormalized_label_run_never_closes_an_issue_issue329(monkeypatch):
    """#309 again: making more issues reachable must not make any of them closeable."""
    monkeypatch.setattr(
        "reconcile_backlog.get_all_issues", lambda rules: copy.deepcopy(ORPHANED_LABEL_ISSUES)
    )
    tracker = _TrackerStub()
    monkeypatch.setattr(subprocess, "run", tracker)

    with tempfile.TemporaryDirectory() as tmpdir:
        _backlog_tree(tmpdir)
        _spec(
            os.path.join(tmpdir, "user-stories"), "us-03-operator.md",
            "Operator Views Live Position",
        )
        monkeypatch.setattr(sys, "argv", ["reconcile_backlog.py", tmpdir])
        main()

    assert tracker.commands, "guard: the stub captured no tracker commands at all"
    for line in tracker.flat():
        assert "issue close" not in line, f"reconciler issued a close: {line}"
        assert "--state closed" not in line.lower(), f"reconciler closed an issue: {line}"


def test_reconciler_has_no_second_label_comparison_rule_issue329():
    """Structural. Two label comparison rules in one module is how #329 survived #313."""
    source_path = os.path.join(SCRIPT_DIR, "reconcile_backlog.py")
    with open(source_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    assert source, "fixture guard: reconcile_backlog.py read as empty"
    assert "def normalize_label(" in source, "the shared comparison rule is missing"
    # The definition plus every comparison site.
    assert source.count("normalize_label(") >= 5, (
        "every label comparison must route through normalize_label; found "
        f"{source.count('normalize_label(')} uses"
    )
