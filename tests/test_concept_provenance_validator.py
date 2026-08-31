#!/usr/bin/env python3
"""
Unit test suite for ConceptProvenanceValidator.
/// Realises: [ConceptProvenanceValidator, Phase0CONOPSValidation, SensorResolutionGroundTruth, InlineCitationVerification]

Tests:
1. Instantiation and IValidator interface adherence.
2. Dynamic ground-truth extraction from schema/extracted/*.
3. Detection and flagging of sensor fabrications (24.0 MP, 640x512) with Severity.ERROR.
4. Detection of parametric mismatches (wingspan, MTOW, airspeeds).
5. Detection of missing inline citation anchors.
6. Detection of non-existent / invalid source locators.
7. Detection of ungrounded AI buzzwords (CUDA, YOLO, PyTorch, etc.).
8. Passing case with fully grounded, cited CONOPS and mission intent documents.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure parity_auditor package is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
PARITY_AUDITOR_SRC = REPO_ROOT / "skills" / "spec-orchestrator" / "parity_auditor" / "src"
if str(PARITY_AUDITOR_SRC) not in sys.path:
    sys.path.insert(0, str(PARITY_AUDITOR_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parity_auditor.core.findings import Finding
from parity_auditor.core.workspace import WorkspaceRepository
from parity_auditor.validators.base import IValidator
from parity_auditor.validators.concept_provenance_validator import (
    ConceptProvenanceValidator,
    RuleID,
    Severity,
    extract_ground_truth,
)


@pytest.fixture
def test_workspace(tmp_path):
    """Create a temporary workspace directory mimicking DEAP structure."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    schema_dir = ws / "schema" / "extracted"
    schema_dir.mkdir(parents=True)
    conops_dir = ws / "docs" / "conops"
    conops_dir.mkdir(parents=True)

    # Populate mock ground-truth extraction file
    spec_sheet_content = """# AVENGER 5 Specification Sheet
## Page 3
PERFORMANCE
Endurance: 90 min
Cruise speed: 31 m/s
Max horizontal speed: 42 m/s
Stall speed: 24 m/s
Max dive speed: 80 m/s
STRUCTURAL DETAILS
Wingspan: 1.8 m
Overall length: 1.6 m
MTOW: 17 kg
INSTRUMENTATION
Day camera - 1280x720
Thermal camera - 1280x720
"""
    (schema_dir / "AVENGER_5_Spec_sheet_full.md").write_text(spec_sheet_content, encoding="utf-8")

    user_manual_content = """# AVENGER 5 USER MANUAL
Table 1.3: Flight Performance
Cruise speed: 30 m/s
Max horizontal speed: 38 m/s
Stall speed: 26 m/s
Table 1.4: Payload & Seeker
Day camera: 1280x720 (HD)
Thermal camera: 1280x720 (HD)
"""
    (schema_dir / "A5_user_manual_full.md").write_text(user_manual_content, encoding="utf-8")

    return ws


class TestConceptProvenanceValidatorInterface:
    """Verify validator interface and typing."""

    def test_implements_ivalidator(self):
        validator = ConceptProvenanceValidator()
        assert isinstance(validator, IValidator)

    def test_validate_signature_accepts_repo_or_ast_spec_dir(self, test_workspace):
        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        
        # Test signature variants
        findings1 = validator.validate(repo=repo)
        assert isinstance(findings1, list)

        findings2 = validator.validate(schema_ast=None, spec_dir=str(test_workspace / "docs" / "conops"))
        assert isinstance(findings2, list)


class TestGroundTruthExtraction:
    """Verify dynamic ground truth extraction from schema/extracted/*_full.md."""

    def test_extract_ground_truth_from_schema(self, test_workspace):
        truth = extract_ground_truth(test_workspace / "schema" / "extracted")
        assert truth["wingspan_m"] == 1.8
        assert truth["mtow_kg"] == 17.0
        assert truth["day_camera_resolution"] == "1280x720"
        assert truth["thermal_camera_resolution"] == "1280x720"
        assert truth["cruise_speed_range"] == (30.0, 31.0)
        assert truth["max_speed_range"] == (38.0, 42.0)
        assert truth["stall_speed_range"] == (24.0, 26.0)


class TestSensorFabricationDetection:
    """Verify detection of fabricated sensor resolutions (24.0 MP, 640x512)."""

    def test_flags_24mp_daylight_camera_fabrication(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "MISSION_INTENT.md"
        conops_file.write_text("""# Mission Intent
| Parameter | Value |
| :--- | :--- |
| **EO Daylight Camera** | 24.0 MP / HD 1280x720 <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Thermal IR Camera** | 1280x720 <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        sensor_errors = [f for f in findings if f.rule_id == RuleID.SENSOR_FABRICATION]
        assert len(sensor_errors) >= 1
        assert any("24.0 MP" in str(f) or "24 MP" in str(f) or "Daylight" in str(f) for f in sensor_errors)
        assert any(f.detail.get("severity") == Severity.ERROR for f in sensor_errors)

    def test_flags_640x512_thermal_camera_fabrication(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "MISSION_INTENT.md"
        conops_file.write_text("""# Mission Intent
| Parameter | Value |
| :--- | :--- |
| **EO Daylight Camera** | 1280x720 <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Thermal IR Camera** | 640x512 / HD 1280x720 <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        sensor_errors = [f for f in findings if f.rule_id == RuleID.SENSOR_FABRICATION]
        assert len(sensor_errors) >= 1
        assert any("640x512" in str(f) or "Thermal" in str(f) for f in sensor_errors)


class TestParametricMismatchDetection:
    """Verify detection of parametric discrepancies (wingspan, MTOW, airspeeds)."""

    def test_flags_wingspan_mismatch(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "CONOPS.md"
        conops_file.write_text("""# CONOPS
The airframe features a 2.4 m wingspan for high-altitude loitering. <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 -->
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        param_errors = [f for f in findings if f.rule_id == RuleID.PARAMETRIC_MISMATCH]
        assert len(param_errors) >= 1
        assert any("wingspan" in str(f).lower() and "2.4" in str(f) for f in param_errors)

    def test_flags_mtow_mismatch(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "CONOPS.md"
        conops_file.write_text("""# CONOPS
| Parameter | Value |
| :--- | :--- |
| **MTOW** | 25.0 kg <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        param_errors = [f for f in findings if f.rule_id == RuleID.PARAMETRIC_MISMATCH]
        assert len(param_errors) >= 1
        assert any("mtow" in str(f).lower() and "25" in str(f) for f in param_errors)


class TestInlineCitationVerification:
    """Verify detection of missing citations and invalid source locators."""

    def test_flags_missing_inline_citation_anchor(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "MISSION_INTENT.md"
        conops_file.write_text("""# Mission Intent
| Parameter | Value |
| :--- | :--- |
| **Wingspan** | 1.8 m |
| **MTOW** | 17.0 kg |
| **Cruise Speed** | 31.0 m/s |
| **EO Daylight Camera** | 1280x720 |
| **Thermal IR Camera** | 1280x720 |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        citation_errors = [f for f in findings if f.rule_id == RuleID.MISSING_CITATION]
        assert len(citation_errors) >= 1

    def test_flags_non_existent_source_locator(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "MISSION_INTENT.md"
        conops_file.write_text("""# Mission Intent
| Parameter | Value |
| :--- | :--- |
| **Wingspan** | 1.8 m <!-- Source: schema/extracted/non_existent_document.md:123 --> |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        locator_errors = [f for f in findings if f.rule_id == RuleID.INVALID_SOURCE_LOCATOR]
        assert len(locator_errors) >= 1
        assert any("non_existent_document" in str(f) for f in locator_errors)


class TestUngroundedAIBuzzwords:
    """Verify rejection of ungrounded deep learning and GPU buzzwords."""

    def test_flags_cuda_and_yolo_buzzwords(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "CONOPS.md"
        conops_file.write_text("""# CONOPS
The payload computer executes YOLO object detection with CUDA GPU acceleration. <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 -->
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        buzzword_errors = [f for f in findings if f.rule_id == RuleID.UNGROUNDED_BUZZWORD]
        assert len(buzzword_errors) >= 1
        assert any("CUDA" in str(f) or "YOLO" in str(f) for f in buzzword_errors)


class TestFullyGroundedCONOPSPasses:
    """Verify that a compliant, grounded CONOPS with valid citations passes with 0 findings."""

    def test_passes_grounded_document(self, test_workspace):
        conops_file = test_workspace / "docs" / "conops" / "MISSION_INTENT.md"
        conops_file.write_text("""# Mission Intent: AVENGER 5 UAS

## Technical Specifications
| Parameter | Specification Value | Description / Source |
| :--- | :--- | :--- |
| **Airframe Wingspan** | 1.8 m | Modular composite wing <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Maximum Takeoff Weight (MTOW)** | 17.0 kg | Maximum launch mass <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Nominal Cruise Speed** | 31.0 m/s | Cruise airspeed <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Stall Speed** | 24.0 m/s | Minimum airspeed <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **EO Daylight Camera** | 1280x720 (HD) | Dual EO/IR gimbal seeker <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
| **Thermal IR Camera** | 1280x720 (HD) | Uncooled microbolometer <!-- Source: schema/extracted/AVENGER_5_Spec_sheet_full.md: Page 3 --> |
""", encoding="utf-8")

        validator = ConceptProvenanceValidator()
        repo = WorkspaceRepository(str(test_workspace))
        findings = validator.validate(repo=repo)

        assert len(findings) == 0
