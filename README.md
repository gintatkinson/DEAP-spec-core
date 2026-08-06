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

### Direct Copy Installation

Copy the pipeline directories and (optionally) the application templates into your project repository.

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

