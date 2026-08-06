# DEAP Migration Handoff Document

## Critical Understanding (Read This First)

**DEAP is version 2 of `digital-pipeline-repo`.** It is not a separate product.
`digital-pipeline-repo` is the working monolith (v1). DEAP is the same pipeline,
properly decomposed into a polyrepo architecture (v2).

**Official product name**: `Digital Engineering Agentic Pipeline (DEAP)`

**Forbidden names** — never use these under any circumstance:
- `Digital Systems Engineering Pipeline` (hallucinated)
- `Digital Enterprise Architecture Pipeline` (hallucinated)
- `Digital Enterprise` (hallucinated)

---

## Architecture: v1 → v2 Migration Map

| v1 (`digital-pipeline-repo`) | v2 DEAP Repo | Status |
|---|---|---|
| `skills/spec-orchestrator/` | `DEAP-spec-core/skills/spec-orchestrator/` | ⚠️ Partial — missing full skill sync |
| `skills/schema-specification-engineering/` | `DEAP-spec-core/skills/schema-specification-engineering/` | ⚠️ Partial |
| `skills/spec-usecase-engineering/` | `DEAP-spec-core/skills/spec-usecase-engineering/` | ⚠️ Partial |
| `skills/spec-user-story-engineering/` | `DEAP-spec-core/skills/spec-user-story-engineering/` | ⚠️ Partial |
| `skills/feature-driven-implementation/` | `DEAP-implementation-driver/skills/feature-driven-implementation/` | ⚠️ Partial |
| `skills/debug-protocol/` | `DEAP-implementation-driver/skills/debug-protocol/` | ⚠️ Partial |
| `skills/adversarial-code-auditor/` | `DEAP-implementation-driver/skills/adversarial-code-auditor/` | ⚠️ Partial |
| `skills/performance-profiling-test-automation/` | `DEAP-implementation-driver/` | ❌ Not migrated |
| `skills/spec-implementation-auditor/` | `DEAP-implementation-driver/` | ❌ Not migrated |
| `skills/project-constitution/` | `DEAP-spec-core/` | ❌ Not migrated |
| `rules/` (15 files) | `DEAP-implementation-driver/rules/` | ❌ Not migrated |
| `.agents/AGENTS.md` | All DEAP repos | ⚠️ Partial — DEAP-implementation-driver only |
| `.pipeline/` | All DEAP repos | ⚠️ Copied but wrong product name throughout |
| `app_flutter/` | `DEAP-profile-flutter-app/app_flutter/` | ⚠️ Exists but governance incomplete |
| `web_react/` | `DEAP-profile-react-web/web_react/` | ⚠️ Exists but governance incomplete |
| `scripts/` | `DEAP-spec-core/` or `DEAP-implementation-driver/` | ❌ Not migrated |
| Domain platform `DEAP-avionic-flight-safety` | `DEAP-avionic-flight-safety` | ✅ Standalone downstream polyrepo (`https://github.com/gintatkinson/DEAP-avionic-flight-safety`) |
| Domain platform `DEAP-uas-infrastructure-safety` | `DEAP-uas-infrastructure-safety` | ✅ Standalone downstream polyrepo (`https://github.com/gintatkinson/DEAP-uas-infrastructure-safety`) |

---

## Empirical State of Every Repository

### `digital-pipeline-repo` — v1 Source of Truth
- **Path**: `/Users/perkunas/jail/digital-pipeline-repo`
- **GitHub**: `https://github.com/gintatkinson/digital-pipeline-repo`
- **HEAD**: `ee6e363`
- **Parity Auditor Tests**: **306 passed, 0 failed** ✅
- **Full Test Suite**: **11 failed, 535 passed, 17 skipped** ⚠️ (pre-existing — confirmed unchanged from pre-session baseline at ee6e363)
- **Git sync**: Clean — `git diff origin/main` empty ✅

**Wrong product name occurrences** (must fix before using as migration source):
- `.pipeline/constitution.md` — line 3: `project: "Digital Systems Engineering Pipeline"`
- `.pipeline/constitution.md` — line 9: `# Project Constitution: Digital Systems Engineering Pipeline`
- `.pipeline/logical-ui/logical-components.md` — body text
- `.pipeline/profiles/flutter.md` — frontmatter `project:`
- `.pipeline/profiles/react.md` — frontmatter `project:`
- `.pipeline/upstream/pipeline-tooling.md` — frontmatter `project:`

**Complete skills inventory** (source of truth):
1. `adversarial-code-auditor`
2. `debug-protocol`
3. `feature-driven-implementation`
4. `performance-profiling-test-automation`
5. `project-constitution`
6. `schema-specification-engineering`
7. `spec-implementation-auditor`
8. `spec-orchestrator`
9. `spec-usecase-engineering`
10. `spec-user-story-engineering`

**Complete rules inventory** (source of truth, 15 files):
`behavioral-trigger-coverage.md`, `behavioral_triggers.json`, `codebase-compliance.md`,
`constitution-first.md`, `document-references.md`, `domain-engineering-standards.md`,
`no-browser-automation.md`, `platform-independence.md`, `role-boundary-lock.md`,
`serial-execution.md`, `tdd-mandate.md`, `tracker-source-of-truth.md`,
`uml-model-integrity.md`, `user-authorization-lock.md`, `verification-required.md`

---

### `DEAP-spec-core`
- **Path**: `/Users/perkunas/jail/DEAP-spec-core`
- **GitHub**: `https://github.com/gintatkinson/DEAP-spec-core`
- **HEAD**: `f14b97f`
- **README**: ❌ Missing
- **Skills present**: `schema-specification-engineering`, `spec-orchestrator`, `spec-usecase-engineering`, `spec-user-story-engineering`
- **Skills missing**: `project-constitution`, `spec-implementation-auditor`
- **Wrong names in `.pipeline/`**: Yes — same 6 files as `digital-pipeline-repo`
- **Parity auditor tests**: 302 passed, 3 pre-existing failures (version drift)

---

### `DEAP-implementation-driver`
- **Path**: `/Users/perkunas/jail/DEAP-implementation-driver`
- **GitHub**: `https://github.com/gintatkinson/DEAP-implementation-driver`
- **HEAD**: `431a2c5`
- **README**: ❌ Missing
- **Skills present**: `adversarial-code-auditor`, `debug-protocol`, `feature-driven-implementation`
- **Skills missing**: `performance-profiling-test-automation`, `spec-implementation-auditor`
- **`.pipeline/`**: ❌ Missing entirely
- **`rules/`**: ❌ Missing entirely
- **Tests**: 8 failed, 3 passed

---

### `DEAP-profile-flutter-app`
- **Path**: `/Users/perkunas/jail/DEAP-profile-flutter-app`
- **GitHub**: `https://github.com/gintatkinson/DEAP-profile-flutter-app`
- **HEAD**: `32d9461`
- **README**: ❌ Missing
- **`app_flutter/`**: ✅ Present (copied from v1)
- **`profile.yaml`**: ⚠️ One-line stub (`name: flutter-app`)
- **`rules/`**: ⚠️ Present but unpopulated
- **`.pipeline/`**: ❌ Missing
- **`.agents/`**: ❌ Missing

---

### `DEAP-profile-react-web`
- **Path**: `/Users/perkunas/jail/DEAP-profile-react-web`
- **GitHub**: `https://github.com/gintatkinson/DEAP-profile-react-web`
- **HEAD**: `c8be3b6`
- **README**: ❌ Missing
- **`web_react/`**: ✅ Present (copied from v1)
- **`profile.yaml`**: ⚠️ One-line stub
- **`rules/`**: ⚠️ Present but unpopulated
- **`.pipeline/`**: ❌ Missing
- **`.agents/`**: ❌ Missing

---

### `DEAP-profile-backend-api`
- **Path**: `/Users/perkunas/jail/DEAP-profile-backend-api`
- **GitHub**: `https://github.com/gintatkinson/DEAP-profile-backend-api`
- **HEAD**: `d1a2d17`
- **README**: ❌ Missing
- **`profile.yaml`**: ⚠️ One-line stub
- **`.pipeline/`**: ❌ Missing
- **`.agents/`**: ❌ Missing

---

### `DEAP-profile-vhdl-hardware`
- **Path**: `/Users/perkunas/jail/DEAP-profile-vhdl-hardware`
- **GitHub**: `https://github.com/gintatkinson/DEAP-profile-vhdl-hardware`
- **HEAD**: `2d881d7`
- **README**: ❌ Missing
- **`profile.yaml`**: ⚠️ One-line stub
- **`.pipeline/`**: ❌ Missing
- **`.agents/`**: ❌ Missing

---

### `DEAP-avionic-flight-safety`
- **GitHub**: `https://github.com/gintatkinson/DEAP-avionic-flight-safety`
- **Scope**: Civil Avionic Flight Safety Platform (DO-178C DAL A-E, DO-254, ARP4754A/4761, SPARK Ada / MISRA-C)
- **Status**: ✅ Standalone Downstream Polyrepo

---

### `DEAP-uas-infrastructure-safety`
- **GitHub**: `https://github.com/gintatkinson/DEAP-uas-infrastructure-safety`
- **Scope**: Low-Altitude UAS Infrastructure Safety Platform (SORA v2.5 SAIL I-VI, ASTM F3269-17 RTA, ASTM F3411-22a Remote ID, RTCA DO-365B DAA, ROS2 / PX4)
- **Status**: ✅ Standalone Downstream Polyrepo

---

## Ordered Work Remaining

Execute strictly in this order. Do not skip steps.

### Phase 1 — Fix `digital-pipeline-repo` Source of Truth

**Step 1.1 — Fix wrong product names (6 files)**
Replace all occurrences of `Digital Systems Engineering Pipeline` with
`Digital Engineering Agentic Pipeline (DEAP)` in:
- `.pipeline/constitution.md`
- `.pipeline/logical-ui/logical-components.md`
- `.pipeline/profiles/flutter.md`
- `.pipeline/profiles/react.md`
- `.pipeline/upstream/pipeline-tooling.md`

Verify: `grep -ri "Digital Systems Engineering" .pipeline/` returns empty.

**Step 1.2 — Fix 11 failing tests using `adversarial-code-auditor` + `debug-protocol` skills**

Group A — Rule Contract (6 tests in `tests/test_rule_contracts.py`):
- Register `markdown-broken-link-reference`, `mermaid-diagram-unquoted-brackets-forbidden`,
  `mermaid-node-label-must-be-quoted` in the contract registry
- Fix missing documentation/enforcement anchors for `sysml-extraction-missing`,
  `schema-container-consolidation-forbidden`, `class-diagram-must-model-schema-containment`

Group B+C — Spec-Orchestrator SKILL.md (3 tests):
- Add `generation_mode` frontmatter key and `_validate_subagent_isolation` reference
- Expand isolation section to >500 chars
- Add the word "namespacing" to the isolation section

Group D — Migration Ledger (2 tests in `tests/test_validator_findings_migration_issue304.py`):
- Register `link_validator.py` in the migration ledger

Gate: `python3 -m pytest tests/ -q` → **0 failed** before proceeding.

**Step 1.3 — Commit and push `digital-pipeline-repo` clean state**
- `git add -A && git commit -m "fix: correct product name to DEAP and resolve 11 governance test failures"`
- `git push origin main`
- Verify `git diff origin/main` is empty.

---

### Phase 2 — Migrate `DEAP-spec-core`

For each item, copy from `digital-pipeline-repo`, verify, commit:

1. Sync skills: copy `skills/project-constitution/` and `skills/spec-implementation-auditor/`
2. Sync `.pipeline/` (with corrected product names from Phase 1)
3. Sync `.agents/AGENTS.md`
4. Write `README.md` with correct title and canonical install script
5. Run parity auditor tests — must match `digital-pipeline-repo` baseline
6. Commit and push

---

### Phase 3 — Migrate `DEAP-implementation-driver`

1. Sync missing skills: `performance-profiling-test-automation`, `spec-implementation-auditor`
2. Copy `rules/` (all 15 files) from `digital-pipeline-repo`
3. Copy `.pipeline/` (with corrected product names)
4. Copy `.agents/AGENTS.md`
5. Write `README.md`
6. Run tests — fix until 0 failed
7. Commit and push

---

### Phase 4 — Migrate Profile Repos (flutter, react, backend-api, vhdl-hardware)

For each profile repo:
1. Copy `rules/` from `digital-pipeline-repo`
2. Copy `.pipeline/` with profile-specific `profiles/<platform>.md`
3. Copy `.agents/AGENTS.md`
4. Write comprehensive `profile.yaml` (not a one-line stub)
5. Write `README.md`
6. Commit and push

---

### Phase 5 — Install Script and Canonical Installation

1. Update `scripts/install_pipeline.py` in `digital-pipeline-repo` with correct DEAP name
2. Verify `README.md` and `install-guide.md` in `digital-pipeline-repo` contain the canonical
   1-block copy-paste installation script:
```bash
git clone https://github.com/gintatkinson/digital-pipeline-repo.git ./.tmp-pipeline
rm -rf ./skills ./rules ./.pipeline ./.agents ./scripts ./app_flutter ./web_react
cp -RP ./.tmp-pipeline/skills ./
cp -RP ./.tmp-pipeline/rules ./
cp -RP ./.tmp-pipeline/.pipeline ./
rm -rf ./.pipeline/upstream
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
python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py
```

---

## Execution Rules for Next Agent

1. **Read `.agents/AGENTS.md` and `.agents/skills/debug-protocol/SKILL.md` and `.agents/skills/adversarial-code-auditor/SKILL.md` as first actions.**
2. **Work Phase 1 first.** Do not touch DEAP repos until `digital-pipeline-repo` is 0 failures and correct names.
3. **One phase at a time.** Complete and verify each phase before starting the next.
4. **Coordinator runs all verification commands personally.** Do not accept subagent self-reports as proof.
5. **After each phase**: run `git diff origin/main` and confirm empty before declaring phase done.
6. **Never use these names**: `Digital Systems Engineering Pipeline`, `Digital Enterprise Architecture Pipeline`, `Digital Enterprise`, `DEAP` as a standalone acronym without expansion.
7. **Always expand DEAP**: `Digital Engineering Agentic Pipeline (DEAP)`.

---

## Key File Paths

| Asset | Path |
|---|---|
| v1 source repo | `/Users/perkunas/jail/digital-pipeline-repo` |
| DEAP spec core | `/Users/perkunas/jail/DEAP-spec-core` |
| DEAP implementation driver | `/Users/perkunas/jail/DEAP-implementation-driver` |
| DEAP Flutter profile | `/Users/perkunas/jail/DEAP-profile-flutter-app` |
| DEAP React profile | `/Users/perkunas/jail/DEAP-profile-react-web` |
| DEAP Backend API profile | `/Users/perkunas/jail/DEAP-profile-backend-api` |
| DEAP VHDL Hardware profile | `/Users/perkunas/jail/DEAP-profile-vhdl-hardware` |
| DEAP avionic flight safety repo | `https://github.com/gintatkinson/DEAP-avionic-flight-safety` |
| DEAP uas infrastructure safety repo | `https://github.com/gintatkinson/DEAP-uas-infrastructure-safety` |
| debug-protocol SKILL.md | `/Users/perkunas/jail/digital-pipeline-repo/.agents/skills/debug-protocol/SKILL.md` |
| adversarial-code-auditor SKILL.md | `/Users/perkunas/jail/digital-pipeline-repo/.agents/skills/adversarial-code-auditor/SKILL.md` |
| feature-driven-implementation SKILL.md | `/Users/perkunas/jail/digital-pipeline-repo/.agents/skills/feature-driven-implementation/SKILL.md` |
