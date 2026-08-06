import os
import sys
import tempfile

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import sanitize_source_references, write_markdown_file, get_upstream_repository, rewrite_header_repository_urls, get_current_branch

# Issue #308: this module used to hardcode "/Users/perkunas/jail/digital-pipeline-repo"
# as the workspace and "blob/main" in its assertions, while sanitize_source_references
# derives the branch live from the workspace. That produced three different outcomes —
# passing on main locally by coincidence, failing on any feature branch, and raising
# FileNotFoundError on CI where the path does not exist — so the suite could not be
# green on a feature branch, which is exactly where the process requires it.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
UPSTREAM = "gintatkinson/digital-pipeline-repo"


def _expected_base():
    """The URL prefix the code under test will build, resolved the same way it does."""
    branch = get_current_branch(REPO_ROOT)
    if not branch or branch == "HEAD":
        branch = "main"
    return "https://github.com/{}/blob/{}".format(UPSTREAM, branch)


def test_sanitize_source_references_converts_workstation_file_uris():
    script = "skills/spec-orchestrator/scripts/reconcile_backlog.py"
    content = (
        "# Feature 01: Backlog Reconciliation\n\n"
        "## 1. Context and References\n"
        "- **File**: file://{root}/{script}#L271-L317\n\n"
        "## 6. Source References\n"
        "- **Primary Source**: [reconcile_backlog.py](file://{root}/{script}:271-317)\n"
        # Deliberately a foreign path, not the workspace: proves non-workspace file://
        # URIs are sanitised too.
        "- **Auxiliary Source**: file:///Users/developer/digital-pipeline-repo/docs/features/feat-01.md\n"
    ).format(root=REPO_ROOT, script=script)

    rules = {
        "tracker_rules": {},
        "meta": {"upstream_repository": UPSTREAM}
    }

    sanitized = sanitize_source_references(content, workspace_dir=REPO_ROOT, rules=rules)
    base = _expected_base()

    # Assert local workstation URIs are completely sanitized
    assert "file:///Users/" not in sanitized
    assert "file:///" not in sanitized

    # Assert clean GitHub URLs are generated, on whatever branch is checked out
    assert "{}/{}#L271-L317".format(base, script) in sanitized
    assert "{}/{}:271-317".format(base, script) in sanitized
    assert "{}/docs/features/feat-01.md".format(base) in sanitized

def test_write_markdown_file_sanitizes_local_file_uris():
    script = "skills/spec-orchestrator/scripts/reconcile_backlog.py"
    content = (
        "# Feature 02: Audit Logging\n\n"
        "## 6. Source References\n"
        "- **Ref**: file://{root}/{script}\n"
    ).format(root=REPO_ROOT, script=script)

    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = os.path.join(tmpdir, "feat-02.md")

        rules = {
            "tracker_rules": {},
            "meta": {"upstream_repository": UPSTREAM}
        }

        written_content = write_markdown_file(spec_path, content, workspace_dir=REPO_ROOT, rules=rules)
        expected = "{}/{}".format(_expected_base(), script)

        assert "file:///Users/" not in written_content
        assert expected in written_content

        with open(spec_path, "r", encoding="utf-8") as f:
            saved_content = f.read()

        assert "file:///Users/" not in saved_content
        assert expected in saved_content

def test_get_upstream_repository_prioritizes_git_remote_over_rules_meta(monkeypatch):
    rules = {
        "meta": {"upstream_repository": "gintatkinson/digital-pipeline-repo"}
    }
    monkeypatch.delenv("UPSTREAM_REPOSITORY", raising=False)
    monkeypatch.delenv("GIT_REMOTE_ORIGIN", raising=False)
    
    # When git remote auto-detection returns a downstream repo e.g. gintatkinson/3dgs-026
    monkeypatch.setattr("reconcile_backlog.get_git_remote_repo", lambda cwd: "gintatkinson/3dgs-026")

    repo = get_upstream_repository(rules, "/Users/perkunas/jail/3dgs-026")
    assert repo == "gintatkinson/3dgs-026"

def test_rewrite_header_repository_urls_rewrites_legacy_urls_to_active_repo():
    content = (
        "# Feature 03: Header Links\n\n"
        "- **Parent Epic**: [Epic 01](https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/epics/epic-01.md)\n"
        "- **Legacy Spec Link**: https://github.com/legacy-org/old-pipeline-repo/blob/master/docs/features/feat-01.md\n"
    )

    active_repo = "gintatkinson/3dgs-026"
    rewritten = rewrite_header_repository_urls(content, active_repo)

    assert "https://github.com/gintatkinson/digital-pipeline-repo/blob/" not in rewritten
    assert "https://github.com/legacy-org/old-pipeline-repo/blob/" not in rewritten
    assert "https://github.com/gintatkinson/3dgs-026/blob/main/docs/epics/epic-01.md" in rewritten
    assert "https://github.com/gintatkinson/3dgs-026/blob/master/docs/features/feat-01.md" in rewritten

