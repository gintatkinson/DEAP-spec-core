import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.parsers.mermaid import MermaidSequenceDiagramParser, MermaidClassDiagramParser, MermaidFlowchartParser

class MockWorkspaceRules:
    class ValidationRules:
        def __init__(self):
            self.visibility_prefixes = ["+", "-", "#", "~"]
            self.relationship_connectors = "(<\\|--|\\*--|o--|-->|\\.\\.>|--)"
    def __init__(self):
        self.validation_rules = self.ValidationRules()

class MockWorkspaceRepository:
    def get_codebase_rules(self):
        return MockWorkspaceRules()

def test_sequence_diagram_parser_skips_code_fences_and_autonumber_and_notes():
    parser = MermaidSequenceDiagramParser()
    
    diagram = """
    ```mermaid
    sequenceDiagram
        autonumber
        Alice->>Bob: hello()
        Note over Alice, Bob: This is a note
        note right of Alice: Another note
        Bob-->>Alice: reply
    ```
    """
    
    result = parser.parse(diagram)
    
    # Assertions
    assert len(result.messages) == 2
    assert result.messages[0].sender == "Alice"
    assert result.messages[0].receiver == "Bob"
    assert result.messages[0].operation == "hello"
    
    assert result.messages[1].sender == "Bob"
    assert result.messages[1].receiver == "Alice"
    assert result.messages[1].arrow == "-->>"
    
    # Verify no parse errors occurred (fences, autonumber, notes skipped successfully)
    assert not result.parse_errors

def test_class_diagram_parser_skips_code_fences_and_notes():
    repo = MockWorkspaceRepository()
    parser = MermaidClassDiagramParser(repo)
    
    diagram = """
    ```mermaid
    classDiagram
        class A {
            +String name
        }
        note "This is a note for class A"
        note for A "Another note"
        A --> B : relationship
    ```
    """
    
    result = parser.parse(diagram)
    
    # Assertions
    assert "A" in result.classes
    assert "B" in result.classes
    assert len(result.relationships) == 1
    assert result.relationships[0].from_class == "A"
    assert result.relationships[0].to_class == "B"
    assert not result.parse_errors

def test_flowchart_parser_skips_code_fences_and_notes():
    parser = MermaidFlowchartParser()
    
    diagram = """
    ```mermaid
    flowchart TD
        A[Start] --> B(Process)
        note "Flowchart note"
        B --> C[End]
    ```
    """
    
    result = parser.parse(diagram)
    
    # Assertions
    assert "A" in result.nodes
    assert "B" in result.nodes
    assert "C" in result.nodes
    assert len(result.connections) == 2
    assert not result.parse_errors

def test_sequence_diagram_note_with_semicolon_rejected():
    parser = MermaidSequenceDiagramParser()
    diagram = """
    sequenceDiagram
        Alice->>Bob: hello()
        Note over Alice, Bob: This is a note; with semicolon
        note right of Alice: Another note;
        Bob-->>Alice: reply
    """
    result = parser.parse(diagram)
    assert len(result.parse_errors) == 2
    assert "Semicolons are not allowed in sequence diagram Note statements: 'Note over Alice, Bob: This is a note; with semicolon'" in result.parse_errors[0]
    assert "Semicolons are not allowed in sequence diagram Note statements: 'note right of Alice: Another note;'" in result.parse_errors[1]

def test_sequence_diagram_message_with_semicolon_rejected():
    parser = MermaidSequenceDiagramParser()
    diagram = """
    sequenceDiagram
        Alice->>Bob: hello();
        Bob-->>Alice: reply;
    """
    result = parser.parse(diagram)
    assert len(result.parse_errors) == 2
    assert "Semicolons are not allowed in sequence diagram message statements: 'Alice->>Bob: hello();'" in result.parse_errors[0]
    assert "Semicolons are not allowed in sequence diagram message statements: 'Bob-->>Alice: reply;'" in result.parse_errors[1]


def test_class_diagram_method_multiplicity_parser_bug223():
    repo = MockWorkspaceRepository()
    parser = MermaidClassDiagramParser(repo)
    
    diagram = """
    classDiagram
        class Node {
            +Boolean setLocation(Real lat, Real lon) [1]
        }
    """
    result = parser.parse(diagram)
    assert "Node" in result.classes
    methods = result.classes["Node"].methods
    assert len(methods) == 1
    assert methods[0].name == "setLocation"
    assert methods[0].return_type == "Boolean [1]"


def test_class_diagram_invalid_relationship_labels_and_notes():
    repo = MockWorkspaceRepository()
    parser = MermaidClassDiagramParser(repo)
    
    # 1. Invalid relationship label with spaces (unquoted)
    diagram1 = """
    classDiagram
        Locations *-- Racks : YANG path: locations slash racks
    """
    res1 = parser.parse(diagram1)
    assert len(res1.parse_errors) == 1
    assert "Syntax error: relationship label containing spaces or colons must be double-quoted" in res1.parse_errors[0]

    # 2. Valid relationship label with spaces (double-quoted)
    diagram2 = """
    classDiagram
        Locations *-- Racks : "YANG path: locations slash racks"
    """
    res2 = parser.parse(diagram2)
    assert len(res2.parse_errors) == 0
    assert len(res2.relationships) == 1
    assert res2.relationships[0].label == "YANG path: locations slash racks"

    # 3. Invalid note directive with unbalanced quote
    diagram3 = """
    classDiagram
        note for Racks "unclosed quote
    """
    res3 = parser.parse(diagram3)
    assert len(res3.parse_errors) == 1
    assert "Syntax error: note directive has unbalanced quotes" in res3.parse_errors[0]

    # 4. Valid note directive with balanced quotes
    diagram4 = """
    classDiagram
        note for Racks "balanced quote"
    """
    res4 = parser.parse(diagram4)
    assert len(res4.parse_errors) == 0
    assert "Racks" in res4.classes
    assert res4.classes["Racks"].notes == ["balanced quote"]




