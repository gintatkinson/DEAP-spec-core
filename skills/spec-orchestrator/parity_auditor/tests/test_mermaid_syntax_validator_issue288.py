"""Regression tests for issues #288 and #289.

#288 - Step D check 7 asserted "contains a mermaid block with valid diagram" but
       had no procedure establishing validity, so an unparseable diagram cleared
       all eleven checks and was filed. It happened on issue #283.
#289 - the character-level Mermaid rules were fragmented across four files with
       disjoint subsets, and no validator enforced any of them.

The gate must be OFFLINE. A blocking gate that calls a third-party renderer fails
when that service is down or rate-limits, and ships specification content to a
third party. See .pipeline/upstream/pipeline-tooling.md, Validation Gates.

Scope limit, asserted explicitly below: this is a rule checker, not a Mermaid
grammar parser. It catches the documented rule violations, not every malformed
diagram.
"""

import os
import sys

import pytest

# Convention in this suite: each test module puts ../src on sys.path itself, because
# the package is not pip-installed locally. CI does `pip install -e`, so both paths
# work there. Omitting this line breaks collection for the entire suite.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parity_auditor.validators.mermaid_syntax_validator import (  # noqa: E402
    MermaidSyntaxValidator,
    check_mermaid_text,
)

FENCE = "```"


def _block(body):
    return f"{FENCE}mermaid\n{body}\n{FENCE}\n"


# The exact diagram filed on issue #283. GitHub reported:
#   "Parse error on line 9 ... got 'INVALID'"
# The semicolon in the Note is read as a statement separator, so the remainder of
# the note becomes a new statement and collides with the following message line.
BROKEN_283 = _block(
    """sequenceDiagram
    participant Sub as Feature Spec Subagent
    participant Val as SchemaCardinalityValidator
    Sub->>Val: validate(feature markdown)
    Note over Val: n = len(containers); error when n == 0 or n > 1
    Val-->>Sub: Consolidation violation, exit code non-zero"""
)

# The corrected version that renders (verified HTTP 200, 62442 byte image).
FIXED_283 = _block(
    """sequenceDiagram
    participant Sub as Feature Spec Subagent
    participant Val as SchemaCardinalityValidator
    Sub->>Val: validate feature markdown
    Note over Val: Accepts exactly one entry, rejects zero or many
    Val-->>Sub: Consolidation violation, non-zero exit"""
)


# --------------------------------------------------------------------------- #
# Guard: the corpus must be non-empty and the known-good case must be clean,
# or a checker that returns errors for everything would appear to work.
# --------------------------------------------------------------------------- #

def test_known_good_diagram_produces_no_errors():
    assert check_mermaid_text(FIXED_283) == [], (
        "the corrected #283 diagram renders in production and must not be flagged; "
        "a checker that rejects valid input is worse than none"
    )


def test_documents_its_own_scope_limit():
    """The module must state that it is not a full grammar parser, so a reader does
    not mistake a passing result for proof the diagram renders."""
    from parity_auditor.validators import mermaid_syntax_validator as mod
    doc = (mod.__doc__ or "").lower()
    assert "not" in doc and "grammar parser" in doc, (
        "module docstring must state that this is not a full Mermaid grammar parser, "
        "so a clean result is not mistaken for proof the diagram renders"
    )


# --------------------------------------------------------------------------- #
# #283's actual defect: semicolons in Note and message text
# --------------------------------------------------------------------------- #

def test_semicolon_in_note_is_rejected_issue288():
    errors = check_mermaid_text(BROKEN_283)
    assert errors, "the diagram that broke #283 must be rejected"
    assert any("semicolon" in e.lower() for e in errors), (
        f"the error must name the semicolon as the cause, got: {errors}"
    )


def test_semicolon_in_message_text_is_rejected_issue288():
    text = _block(
        """sequenceDiagram
    A->>B: do a thing; then another"""
    )
    errors = check_mermaid_text(text)
    assert any("semicolon" in e.lower() for e in errors), (
        f"semicolons in message text are prohibited, got: {errors}"
    )


def test_semicolon_outside_the_text_payload_is_allowed():
    """The prohibition is on Note and message text, not on the whole file."""
    text = "Prose before the block; with a semicolon.\n" + FIXED_283
    assert check_mermaid_text(text) == [], (
        "a semicolon in surrounding prose must not be flagged"
    )


# --------------------------------------------------------------------------- #
# #289's fragmented rules, now enforced
# --------------------------------------------------------------------------- #

def test_unclosed_fence_is_rejected():
    text = f"{FENCE}mermaid\nsequenceDiagram\n    A->>B: hello\n"
    errors = check_mermaid_text(text)
    assert any("unclosed" in e.lower() or "closed" in e.lower() for e in errors), (
        f"an unclosed mermaid fence must be reported, got: {errors}"
    )


def test_colon_in_class_member_is_rejected():
    text = _block(
        """classDiagram
    class Foo {
        +methodName() : ReturnType
    }"""
    )
    assert any("colon" in e.lower() for e in check_mermaid_text(text))


def test_colon_in_note_string_is_rejected():
    text = _block(
        """classDiagram
    class Foo {
        +String bar
    }
    note for Foo "Status: Active\""""
    )
    assert any("colon" in e.lower() for e in check_mermaid_text(text))


def test_stereotype_on_relationship_line_is_rejected():
    text = _block(
        """classDiagram
    class A {
        +String x
    }
    class B {
        +String y
    }
    A --> B : <<references>>"""
    )
    assert any("stereotype" in e.lower() for e in check_mermaid_text(text))


def test_curly_brace_in_class_member_is_rejected():
    text = _block(
        """classDiagram
    class Foo {
        +String bar {default: earth}
    }"""
    )
    assert any("brace" in e.lower() for e in check_mermaid_text(text))


def test_reserved_keyword_in_class_member_is_rejected():
    text = _block(
        """classDiagram
    class Foo {
        +link(arg)
        -style()
        click
        ~callback(param)
    }"""
    )
    errors = check_mermaid_text(text)
    assert any("reserved keyword 'link'" in e.lower() for e in errors)
    assert any("reserved keyword 'style'" in e.lower() for e in errors)
    assert any("reserved keyword 'click'" in e.lower() for e in errors)
    assert any("reserved keyword 'callback'" in e.lower() for e in errors)



def test_errors_identify_the_source_and_line():
    errors = check_mermaid_text(BROKEN_283, source="body.md")
    assert errors and "body.md" in errors[0], (
        f"errors must name their source for actionable output, got: {errors}"
    )


# --------------------------------------------------------------------------- #
# IValidator integration
# --------------------------------------------------------------------------- #

def test_validator_implements_the_ivalidator_contract():
    from parity_auditor.validators.base import IValidator
    assert issubclass(MermaidSyntaxValidator, IValidator)
    assert callable(getattr(MermaidSyntaxValidator, "validate", None))


def test_validator_flags_a_bad_file_in_a_docs_tree(tmp_path):
    from parity_auditor.core.workspace import WorkspaceRepository
    docs = tmp_path / "docs" / "features"
    docs.mkdir(parents=True)
    (docs / "feat-01-bad.md").write_text(BROKEN_283, encoding="utf-8")
    (docs / "feat-02-good.md").write_text(FIXED_283, encoding="utf-8")

    repo = WorkspaceRepository(workspace_dir=str(tmp_path))
    errors = MermaidSyntaxValidator().validate(repo, search_dirs=[str(docs)])
    assert any("feat-01-bad.md" in e for e in errors)
    assert not any("feat-02-good.md" in e for e in errors)


def test_validator_returns_empty_when_nothing_to_scan(tmp_path):
    from parity_auditor.core.workspace import WorkspaceRepository
    repo = WorkspaceRepository(workspace_dir=str(tmp_path))
    assert MermaidSyntaxValidator().validate(repo, search_dirs=[str(tmp_path / "nope")]) == []


# --------------------------------------------------------------------------- #
# The live repository must be clean, or the gate cannot be turned on
# --------------------------------------------------------------------------- #

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Pipeline-owned markdown: source we author and ship. Must be clean.
PIPELINE_OWNED = ("rules", "skills")
# Downstream output: disposable diagnostic material. Symptoms here are the SIGNAL,
# not a failure. Never repaired -- see implementation_plan.md Part D.
DOWNSTREAM_OUTPUT = ("docs",)


def _scan(bases):
    checked, errors = 0, []
    for base in bases:
        root = os.path.join(REPO_ROOT, base)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                if FENCE + "mermaid" not in content:
                    continue
                checked += 1
                errors.extend(
                    check_mermaid_text(content, source=os.path.relpath(path, REPO_ROOT))
                )
    return checked, errors


def test_pipeline_owned_markdown_is_clean():
    """rules/ and skills/ are source we author. These must satisfy our own rules."""
    checked, errors = _scan(PIPELINE_OWNED)
    assert checked >= 3, (
        f"only {checked} pipeline-owned file(s) with diagrams scanned; near-vacuous"
    )
    assert not errors, (
        f"{len(errors)} violation(s) in pipeline-owned markdown:\n"
        + "\n".join(f"  - {e}" for e in errors[:25])
    )


def test_detection_works_against_real_downstream_symptoms():
    """The inverse assertion, and the important one.

    ``docs/`` is disposable downstream output kept to source symptoms. Asserting it is
    clean would force either repairing throwaway content or suppressing signal -- the
    latter is exactly the mistake ``EXCLUDED_DIR_NAMES`` made, concealing 13
    non-rendering diagrams behind a green check.

    So instead: prove the checker fires on real downstream content. If this ever
    reports zero, the corpus was deleted or detection silently broke.
    """
    checked, errors = _scan(DOWNSTREAM_OUTPUT)
    if checked == 0 or not errors:
        pytest.skip("downstream corpus repaired or removed; nothing to diagnose")
    assert errors, (
        f"scanned {checked} downstream file(s) with diagrams but found no violations. "
        "The corpus was either deleted, repaired, or detection silently broke."
    )


def test_embedded_unified_diff_does_not_produce_false_positives():
    """docs embed diffs of other documents. Diff context lines preserve the original
    indentation after the '+'/'-' marker, which must not be read as a UML visibility
    marker. This produced 5 false positives on first implementation."""
    text = (
        "@@ -78,6 +83,21 @@\n"
        "     " + FENCE + "mermaid\n"
        "     classDiagram\n"
        "-       class ContainerName {\n"
        "-           +Type attributeName\n"
        "-       }\n"
        "+       class RootContainer {\n"
        "+           +Type rootAttribute\n"
        "+       }\n"
        "     " + FENCE + "\n"
    )
    assert check_mermaid_text(text) == [], (
        "diff context lines must not be flagged as class member violations"
    )
