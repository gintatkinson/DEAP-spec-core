import os
import signal
import subprocess
import sys
import unittest.mock as mock
import pytest

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import verify_downstream_baseline


def test_run_bounded_success():
    """
    Assert _run_bounded executes process using start_new_session=True and succeeds when exit code is 0.
    """
    mock_proc = mock.MagicMock()
    mock_proc.pid = 1234
    mock_proc.wait.return_value = 0

    with mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        verify_downstream_baseline._run_bounded(["echo", "hello"], cwd="/tmp", timeout=10, label="test echo")
        mock_popen.assert_called_once_with(["echo", "hello"], cwd="/tmp", start_new_session=True)
        mock_proc.wait.assert_called_once_with(timeout=10)


def test_run_bounded_timeout_kills_process_group():
    """
    Assert _run_bounded traps subprocess.TimeoutExpired and calls os.killpg with pgid and SIGTERM/SIGKILL.
    """
    mock_proc = mock.MagicMock()
    mock_proc.pid = 5678
    # First call to wait() raises TimeoutExpired, second call (after SIGTERM wait timeout or SIGKILL) returns
    mock_proc.wait.side_effect = [subprocess.TimeoutExpired(["sleep", "100"], 10), 0]

    with mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen, \
         mock.patch("os.getpgid", return_value=5678) as mock_getpgid, \
         mock.patch("os.killpg") as mock_killpg:
        
        with pytest.raises(subprocess.TimeoutExpired) as exc_info:
            verify_downstream_baseline._run_bounded(["sleep", "100"], cwd="/tmp", timeout=10, label="test sleep")

        mock_popen.assert_called_once_with(["sleep", "100"], cwd="/tmp", start_new_session=True)
        mock_getpgid.assert_called_with(5678)
        assert mock_killpg.called
        killed_pgids = [call.args[0] for call in mock_killpg.call_args_list]
        killed_signals = [call.args[1] for call in mock_killpg.call_args_list]
        assert 5678 in killed_pgids
        assert signal.SIGTERM in killed_signals or signal.SIGKILL in killed_signals


def test_run_bounded_called_process_error():
    """
    Assert _run_bounded raises subprocess.CalledProcessError when command exits with non-zero code.
    """
    mock_proc = mock.MagicMock()
    mock_proc.pid = 9999
    mock_proc.wait.return_value = 1

    with mock.patch("subprocess.Popen", return_value=mock_proc):
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            verify_downstream_baseline._run_bounded(["false"], cwd="/tmp", timeout=10, label="test false")
        assert exc_info.value.returncode == 1


def test_run_verification_uses_run_bounded_for_flutter(tmp_path):
    """
    Assert _run_verification invokes _run_bounded for Flutter commands.
    """
    (tmp_path / ".gitignore").write_text("build/\n")
    dest = tmp_path / "app_flutter"
    dest.mkdir()
    (dest / "pubspec.yaml").write_text("name: test_app\n")
    (dest / "analysis_options.yaml").write_text("linter: {}\n")
    lib = dest / "lib"
    lib.mkdir()
    (lib / "main.dart").write_text("void main() {}\n")
    domain = lib / "domain"
    domain.mkdir()
    (domain / "validation.dart").write_text("void validate() {}\n")
    (domain / "repository_resolver.dart").write_text("class RepositoryResolver {}\n")

    # Build release app bundle path mock
    release_dir = dest / "build" / "macos" / "Build" / "Products" / "Release"
    release_dir.mkdir(parents=True)
    (release_dir / "Platform Console.app").mkdir()

    calls = []

    def mock_run_bounded(cmd, cwd, timeout, label):
        calls.append((cmd, cwd, timeout, label))

    args = mock.MagicMock()
    args.no_domain = False

    with mock.patch.object(verify_downstream_baseline, "_run_bounded", side_effect=mock_run_bounded), \
         mock.patch.object(verify_downstream_baseline, "load_mandated_classes", return_value=[]):
        verify_downstream_baseline._run_verification(args, str(dest), str(tmp_path), is_flutter=True, is_react=False)

    cmd_names = [c[0][0] for c in calls]
    assert "flutter" in cmd_names
    flutter_cmds = [c[0] for c in calls if c[0][0] == "flutter"]
    assert ["flutter", "pub", "get"] in flutter_cmds
    assert ["flutter", "analyze", "--no-fatal-warnings", "--no-fatal-infos"] in flutter_cmds
    assert ["flutter", "test"] in flutter_cmds
    assert ["flutter", "build", "macos", "--release"] in flutter_cmds


def test_run_verification_uses_run_bounded_for_react(tmp_path):
    """
    Assert _run_verification invokes _run_bounded for React commands.
    """
    (tmp_path / ".gitignore").write_text("build/\n")
    dest = tmp_path / "web_react"
    dest.mkdir()
    (dest / "package.json").write_text('{"name": "test_web"}\n')
    (dest / "tsconfig.json").write_text('{}\n')
    src = dest / "src"
    src.mkdir()
    (src / "main.tsx").write_text("console.log('hi');\n")
    domain = src / "domain"
    domain.mkdir()
    (domain / "validation.ts").write_text("export const v = 1;\n")

    calls = []

    def mock_run_bounded(cmd, cwd, timeout, label):
        calls.append((cmd, cwd, timeout, label))

    args = mock.MagicMock()
    args.no_domain = False

    with mock.patch.object(verify_downstream_baseline, "_run_bounded", side_effect=mock_run_bounded), \
         mock.patch.object(verify_downstream_baseline, "load_mandated_classes", return_value=[]):
        verify_downstream_baseline._run_verification(args, str(dest), str(tmp_path), is_flutter=False, is_react=True)

    react_cmds = [c[0] for c in calls if c[0][0] == "npm"]
    assert ["npm", "install"] in react_cmds
    assert ["npm", "run", "build"] in react_cmds


def test_run_verification_removes_preexisting_zip_archive_and_logs_size(tmp_path, capsys):
    """
    Assert pre-existing zip_path is removed before zipping and created archive size is logged.
    """
    (tmp_path / ".gitignore").write_text("build/\n")
    dest = tmp_path / "app_flutter"
    dest.mkdir()
    (dest / "pubspec.yaml").write_text("name: test_app\n")
    (dest / "analysis_options.yaml").write_text("linter: {}\n")
    lib = dest / "lib"
    lib.mkdir()
    (lib / "main.dart").write_text("void main() {}\n")
    domain = lib / "domain"
    domain.mkdir()
    (domain / "validation.dart").write_text("void validate() {}\n")
    (domain / "repository_resolver.dart").write_text("class RepositoryResolver {}\n")

    release_dir = dest / "build" / "macos" / "Build" / "Products" / "Release"
    release_dir.mkdir(parents=True)
    (release_dir / "Platform Console.app").mkdir()

    # Create pre-existing zip file at the expected location (repo_root / "app_flutter_release.zip")
    stale_zip = tmp_path / "app_flutter_release.zip"
    stale_zip.write_bytes(b"stale_archive_content_12345")

    zip_existed_during_zip_call = []

    def mock_run_bounded(cmd, cwd, timeout, label):
        if cmd[0] == "zip":
            zip_path = cmd[2]
            # Record whether the pre-existing zip file was removed before zip was called
            zip_existed_during_zip_call.append(os.path.exists(zip_path))
            # Create a fresh zip file to simulate zip output
            with open(zip_path, "wb") as f:
                f.write(b"fresh_zip_content_9876543210")

    args = mock.MagicMock()
    args.no_domain = False

    with mock.patch.object(verify_downstream_baseline, "_run_bounded", side_effect=mock_run_bounded), \
         mock.patch.object(verify_downstream_baseline, "load_mandated_classes", return_value=[]):
        verify_downstream_baseline._run_verification(args, str(dest), str(tmp_path), is_flutter=True, is_react=False)

    assert zip_existed_during_zip_call == [False], "zip_path should have been unlinked before executing zip command"
    captured = capsys.readouterr()
    assert "Created archive size:" in captured.out or "bytes" in captured.out
    assert "26 bytes" in captured.out or f"{len(b'fresh_zip_content_9876543210')} bytes" in captured.out


def test_cleanup_workspace_sqlite_sidecars(tmp_path):
    """
    Assert cleanup_workspace preserves SQLite sidecar files (.db-wal, .db-shm, .db-journal)
    when the owner .db file exists, and unlinks them when the owner .db file is absent.
    """
    # Create active database and its sidecars
    active_db = tmp_path / "active.db"
    active_db.write_text("db_content")
    active_wal = tmp_path / "active.db-wal"
    active_wal.write_text("wal_content")
    active_shm = tmp_path / "active.db-shm"
    active_shm.write_text("shm_content")
    active_journal = tmp_path / "active.db-journal"
    active_journal.write_text("journal_content")

    # Create orphaned sidecars (no owner .db file)
    orphaned_wal = tmp_path / "orphaned.db-wal"
    orphaned_wal.write_text("orphaned_wal")
    orphaned_shm = tmp_path / "orphaned.db-shm"
    orphaned_shm.write_text("orphaned_shm")
    orphaned_journal = tmp_path / "orphaned.db-journal"
    orphaned_journal.write_text("orphaned_journal")

    verify_downstream_baseline.cleanup_workspace(str(tmp_path))

    # Active .db and its sidecars MUST be preserved
    assert active_db.exists()
    assert active_wal.exists()
    assert active_shm.exists()
    assert active_journal.exists()

    # Orphaned sidecars MUST be unlinked
    assert not orphaned_wal.exists()
    assert not orphaned_shm.exists()
    assert not orphaned_journal.exists()


def test_tag_restoration_point_success():
    """
    Assert tag_restoration_point accepts repo_root, passes cwd=repo_root and timeout=30 to subprocess.run.
    """
    mock_res = mock.MagicMock()
    mock_res.returncode = 0

    with mock.patch("subprocess.run", return_value=mock_res) as mock_run:
        result = verify_downstream_baseline.tag_restoration_point(repo_root="/custom/root")
        assert result is True
        assert mock_run.call_count == 2
        
        # Check first call (git rev-parse HEAD)
        args1, kwargs1 = mock_run.call_args_list[0]
        assert args1[0] == ["git", "rev-parse", "HEAD"]
        assert kwargs1.get("cwd") == "/custom/root"
        assert kwargs1.get("timeout") == 30

        # Check second call (git tag -f restoration-point)
        args2, kwargs2 = mock_run.call_args_list[1]
        assert args2[0] == ["git", "tag", "-f", "restoration-point"]
        assert kwargs2.get("cwd") == "/custom/root"
        assert kwargs2.get("timeout") == 30


def test_tag_restoration_point_timeout(capsys):
    """
    Assert tag_restoration_point handles subprocess.TimeoutExpired, logs a warning to stderr, and returns False.
    """
    with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["git", "rev-parse", "HEAD"], 30)):
        result = verify_downstream_baseline.tag_restoration_point(repo_root="/custom/root")
        assert result is False
        captured = capsys.readouterr()
        assert "WARNING: Failed to tag restoration point" in captured.err or "timed out" in captured.err



