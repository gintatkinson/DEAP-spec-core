"""
Unit tests for DocMetadataValidator.

Tests:
1. Positive validation of valid ISO dates (YYYY-MM-DD), semver versions (v?X.Y[.Z]), and required fields.
2. Negative validation of invalid dates (e.g. "August 2026", "2026/08/31", "2026-02-30").
3. Negative validation of missing fields (missing Title, missing Version, missing Date).
4. Negative validation of invalid version strings (e.g. "draft", "1", "alpha").
5. Graceful skipping of READMEs, empty stubs, and documents marked optional.
"""

import os
import sys
import tempfile
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

parity_src = os.path.join(repo_root, "skills", "spec-orchestrator", "parity_auditor", "src")
if parity_src not in sys.path:
    sys.path.insert(0, parity_src)

from parity_auditor.core.workspace import WorkspaceRepository
from parity_auditor.validators.doc_metadata_validator import (
    DocMetadataValidator,
    _is_iso_date,
    _is_semver,
    _has_concatenated_title_metadata,
)


class TestDocMetadataValidator(unittest.TestCase):
    def setUp(self):
        self.validator = DocMetadataValidator()

    def test_helper_is_iso_date(self):
        """Verify ISO 8601 date validation helper."""
        self.assertTrue(_is_iso_date("2026-08-31"))
        self.assertTrue(_is_iso_date("2025-01-01"))
        self.assertTrue(_is_iso_date("2024-02-29"))  # leap year

        self.assertFalse(_is_iso_date("August 2026"))
        self.assertFalse(_is_iso_date("2026/08/31"))
        self.assertFalse(_is_iso_date("31-08-2026"))
        self.assertFalse(_is_iso_date("2026-02-30"))  # invalid day
        self.assertFalse(_is_iso_date("2026-13-01"))  # invalid month
        self.assertFalse(_is_iso_date(""))
        self.assertFalse(_is_iso_date(None))

    def test_helper_is_semver(self):
        """Verify semantic versioning validation helper."""
        self.assertTrue(_is_semver("1.0"))
        self.assertTrue(_is_semver("1.0.0"))
        self.assertTrue(_is_semver("v1.0"))
        self.assertTrue(_is_semver("v1.0.0"))
        self.assertTrue(_is_semver("0.1"))
        self.assertTrue(_is_semver("v0.2.1"))
        self.assertTrue(_is_semver("1.2.3-alpha.1"))
        self.assertTrue(_is_semver("v2.0.0+20260831"))

        self.assertFalse(_is_semver("draft"))
        self.assertFalse(_is_semver("1"))
        self.assertFalse(_is_semver("v1"))
        self.assertFalse(_is_semver("August 2026"))
        self.assertFalse(_is_semver("Version 1.0"))
        self.assertFalse(_is_semver(""))
        self.assertFalse(_is_semver(None))

    def test_valid_vertical_table_passes(self):
        """Verify valid vertical frontmatter metadata table passes without findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Metadata | Value |
| :--- | :--- |
| **Title** | Autonomous UAS Infrastructure Safety Concept of Operations |
| **Version** | 1.0.0 |
| **Date** | 2026-08-31 |
| **Status** | APPROVED |

## 1. Executive Summary
Operational scope description.
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(errors, [])

    def test_valid_release_date_and_v_prefix_passes(self):
        """Verify valid metadata using 'Release Date' and version with 'v' prefix passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_safety = os.path.join(tmpdir, "docs", "safety")
            os.makedirs(docs_safety, exist_ok=True)

            content = """# STPA Matrix Specification

| Field | Value |
| --- | --- |
| Title | Safety Integrity & SORA Assessment Matrix |
| Version | v2.1.0 |
| Release Date | 2026-09-01 |

## 1. Losses and Hazards
"""
            with open(os.path.join(docs_safety, "STPA_MATRIX.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(errors, [])

    def test_valid_horizontal_columnar_table_passes(self):
        """Verify valid horizontal columnar frontmatter table passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_arch = os.path.join(tmpdir, "docs", "architecture")
            os.makedirs(docs_arch, exist_ok=True)

            content = """# Architectural Blueprint

| Title | Version | Date | Status |
| :--- | :--- | :--- | :--- |
| Run-Time Assurance Monitor Architecture | 0.2.0 | 2026-08-20 | Approved |

## System Overview
"""
            with open(os.path.join(docs_arch, "RTA_ARCH.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(errors, [])

    def test_missing_all_metadata_fields(self):
        """Verify document missing metadata table emits doc-metadata-missing-field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Plain Document Without Metadata Table

This document does not contain a frontmatter table.
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-missing-field")
            self.assertIn("Title", str(errors[0]))
            self.assertIn("Version", str(errors[0]))
            self.assertIn("Date", str(errors[0]))

    def test_missing_single_field_version(self):
        """Verify table missing Version field emits doc-metadata-missing-field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Field | Value |
| --- | --- |
| Title | UAS CONOPS |
| Date | 2026-08-31 |
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-missing-field")
            self.assertIn("Version", str(errors[0]))

    def test_missing_single_field_date(self):
        """Verify table missing Date field emits doc-metadata-missing-field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Field | Value |
| --- | --- |
| Title | UAS CONOPS |
| Version | 1.0.0 |
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-missing-field")
            self.assertIn("Date", str(errors[0]))

    def test_invalid_date_format_month_name(self):
        """Verify invalid date format like 'August 2026' emits doc-metadata-invalid-date-format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Field | Value |
| --- | --- |
| Title | UAS CONOPS |
| Version | 1.0.0 |
| Date | August 2026 |
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-invalid-date-format")
            self.assertIn("August 2026", str(errors[0]))

    def test_invalid_date_format_slash(self):
        """Verify invalid date format with slashes emits doc-metadata-invalid-date-format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Field | Value |
| --- | --- |
| Title | UAS CONOPS |
| Version | 1.0.0 |
| Release Date | 2026/08/31 |
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-invalid-date-format")
            self.assertIn("2026/08/31", str(errors[0]))

    def test_invalid_version_format(self):
        """Verify invalid version strings emit doc-metadata-invalid-version-format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Concept of Operations

| Field | Value |
| --- | --- |
| Title | UAS CONOPS |
| Version | draft |
| Date | 2026-08-31 |
"""
            with open(os.path.join(docs_conops, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-invalid-version-format")
            self.assertIn("draft", str(errors[0]))

    def test_skips_readme_and_stubs_and_optional_documents(self):
        """Verify README.md files, empty stubs, and files marked optional are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            docs_safety = os.path.join(tmpdir, "docs", "safety")
            os.makedirs(docs_conops, exist_ok=True)
            os.makedirs(docs_safety, exist_ok=True)

            # README.md without metadata table
            with open(os.path.join(docs_conops, "README.md"), "w", encoding="utf-8") as f:
                f.write("# CONOPS Directory\nLanding zone placeholder.\n")

            # Empty stub file
            with open(os.path.join(docs_safety, "stub.md"), "w", encoding="utf-8") as f:
                f.write("")

            # Optional document with comment
            with open(os.path.join(docs_conops, "draft_notes.md"), "w", encoding="utf-8") as f:
                f.write("<!-- optional -->\n# Draft Notes\nInformal scratchpad.\n")

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(errors, [])

    def test_helper_has_concatenated_title_metadata(self):
        """Verify concatenated title metadata helper detects versions, dates, and doc IDs."""
        self.assertFalse(_has_concatenated_title_metadata("Mission Intent — AVENGER 5 Autonomous UAS"))
        self.assertFalse(_has_concatenated_title_metadata("Autonomous UAS Infrastructure Safety Concept of Operations"))
        self.assertFalse(_has_concatenated_title_metadata("STPA Matrix Specification"))

        self.assertTrue(_has_concatenated_title_metadata("Mission Intent (DOC-MI-A5-001 v3.0.0 2026-08-31)"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent v1.0.0"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent v2.1"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent 1.0.0"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent (version: 2)"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent 2026-08-31"))
        self.assertTrue(_has_concatenated_title_metadata("Mission Intent (DOC-MI-A5-001)"))

    def test_clean_canonical_title_passes(self):
        """Verify clean canonical document title passes without finding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Mission Intent

| Metadata | Value |
| :--- | :--- |
| **Title** | Mission Intent — AVENGER 5 Autonomous UAS |
| **Version** | 1.0.0 |
| **Date** | 2026-08-31 |
| **Status** | APPROVED |

## 1. Executive Summary
Operational scope description.
"""
            with open(os.path.join(docs_conops, "MISSION_INTENT.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(errors, [])

    def test_concatenated_title_fails(self):
        """Verify document title containing concatenated metadata attributes emits doc-metadata-concatenated-title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_conops = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_conops, exist_ok=True)

            content = """# Mission Intent

| Metadata | Value |
| :--- | :--- |
| **Title** | Mission Intent (DOC-MI-A5-001 v3.0.0 2026-08-31) |
| **Version** | 3.0.0 |
| **Date** | 2026-08-31 |
| **Status** | DRAFT |

## 1. Executive Summary
Operational scope description.
"""
            with open(os.path.join(docs_conops, "MISSION_INTENT.md"), "w", encoding="utf-8") as f:
                f.write(content)

            repo = WorkspaceRepository(workspace_dir=tmpdir)
            errors = self.validator.validate(repo)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].rule_id, "doc-metadata-concatenated-title")
            self.assertIn("Document title contains concatenated metadata attributes", str(errors[0]))
            self.assertIn("Mission Intent (DOC-MI-A5-001 v3.0.0 2026-08-31)", str(errors[0]))


if __name__ == "__main__":
    unittest.main()
