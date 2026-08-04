"""Regression tests for issues #320 and #322 — Source References integrity.

#322: during drafting a subagent rewrites an authoritative upstream locator
(`https://github.com/YangModels/...`) into a fabricated local one
(`https://github.com/<this repo>/blob/main/schema/...`). The prompt supplied the
upstream URL for retrieval but never required preserving it in the output.

#320: nothing catches that, because no gate extracts Markdown links at all.

**The gate is offline by mandate.** `.pipeline/upstream/pipeline-tooling.md`
§ *Validation Gates* requires blocking gates to be offline and dependency-free, and
forbids sending specification content to a third party. #320's text speaks of
"reachability"; reachability is NOT implemented and must not be — an HTTP-fetching
blocking gate fails whenever the far end is down or rate-limits, for reasons unrelated
to correctness, and leaks specification content.

What is checkable offline is the *structure* of the rewrite, which is what actually
catches #322: an entry describing an external artefact — a structural schema or a
normative specification — must not point at this repository. Those artefacts are
external by definition, so a self-referential URL is the rewrite, detectable with
certainty and no network.

Fixtures are built in `tmp_path`. The live `docs/` corpus is deliberately not used:
it carries 20+ pre-existing violations and `implementation_plan.md` Part D records it
as disposable symptom-source content that is never repaired.
"""

import os
import sys

SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src")
)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parity_auditor.core.workspace import WorkspaceRepository  # noqa: E402
from parity_auditor.validators.source_reference_validator import (  # noqa: E402
    SourceReferenceValidator,
)

UPSTREAM = "gintatkinson/digital-pipeline-repo"


def _workspace(tmp_path, features):
    """A minimal workspace with a features directory and a codebase_rules.json."""
    (tmp_path / ".pipeline" / "logical-ui").mkdir(parents=True)
    (tmp_path / ".pipeline" / "logical-ui" / "codebase_rules.json").write_text(
        '{"meta": {"upstream_repository": "%s"},'
        ' "backlog_directories": {"epics": "docs/epics", "features": "docs/features",'
        ' "user_stories": "docs/user-stories", "use_cases": "docs/use-cases"}}' % UPSTREAM
    )
    feat_dir = tmp_path / "docs" / "features"
    feat_dir.mkdir(parents=True)
    for name, body in features.items():
        (feat_dir / name).write_text(body)
    return WorkspaceRepository(str(tmp_path))


def _spec(source_refs):
    return (
        "---\ntitle: \"Geo Location\"\ntype: \"feature\"\n---\n\n"
        "# Feature: Geo Location\n\n"
        "## Source References\n" + source_refs + "\n"
    )


def test_the_scan_discovers_specifications(tmp_path):
    """Guard: a scan that finds nothing reports no violations and proves nothing."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "Structural Schema: [ietf-geo.yang](https://github.com/YangModels/yang/blob/main/ietf-geo.yang)"
    )})
    found = SourceReferenceValidator().collect_references(repo)
    assert found, "the reference scan discovered nothing; every assertion below is vacuous"


def test_authoritative_schema_url_rewritten_to_this_repo_is_rejected_issue322(tmp_path):
    """The #322 rewrite, structurally detected without a network call."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        f"Structural Schema: [ietf-geo.yang](https://github.com/{UPSTREAM}/blob/main/schema/ietf-geo.yang)"
    )})
    errors = SourceReferenceValidator().validate(repo)
    assert errors, (
        "a Structural Schema reference pointing at this repository is the #322 rewrite "
        "of an authoritative upstream locator, and was not reported"
    )
    assert any("self-referential" in str(e) or "upstream" in str(e) for e in errors), errors


def test_genuine_upstream_schema_url_is_accepted_issue322(tmp_path):
    """Positive control: the gate must not reject correct references."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "Structural Schema: [ietf-geo.yang](https://github.com/YangModels/yang/blob/main/ietf-geo.yang)\n"
        "Normative Specification: [RFC 9179](https://datatracker.ietf.org/doc/html/rfc9179)"
    )})
    assert SourceReferenceValidator().validate(repo) == []


def test_internal_relative_links_are_not_flagged_issue320(tmp_path):
    """Specs legitimately cite the constitution and profiles by relative path.

    Flagging every repo-internal link would reject the live corpus wholesale and the
    first response would be to switch the gate off.
    """
    (tmp_path / ".pipeline").mkdir(parents=True, exist_ok=True)
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "- **Project Constitution**: [constitution.md](../../.pipeline/constitution.md#L88-L94)"
    )})
    (tmp_path / ".pipeline" / "constitution.md").write_text("# c\n")
    assert SourceReferenceValidator().validate(repo) == []


def test_unresolved_template_placeholder_is_rejected_issue320(tmp_path):
    """`link-to-schema` ships in the SKILL.md template and must never survive."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "Structural Schema: [Target Schema File](link-to-schema) (Clause: [Clause Number])"
    )})
    errors = SourceReferenceValidator().validate(repo)
    assert errors, "an unpopulated template placeholder passed the gate"
    assert any("placeholder" in str(e) for e in errors), errors


def test_broken_relative_link_is_rejected_issue320(tmp_path):
    """A relative link naming a file that is not there is a dangling reference."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "- **Profile**: [react.md](../../.pipeline/profiles/react.md)"
    )})
    errors = SourceReferenceValidator().validate(repo)
    assert errors, "a relative link to a non-existent file passed the gate"
    assert any("does not exist" in str(e) for e in errors), errors


def test_no_network_call_is_made(monkeypatch, tmp_path):
    """The gate is offline by mandate; prove it never opens a socket."""
    import socket

    def _boom(*a, **k):
        raise AssertionError(
            "the gate attempted a network connection. pipeline-tooling.md "
            "§ Validation Gates requires blocking gates to be offline."
        )

    monkeypatch.setattr(socket.socket, "connect", _boom)
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        "Structural Schema: [x](https://github.com/YangModels/yang/blob/main/a.yang)"
    )})
    SourceReferenceValidator().validate(repo)


def test_every_emitted_finding_carries_a_rule_id(tmp_path):
    """Findings must aggregate; a bare string is invisible to the aggregator (#304)."""
    repo = _workspace(tmp_path, {"feat-01-geo.md": _spec(
        f"Structural Schema: [a](https://github.com/{UPSTREAM}/blob/main/schema/a.yang)"
    )})
    errors = SourceReferenceValidator().validate(repo)
    assert errors
    for e in errors:
        assert getattr(e, "rule_id", None), f"finding without a rule_id: {e!r}"
