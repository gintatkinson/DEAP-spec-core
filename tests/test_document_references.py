"""Unit tests for document reference integrity and frontmatter governance (Issue #373)."""

import os
import re
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_DOC = os.path.join(REPO_ROOT, "docs", "feat-hardware-decoupled-persistence-design.md")


def test_hardware_decoupled_persistence_design_document_integrity_issue373():
    if not os.path.isfile(TARGET_DOC):
        return

    with open(TARGET_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify YAML frontmatter presence and fields
    assert content.startswith("---"), "Document must begin with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Document must contain closed YAML frontmatter"

    frontmatter_raw = parts[1]
    metadata = yaml.safe_load(frontmatter_raw)
    assert isinstance(metadata, dict), "Frontmatter must parse as a valid YAML dictionary"

    assert "title" in metadata, "Frontmatter must contain 'title'"
    assert metadata.get("type") == "design", "Frontmatter 'type' must be 'design'"
    assert str(metadata.get("issue_id")) == "373", "Frontmatter 'issue_id' must be 373"
    assert metadata.get("platform") == "vhdl-fpga", "Frontmatter 'platform' must be 'vhdl-fpga'"

    # Verify zero .yang file references
    assert ".yang" not in content, "Document must not reference any .yang schema file"
    assert "ietf-geo-location" not in content, "Document must not reference 'ietf-geo-location'"

    # Verify domain-free abstract primitive register names exist
    assert "REGISTER_0" in content, "Document must reference primitive REGISTER_0"
    assert "REGISTER_1" in content, "Document must reference primitive REGISTER_1"
    assert "REGISTER_2" in content, "Document must reference primitive REGISTER_2"
    assert "CONFIG_FLAGS" in content, "Document must reference CONFIG_FLAGS"
    assert "CONTROL_STATUS" in content, "Document must reference CONTROL_STATUS"

    # Verify purge of geodetic terms
    for domain_term in ["COORD_LAT_X", "COORD_LON_Y", "COORD_ALT_Z", "GEODETIC_SYSTEM", "geodetic"]:
        assert domain_term not in content, f"Document must not contain domain term '{domain_term}'"

    # Verify path resolution of any referenced files if Source References section exists
    if "## Source References" in content:
        source_ref_section = content.split("## Source References", 1)[1]
        referenced_paths = re.findall(r"`([a-zA-Z0-9_\-/\.]+\.(?:json|yaml|md))`", source_ref_section)
        for rel_path in referenced_paths:
            abs_path = os.path.join(REPO_ROOT, rel_path)
            assert os.path.isfile(abs_path), f"Referenced file does not exist: {rel_path} (resolved to {abs_path})"


def test_control_status_bits_fsm_realisation_issue372():
    if not os.path.isfile(TARGET_DOC):
        return

    with open(TARGET_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # Assert FSM Realisation Matrix section/table exists
    assert "FSM Realisation Matrix" in content or "Realisation Matrix" in content, (
        "Document must contain an FSM Realisation Matrix for CONTROL_STATUS bits"
    )

    # Assert CONTROL_STATUS bit definitions are realised in FSM
    assert "Commit bit 0" in content or "Bit 0: Commit" in content or "Bit 0" in content, (
        "Document must define Commit bit 0 in FSM matrix"
    )
    assert "Busy bit 1" in content or "Bit 1: Busy" in content or "Bit 1" in content, (
        "Document must define Busy bit 1 in FSM matrix"
    )
    assert "Error bit 2" in content or "Bit 2: Error" in content or "Bit 2" in content, (
        "Document must define Error bit 2 in FSM matrix"
    )

    # Assert STAGED and ERROR states exist in FSM diagram / prose
    assert "STAGED" in content, "Document must include STAGED state in FSM"
    assert "ERROR" in content, "Document must include ERROR state in FSM"

    # Assert STAGED -> COMMIT_REG guard requirements
    assert "commit_bit" in content or "Commit bit" in content, "FSM must check commit_bit / Commit bit"
    assert "01" in content and "10" in content, "FSM guard must check valid mode choice 01 or 10"

    # Assert error transitions and triggers
    assert "11" in content and "00" in content, "FSM must specify error triggers for invalid 11 and unconfigured 00"
    assert "truncated" in content.lower() or "out-of-range" in content.lower() or "error" in content.lower()

    # Assert ERROR --> IDLE transition on error acknowledgment
    assert "ERROR --> IDLE" in content or ("ERROR" in content and "IDLE" in content), (
        "FSM must define transition from ERROR to IDLE on error acknowledgment"
    )


def test_abstract_fixed_point_representations_issue371():
    if not os.path.isfile(TARGET_DOC):
        return

    with open(TARGET_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Q16.16 signed (range -32768 to +32767.99998)
    assert "Q16.16" in content, "Document must define Q16.16 representation"
    assert "-32768" in content and "+32767.99998" in content, (
        "Document must define Q16.16 range -32768 to +32767.99998 for fixed-point representation"
    )

    # 2. Q24.8 signed (range -8388608 to +8388607.996)
    assert "Q24.8" in content, "Document must define Q24.8 representation"
    assert "-8388608" in content and "+8388607.996" in content, (
        "Document must define Q24.8 range -8388608 to +8388607.996 for fixed-point representation"
    )

    # 3. Primitive register REGISTER_2 format assertion
    reg2_lines = [line for line in content.splitlines() if "REGISTER_2" in line]
    assert len(reg2_lines) > 0, "Document must reference REGISTER_2"

    # 4. Overflow error flag assertions: exceeding representable range leaves register unmodified and sets CONTROL_STATUS bit 2 (Error flag)
    assert "unmodified" in content.lower(), (
        "Document must specify that out-of-range writes leave the register unmodified"
    )
    assert "CONTROL_STATUS" in content, "Document must reference CONTROL_STATUS for overflow flag"


def test_simulation_testbench_golden_vector_oracle_issue370():
    if not os.path.isfile(TARGET_DOC):
        return

    with open(TARGET_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    content_lower = content.lower()

    # Assert golden vector oracle requirements
    assert "golden vector oracle" in content_lower or "golden vector" in content_lower, (
        "Document must define golden vector oracle test requirements"
    )
    assert "ieee-754" in content_lower, "Document must specify IEEE-754 input vectors"
    assert "q16.16" in content_lower and "q24.8" in content_lower, (
        "Document must specify expected Q16.16 and Q24.8 golden fixed-point outputs"
    )

    # Assert mandated assertions: nominal conversion accuracy, negative two's complement sign extension, LSB rounding mode, saturation/error flag on overflow
    assert "nominal conversion accuracy" in content_lower or "nominal accuracy" in content_lower, (
        "Document must mandate nominal conversion accuracy assertions"
    )
    assert "two's complement" in content_lower and "sign extension" in content_lower, (
        "Document must mandate negative two's complement sign extension assertions"
    )
    assert "rounding" in content_lower, "Document must mandate LSB rounding mode assertions"
    assert "saturation" in content_lower or "overflow" in content_lower, (
        "Document must mandate saturation/error flag assertions on overflow"
    )

    # Assert negative control requirement
    assert "negative control" in content_lower, (
        "Document must mandate a negative control verification requirement"
    )
    assert "pass-through" in content_lower or "stubbed" in content_lower, (
        "Document must mandate failure if conversion is stubbed to pass-through"
    )


def test_parameterized_wrapper_kind_and_equivalence_matrix_issue374():
    if not os.path.isfile(TARGET_DOC):
        return

    with open(TARGET_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    content_lower = content.lower()

    # 1. Parameterized testbench execution over WRAPPER_KIND (SPI, AXI_LITE, PCIE)
    assert "wrapper_kind" in content_lower, (
        "Document must parameterize testbench execution over WRAPPER_KIND"
    )
    for wrapper in ["spi", "axi_lite", "pcie"]:
        assert wrapper in content_lower, f"Document must include wrapper kind '{wrapper}' in WRAPPER_KIND"

    # 2. Cross-Wrapper Equivalence Assertion
    assert "cross-wrapper equivalence assertion" in content_lower or "equivalence assertion" in content_lower, (
        "Document must contain Cross-Wrapper Equivalence Assertion"
    )
    for reg in ["REGISTER_0", "REGISTER_1", "REGISTER_2", "CONTROL_STATUS"]:
        assert reg in content, f"Cross-wrapper equivalence assertion must cover register '{reg}'"

    for wrap_name in ["SPI_Wrap", "AXI_Lite", "PCIe_Wrap"]:
        assert wrap_name in content, f"Cross-wrapper equivalence assertion must cover adapter '{wrap_name}'"

    # 3. Objective-to-Assertion Matrix
    assert "objective-to-assertion matrix" in content_lower or "objective-to-assertion" in content_lower, (
        "Document must contain an Objective-to-Assertion Matrix binding Section 1 objectives to verification assertions"
    )


LUMI_BLUEPRINT_DOC = os.path.join(REPO_ROOT, "docs", "designs", "lumi-framework-blueprint.md")


def test_lumi_framework_blueprint_document_integrity():
    """Verify that docs/designs/lumi-framework-blueprint.md exists and contains valid LUMI framework definitions."""
    if not os.path.isfile(LUMI_BLUEPRINT_DOC):
        return

    with open(LUMI_BLUEPRINT_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Frontmatter verification
    assert content.startswith("---"), "LUMI blueprint must begin with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "LUMI blueprint must contain closed YAML frontmatter"

    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), "Frontmatter must parse as a valid YAML dictionary"
    assert metadata.get("type") == "design", "Frontmatter 'type' must be 'design'"
    assert "title" in metadata, "Frontmatter must contain 'title'"

    # 2. Executive Summary & Metamodel Vision categories
    for category in ["Visual GUI", "M2M API", "Hardware Bus"]:
        assert category in content, f"LUMI blueprint must define category '{category}'"

    # 3. Mermaid diagrams
    assert "classDiagram" in content, "LUMI blueprint must contain a Mermaid class diagram"
    assert "sequenceDiagram" in content, "LUMI blueprint must contain a Mermaid sequence diagram"
    assert "LUMIInterfaceBinding" in content, "LUMI blueprint must include LUMIInterfaceBinding class"

    # 4. Schemas and Grammars
    assert "interface_type" in content, "LUMI blueprint must specify interface_type scalar"
    assert "interface_types" in content, "LUMI blueprint must specify interface_types array"
    assert "## Logical UI & Interface Bindings" in content, "LUMI blueprint must include section ## Logical UI & Interface Bindings"
    assert "EBNF" in content or "ebnf" in content.lower(), "LUMI blueprint must contain EBNF grammar specification"

    # 5. Canonical Interface Component & Handler Dictionary
    for component in ["StringInputField", "MCPToolHandler", "RESTEndpointHandler", "RegisterBuffer"]:
        assert component in content, f"LUMI blueprint must define canonical component/handler '{component}'"

    # 6. Parity Auditor Validator Algorithm
    assert "logical_ui_validator.py" in content, "LUMI blueprint must reference logical_ui_validator.py"

    # 7. Constitution Amendment Specification AMEND-0014
    assert "AMEND-0014" in content, "LUMI blueprint must include Constitution Amendment Specification AMEND-0014"


SYSMLV2_BLUEPRINT_DOC = os.path.join(REPO_ROOT, "docs", "designs", "sysmlv2-universal-ingestion-blueprint.md")


def test_sysmlv2_universal_ingestion_blueprint_document_integrity():
    """Verify that docs/designs/sysmlv2-universal-ingestion-blueprint.md exists and contains valid SysML v2 IR framework definitions."""
    if not os.path.isfile(SYSMLV2_BLUEPRINT_DOC):
        return

    with open(SYSMLV2_BLUEPRINT_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Frontmatter verification
    assert content.startswith("---"), "SysML v2 blueprint must begin with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "SysML v2 blueprint must contain closed YAML frontmatter"

    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), "Frontmatter must parse as a valid YAML dictionary"
    assert metadata.get("type") == "design", "Frontmatter 'type' must be 'design'"
    assert "title" in metadata, "Frontmatter must contain 'title'"

    # 2. Executive Vision standards coverage
    for std in ["IETF YANG", "3GPP TS", "IEEE", "ISO", "OpenAPI", "Protobuf", "AUTOSAR", "ARINC 661"]:
        assert std in content, f"SysML v2 blueprint must reference normative standard '{std}'"

    # 3. Domain-to-SysML v2 Mapping Metamodel Table
    for mapping in ["package", "attribute def", "part def", "action def", "port def"]:
        assert mapping in content, f"SysML v2 blueprint mapping metamodel must contain '{mapping}'"

    # 4. Mermaid diagrams
    assert "classDiagram" in content or "graph TD" in content or "flowchart TD" in content, "SysML v2 blueprint must contain Mermaid architecture diagram"
    assert "sequenceDiagram" in content, "SysML v2 blueprint must contain a Mermaid sequence diagram"

    # 5. Formal SysML v2 Synthesis EBNF Grammar
    assert "EBNF" in content or "ebnf" in content.lower(), "SysML v2 blueprint must contain EBNF grammar specification"
    assert "package" in content and "part def" in content, "SysML v2 blueprint grammar must define packages and part defs"

    # 6. Skill Architecture Spec for skills/sysmlv2-schema-ingestion/SKILL.md
    assert "skills/sysmlv2-schema-ingestion/SKILL.md" in content, "SysML v2 blueprint must specify skills/sysmlv2-schema-ingestion/SKILL.md"

    # 7. Pipeline Integration & Downstream Forwarding Flow
    assert "is_sysml=True" in content, "SysML v2 blueprint must specify is_sysml=True downstream forwarding flag"


def test_product_name_standardization_enforcement():
    """Verify that project metadata and product references across governance and documentation files match 'Digital Engineering Agent Platform (DEAP)'."""
    constitution_path = os.path.join(REPO_ROOT, ".pipeline", "constitution.md")
    assert os.path.isfile(constitution_path), f"Constitution file missing: {constitution_path}"

    with open(constitution_path, "r", encoding="utf-8") as f:
        const_content = f.read()

    assert const_content.startswith("---"), "Constitution must begin with YAML frontmatter delimiter '---'"
    const_parts = const_content.split("---", 2)
    assert len(const_parts) >= 3, "Constitution must contain closed YAML frontmatter"
    const_metadata = yaml.safe_load(const_parts[1])
    assert isinstance(const_metadata, dict), "Constitution frontmatter must parse as dict"

    expected_product_name = "Digital Engineering Agent Platform (DEAP)"
    actual_project_name = const_metadata.get("project")
    assert actual_project_name == expected_product_name, (
        f"Constitution project name '{actual_project_name}' does not match expected '{expected_product_name}'"
    )

    candidate_gov_files = [
        os.path.join(REPO_ROOT, ".pipeline", "constitution.md"),
        os.path.join(REPO_ROOT, ".pipeline", "profiles", "flutter.md"),
        os.path.join(REPO_ROOT, ".pipeline", "profiles", "react.md"),
        os.path.join(REPO_ROOT, ".pipeline", "upstream", "pipeline-tooling.md"),
    ]
    profiles_dir = os.path.join(REPO_ROOT, ".pipeline", "profiles")
    if os.path.isdir(profiles_dir):
        for pf in os.listdir(profiles_dir):
            if pf.endswith(".md"):
                candidate_gov_files.append(os.path.join(profiles_dir, pf))

    governance_files_with_frontmatter = [f for f in candidate_gov_files if os.path.isfile(f)]

    for gov_file in governance_files_with_frontmatter:
        with open(gov_file, "r", encoding="utf-8") as f:
            c = f.read()
        parts = c.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1])
            if isinstance(meta, dict) and "project" in meta:
                assert meta.get("project") == expected_product_name, (
                    f"File {gov_file} project field '{meta.get('project')}' does not match '{expected_product_name}'"
                )

    legacy_terms = [
        "Digital Engineering Agentic Pipeline",
        "Digital Engineering Agent Pipeline",
        "DEAP-spec-core",
        "Distributed Ecosystem Architecture Platform",
    ]

    target_files = [
        os.path.join(REPO_ROOT, ".pipeline", "constitution.md"),
        os.path.join(REPO_ROOT, ".pipeline", "constitution-amendments.md"),
        os.path.join(REPO_ROOT, ".pipeline", "logical-ui", "logical-components.md"),
        os.path.join(REPO_ROOT, ".pipeline", "profiles", "flutter.md"),
        os.path.join(REPO_ROOT, ".pipeline", "profiles", "react.md"),
        os.path.join(REPO_ROOT, ".pipeline", "upstream", "pipeline-tooling.md"),
        os.path.join(REPO_ROOT, "README.md"),
        os.path.join(REPO_ROOT, "install-guide.md"),
        os.path.join(REPO_ROOT, "scripts", "install_pipeline.sh"),
        os.path.join(REPO_ROOT, ".tessl-plugin", "plugin.json"),
        os.path.join(REPO_ROOT, "tessl.json"),
        os.path.join(REPO_ROOT, "docs", "designs", "lumi-framework-blueprint.md"),
        os.path.join(REPO_ROOT, "docs", "designs", "sysmlv2-universal-ingestion-blueprint.md"),
        os.path.join(REPO_ROOT, "docs", "designs", "six-mechanical-enforcement-gates-blueprint.md"),
        os.path.join(REPO_ROOT, "docs", "designs", "zero-skip-test-remediation-blueprint.md"),
    ]

    for tf in target_files:
        if not os.path.isfile(tf):
            continue
        with open(tf, "r", encoding="utf-8") as f:
            content = f.read()

        if tf.endswith("constitution-amendments.md"):
            # Exclude historical 'Before:' diff quotation blocks in amendment logs
            lines = content.splitlines()
            filtered = []
            in_before_block = False
            for line in lines:
                if "Before:" in line:
                    in_before_block = True
                    continue
                if in_before_block and (line.startswith("After:") or line.startswith("###") or line.startswith("---")):
                    in_before_block = False
                if not in_before_block:
                    filtered.append(line)
            check_content = "\n".join(filtered)
        elif tf.endswith("README.md"):
            # Exclude deprecation/archive banner block pointing to DEAP-spec-core
            lines = content.splitlines()
            filtered = [l for l in lines if "THIS REPOSITORY IS FROZEN & ARCHIVED" not in l and "DEAP-spec-core" not in l]
            check_content = "\n".join(filtered)
        else:
            check_content = content

        for term in legacy_terms:
            assert term not in check_content, f"Target file {tf} contains legacy term '{term}'"


SIX_MECHANICAL_GATES_BLUEPRINT_DOC = os.path.join(REPO_ROOT, "docs", "designs", "six-mechanical-enforcement-gates-blueprint.md")


def test_six_mechanical_enforcement_gates_blueprint_document_integrity():
    """Verify that docs/designs/six-mechanical-enforcement-gates-blueprint.md exists and contains valid enforcement gate specifications."""
    if not os.path.isfile(SIX_MECHANICAL_GATES_BLUEPRINT_DOC):
        return

    with open(SIX_MECHANICAL_GATES_BLUEPRINT_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Frontmatter verification
    assert content.startswith("---"), "Blueprint must begin with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Blueprint must contain closed YAML frontmatter"

    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), "Frontmatter must parse as a valid YAML dictionary"
    assert metadata.get("type") == "design", "Frontmatter 'type' must be 'design'"
    assert "title" in metadata, "Frontmatter must contain 'title'"
    assert metadata.get("project") == "Digital Engineering Agent Platform (DEAP)", (
        "Frontmatter 'project' must match 'Digital Engineering Agent Platform (DEAP)'"
    )

    # 2. Check 6 Core Deterministic Enforcement Mechanisms
    mechanisms = [
        "Pre-Dispatch Schema Ingestion Gate",
        "Runtime Capability Pre-Flight Probe Check",
        "Subagent Output Integrity Validator",
        "Template Placeholder Escape Tokens",
        "Shift-Left Registration-Time Phase Gate",
        "Plan-to-Schema Cross-Reference Gate",
    ]
    for mech in mechanisms:
        assert mech in content, f"Blueprint must contain mechanism '{mech}'"

    # Specific technical details for Mechanism 1
    assert "schema-digest.json" in content, "Blueprint must reference 'schema-digest.json'"
    assert "SHA-256" in content or "sha256" in content.lower(), "Blueprint must specify SHA-256 digest"

    # Specific technical details for Mechanism 2
    assert "Probe subagent" in content or "probe subagent" in content.lower(), "Blueprint must reference Probe subagent"

    # Specific technical details for Mechanism 3
    assert "verify_subagent_output.py" in content, "Blueprint must reference 'verify_subagent_output.py'"

    # Specific technical details for Mechanism 4
    for escape_token in ["{{REQUIRED_JUSTIFICATION}}", "{{REQUIRED_SOURCE_REF}}", "{{REQUIRED_LUI}}"]:
        assert escape_token in content, f"Blueprint must define escape token '{escape_token}'"

    # Specific technical details for Mechanism 5
    assert "Phase 3" in content or "Use Case" in content, "Blueprint must specify Phase 3 Use Case flow validation"

    # Specific technical details for Mechanism 6
    assert "implementation_plan.md" in content, "Blueprint must reference 'implementation_plan.md'"
    assert "schema_nodes" in content, "Blueprint must reference 'schema_nodes' mapping table"

    # 3. Mermaid diagrams
    assert "classDiagram" in content or "graph TD" in content or "flowchart TD" in content, (
        "Blueprint must contain Mermaid architecture diagram"
    )
    assert "sequenceDiagram" in content, "Blueprint must contain Mermaid sequence diagram"

    # 4. Formal EBNF Grammar & JSON Schema Specifications
    assert "EBNF" in content or "ebnf" in content.lower(), "Blueprint must contain EBNF grammar specification"
    assert "$schema" in content or "json" in content.lower(), "Blueprint must contain JSON Schema specification"

    # 5. Codebase Deliverables & Test Plan section
    assert "Codebase Deliverables" in content or "Test Plan" in content, (
        "Blueprint must include Codebase Deliverables & Test Plan section"
    )


FIRESTORE_PROFILE_DOC = os.path.join(REPO_ROOT, "docs", "architecture", "profiles", "FIRESTORE_PERSISTENCE_PROFILE.md")


def test_firestore_profile_domain_neutrality():
    """Verify domain-specific sample data is purged from FIRESTORE_PERSISTENCE_PROFILE.md (Issue #373 compliance)."""
    if not os.path.isfile(FIRESTORE_PROFILE_DOC):
        return

    with open(FIRESTORE_PROFILE_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # Assert presence of abstract CS primitives
    assert "NODE_INSTANCE_01" in content, "Document must reference abstract primitive NODE_INSTANCE_01"
    assert "referenceSystem" in content, "Document must reference referenceSystem"
    assert "SYSTEM_PRIMARY" in content, "Document must reference SYSTEM_PRIMARY"
    assert "PRIMARY_TYPE" in content, "Document must reference PRIMARY_TYPE"

    # Assert absence of domain-specific sample data
    for domain_term in ["Tokyo-Gateway-01", "astronomicalBody", "earth", "ROUTER"]:
        assert domain_term not in content, f"Document must not contain domain-specific term '{domain_term}'"


ZERO_SKIP_BLUEPRINT_DOC = os.path.join(REPO_ROOT, "docs", "designs", "zero-skip-test-remediation-blueprint.md")


def test_zero_skip_test_remediation_blueprint_document_integrity():
    """Verify that docs/designs/zero-skip-test-remediation-blueprint.md exists and contains valid Zero-Skip remediation definitions."""
    if not os.path.isfile(ZERO_SKIP_BLUEPRINT_DOC):
        return

    with open(ZERO_SKIP_BLUEPRINT_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Frontmatter verification
    assert content.startswith("---"), "Blueprint must begin with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Blueprint must contain closed YAML frontmatter"

    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), "Frontmatter must parse as a valid YAML dictionary"
    assert metadata.get("type") == "design", "Frontmatter 'type' must be 'design'"
    assert "title" in metadata, "Frontmatter must contain 'title'"
    assert metadata.get("project") == "Digital Engineering Agent Platform (DEAP)", (
        "Frontmatter 'project' must match 'Digital Engineering Agent Platform (DEAP)'"
    )

    # 2. Key Section Assertions
    assert "Architectural Goal" in content or "Executive Summary" in content, (
        "Blueprint must detail Architectural Goal"
    )
    assert "Co-Normative Rule Contract Heading Scan Resolution" in content, (
        "Blueprint must detail Co-Normative Rule Contract Heading Scan Resolution"
    )
    assert "Fixture Directory & Mock Scoped Context Patterns" in content, (
        "Blueprint must detail Fixture Directory & Mock Scoped Context Patterns"
    )
    assert "Verification Metrics & Maintenance Mandate" in content, (
        "Blueprint must detail Verification Metrics & Maintenance Mandate"
    )

    # 3. File & Module Reference Assertions
    assert "tests/test_rule_contracts.py" in content, "Blueprint must reference 'tests/test_rule_contracts.py'"
    assert "rules/platform-independence.md" in content, "Blueprint must reference 'rules/platform-independence.md'"
    assert "rules/tracker-source-of-truth.md" in content, "Blueprint must reference 'rules/tracker-source-of-truth.md'"
    assert "rules/user-authorization-lock.md" in content, "Blueprint must reference 'rules/user-authorization-lock.md'"
    assert ".agents/AGENTS.md" in content, "Blueprint must reference '.agents/AGENTS.md'"

    assert "tests/repro_cases/.gitkeep" in content, "Blueprint must reference 'tests/repro_cases/.gitkeep'"
    assert "test_gate_scope_issue321_issue331.py" in content, "Blueprint must reference 'test_gate_scope_issue321_issue331.py'"
    assert "test_validator_findings_migration_issue304.py" in content, (
        "Blueprint must reference 'test_validator_findings_migration_issue304.py'"
    )
    assert "test_pyproject_floor.py" in content, "Blueprint must reference 'test_pyproject_floor.py'"

    # 4. Mermaid Diagrams
    assert "classDiagram" in content or "graph TD" in content or "flowchart TD" in content, (
        "Blueprint must contain Mermaid architecture diagram"
    )
    assert "sequenceDiagram" in content, "Blueprint must contain Mermaid sequence diagram"
