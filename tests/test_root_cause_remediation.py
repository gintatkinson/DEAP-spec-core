import json
import os
import sys
import pytest

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import verify_downstream_baseline
import prune_stale_projects


# --- Tests for verify_downstream_baseline.py (Checks 10, 11, 12) ---

def test_check_gitignore_exists_success(tmp_path):
    """Check 10 passes when .gitignore exists in repo_root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".gitignore").write_text("build/\n*.log\n")

    # Should not raise exception
    verify_downstream_baseline.check_gitignore_exists(str(repo_root))


def test_check_gitignore_exists_missing_raises_sysexit(tmp_path):
    """Check 10 fails (sys.exit(1)) when .gitignore is missing from repo_root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        verify_downstream_baseline.check_gitignore_exists(str(repo_root))
    assert exc_info.value.code == 1


def test_check_no_ds_store_files_success(tmp_path):
    """Check 11 passes when zero .DS_Store files exist in repo_root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "main.py").write_text("print('hello')\n")

    verify_downstream_baseline.check_no_ds_store_files(str(repo_root))


def test_check_no_ds_store_files_found_raises_sysexit(tmp_path):
    """Check 11 fails (sys.exit(1)) when .DS_Store exists in working tree."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    sub_dir = repo_root / "subdir"
    sub_dir.mkdir()
    (sub_dir / ".DS_Store").write_bytes(b"os_metadata")

    with pytest.raises(SystemExit) as exc_info:
        verify_downstream_baseline.check_no_ds_store_files(str(repo_root))
    assert exc_info.value.code == 1


def test_check_no_duplicate_master_blueprints_success(tmp_path):
    """Check 12 passes when no duplicate master core blueprints exist."""
    dest = tmp_path / "downstream_app"
    dest.mkdir()
    (dest / "README.md").write_text("# App\n")

    verify_downstream_baseline.check_no_duplicate_master_blueprints(str(dest))


@pytest.mark.parametrize("blueprint_name", [
    "DEAP_MASTER_ARCHITECTURE.md",
    "THREE_TIER_GOVERNANCE_BLUEPRINT.md",
    "DEAP_SYSML_V2_SAFETY_MODEL_SPECIFICATION.sysml"
])
def test_check_no_duplicate_master_blueprints_found_raises_sysexit(tmp_path, blueprint_name):
    """Check 12 fails (sys.exit(1)) when a duplicate master core blueprint is found."""
    dest = tmp_path / "downstream_app"
    dest.mkdir()
    (dest / blueprint_name).write_text("# Duplicated Master Blueprint\n")

    with pytest.raises(SystemExit) as exc_info:
        verify_downstream_baseline.check_no_duplicate_master_blueprints(str(dest))
    assert exc_info.value.code == 1


# --- Tests for prune_stale_projects.py ---

def test_prune_projects_json_removes_nonexistent_paths(tmp_path):
    """prune_projects_json removes non-existent path entries while keeping valid ones."""
    valid_dir = tmp_path / "valid_project"
    valid_dir.mkdir()

    projects_file = tmp_path / "projects.json"
    initial_data = [
        str(valid_dir),
        "/non/existent/path/foo_bar_project"
    ]
    projects_file.write_text(json.dumps(initial_data))

    pruned, kept = prune_stale_projects.prune_projects_json(projects_file=str(projects_file))

    assert len(pruned) == 1
    assert str(valid_dir) in kept

    with open(projects_file, "r") as f:
        updated_data = json.load(f)
    assert updated_data == [str(valid_dir)]


def test_clean_dead_temp_dirs(tmp_path):
    """clean_dead_temp_dirs removes dead temporary directories and dead symlinks."""
    tmp_dir = tmp_path / "tmp"
    history_dir = tmp_path / "history"
    tmp_dir.mkdir()
    history_dir.mkdir()

    dead_temp = tmp_dir / "dead_clone_123"
    dead_temp.mkdir()

    active_temp = tmp_dir / "active_clone_456"
    active_temp.mkdir()

    cleaned = prune_stale_projects.clean_dead_temp_dirs(
        tmp_dir=str(tmp_dir),
        history_dir=str(history_dir),
        active_paths=[str(active_temp)]
    )

    assert str(dead_temp) in cleaned
    assert not dead_temp.exists()
    assert active_temp.exists()


def test_clean_ds_store_files(tmp_path):
    """clean_ds_store_files removes all .DS_Store files in the workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sub_dir = workspace / "nested"
    sub_dir.mkdir()

    ds1 = workspace / ".DS_Store"
    ds1.write_bytes(b"ds1")
    ds2 = sub_dir / ".DS_Store"
    ds2.write_bytes(b"ds2")

    normal_file = sub_dir / "index.js"
    normal_file.write_text("console.log('ok');")

    removed = prune_stale_projects.clean_ds_store_files(workspace_dir=str(workspace))

    assert len(removed) == 2
    assert not ds1.exists()
    assert not ds2.exists()
    assert normal_file.exists()


# --- Contract verification tests ---

def test_constitution_has_ssot_mandate():
    """Verify .pipeline/constitution.md includes SSOT and Clean Baseline mandate."""
    const_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".pipeline", "constitution.md"))
    with open(const_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Downstream Single Source of Truth (SSOT) & Clean Baseline Mandate" in content
    assert "DEAP_MASTER_ARCHITECTURE.md" in content
    assert ".gitignore" in content


def test_agents_md_has_ssot_mandate():
    """Verify .agents/AGENTS.md includes SSOT and Clean Baseline mandate."""
    agents_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".agents", "AGENTS.md"))
    with open(agents_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Downstream Single Source of Truth (SSOT) & Clean Baseline Mandate" in content
    assert "No Master Blueprint Duplication" in content
    assert "Zero `.DS_Store` Policy" in content
