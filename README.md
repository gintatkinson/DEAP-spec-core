# DEAP Spec Core (`DEAP-spec-core`)

[![DEAP Spec Core CI](https://github.com/gintatkinson/DEAP-spec-core/actions/workflows/ci.yml/badge.svg)](https://github.com/gintatkinson/DEAP-spec-core/actions)

`DEAP-spec-core` contains the master safety architecture blueprints, SysML v2 models, YANG protocol schemas, and specification engineering skills for the Distributed Ecosystem Architecture Platform (DEAP).

## Repository Overview

- **Safety & Domain Architecture Blueprints**: [docs/architecture/](docs/architecture/)
  - Master safety model, hazard analysis, risk matrix, and SysML v2 specification blueprints.
- **Pipeline Governance & Profiles**: [.pipeline/](.pipeline/)
  - System constitution ([.pipeline/constitution.md](.pipeline/constitution.md)) and platform profiles ([.pipeline/profiles/](.pipeline/profiles/)).
- **Agent Governance**: [.agents/AGENTS.md](.agents/AGENTS.md)
  - Agentic rules, planning gates, and compliance protocols.
- **Specification Engineering Skills**: [skills/](skills/)
  - `project-constitution`: Platform profile and constitution management ([skills/project-constitution/SKILL.md](skills/project-constitution/SKILL.md)).
  - `schema-specification-engineering`: Schema to Agile Epics transformation ([skills/schema-specification-engineering/SKILL.md](skills/schema-specification-engineering/SKILL.md)).
  - `spec-orchestrator`: End-to-end specification engineering pipeline ([skills/spec-orchestrator/SKILL.md](skills/spec-orchestrator/SKILL.md)).
  - `spec-usecase-engineering`: Use case extraction and OOA/OOD modeling ([skills/spec-usecase-engineering/SKILL.md](skills/spec-usecase-engineering/SKILL.md)).
  - `spec-user-story-engineering`: BDD user story engineering ([skills/spec-user-story-engineering/SKILL.md](skills/spec-user-story-engineering/SKILL.md)).
  - `spec-implementation-auditor`: Spec vs code parity auditing ([skills/spec-implementation-auditor/SKILL.md](skills/spec-implementation-auditor/SKILL.md)).
- **Compilers & Scripts**: [scripts/](scripts/)
  - SysML v2 model compiler ([scripts/compile_sysml.py](scripts/compile_sysml.py))
  - YANG protocol compiler ([compile_yang.py](compile_yang.py))

## Verification & Testing

To run the full test suite and audit suite:

```bash
python3 -m pytest tests/
```
