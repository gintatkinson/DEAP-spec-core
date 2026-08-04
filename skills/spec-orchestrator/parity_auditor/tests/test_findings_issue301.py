"""Tests for the Finding type (issue #301).

The type subclasses ``str`` specifically so ~172 existing assertions keep working. These
tests pin that compatibility, because if it regresses the failure surfaces as dozens of
unrelated test errors rather than as one clear message.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.core.findings import (  # noqa: E402
    Finding,
    rule_ids,
    unmigrated_count,
)


def _f(rule="demo-rule", msg="docs/a.md:3: something is wrong"):
    return Finding(rule, msg, location="docs/a.md:3", detail={"n": 4})


# --------------------------------------------------------------------------- #
# String compatibility — the reason the type subclasses str
# --------------------------------------------------------------------------- #

def test_finding_is_its_message():
    f = _f()
    assert str(f) == "docs/a.md:3: something is wrong"
    assert f == "docs/a.md:3: something is wrong"


def test_substring_containment_works():
    """Assertions of the form any("x" in e for e in errors) must keep working."""
    assert "something is wrong" in _f()


def test_join_works():
    """Several existing tests do " ".join(errors)."""
    joined = " ".join([_f(msg="first"), _f(msg="second")])
    assert joined == "first second"


def test_fstring_and_sorting_work():
    assert f"{_f(msg='abc')}" == "abc"
    assert sorted([_f(msg="b"), _f(msg="a")]) == ["a", "b"]


def test_mixed_list_of_findings_and_plain_strings_is_usable():
    """Un-migrated validators still return plain strings; both must coexist."""
    mixed = [_f(msg="structured"), "plain string error"]
    assert " ".join(mixed) == "structured plain string error"
    assert any("plain" in e for e in mixed)


# --------------------------------------------------------------------------- #
# The added behaviour
# --------------------------------------------------------------------------- #

def test_carries_rule_id_and_detail():
    f = _f()
    assert f.rule_id == "demo-rule"
    assert f.location == "docs/a.md:3"
    assert f.detail == {"n": 4}


def test_empty_rule_id_is_rejected():
    """A finding with no rule id never groups, so it defeats the type's purpose.
    Fail at construction rather than emitting an invisible row."""
    with pytest.raises(ValueError, match="requires a rule_id"):
        Finding("", "some message")


# --------------------------------------------------------------------------- #
# Signature — the cross-downstream grouping key
# --------------------------------------------------------------------------- #

def test_signature_ignores_downstream_specific_detail():
    """The same pipeline defect in two differently-named projects must collapse to one
    signature. This is the property the whole aggregator rests on."""
    project_a = Finding(
        "spec-filename-duplicate-ordinal",
        "docs/features: duplicate ordinal - 4 is claimed by 2 files (feat-04-a.md, feat-04-b.md)",
        location="docs/features",
    )
    project_b = Finding(
        "spec-filename-duplicate-ordinal",
        "specs/feat: duplicate ordinal - 11 is claimed by 3 files (feat-11-x.md, feat-11-y.md, feat-11-z.md)",
        location="specs/feat",
    )
    assert project_a.signature() == project_b.signature(), (
        "the same rule violated in two downstreams must share a signature, otherwise "
        "recurrence is scattered across rows and the signal is lost"
    )
    assert project_a != project_b, "the messages themselves must remain distinct"


def test_different_rules_do_not_collapse():
    assert _f(rule="rule-a").signature() != _f(rule="rule-b").signature()


# --------------------------------------------------------------------------- #
# Coverage helpers — migration progress must be visible, not assumed
# --------------------------------------------------------------------------- #

def test_rule_ids_extracts_only_structured_findings():
    mixed = [_f(rule="a"), _f(rule="b"), "plain", _f(rule="a")]
    assert rule_ids(mixed) == {"a", "b"}


def test_unmigrated_count_reports_plain_strings():
    assert unmigrated_count([_f(), "plain", "also plain"]) == 2
    assert unmigrated_count([_f(), _f()]) == 0
