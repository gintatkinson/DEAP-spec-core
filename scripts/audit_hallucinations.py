#!/usr/bin/env python3
"""
Automated Anti-Hallucination Scanner & Ground-Truth Citation Verifier.
Verifies parametric consistency, flags ungrounded AI/deep-learning buzzwords,
and audits ground-truth source citations across specification markdown files
and SysML v2 models.

Authoritative Ground Truth Sources:
- A5 User Manual (schema/extracted/A5_user_manual_full.md)
- AVENGER 5 Specification Sheet (schema/extracted/AVENGER_5_Spec_sheet_full.md)
- A5 Prep and Safety Guide (schema/extracted/A5_prep_and_safety_full.md)
- ESAD ICD (schema/extracted/ESAD_ICD_full.md)
- SysML v2 Architecture Model (schema/Avenger5.sysml)
"""

import argparse
import dataclasses
import json
import os
import re
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# Ground-Truth Reference Constants & Invariants
# ==============================================================================

class GroundTruth:
    """Platform invariants established in schema/Avenger5.sysml and authoritative manuals."""
    WINGSPAN_M = 1.8
    MTOW_KG = 17.0
    STALL_SPEED_MPS = 24.0
    CRUISE_SPEED_MPS = 31.0
    MAX_SPEED_MPS = 42.0
    LAUNCH_SPEED_MPS = 26.0
    LAUNCH_PRESSURE_NOMINAL_BAR = 10.0
    LAUNCH_PRESSURE_MIN_BAR = 8.5
    LAUNCH_PRESSURE_MAX_BAR = 13.5
    LAUNCH_PRESSURE_RELIEF_MAX_BAR = 14.0


# Authoritative source document identifiers
AUTHORITATIVE_SOURCES = {
    "user_manual": [
        "schema/extracted/A5_user_manual_full.md",
        "A5_user_manual_full.md",
        "schema/A5-user-manual 2.pdf",
        "A5-user-manual 2.pdf",
        "A5-user-manual",
        "A5 User Manual",
        "UDS-A5UM-001",
    ],
    "spec_sheet": [
        "schema/extracted/AVENGER_5_Spec_sheet_full.md",
        "AVENGER_5_Spec_sheet_full.md",
        "schema/AVENGER 5 Spec sheet_rev3.pdf",
        "AVENGER 5 Spec sheet_rev3.pdf",
        "AVENGER 5 Spec sheet",
        "Avenger 5 Specification Sheet",
    ],
    "prep_and_safety": [
        "schema/extracted/A5_prep_and_safety_full.md",
        "A5_prep_and_safety_full.md",
        "schema/A5_prep and safety_rev7.pdf",
        "A5_prep and safety_rev7.pdf",
        "A5_prep and safety",
        "Preparation and Safety Instructions",
    ],
    "esad_icd": [
        "schema/extracted/ESAD_ICD_full.md",
        "ESAD_ICD_full.md",
        "schema/ESAD ICD_for Excalibur_AB00-0054-01AA-0005 2 1.pdf",
        "ESAD ICD_for Excalibur_AB00-0054-01AA-0005 2 1.pdf",
        "ESAD ICD",
        "AB00-0054-01AA-0005",
    ],
    "sysml_model": [
        "schema/Avenger5.sysml",
        "Avenger5.sysml",
        "Avenger5Model",
        "Avenger5Definitions",
    ],
}

# Forbidden ungrounded AI / Deep Learning Buzzwords
UNGROUNDED_BUZZWORDS = [
    (r"\bCUDA\b", "CUDA", "NVIDIA CUDA GPU programming framework"),
    (r"\bYOLO(?:v\d+)?\b", "YOLO", "YOLO deep learning object detector"),
    (r"\b(?:PyTorch|torch\.nn|torchvision)\b", "PyTorch", "PyTorch deep learning framework"),
    (r"\bTensorRT\b", "TensorRT", "NVIDIA TensorRT inference accelerator"),
    (r"\bbackprop(?:agation)?\b", "backprop", "Onboard gradient backpropagation / training"),
    (
        r"\b(?:transformer\s+neural\s+network|vision\s+transformer|ViT-based|transformer-based\s+(?:tracker|tracking|detector|detection|guidance|control))\b",
        "transformer neural network",
        "Transformer-based neural network architecture in tracking/guidance",
    ),
    (
        r"\bdeep\s+reinforcement\s+learning\s+(?:flight\s+control|guidance|autopilot)\b",
        "deep reinforcement learning flight control",
        "Ungrounded deep RL in safety-critical flight control laws",
    ),
]


# ==============================================================================
# Helper Functions
# ==============================================================================

def clean_latex(text: str) -> str:
    """Strips LaTeX formatting, delimiters, and spacing to normalize engineering text."""
    cleaned = re.sub(r"\\[,;!]|\\quad|\\qquad", " ", text)
    cleaned = re.sub(r"\\(?:text|mathrm|mathbf|mathit)\{([^}]*)\}", r"\1", cleaned)
    cleaned = cleaned.replace("$", "")
    return cleaned


# ==============================================================================
# Finding Data Model
# ==============================================================================

class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class FindingCategory(str, Enum):
    PARAMETRIC_WINGSPAN = "PARAMETRIC_WINGSPAN"
    PARAMETRIC_MTOW = "PARAMETRIC_MTOW"
    PARAMETRIC_STALL_SPEED = "PARAMETRIC_STALL_SPEED"
    PARAMETRIC_CRUISE_SPEED = "PARAMETRIC_CRUISE_SPEED"
    PARAMETRIC_MAX_SPEED = "PARAMETRIC_MAX_SPEED"
    PARAMETRIC_LAUNCH_SPEED = "PARAMETRIC_LAUNCH_SPEED"
    PARAMETRIC_LAUNCH_PRESSURE = "PARAMETRIC_LAUNCH_PRESSURE"
    UNGROUNDED_AI_BUZZWORD = "UNGROUNDED_AI_BUZZWORD"
    GROUND_TRUTH_CITATION = "GROUND_TRUTH_CITATION"


@dataclasses.dataclass
class Finding:
    file_path: str
    line_number: int
    category: FindingCategory
    severity: Severity
    message: str
    matched_text: str
    expected_value: str
    actual_value: str
    suggestion: str
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "matched_text": self.matched_text,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "suggestion": self.suggestion,
            "snippet": self.snippet,
        }


# ==============================================================================
# Parametric Consistency Auditor
# ==============================================================================

class ParametricAuditor:
    """Audits SysML and Markdown files for platform parametric consistency."""

    # Regex patterns for markdown inspection
    RE_WINGSPAN_MD = re.compile(
        r"(?:wingspan|wing\s+span)\s*(?:\(b\))?\s*(?:of|=|:|\bis\b|\|)\s*(?:b\s*=\s*)?([0-9]+\.?[0-9]*)\s*m\b",
        re.IGNORECASE,
    )
    RE_WINGSPAN_ALT_MD = re.compile(
        r"\b([0-9]+\.?[0-9]*)\s*m\s*(?:composite\s*)?wingspan\b",
        re.IGNORECASE,
    )
    RE_WINGSPAN_PARAM_MD = re.compile(
        r"Parameter:\s*Wingspan\s*\|\s*Value:\s*([0-9]+\.?[0-9]*)\s*m",
        re.IGNORECASE,
    )

    RE_MTOW_MD = re.compile(
        r"(?:MTOW|MTOM|Maximum\s+Take-?Off\s+(?:Weight|Mass))\s*(?:\([^)]*\))?\s*(?:of|=|:|\bis\b|\||<|>|<=|>=|≤|≥)?\s*([0-9]+\.?[0-9]*)\s*kg",
        re.IGNORECASE,
    )
    RE_MTOW_ALT_MD = re.compile(
        r"(?:[<>]|<=|>=|≤|≥)?\s*([0-9]+\.?[0-9]*)\s*kg\s*(?:MTOW|MTOM)",
        re.IGNORECASE,
    )
    RE_MTOW_LATEX_MD = re.compile(
        r"m_\{?(?:\\text\{)?MTOW\}?\s*(?:=|\\le|<=|≤)\s*([0-9]+\.?[0-9]*)",
        re.IGNORECASE,
    )

    RE_STALL_SPEED_MD = re.compile(
        r"(?:stall\s+speed|V_s|V_stall|V_\{s\}|V_\{stall\})\s*(?:\([^)]*\))?\s*(?:of|=|:|\bis\b|\|)\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)",
        re.IGNORECASE,
    )
    RE_STALL_SPEED_TABLE = re.compile(
        r"\|\s*V_s\s*\|\s*Stall\s+Airspeed\s*\|\s*([0-9]+\.?[0-9]*)\s*m/s",
        re.IGNORECASE,
    )

    RE_CRUISE_SPEED_MD = re.compile(
        r"(?:cruise\s+speed|V_cruise|V_\{cruise\})\s*(?:\([^)]*\))?\s*(?:of|=|:|\bis\b|\|)\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)",
        re.IGNORECASE,
    )

    RE_MAX_SPEED_MD = re.compile(
        r"(?:max(?:imum)?\s+(?:horizontal\s+|level\s+)?speed|max(?:imum)?\s+(?:level\s+)?airspeed|V_max|V_\{max\})\s*(?:\([^)]*\))?\s*(?:of|=|:|\bis\b|\|)\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)",
        re.IGNORECASE,
    )

    RE_LAUNCH_SPEED_MD = re.compile(
        r"(?:launch\s+speed|exit\s+airspeed|exit\s+speed)\s*(?:\([^)]*\))?\s*(?:of|=|:|\bis\b|\||>=|\\ge)\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)",
        re.IGNORECASE,
    )

    @classmethod
    def audit_file(cls, file_path: str, content: str, rel_path: str) -> List[Finding]:
        findings: List[Finding] = []
        is_sysml = file_path.endswith(".sysml")
        lines = content.splitlines()

        if is_sysml:
            findings.extend(cls._audit_sysml(lines, rel_path))
        else:
            findings.extend(cls._audit_markdown(lines, rel_path))

        return findings

    @classmethod
    def _audit_sysml(cls, lines: List[str], rel_path: str) -> List[Finding]:
        findings: List[Finding] = []

        sysml_attr_patterns = [
            (
                re.compile(r"attribute\s+wingspan_m\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_WINGSPAN,
                GroundTruth.WINGSPAN_M,
                0.01,
                "Wingspan attribute 'wingspan_m' must default to 1.8 m.",
                "1.8",
                "attribute wingspan_m : Real default 1.8;",
            ),
            (
                re.compile(r"attribute\s+mtow_kg\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_MTOW,
                GroundTruth.MTOW_KG,
                0.1,
                "MTOW attribute 'mtow_kg' must default to 17.0 kg.",
                "17.0",
                "attribute mtow_kg : Real default 17.0;",
            ),
            (
                re.compile(r"attribute\s+stallSpeed_mps\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_STALL_SPEED,
                GroundTruth.STALL_SPEED_MPS,
                0.1,
                "Stall speed attribute 'stallSpeed_mps' must default to 24.0 m/s.",
                "24.0",
                "attribute stallSpeed_mps : Real default 24.0;",
            ),
            (
                re.compile(r"attribute\s+cruiseSpeed_mps\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_CRUISE_SPEED,
                GroundTruth.CRUISE_SPEED_MPS,
                0.1,
                "Cruise speed attribute 'cruiseSpeed_mps' must default to 31.0 m/s.",
                "31.0",
                "attribute cruiseSpeed_mps : Real default 31.0;",
            ),
            (
                re.compile(r"attribute\s+maxSpeed_mps\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_MAX_SPEED,
                GroundTruth.MAX_SPEED_MPS,
                0.1,
                "Max level speed attribute 'maxSpeed_mps' must default to 42.0 m/s.",
                "42.0",
                "attribute maxSpeed_mps : Real default 42.0;",
            ),
            (
                re.compile(r"attribute\s+(?:launchSpeed_mps|exitAirspeed_mps)\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_LAUNCH_SPEED,
                GroundTruth.LAUNCH_SPEED_MPS,
                0.1,
                "Launch speed attribute must default to >= 26.0 m/s.",
                ">= 26.0",
                "attribute launchSpeed_mps : Real default 26.0;",
            ),
            (
                re.compile(r"attribute\s+minPressure_bar\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);"),
                FindingCategory.PARAMETRIC_LAUNCH_PRESSURE,
                GroundTruth.LAUNCH_PRESSURE_MIN_BAR,
                0.1,
                "Launcher min operating pressure 'minPressure_bar' must default to 8.5 bar.",
                "8.5",
                "attribute minPressure_bar : Real default 8.5;",
            ),
        ]

        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()
            for pat, cat, expected, tol, msg, exp_str, sugg in sysml_attr_patterns:
                m = pat.search(line_str)
                if m:
                    val = float(m.group(1))
                    if abs(val - expected) > tol:
                        findings.append(
                            Finding(
                                file_path=rel_path,
                                line_number=line_num,
                                category=cat,
                                severity=Severity.ERROR,
                                message=msg,
                                matched_text=m.group(0),
                                expected_value=exp_str,
                                actual_value=str(val),
                                suggestion=sugg,
                                snippet=line_str,
                            )
                        )

            # Check nominalPressure_bar range [10.0, 13.5]
            m_nom = re.search(r"attribute\s+nominalPressure_bar\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);", line_str)
            if m_nom:
                val = float(m_nom.group(1))
                if val < 10.0 - 0.05 or val > 13.5 + 0.05:
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.PARAMETRIC_LAUNCH_PRESSURE,
                            severity=Severity.ERROR,
                            message="Launcher nominal pressure must be within [10.0, 13.5] bar.",
                            matched_text=m_nom.group(0),
                            expected_value="10.0 bar (nominal) / [10.0, 13.5] bar",
                            actual_value=f"{val} bar",
                            suggestion="attribute nominalPressure_bar : Real default 10.0;",
                            snippet=line_str,
                        )
                    )

            # Check maxPressure_bar range [13.5, 14.0]
            m_max = re.search(r"attribute\s+maxPressure_bar\s*:\s*Real\s*default\s*([0-9]+\.?[0-9]*);", line_str)
            if m_max:
                val = float(m_max.group(1))
                if val < 13.5 - 0.05 or val > 14.0 + 0.05:
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.PARAMETRIC_LAUNCH_PRESSURE,
                            severity=Severity.ERROR,
                            message="Launcher max pressure must be within [13.5, 14.0] bar.",
                            matched_text=m_max.group(0),
                            expected_value="13.5 - 14.0 bar",
                            actual_value=f"{val} bar",
                            suggestion="attribute maxPressure_bar : Real default 14.0;",
                            snippet=line_str,
                        )
                    )

        return findings

    @classmethod
    def _audit_markdown(cls, lines: List[str], rel_path: str) -> List[Finding]:
        findings: List[Finding] = []

        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("<!--"):
                continue

            cleaned_line = clean_latex(line_str)

            # 1. Wingspan checking
            for pat in [cls.RE_WINGSPAN_MD, cls.RE_WINGSPAN_ALT_MD, cls.RE_WINGSPAN_PARAM_MD]:
                for m in pat.finditer(cleaned_line):
                    try:
                        val = float(m.group(1))
                    except ValueError:
                        continue
                    if abs(val - GroundTruth.WINGSPAN_M) > 0.05:
                        findings.append(
                            Finding(
                                file_path=rel_path,
                                line_number=line_num,
                                category=FindingCategory.PARAMETRIC_WINGSPAN,
                                severity=Severity.ERROR,
                                message=f"Contradicts wingspan ground-truth invariant (expected 1.8 m, found {val} m).",
                                matched_text=m.group(0),
                                expected_value="1.8 m",
                                actual_value=f"{val} m",
                                suggestion="Set wingspan to 1.8 m (1.80 m).",
                                snippet=line_str,
                            )
                        )

            # 2. MTOW / MTOM checking
            for pat in [cls.RE_MTOW_MD, cls.RE_MTOW_ALT_MD, cls.RE_MTOW_LATEX_MD]:
                for m in pat.finditer(cleaned_line):
                    matched = m.group(0)
                    try:
                        val = float(m.group(1))
                    except ValueError:
                        continue

                    # Ignore valid operational payload mass / battery mass statements if not claiming to be MTOW
                    if "payload" in line_str.lower() and "mtow" not in matched.lower() and "mtom" not in matched.lower() and "maximum take-off" not in matched.lower():
                        continue
                    if "battery" in line_str.lower() and "mtow" not in matched.lower() and "mtom" not in matched.lower() and "maximum take-off" not in matched.lower():
                        continue
                    if "carriage" in line_str.lower() and "mtow" not in matched.lower() and "mtom" not in matched.lower() and "maximum take-off" not in matched.lower():
                        continue

                    if abs(val - GroundTruth.MTOW_KG) > 0.1:
                        findings.append(
                            Finding(
                                file_path=rel_path,
                                line_number=line_num,
                                category=FindingCategory.PARAMETRIC_MTOW,
                                severity=Severity.ERROR,
                                message=f"Contradicts Maximum Take-Off Mass (MTOW) ground-truth invariant (expected 17.0 kg, found {val} kg).",
                                matched_text=m.group(0),
                                expected_value="17.0 kg",
                                actual_value=f"{val} kg",
                                suggestion="Set platform MTOW to 17.0 kg.",
                                snippet=line_str,
                            )
                        )

            # 3. Stall Speed checking
            for pat in [cls.RE_STALL_SPEED_MD, cls.RE_STALL_SPEED_TABLE]:
                for m in pat.finditer(cleaned_line):
                    try:
                        val = float(m.group(1))
                    except ValueError:
                        continue
                    if abs(val - GroundTruth.STALL_SPEED_MPS) > 0.1:
                        findings.append(
                            Finding(
                                file_path=rel_path,
                                line_number=line_num,
                                category=FindingCategory.PARAMETRIC_STALL_SPEED,
                                severity=Severity.ERROR,
                                message=f"Contradicts aerodynamic stall speed (V_s) ground-truth invariant (expected 24.0 m/s, found {val} m/s).",
                                matched_text=m.group(0),
                                expected_value="24.0 m/s",
                                actual_value=f"{val} m/s",
                                suggestion="Set stall speed to 24.0 m/s.",
                                snippet=line_str,
                            )
                        )

            # 4. Cruise Speed checking
            for m in cls.RE_CRUISE_SPEED_MD.finditer(cleaned_line):
                try:
                    val = float(m.group(1))
                except ValueError:
                    continue
                # If line contains obsolete value and an explicit SSOT correction annotation, note warning or error
                if abs(val - GroundTruth.CRUISE_SPEED_MPS) > 0.1:
                    is_annotated = "sysml ssot: 31.0" in line_str.lower()
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.PARAMETRIC_CRUISE_SPEED,
                            severity=Severity.WARNING if is_annotated else Severity.ERROR,
                            message=f"Cruise speed mismatch (expected 31.0 m/s, found {val} m/s).",
                            matched_text=m.group(0),
                            expected_value="31.0 m/s",
                            actual_value=f"{val} m/s",
                            suggestion="Update cruise speed to 31.0 m/s in accordance with SysML SSOT.",
                            snippet=line_str,
                        )
                    )

            # 5. Max Speed checking
            for m in cls.RE_MAX_SPEED_MD.finditer(cleaned_line):
                # Ignore dive speed if explicitly noted as dive
                if "dive" in line_str.lower() and "horizontal" not in line_str.lower() and "level" not in line_str.lower():
                    continue
                try:
                    val = float(m.group(1))
                except ValueError:
                    continue
                if abs(val - GroundTruth.MAX_SPEED_MPS) > 0.1:
                    is_annotated = "sysml ssot: 42.0" in line_str.lower()
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.PARAMETRIC_MAX_SPEED,
                            severity=Severity.WARNING if is_annotated else Severity.ERROR,
                            message=f"Max horizontal speed mismatch (expected 42.0 m/s, found {val} m/s).",
                            matched_text=m.group(0),
                            expected_value="42.0 m/s",
                            actual_value=f"{val} m/s",
                            suggestion="Update max horizontal speed to 42.0 m/s in accordance with SysML SSOT.",
                            snippet=line_str,
                        )
                    )

            # 6. Launch Speed checking
            for m in cls.RE_LAUNCH_SPEED_MD.finditer(cleaned_line):
                try:
                    val = float(m.group(1))
                except ValueError:
                    continue
                if val < GroundTruth.LAUNCH_SPEED_MPS - 0.1 or val > 32.1:
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.PARAMETRIC_LAUNCH_SPEED,
                            severity=Severity.ERROR,
                            message=f"Launch/exit airspeed out of certified envelope (expected >= 26.0 m/s, found {val} m/s).",
                            matched_text=m.group(0),
                            expected_value=">= 26.0 m/s (nominal 26.0--26.5 m/s)",
                            actual_value=f"{val} m/s",
                            suggestion="Set catapult exit airspeed to >= 26.0 m/s.",
                            snippet=line_str,
                        )
                    )

        return findings


# ==============================================================================
# Ungrounded AI / Deep Learning Buzzword Auditor
# ==============================================================================

class AIBuzzwordAuditor:
    """Audits files for ungrounded machine learning and deep learning assumptions."""

    COMPILED_PATTERNS = [
        (re.compile(pat, re.IGNORECASE), name, desc)
        for pat, name, desc in UNGROUNDED_BUZZWORDS
    ]

    @classmethod
    def audit_file(cls, file_path: str, content: str, rel_path: str) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("<!--"):
                continue

            for pat, name, desc in cls.COMPILED_PATTERNS:
                m = pat.search(line_str)
                if m:
                    findings.append(
                        Finding(
                            file_path=rel_path,
                            line_number=line_num,
                            category=FindingCategory.UNGROUNDED_AI_BUZZWORD,
                            severity=Severity.ERROR,
                            message=(
                                f"Ungrounded AI/ML assumption '{name}' detected. Optical tracking and guidance "
                                f"must use classical 2D Kalman point/centroid tracking with Mahalanobis innovation "
                                f"gating on embedded companion hardware (A5 User Manual §11.4 & §12)."
                            ),
                            matched_text=m.group(0),
                            expected_value="Classical 2D Kalman Filter + Mahalanobis Innovation Gating",
                            actual_value=m.group(0),
                            suggestion=(
                                f"Replace '{name}' with deterministic embedded algorithms (classical 2D Kalman filter, "
                                f"Mahalanobis distance innovation gating, or companion processor image processing buffers)."
                            ),
                            snippet=line_str,
                        )
                    )

        return findings


# ==============================================================================
# Ground-Truth Source Citation Auditor
# ==============================================================================

class SourceCitationAuditor:
    """Audits feature specifications for authoritative source citations and validity of schema links."""

    RE_MD_LINKS = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
    RE_PLACEHOLDER = re.compile(r"\[(link-to-schema|link-to-specification|link-to-normative-source)\]", re.IGNORECASE)

    @classmethod
    def audit_feature_spec(cls, file_path: str, content: str, rel_path: str, repo_root: Path) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        # 1. Verify presence of at least one authoritative ground-truth source
        cited_sources: Set[str] = set()
        for doc_key, aliases in AUTHORITATIVE_SOURCES.items():
            for alias in aliases:
                if alias in content:
                    cited_sources.add(doc_key)
                    break

        if not cited_sources:
            findings.append(
                Finding(
                    file_path=rel_path,
                    line_number=1,
                    category=FindingCategory.GROUND_TRUTH_CITATION,
                    severity=Severity.ERROR,
                    message=(
                        f"Feature specification '{os.path.basename(file_path)}' does not cite any authoritative "
                        f"ground-truth source documents."
                    ),
                    matched_text="No authoritative source cited",
                    expected_value=(
                        "At least one authoritative source: schema/extracted/A5_user_manual_full.md, "
                        "schema/AVENGER 5 Spec sheet_rev3.pdf, schema/A5_prep and safety_rev7.pdf, "
                        "schema/ESAD ICD_for Excalibur_AB00-0054-01AA-0005 2 1.pdf, or schema/Avenger5.sysml"
                    ),
                    actual_value="None",
                    suggestion=(
                        "Add citation in header metadata and '## Source References' block referencing "
                        "the applicable authoritative schema/extracted documents."
                    ),
                    snippet=lines[0] if lines else "",
                )
            )

        # 2. Audit markdown links and placeholders in the file
        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()

            # Check placeholders
            m_place = cls.RE_PLACEHOLDER.search(line_str)
            if m_place:
                findings.append(
                    Finding(
                        file_path=rel_path,
                        line_number=line_num,
                        category=FindingCategory.GROUND_TRUTH_CITATION,
                        severity=Severity.ERROR,
                        message=f"Unresolved template placeholder '{m_place.group(0)}' found in source references.",
                        matched_text=m_place.group(0),
                        expected_value="Concrete path to authoritative source document",
                        actual_value=m_place.group(0),
                        suggestion="Replace template placeholder with concrete link to schema or manual.",
                        snippet=line_str,
                    )
                )

            # Check schema links for existence
            for m_link in cls.RE_MD_LINKS.finditer(line_str):
                link_text, link_target = m_link.groups()
                # If target references a schema or extracted document
                if "schema/" in link_target:
                    # Resolve relative target
                    file_dir = Path(file_path).parent
                    target_path = (file_dir / link_target).resolve()
                    # Also check relative to repo root
                    repo_rel_target = (repo_root / link_target.lstrip("./")).resolve()

                    if not target_path.exists() and not repo_rel_target.exists():
                        findings.append(
                            Finding(
                                file_path=rel_path,
                                line_number=line_num,
                                category=FindingCategory.GROUND_TRUTH_CITATION,
                                severity=Severity.ERROR,
                                message=f"Cited schema file '{link_target}' does not exist on disk.",
                                matched_text=m_link.group(0),
                                expected_value="Existing file in schema/ or schema/extracted/",
                                actual_value=link_target,
                                suggestion="Verify file path and update link to existing schema artifact.",
                                snippet=line_str,
                            )
                        )

        return findings


# ==============================================================================
# Scanner Engine
# ==============================================================================

class HallucinationScanner:
    """Orchestrates comprehensive anti-hallucination scanning."""

    def __init__(self, repo_root: Path, target_paths: Optional[List[str]] = None):
        self.repo_root = repo_root.resolve()
        self.target_paths = target_paths or []
        self.files_to_scan: List[Path] = []
        self.findings: List[Finding] = []

    def discover_files(self) -> List[Path]:
        """Discovers all markdown files in docs/ and schema/Avenger5.sysml."""
        if self.target_paths:
            resolved = []
            for p in self.target_paths:
                path_obj = Path(p)
                if not path_obj.is_absolute():
                    path_obj = self.repo_root / path_obj
                if path_obj.is_file():
                    resolved.append(path_obj)
                elif path_obj.is_dir():
                    resolved.extend(path_obj.glob("**/*.md"))
                    resolved.extend(path_obj.glob("**/*.sysml"))
            self.files_to_scan = sorted(list(set(resolved)))
            return self.files_to_scan

        docs_dir = self.repo_root / "docs"
        schema_dir = self.repo_root / "schema"

        files: List[Path] = []
        if docs_dir.exists():
            for md_file in docs_dir.glob("**/*.md"):
                if any(p in md_file.parts for p in ("defects", "audits", "decisions", "designs")):
                    continue
                files.append(md_file)

        sysml_file = schema_dir / "Avenger5.sysml"
        if sysml_file.exists():
            files.append(sysml_file)

        # Include other sysml files under schema if present
        if schema_dir.exists():
            for sf in schema_dir.glob("*.sysml"):
                if sf not in files:
                    files.append(sf)

        self.files_to_scan = sorted(list(set(files)))
        return self.files_to_scan

    def run(self) -> List[Finding]:
        """Executes all checks across discovered files."""
        if not self.files_to_scan:
            self.discover_files()

        self.findings = []
        for file_path in self.files_to_scan:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
                continue

            try:
                rel_path = str(file_path.relative_to(self.repo_root))
            except ValueError:
                rel_path = str(file_path)

            # 1. Parametric consistency check
            self.findings.extend(ParametricAuditor.audit_file(str(file_path), content, rel_path))

            # 2. Ungrounded AI / deep learning buzzword check
            self.findings.extend(AIBuzzwordAuditor.audit_file(str(file_path), content, rel_path))

            # 3. Ground-truth source citation check (features and all docs)
            if "/docs/features/" in rel_path or rel_path.startswith("docs/features/"):
                self.findings.extend(
                    SourceCitationAuditor.audit_feature_spec(str(file_path), content, rel_path, self.repo_root)
                )

        return self.findings

    def generate_report(self, json_report_path: Optional[str] = None, show_fix: bool = False) -> Dict[str, Any]:
        """Generates console output and structured JSON report."""
        error_count = sum(1 for f in self.findings if f.severity == Severity.ERROR)
        warning_count = sum(1 for f in self.findings if f.severity == Severity.WARNING)

        report = {
            "summary": {
                "scanned_files_count": len(self.files_to_scan),
                "total_findings": len(self.findings),
                "error_count": error_count,
                "warning_count": warning_count,
                "passed": error_count == 0,
            },
            "findings": [f.to_dict() for f in self.findings],
        }

        if json_report_path:
            out_p = Path(json_report_path)
            if not out_p.is_absolute():
                out_p = self.repo_root / out_p
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as jf:
                json.dump(report, jf, indent=2)
            print(f"Structured JSON audit report written to: {out_p}")

        return report


# ==============================================================================
# Console Presentation & Formatting
# ==============================================================================

def print_audit_report(scanner: HallucinationScanner, show_fix: bool = False):
    findings = scanner.findings
    scanned_count = len(scanner.files_to_scan)
    error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
    warning_count = sum(1 for f in findings if f.severity == Severity.WARNING)

    print("=" * 80)
    print(" 🦅 AVENGER 5 (UAS-003) ANTI-HALLUCINATION & GROUND-TRUTH CITATION AUDIT")
    print("=" * 80)
    print(f" Scanned Files : {scanned_count}")
    print(f" Violations    : {error_count} Errors, {warning_count} Warnings")
    print("-" * 80)

    if not findings:
        print(" ✅ 100% CLEAN - All specifications conform to ground-truth invariants,")
        print("    contain zero ungrounded AI buzzwords, and properly cite authoritative manuals.")
        print("=" * 80)
        return

    # Group findings by file
    findings_by_file: Dict[str, List[Finding]] = {}
    for f in findings:
        findings_by_file.setdefault(f.file_path, []).append(f)

    for file_path, file_findings in sorted(findings_by_file.items()):
        print(f"\n📄 {file_path}")
        for idx, f in enumerate(file_findings, 1):
            sev_badge = "🔴 ERROR" if f.severity == Severity.ERROR else "🟡 WARN"
            print(f"  [{sev_badge}] Line {f.line_number} | {f.category.value}")
            print(f"    Issue   : {f.message}")
            print(f"    Matched : \"{f.matched_text}\"")
            print(f"    Expected: {f.expected_value}")
            if f.actual_value:
                print(f"    Actual  : {f.actual_value}")
            print(f"    Snippet : {f.snippet}")
            if show_fix or f.suggestion:
                print(f"    💡 Fix  : {f.suggestion}")
            print()

    print("=" * 80)
    if error_count > 0:
        print(f" ❌ AUDIT FAILED: {error_count} ungrounded claims/violations must be rectified.")
    else:
        print(f" ⚠️ AUDIT PASSED WITH WARNINGS ({warning_count} warnings).")
    print("=" * 80)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Audit specifications and SysML for ungrounded claims, parametric consistency, and citations."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional specific file or directory targets to scan (defaults to docs/ and schema/Avenger5.sysml).",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Root path of the repository (default: auto-detected).",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help="Optional path to output a structured JSON findings report.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Display actionable remediation suggestions and replacement snippets for all violations.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: treat warnings as failures (exit 1 on warnings).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )

    args = parser.parse_args()

    # Detect repo root
    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        # Step up from scripts/ to repo root
        repo_root = Path(__file__).resolve().parent.parent

    scanner = HallucinationScanner(repo_root=repo_root, target_paths=args.targets)
    scanner.discover_files()
    findings = scanner.run()

    # Generate JSON report if requested
    report = scanner.generate_report(json_report_path=args.json_report, show_fix=args.fix)

    # Print human-readable report
    print_audit_report(scanner, show_fix=args.fix)

    # Exit code determination
    error_count = report["summary"]["error_count"]
    warning_count = report["summary"]["warning_count"]

    if error_count > 0:
        sys.exit(1)
    if args.strict and warning_count > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
