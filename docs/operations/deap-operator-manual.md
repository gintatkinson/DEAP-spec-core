# DEAP Operator Manual: End-to-End Operational Guide

> **Digital Engineering Agentic Pipeline (DEAP)**  
> Operational manual for domain specification ingestion, model compilation, parity auditing, downstream baseline verification, and GitHub backlog synchronization.

---

## 1. Overview & Operational Scope

The **Digital Engineering Agentic Pipeline (DEAP)** is an automated, multi-agent engineering toolchain designed to transform domain specifications and structural schemas into executable software implementations while maintaining zero-drift governance.

### Role of the DEAP Operator
As a DEAP Operator, your primary responsibility is to orchestrate, execute, and validate the pipeline stages that bridge abstract domain modeling and target platform code generation. This manual provides step-by-step instructions, copy-pasteable CLI commands, environment setup rules, and diagnostic matrices for operating the DEAP toolchain.

> [!NOTE]
> All DEAP operations are fully offline-capable except for the final GitHub backlog synchronization phase. Validation gates run deterministically against local repository files.

---

## 2. DEAP Pipeline Architecture & Three-Tier Governance

DEAP isolates domain semantics from technical execution using a **Three-Tier Architecture Governance Model**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Functional Layer (Abstract Specifications)                        │
│ - .pipeline/constitution.md                                              │
│ - Agile Backlog: Epics, Features, User Stories, Use Cases                │
│ - Platform-Independent: Zero framework or vendor dependencies            │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Tier 2: Dynamic Context & Runtime Parameters                             │
│ - .pipeline/logical-ui/codebase_rules.json                               │
│ - .pipeline/logical-ui/logical-layout.json                              │
│ - UI Shell Bindings, Design Tokens, & Domain Ontologies                  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Tier 3: Platform Implementation Profiles (Technical Execution)           │
│ - .pipeline/profiles/flutter.md  (Dart / Flutter Desktop & Mobile)     │
│ - .pipeline/profiles/react.md    (TypeScript / React Web Shell)        │
│ - Target-Specific Build, Test, Security, & Linting Mandates              │
└──────────────────────────────────────────────────────────────────────────┘
```

### Governance Principles
1. **Single Source of Truth**: Abstract specifications residing in Tier 1 define *what* the system does without referencing target languages or UI frameworks.
2. **Dynamic Adaptation**: UI layouts and data models adaptation occurs via Tier 2 parameters without requiring source code modifications.
3. **Decoupled Execution**: Tier 3 profiles enforce strict platform-specific execution standards (`npm run build`, `flutter analyze && flutter test`) without polluting Tier 1 specifications.

---

## 3. Environment Setup & Prerequisites

### 3.1 Required Tooling & Runtime Versions

| Tool | Minimum Required Version | Recommended / Mandatory Path |
|---|---|---|
| **Python** | `>= 3.12.0` | `/opt/homebrew/opt/python@3.12/bin/python3.12` or `.venv` |
| **Node.js / npm** | Node `>= 18.0`, npm `>= 9.0` | System PATH (for React platform builds) |
| **Flutter SDK** | `>= 3.12.0` (stable channel) | System PATH (for Flutter platform builds) |
| **Git** | `>= 2.30.0` | System PATH |
| **GitHub CLI (`gh`)** | `>= 2.20.0` | Authenticated with `repo` scope |

> [!IMPORTANT]
> **Python 3.12 Floor Mandate**: The default macOS system `python3` is often 3.9.x, which is unsupported. You MUST explicitly invoke `python3.12` or activate a Python 3.12+ virtual environment (`source .venv/bin/activate`).

### 3.2 Environment Setup Commands

Execute the following commands from the repository root to initialize your operator environment:

```bash
# 1. Verify Python 3.12+ interpreter
python3.12 --version

# 2. Create and activate a Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Prevent mtime stale bytecode caching issues during validation runs
export PYTHONDONTWRITEBYTECODE=1

# 4. Install pipeline runtime dependencies
pip install -r requirements.txt

# 5. Install parity_auditor in local editable mode
pip install -e skills/spec-orchestrator/parity_auditor

# 6. Verify parity_auditor CLI installation
parity-auditor --help
```

> [!TIP]
> Alternatively, if `uv` is installed, you can perform a fast virtual environment setup:
> ```bash
> uv venv --python 3.12 .venv
> source .venv/bin/activate
> uv pip install -r requirements.txt
> uv pip install -e skills/spec-orchestrator/parity_auditor
> ```

---

## 4. Step-by-Step Operator Workflows

### Workflow 1: Domain Specification Ingestion (`.pipeline/domain_specs/`)

Domain specifications define functional features (`feat-*.md`) and use cases (`uc-*.md`) staged for downstream execution.

> [!IMPORTANT]
> **Mandatory Direct-Path Verification**: Because glob and ripgrep queries bypass hidden folders, operators and scripts MUST perform explicit path reads (e.g. `ls .pipeline/domain_specs/`) to confirm file presence before initiating ingestion.

#### Step-by-Step Execution:

```bash
# 1. Verify presence of domain specifications directly in hidden directory
ls -la .pipeline/domain_specs/

# 2. Inspect a specific domain specification file
cat .pipeline/domain_specs/feat-45-yang-decomposition.md

# 3. Ingest domain specification issue into tracker pipeline
python3 scripts/ingest_issue.py --source .pipeline/domain_specs/feat-45-yang-decomposition.md
```

---

### Workflow 2: SysML v2 Model Compilation (`compile_sysml.py`)

The SysML v2 compiler parses textual Systems Modeling Language (`.sysml`) files, generates an Abstract Syntax Tree (AST), and extracts packages, part definitions, port definitions, requirements, and state definitions.

#### Step-by-Step Execution:

```bash
# 1. Create or inspect SysML v2 model file
cat << 'EOF' > schema/network_gateway.sysml
package NetworkGateway {
    part def RouterContainer;
    attribute def BandwidthGbps;
    port def OpticalPort;
    requirement def HighAvailability;
    state def ActiveOperational;
}
EOF

# 2. Compile SysML v2 textual model to JSON AST
python3 scripts/compile_sysml.py schema/network_gateway.sysml > schema/network_gateway.ast.json

# 3. Inspect generated SysML v2 AST output
cat schema/network_gateway.ast.json
```

#### Expected AST JSON Structure:
```json
{
  "packages": ["NetworkGateway"],
  "part_defs": ["RouterContainer"],
  "attribute_defs": ["BandwidthGbps"],
  "port_defs": ["OpticalPort"],
  "requirement_defs": ["HighAvailability"],
  "state_defs": ["ActiveOperational"]
}
```

---

### Workflow 3: Executing YANG Decompositions (`compile_yang.py`)

The YANG compiler parses YANG (RFC 7950) schema models using `pyang` and transforms structural containers, lists, and leaves into the platform-agnostic `.pipeline/logical-ui/logical-layout.json`.

#### Step-by-Step Execution:

```bash
# 1. Validate pyang installation
pyang --version

# 2. Execute YANG-to-LUI compiler
python3 scripts/compile_yang.py \
  --input schema/ietf-network-inventory.yang \
  --output .pipeline/logical-ui/logical-layout.json

# 3. Validate generated layout structure
python3 scripts/validate_layout.py .pipeline/logical-ui/logical-layout.json
```

> [!NOTE]
> `compile_yang.py` maps YANG XPaths directly to UI component keys (e.g. `interfaces/interface/state/mtu`), enabling zero-translation gNMI data binding in generic UI viewports (`PropertyGrid`, `TableView`).

---

### Workflow 4: Running Parity Audits (`parity_auditor`)

The `parity_auditor` suite executes 19 offline validators to ensure zero-drift alignment across schemas, specifications, Mermaid diagrams, layout bindings, and codebase ASTs.

#### Step-by-Step Execution:

```bash
# Option A: Run specification-only validation (Fast pre-commit check)
python3 skills/spec-orchestrator/scripts/verify_model_coverage.py --spec-only --allow-missing-specs

# Option B: Run full repository parity audit via CLI
parity-auditor

# Option C: Run parity audit scoped to a single specification file
parity-auditor --only docs/features/feat-01-fiber-cable-and-strand-inventory.md

# Option D: Run parity audit in strict mode (fail if specs are missing)
parity-auditor --no-allow-missing-specs

# Option E: Run SysML v2 model coverage parity validation
parity-auditor --sysml
```

#### Validation Suite Coverage:
- **UML & Mermaid Syntax**: Validates no curly braces in class bodies, no unquoted colons, and valid diagram headers.
- **Schema Container Traceability**: Verifies every Feature declares exactly 1 valid schema container XPath.
- **Logical UI Bindings**: Verifies components match container types and spatial features bind `TopologyMap`.
- **Markdown & Link Integrity**: Validates all relative links and source reference URLs.
- **AST Codebase Compliance**: Scans target codebases for forbidden imports, hardcoded hex colors, and un-clamped states.

---

### Workflow 5: Running Baseline Verification (`verify_downstream_baseline.py`)

`verify_downstream_baseline.py` enforces target platform conformance by validating mandated domain classes/types, running linting and unit tests, and building release artifacts.

#### Step-by-Step Execution:

```bash
# 1. Verify Flutter Desktop/Mobile Application Baseline
python3 scripts/verify_downstream_baseline.py --platform flutter app_flutter/

# 2. Verify React Web Application Baseline
python3 scripts/verify_downstream_baseline.py --platform react web_react/

# 3. Fast Verification (Skip domain type checks during early iteration)
python3 scripts/verify_downstream_baseline.py --platform flutter --no-domain app_flutter/
```

#### Verification Pipeline Steps Executed:
1. **Baseline File Assertion**: Checks for mandatory config/entry files (`pubspec.yaml`, `tsconfig.json`, `main.dart`, `main.tsx`).
2. **Type Compatibility Check**: Validates that `types.dart` or `types.ts` implements mandated domain classes.
3. **Dependencies & Static Analysis**: Runs `flutter pub get && flutter analyze` or `npm install`.
4. **Unit & Integration Testing**: Runs `flutter test` or `npm run test`.
5. **Release Compilation**: Executes `flutter build macos --release` or `npm run build` and packages output into `app_flutter_release.zip`.

---

### Workflow 6: Performing Backlog Reconciliation (`reconcile_backlog.py`)

`reconcile_backlog.py` synchronizes local Markdown specifications (`docs/epics/`, `docs/features/`, `docs/user-stories/`, `docs/use-cases/`) with GitHub Issues.

> [!WARNING]
> **Zero-Tolerance Gate**: `reconcile_backlog.py` will abort immediately with exit code 1 if any specification files were skipped or rejected by `parity_auditor`. All linter errors MUST be fixed before running reconciliation.

#### Step-by-Step Execution:

```bash
# 1. Ensure GitHub CLI authentication
gh auth status

# 2. Synchronize labels across issue tracker
python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py

# 3. Run backlog reconciliation
python3 skills/spec-orchestrator/scripts/reconcile_backlog.py

# 4. Verify remote synchronization status (Git diff must be clean)
git status
git diff origin/main
```

#### Key Reconciliation Actions:
- Resolves placeholder `#IssueID` links in Markdown files with live GitHub Issue numbers.
- Updates checklist checkboxes (`- [x] #123`) when child features are completed.
- Syncs Markdown body text directly to GitHub Issue bodies via `gh issue edit`.
- Marks completed issues as `Fixed / Resolved` (**Never** sets issues to `Closed`, preserving PO validation gates per `constitution.md`).

---

## 5. End-to-End Operator Execution Pipeline (Sequential Run Sheet)

When processing a new domain update end-to-end, execute the following sequential pipeline:

```bash
#!/usr/bin/env bash
set -eo pipefail

echo "=== DEAP End-to-End Operational Pipeline ==="

# Step 1: Environment Sanitation
export PYTHONDONTWRITEBYTECODE=1
source .venv/bin/activate

# Step 2: Ingest Domain Specs & Verify Direct Paths
echo "[1/6] Ingesting Domain Specifications..."
ls -la .pipeline/domain_specs/

# Step 3: Compile Schemas & Layouts
echo "[2/6] Compiling SysML v2 and YANG Models..."
python3 scripts/compile_sysml.py schema/*.sysml || true
python3 scripts/compile_yang.py --input schema/*.yang --output .pipeline/logical-ui/logical-layout.json

# Step 4: Run Model Parity Audit
echo "[3/6] Running Parity Auditor Gate..."
python3 skills/spec-orchestrator/scripts/verify_model_coverage.py --spec-only --allow-missing-specs
parity-auditor

# Step 5: Verify Target Platform Baselines
echo "[4/6] Verifying Downstream Baselines..."
python3 scripts/verify_downstream_baseline.py --platform flutter app_flutter/
python3 scripts/verify_downstream_baseline.py --platform react web_react/

# Step 6: Synchronize Backlog Tracker & Remote Git
echo "[5/6] Reconciling GitHub Backlog..."
python3 skills/spec-orchestrator/scripts/reconcile_backlog.py

echo "[6/6] Verifying Remote Synchronization..."
git diff origin/main --exit-code

echo "=== DEAP Operational Pipeline Completed Successfully! ==="
```

---

## 6. Error Diagnostics & Troubleshooting Matrix

| Error Code / Symptom | Root Cause | Diagnostic Command | Remediation Step |
|---|---|---|---|
| **`ImportError: pyang`** | `pyang` not installed in active Python environment | `python3 -c "import pyang"` | Run `pip install pyang` or `pip install -r requirements.txt`. |
| **`Python Version Mismatch`** | Running system Python 3.9 instead of required Python 3.12 | `python3 --version` | Use `python3.12` or activate `.venv` built with Python 3.12+. |
| **`Mermaid Syntax Error (Colons)`** | Secondary colons in class member lines or note strings | `parity-auditor --only <file.md>` | Remove colons or run `python3 scripts/fix_mermaid_colons.py <file.md>`. |
| **`Mermaid Syntax Error (Curly Braces)`** | Curly braces `{}` used inside Mermaid class bodies | `parity-auditor` | Replace `{}` with parentheses `()` or square brackets `[]`. |
| **`Container Traceability Failure`** | Feature has missing or multiple entries in `schema_containers` | `grep -A 5 "schema_containers" <file.md>` | Ensure exactly 1 fully-qualified container XPath is listed in YAML frontmatter. |
| **`Logical UI Unbound Component`** | Feature `Target LUI Component` not in `logical-layout.json` | `python3 scripts/validate_layout.py .pipeline/logical-ui/logical-layout.json` | Update feature binding or add declared component to `logical-layout.json`. |
| **`Blocked Specs Reconciliation Exit`** | `reconcile_backlog.py` skipped files rejected by linter | `python3 skills/spec-orchestrator/scripts/reconcile_backlog.py` | Fix all linter findings reported by `parity-auditor` before running reconciler. |
| **`Baseline Build Timeout`** | Flutter analyze or npm build exceeded 600s timeout | `flutter clean && flutter pub get` | Clean build workspace and retry baseline verification script. |
| **`GitHub CLI Auth Error`** | `gh` token missing or expired in environment | `gh auth status` | Run `gh auth login` or export valid `GH_TOKEN`. |
| **`Remote Divergence Error`** | Uncommitted files or untracked pipeline infra after run | `git status` | Stage infra changes (`git add .pipeline/ skills/`) and push to `origin/main`. |

---

## 7. Upstream Defect Reporting & Escalation Protocol

If an operation fails due to a bug or limitation in shared pipeline scripts (`parity_auditor`, `reconcile_backlog.py`, `compile_yang.py`, `verify_downstream_baseline.py`), operators MUST file an upstream defect report.

> [!CAUTION]
> Operators are strictly forbidden from applying local silent patches to shared pipeline scripts without reporting the defect upstream.

### Upstream Reporting Command:

```bash
gh issue create \
  --repo gintatkinson/digital-pipeline-repo \
  --title "Tooling Defect: [Brief summary of failure]" \
  --body "### Environment
- OS: $(uname -s) $(uname -m)
- Python: $(python3 --version)
- Component: [e.g. parity_auditor / reconcile_backlog.py]

### Reproduction Steps
1. Run command: \`<command>\`
2. Failure output:
\`\`\`
[Paste error log snippet here]
\`\`\`

### Expected Behavior
[Description of expected outcome]"
```

---
