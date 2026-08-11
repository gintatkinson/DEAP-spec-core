"""Integrity gate for the constitution amendment protocol.

The constitution is the Tier 1 governing document, yet before this gate existed it had
a weaker change process than the Tier 2 implementation profiles: profiles had a full
add/update/remove/list lifecycle, the constitution had one sentence. The result was
that the safe default became refusal, and two known defects stayed unfixed because
there was no described way to amend it safely.

This makes the audit trail mandatory rather than aspirational. The checksum of
``.pipeline/constitution.md`` must match the newest entry in
``.pipeline/constitution-amendments.md``, so **any** unlogged edit — by a human, by an
agent, or by a merge — fails the suite.

That is a deliberate trade. Allowing an agent to amend the constitution reduces a
safety property; making every change attributable and detectable is what makes the
reduction acceptable.
"""

import hashlib
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONSTITUTION = os.path.join(REPO_ROOT, ".pipeline", "constitution.md")
AMENDMENT_LOG = os.path.join(REPO_ROOT, ".pipeline", "constitution-amendments.md")

REQUIRED_FIELDS = (
    "Date", "Logged", "Motivating issue", "Approved by",
    "Destructive", "Line count", "Resulting SHA-256",
)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _entries():
    """Parse amendment entries in file order. Returns a list of (id, fields, body)."""
    content = _read(AMENDMENT_LOG)
    chunks = re.split(r"^## AMEND-(\d+)", content, flags=re.M)[1:]
    parsed = []
    for i in range(0, len(chunks), 2):
        amend_id, body = chunks[i], chunks[i + 1]
        fields = {}
        for name in REQUIRED_FIELDS:
            m = re.search(
                rf"^- \*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", body, re.M
            )
            if m:
                fields[name] = m.group(1).strip().strip("`")
        parsed.append((amend_id, fields, body))
    return parsed


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

def test_constitution_and_log_both_exist():
    assert os.path.isfile(CONSTITUTION), f"missing {CONSTITUTION}"
    assert os.path.isfile(AMENDMENT_LOG), (
        f"missing {AMENDMENT_LOG}. The constitution may not be changed without an "
        "amendment log to record it."
    )


def test_log_contains_at_least_the_baseline_entry():
    entries = _entries()
    assert entries, (
        "no AMEND-nnnn entries parsed from the amendment log; the checksum assertion "
        "below would be vacuous"
    )


# --------------------------------------------------------------------------- #
# The core assertion: no unlogged change
# --------------------------------------------------------------------------- #

def test_constitution_checksum_matches_newest_amendment():
    entries = _entries()
    amend_id, fields, _ = entries[-1]
    logged = fields.get("Resulting SHA-256")
    actual = _sha256(CONSTITUTION)
    assert logged, f"AMEND-{amend_id} has no 'Resulting SHA-256' field"
    assert logged == actual, (
        f"constitution.md has been modified without a logged amendment.\n"
        f"  newest log entry : AMEND-{amend_id} -> {logged}\n"
        f"  file on disk     : {actual}\n"
        "Append an entry via project-constitution Step 9, recording the motivating "
        "issue and the verbatim human approval, or revert the edit."
    )


# --------------------------------------------------------------------------- #
# Entry completeness and provenance
# --------------------------------------------------------------------------- #

def test_every_entry_carries_all_required_fields():
    problems = []
    for amend_id, fields, _ in _entries():
        for name in REQUIRED_FIELDS:
            if name not in fields:
                problems.append(f"AMEND-{amend_id} missing '{name}'")
    assert not problems, (
        "amendment entries are incomplete, so the trail is not auditable: " + str(problems)
    )


def test_every_entry_records_approval_provenance():
    """An amendment without recorded approval is indistinguishable from an unapproved one."""
    problems = []
    for amend_id, fields, _ in _entries():
        approved = fields.get("Approved by", "")
        if not approved:
            problems.append(f"AMEND-{amend_id}: empty")
        elif approved.startswith("n/a") and len(approved) < 12:
            problems.append(f"AMEND-{amend_id}: 'n/a' without a stated reason")
    assert not problems, f"entries lacking approval provenance: {problems}"


def test_last_updated_matches_the_newest_amendment_date():
    _, fields, _ = _entries()[-1]
    m = re.search(r'^last_updated:\s*"?([^"\n]+)"?', _read(CONSTITUTION), re.M)
    assert m, "constitution frontmatter has no last_updated field"
    assert m.group(1).strip() == fields.get("Date"), (
        f"constitution last_updated is {m.group(1).strip()!r} but the newest amendment "
        f"records Date {fields.get('Date')!r}. Bump last_updated when amending."
    )


# --------------------------------------------------------------------------- #
# Cumulative, never destructive (project-constitution Mandate 3)
# --------------------------------------------------------------------------- #

def test_non_destructive_amendments_do_not_shrink_the_constitution():
    entries = _entries()
    problems = []
    previous = None
    for amend_id, fields, body in entries:
        try:
            count = int(fields.get("Line count", "").split()[0])
        except (ValueError, IndexError):
            problems.append(f"AMEND-{amend_id}: unparseable Line count")
            continue
        destructive = fields.get("Destructive", "").lower().startswith("yes")
        if previous is not None and not destructive and count < previous:
            problems.append(
                f"AMEND-{amend_id}: line count fell {previous} -> {count} but is not "
                "flagged Destructive. Mandate 3 requires amendments to be cumulative."
            )
        if destructive and len(body.strip()) < 200:
            problems.append(
                f"AMEND-{amend_id}: flagged Destructive without a justification "
                "paragraph explaining what was removed and why"
            )
        previous = count
    assert not problems, str(problems)


def test_current_line_count_matches_newest_entry():
    _, fields, _ = _entries()[-1]
    actual = len(_read(CONSTITUTION).splitlines())
    assert str(actual) == fields.get("Line count"), (
        f"constitution has {actual} lines but the newest amendment records "
        f"{fields.get('Line count')!r}"
    )


def test_traceability_rules_name_enforcing_validators():
    content = _read(CONSTITUTION)
    expected_rules = [
        "Every Epic MUST reference the specification section(s) it covers. Enforced by parity_auditor/validators/uml.py via required sections configuration.",
        "Enforced by parity_auditor/validators/uml.py via required_sections configuration in codebase_rules.json.",
        "Every User Story MUST link to the Features it validates. Enforced by parity_auditor/validators/uml.py via Required Features Matrix validation.",
        "Every Use Case MUST link to the User Stories and Features it realizes. Enforced by parity_auditor/validators/uml.py via Realization Matrix validation.",
    ]
    for rule_pattern in expected_rules:
        assert rule_pattern in content, (
            f"Constitution traceability section is missing expected enforcing validator rule anchor: {rule_pattern!r}"
        )


def test_title_normalization_clause_updated():
    content = _read(CONSTITUTION)
    expected_clause = (
        "Matching by title normalization is the primary selector used by the backlog reconciliation tool. "
        "To prevent collisions, all specification files of the same spec type MUST have unique normalised titles, "
        "as enforced by parity_auditor/validators/spec_title_uniqueness_validator.py and rules/tracker-source-of-truth.md."
    )
    assert expected_clause in content, (
        "Constitution is missing the updated title normalization clause."
    )
    assert "prohibited as a primary selector" not in content, (
        "Constitution still contains 'prohibited as a primary selector'."
    )


def test_three_tier_architecture_section_and_mermaid_diagram():
    content = _read(CONSTITUTION)
    assert "## Architecture: Three-Tier Platform Isolation" in content, (
        "Constitution is missing top-level '## Architecture: Three-Tier Platform Isolation' section."
    )
    assert "```mermaid" in content, "Constitution is missing Mermaid diagram code fence."
    assert "graph TD" in content, "Constitution is missing 'graph TD' Mermaid diagram header."
    assert "subgraph" in content, "Constitution Mermaid diagram is missing subgraphs for tiers."


def test_source_references_mandated_for_all_spec_types():
    content = _read(CONSTITUTION)
    expected_clause = (
        "Every Feature MUST include a 'Source References' section with verbatim specification clause numbers and schema paths. "
        "Every Epic, User Story, and Use Case MUST also carry a 'Source References' section (or Realization / Target Features Matrix linking to upstream sources). "
        "Enforced by parity_auditor/validators/uml.py via required_sections configuration in codebase_rules.json."
    )
    assert expected_clause in content, (
        "Constitution Traceability section is missing explicit Source References mandate for Epic, Feature, User Story, and Use Case."
    )


def test_all_15_enforced_quality_gates_table_in_constitution():
    content = _read(CONSTITUTION)
    gates_and_enforcers = [
        ("Specification Validation", "validators/spec_validator.py"),
        ("Model Coverage Verification", "scripts/verify_model_coverage.py"),
        ("Cross-Reference Integrity", "validators/link_validator.py"),
        ("Human Approval", "rules/user-authorization-lock.md"),
        ("Downstream Conformance", "scripts/verify_downstream_baseline.py"),
        ("UML Model Integrity", "validators/uml.py"),
        ("Mermaid Syntax Constraints", "validators/mermaid_syntax_validator.py"),
        ("Behavioral Trigger Coverage", "validators/behavioral.py"),
        ("Codebase Compliance", "validators/codebase.py"),
        ("Document Cross-Reference Integrity", "tests/test_skill_path_references.py"),
        ("Constitution Amendment Integrity", "tests/test_constitution_integrity.py"),
        ("Specification File Integrity", "validators/docs.py"),
        ("Spec Title Uniqueness", "validators/spec_title_uniqueness_validator.py"),
        ("Source Reference Integrity", "validators/source_reference_validator.py"),
        ("Logical UI Validation", "validators/logical_ui_validator.py"),
    ]
    for gate_name, enforcer_path in gates_and_enforcers:
        assert gate_name in content, f"Constitution missing quality gate: {gate_name}"
        assert enforcer_path in content, f"Constitution missing enforcing validator path: {enforcer_path} for gate {gate_name}"


def test_labeling_taxonomy_contains_spec_operational_and_state_labels():
    content = _read(CONSTITUTION)
    assert "Specification labels:" in content, "Constitution missing 'Specification labels:' under Labeling Taxonomy"
    assert "Operational labels:" in content, "Constitution missing 'Operational labels:' under Labeling Taxonomy"
    assert "State labels:" in content, "Constitution missing 'State labels:' under Labeling Taxonomy"
    assert "codebase_rules.json" in content, "Constitution Labeling Taxonomy missing reference to codebase_rules.json"
    for label in ["`epic`", "`feature`", "`user-story`", "`use-case`", "`bug`", "`enhancement`", "`chore`", "`status:fixed-resolved`"]:
        assert label in content, f"Constitution missing label: {label}"


def test_cmmi_level_3_process_area_mapping_table_in_constitution():
    content = _read(CONSTITUTION)
    assert "CMMI Level 3 Process Area Mapping" in content, (
        "Constitution missing 'CMMI Level 3 Process Area Mapping' table/header."
    )
    process_areas = [
        ("Requirements Management (REQM)", "tracker-source-of-truth.md"),
        ("Verification (VER)", "verify_model_coverage.py"),
        ("Validation (VAL)", "Closed"),
        ("Configuration Management (CM)", "constitution-amendments.md"),
        ("Technical Solution (TS)", "3-Layer LUI Definition of Done"),
        ("Product Integration (PI)", "verify_downstream_baseline.py"),
    ]
    for pa_name, ref_artifact in process_areas:
        assert pa_name in content, f"Constitution CMMI Level 3 mapping missing Process Area: {pa_name}"
        assert ref_artifact in content, f"Constitution CMMI Level 3 mapping missing reference artifact: {ref_artifact}"


def test_granularity_bounds_normative_rfc2119_and_enforcers():
    content = _read(CONSTITUTION)
    assert "### Granularity Bounds" in content, (
        "Constitution missing '### Granularity Bounds' section under Specification Standards."
    )
    epic_bound = (
        "An Epic SHOULD contain 3-15 Features. Epics exceeding 15 Features MUST be split "
        "by the schema-specification-engineering worker during Step 1 decomposition; "
        "Epics with fewer than 3 Features MUST be reviewed for consolidation. "
        "Enforced by schema-specification-engineering decomposition heuristics."
    )
    feature_bound = (
        "A Feature SHOULD carry 3-10 acceptance criteria. Features exceeding 10 acceptance "
        "criteria MUST be split into targeted sub-features; Features with fewer than 3 "
        "acceptance criteria MUST be expanded to ensure full scenario coverage. "
        "Enforced by parity_auditor/validators/cardinality_validator.py and spec worker review gates."
    )
    assert epic_bound in content, (
        "Constitution missing normative RFC 2119 Epic granularity bound and enforcer statement."
    )
    assert feature_bound in content, (
        "Constitution missing normative RFC 2119 Feature granularity bound and enforcer statement."
    )


def test_amend_0014_lumi_framework_in_constitution():
    content = _read(CONSTITUTION)
    amendment_log = _read(AMENDMENT_LOG)
    assert "AMEND-0014" in amendment_log, "AMEND-0014 missing from constitution-amendments.md"
    assert "Logical User & Machine Interface" in content or "LUMI" in content, (
        "Constitution missing LUMI (Logical User & Machine Interface) Framework definition."
    )

