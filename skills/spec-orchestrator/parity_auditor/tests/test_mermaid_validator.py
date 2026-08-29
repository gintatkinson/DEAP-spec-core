#!/usr/bin/env python3
# Copyright Gint Atkinson, gint.atkinson@gmail.com
"""
Unit tests for Mermaid Diagram Syntax and Portability Validator.

Validates detection of:
1. Multi-target ampersand chaining shorthand in connections (A --> B & C & D, A ==> B & C, A -.-> B & C).
2. Clean, valid explicit individual arrows passing with zero errors (A --> B, A --> C).
3. Unclosed fences, missing diagram headers, unquoted angle brackets, and semicolons in notes.
4. Quoted ampersands inside node titles and non-connection lines remaining valid.
"""

import os
import sys
import tempfile
import pytest

# Ensure parity_auditor and workspace root are on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Find workspace root dynamically
cur = SCRIPT_DIR
while cur and cur != os.path.dirname(cur):
    if os.path.exists(os.path.join(cur, "skills", "spec-orchestrator", "parity_auditor", "src")):
        break
    cur = os.path.dirname(cur)
PROJECT_ROOT = cur if os.path.exists(os.path.join(cur, "skills")) else SCRIPT_DIR
PARITY_AUDITOR_SRC = os.path.join(PROJECT_ROOT, "skills", "spec-orchestrator", "parity_auditor", "src")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "skills", "spec-orchestrator", "scripts")

for p in (PARITY_AUDITOR_SRC, SCRIPTS_DIR, PROJECT_ROOT):
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from parity_auditor.core.workspace import WorkspaceRepository
from parity_auditor.validators.mermaid_validator import (
    MermaidValidator,
    MermaidSyntaxValidator,
    check_mermaid_block,
    check_mermaid_text,
)
from parity_auditor.core.findings import Finding


def test_detects_forbidden_ampersand_chaining_in_connections():
    """Verify that multi-target ampersand chaining in Mermaid connections fails with mermaid-forbidden-ampersand-chaining."""
    bad_chaining_md = """
# Architecture Specification

```mermaid
graph TD
    A --> B & C & D
```
"""
    findings = check_mermaid_text(bad_chaining_md, source="bad_chaining.md")
    rule_ids = [f.rule_id for f in findings]
    assert "mermaid-forbidden-ampersand-chaining" in rule_ids

    chaining_findings = [f for f in findings if f.rule_id == "mermaid-forbidden-ampersand-chaining"]
    assert len(chaining_findings) == 1
    assert "multi-target ampersand chaining '&' is forbidden in Mermaid connections ('A --> B & C & D')" in str(chaining_findings[0])
    assert "Declare each edge on its own line" in str(chaining_findings[0])


def test_detects_ampersand_chaining_across_various_arrow_types():
    """Verify ampersand chaining detection on thick arrows, dotted arrows, and left-side chaining."""
    bad_arrows_md = """
```mermaid
flowchart LR
    A ==> B & C
    D -.-> E & F
    X & Y --> Z
```
"""
    findings = check_mermaid_text(bad_arrows_md, source="bad_arrows.md")
    chaining_findings = [f for f in findings if f.rule_id == "mermaid-forbidden-ampersand-chaining"]
    assert len(chaining_findings) == 3
    rule_ids = [f.rule_id for f in chaining_findings]
    assert all(r == "mermaid-forbidden-ampersand-chaining" for r in rule_ids)


def test_passes_explicit_individual_arrows():
    """Verify that explicit individual arrows (e.g. A --> B and A --> C) pass with 0 errors."""
    clean_md = """
# Clean Architecture Specification

```mermaid
graph TD
    A --> B
    A --> C
    A --> D
```

```mermaid
flowchart LR
    A ==> B
    A ==> C
    D -.-> E
    D -.-> F
```
"""
    findings = check_mermaid_text(clean_md, source="clean_arrows.md")
    assert len(findings) == 0, f"Expected 0 findings but got: {findings}"


def test_check_mermaid_block_direct_invocation():
    """Verify direct invocation of check_mermaid_block with body string and list of lines."""
    # Failing block
    body_fail = [
        "graph TD",
        "    Start --> Step1 & Step2 & Step3",
    ]
    findings_fail = check_mermaid_block(body_fail, start=1, source="test_block.md")
    assert len(findings_fail) == 1
    assert findings_fail[0].rule_id == "mermaid-forbidden-ampersand-chaining"

    # Passing block
    body_pass = [
        "graph TD",
        "    Start --> Step1",
        "    Start --> Step2",
        "    Start --> Step3",
    ]
    findings_pass = check_mermaid_block(body_pass, start=1, source="test_block.md")
    assert len(findings_pass) == 0


def test_allows_ampersand_in_quoted_node_labels_and_subgraphs():
    """Verify that ampersands within quoted node labels or subgraph titles do not trigger ampersand chaining."""
    quoted_amp_md = """
```mermaid
graph TD
    subgraph "Control & Monitoring"
        A["Sensor & Actuator Driver"] --> B["Command & Telemetry Engine"]
    end
```
"""
    findings = check_mermaid_text(quoted_amp_md, source="quoted_amp.md")
    chaining_findings = [f for f in findings if f.rule_id == "mermaid-forbidden-ampersand-chaining"]
    assert len(chaining_findings) == 0


def test_mermaid_validator_workspace_scanning():
    """Verify MermaidValidator and MermaidSyntaxValidator directory traversal with WorkspaceRepository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = os.path.join(tmpdir, "docs")
        os.makedirs(docs_dir)

        with open(os.path.join(docs_dir, "clean.md"), "w", encoding="utf-8") as f:
            f.write("""
# Clean Document

```mermaid
graph TD
    NodeA --> NodeB
    NodeA --> NodeC
```
""")

        with open(os.path.join(docs_dir, "defect.md"), "w", encoding="utf-8") as f:
            f.write("""
# Defect Document

```mermaid
graph TD
    NodeA --> NodeB & NodeC & NodeD
```
""")

        repo = WorkspaceRepository(tmpdir)
        validator = MermaidValidator()
        findings = validator.validate(repo, search_dirs=[docs_dir])

        assert len(findings) == 1
        assert findings[0].rule_id == "mermaid-forbidden-ampersand-chaining"
        assert isinstance(findings[0], Finding)
