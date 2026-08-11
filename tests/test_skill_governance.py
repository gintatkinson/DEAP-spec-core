"""Governance regression tests for skill instruction files.

Covers:
  #287 - the debug-protocol autonomous loop selected work by the ``bug`` label and
         could not stop until zero such issues remained, while Step 0 ordered an
         immediate halt on any selected item that was not a defect. Nothing
         relabelled or closed it, so the terminating condition was unsatisfiable.
         The upstream producer was adversarial-code-auditor Step E, which labelled
         every finding ``bug`` regardless of severity.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEBUG_PROTOCOL = os.path.join(REPO_ROOT, "skills", "debug-protocol", "SKILL.md")
AUDITOR = os.path.join(REPO_ROOT, "skills", "adversarial-code-auditor", "SKILL.md")


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_skill_files_are_discoverable():
    for path in (DEBUG_PROTOCOL, AUDITOR):
        assert os.path.isfile(path), f"skill file not found: {path}"


# --------------------------------------------------------------------------- #
# #287 - the loop must be able to terminate
# --------------------------------------------------------------------------- #

def test_debug_protocol_has_a_reclassification_branch_issue287():
    content = _read(DEBUG_PROTOCOL)
    assert re.search(r"--remove-label\s+bug", content), (
        "debug-protocol/SKILL.md must instruct the agent to relabel a non-defect off "
        "'bug' and continue, rather than halt. Without it the loop's exit condition "
        "cannot be satisfied."
    )
    assert re.search(r"reclassif", content, re.I), (
        "debug-protocol/SKILL.md must name the reclassification path explicitly"
    )


def test_debug_protocol_terminating_condition_is_qualified_issue287():
    content = _read(DEBUG_PROTOCOL)
    assert "ZERO unresolved bugs remaining in the repository backlog" not in content, (
        "the unqualified terminating condition must be replaced. It cannot be met "
        "while a non-defect retains the 'bug' label, and Step 0 forbids processing it."
    )
    assert re.search(r"Step 0 defect gate", content), (
        "the terminating condition must be qualified by the Step 0 defect gate, e.g. "
        "'no open issue labelled bug remains that passes the Step 0 defect gate'"
    )


def test_debug_protocol_explains_why_halting_is_not_an_option_issue287():
    """The 3-iteration skip is unreachable for a non-defect. Say so, or the next
    author will re-derive the halt."""
    content = _read(DEBUG_PROTOCOL)
    assert re.search(r"before iteration one", content, re.I), (
        "debug-protocol/SKILL.md should record that the 3-iteration skip does not "
        "rescue the loop because Step 0 halts before iteration one"
    )


# --------------------------------------------------------------------------- #
# #287 - stop the upstream producer of mislabelled inputs
# --------------------------------------------------------------------------- #

def test_auditor_does_not_hardcode_the_bug_label_issue287():
    content = _read(AUDITOR)
    assert '--label "bug"' not in content, (
        'adversarial-code-auditor/SKILL.md must not hardcode --label "bug" in Step E. '
        "Section 1.4 defines Suggestion as explicitly NOT a current bug, so labelling "
        "it 'bug' manufactures the inputs that deadlock debug-protocol."
    )


def test_auditor_maps_severity_to_label_issue287():
    content = _read(AUDITOR)
    assert "enhancement" in content, (
        "adversarial-code-auditor/SKILL.md Step E must map Suggestion and Nitpick "
        "findings to a non-bug label such as 'enhancement'"
    )
    mapping = re.search(r"Critical.{0,80}Important.{0,120}Suggestion", content, re.S)
    assert mapping, (
        "Step E must state an explicit severity-to-label mapping covering Critical, "
        "Important, Suggestion and Nitpick"
    )


# --------------------------------------------------------------------------- #
# Guard against the duplicate-numbering defect class seen in #283, and
# reintroduced accidentally while fixing #287.
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# #286 - the output template must satisfy the skill's own Step D check 5
#
# Step C:145 orders the subagent to copy the Section 2 skeleton "exactly", and
# Step D:171 forbids filing until every check passes. When the skeleton emitted
# '*' bullets and check 5 required '-', those two instructions were mutually
# unsatisfiable. These tests are deliberately self-referential: they read the
# regex out of the check-5 row and apply it to the skill's own blocks, so drift
# in either direction fails rather than one hardcoded marker.
# --------------------------------------------------------------------------- #

def _check5_regex():
    row = next(
        (l for l in _read(AUDITOR).splitlines() if "Section 1 bullets" in l), None
    )
    assert row, "Step D check 5 row not found in adversarial-code-auditor/SKILL.md"
    m = re.search(r"`([^`]+)`", row)
    assert m, f"no backtick-quoted regex in the check 5 row: {row!r}"
    return m.group(1)


def _context_section_blocks():
    """Every '## 1. Context and References' block and its bullet lines."""
    lines = _read(AUDITOR).splitlines()
    blocks = []
    for i, line in enumerate(lines):
        if line.strip().startswith("## 1. Context and References"):
            seg = []
            for nxt in lines[i + 1:i + 10]:
                if nxt.strip().startswith("##"):
                    break
                if nxt.strip():
                    seg.append(nxt)
            blocks.append(seg)
    return blocks


def test_check5_regex_is_extractable_issue286():
    """Guard: if this breaks, the two tests below prove nothing."""
    pattern = _check5_regex()
    re.compile(pattern)
    assert "File" in pattern and "Pillar" in pattern and "Symptom" in pattern
    blocks = _context_section_blocks()
    assert len(blocks) >= 2, (
        f"expected the skeleton and the worked example, found {len(blocks)} "
        "'## 1. Context and References' blocks"
    )


def test_skeleton_and_example_satisfy_check5_issue286():
    pattern = re.compile(_check5_regex())
    offenders = []
    for idx, block in enumerate(_context_section_blocks()):
        matched = [l for l in block if pattern.match(l)]
        if len(matched) != 3:
            offenders.append((idx, len(matched), block))
    assert not offenders, (
        "a '## 1. Context and References' block does not satisfy the skill's own "
        f"Step D check 5 regex {_check5_regex()!r}. Copying the skeleton exactly, as "
        f"Step C mandates, would produce a body that check 5 rejects: {offenders}"
    )


def test_check5_accepts_either_list_marker_issue286():
    """CommonMark treats '-' and '*' as equivalent, and both render identically.
    The verifier should not reject a body over a distinction the reader cannot see."""
    pattern = _check5_regex()
    for marker in ("-", "*"):
        assert re.match(pattern, f"{marker} **File**: `path.py:1-2`"), (
            f"check 5 regex {pattern!r} rejects the '{marker}' list marker; it should "
            "accept either, since both are valid CommonMark and render identically"
        )


def _ordered_list_runs(text):
    """Yield each maximal run of consecutive top-level numbered lines."""
    run = []
    for line in text.splitlines():
        m = re.match(r"^(\d+)\.\s", line)
        if m:
            run.append(int(m.group(1)))
        elif run and not line.strip():
            continue          # blank lines do not break a list
        elif run and re.match(r"^\s+", line):
            continue          # indented continuation does not break a list
        elif run:
            yield run
            run = []
    if run:
        yield run


def test_skill_numbered_lists_have_no_duplicate_ordinals():
    """An inserted step must renumber the ones after it.

    #283 was partly this defect in schema-specification-engineering. It recurred in
    adversarial-code-auditor Step E while fixing #287, so it is now pinned.
    """
    offenders = []
    for path in (DEBUG_PROTOCOL, AUDITOR):
        for run in _ordered_list_runs(_read(path)):
            if len(run) > 2 and len(set(run)) != len(run):
                dupes = sorted({n for n in run if run.count(n) > 1})
                offenders.append((os.path.basename(os.path.dirname(path)), run, dupes))
    assert not offenders, (
        "numbered lists contain repeated ordinals, so an inserted step did not "
        f"renumber its successors: {offenders}"
    )


# --------------------------------------------------------------------------- #
# #388 - Constructor integrity invariant and cross-cutting field preservation
# --------------------------------------------------------------------------- #

FEATURE_DRIVEN_IMPL = os.path.join(REPO_ROOT, "skills", "feature-driven-implementation", "SKILL.md")


def test_feature_driven_implementation_has_cross_cutting_field_preservation_invariant_issue388():
    content = _read(FEATURE_DRIVEN_IMPL)
    assert "Cross-Cutting Field Preservation" in content, (
        "feature-driven-implementation/SKILL.md Step 3.7 Invariants must contain "
        "'Cross-Cutting Field Preservation' mandate"
    )
    assert re.search(r"Cross-Cutting Field Preservation.*constructors.*copyWith.*valueWriters", content, re.S | re.I), (
        "feature-driven-implementation/SKILL.md Step 3.7 Invariants must mandate that "
        "all constructors, copyWith, and valueWriters preserve new fields when extending domain models"
    )


def test_feature_driven_implementation_has_model_integrity_check_spec_review_issue388():
    content = _read(FEATURE_DRIVEN_IMPL)
    assert "Model Integrity Check" in content, (
        "feature-driven-implementation/SKILL.md Step 3.3 Stage 1 Spec Compliance Review must contain "
        "'Model Integrity Check'"
    )
    assert re.search(r"Model Integrity Check.*constructor.*copyWith.*valueWriter", content, re.S | re.I), (
        "feature-driven-implementation/SKILL.md Step 3.3 Stage 1 Spec Compliance Review must verify that "
        "every constructor, copyWith, and valueWriter in the diff includes or passes through new fields"
    )


def test_feature_driven_implementation_has_constructor_integrity_regression_assertions_issue388():
    content = _read(FEATURE_DRIVEN_IMPL)
    assert re.search(r"Assertion-Based Automation.*regression assertions.*constructor.*copyWith.*valueWriter", content, re.S | re.I), (
        "feature-driven-implementation/SKILL.md Step 4.1 Assertion-Based Automation must mandate "
        "regression assertions on existing tests verifying field preservation through every constructor/copyWith/valueWriter path"
    )


# --------------------------------------------------------------------------- #
# #390 - Prohibit raw N/A strings in Logical UI & Layout Bindings
# --------------------------------------------------------------------------- #

SCHEMA_SPEC_ENG = os.path.join(REPO_ROOT, "skills", "schema-specification-engineering", "SKILL.md")
SPEC_USER_STORY_ENG = os.path.join(REPO_ROOT, "skills", "spec-user-story-engineering", "SKILL.md")
FLUTTER_PROFILE = os.path.join(REPO_ROOT, ".pipeline", "profiles", "flutter.md")
REACT_PROFILE = os.path.join(REPO_ROOT, ".pipeline", "profiles", "react.md")


def test_schema_spec_eng_prohibits_raw_na_lui_bindings_issue390():
    content = _read(SCHEMA_SPEC_ENG)
    assert ", or be `N/A`" not in content and ", or be N/A" not in content, (
        "schema-specification-engineering/SKILL.md must not allow ', or be N/A' as a valid binding option"
    )
    assert "MUST be `N/A`" not in content and "MUST be N/A" not in content, (
        "schema-specification-engineering/SKILL.md must not allow 'MUST be N/A' as a valid binding option"
    )


def test_spec_skills_mandate_unbound_deferred_lui_bindings_and_prohibit_placeholders():
    for path, name in ((SCHEMA_SPEC_ENG, "schema-specification-engineering"), (SPEC_USER_STORY_ENG, "spec-user-story-engineering")):
        content = _read(path)
        assert "Unbound (Deferred to Implementation Profile)" in content, (
            f"{name}/SKILL.md must mandate 'Unbound (Deferred to Implementation Profile)'"
        )
        assert "Deferred to Feature #X Task Y" not in content, (
            f"{name}/SKILL.md must not contain template placeholder string 'Deferred to Feature #X Task Y'"
        )
        assert "literal placeholder strings" in content or "prohibited" in content, (
            f"{name}/SKILL.md must instruct spec workers that literal placeholder strings are prohibited"
        )



def test_implementation_profiles_contain_lui_resolution_guidelines():
    for path, name in ((FLUTTER_PROFILE, "flutter.md"), (REACT_PROFILE, "react.md")):
        assert os.path.isfile(path), f"Profile file not found: {path}"
        content = _read(path)
        assert "## LUI Resolution Guidelines" in content, (
            f"{name} must contain '## LUI Resolution Guidelines' section"
        )
        assert "PropertyGrid" in content and "TableView" in content and "NumericSpinBox" in content, (
            f"{name} LUI Resolution Guidelines must instruct how to map to PropertyGrid, TableView, and NumericSpinBox"
        )


# --------------------------------------------------------------------------- #
# #391 - Replace literal Epic template placeholder with explicit token
# --------------------------------------------------------------------------- #

def test_schema_spec_eng_replaces_semantic_linkage_justification_placeholder_issue391():
    content = _read(SCHEMA_SPEC_ENG)
    assert "(semantic linkage justification)" not in content, (
        "schema-specification-engineering/SKILL.md must not contain literal '(semantic linkage justification)' placeholder"
    )
    assert '{{REQUIRED_JUSTIFICATION}}' in content or '[POPULATE:' in content, (
        "schema-specification-engineering/SKILL.md must contain explicit token '{{REQUIRED_JUSTIFICATION}}' or '[POPULATE:]'"
    )
    assert "EXPLICIT LINKAGE JUSTIFICATION TOKEN RULE" in content or "prohibiting literal placeholder text" in content or "replace all `[POPULATE:" in content or "replace all `{{REQUIRED_JUSTIFICATION}}`" in content, (
        "schema-specification-engineering/SKILL.md must contain explicit skill rule mandating subagents replace all justification tokens"
    )
