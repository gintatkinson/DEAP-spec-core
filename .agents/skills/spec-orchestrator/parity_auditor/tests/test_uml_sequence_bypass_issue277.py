"""Regression tests for issue #277.

``uml.py`` defined ``bypass_suffixes = ("Actor", "Calculator", "Provider", "Mapper",
"Manager", "Configurator", "Architect", "Validator", "ValidatorSystem", "System")``
and skipped the global class registry check for any lifeline classifier ending in one.

The second-order effect was worse than the first. Because a bypassed classifier never
enters ``global_classes``, the downstream guard ``if rx_cls in global_classes:`` was
also false, so **every message sent to that lifeline had its operation signature
validated not at all**. One bypass silently disabled two checks.

This violates ``.pipeline/constitution.md`` § *Universal Model Consistency Rules*:
"No class, component, interface, attribute, operation, signal, or message may be used
in dynamic behavior specifications unless it is explicitly defined in the structural
models."

Note on coverage: ``docs/user-stories/`` contains no files, so this code path has no
live inputs and the fix rests entirely on the synthetic fixtures below.
"""

import json
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.validators.uml import UmlValidator  # noqa: E402
from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402

FENCE = "`" * 3

_SECTIONS = [["## UML Class Diagram", "UML Class Diagram"]]

# Config shaped after test_uml_validator.py's convention, trimmed to what the
# sequence-diagram path needs. Without required_sections the validator emits
# "System Error: Missing ... config" and never reaches lifeline validation.
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
    "validation_rules": {
        "visibility_prefixes": ["+", "-", "#", "~"],
        "multiplicity_regex": "\\[[^\\]]+\\]",
        "uml_primitives": ["String", "Integer", "Real", "Boolean"],
        "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
        "choice_stereotypes": ["<<choice>>"],
        "sequence_replies": ["-->", "--x"],
        "required_sections": {
            "feature_ui": _SECTIONS,
            "feature": _SECTIONS,
            "user_story": [["## UML Sequence Diagram", "UML Sequence Diagram"]],
            "use_case": _SECTIONS,
        },
        "required_diagrams": {"feature": ["classDiagram"], "user_story": ["sequenceDiagram"]},
    },
}

# A class that IS defined in a feature class diagram.
DEFINED_FEATURE = f"""---
generation_mode: subagent
title: "Payment Record"
type: "feature"
interface_type: ui
schema_containers:
  - path: "mod:payments/record"
    node_type: container
---

# Feature: Payment Record

## UML Class Diagram
{FENCE}mermaid
classDiagram
    class PaymentRoot {{
    }}
    class PaymentRecord {{
        +String reference
        +Boolean settle(String reference)
    }}
    PaymentRoot *-- PaymentRecord : record
{FENCE}
"""


def _story(classifier, operation="settle(reference: String)"):
    return f"""---
generation_mode: subagent
title: "Settle a payment"
type: "user-story"
---

# User Story: Settle a payment

## UML Sequence Diagram
{FENCE}mermaid
sequenceDiagram
    autonumber
    actor payer as "payer : Payer"
    participant target as "target : {classifier}"
    payer->>target: {operation}
    target-->payer: status : Status
{FENCE}
"""


_RUN_SEQ = [0]


def _run(tmp_path, story_text):
    # Unique workspace per invocation: the suffix-sweep test calls this repeatedly
    # with the same tmp_path fixture and would otherwise collide on mkdir.
    _RUN_SEQ[0] += 1
    ws = tmp_path / f"ws{_RUN_SEQ[0]}"
    (ws / "schema").mkdir(parents=True)
    (ws / "schema" / "model.yang").write_text("module m {}", encoding="utf-8")

    pipeline = ws / ".pipeline" / "logical-ui"
    pipeline.mkdir(parents=True)
    (pipeline / "codebase_rules.json").write_text(json.dumps(RULES), encoding="utf-8")

    (ws / "docs" / "epics").mkdir(parents=True)
    (ws / "docs" / "use-cases").mkdir(parents=True)

    feats = ws / "docs" / "features"
    feats.mkdir(parents=True)
    (feats / "feat-01-payment-record.md").write_text(DEFINED_FEATURE, encoding="utf-8")

    stories = ws / "docs" / "user-stories"
    stories.mkdir(parents=True)
    (stories / "us-01-settle.md").write_text(story_text, encoding="utf-8")

    repo = WorkspaceRepository(workspace_dir=str(ws))
    validator = UmlValidator()
    global_classes = {
        "PaymentRoot": {"attributes": [], "methods": []},
        "PaymentRecord": {
            "attributes": [{"name": "reference", "type": "String", "visibility": "+"}],
            "methods": [{"name": "settle", "visibility": "+", "params": ["String reference"]}],
        },
    }
    return validator.validate(repo, global_classes=global_classes)


# --------------------------------------------------------------------------- #
# Guard: a defined classifier must NOT be flagged, or the tests below could
# pass against a validator that rejects everything.
# --------------------------------------------------------------------------- #

def test_defined_classifier_is_accepted(tmp_path):
    errors = _run(tmp_path, _story("PaymentRecord"))
    offending = [e for e in errors if "PaymentRecord" in e and "not defined" in e]
    assert not offending, (
        f"a classifier defined in a feature class diagram must be accepted: {offending}"
    )


# --------------------------------------------------------------------------- #
# #277 - the bypass must be gone
# --------------------------------------------------------------------------- #

def test_undefined_manager_classifier_is_rejected_issue277(tmp_path):
    """'PaymentManager' ends with the former bypass suffix 'Manager'."""
    errors = _run(tmp_path, _story("PaymentManager"))
    assert any("PaymentManager" in e and "not defined" in e for e in errors), (
        "a lifeline classifier ending in 'Manager' that appears in no feature class "
        f"diagram must be rejected. The bypass suffix list allowed it. Errors: {errors}"
    )


def test_every_former_bypass_suffix_is_now_checked_issue277(tmp_path):
    """All ten former suffixes, so none is reinstated piecemeal."""
    former = (
        "Actor", "Calculator", "Provider", "Mapper", "Manager",
        "Configurator", "Architect", "Validator", "ValidatorSystem", "System",
    )
    unchecked = []
    for suffix in former:
        classifier = f"Undefined{suffix}"
        errors = _run(tmp_path, _story(classifier))
        if not any(classifier in e and "not defined" in e for e in errors):
            unchecked.append(suffix)
    assert not unchecked, (
        f"these former bypass suffixes still evade the registry check: {unchecked}"
    )


def test_messages_to_an_undefined_lifeline_are_not_silently_accepted_issue277(tmp_path):
    """The second-order effect: a bypassed receiver skipped operation validation too.

    The lifeline itself must be reported. Previously neither the lifeline nor the
    bogus operation produced any error at all.
    """
    errors = _run(tmp_path, _story("PaymentManager", operation="nonExistentOp(x: String)"))
    assert errors, (
        "a sequence diagram naming an undefined classifier and calling an undefined "
        "operation on it must produce at least one error; previously it produced none"
    )
    assert any("PaymentManager" in e for e in errors), (
        f"the undefined receiver classifier must be named in the errors: {errors}"
    )


def test_bypass_suffix_list_is_absent_from_the_source_issue277():
    """Pin the removal, so the tuple cannot be quietly reinstated."""
    src_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "parity_auditor", "validators", "uml.py"
    )
    with open(src_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    assert "bypass_suffixes" not in source, (
        "the bypass_suffixes tuple must not be reintroduced; it silently exempted "
        "lifelines and their messages from the Universal Model Consistency rule"
    )


# --------------------------------------------------------------------------- #
# Option B semantics: exemption keys on UML role, not name spelling
# --------------------------------------------------------------------------- #

def _actor_story(classifier):
    return f"""---
generation_mode: subagent
title: "Settle a payment"
type: "user-story"
---

# User Story: Settle a payment

## UML Sequence Diagram
{FENCE}mermaid
sequenceDiagram
    autonumber
    actor external as "external : {classifier}"
    participant record as "record : PaymentRecord"
    external->>record: settle(reference: String)
    record-->external: status : Status
{FENCE}
"""


def test_external_actors_are_exempt_regardless_of_name_issue277(tmp_path):
    """An `actor` is outside the system boundary, so it is correctly absent from the
    structural models. This is the false-positive class that commit a5de5f8 fixed and
    that option C would have reinstated."""
    still_flagged = []
    for classifier in ("Payer", "HumanOperator", "ThirdPartyBank", "PaymentHandler"):
        errors = _run(tmp_path, _actor_story(classifier))
        if any(classifier in e and "not defined" in e for e in errors):
            still_flagged.append(classifier)
    assert not still_flagged, (
        f"external actor lifelines must be exempt whatever they are called: {still_flagged}"
    )


def test_participant_is_required_even_with_an_exempt_sounding_name_issue277(tmp_path):
    """The mirror of the test above, and the whole point of option B.

    'PaymentManager' was exempt under the suffix list purely because of its spelling.
    Declared as a participant it is an internal object and must resolve.
    """
    errors = _run(tmp_path, _story("PaymentManager"))
    assert any("PaymentManager" in e and "not defined" in e for e in errors), (
        f"a participant must resolve regardless of its name ending: {errors}"
    )


def test_operation_signature_check_is_reachable_again_issue277(tmp_path):
    """The second-order defect, now closed.

    Previously a bypassed classifier never entered global_classes, so the guard
    `if rx_cls in global_classes:` was false and operation validation was skipped for
    every message sent to it. A defined participant carrying a bogus operation proves
    that check is live.
    """
    story = _story("PaymentRecord", operation="noSuchOperation(x: String)")
    errors = _run(tmp_path, story)
    assert any("noSuchOperation" in e for e in errors), (
        "an undefined operation on a defined participant must be reported; this is the "
        f"check the suffix bypass silently disabled. Errors: {errors}"
    )
