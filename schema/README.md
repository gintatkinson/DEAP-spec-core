# Schema Directory

This directory serves as the root repository for input specification schemas, interface definitions, and data models for the Digital Engineering Autonomous Pipeline (DEAP).

## Purpose & Scope

The `schema/` directory contains heterogeneous interface definitions, domain schemas, and high-level architectural models that define the contracts, data structures, and interactions for the system under design.

## Upstream Clean Landing Zone Invariant

In upstream distribution templates (`DEAP-*`), the `schema/` directory is strictly maintained as a **clean landing zone** containing only `.gitkeep` and `README.md`. Upstream distribution templates contain only the abstract compiler, linters, and empty specification directories. Concrete project schemas, domain models, and interface specifications are never committed to upstream templates; they reside exclusively in downstream application workspaces initialized via `scripts/install_pipeline.sh`.

Supported specification formats include:
- **SysML v2** (`.sysml`): Textual modeling for system architecture, item definitions, parts, ports, requirement definitions, state machines, and use cases.
- **OpenAPI 3.0 / 3.1 & JSON Schemas** (`.json`, `.yaml`, `.yml`): REST APIs, JSON data schemas, and object payload definitions.
- **AUTOSAR ARXML** (`.arxml`, `.xml`): Classic and Adaptive AUTOSAR software component descriptions, port interfaces, and package definitions.
- **OMG IDL** (`.idl`): Interface Definition Language files for DDS/CORBA middleware contracts and topics.
- **Protocol Buffers** (`.proto`): Structured serialization schemas for inter-process communication and message exchanges.

## Boundary: Machine Schemas vs. Human-Authored Mission Intent

DEAP enforces a clear architectural boundary between machine-readable schemas in `schema/` and human-authored operational intent in `docs/conops/` (`MISSION_INTENT.md`):

| Dimension | Machine Schemas (`schema/`) | Mission Intent Contract (`docs/conops/` / `MISSION_INTENT.md`) |
| :--- | :--- | :--- |
| **Primary Audience** | Automated compilers, parsers, code generators, and AST analyzers | Systems engineers, safety certifiers, operators, and LLM agent workers |
| **Artifact Format** | SysML v2 (`.sysml`), OpenAPI/JSON Schema (`.json`/`.yaml`), AUTOSAR (`.arxml`), IDL (`.idl`), Protobuf (`.proto`) | Markdown documents (`docs/conops/*.md`) adhering to canonical schema |
| **Content & Scope** | Structural types, port definitions, data models, state machines, and behavioral interfaces | Operational objectives, flight envelopes ($h_{\min}..h_{\max}, v_{\max}$), airspace rules, population density, and stakeholder roles |
| **Ingestion Engine** | `sysmlv2_ingest.py` (AST translation to `.pipeline/schema.sysml`) & Pipeline 0 Worker 0A (Ingestion for physical & functional boundary synthesis) | Pipeline 0 Worker 0A (Universal Multi-Document & Schema Ingestion synthesizing `docs/conops/CONOPS.md`) |
| **Toolchain Target** | Embedded Coder, ROS2 interfaces, DDS IDL, SLDV formal models | High-level CONOPS, STPA hazard matrices, SORA SAIL models, and SysML v2 models |


## Primary Commercial Toolchain Integration Context

This project explicitly declares **MATLAB / Simulink / Stateflow / Embedded Coder** as the Primary Tier-1 Commercial Toolchain Integration Context (Model-Based Design, Control Law Synthesis, DO-178C C/SPARK Ada code generation). SysML v2 serves as the formal Single Source of Truth (SSOT) feeding these downstream synthesis and verification engines.

## SysML v2 Complete Package Definition Mandate

In accordance with [`rules/sysml-ssot-completeness.md`](rules/sysml-ssot-completeness.md), SysML v2 models must not be partial structural skeletons. Schema models MUST define complete, self-contained packages containing:

1. **Structural Blocks (`part def`, `item def`)**: Subsystems, physical/logical components, telemetry items, data definitions, and composite hierarchies.
2. **Requirement Definitions (`requirement def`)**: Functional requirements and safety invariants derived from STPA (Unsafe Control Actions, Loss Scenarios) and FMECA, with explicit `assume`/`require` expressions and `satisfy`/`verify` relationships.
3. **Behavioral States & Modes (`state def`)**: Operational states, mode managers, entry/exit actions, and guarded transitions.
4. **Interface Boundaries & Ports (`port def`)**: Strongly-typed directional ports (`in`, `out`, `inout`) defining electrical, logical, or network contracts.
5. **System Use Cases (`use case def`)**: Explicit use case blocks specifying:
   - `subject`: The subsystem or component (`part def`) realizing the use case.
   - `actor`: Primary initiating actors and secondary participating actors bound via typed ports.
   - `objective`: Formal operational goal, preconditions, and success criteria.
   - `include` / `extend`: Formal relationships connecting modular or conditional sub-use-cases.

## SysML v2 Universal Ingestion Workflow

Heterogeneous schemas placed in `schema/` are canonically ingested and translated into SysML v2 semantic AST models and downstream engineering contracts using the ingestion engine:

```bash
python3 skills/spec-orchestrator/scripts/sysmlv2_ingest.py \
  --schema schema/<your-schema-file> \
  --format auto \
  --out .pipeline/schema.sysml \
  --digest .pipeline/schema-digest.json
```

### Ingestion Pipeline Features
1. **Automatic Format Detection**: Automatically determines format based on file extension and syntactic cues.
2. **Canonical SysML v2 Generation**: Emits standardized SysML v2 textual packages (`.sysml`) capturing data types, interfaces, ports, states, requirements, and use cases.
3. **Cryptographic Integrity & Digest**: Generates `.pipeline/schema-digest.json` containing SHA-256 integrity hash, line count, AST node metrics, and symbol tables.
4. **Toolchain & Downstream Integration**: Feeds downstream synthesis including MATLAB / Simulink / Stateflow model generation, control law synthesis, and DO-178C C/SPARK Ada code contracts.

## Bidirectional Elaboration Loop & Zero Model Drift

To prevent model drift between textual specifications and architectural models, DEAP enforces a strict **bidirectional elaboration loop** governed by [`docs/architecture/blueprints/SYSML_SSOT_BIDIRECTIONAL_SYNCHRONIZATION_ARCHITECTURE.md`](docs/architecture/blueprints/SYSML_SSOT_BIDIRECTIONAL_SYNCHRONIZATION_ARCHITECTURE.md):

```
 [Heterogeneous Schemas] (schema/)
           │
           ▼
 [SysML v2 Ingestion Engine] (sysmlv2_ingest.py)
           │
           ▼
 [Canonical SysML v2 AST Model] (.pipeline/schema.sysml) ─── 100% SSOT ───┐
           │                                                               │
     Formal AST Mapping (Zero Heuristic Prose Parsing)                     │
           │                                                               │
           ▼                                                               │
 [Downstream Backlog Specifications] (docs/)                               │
   ├─ Epics & Features       <── derived from `package`, `part def`        │
   ├─ User Stories           <── derived from `action def`, `state def`    │
   └─ Use Cases              <── derived from `use case def`               │
           │                                                               │
           ▼                                                               │
 [Automated Reverse Sync Engine] (compile_sysml.py --reverse-sync)        │
           │                                                               │
           └──────── Bidirectional Delta Merge & Digest Update ────────────┘
```

### Automated Reverse Synchronization Standard

When downstream specification workers (Phases 1–3) elaborate edge cases, exception flows, state transitions, or refined interactions, any newly introduced structural elements, states, ports, or use cases MUST be synchronized back into the SysML v2 model using the reverse compilation engine:

```bash
python3 scripts/compile_sysml.py --reverse-sync
```

1. **AST Delta Extraction**: Scans all backlog markdown specifications (`docs/epics`, `docs/features`, `docs/user-stories`, `docs/use-cases`), BDD Given-When-Then action signatures, Mermaid state diagrams, interface tables, and STPA/FMECA hazard matrices.
2. **Semantic AST Merging**: Ingests deltas and updates `.pipeline/schema.sysml` via non-destructive AST merging in `sysmlv2_ast.py`.
3. **Cryptographic Parity Digest**: Recomputes `.pipeline/schema-digest.json` with updated SHA-256 checksum and symbol tables.
4. **22-Gate Parity Lock**: Verifies 100% model coverage, UML 2.5.1 conformance, and behavioral trigger parity via `verify_model_coverage.py --spec-only`.

## Usage Guidelines
- In upstream distribution templates (`DEAP-*`), `schema/` remains a clean landing zone containing only `.gitkeep` awaiting user-provided schemas.
- In downstream workspaces (installed via `scripts/install_pipeline.sh`), place all project schema specifications into `schema/` (or structured subdirectories within `schema/`).
- Commit schemas alongside downstream pipeline configuration to preserve end-to-end traceability and model parity.
- Adhere strictly to [`rules/sysml-ssot-completeness.md`](rules/sysml-ssot-completeness.md) across all modeling and specification tasks.


