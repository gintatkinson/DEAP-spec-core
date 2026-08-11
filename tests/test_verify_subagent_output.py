import json
import os
import subprocess
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "verify_subagent_output.py")

def test_script_exists():
    assert os.path.exists(SCRIPT_PATH), f"Script missing at {SCRIPT_PATH}"

def test_verify_valid_output(tmp_path):
    deliverable = tmp_path / "feat-01.md"
    content = """---
title: "Test Feature"
type: "feature"
---

# Feature: Test Feature

See issue: https://github.com/org/repo/issues/123

## Architecture
```mermaid
classDiagram
    class TestClass {
        +String name "[1]"
    }
```

## Description
This is a fully resolved feature document without placeholders.

## Source References
Structural Schema: schema.yang

## Logical UI & Interface Bindings
- **Target LUI Component:** StringInputField
"""
    deliverable.write_text(content)
    report_file = tmp_path / "report.json"

    cmd = [sys.executable, SCRIPT_PATH, "--files", str(deliverable), "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Validator failed: {res.stderr}\n{res.stdout}"

    assert report_file.exists()
    report = json.loads(report_file.read_text())
    assert report["status"] == "PASS"
    assert len(report["checks"]) == 1
    assert report["checks"][0]["non_zero"] is True
    assert report["checks"][0]["creation_proof"] is True
    assert report["checks"][0]["escape_tokens_clear"] is True

def test_verify_rejects_empty_file(tmp_path):
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("")
    report_file = tmp_path / "report.json"

    cmd = [sys.executable, SCRIPT_PATH, "--files", str(empty_file), "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0

    assert report_file.exists()
    report = json.loads(report_file.read_text())
    assert report["status"] == "FAIL"
    assert report["checks"][0]["non_zero"] is False

def test_verify_rejects_escape_tokens(tmp_path):
    bad_file = tmp_path / "feat-bad.md"
    content = """---
title: "Bad Feature"
---

# Feature: Bad Feature

Link: {{REQUIRED_JUSTIFICATION}}
"""
    bad_file.write_text(content)
    report_file = tmp_path / "report.json"

    cmd = [sys.executable, SCRIPT_PATH, "--files", str(bad_file), "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0

    assert report_file.exists()
    report = json.loads(report_file.read_text())
    assert report["status"] == "FAIL"
    assert report["checks"][0]["escape_tokens_clear"] is False

def test_verify_rejects_unclosed_mermaid(tmp_path):
    bad_mermaid = tmp_path / "feat-mermaid.md"
    content = """---
title: "Bad Mermaid Feature"
---

# Feature

```mermaid
classDiagram
    class TestClass

## Next Section
"""
    bad_mermaid.write_text(content)
    report_file = tmp_path / "report.json"

    cmd = [sys.executable, SCRIPT_PATH, "--files", str(bad_mermaid), "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0


def test_verify_prompt_payload_cli_pass(tmp_path):
    report_file = tmp_path / "report.json"
    valid_prompt = (
        "Execute view_file on skills/feature-driven-implementation/SKILL.md as step 1. "
        "Perform full implementation without truncation."
    )
    cmd = [sys.executable, SCRIPT_PATH, "--prompt", valid_prompt, "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Prompt verification failed: {res.stderr}\n{res.stdout}"
    report = json.loads(report_file.read_text())
    assert report["status"] == "PASS"


def test_verify_prompt_payload_cli_fail(tmp_path):
    report_file = tmp_path / "report.json"
    invalid_prompt = "Do audit task using audit skill."
    cmd = [sys.executable, SCRIPT_PATH, "--prompts", invalid_prompt, "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    report = json.loads(report_file.read_text())
    assert report["status"] == "FAIL"


def test_verify_prompt_payload_rejects_gh_issue_close(tmp_path):
    report_file = tmp_path / "report.json"
    close_prompt = "Execute view_file on skills/debug-protocol/SKILL.md as step 1. Run gh issue close 1."
    cmd = [sys.executable, SCRIPT_PATH, "--prompt", close_prompt, "--report", str(report_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    report = json.loads(report_file.read_text())
    assert report["status"] == "FAIL"
    assert report["checks"][0]["forbid_issue_close"] is False

