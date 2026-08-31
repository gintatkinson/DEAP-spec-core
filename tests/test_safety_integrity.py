"""
Safety Integrity Quality Gate & SORA OSO-01..24 Completeness Verification Suite.
/// Realises: [SafetyIntegrityQualityGate, SORACompleteness, ASTM_F3269_RTA, STPALossScenariosSetEquality, QuantitativeFMECAValidation]
"""
import os
import re
import sys
import tempfile
import pytest

# Ensure scripts directory and parity_auditor are in sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

parity_src = os.path.join(repo_root, "skills", "spec-orchestrator", "parity_auditor", "src")
if parity_src not in sys.path:
    sys.path.insert(0, parity_src)

from scripts.verify_downstream_baseline import (
    count_fmeca_rows,
    check_uca_categories,
    check_sora_osos,
    validate_safety_matrix_content,
    check_safety_integrity_and_sora_completeness,
)
from parity_auditor.validators.safety_trace_validator import (
    SafetyTraceValidator,
    EXPECTED_LOSS_SCENARIOS,
    extract_loss_scenarios,
    parse_fmeca_modes,
    parse_spof_rows,
    parse_ucas,
)
from parity_auditor.core.workspace import WorkspaceRepository

# Canonical list of 22 physical subsystems and alpha fraction distributions summing to exactly 1.0
FMECA_22_COMPONENTS = [
    ("Fuselage Structure", "Fuselage", 8.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("Wing Assembly", "WingAssembly", 10.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("Elevon Actuator", "ElevonActuator", 20.0, [0.12, 0.10, 0.10, 0.08, 0.10, 0.08, 0.08, 0.08, 0.08, 0.06, 0.06, 0.06]),
    ("Electric Motor", "ElectricMotor", 12.5, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("Pusher Propeller", "Propeller", 9.0, [0.15, 0.12, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.07, 0.07, 0.07]),
    ("Electronic Speed Controller", "ElectronicSpeedController", 18.0, [0.12, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.06, 0.06]),
    ("6S LiPo Battery Pack", "LiPoBatteryPack", 15.0, [0.12, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.06, 0.06]),
    ("Power Management Unit", "PowerManagementUnit", 14.0, [0.12, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.06, 0.06]),
    ("Flight Controller CPU", "FlightControllerCPU", 22.0, [0.12, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.06, 0.06]),
    ("Dual 6-DOF IMU Suite", "DualIMUSuite", 16.0, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("Barometer & Pitot Sensor", "BarometerAirspeedSensor", 13.5, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("RTK GNSS Receiver", "RTKGNSSReceiver", 15.5, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("DAA / ADS-B In Receiver", "SurveillanceReceiver", 14.5, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("C2 Telemetry Transceiver", "C2Transceiver", 16.5, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("Antenna Rotator Subsystem", "AntennaRotatorSubsystem", 16.0, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("Operator Tablet / Virtual Joystick", "PanasonicFZG2Tablet", 19.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("Optical Seeker Payload", "OpticalSeekerPayload", 17.0, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("Multitrack Target Tracker", "MultitrackTargetTracker", 15.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("Dead-Reckoning Navigation Unit", "DeadReckoningNavUnit", 14.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("ASTM F3269-17 RTA Safety Monitor", "RTAMonitor", 8.0, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
    ("PL-40 Catapult Launcher", "PL40CatapultLauncher", 12.0, [0.15, 0.12, 0.10, 0.08, 0.10, 0.10, 0.08, 0.07, 0.06, 0.08, 0.06]),
    ("PL-40 Umbilical Connector", "UmbilicalConnector", 8.5, [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]),
]


def generate_valid_stpa_matrix_content(
    loss_scenario_count: int = 40,
    fmeca_row_count: int = 240,
    include_all_osos: bool = True,
    spof_status: str = "ELIMINATED",
    missing_scenario_id: int = None,
) -> str:
    """Generate a fully conforming 8-pillar STPA / FMECA / SORA specification document string."""
    # 1. Loss scenarios (LS-01 through LS-40)
    ls_rows = []
    for i in range(1, loss_scenario_count + 1):
        if missing_scenario_id is not None and i == missing_scenario_id:
            continue
        ls_rows.append(
            f"| **LS-{i:02d}** | Multi-Factor Scenario {i} | UCA-01, UCA-02 | H-1, L-1 | Causal chain mechanism for scenario {i} under environmental and hardware dynamics. | **SC-01, SC-02** |"
        )
    ls_table_str = "\n".join(ls_rows)

    # 2. FMECA failure mode rows across 22 components
    fmeca_rows = []
    mode_idx = 1
    for comp_name, part_ref, lambda_p, alphas in FMECA_22_COMPONENTS:
        for a_idx, alpha in enumerate(alphas, 1):
            if len(fmeca_rows) >= fmeca_row_count:
                break
            beta = 0.80
            s = 4
            p = 2
            d = 2
            rpn = s * p * d
            fmeca_rows.append(
                f"| **{comp_name}** (`{part_ref}`) | Failure Mode {mode_idx} | α = {alpha:.2f} | Physical mechanism {mode_idx} | Local effect {mode_idx} | Subsystem effect {mode_idx} | System effect {mode_idx} | {lambda_p:.1f} | β = {beta:.2f} | Class 4 | {s} | {p} | {d} | **{rpn}** | Redundant architecture mitigation (SC-01). | 2 | 1 | 1 | **2** |"
            )
            mode_idx += 1
        if len(fmeca_rows) >= fmeca_row_count:
            break

    # If extra rows requested beyond standard 240
    while len(fmeca_rows) < fmeca_row_count:
        fmeca_rows.append(
            f"| **Fuselage Structure** (`Fuselage`) | Synthetic Mode {mode_idx} | α = 0.01 | Mech {mode_idx} | Local {mode_idx} | Next {mode_idx} | End {mode_idx} | 8.0 | β = 0.80 | Class 4 | 4 | 2 | 2 | **16** | Mitigations (SC-01). | 2 | 1 | 1 | **2** |"
        )
        mode_idx += 1

    fmeca_table_str = "\n".join(fmeca_rows)

    # 3. SPOF elimination table for all 22 components
    spof_rows = []
    for idx, (comp_name, part_ref, _, _) in enumerate(FMECA_22_COMPONENTS, 1):
        spof_rows.append(
            f"| **{idx}. {comp_name}** (`{part_ref}`) | Potential SPOF for {comp_name} | High-g load fatigue | Redundant dual architecture | Dual Load Path Redundancy | Invariant proof holds strictly | **{spof_status}** |"
        )
    spof_table_str = "\n".join(spof_rows)

    # 4. SORA OSOs (OSO-01 through OSO-24)
    osos_list = [f"- **OSO-{i:02d}**: Robustness Level High / Satisfied via Architecture" for i in range(1, 25)]
    if not include_all_osos:
        osos_list = osos_list[:-2]  # Remove OSO-23 and OSO-24
    osos_str = "\n".join(osos_list)

    header_suffix = "(OSO-01 through OSO-24)" if include_all_osos else "(Partial OSO Set)"

    return rf"""# STPA Safety Analysis, FMECA Matrix & SORA SAIL Assessment

> **Primary Commercial Toolchain Integration Context:** MATLAB / Simulink / Stateflow / Embedded Coder  
> **Safety Standards:** JARUS SORA v2.5 | ASTM F3269-17 RTA | RTCA DO-365B  

---

## 1. System Losses (**L-1..N**)

- **L-1**: Loss of human life or severe ground fatal injury.
- **L-2**: Mid-air collision with crewed aircraft.
- **L-3**: Total loss of UAS airframe and critical infrastructure payload.
- **L-4**: Airspace violation or loss of separation.

---

## 2. System Hazards (**H-1..N**)

- **H-1**: Aircraft breaches 3D operational containment geofence boundary.
- **H-2**: Aircraft violates RTCA DO-365B DAA well-clear safety separation.
- **H-3**: Uncontrolled flight termination due to propulsion/actuator loss.
- **H-4**: Loss of flight control authority or wing stall.

---

## 3. Hierarchical Control Structure Topology

The control structure consists of the Remote Pilot in Command (RPIC), Autopilot Flight Controller, ASTM F3269-17 Run-Time Assurance (RTA) Safety Net Monitor, Actuator Servos, and Telemetry Sensor Suite.

```mermaid
flowchart TD
    RPIC["Remote Pilot in Command"] --> Autopilot["Autopilot Flight Controller"]
    Autopilot --> RTA["ASTM F3269-17 RTA Monitor"]
    RTA --> Actuator["Actuator Servos / Flight Surfaces"]
    Sensors["IMU / GPS / DAA Sensors"] --> RTA
    Sensors --> Autopilot
```

---

## 4. Unsafe Control Actions (**UCA-1..N**)

Systematic identification across 4 STPA guide words / failure mode categories:

1. **Not providing causes hazard**:
   - `UCA-01`: Not providing emergency parachute deployment command when uncontrolled descent detected.
2. **Providing causes hazard**:
   - `UCA-02`: Providing motor cutoff command during active low-altitude hover over populated area.
3. **Providing too early, too late, or out of order**:
   - `UCA-03`: Providing collision avoidance maneuver too late after DAA boundary violation.
4. **Stopped too soon or applied too long**:
   - `UCA-04`: Stopped too soon contingency Return-to-Launch climb before reaching minimum safe altitude.

| UCA ID | Controller | Control Action | Guide Word | Operational State / Context | Resulting Hazards | Detailed Unsafe Control Behavior | Governing Safety Constraint |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **UCA-01** | RTA Supervisor | `EngageAutonomousRTL` | Not providing | C2 datalink lost for t >= 30.0 s in BVLOS transit. | H-1, H-4 | UAS continues unguided along last heading without C2 oversight. | **SC-01, SC-06** |
| **UCA-02** | RTA Supervisor | `EngageAutonomousRTL` | Providing | Touchdown flare maneuver at h <= 2.0 m AGL during recovery. | H-3, L-2 | Abrupt throttle spool-up during final contact causes ground crash. | **SC-03, SC-16** |
| **UCA-03** | RTA Supervisor | `EngageAutonomousRTL` | Too late | Battery SoC drops below 20% while in transit. | H-4, L-2 | RTL engaged after Point-of-No-Return. | **SC-05, SC-28** |
| **UCA-04** | RTA Supervisor | `EngageAutonomousRTL` | Stopped too soon | Failsafe transit before reaching recovery waypoint. | H-1, H-4 | RTL disengages prematurely in active corridor. | **SC-01, SC-06** |

---

## 5. Loss Scenarios (**LS-1..N**) & Causal Factors

| Scenario ID | Causal Scenario Title | Associated UCAs | Resulting Hazards | Multi-Factor Causal Chain & Interaction Mechanism | Corrective Safety Constraints |
| :--- | :--- | :--- | :---: | :--- | :--- |
{ls_table_str}

---

## 6. Formal Safety Constraints (**SC-1..N**)

- **SC-01**: The flight control system shall enforce pitch limits between $-15^\circ$ and $+25^\circ$ under all operating conditions.
- **SC-02**: The ASTM F3269-17 RTA Safety Net shall switch to certified safe-state recovery within 50ms of barrier violation.

---

## 2. Exhaustive Component-Level Multi-Mode FMECA Matrix

| Component Name & SysML Part Reference | Failure Mode | Failure Mode Fraction α | Failure Cause & Physical Mechanism | Local Failure Effect | Next Higher Level Failure Effect | End / System-Level Failure Effect | Base Failure Rate λp (/10^6 hr) | Conditional Failure Probability β | Severity Class (1-5) | Initial Severity S | Initial Probability P | Initial Detection D | Initial RPN | Architectural Mitigations & Safety Invariants | Residual S | Residual P | Residual D | Residual RPN |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
{fmeca_table_str}

---

## 5. Single Point of Failure (SPOF) Analysis & Elimination Proofs

### 5.1 Comprehensive SPOF Elimination Matrix (22 Subsystems & Critical Paths)

| Critical Path / Function | Potential Single Point of Failure (SPOF) | Failure Mechanism | Architectural Resolution & Mitigation | Redundancy Mechanism | Formal Proof / Governing Invariant | Residual Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
{spof_table_str}

---

## 8. SORA SAIL Risk Mitigations & OSO Traceability Table

- **Ground Risk Class (GRC):** Final GRC = 4 (Initial GRC = 5, M1/M2 mitigations applied).
- **Air Risk Class (ARC):** Final ARC-c.
- **Specific Assurance and Integrity Level (SAIL):** SAIL III.

### Operational Safety Objectives {header_suffix}

{osos_str}

---

## 9. ASTM F3269-17 Run-Time Assurance (RTA) & Commercial Toolchain Architecture

The safety net monitor architecture complies with **ASTM F3269-17** Run-Time Assurance (RTA) for Aircraft Systems. Formal invariant proofs and Stateflow recovery supervisors are synthesized directly into **MATLAB / Simulink / Stateflow / Embedded Coder** and verified with Simulink Design Verifier (SLDV).
"""


def test_upstream_safety_landing_zone_clean():
    """Verify that upstream distribution templates enforce clean docs/safety/ landing zone."""
    if os.path.isdir(os.path.join(repo_root, ".pipeline", "upstream")):
        safety_dir = os.path.join(repo_root, "docs", "safety")
        if os.path.isdir(safety_dir):
            allowed = {".gitkeep", "README.md"}
            for f in os.listdir(safety_dir):
                assert f in allowed, f"Upstream template contains non-template file in docs/safety/: {f}"


def test_upstream_safety_landing_zone_dirty_fails():
    """Verify check_safety_integrity_and_sora_completeness rejects dirty upstream safety landing zones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".pipeline", "upstream"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "docs", "safety"), exist_ok=True)

        # Write allowed README.md
        with open(os.path.join(tmpdir, "docs", "safety", "README.md"), "w") as f:
            f.write("# Safety Directory\n")

        # Write concrete spec file (violation)
        with open(os.path.join(tmpdir, "docs", "safety", "STPA_MATRIX.md"), "w") as f:
            f.write("# Concrete STPA Matrix\n")

        with pytest.raises(SystemExit) as exc_info:
            check_safety_integrity_and_sora_completeness(tmpdir)
        assert exc_info.value.code == 1


def test_downstream_8_pillar_passing():
    """Verify that a complete 8-pillar STPA matrix with 40 LS and 240 FMECA rows passes with zero errors."""
    valid_content = generate_valid_stpa_matrix_content(loss_scenario_count=40, fmeca_row_count=240, include_all_osos=True)
    errors = validate_safety_matrix_content(valid_content)
    assert not errors, f"Expected 0 errors for valid 8-pillar STPA matrix, got:\n{errors}"


def test_stpa_loss_scenario_01_to_40_strict_set_equality():
    """Verify strict mathematical set-equality against all 40 STPA Loss Scenarios (LS-01..LS-40)."""
    # 1. Complete set of 40 scenarios
    valid_content = generate_valid_stpa_matrix_content(loss_scenario_count=40)
    detected = extract_loss_scenarios(valid_content)
    assert detected == EXPECTED_LOSS_SCENARIOS
    assert len(detected) == 40
    errors = validate_safety_matrix_content(valid_content)
    assert not any("Pillar 5 violation" in e for e in errors)

    # 2. Missing LS-05 scenario
    missing_ls05_content = generate_valid_stpa_matrix_content(loss_scenario_count=40, missing_scenario_id=5)
    errors = validate_safety_matrix_content(missing_ls05_content)
    assert any("LS-05" in e for e in errors), f"Expected missing LS-05 error, got:\n{errors}"

    # 3. Missing LS-40 scenario
    missing_ls40_content = generate_valid_stpa_matrix_content(loss_scenario_count=40, missing_scenario_id=40)
    errors = validate_safety_matrix_content(missing_ls40_content)
    assert any("LS-40" in e for e in errors), f"Expected missing LS-40 error, got:\n{errors}"

    # 4. Incomplete scenario set (e.g. only 30 scenarios)
    incomplete_30_content = generate_valid_stpa_matrix_content(loss_scenario_count=30)
    errors = validate_safety_matrix_content(incomplete_30_content)
    assert any("LS-31" in e and "LS-40" in e for e in errors), f"Expected missing LS-31..LS-40 error, got:\n{errors}"


def test_fmeca_240_rows_and_quantitative_criticality():
    """Verify strict quantitative FMECA matrix validation: 240+ failure modes across 22 components, sum(alpha)=1.0, SPOF status."""
    # 1. Valid 240 rows across 22 components
    valid_content_240 = generate_valid_stpa_matrix_content(fmeca_row_count=240)
    assert count_fmeca_rows(valid_content_240) >= 240
    errors = validate_safety_matrix_content(valid_content_240)
    assert not any("Pillar 7 violation" in e for e in errors)

    # 2. Incomplete FMECA rows (e.g. 239 rows)
    invalid_content_239 = generate_valid_stpa_matrix_content(fmeca_row_count=239)
    assert count_fmeca_rows(invalid_content_239) == 239
    errors = validate_safety_matrix_content(invalid_content_239)
    assert any("FMECA Criticality Matrix contains 239 row(s); minimum required is 240 rows" in err for err in errors)

    # 3. Severely truncated FMECA rows (e.g. 15 rows)
    invalid_content_15 = generate_valid_stpa_matrix_content(fmeca_row_count=15)
    errors = validate_safety_matrix_content(invalid_content_15)
    assert any("minimum required is 240 rows across 22 components" in err for err in errors)

    # 4. SPOF status violation (uneliminated single point of failure)
    spof_pending_content = generate_valid_stpa_matrix_content(fmeca_row_count=240, spof_status="PENDING")
    validator = SafetyTraceValidator()
    spof_findings = validator.validate_fmeca_matrix(spof_pending_content)
    assert any("uneliminated SPOF status" in f for f in spof_findings)


def test_sora_oso_01_to_24_validation():
    """Verify all 24 SORA OSOs (OSO-01 through OSO-24) are rigorously validated."""
    all_osos_text = " ".join([f"OSO-{i:02d}" for i in range(1, 25)])
    assert check_sora_osos(all_osos_text) == []

    partial_osos_text = " ".join([f"OSO-{i:02d}" for i in range(1, 25) if i not in (7, 24)])
    missing = check_sora_osos(partial_osos_text)
    assert missing == ["OSO-07", "OSO-24"]

    incomplete_content = generate_valid_stpa_matrix_content(include_all_osos=False)
    errors = validate_safety_matrix_content(incomplete_content)
    assert any("OSO-23" in err and "OSO-24" in err for err in errors), f"Expected missing OSOs error, got:\n{errors}"


def test_uca_failure_mode_categories():
    """Verify all 4 STPA UCA failure mode categories are required."""
    all_cats_text = (
        "1. Not providing causes hazard\n"
        "2. Providing causes hazard\n"
        "3. Providing too early, too late, or out of order\n"
        "4. Stopped too soon or applied too long"
    )
    assert check_uca_categories(all_cats_text) == []

    no_omission = (
        "2. Providing causes hazard\n"
        "3. Providing too early, too late, or out of order\n"
        "4. Stopped too soon or applied too long"
    )
    missing = check_uca_categories(no_omission)
    assert any("Not providing" in m for m in missing)


def test_astm_f3269_rta_and_commercial_toolchain_hooks():
    """Verify ASTM F3269-17 RTA and MATLAB/Simulink hooks are strictly enforced."""
    base_content = generate_valid_stpa_matrix_content()

    no_rta = base_content.replace("ASTM F3269-17", "").replace("ASTM F3269", "")
    errors = validate_safety_matrix_content(no_rta)
    assert any("ASTM F3269-17" in err for err in errors)

    no_matlab = base_content.replace("MATLAB", "").replace("Simulink", "").replace("Stateflow", "").replace("Embedded Coder", "").replace("SLDV", "")
    errors = validate_safety_matrix_content(no_matlab)
    assert any("MATLAB / Simulink" in err for err in errors)


def test_safety_trace_validator_direct():
    """Verify SafetyTraceValidator direct API execution across LS set-equality, FMECA math, and UCA coverage."""
    validator = SafetyTraceValidator()

    # 1. Test loss scenarios validation
    valid_content = generate_valid_stpa_matrix_content(loss_scenario_count=40, fmeca_row_count=240)
    assert validator.validate_loss_scenarios(valid_content) == []

    corrupted_ls = generate_valid_stpa_matrix_content(loss_scenario_count=40, missing_scenario_id=12)
    ls_findings = validator.validate_loss_scenarios(corrupted_ls)
    assert len(ls_findings) == 1
    assert "LS-12" in ls_findings[0]
    assert ls_findings[0].rule_id == "safety-stpa-loss-scenario-set-equality-violation"

    # 2. Test FMECA matrix validation
    fmeca_findings = validator.validate_fmeca_matrix(valid_content)
    assert fmeca_findings == []

    # Corrupt alpha sum on component
    corrupted_alpha = valid_content.replace("α = 0.15", "α = 0.05", 1)
    alpha_findings = validator.validate_fmeca_matrix(corrupted_alpha)
    assert any(f.rule_id == "safety-fmeca-alpha-sum-violation" for f in alpha_findings)

    # 3. Test UCA coverage validation
    uca_findings = validator.validate_uca_coverage(valid_content)
    assert uca_findings == []


def test_end_to_end_check_17_downstream_integration():
    """Verify end-to-end Check 17 execution on downstream project directory with exit code 1 on violations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        safety_dir = os.path.join(tmpdir, "docs", "safety")
        os.makedirs(safety_dir, exist_ok=True)

        stpa_file = os.path.join(safety_dir, "STPA_MATRIX.md")
        valid_content = generate_valid_stpa_matrix_content(loss_scenario_count=40, fmeca_row_count=240, include_all_osos=True)

        with open(stpa_file, "w", encoding="utf-8") as f:
            f.write(valid_content)

        # Should pass with no exception
        check_safety_integrity_and_sora_completeness(tmpdir)

        # Corrupt file with violation 1: drop LS-40
        corrupted_ls = valid_content.replace("**LS-40**", "**LS-INVALID**")
        with open(stpa_file, "w", encoding="utf-8") as f:
            f.write(corrupted_ls)
        with pytest.raises(SystemExit) as exc_info:
            check_safety_integrity_and_sora_completeness(tmpdir)
        assert exc_info.value.code == 1

        # Corrupt file with violation 2: drop OSO-24
        corrupted_oso = valid_content.replace("OSO-24", "INVALID-REF")
        with open(stpa_file, "w", encoding="utf-8") as f:
            f.write(corrupted_oso)
        with pytest.raises(SystemExit) as exc_info:
            check_safety_integrity_and_sora_completeness(tmpdir)
        assert exc_info.value.code == 1


def test_live_docs_safety_workspace_verification():
    """Verify live repository docs/safety/ passes Check 17 and SafetyTraceValidator with zero errors."""
    repo = WorkspaceRepository(workspace_dir=repo_root)
    validator = SafetyTraceValidator()
    findings = validator.validate(repo)
    assert findings == [], f"Expected 0 findings in live workspace docs/safety/, got:\n{findings}"

    # Verify Check 17 runs cleanly on live repository root
    check_safety_integrity_and_sora_completeness(repo_root)


def test_feature_specifications_fmeca_embedding_completeness():
    """Verify all 24 Feature Specifications embed exact quantitative MIL-STD-1629A FMECA tables covering all 22 components and 240 modes."""
    if os.path.isdir(os.path.join(repo_root, ".pipeline", "upstream")):
        pytest.skip("Upstream template repository has clean landing zones; feature specs verified in downstream projects.")
    features_dir = os.path.join(repo_root, "docs", "features")
    feature_files = sorted([f for f in os.listdir(features_dir) if f.startswith("feat-") and f.endswith(".md")])
    assert len(feature_files) == 24, f"Expected 24 feature specification files, found {len(feature_files)}"

    total_embedded_modes = 0
    covered_components = set()

    for fname in feature_files:
        fpath = os.path.join(features_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fp:
            content = fp.read()

        # 1. Verify two-column metadata table
        assert content.startswith("| Attribute | Specification Detail |") or "| Attribute |" in content[:200], f"Missing metadata table in {fname}"

        # 2. Verify FMECA subsection exists under Section 2
        assert "Quantitative FMECA Failure Mode" in content, f"Missing FMECA subsection in {fname}"

        # 3. Parse FMECA modes from feature file
        modes, comps = parse_fmeca_modes(content)
        assert len(modes) > 0, f"No FMECA modes parsed in {fname}"

        for comp_name, comp_modes in comps.items():
            covered_components.add(comp_name)
            # Verify sum(alpha) == 1.00 (+/- 0.01)
            alpha_sum = sum(m["alpha"] for m in comp_modes)
            assert abs(alpha_sum - 1.0) < 0.02, f"sum(alpha) = {alpha_sum} != 1.0 for {comp_name} in {fname}"

            # Verify all modes have valid quantitative attributes and ELIMINATED SPOF
            for m in comp_modes:
                assert m["lambda_p"] > 0, f"Invalid lambda_p in {fname}: {m}"
                assert 0.0 <= m["beta"] <= 1.0, f"Invalid beta in {fname}: {m}"
                init_rpn = int(re.sub(r"[*]", "", m["initial_rpn"]))
                res_rpn = int(re.sub(r"[*]", "", m["residual_rpn"]))
                assert init_rpn > 0, f"Invalid initial RPN in {fname}: {m}"
                assert res_rpn > 0, f"Invalid residual RPN in {fname}: {m}"
                assert "ELIMINATED" in m["line"], f"SPOF not eliminated in row in {fname}: {m['line']}"

        total_embedded_modes += len(modes)

    # Verify all 22 components from FMECA_MATRIX.md are covered
    expected_comp_names = {c[0] for c in FMECA_22_COMPONENTS}
    # Match by substring/prefix since component strings may include part refs
    matched_expected = set()
    for exp in expected_comp_names:
        for cov in covered_components:
            if exp in cov or cov in exp:
                matched_expected.add(exp)
                break

    assert len(matched_expected) == len(expected_comp_names), f"Missing components in features: {expected_comp_names - matched_expected}"
    assert total_embedded_modes >= 240, f"Total embedded modes ({total_embedded_modes}) is less than 240"

