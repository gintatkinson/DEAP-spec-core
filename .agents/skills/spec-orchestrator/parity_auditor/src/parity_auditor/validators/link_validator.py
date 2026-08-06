"""Enforces markdown link integrity across all specifications."""
import os
import re
from typing import List

from .base import IValidator
from ..core.findings import Finding
from ..core.workspace import WorkspaceRepository

# Match markdown links: [text](link) ending in .md or with an anchor .md#anchor
_LINK_RE = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
_GITHUB_BLOB_RE = re.compile(r'https://github\.com/[^\s/]+/[^\s/]+/blob/[^\s/]+/[^\s\)\]\'">]+')

class LinkValidator(IValidator):
    def validate(self, repo: WorkspaceRepository, **kwargs) -> List[Finding]:
        rules = repo.get_codebase_rules()
        backlog_dirs = rules.backlog_directories
        errors: List[Finding] = []

        directories_to_check = []
        for dir_key in ["features", "epics", "user_stories", "use_cases"]:
            rel = getattr(backlog_dirs, dir_key, None)
            if rel:
                directories_to_check.append(rel)

        workspace_dir = repo.workspace_dir

        for rel_dir in directories_to_check:
            target_dir = os.path.join(workspace_dir, rel_dir)
            if not os.path.isdir(target_dir):
                continue
            
            for filename in os.listdir(target_dir):
                if not filename.endswith(".md") or filename.startswith("."):
                    continue
                
                filepath = os.path.join(target_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Find all links
                links_to_check = []
                for match in _LINK_RE.finditer(content):
                    links_to_check.append(match.group(1))
                
                for match in _GITHUB_BLOB_RE.finditer(content):
                    if match.group(0) not in links_to_check:
                        links_to_check.append(match.group(0))

                for link_raw in links_to_check:
                    link_target = link_raw.split("#")[0]  # strip fragments
                    
                    is_blob = False
                    # Clean up GitHub blob URLs, if any
                    if "blob/" in link_target:
                        parts = link_target.split("blob/")
                        if len(parts) > 1:
                            branch_and_path = parts[1]
                            path_parts = branch_and_path.split("/", 1)
                            if len(path_parts) > 1:
                                link_target = path_parts[1]
                                is_blob = True
                    elif "tree/" in link_target:
                        parts = link_target.split("tree/")
                        if len(parts) > 1:
                            branch_and_path = parts[1]
                            path_parts = branch_and_path.split("/", 1)
                            if len(path_parts) > 1:
                                link_target = path_parts[1]
                                is_blob = True
                    
                    # If it's still a full HTTP url without blob/tree, skip
                    if link_target.startswith("http"):
                        continue
                        
                    if link_target.startswith("/"):
                        resolved_path = os.path.join(workspace_dir, link_target.lstrip("/"))
                    elif is_blob:
                        resolved_path = os.path.join(workspace_dir, link_target)
                    else:
                        # Standard markdown relative link
                        resolved_path = os.path.normpath(os.path.join(target_dir, link_target))
                    
                    if not os.path.isfile(resolved_path):
                        errors.append(Finding(
                            "markdown-broken-link-reference",
                            f"{rel_dir}/{filename}: Broken markdown link points to non-existent file '{link_raw}'.",
                            location=f"{rel_dir}/{filename}"
                        ))

        return errors
