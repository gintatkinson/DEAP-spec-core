---
title: "DEAP Profile Provisioning & Extension Guide"
project: "Digital Engineering Agentic Pipeline (DEAP)"
tier: operations
version: "1.0.0"
created: "2026-08-05"
last_updated: "2026-08-05"
---

# DEAP Profile Provisioning & Extension Guide

> This document provides complete operational guidance for managing, creating, and extending target platform implementation profiles within the Digital Engineering Agentic Pipeline (DEAP). It details profile architecture, template syntax, automated provisioning, and step-by-step instructions for adding custom target platform profiles.

---

## 1. Overview

The Digital Engineering Agentic Pipeline (DEAP) isolates abstract domain specifications from concrete platform execution rules using a **Three-Tier Architecture Governance Model**:

1. **Tier 1: Functional Layer (Abstract Specification)** — Platform-independent specifications documented in `.pipeline/constitution.md`, Epics, Features, User Stories, and Use Cases. Focuses on *what* the system does without mentioning specific programming languages, visual tokens, or frame/build tools.
2. **Tier 2: Runtime Configuration Parameters (Dynamic Context)** — Standard-specific and environment-specific parameters (e.g. design tokens, color schemes, API endpoint configurations) loaded dynamically at runtime via configuration files (`config.json`).
3. **Tier 3: Platform Implementation Profiles (Technical Execution)** — Platform-specific markdown profiles residing under `.pipeline/profiles/` (e.g., `react.md`, `flutter.md`) and configuration files (`.pipeline/profile_config.json`). Govern platform technology stacks, coding conventions, testing mandates, build commands, and security guidelines.

> [!NOTE]
> By decoupling abstract functional specifications (Tier 1) from platform implementation profiles (Tier 3), DEAP enables a single specification backlog to target multiple frontends (e.g., React, Flutter), backends (e.g., Node.js API, Go microservice), or specialized hardware targets (e.g., VHDL/Verilog) without modifying functional requirements.

---

## 2. Profile Architecture (`.pipeline/profiles/`)

Profiles are stored in the `.pipeline/profiles/` directory alongside active runtime pipeline configurations.

```
.pipeline/
├── constitution.md           # Tier 1: Functional Layer Governance
├── profile_config.json       # Tier 3: Active Profile Configuration State
└── profiles/                 # Tier 3: Target Platform Profiles
    ├── flutter.md            # Flutter/Dart Mobile & Desktop Profile
    ├── react.md              # React/TypeScript Web Profile
    ├── backend-api.md        # Backend API Service Profile (Custom)
    └── vhdl-hardware.md      # Hardware Description Profile (Custom)
```

### 2.1 Profile Markdown File Structure

Every platform implementation profile stored under `.pipeline/profiles/` is a structured Markdown document with mandatory YAML frontmatter and standard sections:

```markdown
---
title: "Implementation Profile — <Platform Name>"
project: "Digital Systems Engineering Pipeline"
tier: implementation
platform: "<platform-id>"
version: "1.0.0"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
---

# Implementation Profile: <Platform Name>

## 1. Platform & Stack
- Language & Compiler version rules.
- Framework & architectural decoupling patterns.
- Repository & persistence adapter requirements.

## 2. Coding Standards & UI Patterns
- Architecture isolation (e.g., Clean Architecture, Bounded Contexts).
- Visual tokens & dynamic theme rendering rules.
- Threading, off-main-thread execution, & memory lifecycle management.

## 3. Testing Mandates
- TDD RED-GREEN-REFACTOR cycle rules.
- Component computed-style assertions & visual state tests.
- E2E & integration test harness guidelines.

## 4. Build & Operations
- Standard linting, dev server, emulator, and production build CLI commands.

## 5. Security & Credentials
- Secret key handling, runtime config resolution, and CSP/CORS governance.
```

### 2.2 Profile Active Configuration (`.pipeline/profile_config.json`)

The active target profile is recorded in `.pipeline/profile_config.json`. This configuration file determines which platform rules are active during automated feature generation and verification:

```json
{
  "active_profile": "react-web"
}
```

> [!IMPORTANT]
> Autonomous implementation subagents inspect `.pipeline/profile_config.json` at task initialization to determine which profile document in `.pipeline/profiles/` to read and enforce during coding, testing, and building.

---

## 3. Template Syntax & Variable Substitution

DEAP platform profiles utilize standard template substitution tokens to allow dynamic code generation scripts and subagents to project abstract domain specifications into platform-specific code structures.

### 3.1 Standard Template Substitution Variables

| Template Variable | Description | Example (React) | Example (Flutter) | Example (Backend API) |
| :--- | :--- | :--- | :--- | :--- |
| `{{PLATFORM_NAME}}` | Target platform identifier | `react` | `flutter` | `backend-api` |
| `{{FRAMEWORK_VERSION}}` | Primary framework version | `React 18.x / TS 5.x` | `Flutter 3.x / Dart 3.x` | `Node.js 20.x / TS 5.x` |
| `{{SRC_DIR}}` | Target source directory | `web_react/src` | `app_flutter/lib` | `backend_api/src` |
| `{{BUILD_OUTPUT_DIR}}` | Target build binary path | `web_react/dist` | `app_flutter/build/macos` | `backend_api/dist` |
| `{{LINT_CMD}}` | Code verification / linter CLI | `npm run lint` | `flutter analyze` | `npm run lint` |
| `{{DEV_SERVER_CMD}}` | Local dev server command | `npm run dev` | `flutter run -d macos` | `npm run dev` |
| `{{TEST_RUNNER_CMD}}` | Unit test execution command | `npm run test` | `flutter test` | `npm run test` |
| `{{PERSISTENCE_ADAPTER}}` | Target concrete database adapter | `FirestoreRepositoryAdapter` | `HiveRepositoryAdapter` | `PostgresRepositoryAdapter` |

### 3.2 Dynamic Template Processing Protocol

During subagent dispatches and code generation loops:
1. Subagents read the active profile identifier from `.pipeline/profile_config.json`.
2. The subagent opens `.pipeline/profiles/<platform>.md` using `view_file`.
3. Template placeholders inside boilerplate assets or generated code files are substituted with concrete values matching the project's profile settings before writing files to disk.

---

## 4. Automated Provisioning with `scripts/install_pipeline.py`

Automated profile activation and environment switching is driven by the Python CLI tool `scripts/install_pipeline.py`.

### 4.1 CLI Usage & Options

`scripts/install_pipeline.py` sets up `.pipeline/profile_config.json` and prepares workspace configuration settings.

```bash
# Display help and available choices
python3 scripts/install_pipeline.py --help

# Provision the React web implementation profile
python3 scripts/install_pipeline.py --profile react-web

# Provision the Flutter mobile implementation profile
python3 scripts/install_pipeline.py --profile flutter-mobile

# Provision the Backend API implementation profile
python3 scripts/install_pipeline.py --profile backend-api

# Provision the VHDL Hardware implementation profile
python3 scripts/install_pipeline.py --profile vhdl-hardware
```

### 4.2 How `install_pipeline.py` Works

The script manages configuration state deterministically:

```python
import argparse
import json
import os
import sys

PROFILES = ["react-web", "flutter-mobile", "backend-api", "vhdl-hardware"]

def install(profile_name):
    config_path = os.path.join(".pipeline", "profile_config.json")
    os.makedirs(".pipeline", exist_ok=True)
    config = {"active_profile": profile_name}
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Successfully configured pipeline for profile: {profile_name}")
```

### 4.3 `.gitignore` Auto-Whitelisting Mandate

To ensure that pipeline configurations and profile definitions are preserved in version control while build artifacts are ignored, DEAP enforces strict `.gitignore` rules:

```gitignore
# Pipeline Configuration & Profiles MUST be tracked
!.pipeline/
!.pipeline/constitution.md
!.pipeline/profile_config.json
!.pipeline/profiles/
!.pipeline/profiles/*.md

# Target Platform Build Artifacts MUST be ignored
web_react/dist/
web_react/node_modules/
app_flutter/build/
app_flutter/.dart_tool/
backend_api/dist/
backend_api/node_modules/
```

> [!TIP]
> Always verify that your profile `.md` files under `.pipeline/profiles/` are whitelisted in `.gitignore` using `git status` after provisioning a new profile.

---

## 5. Step-by-Step Tutorial: Adding a New Target Platform Profile

This tutorial walks through creating a new custom profile named `backend-api` for a TypeScript Node.js microservice architecture.

### Step 1: Create the Profile Markdown Document

Create `.pipeline/profiles/backend-api.md` with explicit platform guidelines:

```markdown
---
title: "Implementation Profile — Backend API Service"
project: "Digital Systems Engineering Pipeline"
tier: implementation
platform: "backend-api"
version: "1.0.0"
created: "2026-08-05"
---

# Implementation Profile: Backend API Service

## 1. Platform & Stack
- **Framework & Version:** Node.js 20 LTS / Express or Fastify.
- **Language & Version:** TypeScript 5.x (strict null checks enabled).
- **Architecture:** Clean Architecture with Bounded Contexts.
- **Persistence Pattern:** Abstract Repository pattern; concrete driver (PostgreSQL/Redis) injected via DI container.

## 2. Coding Standards
- **Naming Conventions:** camelCase for variables/methods, PascalCase for classes/types, kebab-case for filenames.
- **Async Operations:** All asynchronous APIs must return `Promise<T>` and use standard `async/await` syntax.
- **Error Handling:** Centralized exception handling middleware with typed domain exceptions.

## 3. Testing Mandates
- **Unit Testing:** Jest or Vitest with 100% domain logic coverage.
- **Integration Testing:** Supertest against live local PostgreSQL container.

## 4. Build & Operations
- **Lint Command:** `npm run lint`
- **Dev Server:** `npm run dev`
- **Build Command:** `npm run build` (compiles to `dist/`)

## 5. Security & Credentials
- **Secrets Management:** Credentials loaded via environment variables or secret vaults. Never committed to git.
```

### Step 2: Register the Profile Name in `scripts/install_pipeline.py`

Update the `PROFILES` array in `scripts/install_pipeline.py`:

```python
PROFILES = [
    "react-web",
    "flutter-mobile",
    "backend-api",      # Added new backend profile
    "vhdl-hardware"     # Added new hardware profile
]
```

### Step 3: Define Asset Templates & Variable Substitutions

Define default paths and template mappings for `backend-api`:

- `{{SRC_DIR}}` -> `backend_api/src`
- `{{BUILD_CMD}}` -> `npm run build`
- `{{TEST_RUNNER_CMD}}` -> `npm run test`
- `{{PERSISTENCE_ADAPTER}}` -> `PostgresRepositoryAdapter`

### Step 4: Add Target Folder Rules to `.gitignore`

Ensure target repository paths are protected:

```gitignore
# Whitelist pipeline profile
!.pipeline/profiles/backend-api.md

# Ignore backend build artifacts
backend_api/node_modules/
backend_api/dist/
backend_api/.env
```

### Step 5: Test Provisioning Execution

Execute the provisioning script and verify configuration state:

```bash
# Provision the new profile
python3 scripts/install_pipeline.py --profile backend-api

# Output verification
# Successfully configured pipeline for profile: backend-api

# Inspect generated profile configuration
cat .pipeline/profile_config.json
```

---

## 6. Verification Tests & Audit Rules

Once a profile is provisioned, DEAP enforces strict downstream verification and baseline conformance testing before feature integration begins.

### 6.1 Baseline Downstream Verification

Run `scripts/verify_downstream_baseline.py` to ensure target platform files conform to profile standards:

```bash
python3 scripts/verify_downstream_baseline.py
```

This verification script asserts that:
- Required baseline directories and target platform source structures exist.
- Linter gates pass cleanly without compilation errors (`exit code 0`).
- No hardcoded in-memory stubs or forbidden UI mocks exist in production paths.

### 6.2 Profile Audit Execution

Execute `scripts/run_profile_audit.py` to run performance, memory growth, and frame rate budget checks:

```bash
python3 scripts/run_profile_audit.py
```

Audit thresholds evaluated:
- **Memory Delta Threshold:** Memory growth delta must not exceed 100 MB (`rss_threshold_kb = 100 * 1024`).
- **Frame Rate Jank Threshold:** Average frame build time must stay below 16.6 ms (targeting 60 FPS).
- **Leak Detection:** Zero memory leak flags during interactive widget/view passes.

> [!WARNING]
> If `run_profile_audit.py` or `verify_downstream_baseline.py` returns a non-zero exit code, the pipeline execution halts immediately. The developer or agent must remediate the regression before proceeding.

---

## 7. Summary & Best Practices Checklist

- [x] **Keep Specifications Abstract:** Never put platform-specific code, framework keywords, or fixed pixel values in Tier 1 documents (`.pipeline/constitution.md` or Epics/Features).
- [x] **Store Profiles in `.pipeline/profiles/`:** Keep platform implementation rules organized in separate markdown files per target platform.
- [x] **Use `install_pipeline.py` for Switch Logic:** Always switch active profile state via `python3 scripts/install_pipeline.py --profile <name>`.
- [x] **Whitelist `.pipeline/` in Git:** Ensure profile definitions are tracked in git while build artifacts (`dist/`, `build/`) are ignored.
- [x] **Enforce Verification Gates:** Validate baseline conformance with `verify_downstream_baseline.py` and run profile audits with `run_profile_audit.py` prior to feature deployment.
