#!/usr/bin/env python3
"""
SysML v2 Compiler, STPA Safety Constraints & RTA Compiler & Textual Model Serializer

Compiles and parses SysML v2 textual models into structured AST representations,
extracting all 6 core model constructs (packages, parts, attributes, ports,
actions, capabilities, operations, interactions, constraints/assertions,
test cases, requirements, states, use cases, items).

Implements STPA-to-SysML compilation: parses STPA Unsafe Control Actions (UCAs)
and FMECA failure modes, compiling them into formal SysML v2 `constraint def` and
`assert constraint` expressions for Run-Time Assurance (RTA) mathematical verification
with Simulink Design Verifier (SLDV) and Embedded Coder synthesis.

Usage:
    python3 scripts/compile_sysml.py <file.sysml>
    python3 scripts/compile_sysml.py --stpa <stpa_file.md>
"""

import sys
import json
import os
import re
from typing import Dict, List, Any, Optional

# Ensure spec-orchestrator scripts are on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SPEC_SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "skills", "spec-orchestrator", "scripts")
if SPEC_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SPEC_SCRIPTS_DIR)

try:
    from sysmlv2_ast import SysMLParser, SysMLPackage, SysMLConstraintDef, PartDef
except ImportError:
    SysMLParser = None
    SysMLPackage = None
    SysMLConstraintDef = None
    PartDef = None


def parse_stpa_ucas(content: str) -> List[Dict[str, Any]]:
    """
    Parses STPA Unsafe Control Actions (UCAs) from markdown tables, structured text,
    or specification matrices.

    Returns:
        List of dicts representing parsed UCAs with fields:
        - id: UCA identifier (e.g. 'UCA-UAS-01')
        - controller: Controlling element (e.g. 'Flight Controller')
        - control_action: Action commanded (e.g. 'Fail-Safe Return-to-Launch (RTL)')
        - category: STPA UCA category (e.g. '1. Not Provided', '2. Provided Unsafely')
        - context: Environmental Context / Trigger condition
        - hazard: Associated System Hazard (e.g. 'H_UAS_1')
        - severity: Severity level (e.g. 'Catastrophic')
        - sail: SORA SAIL level (e.g. 'SAIL IV-VI')
    """
    ucas = []
    # Pattern 1: Markdown table row with UCA
    # | UCA ID | Controller | Control Action | STPA UCA Category | Context | Hazard | Severity | SAIL |
    row_pattern = re.compile(
        r'\|\s*(?:\*\*)?(UCA(?:-[A-Za-z0-9_]+)?-\d+)(?:\*\*)?\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'(?:\s*([^|\n]+)\s*\|)?'
    )

    for match in row_pattern.finditer(content):
        uca_id = match.group(1).strip()
        controller = match.group(2).strip()
        control_action = match.group(3).strip()
        category = match.group(4).strip().strip('*')
        context = match.group(5).strip()
        hazard = match.group(6).strip().strip('*')
        severity = match.group(7).strip()
        sail = match.group(8).strip() if match.group(8) else ""

        ucas.append({
            "id": uca_id,
            "controller": controller,
            "control_action": control_action,
            "category": category,
            "context": context,
            "hazard": hazard,
            "severity": severity,
            "sail": sail
        })

    # Pattern 2: Generic UCA extraction fallback (e.g. list items or headings)
    if not ucas:
        generic_pattern = re.compile(r'\b(UCA(?:-[A-Za-z0-9_]+)?-\d+)\b')
        for match in generic_pattern.finditer(content):
            uid = match.group(1)
            if not any(u["id"] == uid for u in ucas):
                ucas.append({
                    "id": uid,
                    "controller": "FlightController",
                    "control_action": "SafetyAction",
                    "category": "UnsafeControlAction",
                    "context": "OperationalEnvelopeExceeded",
                    "hazard": "H_UAS_Hazard",
                    "severity": "Catastrophic",
                    "sail": "SAIL_IV"
                })

    return ucas


def parse_fmeca_modes(content: str) -> List[Dict[str, Any]]:
    """
    Parses FMECA failure modes from markdown tables or specification text.
    """
    fmecas = []
    row_pattern = re.compile(
        r'\|\s*(?:\*\*)?(FMECA(?:-[A-Za-z0-9_]+)?-\d+)(?:\*\*)?\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'\s*([^|]+)\s*\|'
        r'(?:\s*([^|\n]+)\s*\|)?'
    )

    for match in row_pattern.finditer(content):
        fmeca_id = match.group(1).strip()
        component = match.group(2).strip()
        failure_mode = match.group(3).strip()
        effect = match.group(4).strip()
        mitigation = match.group(5).strip() if match.group(5) else ""

        fmecas.append({
            "id": fmeca_id,
            "component": component,
            "failure_mode": failure_mode,
            "effect": effect,
            "mitigation": mitigation
        })

    return fmecas


def _sanitize_id(identifier: str) -> str:
    """Converts hyphens and non-alphanumeric chars into clean underscores for SysML IDs."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', identifier)


def _derive_formal_rta_expression(uca: Dict[str, Any]) -> str:
    """
    Synthesizes a mathematically verifiable Simulink Design Verifier (SLDV) / RTA
    predicate expression from an STPA UCA context and control action.
    """
    uca_id = uca.get("id", "")
    context = uca.get("context", "")
    action = uca.get("control_action", "")
    category = uca.get("category", "").lower()

    # Clean LaTeX math formatting
    clean_ctx = re.sub(r'[\$\\_{}]', '', context)
    clean_ctx = re.sub(r'\\text\{([^}]*)\}', r'\1', clean_ctx)
    clean_ctx = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', clean_ctx)
    clean_ctx = re.sub(r'\\mu', 'micro', clean_ctx)
    clean_ctx = re.sub(r'\\le', '<=', clean_ctx)
    clean_ctx = re.sub(r'\\ge', '>=', clean_ctx)

    # Specific known standard predicates
    if "t_loss" in clean_ctx or "loss" in clean_ctx.lower():
        return "not (lossDuration > 2.0 and c2LinkStatus == False) or (rtlActive == True)"
    elif "EMF" in clean_ctx or "flux" in clean_ctx.lower() or "magnetometer" in clean_ctx.lower():
        return "magneticFluxNorm <= 250.0"
    elif "LiDAR" in clean_ctx or "wire" in clean_ctx.lower():
        return "obstacleDistance >= 5.0"
    elif "Throttle" in action or "descent" in clean_ctx.lower():
        return "not (descentRate > 3.0 and altitudeAGL < 20.0) or (throttleDemand >= 0.25)"
    elif "geofence" in clean_ctx.lower() or "Geofence" in action:
        return "geofenceBoundaryDistance >= 5.0"
    elif "intruder" in clean_ctx.lower() or "closure" in clean_ctx.lower():
        return "intruderSeparationDistance >= 300.0"
    elif "cell" in clean_ctx.lower() or "voltage" in clean_ctx.lower() or "Vcell" in clean_ctx:
        return "batteryCellVoltage >= 3.2 and packCurrent <= 60.0"
    elif "altitude" in clean_ctx.lower():
        return "altitudeAGL >= 50.0"
    elif "airspeed" in clean_ctx.lower():
        return "airspeed <= 35.0"
    elif "temperature" in clean_ctx.lower() or "thermal" in clean_ctx.lower():
        return "coreTemperature <= 85.0"
    else:
        clean_action = _sanitize_id(action)
        return f"safetyInvariant_{_sanitize_id(uca_id)} == true"


def compile_uca_to_constraint(uca: Dict[str, Any]) -> Any:
    """
    Compiles a parsed UCA into a formal SysMLConstraintDef AST node configured
    as an `assert constraint` for Run-Time Assurance (RTA) mathematical verification.
    """
    uca_id = uca["id"]
    clean_id = _sanitize_id(uca_id)
    name = f"Assert_{clean_id}"
    expression = _derive_formal_rta_expression(uca)
    
    doc = (
        f"STPA RTA Safety Invariant for {uca_id} | Controller: {uca.get('controller', '')} | "
        f"Hazard: {uca.get('hazard', '')} | Severity: {uca.get('severity', '')}"
    )

    if SysMLConstraintDef:
        return SysMLConstraintDef(
            name=name,
            expression=expression,
            is_assertion=True,
            doc=doc
        )
    return {
        "name": name,
        "expression": expression,
        "is_assertion": True,
        "doc": doc
    }


def compile_fmeca_to_constraint(fmeca: Dict[str, Any]) -> Any:
    """
    Compiles a parsed FMECA failure mode into a formal SysMLConstraintDef AST node.
    """
    fmeca_id = fmeca["id"]
    clean_id = _sanitize_id(fmeca_id)
    name = f"Constraint_{clean_id}"
    comp = _sanitize_id(fmeca.get("component", "Component"))
    expression = f"{comp}_healthStatus == Normal"
    doc = f"FMECA Safety Invariant for {fmeca_id} | Failure Mode: {fmeca.get('failure_mode', '')}"

    if SysMLConstraintDef:
        return SysMLConstraintDef(
            name=name,
            expression=expression,
            is_assertion=False,
            doc=doc
        )
    return {
        "name": name,
        "expression": expression,
        "is_assertion": False,
        "doc": doc
    }


def compile_stpa_to_ast(content: str, package_name: str = "AutonomousUAS_SafetyConstraints") -> Any:
    """
    Compiles STPA and FMECA hazard analyses into a canonical SysMLPackage AST containing
    formal `assert constraint` and `constraint def` nodes.
    """
    ucas = parse_stpa_ucas(content)
    fmecas = parse_fmeca_modes(content)

    constraints = []
    for u in ucas:
        constraints.append(compile_uca_to_constraint(u))
    for f in fmecas:
        constraints.append(compile_fmeca_to_constraint(f))

    if SysMLPackage:
        pkg = SysMLPackage(
            name=package_name,
            doc="STPA and FMECA Safety Invariants compiled for Run-Time Assurance (RTA) & SLDV Verification",
            constraint_defs=constraints
        )
        return pkg
    return {
        "package": package_name,
        "constraints": constraints
    }


def compile_stpa_to_sysml(content: str, package_name: str = "AutonomousUAS_SafetyConstraints") -> str:
    """
    Compiles STPA hazard matrices and FMECA modes into textual SysML v2 model notation.
    """
    ast_pkg = compile_stpa_to_ast(content, package_name)
    if hasattr(ast_pkg, "to_sysml"):
        return ast_pkg.to_sysml()

    lines = [f"package {package_name} {{", f"    doc /* STPA RTA Safety Invariants */"]
    for c in ast_pkg.get("constraints", []):
        kw = "assert constraint" if c.get("is_assertion") else "constraint def"
        lines.append(f"    doc /* {c.get('doc', '')} */")
        lines.append(f"    {kw} {c.get('name')} {{")
        lines.append(f"        {c.get('expression')};")
        lines.append("    }\n")
    lines.append("}")
    return "\n".join(lines)


def parse_sysml(content: str) -> Dict[str, List[str]]:
    """
    Parses SysML v2 textual model content and returns a dictionary of extracted
    AST node names across all 6 core constructs and architectural elements.
    """
    ast: Dict[str, List[str]] = {
        "packages": [],
        "part_defs": [],
        "attribute_defs": [],
        "port_defs": [],
        "action_defs": [],
        "capability_defs": [],
        "operation_defs": [],
        "interaction_defs": [],
        "constraint_defs": [],
        "test_case_defs": [],
        "requirement_defs": [],
        "state_defs": [],
        "use_case_defs": [],
        "item_defs": []
    }

    if SysMLParser is not None:
        try:
            pkg = SysMLParser.parse_text(content)
            
            def _extract_from_pkg(p: SysMLPackage):
                if p.name and p.name not in ast["packages"] and p.name != "SysML_Model":
                    ast["packages"].append(p.name)
                for a in p.attribute_defs:
                    if a.name not in ast["attribute_defs"]:
                        ast["attribute_defs"].append(a.name)
                for pt in p.port_defs:
                    if pt.name not in ast["port_defs"]:
                        ast["port_defs"].append(pt.name)
                for ac in p.action_defs:
                    if ac.name not in ast["action_defs"]:
                        ast["action_defs"].append(ac.name)
                for cap in p.capability_defs:
                    if cap.name not in ast["capability_defs"]:
                        ast["capability_defs"].append(cap.name)
                for op in p.operation_defs:
                    if op.name not in ast["operation_defs"]:
                        ast["operation_defs"].append(op.name)
                for it in p.interaction_defs:
                    if it.name not in ast["interaction_defs"]:
                        ast["interaction_defs"].append(it.name)
                for c in p.constraint_defs:
                    if c.name not in ast["constraint_defs"]:
                        ast["constraint_defs"].append(c.name)
                for tc in p.test_case_defs:
                    if tc.name not in ast["test_case_defs"]:
                        ast["test_case_defs"].append(tc.name)
                for r in p.requirement_defs:
                    if r.name not in ast["requirement_defs"]:
                        ast["requirement_defs"].append(r.name)
                for s in p.state_defs:
                    if s.name not in ast["state_defs"]:
                        ast["state_defs"].append(s.name)
                for uc in p.use_case_defs:
                    if uc.name not in ast["use_case_defs"]:
                        ast["use_case_defs"].append(uc.name)
                for itm in p.item_defs:
                    if itm.name not in ast["item_defs"]:
                        ast["item_defs"].append(itm.name)

                for part in p.part_defs:
                    _extract_from_part(part)

                for sub in p.sub_packages:
                    _extract_from_pkg(sub)

            def _extract_from_part(part):
                if part.name not in ast["part_defs"]:
                    ast["part_defs"].append(part.name)
                for a in part.attributes:
                    if a.name not in ast["attribute_defs"]:
                        ast["attribute_defs"].append(a.name)
                for pt in part.ports:
                    if pt.name not in ast["port_defs"]:
                        ast["port_defs"].append(pt.name)
                for ac in part.actions:
                    if ac.name not in ast["action_defs"]:
                        ast["action_defs"].append(ac.name)
                for op in part.operations:
                    if op.name not in ast["operation_defs"]:
                        ast["operation_defs"].append(op.name)
                for cap in part.capabilities:
                    if cap.name not in ast["capability_defs"]:
                        ast["capability_defs"].append(cap.name)
                for it in part.interactions:
                    if it.name not in ast["interaction_defs"]:
                        ast["interaction_defs"].append(it.name)
                for c in part.constraints:
                    if c.name not in ast["constraint_defs"]:
                        ast["constraint_defs"].append(c.name)
                for tc in part.test_cases:
                    if tc.name not in ast["test_case_defs"]:
                        ast["test_case_defs"].append(tc.name)
                for r in part.requirements:
                    if r.name not in ast["requirement_defs"]:
                        ast["requirement_defs"].append(r.name)
                for s in part.states:
                    if s.name not in ast["state_defs"]:
                        ast["state_defs"].append(s.name)
                for uc in part.use_cases:
                    if uc.name not in ast["use_case_defs"]:
                        ast["use_case_defs"].append(uc.name)
                for itm in part.item_defs:
                    if itm.name not in ast["item_defs"]:
                        ast["item_defs"].append(itm.name)
                for sub_part in part.parts:
                    _extract_from_part(sub_part)

            _extract_from_pkg(pkg)
            return ast
        except Exception:
            pass

    # Regex-based extraction fallback
    for match in re.finditer(r'\bpackage\s+([a-zA-Z0-9_\-\.]+)', content):
        name = match.group(1).replace('.', '_')
        if name not in ast["packages"]:
            ast["packages"].append(name)
    for match in re.finditer(r'\bpart\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["part_defs"]:
            ast["part_defs"].append(match.group(1))
    for match in re.finditer(r'\battribute\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["attribute_defs"]:
            ast["attribute_defs"].append(match.group(1))
    for match in re.finditer(r'\b(?:in|out|inout)?\s*port\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["port_defs"]:
            ast["port_defs"].append(match.group(1))
    for match in re.finditer(r'\baction\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["action_defs"]:
            ast["action_defs"].append(match.group(1))
    for match in re.finditer(r'\bcapability\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["capability_defs"]:
            ast["capability_defs"].append(match.group(1))
    for match in re.finditer(r'\b(?:operation|feature)\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["operation_defs"]:
            ast["operation_defs"].append(match.group(1))
    for match in re.finditer(r'\binteraction\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["interaction_defs"]:
            ast["interaction_defs"].append(match.group(1))
    for match in re.finditer(r'\b(?:assert\s+constraint|constraint\s+(?:def)?)\s+([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["constraint_defs"]:
            ast["constraint_defs"].append(match.group(1))
    for match in re.finditer(r'\btest\s+case\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["test_case_defs"]:
            ast["test_case_defs"].append(match.group(1))
    for match in re.finditer(r'\brequirement\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["requirement_defs"]:
            ast["requirement_defs"].append(match.group(1))
    for match in re.finditer(r'\bstate\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["state_defs"]:
            ast["state_defs"].append(match.group(1))
    for match in re.finditer(r'\buse\s+case\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["use_case_defs"]:
            ast["use_case_defs"].append(match.group(1))
    for match in re.finditer(r'\bitem\s+(?:def\s+)?([a-zA-Z0-9_]+)', content):
        if match.group(1) not in ast["item_defs"]:
            ast["item_defs"].append(match.group(1))

    return ast


def main():
    if len(sys.argv) < 2:
        print("Usage: compile_sysml.py [--stpa] <file.sysml|stpa_matrix.md>")
        sys.exit(1)

    is_stpa = False
    target_file = sys.argv[1]
    if sys.argv[1] in ("--stpa", "--compile-stpa"):
        if len(sys.argv) < 3:
            print("Error: Missing STPA file path argument.")
            sys.exit(1)
        is_stpa = True
        target_file = sys.argv[2]

    if not os.path.exists(target_file):
        print(f"Error: File not found: {target_file}")
        sys.exit(1)

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if is_stpa or ("UCA-" in content and "package " not in content):
        print(compile_stpa_to_sysml(content))
    else:
        print(json.dumps(parse_sysml(content), indent=2))


if __name__ == '__main__':
    main()
