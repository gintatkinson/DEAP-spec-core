import os
import re
from typing import List, Dict, Any
import yaml

from .base import IValidator
from ..core.findings import Finding
from ..core.workspace import WorkspaceRepository


def _extract_frontmatter(content: str) -> Dict[str, Any]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1).replace('\x01', ''))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class SpecValidator(IValidator):
    def validate_schema_container_paths(self, repo: WorkspaceRepository, **kwargs) -> List[str]:
        rules = repo.get_codebase_rules()
        backlog_dirs = rules.backlog_directories

        features_dir = kwargs.get("features_dir")
        if not features_dir:
            features_dir_rel = getattr(backlog_dirs, "features", None) if backlog_dirs else None
            if not features_dir_rel:
                return []
            features_dir = os.path.join(repo.workspace_dir, features_dir_rel)

        if not os.path.exists(features_dir):
            return []

        errors = []
        for filename in sorted(os.listdir(features_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(features_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            fm = _extract_frontmatter(content)
            containers = fm.get("schema_containers")
            if not containers or not isinstance(containers, list):
                continue

            for container in containers:
                path = None
                if isinstance(container, dict):
                    path = container.get("path")
                elif isinstance(container, str):
                    path = container

                if path and ":" not in path:
                    errors.append(Finding(
                        "schema-container-path-must-be-fully-qualified",
                        f"Feature '{filename}': schema container path '{path}' is unqualified (missing module prefix colon ':'). "
                        f"Expected format e.g. 'ietf-geo-location:geo-location/reference-frame'.",
                        location=os.path.basename(os.path.normpath(features_dir)),
                    ))

        return errors

    def validate(self, repo: WorkspaceRepository, **kwargs) -> List[str]:
        return self.validate_schema_container_paths(repo, **kwargs)
