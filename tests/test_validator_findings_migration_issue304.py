"""Issue #304 — validators must emit structured ``Finding`` objects, not bare strings.

#301 built ``Finding`` and the multi-downstream aggregator but migrated only 2 of the
14 validators. The other 12 still returned plain ``str``, so every symptom they detected
was invisible to cross-downstream grouping: ``aggregator.collect`` skips anything that is
not a ``Finding``, and ``unmigrated_count`` was the only trace it left.

**All 14 are now migrated.** This file stops being a progress ledger and becomes a
regression gate: it is what fails if a new emission site is added without a rule id, or
if a validator is quietly dropped from the list rather than migrated.

This file is the gate for the migration. It is deliberately **static** rather than
behavioural. ``tests/test_rule_contracts.py::test_every_emitted_rule_id_is_registered``
already checks the rule ids that the live corpus happens to trigger, which is a subset:
a rule whose condition no file in this repository currently violates emits nothing and
is therefore checked by nothing. Reading the source instead catches every emission site,
including the ones this corpus never reaches.

Three invariants:

1. Every emission site in a migrated validator is wrapped in ``Finding(...)``.
2. Every migrated validator is actually wired into ``AGGREGATING_VALIDATORS``; wrapping
   without wiring produces rule ids that still reach no report.
3. The un-migrated remainder is enumerated with its site count, so partial progress is
   visible rather than implied. An empty ledger and a complete migration must not look
   the same — the failure mode ``KNOWN_UNREGISTERED_FAMILIES`` exists to prevent.
"""

import ast
import os

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VALIDATORS_DIR = os.path.join(
    REPO_ROOT,
    "skills", "spec-orchestrator", "parity_auditor", "src", "parity_auditor", "validators",
)

# Validators required to emit only structured findings. Adding a name here without
# migrating the module fails; migrating a module without adding it here passes, which is
# why invariant 3 below pins the remainder as well.
MIGRATED = (
    "mermaid_syntax_validator.py",
    "spec_filename_validator.py",
    # Added by #318 rather than migrated: it was written against Finding from the
    # start, so it joins the ledger fully migrated. Listing it here is what keeps
    # test_validator_discovery_is_not_vacuous_issue304's ledger-equals-package
    # assertion true, and what forces any future emission site in it to carry a rule id.
    "spec_title_uniqueness_validator.py",
    "source_reference_validator.py",
    # Added by #336 rather than migrated: its single emission site was written as
    # Finding("markdown-broken-link-reference", ...) from the start, so it joins the
    # ledger fully migrated. It was absent from both MIGRATED and NOT_YET_MIGRATED,
    # which is the "unaccounted for" state test_validator_discovery_is_not_vacuous_issue304
    # exists to catch -- an emitting validator no gate was checking.
    "link_validator.py",
    "cardinality_validator.py",
    "spec_validator.py",
    "dependency_validator.py",
    "sync_validator.py",
    "profile_scoping_validator.py",
    "behavioral.py",
    "schema_mapping_validator.py",
    "test_completeness_validator.py",
    "docs.py",
    "logical_ui_validator.py",
    "codebase.py",
    "uml.py",
    "docstring_validator.py",
    "profile_compliance_validator.py",
    "dispatch_preamble_validator.py",
    "plan_validator.py",
)

# Migrated, but deliberately NOT wired into AGGREGATING_VALIDATORS. Each entry states
# why, at length, because "not wired" and "forgotten to wire" are indistinguishable
# otherwise — the same reason `KNOWN_UNREGISTERED_FAMILIES` exists.
AGGREGATION_EXEMPT = {
    "sync_validator.py": (
        "SyncValidator shells out to the issue tracker (subprocess.run on "
        "tracker_rules.commands.list_issues, 30s timeout) to fetch registered issues. "
        ".pipeline/upstream/pipeline-tooling.md, section Validation Gates, forbids "
        "network egress inside a blocking validation gate: a gate that calls a "
        "third-party service fails when that service is down or rate-limits, blocking "
        "work for reasons unrelated to correctness. The aggregator runs over N "
        "workspaces and is exercised by the contract gate in CI, so wiring this in "
        "would put N tracker round-trips on the critical path of every run. Its "
        "findings are still structured, so its rule ids are registered and orphan "
        "detection covers it; only the aggregation wiring is withheld. Making it "
        "aggregate needs an offline issue snapshot, which is out of scope for #304."
    ),
}

# The remainder, with the emission-site count measured at the time of writing. The count
# is asserted, so a module that grows new bare-string sites while awaiting migration is
# reported rather than absorbed silently.
#
# These counts are higher than the inventory table on issue #304, which counted
# `errors.append` occurrences with grep. Four validators also emit through an early
# `return ["..."]` — profile_scoping and schema_mapping bail out that way when the
# codebase is empty, logical_ui twice and test_completeness once. Those messages reach
# the same consumers and are equally invisible to aggregation, so they are sites too.
# Measured: 152 emission sites in total, 12 migrated by #301, 140 remaining — not 135.
#
# **Now empty: the migration is complete.** All 140 remaining sites were migrated, in the
# order profile_scoping (2), behavioral (2), schema_mapping (3), test_completeness (6),
# docs (6), logical_ui (16), codebase (18), uml (78).
#
# An empty mapping is exactly the state invariant 3 was written to distrust, because
# "finished" and "nobody kept the ledger" render identically here. The structure is kept
# rather than deleted so a future un-migrated validator has a defined home, and
# `test_the_remainder_is_empty_because_migration_is_complete_issue304` below asserts the
# stronger property directly: emptiness is only acceptable while every discovered
# validator is listed as migrated. Deleting a name from MIGRATED without adding it here
# fails that test rather than quietly shrinking what the suite checks.
NOT_YET_MIGRATED = {}

# Modules in the package that emit nothing and so are neither migrated nor pending.
_NON_EMITTING = {"__init__.py", "base.py"}


def _parse(filename):
    path = os.path.join(VALIDATORS_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def _is_finding_call(node):
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "Finding")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "Finding")
    )


def _emission_sites(tree):
    """Every place the module hands a message to a caller.

    Two shapes occur in this package: ``errors.append(...)`` — by far the common one —
    and an early ``return ["..."]`` used by validators that bail out with a single
    message. Both reach the aggregator, so both must carry a rule id. ``errors.extend``
    is not a site: it forwards findings another site already constructed.
    """
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "append" and node.args:
                target = node.func.value
                if isinstance(target, ast.Name) and target.id.endswith("errors"):
                    sites.append((node.lineno, node.args[0]))
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.List):
            for element in node.value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    sites.append((node.lineno, element))
                elif isinstance(element, ast.JoinedStr):
                    sites.append((node.lineno, element))
    return sites


# --------------------------------------------------------------------------- #
# Fixture guards. A scan that discovers nothing must not read as a pass.
# --------------------------------------------------------------------------- #

def test_validator_discovery_is_not_vacuous_issue304():
    assert os.path.isdir(VALIDATORS_DIR), f"validators package missing: {VALIDATORS_DIR}"
    discovered = {
        n for n in os.listdir(VALIDATORS_DIR)
        if n.endswith(".py") and n not in _NON_EMITTING
    }
    assert len(discovered) >= 12, (
        f"only {len(discovered)} emitting validator modules discovered in "
        f"{VALIDATORS_DIR}; the assertions below would be near-vacuous"
    )
    ledger = set(MIGRATED) | set(NOT_YET_MIGRATED)
    assert discovered == ledger, (
        "the migration ledger has drifted from the package. Only in ledger: "
        f"{sorted(ledger - discovered)}; only on disk: {sorted(discovered - ledger)}. "
        "A validator in neither MIGRATED nor NOT_YET_MIGRATED is unaccounted for."
    )


def test_migrated_validators_have_emission_sites_issue304():
    """Guard for invariant 1: a module with no sites would satisfy it trivially."""
    for filename in MIGRATED:
        sites = _emission_sites(_parse(filename))
        assert sites, (
            f"{filename}: no emission sites found, so the Finding-wrapping assertion "
            "would pass vacuously. The AST scan is probably looking for the wrong shape."
        )


# --------------------------------------------------------------------------- #
# Invariant 1 — every emission site in a migrated validator carries a rule id.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("filename", MIGRATED)
def test_migrated_validator_emits_only_findings_issue304(filename):
    bare = [
        lineno for lineno, arg in _emission_sites(_parse(filename))
        if not _is_finding_call(arg)
    ]
    assert not bare, (
        f"{filename}: {len(bare)} emission site(s) still produce a bare string, at "
        f"line(s) {bare}. A message without a rule id is skipped by "
        "aggregator.collect and contributes nothing to cross-downstream grouping "
        "(#301). Wrap it: Finding(\"<registered-rule-id>\", <message>, location=...)."
    )


# --------------------------------------------------------------------------- #
# Invariant 2 — migrated means wired in, not merely wrapped.
# --------------------------------------------------------------------------- #

def test_migrated_validators_are_wired_into_the_aggregator_issue304():
    from parity_auditor.aggregator import AGGREGATING_VALIDATORS

    wired = {
        cls.__module__.rsplit(".", 1)[-1] + ".py" for cls in AGGREGATING_VALIDATORS
    }
    assert wired, "AGGREGATING_VALIDATORS is empty; this assertion would be vacuous"
    missing = sorted(set(MIGRATED) - wired - set(AGGREGATION_EXEMPT))
    assert not missing, (
        f"validators migrated to Finding but absent from AGGREGATING_VALIDATORS: "
        f"{missing}. Their rule ids reach no report, so the migration bought nothing. "
        "If the omission is deliberate, record it in AGGREGATION_EXEMPT with a reason."
    )
    stale = sorted(set(AGGREGATION_EXEMPT) & wired)
    assert not stale, (
        f"AGGREGATION_EXEMPT still excuses validators that are in fact wired in: "
        f"{stale}. A stale exemption reads as a known gap that no longer exists."
    )


def test_aggregation_exemptions_state_a_reason_issue304():
    """An unexplained exemption is indistinguishable from an oversight."""
    assert AGGREGATION_EXEMPT, (
        "no exemptions recorded; if that becomes true this guard should be deleted "
        "along with AGGREGATION_EXEMPT, not left asserting an empty mapping"
    )
    for filename, reason in AGGREGATION_EXEMPT.items():
        assert filename in MIGRATED, (
            f"{filename} is exempt from aggregation but is not listed as migrated; "
            "the exemption is about wiring, not about skipping the migration"
        )
        assert len(reason) > 200, (
            f"{filename}: the exemption needs a reason naming the governing constraint "
            "and what it would take to lift, not a one-line excuse"
        )


# --------------------------------------------------------------------------- #
# Invariant 3 — the remainder stays counted.
# --------------------------------------------------------------------------- #

def test_the_remainder_is_empty_because_migration_is_complete_issue304():
    """An empty remainder must be *proved* complete, not merely observed empty.

    The parametrized count assertion below generates zero cases once NOT_YET_MIGRATED is
    empty, so on its own it stops checking anything at exactly the moment the ledger
    claims success. This test is what keeps that state honest: while the remainder is
    empty, every emitting validator in the package must appear in MIGRATED, and each must
    genuinely have emission sites — a module silently emptied of its checks would
    otherwise satisfy "migrated" for free.
    """
    if NOT_YET_MIGRATED:
        pytest.skip(
            f"migration still in progress; {len(NOT_YET_MIGRATED)} validator(s) pending, "
            "so the per-module count assertions below are the live gate"
        )
    discovered = {
        n for n in os.listdir(VALIDATORS_DIR)
        if n.endswith(".py") and n not in _NON_EMITTING
    }
    unaccounted = sorted(discovered - set(MIGRATED))
    assert not unaccounted, (
        f"the remainder ledger is empty but {unaccounted} are in neither MIGRATED nor "
        "NOT_YET_MIGRATED. An empty remainder must mean 'all migrated', never 'no longer "
        "tracked'."
    )
    assert len(MIGRATED) >= 14, (
        f"only {len(MIGRATED)} validators listed as migrated; #304 covers 14. A shrinking "
        "MIGRATED tuple with an empty remainder is the ledger being abandoned, not a "
        "completed migration."
    )


@pytest.mark.parametrize("filename,expected", sorted(NOT_YET_MIGRATED.items()) or [("__none__", 0)])
def test_unmigrated_site_count_is_recorded_issue304(filename, expected):
    if filename == "__none__":
        assert expected == 0
        return
    actual = len(_emission_sites(_parse(filename)))
    assert actual == expected, (
        f"{filename}: {actual} emission sites, ledger says {expected}. If sites were "
        "migrated, move the module to MIGRATED; if sites were added, they were added "
        "un-migrated and the debt in #304 grew silently."
    )
