# Master Agent Handoff & Governance Briefing: DEAP-spec-core

**Target Repository**: `gintatkinson/DEAP-spec-core`  
**Document Classification**: Mandatory Agent Onboarding, Forensic Diagnosis & Transgression Prevention Contract  
**Effective Date**: 2026-08-29  
**Repository Role**: `UPSTREAM_SPEC_CORE_COMPILER` (Digital Engineering Agent Platform Core Specification Compiler)

---

## 1. Executive Summary & Architectural Hierarchy

This repository, **`DEAP-spec-core`**, is the **Upstream Abstract Specification Core Compiler** for the Digital Engineering Agent Platform (DEAP).

### Fundamental Architectural Invariant:
* **100% Domain-Agnostic and Purely Schema-Driven**: DEAP is an abstract Model-Based Systems Engineering (MBSE) compiler and multi-agent verification platform. It operates purely on Abstract Syntax Tree (AST) tokens derived from user-provided schemas in `schema/` (SysML v2, YANG, OpenAPI, Protobuf, IDL, ARXML).
* **Zero Hardcoded Domain Concepts**: Agents and core tools are strictly prohibited from hardcoding or inventing domain-specific concepts (e.g., aerospace flight controllers, automotive ECUs, medical devices, telecommunications networks) anywhere in core logic, governance, templates, or tests.
* **Hierarchical Boundary**:
  1. **Tier 0 (Upstream Core Compiler - `DEAP-spec-core`)**: Domain-free compiler, parity auditor, SysML v2 AST parsers, universal verification gates, and orchestrator skills.
  2. **Tier 1 (Downstream Domain Distribution Templates - e.g., `DEAP-uas-infrastructure-safety`)**: Domain-specific templates containing regulatory matrices (SORA, DO-178C, ISO 26262), domain profiles (ROS2, PX4, AUTOSAR), and safety statechart baselines.
  3. **Tier 2 (Downstream Customer Project Workspaces)**: Concrete customer code, proprietary flight logs, sensor models, and mission parameters installed via `scripts/install_pipeline.sh`.

---

## 2. Complete Inventory of Domain Contamination in DEAP-spec-core

Below is the exhaustive, empirical catalog of domain contamination currently present in this upstream compiler repository:

### A. Root Documentation ([`README.md`](README.md))
* **Lines 1–15**:
  - Renames repository to `DEAP-uas-infrastructure-safety` (Low-Altitude UAS Infrastructure Safety Platform).
  - Scope erroneously defined around Uncrewed Aircraft Systems (UAS), Urban Air Mobility (UAM), and autonomous flight fleet safety.
* **Lines 30–55**:
  - Hardcodes aviation regulatory standards: `JARUS SORA v2.5 (SAIL I–VI)`, `ASTM F3269-17 RTA`, `ASTM F3411-22a Remote ID`, and `RTCA DO-365B DAA`.
  - Hardcodes platform profiles: `ROS2 C++ Real-Time Lifecycle Nodes` and `PX4 Autopilot Flight Modules`.
* **Lines 370–525**:
  - Injects Pipeline 0 UAS CONOPS workflows, Remote Pilot in Command (RPIC) lifelines, pitch envelope limits, fail-safe Return-to-Launch (RTL), and aerodynamic flight statecharts.

### B. Functional Governance ([`.pipeline/constitution.md`](.pipeline/constitution.md))
* **Lines 120–155**:
  - Hardcodes `Phase 0 Safety Engineering Airworthiness Gate` requiring JARUS SORA Annex E OSO-01..24 matrices and ASTM F3269-17 RTA safety monitors directly in Tier 1 functional constitution.
  - Defines canonical Logical UI patterns using domain-specific examples (`ARINC 661 Cockpit Display Systems`, `Flight Control Statecharts`) rather than abstract UI/API/State patterns.

### C. Agent Rules ([`AGENTS.md`](AGENTS.md) and [`.agents/AGENTS.md`](.agents/AGENTS.md))
* **Lines 3–7**:
  - Declares `Repository Classification: PIPELINE_DISTRIBUTION_TEMPLATE (Upstream Domain Template for UAS Infrastructure Safety)`.
  - Inverts the boundary: misclassifies the upstream specification core compiler as a domain-specific UAS template.

### D. Skill Templates ([`skills/`](skills))
* **[`skills/schema-specification-engineering/SKILL.md`](skills/schema-specification-engineering/SKILL.md)**:
  - Hardcodes `AutonomousCollisionAvoidance`, `FlightGuidance`, and `+Boolean ExecuteManeuver(Float in_targetHeading, ...)` into canonical template class diagrams.
* **[`skills/spec-user-story-engineering/SKILL.md`](skills/spec-user-story-engineering/SKILL.md)**:
  - Hardcodes `flightGuidance : FlightGuidanceComputer` in sequence diagram lifelines.
* **[`skills/spec-orchestrator/SKILL.md`](skills/spec-orchestrator/SKILL.md)**:
  - Contains references to SORA matrices, STPA flight envelopes, and UAS safety deliverables.

### E. Architectural Blueprints ([`docs/architecture/blueprints/`](docs/architecture/blueprints))
* Legacy UAS concept blueprints committed directly in upstream core:
  - `docs/architecture/blueprints/DEAP_UAS_INFRASTRUCTURE_SAFETY_CONCEPT_PAPER.md`
  - `docs/architecture/blueprints/DEAP_FLIGHT_SYSTEMS_SAFETY_CONCEPT_PAPER.md`
  - `docs/architecture/blueprints/DEAP_SYSML_V2_SAFETY_MODEL_SPECIFICATION.sysml` (contains flight control and avionics terms)
  - `docs/architecture/DEAP_PIPELINE_0_FRONTEND_SYSTEMS_SAFETY_BLUEPRINT.md`

### F. Unit & Integration Tests ([`tests/`](tests))
* **[`tests/test_safety_integrity.py`](tests/test_safety_integrity.py)**:
  - Hardcodes assertions checking for SORA OSO-01..24 airworthiness requirements directly in the core test suite.

---

## 3. Forensic Git Chronology (How the Regression Occurred)

Inspection of `git log` reveals the commit chain that introduced this domain contamination into `DEAP-spec-core`:

1. **Commit `716f4ff`** (*feat(governance): enforce pure schema-driven compiler & clean landing zones*):
   - Established the rule forbidding hardcoded domain concepts, but simultaneously introduced the header classifying the repository as `PIPELINE_DISTRIBUTION_TEMPLATE (Upstream Domain Template for UAS Infrastructure Safety)` in `AGENTS.md`.
2. **Commit `c145860`** (*fix(docs): resolve Worker 0A prompt, AGENTS.md scope, and GitLab onboarding*):
   - Injected UAS-specific CONOPS prompts and Remote Pilot lifelines into `README.md`.
3. **Commit `0bfe0f4` & `be327b1`** (*fix(conops): add file-based input spec contract and Dual-Mode Worker 0A*):
   - Merged Pipeline 0 UAS safety engineering specifications into `README.md`.
4. **Commit `9f3e6b8` & `62cba2d`** (*feat(safety): implement Safety Integrity Quality Gate (Check 17) and SORA OSO-01..24 completeness*):
   - Injected JARUS SORA OSO-01..24, ASTM F3269-17, and DO-365B airworthiness gates directly into `.pipeline/constitution.md` and `README.md`.
5. **Root Cause Mechanism**:
   - Upstream core development mistakenly merged downstream distribution template features (`DEAP-uas-infrastructure-safety`) directly into `DEAP-spec-core`.
   - The absence of an automated static analysis test in CI allowed domain-specific terms to pass validation without triggering build failures.

---

## 4. Post-Mortem of Previous Agent Transgressions (CRITICAL — NEVER REPEAT)

Incoming agents must understand the three specific mistakes made during this session and avoid them completely:

### Transgression 1: Violation of the Strict Planning Gate & Authorization Lock
* **The Failure**: Upon receiving a user statement (*"you must have all your work performed autonomously without my intervention"*), the agent assumed it had authority to start modifying files and dispatching background subagents.
* **The Rule**: Under [`.agents/AGENTS.md`](.agents/AGENTS.md) § *Strict Planning Gate* and [`rules/user-authorization-lock.md`](rules/user-authorization-lock.md), execution is strictly locked until the user explicitly responds to an `implementation_plan.md` with **`PROCEED`**, **`Approved`**, or **`Approve plan`** in that immediate turn. No general instruction or conversational remark ever authorizes autonomous execution.

### Transgression 2: Hardcoding Domain Blocklists in Test Code
* **The Failure**: To prevent future domain regressions, the agent proposed creating a test file (`tests/test_no_domain_contamination.py`) with a hardcoded Python blacklist of UAS terms (`UAS`, `drone`, `PX4`, `SORA`).
* **The Rule**: **Hardcoding domain terms into compiler source/test code is itself domain contamination.** The compiler must remain 100% abstract. Vocabulary and prohibited standards must reside in external configuration (`codebase_rules.json`), and validation must be positive/AST-grounded (verifying that all entities in a spec resolve to nodes in `schema/`) rather than hardcoded negative string checks in Python.

### Transgression 3: Saving Handoff Documents to Session-Isolated Directories
* **The Failure**: The agent initially saved the handoff briefing inside its private session brain folder (`~/.gemini/antigravity/brain/<id>/agent_handoff.md`).
* **The Rule**: New agent conversations run in isolated contexts and are strictly forbidden from accessing other conversation directories. Handoff documentation and persistent repository guidance must be placed directly in the repository workspace (e.g., [`docs/HANDOFF.md`](docs/HANDOFF.md)).

---

## 5. Strict Operational Invariants for Incoming Agents

Every agent operating in this repository MUST adhere to these rules:

### Invariant 1: Mandatory 4-Point Karpathy Compliance Check
Every single thought block MUST begin with:
1. *Is the user's message a question/inquiry or a direct command?*
2. *Has the user explicitly approved a file-write/command execution for this turn? (Yes/No)*
3. *Am I making any silent assumptions about the user's intent?*
4. *Does the active skill mandate context-isolated subagent dispatches, or does this turn write any repository source or specification file? (If yes, coordinator direct file-writing is locked).*

### Invariant 2: Pure Schema-Driven Metamodel
Use only abstract, generic UML/SysML entities in core templates:
* **Classes**: `Component`, `SystemClassifier`, `DataPayload`, `StateService`
* **Operations**: `+Boolean processPayload(in_payload: DataType, out_status: StatusEnum)`
* **Lifelines**: `userActor : UserActor`, `systemService : SystemService`
* **Interfaces**: Generic UI (`gui`), Machine API (`mcp`/`api`), Hardware Bus (`hardware`)

### Invariant 3: Configuration-Driven Validation & AST Traceability
* Load all forbidden terms or standards dynamically from `codebase_rules.json` (e.g., `spec_rules.forbidden_standards_blocklist`).
* Enforce positive AST derivation: reject any specification entity not grounded in `schema/*.sysml`.

### Invariant 4: Context-Isolated Subagent Dispatch Mandate
* Coordinator is strictly locked from modifying codebase source files or specifications directly.
* Subagents must be dispatched with single-item micro-task scope, fresh isolated context, and mandatory `view_file` on `SKILL.md` as Step 1.
* Every completed subagent must be immediately terminated/reclaimed via `manage_subagents kill`.

---

## 6. Comprehensive Remediation Work Packages (Exact Specifications)

When the user provides an approved plan and gives the **`PROCEED`** command, execute these work packages via context-isolated subagents:

### Work Package 1: Cleanse Governance & Repository Classification
* **Target Files**: [`AGENTS.md`](AGENTS.md) and [`.agents/AGENTS.md`](.agents/AGENTS.md)
* **Exact Modification**:
  ```markdown
  ## Repository Role & Scope Classification
  - **Repository Classification:** `UPSTREAM_SPEC_CORE_COMPILER` (Digital Engineering Agent Platform Core Specification Compiler)
  - **Sentinel Indicator:** The presence of `.pipeline/upstream/` and `skills/spec-orchestrator/` denotes that this repository is the **Upstream Specification Core Compiler**, NOT a downstream customer application workspace or domain template.
  - **Domain Template & Customer Data Boundary:** Domain-specific platforms (e.g. UAS safety, automotive, medical) and customer applications belong in downstream distribution repositories, and must NOT be committed to this upstream specification core compiler repository.
  ```

### Work Package 2: Cleanse Master Documentation (`README.md`)
* **Target File**: [`README.md`](README.md)
* **Exact Modifications**:
  - Title: `# Digital Engineering Agent Platform (DEAP) — Core Specification Compiler`
  - Identifier: `DEAP-spec-core`
  - Classification: `Abstract Model-Based Systems Engineering (MBSE) Compiler & Multi-Agent Verification Platform`
  - Replace Section 2 (UAS Regulations) with: **Supported Schema & Modeling Standards** (SysML v2, OMG IDL, AUTOSAR ARXML, YANG RFC 8345, OpenAPI v3, Protobuf v3).
  - Replace Section 3 (ROS2/PX4 Profiles) with: **Multi-Platform Implementation Engine Overview** (Flutter LUI, React Web, Embedded C, SPARK Ada).
  - Replace Section 8 & 9 (UAS Flight Prompts) with: **Domain-Agnostic Systems Engineering & State Machine Prompts**.
  - Retain all core infrastructure: MATLAB/Simulink Integration, SysML v2 SSOT Compilation, Multi-Provider GitHub/GitLab support, 22 Parity Gates, and Turnkey Installer (`scripts/install_pipeline.sh`).

### Work Package 3: Cleanse Functional Constitution (`.pipeline/constitution.md`)
* **Target File**: [`.pipeline/constitution.md`](.pipeline/constitution.md)
* **Exact Modifications**:
  - Remove SORA SAIL I–VI and OSO-01..24 airworthiness requirements from Tier 1 governance.
  - Replace domain-specific LUI examples (ARINC 661, Flight Control Statecharts) with abstract 3-layer semantic patterns:
    1. *Domain State & Signal Model* (Input Buffer / Event Stream)
    2. *Logic & Safety State Management* (Statechart / ViewModel / FSM)
    3. *Display & Actuator Interface Binding* (GUI Widget / Driver Interface)
  - Log amendment in `.pipeline/constitution-amendments.md` following the Step 9 amendment protocol.

### Work Package 4: Sanitize Skill Templates
* **Target Files**: [`skills/schema-specification-engineering/SKILL.md`](skills/schema-specification-engineering/SKILL.md) and [`skills/spec-user-story-engineering/SKILL.md`](skills/spec-user-story-engineering/SKILL.md)
* **Exact Modifications**:
  - Replace `AutonomousCollisionAvoidance`, `FlightGuidance`, and `ExecuteManeuver` with generic classifiers (`TelemetryProcessor`, `SystemController`, `processDataPayload`).
  - Replace `flightGuidance : FlightGuidanceComputer` with `systemController : SystemController`.

### Work Package 5: Purge Legacy UAS Blueprints & Sanitize Safety Test
* **Target Files**:
  - Remove or relocate legacy UAS blueprints from `docs/architecture/blueprints/` to downstream templates.
  - Refactor [`tests/test_safety_integrity.py`](tests/test_safety_integrity.py) to check generic safety invariant traceability rather than hardcoded SORA OSO-01..24 checks.
  - Update `codebase_rules.json` to configure forbidden domain standards dynamically.

---

## 7. Verification Protocol & Quality Gates

After executing all remediation work packages via subagents, execute:
1. **Unit & Parity Suite**:
   ```bash
   python3 -m unittest discover -s tests
   ```
2. **Downstream Baseline Verification**:
   ```bash
   python3 scripts/verify_downstream_baseline.py --no-domain
   ```
3. **Model Coverage Gate**:
   ```bash
   python3 skills/spec-orchestrator/scripts/verify_model_coverage.py --spec-only
   ```
4. **Git Synchronization Gate**:
   - Verify `git status` shows clean working tree.
   - Verify `git diff origin/main` is empty after push.

---

## 8. Incoming Agent Verification Checklist
Before taking any action, the incoming agent must confirm:
- [ ] I have read [`docs/HANDOFF.md`](docs/HANDOFF.md) in full.
- [ ] I have verified that `git status` is clean on `main`.
- [ ] I will NOT write files, run modifying commands, or dispatch subagents without explicit **`PROCEED`** approval for that specific turn.
- [ ] I will maintain 100% domain neutrality across all outputs and templates.
- [ ] I will never hardcode domain vocabulary into Python test files.
