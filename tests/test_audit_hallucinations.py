#!/usr/bin/env python3
"""
Unit test suite for the Automated Anti-Hallucination Scanner & Ground-Truth Citation Verifier.
Validates parametric consistency checking, ungrounded AI buzzword detection,
ground-truth source citation auditing, and CLI reporting.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure scripts directory and repo root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_hallucinations import (
    AIBuzzwordAuditor,
    FindingCategory,
    GroundTruth,
    HallucinationScanner,
    ParametricAuditor,
    Severity,
    SourceCitationAuditor,
    clean_latex,
)


# ==============================================================================
# 0. Utility Functions Tests
# ==============================================================================

class TestCleanLatex:
    """Tests for LaTeX string sanitization."""

    def test_clean_latex_removes_math_wrappers(self):
        assert clean_latex(r"$< 25\,\text{kg}$ MTOW") == "< 25 kg MTOW"
        assert clean_latex(r"$V_s = 24.0\mathrm{ m/s}$") == "V_s = 24.0 m/s"
        assert clean_latex(r"$m_{\mathbf{MTOW}} = 17.0\quad\text{kg}$") == "m_{MTOW} = 17.0 kg"


# ==============================================================================
# 1. Parametric Consistency Tests
# ==============================================================================

class TestParametricAuditor:
    """Tests for parametric consistency verification against SSOT invariants."""

    def test_wingspan_detection(self):
        """Verify that wingspan values != 1.8 m are flagged, and 1.8 m passes."""
        # Valid wingspans
        valid_md = """
        | **Wingspan (b)** | 1.8 | m |
        The aircraft has a 1.80 m composite wingspan.
        Parameter: Wingspan | Value: 1.8 m
        wingspan = 1.80 m
        """
        findings = ParametricAuditor._audit_markdown(valid_md.splitlines(), "test.md")
        wingspan_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_WINGSPAN]
        assert len(wingspan_findings) == 0

        # Invalid wingspans
        invalid_md = """
        The UAV features a 2.4 m wingspan for increased glide efficiency.
        | Wingspan | 2.2 m |
        Parameter: Wingspan | Value: 1.5 m
        """
        findings = ParametricAuditor._audit_markdown(invalid_md.splitlines(), "test.md")
        wingspan_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_WINGSPAN]
        assert len(wingspan_findings) == 3
        assert all(f.severity == Severity.ERROR for f in wingspan_findings)

    def test_mtow_detection(self):
        """Verify that MTOW values != 17.0 kg are flagged, including LaTeX formatted claims."""
        # Valid MTOW statements
        valid_md = """
        | Maximum Takeoff Weight (MTOW) | 17.0 | kg |
        Operating at a Maximum Take-Off Mass (MTOM) of 17.0 kg.
        The 17.0 kg MTOW aircraft is launched.
        $m_{\\text{MTOW}} = 17.0$
        Payload mass is 5.0 kg and battery mass is 4.2 kg.
        """
        findings = ParametricAuditor._audit_markdown(valid_md.splitlines(), "test.md")
        mtow_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_MTOW]
        assert len(mtow_findings) == 0

        # Invalid MTOW statements
        invalid_md = """
        - Airframe Type: Multi-Rotor / VTOL Fixed-Wing Hybrid ($< 25\\,\\text{kg}$ MTOW).
        | MTOW | 22.0 kg |
        Maximum Take-Off Weight (MTOW) of 15.0 kg.
        m_{\\text{MTOW}} = 20.0
        """
        findings = ParametricAuditor._audit_markdown(invalid_md.splitlines(), "test.md")
        mtow_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_MTOW]
        assert len(mtow_findings) == 4
        assert all(f.severity == Severity.ERROR for f in mtow_findings)

    def test_stall_speed_detection(self):
        """Verify that stall speed values != 24.0 m/s are flagged."""
        valid_md = "Stall speed: 24.0 m/s (V_s = 24.0 m/s)."
        findings = ParametricAuditor._audit_markdown(valid_md.splitlines(), "test.md")
        stall_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_STALL_SPEED]
        assert len(stall_findings) == 0

        invalid_md = """
        Aerodynamic stall speed V_s = 18.0 m/s.
        Stall speed: 20.0 m/s.
        | V_s | Stall Airspeed | 22.0 m/s |
        """
        findings = ParametricAuditor._audit_markdown(invalid_md.splitlines(), "test.md")
        stall_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_STALL_SPEED]
        assert len(stall_findings) == 3

    def test_cruise_and_max_speed_detection(self):
        """Verify that cruise speed (31.0 m/s) and max horizontal speed (42.0 m/s) are audited."""
        valid_md = """
        Cruise speed: 31.0 m/s.
        Max horizontal speed: 42.0 m/s.
        Max dive speed: 80.0 m/s.
        Terminal dive speed: 55.0 m/s.
        """
        findings = ParametricAuditor._audit_markdown(valid_md.splitlines(), "test.md")
        speed_findings = [
            f for f in findings
            if f.category in (FindingCategory.PARAMETRIC_CRUISE_SPEED, FindingCategory.PARAMETRIC_MAX_SPEED)
        ]
        assert len(speed_findings) == 0

        invalid_md = """
        Cruise speed: 25.0 m/s.
        Max horizontal speed: 50.0 m/s.
        """
        findings = ParametricAuditor._audit_markdown(invalid_md.splitlines(), "test.md")
        cruise_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_CRUISE_SPEED]
        max_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_MAX_SPEED]
        assert len(cruise_findings) == 1
        assert len(max_findings) == 1

    def test_launch_speed_detection(self):
        """Verify launch and exit airspeed (>= 26.0 m/s) checking."""
        valid_md = """
        Launch speed: 26.0 m/s.
        Exit airspeed: 26.5 m/s.
        """
        findings = ParametricAuditor._audit_markdown(valid_md.splitlines(), "test.md")
        launch_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_LAUNCH_SPEED]
        assert len(launch_findings) == 0

        invalid_md = """
        Launch speed: 18.0 m/s.
        Exit airspeed: 20.0 m/s.
        """
        findings = ParametricAuditor._audit_markdown(invalid_md.splitlines(), "test.md")
        launch_findings = [f for f in findings if f.category == FindingCategory.PARAMETRIC_LAUNCH_SPEED]
        assert len(launch_findings) == 2

    def test_sysml_parametric_auditing(self):
        """Verify that SysML attribute definitions are strictly validated against SSOT constants."""
        valid_sysml = """
        part def Avenger5UAV {
            attribute wingspan_m : Real default 1.8;
            attribute mtow_kg : Real default 17.0;
            attribute cruiseSpeed_mps : Real default 31.0;
            attribute maxSpeed_mps : Real default 42.0;
            attribute stallSpeed_mps : Real default 24.0;
            attribute launchSpeed_mps : Real default 26.0;
        }
        part def PL40CatapultLauncher {
            attribute minPressure_bar : Real default 8.5;
            attribute nominalPressure_bar : Real default 10.0;
            attribute maxPressure_bar : Real default 14.0;
        }
        """
        findings = ParametricAuditor._audit_sysml(valid_sysml.splitlines(), "schema/Avenger5.sysml")
        assert len(findings) == 0

        invalid_sysml = """
        part def Avenger5UAV {
            attribute wingspan_m : Real default 2.2;
            attribute mtow_kg : Real default 25.0;
            attribute cruiseSpeed_mps : Real default 28.0;
            attribute maxSpeed_mps : Real default 48.0;
            attribute stallSpeed_mps : Real default 18.0;
            attribute launchSpeed_mps : Real default 20.0;
        }
        part def PL40CatapultLauncher {
            attribute minPressure_bar : Real default 5.0;
            attribute nominalPressure_bar : Real default 20.0;
            attribute maxPressure_bar : Real default 16.0;
        }
        """
        findings = ParametricAuditor._audit_sysml(invalid_sysml.splitlines(), "schema/Avenger5.sysml")
        categories = {f.category for f in findings}
        assert FindingCategory.PARAMETRIC_WINGSPAN in categories
        assert FindingCategory.PARAMETRIC_MTOW in categories
        assert FindingCategory.PARAMETRIC_STALL_SPEED in categories
        assert FindingCategory.PARAMETRIC_CRUISE_SPEED in categories
        assert FindingCategory.PARAMETRIC_MAX_SPEED in categories
        assert FindingCategory.PARAMETRIC_LAUNCH_SPEED in categories
        assert FindingCategory.PARAMETRIC_LAUNCH_PRESSURE in categories
        assert len(findings) == 9


# ==============================================================================
# 2. Ungrounded AI / Deep Learning Buzzword Tests
# ==============================================================================

class TestAIBuzzwordAuditor:
    """Tests for detecting ungrounded machine learning and deep learning assumptions."""

    def test_detects_cuda_buzzword(self):
        content = "The optical tracking subsystem utilizes CUDA kernel acceleration on Nvidia GPU."
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.UNGROUNDED_AI_BUZZWORD
        assert "CUDA" in findings[0].matched_text

    def test_detects_yolo_buzzword(self):
        content = "Bounding boxes are extracted using YOLOv8 neural network inference at 30 fps."
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) == 1
        assert "YOLO" in findings[0].matched_text

    def test_detects_pytorch_and_tensorrt(self):
        content = """
        Model weights are trained in PyTorch and deployed via TensorRT runtime.
        """
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        matched = [f.matched_text for f in findings]
        assert any("PyTorch" in m for m in matched)
        assert any("TensorRT" in m for m in matched)

    def test_detects_backpropagation(self):
        content = "Online gradient backprop updates model weights during flight."
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) == 1
        assert "backprop" in findings[0].matched_text.lower()

    def test_detects_transformer_neural_network(self):
        content = "Target tracking is performed by a vision transformer neural network tracker."
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) >= 1
        assert findings[0].category == FindingCategory.UNGROUNDED_AI_BUZZWORD

    def test_detects_deep_rl_flight_control(self):
        content = "The autopilot runs deep reinforcement learning flight control algorithms."
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) == 1
        assert "reinforcement learning" in findings[0].matched_text.lower()

    def test_allows_benign_transformer_terminology(self):
        """Verify that electrical power transformers or coordinate transformers are not flagged."""
        content = """
        The antenna rotator utilizes WGS84CoordinateTransformer for ENU coordinate conversion.
        A step-down electrical transformer converts AC power at the GCS generator interface.
        """
        findings = AIBuzzwordAuditor.audit_file("test.md", content, "test.md")
        assert len(findings) == 0


# ==============================================================================
# 3. Ground-Truth Source Citation Tests
# ==============================================================================

class TestSourceCitationAuditor:
    """Tests for auditing authoritative ground-truth source citations."""

    def test_flags_missing_ground_truth_citation_in_feature_spec(self, tmp_path):
        bad_spec = """
        # Feature: FEAT-999: Invented Guidance Logic

        ## Description
        This specification describes an imaginary subsystem with no authoritative source citations.
        """
        spec_file = tmp_path / "docs" / "features" / "feat-999-invented.md"
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        spec_file.write_text(bad_spec, encoding="utf-8")

        findings = SourceCitationAuditor.audit_feature_spec(
            str(spec_file), bad_spec, "docs/features/feat-999-invented.md", tmp_path
        )
        citation_findings = [f for f in findings if f.category == FindingCategory.GROUND_TRUTH_CITATION]
        assert len(citation_findings) >= 1
        assert "does not cite any authoritative ground-truth source" in citation_findings[0].message

    def test_passes_valid_source_citation(self, tmp_path):
        schema_file = tmp_path / "schema" / "Avenger5.sysml"
        schema_file.parent.mkdir(parents=True, exist_ok=True)
        schema_file.write_text("package Avenger5Model {}", encoding="utf-8")

        manual_file = tmp_path / "schema" / "extracted" / "A5_user_manual_full.md"
        manual_file.parent.mkdir(parents=True, exist_ok=True)
        manual_file.write_text("# User Manual", encoding="utf-8")

        good_spec = """
        | **Specification Source** | [schema/Avenger5.sysml](../../schema/Avenger5.sysml) |

        # Feature: FEAT-001A: Fuselage & Structure

        ## Source References
        Structural Schema: [`schema/Avenger5.sysml`](../../schema/Avenger5.sysml)
        Normative Specification: [`schema/extracted/A5_user_manual_full.md`](../../schema/extracted/A5_user_manual_full.md)
        """
        spec_file = tmp_path / "docs" / "features" / "feat-001a.md"
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        spec_file.write_text(good_spec, encoding="utf-8")

        findings = SourceCitationAuditor.audit_feature_spec(
            str(spec_file), good_spec, "docs/features/feat-001a.md", tmp_path
        )
        assert len(findings) == 0

    def test_detects_unresolved_placeholders(self, tmp_path):
        placeholder_spec = """
        | **Specification Source** | [link-to-schema] |

        ## Source References
        Normative Specification: [link-to-specification]
        """
        spec_file = tmp_path / "docs" / "features" / "feat-001a.md"
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        spec_file.write_text(placeholder_spec, encoding="utf-8")

        findings = SourceCitationAuditor.audit_feature_spec(
            str(spec_file), placeholder_spec, "docs/features/feat-001a.md", tmp_path
        )
        placeholder_findings = [f for f in findings if "Unresolved template placeholder" in f.message]
        assert len(placeholder_findings) >= 1

    def test_detects_broken_schema_links(self, tmp_path):
        broken_link_spec = """
        | **Specification Source** | [schema/Avenger5.sysml](../../schema/Avenger5.sysml) |

        ## Source References
        Normative Specification: [Nonexistent Manual](../../schema/extracted/nonexistent_manual.md)
        """
        spec_file = tmp_path / "docs" / "features" / "feat-001a.md"
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        spec_file.write_text(broken_link_spec, encoding="utf-8")

        findings = SourceCitationAuditor.audit_feature_spec(
            str(spec_file), broken_link_spec, "docs/features/feat-001a.md", tmp_path
        )
        broken_findings = [f for f in findings if "does not exist on disk" in f.message]
        assert len(broken_findings) >= 1


# ==============================================================================
# 4. CLI & End-to-End Scanner Tests
# ==============================================================================

class TestScannerCLI:
    """Tests for CLI flags, exit codes, and JSON reporting."""

    def test_scanner_on_clean_temp_repo(self, tmp_path):
        """Verify that a 100% compliant repo exits with code 0."""
        schema_file = tmp_path / "schema" / "Avenger5.sysml"
        schema_file.parent.mkdir(parents=True, exist_ok=True)
        schema_file.write_text(
            """
            package Avenger5Model {
                part def Avenger5UAV {
                    attribute wingspan_m : Real default 1.8;
                    attribute mtow_kg : Real default 17.0;
                    attribute stallSpeed_mps : Real default 24.0;
                    attribute cruiseSpeed_mps : Real default 31.0;
                    attribute maxSpeed_mps : Real default 42.0;
                    attribute launchSpeed_mps : Real default 26.0;
                }
            }
            """,
            encoding="utf-8",
        )

        extracted_manual = tmp_path / "schema" / "extracted" / "A5_user_manual_full.md"
        extracted_manual.parent.mkdir(parents=True, exist_ok=True)
        extracted_manual.write_text("# A5 User Manual", encoding="utf-8")

        doc_file = tmp_path / "docs" / "features" / "feat-001a.md"
        doc_file.parent.mkdir(parents=True, exist_ok=True)
        doc_file.write_text(
            """
            | **Specification Source** | [schema/Avenger5.sysml](../../schema/Avenger5.sysml) |

            # Feature FEAT-001A
            Wingspan: 1.8 m, MTOW: 17.0 kg, Stall speed: 24.0 m/s, Cruise speed: 31.0 m/s.
            Tracking uses classical 2D Kalman filter with Mahalanobis innovation gating.

            ## Source References
            - [schema/extracted/A5_user_manual_full.md](../../schema/extracted/A5_user_manual_full.md)
            """,
            encoding="utf-8",
        )

        scanner = HallucinationScanner(repo_root=tmp_path)
        findings = scanner.run()
        error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
        assert error_count == 0

        # Run via CLI
        report_path = tmp_path / "report.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "audit_hallucinations.py"),
            "--repo-root",
            str(tmp_path),
            "--json-report",
            str(report_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert report_path.exists()

        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert report_data["summary"]["passed"] is True
        assert report_data["summary"]["error_count"] == 0

    def test_scanner_detects_violations_and_exits_one(self, tmp_path):
        """Verify that violations produce exit code 1 and structured JSON output."""
        bad_doc = tmp_path / "docs" / "features" / "feat-bad.md"
        bad_doc.parent.mkdir(parents=True, exist_ok=True)
        bad_doc.write_text(
            """
            # Feature FEAT-BAD
            Wingspan is 3.5 m, MTOW is 35.0 kg.
            Guidance utilizes CUDA-accelerated PyTorch YOLOv8 transformer neural network.
            """,
            encoding="utf-8",
        )

        report_path = tmp_path / "bad_report.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "audit_hallucinations.py"),
            "--repo-root",
            str(tmp_path),
            "--json-report",
            str(report_path),
            "--fix",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "AUDIT FAILED" in result.stdout
        assert "CUDA" in result.stdout

        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert report_data["summary"]["passed"] is False
        assert report_data["summary"]["error_count"] >= 4
