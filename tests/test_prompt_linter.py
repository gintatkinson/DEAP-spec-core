#!/usr/bin/env python3
"""
Unit test suite for the Physical Subagent Prompt Payload Linter.
Validates:
- Rule 1 (Single-Task Enforcement): Multi-item task lists, multi-domain imperative verbs, >1 target spec item/file.
- Rule 2 (Skill Template Match): Exact Section 5 dispatch template matching for standardized skills like adversarial-code-auditor.
- Rule 3 (Zero Inline Issue Body): Forbidding inline --body / -b issue creation in favor of --body-file.
- Transcript JSONL parsing and prompt extraction.
- CLI entrypoint execution, positional arguments, piped stdin, and exit codes.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure scripts directory and repo root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lint_subagent_prompt import (
    lint_prompt_payload,
    extract_prompts_from_transcript,
    main,
)


# ==============================================================================
# 1. Passing Atomic Prompts
# ==============================================================================

class TestPassingAtomicPrompts:
    """Tests for compliant, atomic subagent prompt payloads."""

    def test_compliant_single_feature_implementation(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        Section 1.9 Zero-Mocking Live Persistence Mandate.
        3-Layer Definition of Done (DoD).
        RED-GREEN-REFACTOR.
        Build/Test Verification Commands: python3 -m pytest tests/test_fuselage.py (all pass).
        ---GOVERNANCE-END---

        TASK: Implement Fuselage Structural Frame for FEAT-001A.
        Target File: src/structures/fuselage.py
        Test File: tests/test_fuselage.py

        Implement the composite bulkhead load distribution calculation according to the FEAT-001A specification.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == [], f"Expected 0 violations, got: {violations}"

    def test_compliant_single_unit_test_task(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        Section 1.9 Zero-Mocking Live Persistence Mandate.
        3-Layer Definition of Done (DoD).
        RED-GREEN-REFACTOR.
        ---GOVERNANCE-END---

        TASK: Author unit tests for Pitot Sensor calibration in tests/test_pitot_sensor.py for FEAT-003B.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == [], f"Expected 0 violations, got: {violations}"

    def test_compliant_prompt_with_body_file(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        ---GOVERNANCE-END---

        TASK: File the audit finding using gh issue create --repo gintatkinson/uas-003 --title "[AUDIT] [bridge.cpp]: UAF" --label "bug" --body-file /tmp/gh_body_123.md.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == [], f"Expected 0 violations, got: {violations}"

    def test_single_spec_id_repeated_multiple_times_passes(self):
        prompt = """
        TASK: FEAT-001A implementation.
        Verify FEAT-001A against FEAT-001A acceptance criteria.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == []

    def test_code_blocks_with_numbers_do_not_trigger_false_positives(self):
        prompt = """
        TASK: Implement parsing logic for FEAT-002A.
        Here is the example format to parse:
        ```python
        # Example steps in docstring:
        # 1. First step
        # 2. Second step
        # 3. Third step
        def parse():
            pass
        ```
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == []


# ==============================================================================
# 2. Rule 1: Single-Task Enforcement
# ==============================================================================

class TestRule1SingleTaskEnforcement:
    """Tests enforcing atomic single-task scope (rejecting bundled multi-task prompts)."""

    def test_rejects_empty_or_whitespace_prompt(self):
        assert len(lint_prompt_payload("")) >= 1
        assert len(lint_prompt_payload("   \n\t  ")) >= 1
        assert len(lint_prompt_payload(None)) >= 1  # type: ignore

    def test_rejects_multi_item_numbered_task_list(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        ---GOVERNANCE-END---

        TASK: Implement FEAT-001A.
        Work Items:
        1. Create the database model in src/models/fuselage.py
        2. Create the API endpoints in src/api/fuselage_routes.py
        3. Create the UI widgets in src/ui/fuselage_view.py
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("Rule 1" in v or "Single-Task" in v or "numbered task list" in v.lower() for v in violations)

    def test_rejects_multiple_numbered_lines_in_task(self):
        prompt = """
        TASK: Multiple tasks to complete:
        1. Fix bug in motor controller
        2. Refactor battery management unit
        3. Write new tests for ESC
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("numbered task list" in v.lower() or "single-task" in v.lower() for v in violations)

    def test_rejects_disparate_domain_imperative_verbs_author_and_code(self):
        prompt = """
        TASK: Author the feature specification for FEAT-004A and implement the backend code in src/fhss.py.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("disparate domain" in v.lower() or "verbs" in v.lower() or "single-task" in v.lower() for v in violations)

    def test_rejects_disparate_domain_imperative_verbs_code_and_file(self):
        prompt = """
        TASK: Implement the battery sensor in src/pmu.py and file a bug issue on GitHub tracker.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("disparate domain" in v.lower() or "verbs" in v.lower() or "single-task" in v.lower() for v in violations)

    def test_rejects_multiple_target_spec_items(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        ---GOVERNANCE-END---

        TASK: Implement telemetry synchronization handling both FEAT-004A (FHSS Datalink) and FEAT-004C (SwarmC2 UI).
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("specification item" in v.lower() or "target spec" in v.lower() or "multiple" in v.lower() for v in violations)

    def test_rejects_multiple_target_spec_files(self):
        prompt = """
        Adopt the feature-driven-implementation skill referencing .pipeline/constitution.md.
        Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1.
        ---GOVERNANCE-END---

        TASK: Update specifications in docs/features/feat-001a-fuselage.md and docs/features/feat-001b-wing.md.
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("specification" in v.lower() or "multiple" in v.lower() for v in violations)


# ==============================================================================
# 3. Rule 2: Skill Template Match
# ==============================================================================

class TestRule2SkillTemplateMatch:
    """Tests enforcing exact Section 5 dispatch template match for standardized skills."""

    def test_compliant_adversarial_code_auditor_dispatch(self):
        prompt = """
        Execute adversarial-code-auditor skill.
        Read skills/adversarial-code-auditor/SKILL.md in full. Follow the Protocol (Section 3) exactly — Read, Audit, Write, Verify, File.
        FILE_PATH: cesium_native_bridge/src/bridge.cpp:56-61 PILLAR: Memory Safety MODE: bug-based REPO: gintatkinson/uas-003
        Return issue URLs with severities. PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == [], f"Expected 0 violations for valid skill dispatch, got: {violations}"

    def test_rejects_adversarial_auditor_missing_exact_opening_header(self):
        prompt = """
        Please run adversarial-code-auditor skill on the bridge file.
        FILE_PATH: src/bridge.cpp PILLAR: Concurrency MODE: bug-based REPO: gintatkinson/uas-003 PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("Execute adversarial-code-auditor skill." in v or "Rule 2" in v or "opening" in v.lower() for v in violations)

    def test_rejects_adversarial_auditor_missing_required_placeholders(self):
        prompt = """
        Execute adversarial-code-auditor skill.
        Read skills/adversarial-code-auditor/SKILL.md in full. Follow the Protocol (Section 3) exactly — Read, Audit, Write, Verify, File.
        FILE_PATH: src/bridge.cpp PILLAR: Concurrency
        Return issue URLs with severities. PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("MODE" in v or "REPO" in v or "missing" in v.lower() for v in violations)

    def test_rejects_adversarial_auditor_missing_proceed_token(self):
        prompt = """
        Execute adversarial-code-auditor skill.
        Read skills/adversarial-code-auditor/SKILL.md in full. Follow the Protocol (Section 3) exactly — Read, Audit, Write, Verify, File.
        FILE_PATH: src/bridge.cpp PILLAR: Concurrency MODE: bug-based REPO: gintatkinson/uas-003
        Return issue URLs with severities.
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("PROCEED" in v for v in violations)


# ==============================================================================
# 4. Rule 3: Zero Inline Issue Body
# ==============================================================================

class TestRule3ZeroInlineIssueBody:
    """Tests enforcing zero inline issue body (--body "...") in favor of --body-file."""

    def test_rejects_inline_double_quoted_body(self):
        prompt = """
        TASK: File the bug on GitHub using gh issue create --title "Bug" --body "This is an inline body description with details".
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("Rule 3" in v or "inline" in v.lower() or "--body-file" in v for v in violations)

    def test_rejects_inline_single_quoted_body(self):
        prompt = """
        TASK: File issue with gh issue create --title 'Bug' --body='Inline description here'
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("--body-file" in v or "inline" in v.lower() for v in violations)

    def test_rejects_inline_short_b_flag(self):
        prompt = """
        TASK: Create issue: gh issue create -t "Title" -b "Inline body string"
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert len(violations) >= 1
        assert any("--body-file" in v or "inline" in v.lower() for v in violations)

    def test_passes_valid_body_file_usage(self):
        prompt = """
        TASK: Run command gh issue create --title "Title" --body-file /tmp/issue_123.md
        PROCEED
        """
        violations = lint_prompt_payload(prompt)
        assert violations == []


# ==============================================================================
# 5. Transcript Parsing & Prompt Extraction
# ==============================================================================

class TestTranscriptParsing:
    """Tests parsing JSONL transcripts for invoke_subagent calls."""

    def test_extract_openai_style_tool_calls(self, tmp_path):
        jsonl_content = [
            json.dumps({
                "role": "assistant",
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "invoke_subagent",
                        "arguments": json.dumps({"prompt": "Execute adversarial-code-auditor skill.\nRead skills/adversarial-code-auditor/SKILL.md in full. Follow the Protocol (Section 3) exactly — Read, Audit, Write, Verify, File.\nFILE_PATH: bridge.cpp PILLAR: Memory Safety MODE: bug-based REPO: myrepo\nPROCEED"})
                    }
                }]
            }),
            json.dumps({
                "role": "assistant",
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "foo.py"})
                    }
                }]
            })
        ]
        transcript_file = tmp_path / "transcript.jsonl"
        transcript_file.write_text("\n".join(jsonl_content), encoding="utf-8")

        prompts = extract_prompts_from_transcript(transcript_file)
        assert len(prompts) == 1
        assert "Execute adversarial-code-auditor skill." in prompts[0][1]

    def test_extract_anthropic_style_tool_use(self, tmp_path):
        jsonl_content = [
            json.dumps({
                "type": "tool_use",
                "name": "invoke_subagent",
                "input": {
                    "prompt": "TASK: Single task on FEAT-001A.\nPROCEED"
                }
            })
        ]
        transcript_file = tmp_path / "transcript_anthropic.jsonl"
        transcript_file.write_text("\n".join(jsonl_content), encoding="utf-8")

        prompts = extract_prompts_from_transcript(transcript_file)
        assert len(prompts) == 1
        assert "FEAT-001A" in prompts[0][1]

    def test_extract_direct_dict_records(self, tmp_path):
        jsonl_content = [
            json.dumps({
                "name": "invoke_subagent",
                "prompt": "TASK: Direct prompt for FEAT-002A.\nPROCEED"
            })
        ]
        transcript_file = tmp_path / "transcript_direct.jsonl"
        transcript_file.write_text("\n".join(jsonl_content), encoding="utf-8")

        prompts = extract_prompts_from_transcript(transcript_file)
        assert len(prompts) == 1
        assert "FEAT-002A" in prompts[0][1]


# ==============================================================================
# 6. CLI Execution & Exit Codes
# ==============================================================================

class TestCLIExecution:
    """Tests CLI entrypoint, options, and exit codes."""

    def test_cli_valid_prompt_string_exits_0(self):
        valid_prompt = (
            "Execute adversarial-code-auditor skill.\n"
            "Read skills/adversarial-code-auditor/SKILL.md in full. Follow the Protocol (Section 3) exactly — Read, Audit, Write, Verify, File.\n"
            "FILE_PATH: bridge.cpp PILLAR: Memory Safety MODE: bug-based REPO: myrepo\n"
            "Return issue URLs with severities. PROCEED"
        )
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"), "--prompt", valid_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "PASSED" in result.stdout

    def test_cli_invalid_prompt_string_exits_1(self):
        invalid_prompt = 'TASK: Create issue with gh issue create --body "inline body"'
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"), "--prompt", invalid_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "FAILED" in result.stdout or "VIOLATION" in result.stdout or "Rule 3" in result.stdout

    def test_cli_positional_raw_prompt_string(self):
        valid_prompt = "TASK: Single task for FEAT-001A.\nPROCEED"
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"), valid_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "PASSED" in result.stdout

    def test_cli_transcript_file_passes(self, tmp_path):
        valid_prompt = (
            "TASK: Implement single component for FEAT-001A.\nPROCEED"
        )
        transcript_file = tmp_path / "valid.jsonl"
        transcript_file.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": valid_prompt}) + "\n",
            encoding="utf-8"
        )
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"), str(transcript_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "PASSED" in result.stdout

    def test_cli_transcript_file_fails_on_violations(self, tmp_path):
        invalid_prompt = (
            "TASK: Do multiple things:\n1. Task one\n2. Task two\nPROCEED"
        )
        transcript_file = tmp_path / "invalid.jsonl"
        transcript_file.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": invalid_prompt}) + "\n",
            encoding="utf-8"
        )
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"), "--file", str(transcript_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "FAILED" in result.stdout

    def test_cli_json_report_generation(self, tmp_path):
        valid_prompt = "TASK: Single task for FEAT-001A.\nPROCEED"
        report_file = tmp_path / "report.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"),
            "--prompt", valid_prompt,
            "--json-report", str(report_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert report_file.exists()
        data = json.loads(report_file.read_text(encoding="utf-8"))
        assert data["status"] == "PASS"
        assert data["total_prompts"] == 1
        assert data["total_violations"] == 0

    def test_cli_json_report_on_failure(self, tmp_path):
        invalid_prompt = 'TASK: Create issue gh issue create --body "inline"'
        report_file = tmp_path / "fail_report.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "lint_subagent_prompt.py"),
            "--prompt", invalid_prompt,
            "--json-report", str(report_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert report_file.exists()
        data = json.loads(report_file.read_text(encoding="utf-8"))
        assert data["status"] == "FAIL"
        assert data["total_violations"] >= 1


# ==============================================================================
# 7. Integration with scripts/verify_subagent_output.py
# ==============================================================================

class TestVerifySubagentOutputIntegration:
    """Tests verify_subagent_output.py integration with lint_prompt_payload and transcript scanning."""

    def test_scan_transcript_logs_clean(self, tmp_path):
        from scripts.verify_subagent_output import scan_transcript_logs

        logs_dir = tmp_path / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        valid_prompt = "TASK: Single task for FEAT-001A.\nPROCEED"
        transcript = logs_dir / "session_001.jsonl"
        transcript.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": valid_prompt}) + "\n",
            encoding="utf-8"
        )

        results, all_passed = scan_transcript_logs(str(logs_dir))
        assert all_passed is True
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["violations"] == []

    def test_scan_transcript_logs_with_violations(self, tmp_path):
        from scripts.verify_subagent_output import scan_transcript_logs

        logs_dir = tmp_path / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        invalid_prompt = 'TASK: Create issue gh issue create --body "inline string"'
        transcript = logs_dir / "session_002.jsonl"
        transcript.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": invalid_prompt}) + "\n",
            encoding="utf-8"
        )

        results, all_passed = scan_transcript_logs(str(logs_dir))
        assert all_passed is False
        assert len(results) == 1
        assert results[0]["passed"] is False
        assert len(results[0]["violations"]) >= 1

    def test_verify_subagent_output_cli_blocks_commit_on_invalid_transcript(self, tmp_path):
        logs_dir = tmp_path / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        invalid_prompt = "TASK: Multi-item list:\n1. Step A\n2. Step B\nPROCEED"
        transcript = logs_dir / "session_bad.jsonl"
        transcript.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": invalid_prompt}) + "\n",
            encoding="utf-8"
        )

        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_subagent_output.py"),
            "--logs-dir", str(logs_dir)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert result.returncode == 1, f"Expected returncode 1, got {result.returncode}. Output: {result.stdout}\n{result.stderr}"
        assert "FAILED" in result.stdout or "FAILED" in result.stderr

    def test_verify_subagent_output_cli_passes_on_valid_transcript(self, tmp_path):
        logs_dir = tmp_path / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        valid_prompt = "TASK: Single atomic task for FEAT-002A.\nPROCEED"
        transcript = logs_dir / "session_good.jsonl"
        transcript.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": valid_prompt}) + "\n",
            encoding="utf-8"
        )

        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_subagent_output.py"),
            "--logs-dir", str(logs_dir)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert result.returncode == 0, f"Expected returncode 0, got {result.returncode}. Output: {result.stdout}\n{result.stderr}"
        assert "PASSED" in result.stdout

    def test_verify_subagent_output_precommit_auto_scans_system_generated_logs(self, tmp_path):
        logs_dir = tmp_path / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        invalid_prompt = 'TASK: Bad prompt with gh issue create -b "inline"'
        transcript = logs_dir / "auto_scan.jsonl"
        transcript.write_text(
            json.dumps({"name": "invoke_subagent", "prompt": invalid_prompt}) + "\n",
            encoding="utf-8"
        )

        # Running without --logs-dir in cwd where .system_generated/logs exists should auto-scan and fail
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_subagent_output.py")
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert result.returncode == 1, f"Expected returncode 1, got {result.returncode}. Output: {result.stdout}\n{result.stderr}"

