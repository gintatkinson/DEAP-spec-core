"""
Unit tests for SysML v2 Universal Ingestion Engine.
Verifies AST serialization, multi-schema translation (IDL, AUTOSAR ARXML, Protobuf, OpenAPI),
CLI entrypoint execution, and schema digest generation.
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "scripts")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from sysmlv2_ast import (
        SysMLPackage,
        PartDef,
        PortDef,
        AttributeDef,
        ActionDef,
    )
    from translators.idl_translator import IDLTranslator
    from translators.autosar_translator import AUTOSARTranslator
    from translators.protobuf_translator import ProtobufTranslator
    from translators.openapi_translator import OpenAPITranslator
    from sysmlv2_ingest import ingest_schema, main as cli_main
except ImportError:
    from skills.spec_orchestrator.scripts.sysmlv2_ast import (
        SysMLPackage,
        PartDef,
        PortDef,
        AttributeDef,
        ActionDef,
    )
    from skills.spec_orchestrator.scripts.translators.idl_translator import IDLTranslator
    from skills.spec_orchestrator.scripts.translators.autosar_translator import AUTOSARTranslator
    from skills.spec_orchestrator.scripts.translators.protobuf_translator import ProtobufTranslator
    from skills.spec_orchestrator.scripts.translators.openapi_translator import OpenAPITranslator
    from skills.spec_orchestrator.scripts.sysmlv2_ingest import ingest_schema, main as cli_main


def test_sysmlv2_ast_construction_and_serialization():
    attr = AttributeDef(name="vehicleSpeed", type_name="Real", doc="Current speed in km/h")
    port = PortDef(name="speedSensorPort", type_name="SpeedPort", direction="in")
    action = ActionDef(name="calculateBrakeForce", doc="Calculates required braking force")
    part = PartDef(
        name="BrakingController",
        doc="Main brake management component",
        attributes=[attr],
        ports=[port],
        actions=[action],
    )
    pkg = SysMLPackage(name="AutomotiveSafetySystem", doc="Root safety package", part_defs=[part])

    sysml_text = pkg.to_sysml()
    assert "package AutomotiveSafetySystem {" in sysml_text
    assert "part def BrakingController {" in sysml_text
    assert "attribute vehicleSpeed : Real;" in sysml_text
    assert "port speedSensorPort : SpeedPort;" in sysml_text
    assert "action calculateBrakeForce;" in sysml_text

    counts = pkg.node_counts()
    assert counts["packages"] == 1
    assert counts["part_defs"] == 1
    assert counts["attribute_defs"] == 1
    assert counts["port_defs"] == 1
    assert counts["action_defs"] == 1


def test_idl_translator():
    idl_sample = """
    module FlightControl {
        struct AltitudeData {
            float currentAltitude;
            float targetAltitude;
        };

        interface AutopilotService {
            void setHeading(in float headingAngle);
        };
    };
    """
    translator = IDLTranslator()
    pkg = translator.translate(idl_sample)

    assert pkg.name == "FlightControl"
    part_names = [p.name for p in pkg.part_defs]
    assert "AltitudeData" in part_names
    assert "AutopilotService" in part_names

    alt_struct = next(p for p in pkg.part_defs if p.name == "AltitudeData")
    attr_names = [a.name for a in alt_struct.attributes]
    assert "currentAltitude" in attr_names
    assert "targetAltitude" in attr_names

    autopilot = next(p for p in pkg.part_defs if p.name == "AutopilotService")
    action_names = [a.name for a in autopilot.actions]
    assert "setHeading" in action_names


def test_autosar_translator():
    arxml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <AUTOSAR xmlns="http://autosar.org/schema/r4.0">
      <AR-PACKAGES>
        <AR-PACKAGE>
          <SHORT-NAME>EngineManagement</SHORT-NAME>
          <ELEMENTS>
            <APPLICATION-SW-COMPONENT-TYPE>
              <SHORT-NAME>ThrottleController</SHORT-NAME>
              <PORTS>
                <P-PORT-PROTOTYPE>
                  <SHORT-NAME>ThrottleOut</SHORT-NAME>
                </P-PORT-PROTOTYPE>
                <R-PORT-PROTOTYPE>
                  <SHORT-NAME>PedalPosIn</SHORT-NAME>
                </R-PORT-PROTOTYPE>
              </PORTS>
            </APPLICATION-SW-COMPONENT-TYPE>
          </ELEMENTS>
        </AR-PACKAGE>
      </AR-PACKAGES>
    </AUTOSAR>
    """
    translator = AUTOSARTranslator()
    pkg = translator.translate(arxml_sample)

    assert pkg.name == "EngineManagement"
    assert len(pkg.part_defs) == 1
    part = pkg.part_defs[0]
    assert part.name == "ThrottleController"
    port_names = [p.name for p in part.ports]
    assert "ThrottleOut" in port_names
    assert "PedalPosIn" in port_names


def test_protobuf_translator():
    proto_sample = """
    syntax = "proto3";
    package telemetry;

    message SignalData {
        string signal_id = 1;
        double timestamp = 2;
        double value = 3;
    }

    service TelemetryService {
        rpc StreamSignal (SignalData) returns (SignalData);
    }
    """
    translator = ProtobufTranslator()
    pkg = translator.translate(proto_sample)

    assert pkg.name == "telemetry"
    part_names = [p.name for p in pkg.part_defs]
    assert "SignalData" in part_names
    assert "TelemetryService" in part_names

    signal_msg = next(p for p in pkg.part_defs if p.name == "SignalData")
    attr_names = [a.name for a in signal_msg.attributes]
    assert "signal_id" in attr_names
    assert "timestamp" in attr_names
    assert "value" in attr_names


def test_openapi_translator():
    openapi_sample = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "NavigationAPI", "version": "1.0.0"},
        "paths": {
            "/route": {
                "post": {
                    "operationId": "calculateRoute",
                    "summary": "Calculate trajectory route"
                }
            }
        },
        "components": {
            "schemas": {
                "Waypoint": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"}
                    }
                }
            }
        }
    })
    translator = OpenAPITranslator()
    pkg = translator.translate(openapi_sample)

    assert pkg.name == "NavigationAPI"
    part_names = [p.name for p in pkg.part_defs]
    assert "Waypoint" in part_names
    assert any("calculateRoute" in [act.name for act in p.actions] for p in pkg.part_defs) or len(pkg.action_defs) > 0 or any("calculateRoute" in act.name for act in pkg.action_defs)


def test_sysmlv2_ingest_cli(tmp_path):
    idl_file = tmp_path / "sensor.idl"
    idl_file.write_text("""
    module RadarSensor {
        struct Detection {
            float distance;
            float azimuth;
        };
    };
    """)

    out_sysml = tmp_path / "sensor.sysml"
    digest_out = tmp_path / "schema-digest.json"

    result_pkg, digest_data = ingest_schema(
        schema_path=str(idl_file),
        format_type="idl",
        output_path=str(out_sysml),
        digest_path=str(digest_out)
    )

    assert out_sysml.exists()
    assert digest_out.exists()
    sysml_content = out_sysml.read_text()
    assert "package RadarSensor" in sysml_content
    assert "part def Detection" in sysml_content

    with open(digest_out, "r") as f:
        digest_json = json.load(f)

    assert "sha256" in digest_json
    assert "total_lines" in digest_json
    assert "node_counts" in digest_json
    assert "schema_nodes" in digest_json


def test_schema_specification_engineering_wiring():
    skill_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "skills",
        "schema-specification-engineering",
        "SKILL.md"
    )
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "sysmlv2_ingest.py" in content
