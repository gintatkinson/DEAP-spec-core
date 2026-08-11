import os
import shutil
import subprocess
import sys


INFRA_DIRS = ["/skills", "/rules", "/.pipeline", "/.agents", "/scripts"]
WHITELIST_ENTRIES = [f"!{d}{s}" for d in INFRA_DIRS for s in ("/", "/**")]


def _make_repo(tmp_path, init_git=True):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".*\n")
    if init_git:
        subprocess.run(["git", "init"], capture_output=True, cwd=str(tmp_path))
    else:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "hooks").mkdir()

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    src = os.path.join(os.path.dirname(__file__), "..", "scripts", "setup_git_hooks.py")
    shutil.copy2(src, scripts_dir / "setup_git_hooks.py")

    for d in [".pipeline", ".agents", "skills", "rules", "scripts"]:
        (tmp_path / d).mkdir(exist_ok=True)
        (tmp_path / d / ".gitkeep").write_text("")

    return scripts_dir / "setup_git_hooks.py"


def _run_script(script_path, cwd):
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, cwd=str(cwd)
    )


def test_whitelist_skipped_when_not_git_repo(tmp_path):
    script = _make_repo(tmp_path, init_git=False)
    result = _run_script(script, tmp_path)
    assert result.returncode == 0, result.stderr

    content = (tmp_path / ".gitignore").read_text()
    for entry in WHITELIST_ENTRIES:
        assert entry not in content, f"Whitelist entry should NOT be present without .git/HEAD: {entry}"


def test_whitelist_appended_when_git_repo(tmp_path):
    script = _make_repo(tmp_path, init_git=True)
    result = _run_script(script, tmp_path)
    assert result.returncode == 0, result.stderr

    content = (tmp_path / ".gitignore").read_text()
    for entry in WHITELIST_ENTRIES:
        assert entry in content, f"Missing whitelist entry: {entry}"


def test_pipeline_dirs_staged_after_setup(tmp_path):
    script = _make_repo(tmp_path, init_git=True)
    result = _run_script(script, tmp_path)
    assert result.returncode == 0, result.stderr

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=str(tmp_path)
    )
    staged_files = staged.stdout.strip().split("\n") if staged.stdout.strip() else []
    for d in [".pipeline", ".agents", "skills", "rules", "scripts"]:
        found = any(f.startswith(d + "/") or f == d for f in staged_files)
        assert found, f"Directory not staged: {d}"


def test_hooks_configured_by_setup(tmp_path):
    script = _make_repo(tmp_path, init_git=False)
    hooks_dir = tmp_path / ".git" / "hooks"

    pre_commit = hooks_dir / "pre-commit"
    pre_push = hooks_dir / "pre-push"
    for hook in [pre_commit, pre_push]:
        hook.write_text("#!/bin/sh\necho 'heavy build'\n")
        os.chmod(str(hook), 0o755)

    result = _run_script(script, tmp_path)
    assert result.returncode == 0, result.stderr

    assert pre_commit.exists(), "pre-commit hook was not installed"
    assert "verify_subagent_output.py" in pre_commit.read_text()
    assert not pre_push.exists(), "pre-push hook was not removed"


def test_exits_nonzero_on_hook_removal_failure(tmp_path):
    script = _make_repo(tmp_path, init_git=False)
    hooks_dir = tmp_path / ".git" / "hooks"

    pre_push = hooks_dir / "pre-push"
    pre_push.write_text("#!/bin/sh\necho 'heavy build'\n")
    os.chmod(str(pre_push), 0o755)

    hooks_dir.chmod(0o500)

    result = _run_script(script, tmp_path)
    assert result.returncode != 0, (
        f"Expected non-zero exit when hook removal fails, got {result.returncode}"
    )

    hooks_dir.chmod(0o700)


def test_pipeline_dirs_staged_even_if_already_whitelisted(tmp_path):
    script = _make_repo(tmp_path, init_git=True)
    # First run to append whitelist entries
    result = _run_script(script, tmp_path)
    assert result.returncode == 0

    # Unstage files to verify staging on the second run
    subprocess.run(["git", "reset"], capture_output=True, cwd=str(tmp_path))

    # Second run where patterns will be empty
    result2 = _run_script(script, tmp_path)
    assert result2.returncode == 0, result2.stderr
    assert "already present in .gitignore" in result2.stdout

    # Verify files are still staged
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=str(tmp_path)
    )
    staged_files = staged.stdout.strip().split("\n") if staged.stdout.strip() else []
    for d in [".pipeline", ".agents", "skills", "rules", "scripts"]:
        found = any(f.startswith(d + "/") or f == d for f in staged_files)
        assert found, f"Directory not staged: {d}"


def test_whitelist_creates_gitignore_if_missing(tmp_path):
    script = _make_repo(tmp_path, init_git=True)
    gitignore = tmp_path / ".gitignore"
    if gitignore.exists():
        gitignore.unlink()

    result = _run_script(script, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Created missing .gitignore file" in result.stdout
    assert gitignore.exists(), ".gitignore file was not created"

    content = gitignore.read_text(encoding="utf-8")
    for entry in WHITELIST_ENTRIES:
        assert entry in content, f"Missing whitelist entry: {entry}"
