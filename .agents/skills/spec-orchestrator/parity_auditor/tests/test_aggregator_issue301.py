"""Tests for the multi-downstream aggregator (issue #301).

The property that matters: the same pipeline defect in two differently-named workspaces
must collapse to one row, while a defect confined to one workspace must not be promoted.
Everything else the aggregator does is presentation.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.aggregator import collect, format_report  # noqa: E402

FENCE = "`" * 3

RULES = {
    "meta": {},
    "backlog_directories": {
        "features": "docs/features", "user_stories": "docs/user-stories",
        "use_cases": "docs/use-cases", "epics": "docs/epics", "schemas": "schema",
    },
    "target_directories": {}, "flutter_rules": {}, "python_rules": {},
    "spec_rules": {},
    # The UML model-integrity gate reports a missing requirement set rather than
    # treating it as "nothing required", so both keys must be present. They are
    # deliberately empty: these fixtures exist to exercise aggregation grouping, and
    # making them satisfy 52 model-integrity rules would bury what the tests assert.
    "validation_rules": {"required_sections": {"feature": []},
                         "required_diagrams": {"feature": []}},
}

# Minimal platform source and test suite, so that the workspace fixtures below are
# workspaces rather than bare documentation trees.
#
# Issue #304 wired the profile-scoping and test-completeness gates into
# AGGREGATING_VALIDATORS. Both then fired on every fixture here, and correctly: a tree
# with no Dart sources and no test files really does have an empty codebase and no test
# suite. That made three of these workspaces share two symptoms they were never meant to
# model, which promoted those symptoms to systemic and outranked the mermaid and filename
# rules the tests are actually about.
#
# The fixtures are corrected rather than the assertions relaxed. `report.systemic == []`
# and "the broadest symptom ranks first" are the properties under test; scoping them to
# an allow-list of rule ids would make them stop failing when a rule IS wrongly promoted,
# which is the only thing they exist to catch.
#
# The test body names one token from each assertion class required by
# rules/tdd-mandate.md section Required assertion classes, so the completeness gate is
# satisfied for the reason it exists rather than by suppression.
MINIMAL_DART_SOURCE = """/// Realises: [Feat-000/AppRoot]
/// AppRoot class definition.
class AppRoot {
  /// AppRoot constructor.
  const AppRoot();
}
"""

MINIMAL_DART_TEST = """void main() {
  test('parses identifiers', () {
    expect(RegExp(r'^[a-z]+$').hasMatch('abc'), isTrue);
    expect(1.005, closeTo(1.0, 0.01));
    expect(getComputedStyle(node).highlight, 'selected');
    expect(pane.width, greaterThanOrEqualTo(240));
    expect(() => parse(''), throwsA(isA<FormatException>()));
  });
}
"""

# The Logical UI bindings block every Feature must carry, bound to nothing. `N/A` is the
# documented spelling for a Feature with no layout binding, so this satisfies the gate
# rather than suppressing it.
# generation_mode records that the item was drafted by a context-isolated subagent. The
# UML validator requires it on every specification (issue #278).
FRONTMATTER = """---
generation_mode: "subagent"
---
"""

BINDINGS = """
## Logical UI & Layout Bindings
- **Target LUI Component:** N/A
- **Target Layout Container ID:** N/A
- **Data Source Binding:** N/A
"""

# The layout manifest every Feature's bindings resolve against. Present so that the
# workspaces below are workspaces; absent, the manifest gate fires in all of them and
# outranks the rules these tests are about.
LAYOUT_MANIFEST = {
    "id": "root", "type": "SplitContainer",
    "children": [{"id": "properties_view", "type": "PropertyGrid"}],
}

# The design token authority. It must exist and must yield at least one hex colour, or
# the codebase gate reports the workspace as unauditable — correctly, since with no token
# file the hardcoded-colour checks would be vacuous.
DESIGN_TOKENS = {"color": {"status": {"nominal": "#1B7F3B", "degraded": "#B26B00"}}}

# Violates mermaid-no-semicolon-in-note-or-message
SEMICOLON_DIAGRAM = f"""{FRONTMATTER}# Spec

{FENCE}mermaid
sequenceDiagram
    participant A as "a : A"
    Note over A: first thing; second thing
{FENCE}
{BINDINGS}"""

CLEAN_DIAGRAM = f"""{FRONTMATTER}# Spec

{FENCE}mermaid
sequenceDiagram
    participant A as "a : A"
    Note over A: first thing, second thing
{FENCE}
{BINDINGS}"""


def _workspace(tmp_path, name, feature_files):
    ws = tmp_path / name
    pipeline = ws / ".pipeline" / "logical-ui"
    pipeline.mkdir(parents=True)
    (pipeline / "codebase_rules.json").write_text(json.dumps(RULES), encoding="utf-8")
    (pipeline / "logical-layout.json").write_text(json.dumps(LAYOUT_MANIFEST), encoding="utf-8")
    (pipeline / "design-tokens.json").write_text(json.dumps(DESIGN_TOKENS), encoding="utf-8")
    feats = ws / "docs" / "features"
    feats.mkdir(parents=True)
    # Configured in RULES, so it must exist: an absent epics directory silently drops
    # Epic-defined classes from the cross-document class registry.
    (ws / "docs" / "epics").mkdir(parents=True)
    for fname, content in feature_files.items():
        # Issue #318 wired the title-uniqueness gate into AGGREGATING_VALIDATORS. Every
        # fixture here carried the same `# Spec` heading, so the H1 fallback gave all of
        # them one title and the gate fired in all four workspaces — correctly: four
        # same-titled Features in one directory really is the collision it reports. That
        # symptom outranked the mermaid and filename rules these tests are about.
        #
        # The fixtures are corrected rather than the assertions relaxed, for the same
        # reason recorded above for #304: "the broadest symptom ranks first" is the
        # property under test, and scoping it to an allow-list of rule ids would stop it
        # failing when a rule IS wrongly promoted. "Fixture" is deliberately not a spec
        # type word, so normalize_spec_title leaves the distinguishing stem intact.
        stem = os.path.splitext(fname)[0]
        titled = content.replace(
            'generation_mode: "subagent"',
            f'generation_mode: "subagent"\ntitle: "Fixture {stem}"',
            1,
        )
        (feats / fname).write_text(titled, encoding="utf-8")

    lib = ws / "app_flutter" / "lib"
    lib.mkdir(parents=True)
    (lib / "app_root.dart").write_text(MINIMAL_DART_SOURCE, encoding="utf-8")
    tests = ws / "app_flutter" / "test"
    tests.mkdir(parents=True)
    (tests / "app_root_test.dart").write_text(MINIMAL_DART_TEST, encoding="utf-8")
    return str(ws)


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

def test_empty_corpus_is_handled(tmp_path):
    report = collect([])
    assert report.corpus == []
    assert report.groups == []
    assert "No structured findings" in format_report(report)


def test_nonexistent_paths_are_skipped(tmp_path):
    report = collect([str(tmp_path / "does-not-exist")])
    assert report.corpus == []


def test_fixtures_actually_produce_findings(tmp_path):
    """Vacuity guard: if the fixtures were clean, every assertion below would pass
    trivially."""
    ws = _workspace(tmp_path, "probe", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    report = collect([ws])
    assert report.groups, "fixture produced no findings; the corpus proves nothing"


# --------------------------------------------------------------------------- #
# The core property: recurrence across differently-named workspaces
# --------------------------------------------------------------------------- #

def test_shared_symptom_collapses_across_workspaces(tmp_path):
    """Two projects with different names and different filenames, same rule violated."""
    a = _workspace(tmp_path, "downstream-alpha", {"feat-01-alpha-thing.md": SEMICOLON_DIAGRAM})
    b = _workspace(tmp_path, "downstream-beta", {"feat-42-beta-other.md": SEMICOLON_DIAGRAM})

    report = collect([a, b])
    semis = [g for g in report.groups if g.signature == "mermaid-no-semicolon-in-note-or-message"]
    assert len(semis) == 1, (
        f"the same rule in two workspaces must be ONE group, got {len(semis)}. If this "
        "splits, recurrence is invisible and the aggregator has no purpose."
    )
    assert semis[0].breadth == 2
    assert set(semis[0].workspaces) == {"downstream-alpha", "downstream-beta"}


def test_local_symptom_is_not_promoted(tmp_path):
    """A defect in one of three workspaces must not read as systemic."""
    a = _workspace(tmp_path, "ds-a", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    b = _workspace(tmp_path, "ds-b", {"feat-01-b.md": CLEAN_DIAGRAM})
    c = _workspace(tmp_path, "ds-c", {"feat-01-c.md": CLEAN_DIAGRAM})

    report = collect([a, b, c])
    assert report.systemic == [], (
        f"1 of 3 workspaces is not systemic, got {[g.signature for g in report.systemic]}"
    )


def test_widespread_symptom_is_flagged_systemic(tmp_path):
    a = _workspace(tmp_path, "ds-a", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    b = _workspace(tmp_path, "ds-b", {"feat-01-b.md": SEMICOLON_DIAGRAM})
    c = _workspace(tmp_path, "ds-c", {"feat-01-c.md": CLEAN_DIAGRAM})

    report = collect([a, b, c])
    sigs = [g.signature for g in report.systemic]
    assert "mermaid-no-semicolon-in-note-or-message" in sigs, (
        f"2 of 3 workspaces crosses the threshold, got {sigs}"
    )


def test_single_workspace_never_systemic(tmp_path):
    """Breadth of 1 proves nothing about the pipeline, even at 1/1."""
    a = _workspace(tmp_path, "only", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    assert collect([a]).systemic == []


# --------------------------------------------------------------------------- #
# Ranking and reporting
# --------------------------------------------------------------------------- #

def test_ranked_by_breadth_not_raw_count(tmp_path):
    """A single workspace with many instances must not outrank a rule appearing
    everywhere."""
    noisy = _workspace(tmp_path, "noisy", {
        f"feat-{i:02d}-x.md": SEMICOLON_DIAGRAM for i in range(1, 6)
    })
    # duplicate ordinals in every workspace -> broad but low count
    b = _workspace(tmp_path, "ds-b", {"feat-01-a.md": CLEAN_DIAGRAM, "feat-01-b.md": CLEAN_DIAGRAM})
    c = _workspace(tmp_path, "ds-c", {"feat-02-a.md": CLEAN_DIAGRAM, "feat-02-b.md": CLEAN_DIAGRAM})
    noisy_dupes = _workspace(tmp_path, "noisy2", {"feat-03-a.md": CLEAN_DIAGRAM, "feat-03-b.md": CLEAN_DIAGRAM})

    report = collect([noisy, b, c, noisy_dupes])
    assert report.groups[0].signature == "spec-filename-ordinal-uniqueness", (
        "the broadest symptom must rank first even though another has more raw "
        f"instances. Order was {[(g.signature, g.breadth, g.total) for g in report.groups]}"
    )


def test_report_states_migration_coverage(tmp_path):
    """Coverage must be visible. Un-migrated validators contribute nothing, and a
    reader has to know that rather than assume full coverage."""
    a = _workspace(tmp_path, "ds-a", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    text = format_report(collect([a]))
    assert "validators" in text and (
        "carried rule ids" in text or "no rule id" in text
    ), f"the report must state aggregation coverage: {text}"


def test_report_is_readable(tmp_path):
    a = _workspace(tmp_path, "ds-a", {"feat-01-a.md": SEMICOLON_DIAGRAM})
    b = _workspace(tmp_path, "ds-b", {"feat-01-b.md": SEMICOLON_DIAGRAM})
    text = format_report(collect([a, b]))
    assert "BREADTH" in text and "ds-a" in text and "ds-b" in text
    assert "mermaid-no-semicolon-in-note-or-message" in text
