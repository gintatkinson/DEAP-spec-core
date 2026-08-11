import json
import os
import subprocess
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GENERATE_DIGEST_SCRIPT = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts", "generate_input_digest.py")
VERIFY_INGESTION_SCRIPT = os.path.join(REPO_ROOT, "scripts", "verify_input_ingestion.py")
BLUEPRINT_DOC = os.path.join(REPO_ROOT, "docs", "designs", "input-validation-architecture-blueprint.md")


def test_scripts_and_doc_exist():
    assert os.path.exists(GENERATE_DIGEST_SCRIPT), f"Script missing: {GENERATE_DIGEST_SCRIPT}"
    assert os.path.exists(VERIFY_INGESTION_SCRIPT), f"Script missing: {VERIFY_INGESTION_SCRIPT}"
    assert os.path.exists(BLUEPRINT_DOC), f"Blueprint missing: {BLUEPRINT_DOC}"


def test_generate_input_digest(tmp_path):
    input_file = tmp_path / "sample_spec.md"
    content = """# Title: Specification Document

## Section 1: Overview
This is a test input document.

## Section 2: Requirements
- Requirement 1: Valid input handling.
- Requirement 2: Zero-loss propagation.
"""
    input_file.write_text(content)
    output_digest = tmp_path / ".pipeline" / "input-digest.json"

    cmd = [sys.executable, GENERATE_DIGEST_SCRIPT, "--input", str(input_file), "--output", str(output_digest)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Digest generation failed: {res.stderr}\n{res.stdout}"

    assert output_digest.exists()
    data = json.loads(output_digest.read_text())

    assert "sha256" in data
    assert len(data["sha256"]) == 64
    assert "total_lines" in data
    assert data["total_lines"] == len(content.splitlines())
    assert "files" in data
    
    file_entry = data["files"].get(str(input_file)) or data["files"].get(os.path.basename(str(input_file)))
    if not file_entry:
        file_entry = list(data["files"].values())[0]
    
    assert file_entry["sha256"] == data["sha256"]
    assert file_entry["total_lines"] == len(content.splitlines())
    assert "line_range_bounds" in file_entry or "line_range" in file_entry
    assert "structural_section_markers" in file_entry
    assert "# Title: Specification Document" in file_entry["structural_section_markers"]
    assert "## Section 1: Overview" in file_entry["structural_section_markers"]


def test_verify_input_ingestion_valid(tmp_path):
    spec_file = tmp_path / "input_spec.md"
    spec_content = "# Target Spec\nLine 1\nLine 2\n"
    spec_file.write_text(spec_content)

    digest_file = tmp_path / "input-digest.json"
    digest_data = {
        "sha256": "dummy",
        "total_lines": 3,
        "files": {
            str(spec_file): {
                "sha256": "dummy",
                "total_lines": 3,
                "line_range_bounds": [1, 3],
                "structural_section_markers": ["# Target Spec"]
            }
        }
    }
    digest_file.write_text(json.dumps(digest_data))

    transcript_file = tmp_path / "transcript.jsonl"
    step1 = {
        "step_index": 1,
        "type": "PLANNER_RESPONSE",
        "tool_calls": [
            {
                "name": "view_file",
                "args": {"AbsolutePath": str(spec_file)}
            }
        ]
    }
    step2 = {
        "step_index": 2,
        "type": "TOOL_RESPONSE",
        "content": f"File Path: {spec_file}\n{spec_content}"
    }
    transcript_file.write_text(json.dumps(step1) + "\n" + json.dumps(step2) + "\n")

    cmd = [
        sys.executable,
        VERIFY_INGESTION_SCRIPT,
        "--transcript", str(transcript_file),
        "--input-digest", str(digest_file),
        "--target-files", str(spec_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Ingestion verification failed unexpectedly: {res.stderr}\n{res.stdout}"


def test_verify_input_ingestion_missing_view_file(tmp_path):
    spec_file = tmp_path / "input_spec.md"
    spec_file.write_text("# Target Spec\nLine 1\nLine 2\n")

    digest_file = tmp_path / "input-digest.json"
    digest_file.write_text(json.dumps({"files": {str(spec_file): {}}}))

    transcript_file = tmp_path / "transcript.jsonl"
    # Transcript has list_dir but NO view_file call
    step = {
        "step_index": 1,
        "type": "PLANNER_RESPONSE",
        "tool_calls": [
            {
                "name": "list_dir",
                "args": {"DirectoryPath": str(tmp_path)}
            }
        ]
    }
    transcript_file.write_text(json.dumps(step) + "\n")

    cmd = [
        sys.executable,
        VERIFY_INGESTION_SCRIPT,
        "--transcript", str(transcript_file),
        "--input-digest", str(digest_file),
        "--target-files", str(spec_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1, f"Expected returncode 1 for missing view_file, got {res.returncode}"


def test_verify_input_ingestion_truncation_detected(tmp_path):
    spec_file = tmp_path / "input_spec.md"
    spec_file.write_text("# Target Spec\nLine 1\nLine 2\n")

    digest_file = tmp_path / "input-digest.json"
    digest_file.write_text(json.dumps({"files": {str(spec_file): {}}}))

    transcript_file = tmp_path / "transcript.jsonl"
    step1 = {
        "step_index": 1,
        "type": "PLANNER_RESPONSE",
        "tool_calls": [
            {
                "name": "view_file",
                "args": {"AbsolutePath": str(spec_file)}
            }
        ]
    }
    step2 = {
        "step_index": 2,
        "type": "TOOL_RESPONSE",
        "content": f"File Path: {spec_file}\n# Target Spec\n...\n<truncated 50 lines>\nLine 2"
    }
    transcript_file.write_text(json.dumps(step1) + "\n" + json.dumps(step2) + "\n")

    cmd = [
        sys.executable,
        VERIFY_INGESTION_SCRIPT,
        "--transcript", str(transcript_file),
        "--input-digest", str(digest_file),
        "--target-files", str(spec_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1, f"Expected returncode 1 when truncation tokens are detected, got {res.returncode}"


def test_blueprint_document_reference_integrity():
    assert os.path.exists(BLUEPRINT_DOC), f"Blueprint document missing at {BLUEPRINT_DOC}"
    with open(BLUEPRINT_DOC, "r", encoding="utf-8") as f:
        content = f.read()

    assert len(content) > 100
    assert "4-Stage Input Validation & Zero-Loss Propagation Architecture" in content
    assert "generate_input_digest.py" in content
    assert "verify_input_ingestion.py" in content
    assert ".pipeline/input-digest.json" in content
    assert "```mermaid" in content
    assert "sequenceDiagram" in content
