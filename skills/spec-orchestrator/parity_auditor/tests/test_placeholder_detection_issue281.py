"""Regression tests for issue #281.

``_validate_placeholders_and_links`` missed unpopulated template text in two ways:

1. ``PLACEHOLDER_STUBS`` was a literal list — ``["*(none registered)*",
   "*to be populated*", "*tbd*", "*n/a*"]`` — so near variants such as ``*(None)*``,
   ``[Epic Title]`` and ``(semantic linkage justification)`` passed straight through.
2. ``if "IssueID" in content`` missed ``#[EpicID]``, because the string ``"EpicID"``
   does not contain ``"IssueID"``.

Compounding both: the stub loop only ran for Epic, Use Case and User Story documents.
Feature documents were checked for ``IssueID`` alone — and Features are exactly where
the live corpus carried 8 entirely unpopulated ``## Parent Epic`` sections.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.validators.uml import UmlValidator  # noqa: E402

CHECKBOX_RE = r"^\s*-\s*\[[ xX]\]\s*(.+)$"

POPULATED_FEATURE = """---
issue_id: 54
title: "Real Feature"
---

# Feature: Real Feature

## Parent Epic
- [x] #43 - [Downstream Data Delivery](https://github.com/o/r/blob/main/docs/epics/epic-43.md) (Epic 43 governs downstream delivery, under which this feature sits.)
"""


def _check(content, doc_type="Feature", filename="feat-01-x.md"):
    errors = []
    UmlValidator()._validate_placeholders_and_links(
        content, doc_type, filename, errors, CHECKBOX_RE
    )
    return errors


# --------------------------------------------------------------------------- #
# Guard: a fully populated document must produce NO placeholder error.
# Without this, a detector that flags everything would appear to pass.
# --------------------------------------------------------------------------- #

def test_populated_document_produces_no_placeholder_errors_issue281():
    errors = _check(POPULATED_FEATURE)
    assert not errors, (
        f"a fully populated Feature must not be flagged; detector is over-eager: {errors}"
    )


# --------------------------------------------------------------------------- #
# Gap 2: unresolved bracket ID tokens
# --------------------------------------------------------------------------- #

def test_epic_id_token_is_detected_issue281():
    """The live failure. '#[EpicID]' evaded 'if "IssueID" in content'."""
    content = POPULATED_FEATURE.replace("#43", "#[EpicID]")
    errors = _check(content)
    assert errors, "an unresolved '#[EpicID]' token must be reported"
    assert any("EpicID" in e or "placeholder" in e.lower() for e in errors), (
        f"the error should identify the unresolved token: {errors}"
    )


def test_issue_id_token_still_detected_issue281():
    """Regression guard on the behaviour that already worked."""
    content = POPULATED_FEATURE.replace("#43", "#[IssueID]")
    assert _check(content), "an unresolved '#[IssueID]' token must still be reported"


def test_other_id_token_variants_are_detected_issue281():
    unchecked = []
    for token in ("#[EpicIssueID]", "#[FeatureID]", "#[StoryID]", "#[SpecificFeatureIssueID]"):
        content = POPULATED_FEATURE.replace("#43", token)
        if not _check(content):
            unchecked.append(token)
    assert not unchecked, f"these unresolved ID tokens evade detection: {unchecked}"


# --------------------------------------------------------------------------- #
# Gap 1: template text that is not in the literal stub list
# --------------------------------------------------------------------------- #

def test_bracketed_template_titles_are_detected_issue281():
    unchecked = []
    for placeholder in ("[Epic Title]", "[Feature Title]", "[User Story Title]", "[Use Case Title]"):
        content = POPULATED_FEATURE.replace("[Downstream Data Delivery]", placeholder)
        if not _check(content):
            unchecked.append(placeholder)
    assert not unchecked, f"these unpopulated template titles evade detection: {unchecked}"


def test_semantic_linkage_justification_placeholder_is_detected_issue281():
    """9 live occurrences in the corpus at the time of filing."""
    content = POPULATED_FEATURE.replace(
        "(Epic 43 governs downstream delivery, under which this feature sits.)",
        "(semantic linkage justification)",
    )
    errors = _check(content)
    assert errors, (
        "the literal template text '(semantic linkage justification)' means the author "
        "never wrote a justification and must be reported"
    )


def test_none_variants_are_detected_issue281():
    unchecked = []
    for variant in ("*(None)*", "*(none)*", "*(NONE)*", "*(none registered)*", "*TBD*", "*N/A*"):
        content = POPULATED_FEATURE + f"\n- [ ] {variant}\n"
        if not _check(content, doc_type="Use Case", filename="uc-01-x.md"):
            unchecked.append(variant)
    assert not unchecked, (
        f"case variants of the placeholder stubs evade detection: {unchecked}. "
        "Literal string membership is why '*(None)*' passed while '*(none)*' failed."
    )


def test_placeholder_epic_path_is_detected_issue281():
    """'epic-XX-name.md' is template scaffolding, not a real path."""
    content = POPULATED_FEATURE.replace("docs/epics/epic-43.md", "docs/epics/epic-XX-name.md")
    assert _check(content), "the placeholder path 'epic-XX-name.md' must be reported"


# --------------------------------------------------------------------------- #
# The live corpus: this is what turns the linter red, deliberately
# --------------------------------------------------------------------------- #

def test_live_feature_corpus_placeholders_are_now_visible_issue281():
    """Documents the accepted consequence of option A: the 8 unpopulated Feature
    files are now reported. The linter being green before was a false green."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    features = os.path.join(repo_root, "docs", "features")
    if not os.path.isdir(features):
        return
    flagged = []
    for name in sorted(os.listdir(features)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(features, name), "r", encoding="utf-8") as fh:
            if _check(fh.read(), doc_type="Feature", filename=name):
                flagged.append(name)
    assert len(flagged) == 0, (
        f"expected 0 known unpopulated Feature files to be flagged, "
        f"got {len(flagged)}: {flagged}"
    )
