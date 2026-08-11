"""
Validator that enforces 1:1 mapping between schema containers/cases and spec files.

Checks that each feature and use-case markdown file declares exactly one schema
container in its YAML frontmatter ``schema_containers`` field. Multi-container
consolidation violates the architecture and is rejected.
"""

import os
import re
from typing import List

import yaml

from .base import IValidator
from ..core.findings import Finding
from ..core.workspace import WorkspaceRepository


def _extract_frontmatter(content: str):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1).replace('\x01', ''))
    except Exception:
        return None


class SchemaCardinalityValidator(IValidator):
    def validate(self, repo: WorkspaceRepository, **kwargs) -> List[str]:
        is_sysml = kwargs.get("is_sysml", False)
        rules = repo.get_codebase_rules()
        backlog_dirs = rules.backlog_directories
        
        schemas_dir_rel = getattr(backlog_dirs, "schemas", None)
        schemas_dir = os.path.join(repo.workspace_dir, schemas_dir_rel) if schemas_dir_rel else os.path.join(repo.workspace_dir, "schemas")
        features_dir_rel = getattr(backlog_dirs, "features", None)
        features_dir = os.path.join(repo.workspace_dir, features_dir_rel) if features_dir_rel else None

        errors = []

        if is_sysml:
            if not os.path.exists(schemas_dir):
                sysml_files = []
            else:
                schema_files = [f for f in os.listdir(schemas_dir) if not f.startswith('.')]
                sysml_files = [f for f in schema_files if f.endswith('.sysml')]

            if not sysml_files:
                errors.append(Finding(
                    "sysml-model-not-readable",
                    f"SysML mode was requested but no .sysml file was found in {schemas_dir}.",
                    location="schemas"
                ))
            else:
                sysml_nodes = set()
                for f in sysml_files:
                    try:
                        with open(os.path.join(schemas_dir, f), 'r', encoding='utf-8') as file:
                            content = file.read()
                            for match in re.finditer(r'(?:part|attribute|port)\s+def\s+(\w+)', content):
                                sysml_nodes.add(match.group(1))
                    except Exception as exc:
                        errors.append(Finding(
                            "sysml-model-not-readable",
                            f"Failed to read SysML model file '{f}': {exc}",
                            location="schemas"
                        ))

                feature_texts = []
                if features_dir and os.path.exists(features_dir):
                    for fn in os.listdir(features_dir):
                        if fn.endswith('.md'):
                            try:
                                with open(os.path.join(features_dir, fn), 'r', encoding='utf-8') as file:
                                    feature_texts.append(file.read())
                            except Exception as exc:
                                errors.append(Finding(
                                    "sysml-feature-not-readable",
                                    f"Failed to read Feature specification '{fn}': {exc}",
                                    location="features"
                                ))

                for node in sysml_nodes:
                    found = False
                    for ft in feature_texts:
                        if re.search(rf"\b{re.escape(node)}\b", ft):
                            found = True
                            break
                    if not found:
                        errors.append(Finding(
                            "sysml-extraction-missing",
                            f"SysML node '{node}' is not extracted into any feature specification.",
                            location="features"
                        ))

        if not os.path.exists(schemas_dir):
            return errors
        schema_files = [f for f in os.listdir(schemas_dir) if not f.startswith('.')]
        if not schema_files:
            return errors
        use_cases_dir_rel = getattr(backlog_dirs, "use_cases", None)
        use_cases_dir = (
            os.path.join(repo.workspace_dir, use_cases_dir_rel)
            if use_cases_dir_rel
            else None
        )

        for dir_label, target_dir, file_type in [
            ("features", features_dir, "Feature"),
            ("use-cases", use_cases_dir, "Use Case"),
        ]:
            if not target_dir or not os.path.exists(target_dir):
                continue
            for filename in sorted(os.listdir(target_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(target_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                fm = _extract_frontmatter(content)
                if fm is None:
                    continue

                containers = fm.get("schema_containers", None)
                if containers is None:
                    errors.append(Finding(
                        "schema-container-declaration-missing",
                        f"{file_type} '{filename}': schema_containers is missing from frontmatter. "
                        f"Every {file_type.lower()} must declare exactly one schema container "
                        f"(e.g. path: 'module/container', node_type: container).",
                        location=dir_label,
                    ))
                    continue

                if not isinstance(containers, list):
                    errors.append(Finding(
                        "schema-container-field-must-be-a-list",
                        f"{file_type} '{filename}': schema_containers must be a list, "
                        f"got {type(containers).__name__}",
                        location=dir_label,
                    ))
                    continue

                n = len(containers)
                if n == 0:
                    errors.append(Finding(
                        "schema-container-declaration-empty",
                        f"{file_type} '{filename}': schema_containers is empty. "
                        f"Every {file_type.lower()} must declare at least one schema container "
                        f"(e.g. path: 'module/container', node_type: container).",
                        location=dir_label,
                    ))
                elif n > 1:
                    # Both worker skills state that the linter rejects
                    # len(schema_containers) != 1, and the 1:1 container-to-item mandate
                    # is what keeps a Feature independently testable. Only the != 1 cases
                    # below one were checked; more-than-one was documented and enforced
                    # nowhere, so consolidated multi-container items passed the gate.
                    errors.append(Finding(
                        "schema-container-consolidation-forbidden",
                        f"{file_type} '{filename}': schema_containers declares {n} containers. "
                        f"Every {file_type.lower()} must declare exactly one. Split the "
                        f"consolidated containers into separate files, one per container.",
                        location=dir_label,
                    ))

        return errors
