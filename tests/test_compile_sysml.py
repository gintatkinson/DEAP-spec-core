import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.compile_sysml import parse_sysml

def test_parse_sysml():
    sysml_content = """
    package MyPackage {
        part def MyPart {
            attribute def MyAttr { }
            port def MyPort { }
        }
        requirement def MyReq { }
        state def MyState { }
    }
    """
    ast = parse_sysml(sysml_content)
    assert "MyPackage" in ast["packages"]
    assert "MyPart" in ast["part_defs"]
    assert "MyAttr" in ast["attribute_defs"]
    assert "MyPort" in ast["port_defs"]
    assert "MyReq" in ast["requirement_defs"]
    assert "MyState" in ast["state_defs"]
