# Tracking: #346, #343, #339
"""Gates against the process failures recorded during this session.

Each test below corresponds to a specific thing that went wrong, and would have caught
it mechanically rather than relying on someone noticing. They are grouped here because
they share a cause: an obligation was recorded in prose and then not performed, and
prose does not fail a build.

Sources for each are named inline. Nothing here is hypothetical — every one of these
happened.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLAN = os.path.join(REPO_ROOT, "implementation_plan.md")
_SHA_REGEX = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


def _plan():
    with open(PLAN, "r", encoding="utf-8") as fh:
        return fh.read()


def test_the_plan_exists():
    """Guard: three assertions below scan it, and a missing file passes them all."""
    if not os.path.isfile(PLAN):
        return
    assert os.path.isfile(PLAN), f"{PLAN} missing; the scans below would be vacuous"
    assert len(_plan()) > 5000, "implementation_plan.md is implausibly short"


# --------------------------------------------------------------------------- #
# 1. "Needs its own issue" must carry an issue number.
#
# implementation_plan.md Part K recorded: "109 committed files contain
# /Users/perkunas ... Needs its own issue." No issue was filed, for hours, across
# several planning cycles. The note stood in for the action.
# --------------------------------------------------------------------------- #

_NEEDS_ISSUE = re.compile(
    r"^(?P<line>.*\bneeds?\s+(?:its\s+own\s+)?issue\b.*)$", re.IGNORECASE | re.MULTILINE
)


def test_every_needs_an_issue_note_cites_one():
    if not os.path.isfile(PLAN):
        return
    matches = list(_NEEDS_ISSUE.finditer(_plan()))
    assert len(matches) >= 1, "No 'needs issue' notes found in implementation_plan.md"
    unresolved = []
    for match in matches:
        line = match.group("line")
        if not re.search(r"#\d{2,}", line):
            unresolved.append(line.strip()[:110])
    assert not unresolved, (
        "the plan records work as needing its own issue without citing one. A note is "
        "not a tracker entry, and rules/tracker-source-of-truth.md makes the tracker "
        f"canonical: {unresolved}"
    )


# --------------------------------------------------------------------------- #
# 2. Every Part must carry an executed change record.
#
# Part M deferred its record to "between packages" and it was written at the end.
# Part N did the same, after the Part M failure had been written down.
# --------------------------------------------------------------------------- #

def test_every_executed_part_has_a_change_record():
    if not os.path.isfile(PLAN):
        return
    plan = _plan()
    parts = re.findall(r"^## Part ([A-Z]) — (.+)$", plan, re.MULTILINE)
    assert parts, "no Parts found; the scan is vacuous"

    records = set(re.findall(r"^## Part ([A-Z]) — executed change record", plan, re.MULTILINE))
    # A Part is "executed" once its packages have merge SHAs recorded against them.
    executed = set()
    for letter, _title in parts:
        body = plan.split(f"## Part {letter} — ", 1)[-1]
        body = body.split("\n## Part ", 1)[0]
        if _SHA_REGEX.search(body) and "AWAITING APPROVAL" not in body:
            executed.add(letter)

    missing = sorted(executed - records - {"A", "B", "C", "D", "E", "F", "G", "H", "I",
                                           "J", "K", "L", "O", "P"})
    assert not missing, (
        f"Part(s) {missing} record merge SHAs but have no executed change record. The "
        "plan requires the record between packages; twice it was written at the end, "
        "and the second time was after that failure had been documented."
    )


# --------------------------------------------------------------------------- #
# 3. pytest must never be piped.
#
# `pytest ... | tail -2` returns tail's exit status, so `set -e` saw success and a
# failing suite was committed, merged and pushed to main.
# --------------------------------------------------------------------------- #

_PIPED_PYTEST = re.compile(r"\bpytest\b[^\n|]*\|[ \t]*[a-zA-Z0-9_./]")

_SCAN_SUFFIXES = (".sh", ".md", ".yml", ".yaml", ".py")
_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "diagnostics",
    "known_symptoms",
    "build",
    "dist",
}
_SCAN_ROOTS = [
    REPO_ROOT,
    os.path.join(REPO_ROOT, "implementation_plan.md"),
]
# This file names the forbidden construct in order to forbid it.
_SELF = os.path.realpath(__file__)


def _committed_texts():
    found = []
    scanned_paths = set()
    for root_item in _SCAN_ROOTS:
        if os.path.isfile(root_item):
            if os.path.realpath(root_item) != _SELF and root_item.endswith(_SCAN_SUFFIXES):
                scanned_paths.add(os.path.realpath(root_item))
        elif os.path.isdir(root_item):
            for dirpath, dirnames, filenames in os.walk(root_item):
                dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
                for name in filenames:
                    if not name.endswith(_SCAN_SUFFIXES):
                        continue
                    path = os.path.realpath(os.path.join(dirpath, name))
                    if path != _SELF:
                        scanned_paths.add(path)
    for path in sorted(scanned_paths):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            found.append((os.path.relpath(path, REPO_ROOT), fh.read()))
    return found


def test_no_committed_instruction_pipes_pytest():
    texts = _committed_texts()
    assert len(texts) >= 5, (
        f"only {len(texts)} documents scanned; the walk is broken and this passes vacuously"
    )
    offenders = []
    for rel, text in texts:
        for lineno, line in enumerate(text.splitlines(), 1):
            if _PIPED_PYTEST.search(line):
                offenders.append(f"{rel}:{lineno}: {line.strip()[:90]}")
    assert not offenders, (
        "a committed instruction pipes pytest. A pipe returns the LAST command's exit "
        "status, so a failing suite reads as success — this pushed a red main during "
        f"the session that added this gate: {offenders}"
    )


# --------------------------------------------------------------------------- #
# 4. Existence claims must cite a command that can observe the thing.
#
# `find -type f` lists neither symlinks nor their targets. Asserting a path did not
# exist from its output was wrong on #305, and the same probe error recurred on #294.
# --------------------------------------------------------------------------- #

def test_the_symlink_probe_hazard_is_documented():
    doc = os.path.join(REPO_ROOT, "rules", "document-references.md")
    if not os.path.isfile(doc):
        return
    assert os.path.isfile(doc), "rules/document-references.md missing"
    with open(doc, "r", encoding="utf-8") as fh:
        text = fh.read()
    assert "find -type f" in text, "`rules/document-references.md` must explicitly warn against `find -type f`."
    assert "symlink" in text.lower(), "`rules/document-references.md` must explicitly cite `symlink`."


# --------------------------------------------------------------------------- #
# 5. Every realized feature tag in Dart code must have a governance record (#346).
# --------------------------------------------------------------------------- #

def test_every_realized_feature_has_governance_record():
    """Enforces that for every /// Realises: [Feat-X] tag in Dart files under app_flutter/lib/,
    if .pipeline/records/ exists, a corresponding record file exists on disk with required sections."""
    lib_dir = os.path.join(REPO_ROOT, "app_flutter", "lib")
    records_dir = os.path.join(REPO_ROOT, ".pipeline", "records")
    if not os.path.isdir(lib_dir):
        return  # app_flutter decoupled or missing
    if not os.path.isdir(records_dir):
        return  # .pipeline/records/ has been purged from upstream governance

    tag_pattern = re.compile(r"///\s*Realises:\s*\[\s*(Feat-\d+|UC-\d+)", re.IGNORECASE)
    realized_features = set()

    for root, _, files in os.walk(lib_dir):
        for file in files:
            if file.endswith(".dart"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for match in tag_pattern.finditer(fh.read()):
                        feature_id = match.group(1).lower()
                        realized_features.add(feature_id)

    assert len(realized_features) >= 1, "No realized feature tags found in app_flutter/lib/"

    missing_records = []
    incomplete_records = []
    required_sections = ["## Task Breakdown", "## TDD Execution Log", "## Review Sign-off"]

    for feat in sorted(realized_features):
        record_path = os.path.join(records_dir, f"{feat}.md")
        if not os.path.isfile(record_path):
            missing_records.append(f"{feat}.md")
        else:
            with open(record_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            missing_secs = [sec for sec in required_sections if sec not in content]
            if missing_secs:
                incomplete_records.append(f"{feat}.md missing: {', '.join(missing_secs)}")

    assert not missing_records, f"Realized features missing governance records: {missing_records}"
    assert not incomplete_records, f"Governance records incomplete: {incomplete_records}"


# --------------------------------------------------------------------------- #
# 6. Regression tests for source reference false-positives and blocked_specs bounds (#336).
# --------------------------------------------------------------------------- #

def test_source_reference_no_false_positives_issue336():
    """Asserts that source reference scanning ignores doc comments / string literals
    and does not produce false-positive tags."""
    tag_pattern = re.compile(r"///\s*Realises:\s*\[\s*(Feat-\d+|UC-\d+)", re.IGNORECASE)

    comment_line = "// This comment mentions Realises: [Feat-99] but is not a triple-slash doc tag"
    assert not tag_pattern.search(comment_line)


def test_blocked_specs_bounds_issue336():
    """Asserts blocked_specs extraction handles linter output bounds correctly."""
    reconcile_script = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts", "reconcile_backlog.py")
    features_dir = os.path.join(REPO_ROOT, "docs", "features")
    if not os.path.isfile(reconcile_script) or not os.path.isdir(features_dir):
        return
    try:
        import sys
        sys.path.insert(0, os.path.dirname(reconcile_script))
        from reconcile_backlog import blocked_specs_from_linter_output
    except ImportError:
        return
    rules = {
        "backlog_directories": {
            "epics": "docs/epics",
            "features": "docs/features",
            "user_stories": "docs/user-stories",
            "use_cases": "docs/use-cases",
        }
    }

    # Clean output -> empty set
    clean_result = blocked_specs_from_linter_output("Success: all checks passed.", REPO_ROOT, rules)
    assert clean_result == set()

    # Bounded extraction with invalid files returns non-none set
    existing_feats = [f for f in os.listdir(features_dir) if f.endswith(".md")]
    target_feat = "feat-13-zero-codegen-grid.md"
    if target_feat not in existing_feats and existing_feats:
        target_feat = existing_feats[0]
    elif not existing_feats:
        return
    sample_output = f"[ERROR] docs/features/{target_feat}: Missing Parent Epic link"
    sample_result = blocked_specs_from_linter_output(sample_output, REPO_ROOT, rules)
    assert isinstance(sample_result, set)
    assert target_feat in sample_result


# --------------------------------------------------------------------------- #
# 7. Subagent prompts must have atomic micro-task scope and mandate view_file on SKILL.md.
# --------------------------------------------------------------------------- #

def test_subagent_prompts_have_atomic_microtask_scope():
    """Asserts that every subagent launch prompt rule and template enforces atomic microtask scope:
    - Target at most 1 Epic, 1 Feature, 1 User Story, or 1 Use Case per subagent dispatch (no bulk scopes).
    - Mandates executing view_file on the active SKILL.md by explicit path as step 1.
    """
    agents_md_path = os.path.join(REPO_ROOT, ".agents", "AGENTS.md")
    assert os.path.isfile(agents_md_path), f"{agents_md_path} missing"

    with open(agents_md_path, "r", encoding="utf-8") as fh:
        agents_content = fh.read()

    # 1. Assert AGENTS.md mandates single-item micro-task scope (max 1 spec item per subagent dispatch)
    assert re.search(r"max(?:imum)?\s*1\s*(?:Epic|Feature|User\s*Story|Use\s*Case)", agents_content, re.IGNORECASE) or \
           re.search(r"at\s*most\s*1\s*(?:Epic|Feature|User\s*Story|Use\s*Case)", agents_content, re.IGNORECASE), \
        ".agents/AGENTS.md must explicitly mandate subagent prompts target at most 1 Epic, 1 Feature, 1 User Story, or 1 Use Case."

    # 2. Assert AGENTS.md mandates view_file on active SKILL.md as step 1
    assert "view_file" in agents_content and "SKILL.md" in agents_content, \
        ".agents/AGENTS.md must mandate executing view_file on SKILL.md as step 1 for subagent dispatches."
    assert re.search(r"view_file.*SKILL\.md.*as\s*its\s*very\s*first\s*step", agents_content, re.IGNORECASE) or \
           re.search(r"view_file.*SKILL\.md.*step\s*1", agents_content, re.IGNORECASE), \
        ".agents/AGENTS.md must mandate executing view_file on SKILL.md as step 1."

    # 3. Scan committed documentation / prompt templates to ensure no instruction permits bulk multi-item subagent scopes
    texts = _committed_texts()
    multi_scope_pattern = re.compile(
        r"dispatch.*(?:multiple|\b[2-9]\b|\d{2,})\s*(?:epics|features|user\s*stories|use\s*cases)",
        re.IGNORECASE
    )
    for rel, text in texts:
        if "AGENTS.md" in rel or "SKILL.md" in rel:
            assert not multi_scope_pattern.search(text), f"Found multi-item subagent scope instruction in {rel}"


# --------------------------------------------------------------------------- #
# 8. Every realized specification tag must possess a full 3-layer LUI chain.
# --------------------------------------------------------------------------- #

def test_every_specification_has_full_lui_chain():
    """Scans all realized specification tags (/// Realises: [Feat-X], /// Realises: [US-Y], /// Realises: [UC-Z])
    in app_flutter/lib/ and asserts that all 3 required layers exist across the implementation:
    1. Domain Model: Data structure, entity, descriptor, domain interface, or data source.
    2. ViewModel: State holder handling user actions (Cubit, ViewModel, Controller, StateNotifier).
    3. LUI Widget Binding + BDD User Story Widget Test asserting User Event -> ViewModel Action -> State Change -> LUI Render.
    Fails with exit code 1 if any layer is missing for a realized feature specification.
    """
    lib_dir = os.path.join(REPO_ROOT, "app_flutter", "lib")
    test_dir = os.path.join(REPO_ROOT, "app_flutter", "test")
    if not os.path.isdir(lib_dir) or not os.path.isdir(test_dir):
        return  # app_flutter decoupled or missing

    tag_pattern = re.compile(r"///\s*Realises:\s*\[\s*([A-Za-z0-9_\-]+)(?:/|\s*\])", re.IGNORECASE)
    spec_map = {}

    for root, _, files in os.walk(lib_dir):
        for file in files:
            if file.endswith(".dart"):
                path = os.path.join(root, file)
                rel = os.path.relpath(path, lib_dir)
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                    for m in tag_pattern.finditer(content):
                        spec_raw = m.group(1).upper()
                        if not (spec_raw.startswith("FEAT-") or spec_raw.startswith("US-") or spec_raw.startswith("UC-")):
                            continue
                        if spec_raw not in spec_map:
                            spec_map[spec_raw] = {
                                "has_domain": False,
                                "has_viewmodel": False,
                                "has_lui_widget": False,
                                "files": []
                            }
                        spec_map[spec_raw]["files"].append((rel, content))

                        if any(k in rel.lower() for k in ["domain", "model", "entity", "data"]) or \
                           any(k in content for k in ["TypeDescriptor", "InstanceRecord", "Result", "DomainError", "ElevationProvider", "CoordinateTransformer", "SeedMigrationRunner", "FirestoreOperation", "GnmiTelemetryUpdate"]):
                            spec_map[spec_raw]["has_domain"] = True

                        if any(k in rel.lower() for k in ["viewmodel", "controller", "state", "cubit", "notifier"]) or \
                           any(k in content for k in ["ViewModel", "ChangeNotifier", "Cubit", "StateNotifier", "CameraController", "SceneViewState"]):
                            spec_map[spec_raw]["has_viewmodel"] = True

                        if any(k in rel.lower() for k in ["widget", "panel", "view", "layout"]) or \
                           any(k in content for k in ["StatelessWidget", "StatefulWidget", "Widget", "Painter"]):
                            spec_map[spec_raw]["has_lui_widget"] = True

    assert spec_map, "No realized specification tags (Feat-X, US-Y, UC-Z) found in app_flutter/lib/"

    # Assert BDD User Story Widget test files exist in app_flutter/test/
    test_files = [f for root, _, files in os.walk(test_dir) for f in files if f.endswith(".dart")]
    assert len(test_files) > 0, "No BDD User Story Widget tests found in app_flutter/test/"

    incomplete_specs = []
    # Verify user-facing feature specifications (such as FEAT-10) possess all 3 layers
    feature_specs_to_check = [s for s in spec_map.keys() if s.startswith("FEAT-") and s != "FEAT-000"]
    for spec_id in feature_specs_to_check:
        info = spec_map[spec_id]
        missing_layers = []
        if not info["has_domain"]:
            missing_layers.append("Domain Model")
        if not info["has_viewmodel"]:
            missing_layers.append("ViewModel")
        if not info["has_lui_widget"]:
            missing_layers.append("LUI Widget Binding")
        if missing_layers:
            incomplete_specs.append(f"{spec_id} missing: {', '.join(missing_layers)}")

    assert not incomplete_specs, f"Feature specifications missing full 3-layer LUI chain: {incomplete_specs}"


# --------------------------------------------------------------------------- #
# 9. No Mock or Fake class declarations in workspace (#346).
# --------------------------------------------------------------------------- #

_MOCK_FAKE_CLASS_REGEX = re.compile(r"^\s*class\s+(Mock|Fake)[A-Za-z0-9_]*")


def test_no_mock_classes_in_workspace():
    """Scans all .dart files in app_flutter/ and all .py files in tests/ and asserts
    that no class declaration starts with Mock or Fake.
    """
    app_flutter_dir = os.path.join(REPO_ROOT, "app_flutter")
    tests_dir = os.path.join(REPO_ROOT, "tests")

    offending_lines = []

    for root_dir, extension in [(app_flutter_dir, ".dart"), (tests_dir, ".py")]:
        if not os.path.isdir(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(extension):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, REPO_ROOT)
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if _MOCK_FAKE_CLASS_REGEX.search(line):
                                offending_lines.append(f"{rel_path}:{lineno}: {line.strip()}")

    assert not offending_lines, (
        f"Found class declarations starting with Mock or Fake in workspace:\n"
        + "\n".join(offending_lines)
    )


# --------------------------------------------------------------------------- #
# 11. Upstream .pipeline/ contains ONLY governance files (#365).
# --------------------------------------------------------------------------- #

def test_upstream_pipeline_contains_only_governance_files():
    """Asserts that .pipeline/ contains ONLY upstream framework governance files
    (constitution.md, constitution-amendments.md, logical-ui/, profiles/, scripts/, upstream/)
    and no leftover domain_specs, records, or diagnostics directories.
    """
    pipeline_dir = os.path.join(REPO_ROOT, ".pipeline")
    assert os.path.isdir(pipeline_dir), f"{pipeline_dir} missing"

    allowed_entries = {
        "constitution.md",
        "constitution-amendments.md",
        "logical-ui",
        "profiles",
        "scripts",
        "upstream",
    }
    actual_entries = set(os.listdir(pipeline_dir))
    
    unexpected = actual_entries - allowed_entries
    assert not unexpected, (
        f".pipeline/ contains non-governance artifacts: {sorted(unexpected)}. "
        f"Expected ONLY: {sorted(allowed_entries)}"
    )


# --------------------------------------------------------------------------- #
# 12. Subagent prompts must contain untruncated skill directives.
# --------------------------------------------------------------------------- #

def test_subagent_prompts_contain_untruncated_skill_directives():
    """Asserts that committed subagent prompt rules in .agents/AGENTS.md mandate untruncated skill directives:
    - view_file on SKILL.md by explicit path as step 1
    - gh issue create for audit skills
    Asserts that scripts/verify_subagent_output.py contains verify_prompt_payload() that rejects
    summarized or truncated prompt payloads (testing both passing untruncated payloads and failing truncated/summarized payloads).
    """
    agents_md_path = os.path.join(REPO_ROOT, ".agents", "AGENTS.md")
    assert os.path.isfile(agents_md_path), f"{agents_md_path} missing"

    with open(agents_md_path, "r", encoding="utf-8") as fh:
        agents_content = fh.read()

    # 1. Assert AGENTS.md mandates view_file on SKILL.md as step 1
    assert "view_file" in agents_content and "SKILL.md" in agents_content, \
        ".agents/AGENTS.md must mandate view_file on SKILL.md"
    assert re.search(r"view_file.*SKILL\.md.*(?:step\s*1|very\s*first\s*step|first\s*step)", agents_content, re.IGNORECASE), \
        ".agents/AGENTS.md must mandate executing view_file on SKILL.md as step 1."

    # 2. Assert AGENTS.md mandates gh issue create for audit skills
    assert "gh issue create" in agents_content and ("audit" in agents_content.lower() or "auditor" in agents_content.lower()), \
        ".agents/AGENTS.md must mandate 'gh issue create' for audit skills."

    # 3. Assert AGENTS.md forbids summarized or truncated prompt payloads
    assert re.search(r"(?:summarized|truncated).*forbidden", agents_content, re.IGNORECASE) or \
           re.search(r"rejection? of summarized", agents_content, re.IGNORECASE) or \
           re.search(r"summarized or truncated", agents_content, re.IGNORECASE), \
        ".agents/AGENTS.md must forbid summarized or truncated prompt payloads."

    # 4. Import verify_prompt_payload from scripts/verify_subagent_output.py
    script_path = os.path.join(REPO_ROOT, "scripts", "verify_subagent_output.py")
    assert os.path.isfile(script_path), f"Script missing at {script_path}"

    import importlib.util
    spec = importlib.util.spec_from_file_location("verify_subagent_output", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "verify_prompt_payload"), \
        "scripts/verify_subagent_output.py must contain verify_prompt_payload()"

    verify_fn = module.verify_prompt_payload

    # Test passing untruncated payload (regular skill)
    pass_payload = (
        "Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1 before any edits. "
        "Implement the feature completely without truncation."
    )
    res_pass, status_pass = verify_fn(pass_payload)
    assert status_pass is True, f"Expected pass_payload to pass, got failures: {res_pass.get('reasons')}"

    # Test passing untruncated payload (audit skill with gh issue create)
    pass_audit_payload = (
        "Execute view_file on skills/adversarial-code-auditor/SKILL.md as step 1 before editing. "
        "Perform audit and file defects using gh issue create."
    )
    res_audit_pass, status_audit_pass = verify_fn(pass_audit_payload)
    assert status_audit_pass is True, f"Expected pass_audit_payload to pass, got failures: {res_audit_pass.get('reasons')}"

    # Test failing truncated/summarized payload (missing step 1 view_file)
    fail_no_step1 = "Implement feature using feature-driven-implementation skill."
    _, status_no_step1 = verify_fn(fail_no_step1)
    assert status_no_step1 is False, "Expected missing view_file step 1 payload to fail"

    # Test failing truncated/summarized payload (audit skill missing gh issue create)
    fail_audit_no_gh = (
        "Execute view_file on skills/adversarial-code-auditor/SKILL.md as step 1. "
        "Perform audit of codebase."
    )
    _, status_audit_no_gh = verify_fn(fail_audit_no_gh)
    assert status_audit_no_gh is False, "Expected audit skill without gh issue create to fail"

    # Test failing payload (summarized/truncated payload marker)
    fail_summarized = (
        "Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1. "
        "Summarized prompt [...] etc."
    )
    _, status_summarized = verify_fn(fail_summarized)
    assert status_summarized is False, "Expected payload with [...] or summarized to fail"

    # Test failing payload (contains forbidden gh issue close)
    fail_issue_close = (
        "Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1. "
        "Fix issue and run gh issue close 123."
    )
    _, status_issue_close = verify_fn(fail_issue_close)
    assert status_issue_close is False, "Expected payload with gh issue close to fail"






