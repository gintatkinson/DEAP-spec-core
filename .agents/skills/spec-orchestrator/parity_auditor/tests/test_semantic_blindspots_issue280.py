"""Regression tests for issue #280 — claimed semantic blindspots in validation.

#280 reports that string-and-regex validation produces "massive false positives" and
"massive false negatives", and prescribes replacing the architecture with an
**LLM-as-a-Judge** semantic evaluator.

The prescription is not implementable as a blocking gate.
`.pipeline/upstream/pipeline-tooling.md` § *Validation Gates* requires blocking gates to
be offline and dependency-free, states that a gate calling a third-party service fails
when that service is down or rate-limits, and adds that sending specification content to
a third party is a confidentiality concern. An LLM judge is all three: network-dependent,
third-party, and fed the specification text. It is available as an optional non-blocking
smoke check, which is what the profile allows, but it cannot be the gate.

The two *defects* named are a different matter, and both are already covered — by
issue #281's placeholder detection and by the BDD check matching content rather than a
heading. This file pins that coverage so it cannot regress silently, which is the real
risk: the issue would then be reopened against a gate that had quietly lost the checks.

Each assertion below corresponds to an example #280 gives verbatim.
"""

import json
import os
import re
import sys

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parity_auditor.validators.uml import (  # noqa: E402
    CONDITIONAL_STUB_PATTERNS,
    find_unresolved_placeholders,
)

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
RULES = os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "codebase_rules.json")
PROFILE = os.path.join(REPO_ROOT, ".pipeline", "upstream", "pipeline-tooling.md")

# Verbatim from #280: "the scripts blindly approve specifications where the actual
# content beneath the headers is *(None)* or (semantic linkage justification)".
CLAIMED_FALSE_POSITIVES = (
    "*(None)*",
    "*(none)*",
    "(semantic linkage justification)",
    "- [ ] #[EpicID] - [Epic Title](epic-XX-name.md)",
)

# Verbatim from #280: "the scripts fail valid specifications if they utilize allowed
# variant headers (e.g. ## BDD Scenario (OOA/OOD Realization))".
CLAIMED_FALSE_NEGATIVE_HEADERS = (
    "## BDD Scenario (OOA/OOD Realization)",
    "## Given-When-Then Acceptance Criteria",
    "## Acceptance Criteria",
)


def _bdd_patterns():
    with open(RULES, "r", encoding="utf-8") as fh:
        rules = json.load(fh)
    pats = rules.get("validation_rules", {}).get("bdd_scenario_regexes") or []
    assert pats, "guard: no BDD patterns configured; the assertions below are vacuous"
    return pats


def test_unconditional_placeholders_are_rejected_issue280():
    """Template text that is never legitimate, whatever the document contains."""
    for probe in ("(semantic linkage justification)",
                  "- [ ] #[EpicID] - [Epic Title](epic-XX-name.md)"):
        hits = list(find_unresolved_placeholders(
            f"## Associated Use Cases\n{probe}\n"
        ))
        assert hits, (
            f"{probe!r} passed validation. #280's false-positive claim would be live: "
            "a linkage section containing only template text would be approved."
        )


def test_none_stub_is_rejected_when_items_exist_issue280():
    """`*(None)*` is caught — conditionally, which is stronger than #280 assumes.

    Issue #239 established the distinction: "*(None registered)*" is a truthful
    statement when nothing is registered, and a lie once something is. The patterns are
    therefore gated on the caller's knowledge of what exists, rather than banned
    outright. #280 reads the un-gated pass as a blindspot; it is a deliberate
    conditional that needs context, not semantics.
    """
    for probe in ("*(None)*", "*(none)*", "*(None registered)*", "*(TBD)*"):
        hits = list(find_unresolved_placeholders(
            f"## Associated Use Cases\n{probe}\n", CONDITIONAL_STUB_PATTERNS
        ))
        assert hits, (
            f"{probe!r} is not recognised as a stub even when the caller knows "
            "matching items exist, so a specification could claim nothing is "
            "registered while the tracker says otherwise"
        )


def test_real_content_is_not_mistaken_for_a_placeholder_issue280():
    """Positive control: over-eager placeholder matching is its own defect.

    This control is what caught a vacuous first draft of this file:
    ``find_unresolved_placeholders`` returns a **generator**, which is always truthy,
    so every assertion of the form ``assert not find(...)`` silently passed. Results
    are materialised with ``list()`` throughout for that reason.
    """
    genuine = (
        "## Associated Use Cases\n"
        "- [ ] #42 - [Register Node](https://example.invalid/docs/use-cases/uc-01.md) "
        "(covers the registration path this Epic introduces)\n"
    )
    assert not list(find_unresolved_placeholders(genuine)), (
        "genuine linkage content was flagged as a placeholder; a gate that rejects "
        "correct output gets switched off"
    )
    assert not list(find_unresolved_placeholders(genuine, CONDITIONAL_STUB_PATTERNS)), (
        "genuine linkage content matched a conditional stub pattern"
    )


def test_variant_bdd_headers_do_not_cause_a_false_negative_issue280():
    """The false-negative claim, which does not hold.

    The check matches the scenario *content*, not the heading, so the heading may be
    worded however the author likes. #280 assumed a header match.
    """
    patterns = _bdd_patterns()
    for header in CLAIMED_FALSE_NEGATIVE_HEADERS:
        doc = f"{header}\n**Given** a node\n**When** it is selected\n**Then** it shows\n"
        assert any(re.search(p, doc, re.DOTALL | re.IGNORECASE) for p in patterns), (
            f"a User Story using the heading {header!r} was not recognised as carrying "
            "a BDD scenario, so #280's false-negative claim would be live"
        )


def test_a_document_with_no_scenario_at_all_still_fails_issue280():
    """Positive control: accepting any heading must not mean accepting empty content."""
    patterns = _bdd_patterns()
    doc = "## BDD Scenario (OOA/OOD Realization)\n\n*(To be written)*\n"
    assert not any(re.search(p, doc, re.DOTALL | re.IGNORECASE) for p in patterns), (
        "a section with no scenario content was accepted as a BDD scenario, which "
        "would make the check vacuous"
    )


def test_an_llm_judge_cannot_be_a_blocking_gate_issue280():
    """The prescribed remedy is excluded by the profile, not by preference."""
    assert os.path.isfile(PROFILE), f"{PROFILE} missing; this assertion is vacuous"
    with open(PROFILE, "r", encoding="utf-8") as fh:
        profile = fh.read()
    assert "Blocking gates MUST be **offline and dependency-free**" in profile, (
        "the offline-gate requirement is gone from pipeline-tooling.md, which is the "
        "only reason #280's LLM-as-a-Judge remedy was rejected. If it was removed "
        "deliberately, #280 deserves reopening on the new terms."
    )
    assert "third-party renderer or API" in profile, (
        "the confidentiality clause forbidding specification content being sent to a "
        "third party is gone; same consequence as above"
    )
