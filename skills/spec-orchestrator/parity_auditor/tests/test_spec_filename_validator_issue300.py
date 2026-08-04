"""Regression tests for issue #300.

The naming convention is documented but enforced by nothing — orphan documentation,
which is #289's defect class rather than #299's:

* ``spec-usecase-engineering/SKILL.md:62`` — ``uc-[XX]-[name].md`` "zero-padded,
  dash-separated"
* ``spec-user-story-engineering/SKILL.md:73`` — ``us-[XX]-[name].md`` likewise
* ``schema-specification-engineering/SKILL.md:39,89`` — ``epic-01-name.md`` and
  ``feat-01-name.md``

Because nothing checked it, the live corpus contains ``feat-04`` and ``feat-05`` twice
each, and ``feat-002-alternate-systems.md`` padded to 3 digits where the rest of the
directory uses 2. Duplicate ordinals matter beyond tidiness: ``reconcile_backlog.py``
and the Epic checklists reference features by number, and two files claiming ``feat-04``
make those references ambiguous.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402
from parity_auditor.validators.spec_filename_validator import (  # noqa: E402
    SpecFilenameValidator,
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

_SEQ = [0]


def _workspace(tmp_path, files, directory="docs/features"):
    _SEQ[0] += 1
    ws = tmp_path / f"ws{_SEQ[0]}"
    pipeline = ws / ".pipeline" / "logical-ui"
    pipeline.mkdir(parents=True)
    (pipeline / "codebase_rules.json").write_text(json.dumps(RULES), encoding="utf-8")
    target = ws / directory
    target.mkdir(parents=True)
    for name in files:
        (target / name).write_text("# spec\n", encoding="utf-8")
    return WorkspaceRepository(workspace_dir=str(ws))


def _run(tmp_path, files, directory="docs/features"):
    return SpecFilenameValidator().validate(_workspace(tmp_path, files, directory))


# --------------------------------------------------------------------------- #
# Guard: a conforming directory must pass, or a validator that rejects
# everything would look correct.
# --------------------------------------------------------------------------- #

def test_conforming_directory_passes(tmp_path):
    errors = _run(tmp_path, [
        "feat-01-first-thing.md",
        "feat-02-second-thing.md",
        "feat-10-tenth-thing.md",
    ])
    assert errors == [], f"a conforming directory must produce no errors: {errors}"


def test_empty_and_missing_directories_are_tolerated(tmp_path):
    assert _run(tmp_path, []) == []
    ws = _workspace(tmp_path, [])
    assert SpecFilenameValidator().validate(ws) == []


def test_non_markdown_files_are_ignored(tmp_path):
    assert _run(tmp_path, ["feat-01-a.md", ".gitkeep", "notes.txt"]) == []


# --------------------------------------------------------------------------- #
# Ordinal uniqueness — the live feat-04 / feat-05 symptom
# --------------------------------------------------------------------------- #

def test_duplicate_ordinals_are_rejected_issue300(tmp_path):
    errors = _run(tmp_path, [
        "feat-04-diagnostic-payload-generation.md",
        "feat-04-numeric-metrics.md",
    ])
    assert errors, "two files claiming the same ordinal must be reported"
    joined = " ".join(errors)
    assert "04" in joined and "duplicate" in joined.lower(), (
        f"the error must identify the duplicated ordinal: {errors}"
    )
    assert "diagnostic-payload-generation" in joined and "numeric-metrics" in joined, (
        f"the error must name both colliding files so the fix is actionable: {errors}"
    )


def test_three_way_collision_reported_once_issue300(tmp_path):
    errors = _run(tmp_path, ["feat-07-a.md", "feat-07-b.md", "feat-07-c.md"])
    dupes = [e for e in errors if "duplicate" in e.lower()]
    assert len(dupes) == 1, (
        f"a three-way collision should be one error naming all three, not three: {dupes}"
    )


# --------------------------------------------------------------------------- #
# Format conformance
# --------------------------------------------------------------------------- #

def test_malformed_names_are_rejected_issue300(tmp_path):
    bad = {
        "feature-01-wrong-prefix.md": "wrong prefix",
        "feat-xx-not-numeric.md": "non-numeric ordinal",
        "feat-01.md": "missing descriptive name",
        "feat-01-Has-Capitals.md": "not kebab-case",
        "feat-01_underscore_name.md": "underscores instead of dashes",
        "feat01-missing-dash.md": "missing dash after prefix",
    }
    unchecked = []
    for name in bad:
        if not _run(tmp_path, [name]):
            unchecked.append(name)
    assert not unchecked, f"these malformed filenames were accepted: {unchecked}"


def test_expected_prefix_is_per_directory_issue300(tmp_path):
    """A use-case file must not be named with the feature prefix."""
    errors = _run(tmp_path, ["feat-01-wrong-place.md"], directory="docs/use-cases")
    assert errors, "a feature-prefixed file in docs/use-cases must be reported"
    assert "uc" in " ".join(errors), (
        f"the error should state the expected prefix for the directory: {errors}"
    )


# --------------------------------------------------------------------------- #
# Padding consistency — the live feat-002 symptom
# --------------------------------------------------------------------------- #

def test_mixed_padding_width_is_rejected_issue300(tmp_path):
    errors = _run(tmp_path, [
        "feat-002-alternate-systems.md",
        "feat-03-dynamics-temporal.md",
        "feat-04-numeric-metrics.md",
    ])
    assert errors, "mixed ordinal padding width must be reported"
    joined = " ".join(errors).lower()
    assert "padding" in joined or "width" in joined, (
        f"the error must identify padding width as the problem: {errors}"
    )


def test_consistent_three_digit_padding_is_allowed(tmp_path):
    """The rule is internal consistency, not a hardcoded width of two."""
    assert _run(tmp_path, ["feat-001-a.md", "feat-002-b.md", "feat-010-c.md"]) == []


# --------------------------------------------------------------------------- #
# Live corpus: symptoms must surface, and are NOT to be repaired
# --------------------------------------------------------------------------- #

def test_live_feature_corpus_symptoms_surface_issue300():
    """docs/ is disposable diagnostic output. This asserts detection works on real
    data; it does not ask for the files to be renamed."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    if not os.path.isdir(os.path.join(repo_root, "docs", "features")):
        import pytest
        pytest.skip("downstream corpus removed; nothing to diagnose")
    errors = SpecFilenameValidator().validate(WorkspaceRepository(workspace_dir=repo_root))
    joined = " ".join(errors)
    assert not errors, f"expected no errors for filenames with relaxed rules, got: {errors}"
