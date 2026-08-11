<!-- Copyright Gint Atkinson, gint.atkinson@gmail.com -->

> [!CAUTION]
> **THIS REPOSITORY IS FROZEN & ARCHIVED**
> All active development, assets, and governance have migrated to [`gintatkinson/DEAP-spec-core`](https://github.com/gintatkinson/DEAP-spec-core).
> Please use [`https://github.com/gintatkinson/DEAP-spec-core`](https://github.com/gintatkinson/DEAP-spec-core) for the latest specification engineering assets, rules, skills, and documentation.

# Digital Engineering Agent Platform (DEAP) (Builders Project)


Welcome to the Digital Engineering Agent Platform (DEAP). This repository contains a suite of autonomous AI Agent "Skills" designed to:

1. **Specification-engineer protocol standards** into deterministic, behavior-driven Agile tracking matrices in the active issue tracker.
2. **Implement features** from those backlogs using subagent-driven TDD execution discipline with two-stage review gates.

By feeding these agents a Structural Schema and its associated Normative Specification Document, the agents will automatically build your Epics, Features, User Stories, and UML Use Cases, ensuring a 100% mathematically bounded requirements pipeline mapped via UML OOA/OOD methodologies.

## Documentation at: https://github.com/gintatkinson/digital-pipeline-repo

---

## Primary Commercial Toolchain Integration

DEAP explicitly declares **MATLAB / Simulink / Stateflow / Embedded Coder** as the Primary Tier-1 Commercial Toolchain Integration (Model-Based Design, Control Law Synthesis, DO-178C C/SPARK Ada Code Generation).

---

## Governance: The Functional Constitution

This pipeline ships with a **default functional constitution** (located at the configured pipeline configuration directory, e.g., `<pipeline_dir>/constitution.md`) that governs all specification generation (Pipeline 1). It defines:

| Section | What it governs |
|---|---|
| **Domain Rules** | Schema compliance, data model integrity, traceability requirements, conflict resolution between normative text and schema |
| **Specification Standards** | Epic/Feature granularity, BDD scenario format, User Story/Use Case formality, labeling taxonomy |
| **Agent Behavior** | Commit format, branch strategy, documentation standards, idempotency, error handling |
| **Universal Quality Gates** | Validation gates per worker phase, 100% model coverage, cross-reference integrity, human approval scope |
| **Forbidden Practices** | No invented requirements, no platform contamination, no skipped error scenarios, no silent node drops |

The constitution is **read by all skills before execution**. It is the single source of truth for specification quality decisions.

For implementation work (Pipeline 2), platform-specific rules live in **Implementation Profiles** (e.g., `<pipeline_dir>/profiles/<platform>.md`). These are created per-project, per-platform, and are never read by specification workers.

```
<pipeline_dir>/
  constitution.md              <-- Governs Pipeline 1 (all agents read this)
  profiles/
    [platform].md              <-- Governs Pipeline 2 for a specific target stack
```

> To customize: edit the constitution file directly. The constitution is human-authored, agent-enforced.

---

## The Agent Architecture

This toolchain operates on a **Master-Worker architecture** with three distinct pipelines:

### Pipeline 0: Front-End Systems & Safety Modeling (Workers 0A–0C)

#### CONOPS & Scenario Synthesis Module (Worker 0A)
Ingests raw customer intent, operational envelopes, airspace parameters, and stakeholder constraints. Synthesizes normative Concept of Operations (`CONOPS.md`) establishing mission profiles, operational phases, environmental boundaries, and baseline SORA v2.5 Ground Risk Class (GRC) and Air Risk Class (ARC) levels.

#### STPA / FMECA / SORA SAIL Hazard Module (Worker 0B)
Applies System-Theoretic Process Analysis (STPA) and Failure Mode, Effects, and Criticality Analysis (FMECA) aligned with JARUS SORA v2.5 (SAIL I–VI), SAE ARP4761/ARP4754A, and ASTM F3269-17 RTA. Generates `STPA_MATRIX.md` defining System Losses ($L$), System Hazards ($H$), Control Structures, Unsafe Control Actions ($UCA$), and Safety Constraints ($SC$).

#### SysML v2 Authoring Module (Worker 0C)
Authors formal SysML v2 textual models (`DEAP_MODEL.sysml`) capturing requirement definitions, system part structures, interface ports, and safety statecharts, while serializing the inter-pipeline AST JSON handoff payload (`pipeline0_handoff_contract.json`) for Pipeline 1 Agile Backlog projection.

### Pipeline 1: Specification Generation (Orchestrator + Workers A-D)

#### Orchestration Module (The Master)
The overarching command-and-control module. It triggers workers in sequence, enforces strict validation gates between phases, and includes error recovery (halt-and-escalate on failure). Configured via the orchestration skill guides.

#### Structural Spec Engineering Module (Worker A: Structure)
Parses raw schemas. Breaks down structural models into **Epics** and **Features** with exhaustive Given-When-Then acceptance criteria, platform scoping, and verbatim spec context injection. Includes duplicate detection to ensure idempotent re-runs.

#### Behavioral Spec Engineering Module (Worker B: Behavior)
Parses operational/deployment chapters. Extracts BDD **User Stories** modeled on UML OOA/OOD principles. Builds a "Cross-Cutting Matrix" linking scenarios to Features. Includes duplicate detection.

#### System Interaction Spec Engineering Module (Worker C: System Interaction)
Extracts formal **UML System Use Cases** (Actors, Preconditions, Main Success Scenarios, Alternate Flows, Postconditions) and maps them to User Stories and Features in a Realization Matrix. Includes duplicate detection.

#### Pipeline Utilities (Worker D & Coverage Check)
* **Backlog Reconciliation Tool**: Zero-trust consistency audit. Queries the active issue tracker provider, syncs checkbox states in local markdown configuration, enforces dependency checks, and auto-closes completed Epics/Stories/Use Cases.
* **UML Compliance Linter**: Automated UML compliance linter. Parses input schemas, builds class/sequence/use-case diagram symbol tables, mathematically verifies 100% model coverage, and asserts OMG UML 2.5.1 metamodel conformance and cross-view consistency rules.

### Pipeline 2: Feature Implementation

#### Governance & Persistent Memory Module
Establishes a project's governing principles (platform constraints, coding standards, testing mandates, domain rules) as a persistent constitution file (e.g. `<pipeline_dir>/constitution.md`). All other skills read this before execution.

#### Feature Implementation Module
The execution engine. Implements features from the backlog using a disciplined, verifiable process. Includes an optional tech stack research phase (configured e.g. in `research.md` or as designated) for features involving unfamiliar or rapidly-evolving frameworks.

**Core execution discipline (14 mandates):**

| # | Mandate | Purpose |
|---|---|---|
| 1 | Serial Execution | One feature at a time, fully closed before next |
| 2 | The Grill Approval | Interactive design review before any code |
| 3 | Traceability | Closing comments link to solution walkthroughs |
| 4 | Agentic Epic Closure | Auto-close Epics when all features complete |
| 5 | No Browser Automation | Manual UI verification (unless project uses Playwright) |
| 6 | Issue Tracker as Source of Truth | Tracker CLI, never trust local state |
| 7 | Cumulative Walkthroughs | Append/merge, never destructive overwrite |
| 8 | Validation Isolation | Separate subagent audit or strict self-audit fallback |
| 9 | **TDD (RED-GREEN-REFACTOR)** | Failing test before code, always |
| 10 | **Micro-Task Decomposition** | 2-5 min tasks with driving test + verification |
| 11 | **Subagent-Driven Development** | Fresh isolated context per micro-task |
| 12 | **Two-Stage Review** | Spec compliance → Code quality, both must pass |
| 13 | **Verification-Before-Completion** | Raw proof (test output) required, no assertions |
| 14 | **Inter-Task Code Review** | Diff against plan, log deviations |

**Additional protocols:**
- **Project Constitution:** Persistent principles file read before every execution
- **Tech Stack Research:** Optional `research.md` phase before The Grill for unfamiliar frameworks
- **Parallel Dispatch `[P]`:** Spec-generation phases 2 & 3 can run in parallel on multi-agent runtimes
- **Systematic Debugging (4-phase):** Reproduce → Diagnose (stack trace, no guessing) → Fix (minimal upstream) → Verify (full suite)
- **Data Flow Slicing Order:** Persistence → Transformation → Interface

---

## Always-Loaded Governance Rules

In addition to skills (loaded on-demand), this pipeline includes **rules** — constraints injected into every agent session regardless of which skill is active. When installed via Tessl, these rules are automatically distributed to agent-specific config files (such as `.cursor/rules/`, `CLAUDE.md`, `AGENTS.md`).

| Rule | Enforcement |
|---|---|
| **`serial-execution`** | One feature at a time. No parallel feature work. |
| **`tdd-mandate`** | RED-GREEN-REFACTOR cycle required. Code before test must be deleted. |
| **`verification-required`** | Raw proof (pasted output) required. "It works" without evidence is forbidden. |
| **`constitution-first`** | Read the constitution file (e.g. `<pipeline_dir>/constitution.md`) before any task. Spec workers must NOT read implementation profiles. |
| **`no-browser-automation`** | No ad-hoc browser scripts. Manual verification or project E2E framework only. |
| **`tracker-source-of-truth`** | Use the issue tracker's CLI tool resolved from configuration to query issue state. |
| **`platform-independence`** | Specs must be functional. No framework names in features, stories, or use cases. |
| **`role-boundary-lock`** | Enforce strict role boundaries between specification and implementation phases. |


These rules live in the rules directory (e.g. `rules/`) and are packaged into the Tessl plugin alongside skills. Without Tessl, agents can read them directly from the configured rules directory.

---

## Installation

### Prerequisites & Python 3.12 Setup

The pipeline requires **Python 3.12+**, the configured tracker CLI, and git. Python scripts require `PyYAML` to parse configuration and issue frontmatter.

#### Installing Python 3.12
- **macOS (Homebrew)**:
  ```bash
  brew install python@3.12
  python3.12 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv
  python3.12 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### Turnkey One-Line Installation (Recommended)

Run the turnkey automated installer directly in your project root:

```bash
curl -sSL https://raw.githubusercontent.com/gintatkinson/digital-pipeline-repo/main/scripts/install_pipeline.sh | bash
```


### Direct Copy / Manual Installation

Alternatively, copy the pipeline directories and (optionally) the application templates into your project repository.

```bash
# Refuse to run inside the pipeline repository itself. The cleanup steps below are
# written for a downstream project: here they delete the upstream-only profile this
# repo owns and concatenate .gitignore onto itself. `test -e` is used rather than
# `find -type f` because rules/document-references.md requires existence checks to
# observe symlinks.
if [ -e ./.pipeline/upstream ]; then
  echo "REFUSING: this is the pipeline repository, not a downstream project." >&2
  exit 1
fi

git clone https://github.com/gintatkinson/digital-pipeline-repo.git ./.tmp-pipeline
rm -rf ./skills ./rules ./.pipeline ./.agents ./scripts ./app_flutter ./web_react
cp -RP ./.tmp-pipeline/skills ./
cp -RP ./.tmp-pipeline/rules ./
cp -RP ./.tmp-pipeline/.pipeline ./
rm -rf ./.pipeline/upstream   # upstream-only tooling profile; not for downstream projects
cp -RP ./.tmp-pipeline/.agents ./
cp -RP ./.tmp-pipeline/scripts ./
cp -RP ./.tmp-pipeline/app_flutter ./
cp -RP ./.tmp-pipeline/web_react ./
if [ -f ./.gitignore ]; then
  cat ./.tmp-pipeline/.gitignore >> ./.gitignore
else
  cp ./.tmp-pipeline/.gitignore ./
fi
rm -rf ./.tmp-pipeline
python3 scripts/setup_git_hooks.py

# Provision the tracker label taxonomy up front, rather than letting it appear one
# label at a time during the first orchestrator run (issue #323). Idempotent, so it
# is also the way to repair a tracker whose labels were deleted.
python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py
```

Then point your agent at the `skills/` directory. This is a one-time copy -- you manage updates manually.

---

### Setup for Google Antigravity / Gemini CLI

After copying the pipeline, configure Gemini to load the skills and rules:

1. **Point Gemini at the skills directory.** In your Gemini CLI session or Antigravity project config, reference the skill files:

   ```
   Read the files in ./skills/ and ./rules/ directories.
   ```

2. **AGENTS.md (recommended).** Create an `AGENTS.md` file in your project root that tells Gemini (and any other agent) where to find the pipeline:

   ```markdown
   # Agent Instructions

   ## Pipeline Skills
   This project uses the Digital Engineering Agent Platform (DEAP).
   - Skills: read all SKILL.md files in the configured skills directory (e.g., `skills/`)
   - Rules: read all files in the configured rules directory (e.g., `rules/`) -- these are mandatory constraints that apply to every task
   - Constitution: read the constitution file (e.g. `<pipeline_dir>/constitution.md`) before any task
   - Implementation profiles: read the implementation profile (e.g. `<pipeline_dir>/profiles/<platform>.md`) before implementing features
   ```

3. **Subagent dispatch.** Gemini CLI supports subagent tool calls with curated context. The `feature-driven-implementation` skill includes Gemini-specific dispatch instructions in Step 3.

### Setup for Claude Code

```bash
# Add to CLAUDE.md:
echo "Read all SKILL.md files in skills/ and all rule files in rules/ before starting any task." >> CLAUDE.md
```

### Setup for Cursor / Windsurf / Cascade

Create `.cursor/rules/pipeline.mdc` or `.windsurf/rules/pipeline.md` referencing the `skills/` and `rules/` directories.

### Downstream Baseline Verification

The verification script (`scripts/verify_downstream_baseline.py`) acts as a post-implementation compliance gate. It is **not** run manually on install when nothing has been implemented yet. Instead, it is run after the **Feature Implementation Agent** runs its implementation loop (or in CI/CD pull request gates) to verify that the generated code conforms to the Project Constitution.

#### Running the Verification Gate

To verify that the project is in a conforming state, run from the project root:
```bash
python3 scripts/verify_downstream_baseline.py
```
Or if you want to verify the workspace structure prior to implementing the domain model and validation rules:
```bash
python3 scripts/verify_downstream_baseline.py --no-domain
```

* **Auto-Detection**: The script dynamically auto-detects the platform (Flutter if it detects `pubspec.yaml`, React if it detects `package.json`). If both are present, both check suites are executed in sequence.
* **React Verification**: Asserts the presence of core React template files (`package.json`, `tsconfig.json` / `jsconfig.json`, `src/main.tsx` / `src/index.tsx`, and the domain validation file `src/domain/validation.ts` unless `--no-domain` is specified). Runs dependencies resolution and verifies compilation/packaging via `npm run build` (skipped under `--no-domain`).
* **Flutter Verification**: Asserts the presence of core Flutter template files (`pubspec.yaml`, `analysis_options.yaml`, `lib/main.dart`, and the database integration files `lib/domain/repository_resolver.dart` / `lib/domain/validation.dart` unless `--no-domain` is specified). Runs dependencies resolution (`flutter pub get`), static analysis (excluding fatal warning/info blocks), and the full automated test suite (skipped under `--no-domain`).

---

## Supported Runtimes

The skills are runtime-agnostic markdown files. The `feature-driven-implementation` skill includes runtime-specific dispatch instructions:

| Runtime | Subagent Dispatch | Two-Stage Review |
|---|---|---|
| **Claude Code** | `Task("prompt")` — native isolated subagent | Separate reviewer subagents |
| **Gemini CLI** | Subagent tool call with curated context | Separate reviewer subagents |
| **Cascade (Windsurf/Devin)** | Coordinator re-reads files per task to simulate isolation; user opens new chat for true isolation | Explicit self-audit documented in `task.md` |

---

## How to Run the Specification Pipeline

**Prerequisites:** AI agent framework capable of reading `.md` skill files + executing CLI commands required by the configured tracker (e.g. git, tracker CLI).

1. Ensure your AI agent has access to the configured skills directory.
2. Provide your agent with the following prompt:

> **Specification Generation Prompt:**
>
> "Adopt the specification-orchestrator skill by executing view_file on 
> `skills/spec-orchestrator/SKILL.md` as step 1.
>
> I want to specification-engineer [Protocol Standard, e.g., IETF / standard protocol schemas].
>
> 1. Inputs & Paths:
>    - Structural schemas are located at: `[path to schemas]`
>    - Normative specification documents are located at: `[path to specs]`
>    - Backlog output directory: `.pipeline/domain_specs/` (and live GitHub issue tracker)
>
> 2. Governance & Boundary Lock:
>    - Read and strictly adhere to `.pipeline/constitution.md` (Domain Rules, Specification Standards, 100% Model Coverage Gate).
>    - Enforce strict Role Boundary Lock: Specification workers are strictly forbidden from reading implementation profiles (`.pipeline/profiles/`), implementation plans, or codebase source files. Specs must remain 100% platform-independent.
>
> 3. Execution Discipline:
>    - Run tracker label bootstrap: `python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py`.
>    - Dispatch fresh, context-isolated subagents for Phase 1 (Worker A: Structure), Phase 2 (Worker B: Behavior), and Phase 3 (Worker C: System Interaction).
>    - Instruct every subagent to target AT MOST 1 specification item per dispatch prompt and execute view_file on its respective skill `SKILL.md` as step 1.
>
> 4. Verification & Backlog Reconciliation:
>    - Run model coverage verification: `python3 skills/spec-orchestrator/coverage_checker/src/verify_model_coverage.py`
>    - Run UML compliance linter: `python3 skills/spec-orchestrator/uml_linter/src/lint_uml_syntax.py`
>    - Execute backlog reconciliation: `python3 skills/spec-orchestrator/scripts/reconcile_backlog.py`
>    - Report raw verification results showing 100% model coverage and 0 linter errors."

---

## How to Implement a Feature

**Prerequisites:**
- AI agent framework capable of reading `.md` skill files.
- The target implementation profile configured (e.g. `.pipeline/profiles/react.md` or `.pipeline/profiles/flutter.md`).
- For Firestore target profiles, the local Firestore database emulator must be running (start via: `npx firebase-tools emulators:start --only firestore`).

> **Feature Implementation Prompt:**
>
> "Adopt the feature-driven-implementation skill by executing view_file on 
> `skills/feature-driven-implementation/SKILL.md` as step 1.
>
> I want to implement Feature [Issue Number, e.g., #82] targeting platform [react | flutter].
>
> 1. Pre-Execution Seeding & Rules Verification:
>    - Read and adhere to the Project Constitution (`.pipeline/constitution.md`):
>      * Section 1.9 Zero-Mocking Live Persistence Mandate (no in-memory mock repositories in DI).
>      * Section 4.5 Downstream Conformance Gates.
>      * Section 5 Forbidden Practices (do NOT remove layout splitters, timeline scrubber, or focus-loss property grid).
>      * Zero-Codegen Parameter Isolation Rule (UI widgets must be driven by TypeDescriptor schemas at runtime; zero hardcoded domain attributes in platform widgets).
>    - Map dependencies from `.pipeline/domain_specs/` and repo issue tracker.
>
> 2. Draft Implementation Plan enforcing the 3-Layer Definition of Done (DoD):
>    - Layer 1 (Domain Model): Clean domain types, schemas, validation logic.
>    - Layer 2 (ViewModel): State holder handling user actions and persistence dispatch.
>    - Layer 3 (LUI Widget Binding + BDD Acceptance Test): Responsive UI component bound to ViewModel, accompanied by a BDD User Story Widget test asserting (User Event -> ViewModel Action -> State Change -> LUI Render).
>    - Zero-Mocking Persistence: Concrete transport adapters / SQLite local emulator integration.
>    - Decompose into micro-tasks (2-5 min each, with a driving RED-GREEN test per task).
>
> 3. Present the plan for approval.
>
> 4. Execution Discipline:
>    - Dispatch fresh, context-isolated subagents targeting AT MOST 1 specification item per dispatch prompt.
>    - Instruct every subagent to execute view_file on `skills/feature-driven-implementation/SKILL.md` as step 1.
>    - Run TDD loops (RED-GREEN-REFACTOR) for each micro-task.
>    - Perform two-stage review after each micro-task (spec compliance, then code quality).
>
> 5. Verification Proof:
>    - Run compliance engine: `python3 scripts/verify_downstream_baseline.py`
>    - Run test suite: `python3 -m pytest tests/` (or `flutter test` / `npm test`)
>    - Provide raw build/test output as proof of zero-regression success.
>    - Provide step-by-step human manual testing instructions.
>
> 6. Deliver the cumulative walkthrough and update issue status to status:fixed-resolved."

---

## Section 6: Pipeline 0: Pre-Spec Safety Engineering Execution Workflow

Pipeline 0 (*Pre-Spec Safety Engineering Execution Workflow*) ingests unstructured customer intent, operational parameters, and flight envelopes to synthesize normative Concept of Operations (`CONOPS.md`), System-Theoretic Process Analysis safety matrices (`STPA_MATRIX.md`), SysML v2 textual models (`DEAP_MODEL.sysml`), and inter-pipeline handoff JSON contracts (`pipeline0_handoff_contract.json`).

### 6.1 Subagent Execution Roles

#### 1. Worker 0A: CONOPS & Scenario Synthesizer
* **Role Description:** Front-end ingestion subagent responsible for parsing raw customer intent, operational mission parameters, flight envelopes, airspace classifications, BVLOS constraints, and stakeholder boundaries.
* **Input Artifacts:** Unstructured customer intent, operational parameters, population density metrics, flight range/altitude bounds.
* **Output Artifacts:** `CONOPS.md` establishing mission goals, operational phases (`PRE_FLIGHT`, `TAKEOFF`, `CRUISE`, `INSPECTION`, `APPROACH`, `LANDING`, `RTA_BACKUP`), environmental boundaries, system interfaces, and baseline JARUS SORA v2.5 Ground Risk Class (GRC) and Air Risk Class (ARC) assignments.

#### 2. Worker 0B: STPA / FMECA / SORA SAIL Hazard Worker
* **Role Description:** Safety engineering subagent applying System-Theoretic Process Analysis (STPA) and Failure Mode, Effects, and Criticality Analysis (FMECA) aligned with JARUS SORA v2.5 (SAIL I–VI), SAE ARP4761/ARP4754A, and ASTM F3269-17 RTA.
* **Input Artifacts:** `CONOPS.md` generated by Worker 0A and target regulatory safety frameworks.
* **Output Artifacts:** `STPA_MATRIX.md` defining System Losses ($L$), System Hazards ($H$), Control Structure Diagrams, Unsafe Control Actions ($UCA$), Safety Constraints ($SC$), FMECA failure modes, and required SORA SAIL risk mitigations.

#### 3. Worker 0C: SysML v2 Authoring Worker
* **Role Description:** Model-Based Systems Engineering (MBSE) authoring subagent that formalizes CONOPS and STPA safety constraints into executable SysML v2 textual models and AST JSON handoff payloads.
* **Input Artifacts:** `CONOPS.md` from Worker 0A, `STPA_MATRIX.md` from Worker 0B.
* **Output Artifacts:** `DEAP_MODEL.sysml` (requirements, parts, ports, safety statecharts) and `pipeline0_handoff_contract.json` (the immutable AST handoff payload for Pipeline 1 Agile spec projection).

### 6.2 Inter-Pipeline Handoff JSON Contract (`pipeline0_handoff_contract.json`)

The interface between Pipeline 0 and Pipeline 1 is strictly governed by a formal handoff JSON contract (`pipeline0_handoff_contract.json`) to maintain platform decoupling and ensure 100% bidirectional traceability from SysML v2 safety requirements down to Pipeline 1 Features (`Feat-NNN`) and Pipeline 2 source code symbols.

```json
{
  "$schema": "https://deap.engine/schemas/pipeline0_handoff_v1.json",
  "metadata": {
    "identifier": "DEAP-PIPELINE-0-HANDOFF-001",
    "timestamp": "2026-08-11T00:00:00Z",
    "source_model": "DEAP_MODEL.sysml",
    "governance_status": "APPROVED",
    "regulatory_target": ["ARP4754A", "ARP4761", "JARUS SORA v2.5", "DO-178C", "DO-254", "ASTM F3269"]
  },
  "conops_summary": {
    "document_path": "docs/conops/CONOPS.md",
    "mission_type": "UAS BVLOS Urban Infrastructure Inspection",
    "operational_phases": ["PRE_FLIGHT", "TAKEOFF", "CRUISE", "INSPECTION", "APPROACH", "LANDING", "RTA_BACKUP"]
  },
  "safety_matrix": {
    "document_path": "docs/safety/STPA_MATRIX.md",
    "system_losses": [
      { "id": "L-1", "title": "Loss of Aircraft Control / Uncontrolled Flight Into Terrain (UFIT)" },
      { "id": "L-2", "title": "Airspace Collision with Manned Aircraft" }
    ],
    "hazards": [
      { "id": "H-1", "loss_refs": ["L-1"], "title": "Flight Controller Command Saturation during High-Wind Turbulence" },
      { "id": "H-2", "loss_refs": ["L-2"], "title": "Loss of Remote ID & DAA Telemetry Stream" }
    ],
    "unsafe_control_actions": [
      {
        "id": "UCA-1",
        "hazard_ref": "H-1",
        "control_action": "Execute Pitch Command",
        "failure_mode": "Provided Wrong / Out of Range",
        "safety_constraint": "SC-1: Pitch command must be rate-limited and bounded by pitch envelope protection safety statechart."
      }
    ]
  },
  "sysml_ast_export": {
    "requirements": [
      {
        "id": "REQ-SYS-001",
        "name": "EnvelopeProtectionRequirement",
        "text": "The flight control system shall enforce pitch angle limits between -15 deg and +25 deg.",
        "stpa_ref": "SC-1",
        "dal": "DAL A"
      }
    ],
    "parts": [
      {
        "id": "PART-SYS-001",
        "name": "FlightControlSystem",
        "ports": ["p_telemetry", "p_actuator_cmd"],
        "subparts": ["PrimaryController", "RunTimeAssuranceMonitor"]
      }
    ],
    "statecharts": [
      {
        "name": "SafetyModeStatechart",
        "states": ["NORMAL", "DEGRADED", "RTA_BACKUP_ENGAGED", "EMERGENCY_FAILSAFE"]
      }
    ]
  }
}
```

### 6.3 Pipeline 0 Command-Line Execution Prompts

To execute Pipeline 0 pre-spec safety engineering workers using an AI agent (e.g. Gemini CLI, Claude Code, Cursor, or Antigravity), use the following copy-pasteable prompt blocks:

#### 6.3.1 Worker 0A: CONOPS & Scenario Synthesizer Prompt
> **Worker 0A Prompt:**
>
> "Adopt the pre-spec safety engineering capabilities for Pipeline 0 Worker 0A.
>
> **Task:** Synthesize a normative Concept of Operations (`CONOPS.md`) from raw customer intent and operational flight envelope parameters.
>
> **Inputs:**
> - Unstructured customer intent, operational parameters, population density metrics, flight range/altitude bounds.
>
> **Outputs:**
> - `docs/conops/CONOPS.md` establishing mission goals, operational phases (`PRE_FLIGHT`, `TAKEOFF`, `CRUISE`, `INSPECTION`, `APPROACH`, `LANDING`, `RTA_BACKUP`), environmental boundaries, system interfaces, and baseline JARUS SORA v2.5 Ground Risk Class (GRC) and Air Risk Class (ARC) assignments.
>
> **Execution Instructions:**
> 1. Read `.pipeline/constitution.md` for domain rules and safety engineering quality gates.
> 2. Parse operational flight envelope parameters and airspace parameters.
> 3. Ensure all operational phases and safety boundaries are explicitly specified without invent-your-own requirement assumptions."

#### 6.3.2 Worker 0B: STPA / FMECA / SORA SAIL Hazard Worker Prompt
> **Worker 0B Prompt:**
>
> "Adopt the pre-spec safety engineering capabilities for Pipeline 0 Worker 0B.
>
> **Task:** Perform System-Theoretic Process Analysis (STPA) and Failure Mode, Effects, and Criticality Analysis (FMECA) hazard modeling.
>
> **Inputs:**
> - `docs/conops/CONOPS.md` generated by Worker 0A
> - Target safety frameworks: JARUS SORA v2.5 (SAIL I–VI), SAE ARP4761/ARP4754A, ASTM F3269-17 RTA
>
> **Outputs:**
> - `docs/safety/STPA_MATRIX.md` defining System Losses ($L$), System Hazards ($H$), Control Structure Diagrams, Unsafe Control Actions ($UCA$), Safety Constraints ($SC$), FMECA failure modes, and required SORA SAIL risk mitigations.
>
> **Execution Instructions:**
> 1. Read `.pipeline/constitution.md` for safety governance and quality gates.
> 2. Analyze control actions and identify all Unsafe Control Actions ($UCA$).
> 3. Formulate concrete Safety Constraints ($SC$) linking back to System Hazards ($H$) and System Losses ($L$)."

#### 6.3.3 Worker 0C: SysML v2 Authoring Worker Prompt
> **Worker 0C Prompt:**
>
> "Adopt the pre-spec safety engineering capabilities for Pipeline 0 Worker 0C.
>
> **Task:** Author formal SysML v2 textual models and serialize the inter-pipeline AST JSON handoff contract.
>
> **Inputs:**
> - `docs/conops/CONOPS.md` from Worker 0A
> - `docs/safety/STPA_MATRIX.md` from Worker 0B
>
> **Outputs:**
> - `DEAP_MODEL.sysml` containing SysML v2 requirements, parts, ports, and safety statecharts.
> - `pipeline0_handoff_contract.json` containing the immutable AST handoff payload for Pipeline 1 Agile Backlog projection.
>
> **Execution Instructions:**
> 1. Read `.pipeline/constitution.md` for SysML v2 textual model governance and AST serialization rules.
> 2. Construct SysML v2 textual models matching OMG SysML v2 metamodel standards.
> 3. Export and validate `pipeline0_handoff_contract.json` against `https://deap.engine/schemas/pipeline0_handoff_v1.json` ensuring 100% bidirectional traceability across STPA safety constraints, SysML v2 requirements, and downstream Feature projections."

---

## Expected Outputs

### Specification Pipeline
A perfectly synchronized taxonomy on your live issue tracker board:

1. **Epics (`epic`)**: High-level structural containers.
2. **Features (`feature`)**: Granular technical building blocks with verbatim spec text and dependency links.
3. **User Stories (`user-story`)**: Object-oriented BDD scenarios mapped to required Features.
4. **Use Cases (`use-case`)**: Formal UML system interactions mapped down to User Stories and Features.

### Implementation Pipeline
For each delivered feature:

1. **Solution Walkthrough** (`<walkthrough_dir>/feat-<Issue_Number>-solution.md` or as configured): Cumulative record of changes, testing, and verification, including a **Code Realization Table** mapping features/attributes to implemented source files, classes, and functions.
2. **Passing test suite**: All tests green with raw output as evidence.
3. **Closed Tracker Issue**: With direct link to the committed solution walkthrough.
4. **Updated Epic checklist**: Feature marked `[x]`, Epic auto-closed when all features complete.

*Note: Skills automatically bootstrap repository labels (epic, feature, user-story, use-case) via the configured label bootstrap command.*

---

## Tessl Integration (Skill Registry & Evaluation)

This pipeline's skills conform to the [Agent Skills specification](https://agentskills.io/specification) and are compatible with [Tessl](https://tessl.io/) — the package manager and governance platform for AI agent skills.

### Install Skills via Tessl

**For Stable Version (`main`):**
```bash
tessl init --agent claude-code --agent cursor --agent gemini
tessl install github:gintatkinson/digital-pipeline-repo
tessl install github:gintatkinson/digital-pipeline-repo --skill spec-orchestrator
```

**For Refactored Version (`refactor`):**
```bash
tessl init --agent claude-code --agent cursor --agent gemini
tessl install github:gintatkinson/digital-pipeline-repo#refactor
tessl install github:gintatkinson/digital-pipeline-repo#refactor --skill spec-orchestrator
```

### Publish to a Private Registry

Package your organization's customized pipeline skills for team-wide distribution:

```bash
# Import a skill into Tessl plugin format
tessl skill import skills/spec-orchestrator

# Review and auto-optimize skill quality
tessl skill review skills/spec-orchestrator --optimize

# Publish to your org's private workspace
tessl skill publish skills/spec-orchestrator --workspace your-org
```

### Evaluate Skill Quality

Tessl provides three evaluation layers critical for safety-critical domains:

- **Skill Review** — `tessl skill review skills/spec-orchestrator --threshold 80` scores structural quality and compliance with the Agent Skills spec. Use as a CI gate.
- **Task Evals** — `tessl eval run` tests whether agents perform better *with* your skills vs *without*, measuring specification accuracy and compliance.
- **Scenario Evals** — `tessl scenario generate` creates realistic evaluation scenarios from your skills to regression-test agent behavior.

### MCP Integration

```bash
# Start the Tessl MCP server for structured agent access
tessl mcp start
```

Agents pull version-locked context from the registry via MCP instead of parsing raw markdown files — preventing context-window overflow and ensuring version consistency across teams.

### Tessl + This Pipeline Architecture

```
┌──────────────────────────────────────────┐
│        TESSL REGISTRY (SaaS/Private)     │
│  Versioned, evaluated plugin packages    │
│  for all domain-specific pipelines       │
└─────────────────────┬────────────────────┘
                      │  tessl install / MCP
                      ▼
┌──────────────────────────────────────────┐
│         AI AGENT (any runtime)           │
│  Claude Code / Gemini / Cursor / Copilot │
│  Pulls verified skills + context bundles │
└─────────────────────┬────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐  ┌──────────────────┐
│  RULES (always)  │  │ SKILLS (on-task) │
│  serial-exec     │  │ spec-orchestrator│
│  tdd-mandate     │  │ Workers A/B/C    │
│  verification    │  │ feature-impl     │
│  constitution    │  │ constitution     │
│  platform-indep  │  │                  │
│  tracker-sot     │  │                  │
│  no-browser      │  │                  │
└──────────────────┘  └──────────────────┘
     Always loaded       Loaded per task
```

---

## Spec Kit Compatibility

This pipeline can also be used **alongside** [Spec Kit](https://github.com/github/spec-kit) without conflict:

- **`specify init`** can bootstrap agent-specific config files (`.claude/`, `.windsurf/`, etc.) in project repos.
- **`.specify/memory/constitution.md`** is analogous to this pipeline's constitution — use whichever convention your project prefers.
- **This pipeline replaces** `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, and `/speckit.implement` with its own more rigorous equivalents (schema-to-spec automation, The Grill, micro-task TDD, two-stage review).
- **This pipeline does NOT depend on Spec Kit.** All skills are pure markdown files that any agent can read directly — no CLI installation required.

## Documentation at: https://github.com/gintatkinson/digital-pipeline-repo

