# Schema Directory

This directory serves as the root repository for input specification schemas, interface definitions, and data models for the Digital Engineering Autonomous Pipeline (DEAP).

## Purpose & Scope

The `schema/` directory contains heterogeneous interface definitions, domain schemas, and high-level architectural models that define the contracts, data structures, and interactions for the system under design.

Supported specification formats include:
- **SysML v2** (`.sysml`): Textual modeling for system architecture, item definitions, parts, ports, and action flows.
- **OpenAPI 3.0 / 3.1 & JSON Schemas** (`.json`, `.yaml`, `.yml`): REST APIs, JSON data schemas, and object payload definitions.
- **AUTOSAR ARXML** (`.arxml`, `.xml`): Classic and Adaptive AUTOSAR software component descriptions, port interfaces, and package definitions.
- **OMG IDL** (`.idl`): Interface Definition Language files for DDS/CORBA middleware contracts and topics.
- **Protocol Buffers** (`.proto`): Structured serialization schemas for inter-process communication and message exchanges.

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
2. **Canonical SysML v2 Generation**: Emits standardized SysML v2 textual packages (`.sysml`) capturing data types, interfaces, ports, and structures.
3. **Cryptographic Integrity & Digest**: Generates `.pipeline/schema-digest.json` containing SHA-256 integrity hash, line count, AST node metrics, and symbol tables.
4. **Toolchain & Downstream Integration**: Feeds downstream synthesis including MATLAB / Simulink / Stateflow model generation, control law synthesis, and DO-178C C/SPARK Ada code contracts.

## Usage Guidelines
- Place all raw or upstream schema specifications into `schema/` (or structured subdirectories within `schema/`).
- Commit schemas alongside pipeline configuration to preserve end-to-end traceability and model parity.
