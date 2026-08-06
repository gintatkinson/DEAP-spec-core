# Implementation Plan - Sprint Verification & Compliance Remediation

This plan details all changes to resolve the Git tracking onboarding issues, downstream pre-push hook validation errors, and the full suite of UML linter bugs (Issues 58 to 63). Each task must undergo auditing and debugging via specialized subagents adopts the designated skills.

---

## 1. Setup, Git Tracking, & Hooks Integration

### Issue A: Downstream Git Tracking (Dot-files Ignored)
*   **Audit Skill**: `spec-implementation-auditor/SKILL.md` (Check how `.pipeline/` and `.agents/` are tracked).
*   **Debug Skill**: `debug-protocol/SKILL.md` (Verify `.gitignore` patterns and `git add` behavior).
*   **Executing Agent**: `Git Tracking Setup Auditor` (`self`)
*   **Proposed Change**:
    *   File: [setup_git_hooks.py](file:///Users/perkunas/jail/digital-pipeline-repo/scripts/setup_git_hooks.py)
    *   Action: Update the script to automatically append whitelist rules for `/skills/`, `/rules/`, `/.pipeline/`, `/.agents/`, and `/scripts/` to the root `.gitignore` file, and programmatically run `git add` to stage those folders during setup.
*   **Verification**:
    *   Run `python3 scripts/setup_git_hooks.py` in a clean environment and assert `.gitignore` contains the whitelists and files are staged.

### Issue B: Pre-Push Hook Removal
*   **Audit Skill**: `spec-implementation-auditor/SKILL.md` (Verify hook performance overhead).
*   **Debug Skill**: `debug-protocol/SKILL.md` (Revert hook configuration).
*   **Executing Agent**: `Git Hook Cleanup Worker` (`self`)
*   **Proposed Change**:
    *   File: [setup_git_hooks.py](file:///Users/perkunas/jail/digital-pipeline-repo/scripts/setup_git_hooks.py)
    *   Action: Completely remove the `pre-push` hook content generation and delete `.git/hooks/pre-push` so pushes do not run expensive tests.
*   **Verification**:
    *   Assert `.git/hooks/pre-push` is deleted and pushes complete without running the validation script.

### Issue C: Config-Driven Downstream Verification (Bypass Pre-Push Crash)
*   **Audit Skill**: `spec-implementation-auditor/SKILL.md` (Verify compatibility rules).
*   **Debug Skill**: `debug-protocol/SKILL.md` (Implement config checking).
*   **Executing Agent**: `Downstream Verification Auditor` (`self`)
*   **Proposed Change**:
    *   File: [verify_downstream_baseline.py](file:///Users/perkunas/jail/digital-pipeline-repo/scripts/verify_downstream_baseline.py)
    *   Action: Modify the script to read `codebase_rules.json` or `baseline_manifest.json` in the destination path. If the configuration declares `"no_domain": true`, programmatically enable `--no-domain` mode, removing the expectation for `repository_resolver.dart` and `validation.dart` and avoiding false-positive crashes on uninitialized projects.
*   **Verification**:
    *   Run `python3 scripts/verify_downstream_baseline.py app_flutter` and assert success when `"no_domain": true` is configured.

### Issue D: Automated Workspace Cleanup
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `Workspace Cleanup Worker` (`self`)
*   **Proposed Change**:
    *   File: [verify_downstream_baseline.py](file:///Users/perkunas/jail/digital-pipeline-repo/scripts/verify_downstream_baseline.py)
    *   Action: Add an automatic cleanup handler that executes before the script exits, recursively removing all generated `.dart_tool/`, `.flutter-plugins`, `.flutter-plugins-dependencies`, and SQLite transaction logs (`*.db-shm`, `*.db-wal`) to keep the project pristine.
*   **Verification**:
    *   Run verification and assert that `git status` remains completely clean after execution.

### Issue E: Auto-Tag Restoration Point
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `Restoration Point Tagging Agent` (`self`)
*   **Proposed Change**:
    *   File: [verify_downstream_baseline.py](file:///Users/perkunas/jail/digital-pipeline-repo/scripts/verify_downstream_baseline.py)
    *   Action: Upon successful verification, automatically tag the current commit as `restoration-point` locally (`git tag -f restoration-point`) to serve as a baseline of certainty.
*   **Verification**:
    *   Assert `git describe --tags` outputs `restoration-point` pointing to the latest verified commit.

---

## 2. Parity Auditor & Linter Refactor (Issues 58 to 63)

### Issue 58: Programmatic validate() ignores Epic diagrams [EPIC-LNT-01]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `UML Epic Validator Auditor` (`self`)
*   **Proposed Change**:
    *   File: [uml.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/validators/uml.py)
    *   Action: Pass `epics_dir` to `build_global_classes` inside `uml.py:L29` to ensure epic diagrams are compiled during programmatic validation calls.
*   **Verification**:
    *   Run `PYTHONPATH=skills/spec-orchestrator/parity_auditor/src python3 -m pytest tests/test_linter_reliability.py` and verify tests pass.

### Issue 59: Epic class compilation bypassed when features list empty [EPIC-LNT-02]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `CLI Epic Compiler Auditor` (`self`)
*   **Proposed Change**:
    *   File: [cli.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/cli.py)
    *   Action: Modify the skipping condition on line 299. Set `skip_coverage_checks = True` only if *both* feature files and epic files are missing, ensuring epic coverage is validated even if features are empty.
*   **Verification**:
    *   Run `PYTHONPATH=skills/spec-orchestrator/parity_auditor/src python3 -m parity_auditor.cli` with empty feature folder and check that Epic classes are still parsed and checked.

### Issue 60: Multiplicity parsed strictly at end of attribute lines [LNT-UML-01]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `Mermaid Parser Auditor` (`self`)
*   **Proposed Change**:
    *   File: [mermaid.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/parsers/mermaid.py)
    *   Action: Refactor the regex in `parse_attribute_signature()` to search for brackets `[...]` anywhere in the signature string (not anchored to the end of the line). Remove the multiplicity substring from the signature type name.
*   **Verification**:
    *   Verify that `+String[0..*] name` parses correctly with `multiplicity="0..*"` and `type="String"`.

### Issue 61: Return validator incorrectly requires multiplicity [LNT-UML-02]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `Method Signature Auditor` (`self`)
*   **Proposed Change**:
    *   File: [uml.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/validators/uml.py)
    *   Action: Modify `_validate_class_diagram()` to default return types without explicit brackets `[...]` to a multiplicity of `[1]` (or `[0..1]`), failing only if brackets are present but violate syntax bounds.
*   **Verification**:
    *   Ensure methods like `+save()` or `+Node fetch()` do not raise multiplicity validation errors.

### Issue 62: Codebase coverage checked via naive substring matching [LNT-UML-03]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `AST Coverage Auditor` (`self`)
*   **Proposed Change**:
    *   File: [cli.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/cli.py)
    *   Action: Define `common_words` (e.g. `id`, `name`) and implement `is_present_in_codebase()`. For common words, use strict regex boundaries matching actual code definitions (like `.id`, `this.id`, `id:`, and variable declarations) to ignore matches inside comments and strings.
*   **Verification**:
    *   Ensure properties named `id` or `name` inside comments do not trigger false positive coverage flags.

### Issue 63: Link and diagram checks run on raw file content [LNT-UML-04]
*   **Audit/Debug Skills**: `spec-implementation-auditor/SKILL.md` & `debug-protocol/SKILL.md`
*   **Executing Agent**: `Prose Validator Auditor` (`self`)
*   **Proposed Change**:
    *   File: [uml.py](file:///Users/perkunas/jail/digital-pipeline-repo/skills/spec-orchestrator/parity_auditor/src/parity_auditor/validators/uml.py)
    *   Action: Extract only the ````mermaid ... ```` blocks from the specification file before running Mermaid-specific checks (like the dotted-link syntax check), allowing standard markdown prose and links to bypass checks.
*   **Verification**:
    *   Verify that specification files containing standard markdown description paragraphs and links pass validation.
