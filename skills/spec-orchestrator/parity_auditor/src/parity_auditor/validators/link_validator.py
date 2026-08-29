"""Enforces markdown link integrity across all specifications and repository documentation."""
import os
import re
from typing import List

from .base import IValidator
from ..core.findings import Finding
from ..core.workspace import WorkspaceRepository

# Match markdown links: [text](link) ending in .md or with an anchor .md#anchor
_LINK_RE = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
_GITHUB_BLOB_RE = re.compile(r'https://github\.com/[^\s/]+/[^\s/]+/blob/[^\s/]+/[^\s\)\]\'">]+')

EXCLUDED_SCAN_DIRS = {".git", ".pytest_cache", ".dart_tool", "node_modules", "build", "diagnostics"}

class LinkValidator(IValidator):
    def validate(self, repo: WorkspaceRepository, **kwargs) -> List[Finding]:
        workspace_dir = repo.workspace_dir
        repo_name = os.path.basename(os.path.abspath(workspace_dir))
        errors: List[Finding] = []

        search_dirs = kwargs.get("search_dirs")
        if not search_dirs:
            rules = repo.get_codebase_rules()
            backlog_dirs = rules.backlog_directories
            search_dirs = [
                os.path.join(workspace_dir, "docs"),
                os.path.join(workspace_dir, "rules"),
                os.path.join(workspace_dir, "skills"),
                os.path.join(workspace_dir, ".pipeline"),
            ]
            for dir_key in ["features", "epics", "user_stories", "use_cases"]:
                rel = getattr(backlog_dirs, dir_key, None)
                if rel:
                    p = os.path.join(workspace_dir, rel)
                    if p not in search_dirs:
                        search_dirs.append(p)

        markdown_files = []
        # Add root markdown files
        try:
            for item in os.listdir(workspace_dir):
                if item.endswith(".md") and not item.startswith("."):
                    markdown_files.append(os.path.join(workspace_dir, item))
        except OSError:
            pass

        # Walk all search directories
        for root_dir in search_dirs:
            if not os.path.isdir(root_dir):
                continue
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Exclude internal / diagnostic directories
                dirnames[:] = [d for d in dirnames if d not in EXCLUDED_SCAN_DIRS]
                # Skip historical point-in-time audit snapshots
                if "docs/audits" in dirpath or "docs/decisions" in dirpath or "docs/designs" in dirpath:
                    continue
                for filename in filenames:
                    if filename.endswith(".md") and not filename.startswith("."):
                        full_p = os.path.join(dirpath, filename)
                        if full_p not in markdown_files:
                            markdown_files.append(full_p)

        for filepath in markdown_files:
            rel_path = os.path.relpath(filepath, workspace_dir)
            source_dir = os.path.dirname(filepath)

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            # Strip fenced code blocks and inline code spans before link extraction
            content_clean = re.sub(r'```[\s\S]*?```', '', content)
            content_clean = re.sub(r'~~~[\s\S]*?~~~', '', content_clean)
            content_clean = re.sub(r'`+[\s\S]*?`+', '', content_clean)

            # Find all links
            links_to_check = []
            for match in _LINK_RE.finditer(content_clean):
                links_to_check.append(match.group(1))

            for match in _GITHUB_BLOB_RE.finditer(content_clean):
                if match.group(0) not in links_to_check:
                    links_to_check.append(match.group(0))

            for link_raw in links_to_check:
                # Prohibit non-portable file:// and file:/// URI schemes
                if link_raw.startswith("file://") or link_raw.startswith("file:/"):
                    errors.append(Finding(
                        "markdown-local-file-protocol-forbidden",
                        f"{rel_path}: Local file protocol link is forbidden: '{link_raw}'. Internal references must use repository-relative paths.",
                        location=rel_path
                    ))
                    continue

                # Skip template placeholders / examples
                if any(placeholder in link_raw for placeholder in [
                    "-XX-", "XX-name", "link-to-", "URL", "target", "example.com", "file.sysml",
                    "docs/features/feat-", "docs/epics/epic-", "docs/user-stories/us-", "docs/use-cases/uc-",
                    "EPIC-001.md", "Avenger5.sysml", "schema/..."
                ]):
                    if not os.path.exists(os.path.join(workspace_dir, link_raw)):
                        continue

                link_target = link_raw.split("#")[0].strip()  # strip fragments
                if not link_target:
                    # Anchor-only link within same document
                    continue

                # Check if it's an external GitHub/GitLab blob URL for a different repository
                if ("github.com/" in link_raw or "gitlab.com/" in link_raw) and repo_name not in link_raw:
                    continue

                is_blob = False
                # Clean up GitHub blob URLs for this repository, if any
                if "blob/" in link_target and repo_name in link_target:
                    parts = link_target.split("blob/")
                    if len(parts) > 1:
                        branch_and_path = parts[1]
                        path_parts = branch_and_path.split("/", 1)
                        if len(path_parts) > 1:
                            link_target = path_parts[1]
                            is_blob = True
                elif "tree/" in link_target and repo_name in link_target:
                    parts = link_target.split("tree/")
                    if len(parts) > 1:
                        branch_and_path = parts[1]
                        path_parts = branch_and_path.split("/", 1)
                        if len(path_parts) > 1:
                            link_target = path_parts[1]
                            is_blob = True

                # Skip external URLs (http, https, mailto, etc.)
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', link_target) or link_target.startswith("mailto:"):
                    continue

                if link_target.startswith("/"):
                    resolved_path = os.path.join(workspace_dir, link_target.lstrip("/"))
                elif is_blob:
                    resolved_path = os.path.join(workspace_dir, link_target)
                else:
                    # Standard markdown relative link resolved from current file directory,
                    # or fallback to repository root relative path
                    resolved_path = os.path.normpath(os.path.join(source_dir, link_target))
                    if not os.path.exists(resolved_path):
                        repo_resolved = os.path.normpath(os.path.join(workspace_dir, link_target))
                        if os.path.exists(repo_resolved):
                            resolved_path = repo_resolved

                if not os.path.exists(resolved_path):
                    errors.append(Finding(
                        "markdown-broken-link-reference",
                        f"{rel_path}: Broken markdown link points to non-existent file '{link_raw}'.",
                        location=rel_path
                    ))

        return errors
