import json
import os
import subprocess
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_PATH = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts", "generate_schema_digest.py")

def test_script_exists():
    assert os.path.exists(SCRIPT_PATH), f"Script missing at {SCRIPT_PATH}"

def test_generate_schema_digest_basic(tmp_path):
    schema_file = tmp_path / "test_model.yang"
    content = """
    module test-model {
        namespace "urn:test:model";
        prefix tm;

        typedef my-type {
            type string;
        }

        identity base-identity;

        grouping my-grouping {
            leaf grouped-leaf {
                type string;
            }
        }

        container main-container {
            leaf name {
                type string;
            }
            list item-list {
                key "id";
                leaf id {
                    type uint32;
                }
            }
        }
    }
    """
    schema_file.write_text(content)
    output_digest = tmp_path / ".pipeline" / "schema-digest.json"
    output_digest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, SCRIPT_PATH, "--input", str(schema_file), "--output", str(output_digest)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Script failed: {res.stderr}"

    assert output_digest.exists()
    data = json.loads(output_digest.read_text())

    assert "sha256" in data
    assert len(data["sha256"]) == 64
    assert "total_lines" in data
    assert data["total_lines"] > 0
    assert "node_counts" in data

    nc = data["node_counts"]
    assert nc["containers"] == 1
    assert nc["lists"] == 1
    assert nc["leaves"] == 3
    assert nc["typedefs"] == 1
    assert nc["identities"] == 1
    assert nc["groupings"] == 1

    assert "schema_nodes" in data
    assert "main-container" in data["schema_nodes"]
    assert "item-list" in data["schema_nodes"]
    assert "name" in data["schema_nodes"]
    assert "id" in data["schema_nodes"]
