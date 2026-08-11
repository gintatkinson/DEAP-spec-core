import os
import sys
import unittest.mock as mock
import pytest

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import verify_downstream_baseline

def test_verify_downstream_baseline_detects_both_flutter_and_react_from_root(tmp_path):
    """
    Issue #352 Verification:
    When running verify_downstream_baseline from repository root against a target directory
    containing both app_flutter/pubspec.yaml and web_react/package.json,
    verification is executed sequentially for each valid target without target commingling.
    """
    root_dir = tmp_path / "downstream_repo"
    root_dir.mkdir()
    
    app_flutter = root_dir / "app_flutter"
    app_flutter.mkdir()
    (app_flutter / "pubspec.yaml").write_text("name: test_flutter\n")
    
    web_react = root_dir / "web_react"
    web_react.mkdir()
    (web_react / "package.json").write_text('{"name": "test_react"}\n')

    captured_calls = []

    def mock_run_verification(args, dest, repo_root, is_flutter, is_react):
        captured_calls.append({
            "dest": dest,
            "repo_root": repo_root,
            "is_flutter": is_flutter,
            "is_react": is_react,
        })
        return

    def mock_tag_restoration_point(repo_root=None):
        return True

    def mock_cleanup_workspace(dest):
        pass

    with mock.patch.object(sys, "argv", ["verify_downstream_baseline.py", "--no-domain", str(root_dir)]), \
         mock.patch.object(verify_downstream_baseline, "_run_verification", side_effect=mock_run_verification), \
         mock.patch.object(verify_downstream_baseline, "tag_restoration_point", side_effect=mock_tag_restoration_point), \
         mock.patch.object(verify_downstream_baseline, "cleanup_workspace", side_effect=mock_cleanup_workspace):
        
        try:
            verify_downstream_baseline.main()
        except SystemExit as e:
            assert e.code == 0, f"main() exited with code {e.code}"

    flutter_calls = [c for c in captured_calls if c["is_flutter"]]
    react_calls = [c for c in captured_calls if c["is_react"]]
    assert len(flutter_calls) == 1, f"Flutter target should be verified once. Calls: {captured_calls}"
    assert len(react_calls) == 1, f"React target should be verified once. Calls: {captured_calls}"
    assert str(app_flutter) in flutter_calls[0]["dest"]
    assert str(web_react) in react_calls[0]["dest"]

def test_tag_restoration_point_unborn_head():
    """
    Test that tag_restoration_point returns True and skips tagging when git HEAD is unborn.
    """
    with mock.patch("subprocess.run") as mock_run:
        mock_proc = mock.MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        result = verify_downstream_baseline.tag_restoration_point()
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=None,
            timeout=verify_downstream_baseline.GIT_TIMEOUT_SECONDS,
        )

