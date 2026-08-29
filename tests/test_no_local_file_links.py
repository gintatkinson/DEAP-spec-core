"""Unit tests verifying that no local file:/// URI links exist across repository markdown files.

Enforces:
1. No markdown file contains broken 'file:///' local URI schemes.
2. LinkValidator detects forbidden 'file:///' and 'file://' protocols with finding rule_id 'markdown-local-file-protocol-forbidden'.
3. LinkValidator scans expanded documentation directories (docs/management, docs/safety, docs/conops) and root README.md.
4. Workspace link validation produces zero broken link or forbidden protocol findings.
"""

import os
import re
import sys
from pathlib import Path
import pytest

# Ensure parity_auditor is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
PARITY_AUDITOR_SRC = str(REPO_ROOT / "skills" / "spec-orchestrator" / "parity_auditor" / "src")

for p in (PARITY_AUDITOR_SRC, str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from parity_auditor.core.workspace import WorkspaceRepository
from parity_auditor.validators.link_validator import LinkValidator, _LINK_RE

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".dart_tool",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    ".mypy_cache",
}


def get_all_markdown_files():
    """Discover all .md files in the repository excluding build and VCS directories."""
    md_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".git")]
        for file in files:
            if file.endswith(".md"):
                md_files.append(Path(root) / file)
    return sorted(md_files)


def test_no_file_protocol_links_in_markdown_files():
    """Assert that zero markdown links in repository documents use file:/// or file:// schemes."""
    md_files = get_all_markdown_files()
    assert len(md_files) > 0, "Expected to find markdown files in repository"

    violations = []
    link_scheme_pattern = re.compile(r'!?\[(?:[^\[\]]|\[[^\]]*\])*\]\((file://[^\)\s]*|file:/[^\)\s]*)\)')

    for md_path in md_files:
        try:
            content = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Strip code blocks to focus on genuine markdown links
        content_clean = re.sub(r'```[\s\S]*?```', '', content)
        content_clean = re.sub(r'~~~[\s\S]*?~~~', '', content_clean)

        rel_path = md_path.relative_to(REPO_ROOT)
        matches = link_scheme_pattern.findall(content_clean)
        for match in matches:
            violations.append(f"{rel_path}: {match}")

    assert not violations, (
        f"Found {len(violations)} forbidden file:// or file:/// markdown links:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_absolute_user_jail_paths_in_markdown():
    """Assert that no markdown links reference local workstation user paths."""
    md_files = get_all_markdown_files()
    violations = []
    user_path_pattern = re.compile(r'(/Users/[a-zA-Z0-9_\-\.]+/jail/[^\)\s\'"]+)')

    for md_path in md_files:
        # Exclude historical defect audit writeups from literal user path check
        if "docs/safety/defects" in str(md_path) or ".pipeline/diagnostics" in str(md_path):
            continue
        try:
            content = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        content_clean = re.sub(r'```[\s\S]*?```', '', content)
        content_clean = re.sub(r'~~~[\s\S]*?~~~', '', content_clean)

        rel_path = md_path.relative_to(REPO_ROOT)
        matches = user_path_pattern.findall(content_clean)
        for match in matches:
            violations.append(f"{rel_path}: {match}")

    assert not violations, (
        f"Found {len(violations)} workstation user paths in markdown files:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_link_validator_detects_forbidden_file_protocol(tmp_path):
    """Verify that LinkValidator emits markdown-local-file-protocol-forbidden for file:/// URIs."""
    test_repo_dir = tmp_path / "test_repo"
    test_repo_dir.mkdir()
    docs_dir = test_repo_dir / "docs" / "features"
    docs_dir.mkdir(parents=True)

    bad_file = docs_dir / "feat-test.md"
    bad_file.write_text(
        "# Feature Test\n\n"
        "See [Spec](file:///home/dev/test.md) for details.\n"
        "And [Another](file://some/path.md).\n",
        encoding="utf-8"
    )

    repo = WorkspaceRepository(workspace_dir=str(test_repo_dir))
    validator = LinkValidator()
    findings = validator.validate(repo)

    forbidden_findings = [f for f in findings if f.rule_id == "markdown-local-file-protocol-forbidden"]
    assert len(forbidden_findings) == 2
    assert any("file:///home/dev/test.md" in str(f) for f in forbidden_findings)
    assert any("file://some/path.md" in str(f) for f in forbidden_findings)


def test_link_validator_detects_broken_link(tmp_path):
    """Verify that LinkValidator emits markdown-broken-link-reference for non-existent target."""
    test_repo_dir = tmp_path / "test_repo"
    test_repo_dir.mkdir()
    docs_dir = test_repo_dir / "docs" / "features"
    docs_dir.mkdir(parents=True)

    bad_file = docs_dir / "feat-broken.md"
    bad_file.write_text(
        "# Feature Test\n\n"
        "See [NonExistent](non_existent_file.md) for details.\n",
        encoding="utf-8"
    )

    repo = WorkspaceRepository(workspace_dir=str(test_repo_dir))
    validator = LinkValidator()
    findings = validator.validate(repo)

    broken_findings = [f for f in findings if f.rule_id == "markdown-broken-link-reference"]
    assert len(broken_findings) == 1
    assert "non_existent_file.md" in str(broken_findings[0])


def test_link_validator_passes_valid_relative_links(tmp_path):
    """Verify that LinkValidator passes valid repository-relative links."""
    test_repo_dir = tmp_path / "test_repo"
    test_repo_dir.mkdir()
    docs_dir = test_repo_dir / "docs" / "features"
    docs_dir.mkdir(parents=True)
    schema_dir = test_repo_dir / "schema"
    schema_dir.mkdir(parents=True)

    (schema_dir / "model.sysml").write_text("package Avenger5 {}", encoding="utf-8")
    (docs_dir / "schema").mkdir(parents=True, exist_ok=True)
    (docs_dir / "schema" / "model.sysml").write_text("package Avenger5 {}", encoding="utf-8")
    good_file = docs_dir / "feat-good.md"
    good_file.write_text(
        "# Feature Test\n\n"
        "See [Schema](../../schema/model.sysml) or [Root Spec](schema/model.sysml).\n"
        "External link: [GitLab](https://gitlab.com/example/repo).\n",
        encoding="utf-8"
    )

    repo = WorkspaceRepository(workspace_dir=str(test_repo_dir))
    validator = LinkValidator()
    findings = validator.validate(repo)

    assert len(findings) == 0


def test_workspace_repository_link_integrity():
    """Assert that LinkValidator on actual workspace finds zero broken links or forbidden protocols."""
    repo = WorkspaceRepository(workspace_dir=str(REPO_ROOT))
    validator = LinkValidator()
    findings = validator.validate(repo)

    critical_findings = [
        f for f in findings
        if f.rule_id in ("markdown-local-file-protocol-forbidden", "markdown-broken-link-reference")
    ]
    assert not critical_findings, (
        f"Workspace has {len(critical_findings)} link validation findings:\n"
        + "\n".join(f"  - [{f.rule_id}] {str(f)}" for f in critical_findings)
    )
