"""Guards the four wording fixes that closed two downstream agent failures.

Both failures were caused by upstream prose, not by the downstream agents' reasoning:

1. A planning agent read "every implementation subagent's DoD must enforce the full
   3-layer chain" as "every micro-task delivers all three layers". That contradicts the
   single-item scope rule beside it, the 2-5 minute micro-task mandate, and the gate,
   which aggregates per Feature across files. It marked two layers "N/A" instead.
2. An implementer hit a file containing symbols its task assumed absent, treated a
   compile error as a RED phase, and self-authorised an in-place rewrite of existing
   code under a task that said append -- logging the deviation rather than halting.

Without these assertions the four corrections are orphan documentation: prose that can
be silently deleted or reverted, which is the failure mode tests/rule_contracts.py
exists to detect.
"""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS = os.path.join(REPO_ROOT, ".agents", "AGENTS.md")
FDI = os.path.join(REPO_ROOT, "skills", "feature-driven-implementation", "SKILL.md")
TDD = os.path.join(REPO_ROOT, "rules", "tdd-mandate.md")


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_governed_documents_exist():
    """Guard: every assertion below reads one of these."""
    for path in (AGENTS, FDI, TDD):
        assert os.path.isfile(path), f"{path} missing; the scans below would be vacuous"


# --------------------------------------------------------------------------- #
# 1. The 3-layer chain binds per specification item, not per dispatch.
# --------------------------------------------------------------------------- #

def test_three_layer_dod_binds_per_specification_item():
    text = _read(AGENTS)
    assert "per specification item" in text, (
        "AGENTS.md must state that the 3-layer LUI chain binds per specification item. "
        "Read as per-dispatch it contradicts the single-item scope rule beside it and "
        "the 2-5 minute micro-task mandate, and it is not what the gate checks."
    )
    assert "test_every_specification_has_full_lui_chain" in text, (
        "AGENTS.md must name the gate that actually enforces the chain, so the "
        "documented rule and the enforced rule can be compared"
    )


def test_na_is_forbidden_against_a_layer():
    text = _read(AGENTS)
    assert "`N/A` is forbidden" in text or "Writing `N/A` against a layer is forbidden" in text, (
        "AGENTS.md must forbid marking a layer N/A. A layer is never inapplicable to a "
        "Feature -- it is delivered or deferred to a named micro-task. N/A is how a "
        "Feature completes permanently missing two layers."
    )
    assert "micro-task number that closes that layer" in text, (
        "a deferred layer must name the micro-task that closes it, otherwise 'deferred' "
        "and 'dropped' are indistinguishable"
    )


# --------------------------------------------------------------------------- #
# 2. "Critical deviation" is defined, so it cannot be self-classified away.
# --------------------------------------------------------------------------- #

def test_critical_deviation_is_enumerated():
    text = _read(FDI)
    assert "A deviation is **critical**" in text, (
        "mandate 14 says critical deviations block progress but never defined critical, "
        "so agents self-classified and continued"
    )
    for clause in (
        "set of files touched differs",
        "requires modifying or replacing existing code",
        "existing symbol that has callers",
        "expands beyond the named files",
    ):
        assert clause in text, f"missing critical-deviation clause: {clause!r}"


def test_only_viable_path_is_rejected_as_a_finding():
    text = _read(FDI)
    assert "is not a finding" in text, (
        "'this is the only viable path' was the reasoning used to self-authorise a "
        "critical deviation. The skill must say that this is the report, not the "
        "justification for proceeding."
    )


# --------------------------------------------------------------------------- #
# 3. A compile error is not a RED phase.
# --------------------------------------------------------------------------- #

def test_compile_error_is_not_red():
    text = _read(TDD)
    assert "A compile error is not a RED phase" in text, (
        "an implementer recorded an undefined-symbol compile error as its RED phase. A "
        "test that does not compile has not run and evidences nothing."
    )
    assert "has not run" in text
    assert "failing on an assertion" in text, (
        "RED must be defined positively -- an executed test failing on an assertion -- "
        "or the prohibition above has nothing to redirect to"
    )


def test_behavioural_failures_must_not_be_masked():
    text = _read(TDD)
    assert "mask a behavioural one" in text, (
        "where a task both adds symbols and corrects behaviour, the behavioural "
        "failures are the evidence the task exists; bundling them behind an "
        "undefined-symbol error discards them"
    )


# --------------------------------------------------------------------------- #
# 4. Provenance is established before editing unexpected pre-existing code.
# --------------------------------------------------------------------------- #

def test_provenance_check_is_mandated():
    text = _read(FDI)
    assert "Provenance check" in text, (
        "an implementer found symbols its task assumed absent, described them as "
        "'concurrently modified by another process', and edited them without "
        "establishing whether that was committed code or a live concurrent writer"
    )
    for clause in ("git log -p", "git diff", "stale view"):
        assert clause in text, f"provenance check missing: {clause!r}"


def test_concurrent_writer_is_a_halt():
    text = _read(FDI)
    assert "concurrent writer" in text and "HALT" in text, (
        "uncommitted changes by another process mean a parallel implementer, which "
        "section 3.7 Invariants forbids. Editing that file corrupts their work, so it "
        "must halt rather than reconcile."
    )
