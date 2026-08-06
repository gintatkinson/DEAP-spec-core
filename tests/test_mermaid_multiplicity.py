import os
import json

def test_mermaid_type_bound_multiplicity_extraction(tmp_path):
    from parity_auditor.core.workspace import WorkspaceRepository
    from parity_auditor.parsers.mermaid import MermaidClassDiagramParser

    # Minimal workspace setup
    rules_dir = tmp_path / ".pipeline" / "logical-ui"
    os.makedirs(rules_dir, exist_ok=True)
    rules = {
        "meta": {"version": "1.0.0", "description": "test"},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
        },
    }
    with open(rules_dir / "codebase_rules.json", "w", encoding="utf-8") as f:
        json.dump(rules, f)

    repo = WorkspaceRepository(str(tmp_path))
    parser = MermaidClassDiagramParser(repo)

    # Type-bound multiplicity: [0..*] belongs to String, not the attribute
    diagram = """```mermaid
classDiagram
    class C {
        +String[0..*] name
    }
```"""
    result = parser.parse(diagram)
    attr = list(result.classes["C"].attributes)[0]

    assert attr.name == "name", f"Expected name='name', got {attr.name!r}"
    assert attr.type == "String[0..*]", f"Expected type='String[0..*]', got {attr.type!r}"
    assert attr.multiplicity is None, f"Expected multiplicity=None (type-bound stays with type), got {attr.multiplicity!r}"
    assert attr.visibility == "+", f"Expected visibility='+', got {attr.visibility!r}"

    # Attribute-level multiplicity: [0..1] belongs to the attribute
    diagram2 = """```mermaid
classDiagram
    class C {
        +String name[0..1]
    }
```"""
    result2 = parser.parse(diagram2)
    attr2 = list(result2.classes["C"].attributes)[0]

    assert attr2.name == "name", f"Expected name='name', got {attr2.name!r}"
    assert attr2.type == "String", f"Expected type='String', got {attr2.type!r}"
    assert attr2.multiplicity == "0..1", f"Expected multiplicity='0..1' (attr-level), got {attr2.multiplicity!r}"
    assert attr2.visibility == "+", f"Expected visibility='+', got {attr2.visibility!r}"

    # Both: type-bound + attribute-level multiplicities coexist
    diagram3 = """```mermaid
classDiagram
    class C {
        +String[0..*] name[0..1]
    }
```"""
    result3 = parser.parse(diagram3)
    attr3 = list(result3.classes["C"].attributes)[0]

    assert attr3.name == "name", f"Expected name='name', got {attr3.name!r}"
    assert attr3.type == "String[0..*]", f"Expected type='String[0..*]', got {attr3.type!r}"
    assert attr3.multiplicity == "0..1", f"Expected multiplicity='0..1' (attr-level), got {attr3.multiplicity!r}"
