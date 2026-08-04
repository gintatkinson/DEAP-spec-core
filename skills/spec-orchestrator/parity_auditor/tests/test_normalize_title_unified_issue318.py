"""Regression tests for the three divergent copies of `normalize_title` (flagged while
working #318, deferred twice, resolved here).

`reconcile_backlog.py` addresses tracker issues by normalised title whenever a spec has
no canonical `issue_id` yet. Two validators exist to stop that key colliding — the #318
uniqueness gate, and `SyncValidator`'s local/tracker parity check — and each carried its
own copy of the normaliser:

* `reconcile_backlog.py::normalize_title` — the consumer. Keeps the original title when
  prefix-stripping would empty it, so "Epic 2" normalises to `epic 2` rather than `""`.
* `spec_title_uniqueness_validator.py::normalize_spec_title` — copied from the reconciler
  deliberately (#318), guard included.
* `sync_validator.py`'s local closure — **no guard**, and it additionally folded `_` to a
  space. Two independent divergences from the function it exists to protect.

A gate that collides in a different space from its consumer is worse than no gate: the
looser copy misses collisions the reconciler will make, and the stricter one invents
collisions it will not. `sync_validator`'s copy was both at once — looser on prefix-only
titles (every "Epic 2"-shaped title collapsed to one key) and stricter on underscores.

The unification is by identity, not by copying: both validators now import the
reconciler's function, so a future change to it cannot silently desynchronise a gate.
`utils/spec_titles.py` documents why the dependency runs in that direction.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PACKAGE_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

import reconcile_backlog  # noqa: E402
from parity_auditor.utils import spec_titles  # noqa: E402
from parity_auditor.validators import spec_title_uniqueness_validator, sync_validator  # noqa: E402


# Titles chosen so that every way the three copies differed shows up.
CORPUS = [
    "Epic 01: Geo Location Framework",
    "epic-01-geo-location-framework",
    "Epic 2",                      # prefix-only: the guard the sync copy lacked
    "feat-02: User Authentication",
    "US-03",
    "uc-04-device-state",
    "geo_location_capture",        # underscore: the fold only the sync copy did
    "  Quoted \"Title\"  ",
    "",
]


def test_the_shared_normaliser_is_the_reconcilers_own_function_issue318():
    """Identity, not equivalence. Equivalent copies drift; a shared reference cannot."""
    assert spec_titles.normalize_spec_title is reconcile_backlog.normalize_title
    assert spec_title_uniqueness_validator.normalize_spec_title is (
        reconcile_backlog.normalize_title
    ), "the #318 gate must normalise through the reconciler it protects"
    assert sync_validator.normalize_spec_title is reconcile_backlog.normalize_title, (
        "SyncValidator must normalise through the reconciler it protects"
    )


def test_every_consumer_agrees_across_the_corpus_issue318():
    assert CORPUS, "fixture guard: the corpus is empty"
    for title in CORPUS:
        expected = reconcile_backlog.normalize_title(title)
        assert spec_titles.normalize_spec_title(title) == expected, title
        assert spec_title_uniqueness_validator.normalize_spec_title(title) == expected, title
        assert sync_validator.normalize_spec_title(title) == expected, title


def test_prefix_only_titles_keep_the_guard_issue318():
    """"Epic 2" must not normalise to the empty string.

    Without the guard every prefix-only title shares one key, and `SyncValidator` reports
    a collision between two specs the reconciler would resolve apart — or misses one it
    would not.
    """
    assert reconcile_backlog.normalize_title("Epic 2") == "epic 2"
    assert sync_validator.normalize_spec_title("Epic 2") == "epic 2"
    assert sync_validator.normalize_spec_title("Epic 3") != sync_validator.normalize_spec_title(
        "Epic 2"
    )


def test_underscores_are_preserved_like_the_reconciler_issue318():
    """The reconciler's `[^\\w\\s]` strip leaves `_` alone; the sync copy folded it to a
    space, so two specs the reconciler keys apart looked identical to the gate."""
    assert reconcile_backlog.normalize_title("geo_location") == "geo_location"
    assert sync_validator.normalize_spec_title("geo_location") == "geo_location"
    assert sync_validator.normalize_spec_title("geo_location") != (
        sync_validator.normalize_spec_title("geo location")
    )


def test_no_second_definition_of_the_normaliser_survives_issue318():
    """Structural. Three copies is how the divergence arose; one definition is the fix."""
    roots = [
        os.path.join(SRC_ROOT, "parity_auditor"),
        SCRIPT_DIR,
    ]
    scanned = []
    definitions = []
    pattern = re.compile(r"^\s*def\s+normalize_(?:spec_)?title\s*\(", re.MULTILINE)
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                scanned.append(path)
                with open(path, "r", encoding="utf-8") as fh:
                    if pattern.search(fh.read()):
                        definitions.append(os.path.relpath(path, os.path.dirname(SRC_ROOT)))

    assert len(scanned) > 20, f"fixture guard: only {len(scanned)} modules were scanned"
    assert len(definitions) == 1, (
        f"exactly one definition of the normaliser must exist; found {definitions}"
    )
    assert definitions[0].endswith("reconcile_backlog.py"), (
        f"the definition must live with its consumer; found {definitions}"
    )
