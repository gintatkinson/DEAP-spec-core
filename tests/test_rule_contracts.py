"""The contract gate for issue #298.

Asserts that documentation and enforcement stay paired, in both directions.

Seven defects in one audit session were the same class — documented contract
diverging from enforced contract. Fixing them individually has no terminating
condition; instance eight is already out there. These tests are the terminating
condition for the Mermaid family.

Scope is stated deliberately and narrowly: this covers the Mermaid syntax rules.
``rule_contracts.KNOWN_UNREGISTERED_FAMILIES`` lists the families not yet covered so
the gap is explicit rather than implied by an empty section.
"""

import os
import re

import pytest

from rule_contracts import (
    ALL_CONTRACTS,
    FAMILIES,
    KNOWN_UNREGISTERED_FAMILIES,
    RuleContract,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Vacuity guards. A registry test matching nothing is worse than no test.
# --------------------------------------------------------------------------- #

def test_registry_is_populated():
    assert len(ALL_CONTRACTS) >= 5, (
        f"registry holds only {len(ALL_CONTRACTS)} contracts; the assertions below "
        "would be close to vacuous"
    )
    assert all(isinstance(c, RuleContract) for c in ALL_CONTRACTS)


def test_registry_ids_are_unique():
    ids = [c.id for c in ALL_CONTRACTS]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"duplicate contract ids: {dupes}"


def test_scope_limit_is_declared():
    """The registry must name what it does not cover."""
    assert KNOWN_UNREGISTERED_FAMILIES, (
        "KNOWN_UNREGISTERED_FAMILIES must list the families not yet registered, so "
        "an incomplete registry is distinguishable from a complete one"
    )


# --------------------------------------------------------------------------- #
# (a) and (b): both anchors of every contract must resolve.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("contract", ALL_CONTRACTS, ids=lambda c: c.id)
def test_documentation_anchor_resolves(contract):
    path = os.path.join(REPO_ROOT, contract.documented_in)
    assert os.path.isfile(path), f"{contract.id}: doc file missing: {contract.documented_in}"
    assert contract.doc_anchor in _read(path), (
        f"{contract.id}: '{contract.doc_anchor}' not found in {contract.documented_in}. "
        "The rule is enforced but no longer documented — orphan enforcement."
    )


@pytest.mark.parametrize("contract", ALL_CONTRACTS, ids=lambda c: c.id)
def test_enforcement_anchor_resolves(contract):
    path = os.path.join(REPO_ROOT, contract.enforced_in)
    assert os.path.isfile(path), f"{contract.id}: source missing: {contract.enforced_in}"
    assert contract.enforcement_anchor in _read(path), (
        f"{contract.id}: '{contract.enforcement_anchor}' not found in "
        f"{contract.enforced_in}. The rule is documented but no longer enforced — "
        "orphan documentation."
    )


# --------------------------------------------------------------------------- #
# (c) and (d) Orphan detection, parametrized over families.
#
# Choosing #300 as the second family was a deliberate test of whether the #298
# design generalises. It half did: the anchor tests above are family-agnostic and
# picked up the new family for free, but orphan detection was hardcoded to Mermaid.
# These are now driven by each family's own scanners.
# --------------------------------------------------------------------------- #

def _documented_headings(family):
    path = os.path.join(REPO_ROOT, family.doc_file)
    return set(re.findall(family.doc_heading_pattern, _read(path)))


def _enforced_messages(family):
    """Union across every enforcing file the family declares.

    Single-file families are the common case and are unchanged: ``enforcement_paths()``
    returns ``[enforcement_file]`` for them. A family whose rules span validators — the
    schema-traceability family added for #304 — lists all of them, so a rule enforced in
    the second file is not invisible to orphan detection.
    """
    messages = set()
    for rel in family.enforcement_paths():
        messages |= set(re.findall(family.enforcement_pattern, _read(os.path.join(REPO_ROOT, rel))))
    return messages


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.name)
def test_documented_rule_scan_is_not_vacuous(family):
    if family.doc_heading_pattern is None:
        pytest.skip(f"{family.name}: {family.doc_orphan_blocked_by}")
    headings = _documented_headings(family)
    assert len(headings) >= 4, (
        f"{family.name}: only {len(headings)} rule headings parsed from "
        f"{family.doc_file}; the orphan-documentation test would be near-vacuous. "
        f"Found: {headings}"
    )


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.name)
def test_every_documented_rule_is_registered(family):
    """A rule stated as prohibited but enforced by nothing. Issue #289."""
    if family.doc_heading_pattern is None:
        pytest.skip(f"{family.name}: {family.doc_orphan_blocked_by}")
    registered = {c.doc_anchor for c in family.contracts}
    exempt = family.doc_only or {}
    orphans = sorted(
        h for h in _documented_headings(family)
        if h not in registered and h not in exempt
    )
    assert not orphans, (
        f"{family.name}: documented rules with no registry entry: {orphans}. Either pair "
        "each with the code that enforces it, or record it in the family's doc_only map "
        "with a reason."
    )


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.name)
def test_enforced_message_scan_is_not_vacuous(family):
    messages = _enforced_messages(family)
    assert len(messages) >= 3, (
        f"{family.name}: only {len(messages)} enforced messages parsed from "
        f"{', '.join(family.enforcement_paths())}; the orphan-enforcement test would be "
        f"near-vacuous. Found: {messages}"
    )


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f.name)
def test_every_enforced_rule_is_registered(family):
    """A rule the code rejects that no document mentions. Issue #299."""
    registered = [c.enforcement_anchor for c in family.contracts]
    orphans = sorted(
        msg for msg in _enforced_messages(family)
        if not any(anchor in msg or msg in anchor for anchor in registered)
    )
    assert not orphans, (
        f"{family.name}: content is rejected for reasons with no registry entry: "
        f"{orphans}. Every enforced rule must be paired with the document that states "
        "it, or a generating subagent cannot comply."
    )


# --------------------------------------------------------------------------- #
# Known divergences must stay visible, and must not silently accumulate.
# --------------------------------------------------------------------------- #

def test_known_divergences_are_documented_with_a_resolution_path():
    """A recorded divergence is acceptable; an undescribed one is not.

    These exist because an agent may not edit .pipeline/constitution.md, so a
    constitution-level mismatch can only be recorded and escalated. Each entry must
    name where the operative rule lives and what amendment resolves it.
    """
    import rule_contracts
    from rule_contracts import KNOWN_DOC_DIVERGENCES, RESOLVED_DIVERGENCES

    # An empty OPEN register is the goal. The structure must still exist, so a future
    # divergence has a defined home instead of going undocumented.
    assert hasattr(rule_contracts, "KNOWN_DOC_DIVERGENCES"), (
        "the open-divergence register must remain declared even when empty"
    )
    for key, description in KNOWN_DOC_DIVERGENCES.items():
        assert len(description) > 80, (
            f"open divergence '{key}' needs a description naming the governing document, "
            "the implemented rule, and the amendment that would resolve it"
        )
        assert "pending" in description.lower() or "amendment" in description.lower(), (
            f"open divergence '{key}' must state its resolution path, or it is just a "
            "permanent excuse"
        )

    # Resolved entries are history and must record HOW they were closed.
    assert RESOLVED_DIVERGENCES, (
        "the resolved register must not be emptied; it is the record of how divergences "
        "were closed"
    )
    for key, description in RESOLVED_DIVERGENCES.items():
        assert re.search(r"RESOLVED by (AMEND-\d+|#\d+)", description), (
            f"resolved divergence '{key}' must name the amendment or issue that closed "
            "it, e.g. 'RESOLVED by AMEND-0001'"
        )


def test_resolved_divergences_reference_real_amendments():
    """A citation to a non-existent amendment is worse than none."""
    from rule_contracts import RESOLVED_DIVERGENCES

    log = os.path.join(REPO_ROOT, ".pipeline", "constitution-amendments.md")
    if not os.path.isfile(log):
        pytest.skip("amendment log absent")
    logged = set(re.findall(r"^## (AMEND-\d+)", _read(log), re.M))
    missing = []
    for key, description in RESOLVED_DIVERGENCES.items():
        for cited in re.findall(r"AMEND-\d+", description):
            if cited not in logged:
                missing.append(f"{key} -> {cited}")
    assert not missing, (
        f"resolved divergences cite amendments absent from the log: {missing}"
    )


# --------------------------------------------------------------------------- #
# #301 - every rule id a validator emits must be registered here.
#
# Closes the loop rather than adding a parallel check: a Finding whose rule_id is not
# in the registry is invisible to cross-downstream aggregation AND undocumented, so the
# same gate covers #299 and #301.
# --------------------------------------------------------------------------- #

def test_every_emitted_rule_id_is_registered():
    import sys
    src = os.path.join(
        REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "src"
    )
    if src not in sys.path:
        sys.path.insert(0, src)

    from parity_auditor.aggregator import AGGREGATING_VALIDATORS
    from parity_auditor.core.findings import Finding
    from parity_auditor.core.workspace import WorkspaceRepository
    from rule_contracts import REGISTERED_RULE_IDS

    repo = WorkspaceRepository(workspace_dir=REPO_ROOT)
    emitted = set()
    for validator_cls in AGGREGATING_VALIDATORS:
        for finding in validator_cls().validate(repo):
            if isinstance(finding, Finding):
                emitted.add(finding.rule_id)

    assert emitted, (
        "no rule ids were emitted against the live corpus, so this assertion is "
        "vacuous. Either the corpus was deleted or the validators regressed."
    )
    unregistered = sorted(emitted - REGISTERED_RULE_IDS)
    assert not unregistered, (
        f"validators emit rule ids absent from the contract registry: {unregistered}. "
        "An unregistered rule id is both undocumented (#299) and invisible to "
        "cross-downstream aggregation (#301)."
    )
