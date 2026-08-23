# Schema Directory

This directory serves as the root repository for input specification schemas, interface definitions, and data models for the Digital Engineering Autonomous Pipeline (DEAP).

## Purpose & Scope

The `schema/` directory contains heterogeneous interface definitions, domain schemas, and high-level architectural models that define the contracts, data structures, and interactions for the system under design.

## Upstream Clean Landing Zone Invariant

In upstream distribution templates (`DEAP-*`), the `schema/` directory is strictly maintained as a **clean landing zone** containing only `.gitkeep`. Upstream distribution templates contain only the abstract compiler, linters, and empty specification directories. Concrete project schemas, domain models, and interface specifications are never committed to upstream templates; they reside exclusively in downstream application workspaces initialized via `scripts/install_pipeline.sh`.

Supported specification formats include:
- **SysML v2** (`.sysml`): Textual modeling for system architecture, item definitions, parts, ports, requirement definitions, state machines, and use cases.
- **OpenAPI 3.0 / 3.1 & JSON Schemas** (`.json`, `.yaml`, `.yml`): REST APIs, JSON data schemas, and object payload definitions.
- **AUTOSAR ARXML** (`.arxml`, `.xml`): Classic and Adaptive AUTOSAR software component descriptions, port interfaces, and package definitions.
- **OMG IDL** (`.idl`): Interface Definition Language files for DDS/CORBA middleware contracts and topics.
- **Protocol Buffers** (`.proto`): Structured serialization schemas for inter-process communication and message exchanges.

## Primary Commercial Toolchain Integration Context

This project explicitly declares **MATLAB / Simulink / Stateflow / Embedded Coder** as the Primary Tier-1 Commercial Toolchain Integration Context (Model-Based Design, Control Law Synthesis, DO-178C C/SPARK Ada code generation). SysML v2 serves as the formal Single Source of Truth (SSOT) feeding these downstream synthesis and verification engines.

## SysML v2 Complete Package Definition Mandate

In accordance with [`rules/sysml-ssot-completeness.md`](file:///Users/perkunas/jail/DEAP-uas-infrastructure-safety/rules/sysml-ssot-completeness.md), SysML v2 models must not be partial structural skeletons. Schema models MUST define complete, self-contained packages containing:

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

To prevent model drift between textual specifications and architectural models, DEAP enforces a strict **bidirectional elaboration loop**:

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
 [Downstream Backlog Specifications]                                       │
   ├─ Epics & Features       <── derived from `package`, `part def`        │
   ├─ User Stories           <── derived from `action def`, `state def`    │
   └─ Use Cases              <── derived from `use case def`               │
           │                                                               │
           └──────── Bidirectional Synchronization & Enrichment ───────────┘
```

- **Tandem Elaboration**: When downstream specification workers (Phases 1–3) elaborate edge cases, exception flows, or refined interactions, any newly introduced structural elements, states, ports, or use cases MUST be reflected back into the SysML v2 model (`.pipeline/schema.sysml`).
- **100% Bidirectional Parity**: Every backlog item (Epic, Feature, User Story, Use Case) must trace 1:1 to a formal SysML v2 AST node, and all SysML v2 AST definitions must be fully covered in downstream specifications.
- **Continuous Digest Verification**: Any elaboration step that touches specifications must verify AST digest consistency (`.pipeline/schema-digest.json`) against the SysML v2 SSOT before validation gates pass.

## Usage Guidelines
- In upstream distribution templates (`DEAP-*`), `schema/` remains a clean landing zone containing only `.gitkeep` awaiting user-provided schemas.
- In downstream workspaces (installed via `scripts/install_pipeline.sh`), place all project schema specifications into `schema/` (or structured subdirectories within `schema/`).
- Commit schemas alongside downstream pipeline configuration to preserve end-to-end traceability and model parity.
- Adhere strictly to [`rules/sysml-ssot-completeness.md`](file:///Users/perkunas/jail/DEAP-uas-infrastructure-safety/rules/sysml-ssot-completeness.md) across all modeling and specification tasks.


