import json
import os
import subprocess
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROBE_SCRIPT = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts", "subagent_preflight_probe.py")

sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "src"))
from parity_auditor.validators.plan_validator import PlanValidator
from parity_auditor.core.workspace import WorkspaceRepository


def test_probe_script_exists():
    assert os.path.exists(PROBE_SCRIPT)


def test_preflight_probe_execution():
    res = subprocess.run([sys.executable, PROBE_SCRIPT, "--phase", "phase2"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "PASSED" in res.stdout


def test_plan_validator_100_percent_coverage(tmp_path):
    digest_file = tmp_path / "schema-digest.json"
    digest_data = {
        "sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
        "total_lines": 50,
        "node_counts": {"containers": 1, "lists": 0, "leaves": 2, "typedefs": 0, "identities": 0, "groupings": 0},
        "schema_nodes": ["node_alpha", "node_beta"]
    }
    digest_file.write_text(json.dumps(digest_data))

    plan_file = tmp_path / "implementation_plan.md"
    plan_content = """# Implementation Plan
## Schema Coverage
Mapped nodes:
- node_alpha
- node_beta
"""
    plan_file.write_text(plan_content)

    repo = WorkspaceRepository(str(tmp_path))
    validator = PlanValidator()
    errors = validator.validate(repo, digest_path=str(digest_file), plan_path=str(plan_file))
    assert len(errors) == 0


def test_plan_validator_incomplete_coverage_rejection(tmp_path):
    digest_file = tmp_path / "schema-digest.json"
    digest_data = {
        "sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
        "total_lines": 50,
        "node_counts": {"containers": 1, "lists": 0, "leaves": 2, "typedefs": 0, "identities": 0, "groupings": 0},
        "schema_nodes": ["node_alpha", "node_missing"]
    }
    digest_file.write_text(json.dumps(digest_data))

    plan_file = tmp_path / "implementation_plan.md"
    plan_content = """# Implementation Plan
Mapped nodes:
- node_alpha
"""
    plan_file.write_text(plan_content)

    repo = WorkspaceRepository(str(tmp_path))
    validator = PlanValidator()
    errors = validator.validate(repo, digest_path=str(digest_file), plan_path=str(plan_file))
    assert len(errors) == 1
    assert "node_missing" in str(errors[0]) or "coverage" in str(errors[0]).lower()
