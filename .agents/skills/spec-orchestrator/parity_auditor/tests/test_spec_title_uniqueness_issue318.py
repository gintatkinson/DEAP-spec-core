"""Regression tests for issue #318 — the linter has no title uniqueness gate.

``verify_model_coverage.py`` (a shim over ``parity_auditor.cli``) validated schema
coverage, UML conformance, filenames and Mermaid syntax, and never once looked at
whether two specifications claim the same ``title``. Duplicate titles are the input
that makes ``reconcile_backlog.py``'s ``normalize_title`` lookup ambiguous, so a
duplicate that reaches Phase 4 overwrites another issue's body (#316) or orphans it
(#329). This gate is the cheapest place to stop that, because it runs offline and
before anything is published.

**Scope: per spec type, not global.** Issue #303 keyed ``SyncValidator`` on
``(spec_type, normalised_title)`` for exactly this reason — an Epic and a Feature may
legitimately share a subject, and an epic issue is not satisfied by a same-titled
feature file. A global set, as the issue's proposed correction sketches, would reject
the ordinary ``Epic: Geo Location`` / ``Feature: Geo Location`` pairing. The collision
that does damage is two *Features* normalising to one title, because that is the key
the reconciler builds its lookup on.

**Normalisation matches ``reconcile_backlog.py``**, including its guard that keeps the
original title when prefix-stripping would empty it. The gate exists to prevent the
reconciler mis-resolving, so it must collide in exactly the space the reconciler
collides in — a stricter or looser normaliser would report collisions the reconciler
does not have, or miss ones it does.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402
from parity_auditor.validators.spec_title_uniqueness_validator import (  # noqa: E402
    SpecTitleUniquenessValidator,
    normalize_spec_title,
)

RULES = {
    "meta": {},
    "backlog_directories": {
        "features": "docs/features",
        "user_stories": "docs/user-stories",
        "use_cases": "docs/use-cases",
        "epics": "docs/epics",
        "schemas": "schema",
    },
    "target_directories": {},
    "flutter_rules": {},
    "python_rules": {},
    "spec_rules": {},
    "validation_rules": {},
}

RULE_ID = "spec-title-must-be-unique-within-its-spec-type"

_SEQ = [0]


def _spec(title):
    if title is None:
        # No frontmatter `title` and no H1: nothing for either extraction path to find.
        return "---\nissue_id: 1\n---\n\nBody prose with no heading at all.\n"
    return f'---\ntitle: "{title}"\nissue_id: 1\n---\n\n# {title}\n'


def _workspace(tmp_path, tree):
    """``tree`` maps a backlog directory to ``{filename: title}``."""
    _SEQ[0] += 1
    ws = tmp_path / f"ws{_SEQ[0]}"
    pipeline = ws / ".pipeline" / "logical-ui"
    pipeline.mkdir(parents=True)
    (pipeline / "codebase_rules.json").write_text(json.dumps(RULES), encoding="utf-8")
    for directory, files in tree.items():
        target = ws / directory
        target.mkdir(parents=True)
        for name, title in files.items():
            (target / name).write_text(_spec(title), encoding="utf-8")
    return WorkspaceRepository(workspace_dir=str(ws))


def _run(tmp_path, tree):
    return SpecTitleUniquenessValidator().validate(_workspace(tmp_path, tree))


# --------------------------------------------------------------------------- #
# Guards. A validator that rejects everything, or discovers nothing, would look
# correct without these.
# --------------------------------------------------------------------------- #

def test_distinct_titles_pass(tmp_path):
    errors = _run(tmp_path, {"docs/features": {
        "feat-01-a.md": "Feature 01: Geo Location",
        "feat-02-b.md": "Feature 02: Numeric Metrics",
    }})
    assert errors == [], f"distinct titles must produce no errors: {errors}"


def test_empty_and_missing_directories_are_tolerated(tmp_path):
    assert _run(tmp_path, {"docs/features": {}}) == []
    assert _run(tmp_path, {}) == []


def test_discovery_finds_the_specifications_it_iterates_issue318(tmp_path):
    """Fixture guard: the scan must actually read files.

    A validator whose title extraction silently failed would report no duplicates and
    be indistinguishable from a clean corpus, which is the failure mode every other
    assertion here depends on not happening.
    """
    validator = SpecTitleUniquenessValidator()
    repo = _workspace(tmp_path, {"docs/features": {
        "feat-01-a.md": "Feature 01: Geo Location",
        "feat-02-b.md": "Feature 02: Numeric Metrics",
        "feat-03-c.md": "Feature 03: Temporal Precision",
    }})
    discovered = validator.collect_titles(repo)
    assert len(discovered) == 3, (
        f"expected 3 discovered specifications, found {len(discovered)}: {discovered}"
    )


# --------------------------------------------------------------------------- #
# The gate itself
# --------------------------------------------------------------------------- #

def test_duplicate_titles_in_one_directory_are_rejected_issue318(tmp_path):
    errors = _run(tmp_path, {"docs/features": {
        "feat-01-ni-location.md": "Feature 01: Geo Location",
        "feat-02-rfc9179.md": "Feature 02: Geo Location",
    }})
    assert errors, "two Features with the same title must be reported"
    joined = " ".join(errors)
    assert "feat-01-ni-location.md" in joined and "feat-02-rfc9179.md" in joined, (
        f"the error must name both colliding files so the fix is actionable: {errors}"
    )
    assert any(getattr(e, "rule_id", None) == RULE_ID for e in errors), (
        f"the finding must carry the registered rule id {RULE_ID}: "
        f"{[getattr(e, 'rule_id', None) for e in errors]}"
    )


def test_titles_colliding_only_after_normalisation_are_rejected_issue318(tmp_path):
    """The reconciler's lookup key is the *normalised* title, so that is the space
    the collision has to be measured in — the ordinal prefix and the punctuation are
    exactly what it strips."""
    errors = _run(tmp_path, {"docs/features": {
        "feat-01-a.md": "Feature 01: Geo-Location Timing",
        "feat-02-b.md": "feat 2 - Geo Location Timing!",
    }})
    assert errors, (
        "titles that normalise to the same key must be reported; they are one key to "
        "reconcile_backlog.py even though they read differently"
    )


def test_three_way_collision_is_reported_once_issue318(tmp_path):
    errors = _run(tmp_path, {"docs/features": {
        "feat-01-a.md": "Feature 01: Status",
        "feat-02-b.md": "Feature 02: Status",
        "feat-03-c.md": "Feature 03: Status",
    }})
    assert len(errors) == 1, (
        f"a three-way collision is one error naming all three, not three: {errors}"
    )
    joined = " ".join(errors)
    for name in ("feat-01-a.md", "feat-02-b.md", "feat-03-c.md"):
        assert name in joined, f"{name} missing from the collision report: {errors}"


def test_same_title_in_different_spec_types_is_allowed_issue318(tmp_path):
    """The #303 scope decision. An Epic and a Feature may share a subject: the Epic
    names the theme and the Feature delivers part of it, and SyncValidator already
    treats ``(spec_type, normalised_title)`` as the identity, so a same-titled pair
    across types is not a collision in the space that matters."""
    errors = _run(tmp_path, {
        "docs/epics": {"epic-01-geo.md": "Epic 01: Geo Location"},
        "docs/features": {"feat-01-geo.md": "Feature 01: Geo Location"},
    })
    assert errors == [], (
        "an Epic and a Feature sharing a subject must not be reported; uniqueness is "
        f"scoped per spec type, per issue #303: {errors}"
    )


def test_every_spec_type_is_gated_issue318(tmp_path):
    """User Stories and Use Cases reach the same reconciler lookup, so a gate that
    covered only Features would leave two of the four types generating collisions."""
    ungated = []
    for directory, prefix in (
        ("docs/epics", "epic"),
        ("docs/features", "feat"),
        ("docs/user-stories", "us"),
        ("docs/use-cases", "uc"),
    ):
        errors = _run(tmp_path, {directory: {
            f"{prefix}-01-a.md": "Shared Subject",
            f"{prefix}-02-b.md": "Shared Subject",
        }})
        if not errors:
            ungated.append(directory)
    assert not ungated, f"duplicate titles pass unreported in: {ungated}"


def test_specifications_without_a_title_are_skipped_not_collided_issue318(tmp_path):
    """Two files with no ``title`` both normalise to the empty string. Reporting that
    as a collision would blame the wrong defect — a missing title is the UML
    validator's business, and pairing them here produces a message pointing at two
    innocent files."""
    errors = _run(tmp_path, {"docs/features": {
        "feat-01-a.md": None,
        "feat-02-b.md": None,
    }})
    assert errors == [], f"untitled specifications must not be reported as a collision: {errors}"


# --------------------------------------------------------------------------- #
# Normalisation parity with the reconciler
# --------------------------------------------------------------------------- #

def test_normalisation_matches_the_reconciler_issue318():
    assert normalize_spec_title("Feature 04: Numeric and Identifier Metrics") == (
        "numeric and identifier metrics"
    )
    assert normalize_spec_title("feat-04 - Numeric & Identifier Metrics") == (
        "numeric identifier metrics"
    )
    assert normalize_spec_title(None) == ""
    # The guard reconcile_backlog.py carries and sync_validator.py does not: stripping
    # the prefix from a title that is *only* a prefix must not erase it, or every
    # bare "Epic 2"-style title would collide with every other one.
    assert normalize_spec_title("Epic 2") == "epic 2"
