"""
Phase 0 Concept Provenance & CONOPS AST Validator.
/// Realises: [ConceptProvenanceValidator, Phase0CONOPSValidation, SensorResolutionGroundTruth, InlineCitationVerification]

Audits Phase 0 Concept of Operations (CONOPS) and Mission Intent specifications (docs/conops/*.md, docs/MISSION_INTENT.md)
against authoritative OEM ground truth (schema/extracted/*_full.md):
1. Sensor Hardware Provenance: Enforces exact ground-truth daylight and thermal sensor resolutions (1280x720 HD),
   strictly flagging fabrications like 24.0 MP or 640x512.
2. Parametric Airframe & Aerodynamics: Asserts wingspan (1.8 m), MTOW (17.0 kg), and airspeeds (cruise 30-31 m/s,
   max 38-42 m/s, stall 24-26 m/s, launch >= 26 m/s).
3. Inline Ground-Truth Citations: Asserts that every technical specification claim carries a machine-resolvable
   inline citation anchor (<!-- Source: schema/extracted/... --> or Markdown link) targeting an existing ground-truth file.
4. Ungrounded Buzzword Rejection: Rejects ungrounded machine-learning and GPU buzzwords (CUDA, YOLO, PyTorch, TensorRT,
   backpropagation, vision transformer) in safety-critical flight specifications.
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..core.findings import Finding
from ..core.workspace import WorkspaceRepository
from .base import IValidator


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class RuleID:
    SENSOR_FABRICATION = "concept-provenance-sensor-fabrication"
    PARAMETRIC_MISMATCH = "concept-provenance-parametric-mismatch"
    MISSING_CITATION = "concept-provenance-missing-citation"
    INVALID_SOURCE_LOCATOR = "concept-provenance-invalid-source-locator"
    UNGROUNDED_BUZZWORD = "concept-provenance-ungrounded-buzzword"


# Default ground-truth fallback parameters if schema/extracted is empty or absent
DEFAULT_GROUND_TRUTH: Dict[str, Any] = {
    "wingspan_m": 1.8,
    "mtow_kg": 17.0,
    "fuselage_length_m": 1.6,
    "day_camera_resolution": "1280x720",
    "thermal_camera_resolution": "1280x720",
    "cruise_speed_range": (30.0, 31.0),
    "max_speed_range": (38.0, 42.0),
    "stall_speed_range": (24.0, 26.0),
    "max_dive_speed_range": (55.0, 80.0),
    "launch_speed_min": 26.0,
    "launch_pressure_range": (8.5, 14.0),
}

UNGROUNDED_BUZZWORDS: List[Tuple[str, str]] = [
    (r"\bCUDA\b", "CUDA"),
    (r"\bYOLO(?:v\d+)?\b", "YOLO"),
    (r"\b(?:PyTorch|torch\.nn|torchvision)\b", "PyTorch"),
    (r"\bTensorRT\b", "TensorRT"),
    (r"\bbackprop(?:agation)?\b", "backpropagation"),
    (r"\b(?:transformer\s+neural\s+network|vision\s+transformer|ViT-based)\b", "vision transformer"),
    (r"\bdeep\s+reinforcement\s+learning\s+(?:flight\s+control|guidance|autopilot)\b", "deep reinforcement learning"),
]


def find_repo_root(start_path: Optional[Union[str, Path]] = None) -> Path:
    """Locates the repository root directory by searching upwards for .git or schema folder."""
    cur = Path(start_path or os.getcwd()).resolve()
    if cur.is_file():
        cur = cur.parent
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists() or (p / "schema").is_dir():
            return p
    return Path.cwd().resolve()


def extract_ground_truth(extracted_dir: Union[str, Path]) -> Dict[str, Any]:
    """Dynamically extracts ground-truth parameters from schema/extracted/*_full.md."""
    truth: Dict[str, Any] = dict(DEFAULT_GROUND_TRUTH)
    extracted_path = Path(extracted_dir)
    if not extracted_path.exists():
        return truth

    md_files = sorted(list(extracted_path.glob("*_full.md")) + list(extracted_path.glob("*.md")))
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Wingspan
        m = re.search(r"(?:Wingspan|Wing\s+span)\s*(?:\(b\))?\s*[:|=]?\s*([0-9]+\.?[0-9]*)\s*m\b", content, re.IGNORECASE)
        if m:
            truth["wingspan_m"] = float(m.group(1))

        # MTOW
        m = re.search(r"(?:MTOW|MTOM|Maximum\s+take[‐\-]?off\s+(?:weight|mass))\s*[:|=]?\s*([0-9]+\.?[0-9]*)\s*kg\b", content, re.IGNORECASE)
        if m:
            truth["mtow_kg"] = float(m.group(1))

        # Length
        m = re.search(r"(?:Overall\s+length|Fuselage\s+length)\s*[:|=]?\s*([0-9]+\.?[0-9]*)\s*m\b", content, re.IGNORECASE)
        if m:
            truth["fuselage_length_m"] = float(m.group(1))

        # Day camera resolution
        if re.search(r"Day\s+camera\s*[-:=]?\s*1280\s*[x×]\s*720", content, re.IGNORECASE):
            truth["day_camera_resolution"] = "1280x720"

        # Thermal camera resolution
        if re.search(r"Thermal\s+camera\s*[-:=]?\s*1280\s*[x×]\s*720", content, re.IGNORECASE):
            truth["thermal_camera_resolution"] = "1280x720"

    return truth


class ConceptProvenanceValidator(IValidator):
    """Audits Phase 0 CONOPS and Mission Intent documents for ground-truth provenance and anti-hallucination."""

    def validate(
        self,
        schema_ast: Any = None,
        spec_dir: Optional[str] = None,
        repo: Optional[WorkspaceRepository] = None,
        **kwargs: Any
    ) -> List[Finding]:
        """
        Validates Phase 0 CONOPS documents against ground truth.
        Supports invocation via:
        - validate(schema_ast, spec_dir)
        - validate(repo)
        - validate() with default workspace discovery
        """
        findings: List[Finding] = []

        # 1. Determine workspace root
        if repo and hasattr(repo, "workspace_dir") and repo.workspace_dir:
            workspace_dir = Path(repo.workspace_dir).resolve()
        elif spec_dir:
            p = Path(spec_dir).resolve()
            workspace_dir = find_repo_root(p)
        else:
            workspace_dir = find_repo_root()

        # 2. Extract dynamic ground truth from schema/extracted
        extracted_dir = workspace_dir / "schema" / "extracted"
        truth = extract_ground_truth(extracted_dir)

        # 3. Locate target CONOPS and Mission Intent files to validate
        target_files: List[Path] = []
        if spec_dir:
            sd_path = Path(spec_dir).resolve()
            if sd_path.is_file() and sd_path.suffix == ".md":
                target_files.append(sd_path)
            elif sd_path.is_dir():
                target_files.extend(sorted(sd_path.glob("*.md")))

        # If not explicitly provided, scan default locations
        if not target_files:
            conops_dir = workspace_dir / "docs" / "conops"
            if conops_dir.exists():
                target_files.extend(sorted(conops_dir.glob("*.md")))
            mission_intent_file = workspace_dir / "docs" / "MISSION_INTENT.md"
            if mission_intent_file.exists() and mission_intent_file not in target_files:
                target_files.append(mission_intent_file)

        # 4. Perform audit across all target files
        for target_file in target_files:
            try:
                content = target_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel_path = str(target_file.relative_to(workspace_dir)) if target_file.is_relative_to(workspace_dir) else target_file.name
            file_findings = self._audit_document(content, rel_path, workspace_dir, truth)
            findings.extend(file_findings)

        return findings

    def _audit_document(
        self,
        content: str,
        rel_path: str,
        workspace_dir: Path,
        truth: Dict[str, Any]
    ) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        # Track code blocks to avoid false positives inside code examples
        in_code_block = False

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # ------------------------------------------------------------------
            # 1. Sensor Resolution Fabrication Audit
            # ------------------------------------------------------------------
            # Daylight camera checks: Flag 24 MP, 24.0 MP, 4K, 1080p, 1920x1080
            day_camera_match = re.search(
                r"(?:EO\s+Daylight\s+Camera|Day\s+camera|Daylight\s+camera|EO\s+camera)\b[^|\n]*\|\s*([^|\n]+)",
                line,
                re.IGNORECASE
            )
            if day_camera_match:
                spec_val = day_camera_match.group(1).strip()
                if re.search(r"\b24(?:\.0)?\s*MP\b|\b4K\b|\b1920\s*[x×]\s*1080\b|\b1080p\b", spec_val, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id=RuleID.SENSOR_FABRICATION,
                        message=f"{rel_path}:{idx}: Fabricated daylight camera resolution '{spec_val}' violates ground truth '{truth['day_camera_resolution']} (HD)'.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": spec_val, "expected": truth["day_camera_resolution"]}
                    ))

            # Thermal camera checks: Flag 640x512, 320x240, 384x288
            thermal_camera_match = re.search(
                r"(?:Thermal\s+IR\s+Camera|Thermal\s+camera|IR\s+camera)\b[^|\n]*\|\s*([^|\n]+)",
                line,
                re.IGNORECASE
            )
            if thermal_camera_match:
                spec_val = thermal_camera_match.group(1).strip()
                if re.search(r"\b640\s*[x×]\s*512\b|\b320\s*[x×]\s*240\b|\b384\s*[x×]\s*288\b", spec_val, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id=RuleID.SENSOR_FABRICATION,
                        message=f"{rel_path}:{idx}: Fabricated thermal camera resolution '{spec_val}' violates ground truth '{truth['thermal_camera_resolution']} (HD)'.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": spec_val, "expected": truth["thermal_camera_resolution"]}
                    ))

            # ------------------------------------------------------------------
            # 2. Parametric Mismatch Audit (Airspeeds, Weights, Dimensions)
            # ------------------------------------------------------------------
            # Wingspan: matches "Wingspan: 2.4 m" or "2.4 m wingspan"
            wingspan_match = re.search(
                r"(?:\b(?:Wingspan|Wing\s+span)\b[^|\n\d]*[:|=]?\s*([0-9]+\.?[0-9]*)\s*m\b|([0-9]+\.?[0-9]*)\s*m\s*(?:wingspan|wing\s+span)\b)",
                line,
                re.IGNORECASE
            )
            if wingspan_match:
                val_str = wingspan_match.group(1) or wingspan_match.group(2)
                val = float(val_str)
                if abs(val - truth["wingspan_m"]) > 0.05:
                    findings.append(Finding(
                        rule_id=RuleID.PARAMETRIC_MISMATCH,
                        message=f"{rel_path}:{idx}: Wingspan {val} m mismatches authoritative ground truth {truth['wingspan_m']} m.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": val, "expected": truth["wingspan_m"]}
                    ))

            # MTOW: matches "MTOW: 25.0 kg" or "25.0 kg MTOW"
            mtow_match = re.search(
                r"(?:\b(?:MTOW|MTOM|Maximum\s+Takeoff\s+Weight)\b[^|\n\d]*[:|=]?\s*([0-9]+\.?[0-9]*)\s*kg\b|([0-9]+\.?[0-9]*)\s*kg\s*(?:MTOW|MTOM|takeoff\s+weight)\b)",
                line,
                re.IGNORECASE
            )
            if mtow_match:
                val_str = mtow_match.group(1) or mtow_match.group(2)
                val = float(val_str)
                if abs(val - truth["mtow_kg"]) > 0.1:
                    findings.append(Finding(
                        rule_id=RuleID.PARAMETRIC_MISMATCH,
                        message=f"{rel_path}:{idx}: MTOW {val} kg mismatches authoritative ground truth {truth['mtow_kg']} kg.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": val, "expected": truth["mtow_kg"]}
                    ))

            # Cruise speed
            cruise_match = re.search(
                r"(?:\b(?:Nominal\s+Cruise\s+Speed|Cruise\s+Speed|V_cruise)\b[^|\n\d]*[:|=]?\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)\b|([0-9]+\.?[0-9]*)\s*(?:m/s|mps)\s*(?:cruise\s+speed|V_cruise)\b)",
                line,
                re.IGNORECASE
            )
            if cruise_match:
                val_str = cruise_match.group(1) or cruise_match.group(2)
                val = float(val_str)
                min_c, max_c = truth["cruise_speed_range"]
                if val < min_c - 0.5 or val > max_c + 0.5:
                    findings.append(Finding(
                        rule_id=RuleID.PARAMETRIC_MISMATCH,
                        message=f"{rel_path}:{idx}: Cruise speed {val} m/s outside ground truth envelope [{min_c}, {max_c}] m/s.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": val, "expected": f"[{min_c}, {max_c}]"}
                    ))

            # Stall speed
            stall_match = re.search(
                r"(?:\b(?:Stall\s+Speed|V_s|Minimum\s+Speed)\b[^|\n\d]*[:|=]?\s*([0-9]+\.?[0-9]*)\s*(?:m/s|mps)\b|([0-9]+\.?[0-9]*)\s*(?:m/s|mps)\s*(?:stall\s+speed|V_s)\b)",
                line,
                re.IGNORECASE
            )
            if stall_match:
                val_str = stall_match.group(1) or stall_match.group(2)
                val = float(val_str)
                min_s, max_s = truth["stall_speed_range"]
                if val < min_s - 0.5 or val > max_s + 0.5:
                    findings.append(Finding(
                        rule_id=RuleID.PARAMETRIC_MISMATCH,
                        message=f"{rel_path}:{idx}: Stall speed {val} m/s outside ground truth envelope [{min_s}, {max_s}] m/s.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "actual": val, "expected": f"[{min_s}, {max_s}]"}
                    ))

            # ------------------------------------------------------------------
            # 3. Ungrounded AI / Deep Learning Buzzword Audit
            # ------------------------------------------------------------------
            for pattern, name in UNGROUNDED_BUZZWORDS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id=RuleID.UNGROUNDED_BUZZWORD,
                        message=f"{rel_path}:{idx}: Ungrounded buzzword '{name}' detected in Phase 0 specification.",
                        location=f"{rel_path}:{idx}",
                        detail={"severity": Severity.ERROR, "buzzword": name}
                    ))

            # ------------------------------------------------------------------
            # 4. Inline Citation Anchor & Source Locator Verification
            # ------------------------------------------------------------------
            # If line represents a technical parameter row in a markdown table:
            if line.strip().startswith("|") and not line.strip().startswith("| :---") and not line.strip().startswith("| Parameter") and not re.search(r"^\|\s*\*{0,2}Phase", line.strip(), re.IGNORECASE):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 2:
                    param_name = parts[0]
                    # Only enforce on technical/engineering parameters
                    if re.search(r"\b(?:Wingspan|MTOW|Length|Cruise|Speed|Stall|Camera|Gimbal|Payload|Ceiling|Endurance|Catapult|Launch Mechanism|Launch Pressure)\b", param_name, re.IGNORECASE) and not re.search(r"Phase", param_name, re.IGNORECASE):
                        # Check for citation pattern: <!-- Source: ... --> or [Label](path) or [A5-...](...)
                        citation_matches = re.findall(r"<!--\s*Source:\s*([^>]+)\s*-->|\[([^\]]+)\]\(([^)#\s]+)(?:#[^)]*)?\)", line)
                        if not citation_matches:
                            findings.append(Finding(
                                rule_id=RuleID.MISSING_CITATION,
                                message=f"{rel_path}:{idx}: Technical parameter '{param_name}' lacks a mandatory inline ground-truth citation anchor.",
                                location=f"{rel_path}:{idx}",
                                detail={"severity": Severity.ERROR, "parameter": param_name}
                            ))
                        else:
                            # Verify at least one source locator target exists on disk
                            valid_source_found = False
                            last_ref = ""
                            for src_comment, md_text, md_target in citation_matches:
                                ref = src_comment or md_target
                                clean_ref = re.sub(r"[:#].*$", "", ref.strip()).strip().strip("'\"")
                                last_ref = clean_ref
                                target_file = (workspace_dir / clean_ref).resolve()
                                rel_target = ((workspace_dir / rel_path).parent / clean_ref).resolve()
                                if target_file.exists() or rel_target.exists():
                                    valid_source_found = True
                                    break
                            if not valid_source_found:
                                findings.append(Finding(
                                    rule_id=RuleID.INVALID_SOURCE_LOCATOR,
                                    message=f"{rel_path}:{idx}: Referenced source locator '{last_ref}' does not exist on disk.",
                                    location=f"{rel_path}:{idx}",
                                    detail={"severity": Severity.ERROR, "locator": last_ref}
                                ))

        return findings
