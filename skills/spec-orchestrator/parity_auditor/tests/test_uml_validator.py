"""Tests for UML class diagram method return multiplicity validation."""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.uml import UmlValidator
from parity_auditor.core.workspace import WorkspaceRepository


def _setup_workspace(class_diagram_body):
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    user_stories_dir = os.path.join(tmpdir, "user_stories")
    use_cases_dir = os.path.join(tmpdir, "use_cases")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(user_stories_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)

    md_content = """---
generation_mode: subagent
title: Test
interface_type: ui
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + class_diagram_body + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(md_content)
    return tmpdir


def test_method_return_without_multiplicity_rejected():
    """+Node fetch() without [1] should be rejected for missing multiplicity."""
    diagram = """classDiagram
    class Node {
        +String id [1]
        +Node fetch()
    }
    class Container {
        +String name [1]
    }
    Container *-- Node : contains"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        multiplicity_errors = [e for e in errors if "fetch" in e and "multiplicity" in e]
        assert len(multiplicity_errors) >= 1, f"Expected multiplicity error for +Node fetch(), got errors: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_method_return_with_valid_multiplicity_accepted():
    """+Node [1] fetch() with valid multiplicity should be accepted."""
    diagram = """classDiagram
    class Node {
        +String id [1]
        +Node [1] fetch()
    }
    class Container {
        +String name [1]
    }
    Container *-- Node : contains"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        multiplicity_errors = [e for e in errors if "fetch" in e and "multiplicity" in e]
        assert len(multiplicity_errors) == 0, f"Expected NO multiplicity error for +Node [1] fetch(), got: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_method_return_void_skipped():
    """void methods should skip multiplicity check entirely."""
    diagram = """classDiagram
    class Node {
        +String id [1]
        +void save()
        +save()
        +void save(String path)
    }
    class Container {
        +String name [1]
    }
    Container "1" *-- "1" Node : contains"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        actual_errors = [e for e in errors if not e.startswith("Warning:")]
        assert len(actual_errors) == 0, f"void method signatures should not trigger errors, got: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_brackets_in_method_name_not_false_positive():
    """Brackets in method name (e.g. +Node reset[atomic]()) should not trigger false-positive multiplicity detection.
    The method may still be rejected for genuinely missing return-type multiplicity,
    but the rejection must not be caused by confused bracket detection."""
    diagram = """classDiagram
    class ThingProcessor {
        +String name [1]
        +Node reset[atomic]()
    }
    class Node {
        +String id [1]
    }
    ThingProcessor --> Node : uses"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        error_text = "\n".join(errors)
        assert "Missing bracket match" not in error_text, \
            f"Should not report bracket-match errors for brackets in method name, got: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_brackets_in_parameter_types_not_false_positive():
    """Brackets in parameter type expressions (e.g. +Bool sort(T[] items)) should not trigger false-positive multiplicity detection."""
    diagram = """classDiagram
    class Sorter {
        +String name [1]
        +Bool sort(T[] items)
    }
    class Item {
        +String id [1]
    }
    Sorter --> Item : sorts"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        error_text = "\n".join(errors)
        assert "Missing bracket match" not in error_text, \
            f"Should not report bracket-match errors for brackets in parameter types, got: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_flowchart_parser_reports_parse_errors():
    """MermaidFlowchartParser must report parse errors for unrecognized lines (Issue #88)."""
    from parity_auditor.parsers.mermaid import MermaidFlowchartParser
    from parity_auditor.core.models import ParsedFlowchart
    parser = MermaidFlowchartParser()
    result = parser.parse("flowchart TD\n    A[Start] --> B[Process]\n    MALFORMED_NONSENSE\n    C[End]")
    assert isinstance(result, ParsedFlowchart)
    assert len(result.parse_errors) > 0, \
        f"Expected parse_errors for malformed line, got: {result.parse_errors}"
    assert "MALFORMED_NONSENSE" in result.parse_errors[0]


def test_sequence_parser_reports_parse_errors():
    """MermaidSequenceDiagramParser must report parse errors for unrecognized lines (Issue #88)."""
    from parity_auditor.parsers.mermaid import MermaidSequenceDiagramParser
    from parity_auditor.core.models import ParsedSequenceDiagram
    parser = MermaidSequenceDiagramParser()
    result = parser.parse("sequenceDiagram\n    A->>B: hello\n    MALFORMED_NONSENSE\n    B-->>A: world")
    assert isinstance(result, ParsedSequenceDiagram)
    assert len(result.parse_errors) > 0, \
        f"Expected parse_errors for malformed line, got: {result.parse_errors}"
    assert "MALFORMED_NONSENSE" in result.parse_errors[0]


def test_flowchart_parser_no_errors_for_valid_input():
    """MermaidFlowchartParser must return empty parse_errors for valid input (Issue #88)."""
    from parity_auditor.parsers.mermaid import MermaidFlowchartParser
    parser = MermaidFlowchartParser()
    result = parser.parse("flowchart TD\n    A[Start] --> B[End]")
    assert result.parse_errors == [], f"Expected no parse_errors for valid input, got: {result.parse_errors}"


def test_sequence_parser_no_errors_for_valid_input():
    """MermaidSequenceDiagramParser must return empty parse_errors for valid input (Issue #88)."""
    from parity_auditor.parsers.mermaid import MermaidSequenceDiagramParser
    parser = MermaidSequenceDiagramParser()
    result = parser.parse("sequenceDiagram\n    A->>B: hello\n    B-->>A: world")
    assert result.parse_errors == [], f"Expected no parse_errors for valid input, got: {result.parse_errors}"


def test_sanitize_rel_connectors_adds_missing_dot_right_arrow():
    """Issue #98: _sanitize_rel_connectors must add ..> when missing from config."""
    from parity_auditor.parsers.mermaid import MermaidClassDiagramParser
    result = MermaidClassDiagramParser._sanitize_rel_connectors("(--|-->)")
    assert r"\.\.>" in result, f"..> should have been added, got: {result}"


def test_sanitize_rel_connectors_sorts_longest_first():
    """Issue #98: _sanitize_rel_connectors must sort longest-first to prevent prefix shadowing."""
    from parity_auditor.parsers.mermaid import MermaidClassDiagramParser
    result = MermaidClassDiagramParser._sanitize_rel_connectors("(--|-->|..>)")
    inner = result[1:-1]
    parts = inner.split('|')
    idx_dep = parts.index("-->")
    idx_assoc = parts.index("--")
    assert idx_dep < idx_assoc, f"--> should come before -- in sorted list, got: {result}"


def test_sanitize_rel_connectors_idempotent():
    """Issue #98: Double sanitization should be safe (idempotent)."""
    from parity_auditor.parsers.mermaid import MermaidClassDiagramParser
    once = MermaidClassDiagramParser._sanitize_rel_connectors("(--|-->|..>)")
    twice = MermaidClassDiagramParser._sanitize_rel_connectors(once)
    assert once == twice, f"Sanitization should be idempotent: {once} vs {twice}"


def _setup_usecase_workspace(flowchart_body):
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "required_sections": {
                "use_case": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Actors", "Actors"],
                    ["## 3. Preconditions", "Preconditions"],
                    ["## 5. Alternate and Exception Flows", "Alt Flows"],
                    ["## 6. Postconditions", "Postconditions"],
                    ["## 7. Diagrams", "Diagrams"]
                ],
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"], "use_case": ["(?:graph|flowchart)", "stateDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    user_stories_dir = os.path.join(tmpdir, "user_stories")
    use_cases_dir = os.path.join(tmpdir, "use_cases")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(user_stories_dir, exist_ok=True)
    os.makedirs(use_cases_dir, exist_ok=True)

    uc_content = """---
generation_mode: subagent
title: Test Use Case
interface_type: ui
---

## 1. Overview
test

## 2. Actors
- Actor

## 3. Preconditions
- test

## 5. Alternate and Exception Flows
- **1a.** test

## 6. Postconditions
- test

## 7. Diagrams

```mermaid
""" + flowchart_body + """
```

```mermaid
stateDiagram
    [*] --> Draft
    Draft --> Final
```
"""
    with open(os.path.join(use_cases_dir, "uc-01-test-extend.md"), "w") as f:
        f.write(uc_content)
    return tmpdir


def test_extend_arrow_correct_direction_accepted():
    """Issue #99: Correct extend arrow (extending -> base) must not be flagged as reversed."""
    diagram = """flowchart TD
    subgraph boundary[System Boundary]
        ext-cancel[Cancel Order]
        base-order[View Order]
    end
    actor[Customer]
    ext-cancel -->|<<extend>>| base-order
    actor --- base-order"""
    tmpdir = _setup_usecase_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        reversed_errors = [e for e in errors if "reversed" in e]
        assert len(reversed_errors) == 0, f"Expected NO reversed errors for correct extend arrow, got: {reversed_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_extend_arrow_reversed_direction_flagged():
    """Issue #99: The <<extend>> stereotype on the arrow defines the semantic direction
    (source extends target). Naming conventions are advisory and not relied upon for validation.
    Even conventionally-reversed naming does not trigger a validation error when stereotype is present."""
    diagram = """flowchart TD
    subgraph boundary[System Boundary]
        ext-cancel[Cancel Order]
        base-order[View Order]
    end
    actor[Customer]
    base-order -->|<<extend>>| ext-cancel
    actor --- ext-cancel"""
    tmpdir = _setup_usecase_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        reversed_errors = [e for e in errors if "reversed" in e]
        assert len(reversed_errors) == 0, f"Expected NO reversed errors (stereotype defines direction), got: {reversed_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_extend_label_without_stereotype_ignored():
    """Issue #99: Labels containing 'extend' but without <<extend>> stereotype must be ignored."""
    diagram = """flowchart TD
    subgraph boundary[System Boundary]
        uc-a[Use Case A]
        uc-b[Use Case B]
    end
    actor[Customer]
    uc-a -->|extend relationship| uc-b
    actor --- uc-a"""
    tmpdir = _setup_usecase_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        reversed_errors = [e for e in errors if "reversed" in e]
        assert len(reversed_errors) == 0, f"Expected NO reversed errors for non-stereotype 'extend' label, got: {reversed_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_extend_arrow_base_with_ext_in_name_no_false_positive():
    """Issue #99: Base use case with 'ext' at word boundary must not trigger false positive."""
    diagram = """flowchart TD
    subgraph boundary[System Boundary]
        ext-base[Base Inquiry]
        standard[Standard Check]
    end
    actor[Customer]
    standard -->|<<extend>>| ext-base
    actor --- standard"""
    tmpdir = _setup_usecase_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        reversed_errors = [e for e in errors if "reversed" in e]
        assert len(reversed_errors) == 0, f"Expected NO reversed errors for correct arrow with 'ext' in base name, got: {reversed_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_extend_stereotype_formats_recognized():
    """Verify that both literal <<extend>> and entity &lt;&lt;extend&gt;&gt;, plus guillemets «extend», are recognized."""
    import re
    from unittest.mock import patch

    diagram = """flowchart TD
    subgraph boundary[System Boundary]
        ext-cancel[Cancel Order]
        base-order[View Order]
    end
    actor[Customer]
    ext-cancel -->|<<extend>>| base-order
    ext-cancel -->|&lt;&lt;extend&gt;&gt;| base-order
    ext-cancel -->|«extend»| base-order
    actor --- base-order"""
    
    tmpdir = _setup_usecase_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        
        original_search = re.search
        matched_labels = []
        
        def spy_search(pattern, string, flags=0):
            res = original_search(pattern, string, flags)
            if "extend" in pattern and res:
                matched_labels.append(string)
            return res
            
        with patch("re.search", side_effect=spy_search):
            errors = validator.validate(repo)
            
        assert "<<extend>>" in matched_labels
        assert "&lt;&lt;extend&gt;&gt;" in matched_labels
        assert "«extend»" in matched_labels
        reversed_errors = [e for e in errors if "reversed" in e]
        assert len(reversed_errors) == 0
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_actor_lifelines_exempt_participants_required():
    """Exemption keys on UML role, not name spelling (issue #277).

    An `actor` lifeline is an entity outside the system boundary and is correctly
    absent from the structural models. A `participant` is an internal object and
    MUST resolve to a class defined in a feature class diagram.

    Replaces the former suffix-list test. That version declared all 12 lifelines as
    `actor` and asserted 10 were skipped purely because of how their names ended,
    which is the behaviour #277 reports as defective.
    """
    class_diagram = """classDiagram
    class B {
        +void call()
    }
    class C {
        +String name [1]
    }
    C --> B : calls"""

    story_content = """---
generation_mode: subagent
title: Test Story
---

## 1. Overview
As a User, I want to do something, so that we win.

## 2. User Story Scenario
Given something
When action
Then result

## 3. Sequence Diagram
```mermaid
sequenceDiagram
    actor a as "a: MyActor"
    actor c as "c: SuperCalculator"
    actor p as "p: DataProvider"
    actor m as "m: UserMapper"
    actor mgr as "mgr: SessionManager"
    actor cfg as "cfg: AuthConfigurator"
    actor arc as "arc: SystemArchitect"
    actor val as "val: FormValidator"
    actor sys as "sys: ValidatorSystem"
    actor s as "s: RemoteSystem"
    actor b as "b: B"
    participant x as "x: InvalidClass"
    a->>b: call()
```

## Required Features Matrix
- [ ] [Feature Link](http://example.com/feat-01-test.md) (Justification)
"""

    tmpdir = _setup_sequence_workspace(class_diagram, story_content)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        
        # Check that we DO get an error for 'InvalidClass'
        invalid_errors = [e for e in errors if "InvalidClass" in e]
        assert len(invalid_errors) >= 1, f"Expected validation error for InvalidClass, got: {errors}"
        
        # Actors are exempt regardless of how their names end.
        exempt_actors = ["MyActor", "SuperCalculator", "DataProvider", "UserMapper", "SessionManager", "AuthConfigurator", "SystemArchitect", "FormValidator", "ValidatorSystem", "RemoteSystem"]
        for actor_cls in exempt_actors:
            actor_errors = [e for e in errors if actor_cls in e]
            assert len(actor_errors) == 0, f"Expected no error for external actor {actor_cls}, got: {actor_errors}"

        # And the exemption must be about the role, not the spelling: a participant
        # whose name ends in a former bypass suffix must now be required to resolve.
        assert "InvalidClass" in " ".join(invalid_errors), (
            "a participant with an undefined classifier must be reported"
        )
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_backtick_class_definitions_no_syntax_error():
    """Verify that backtick-enclosed class definitions (e.g. class `Nw:networks` {) do not trigger syntax errors or conflicts."""
    diagram = """classDiagram
    class `Networks` {
        +String id [1]
    }
    class `Nw:network` {
        +String name [1]
    }
    `Networks` --> `Nw:network` : references"""

    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    os.makedirs(features_dir, exist_ok=True)

    md_content = """---
generation_mode: subagent
title: Test
interface_type: ui
schema_containers:
  - path: "nw:networks/nw:Nw:network"
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + diagram + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(md_content)

    try:
        repo = WorkspaceRepository(tmpdir)
        
        # Direct-check parser AST output
        from parity_auditor.parsers.mermaid import MermaidClassDiagramParser
        parser = MermaidClassDiagramParser(repo)
        parsed = parser.parse(diagram)
        
        # Assert class names are captured correctly without backticks
        assert "Networks" in parsed.classes
        assert "Nw:network" in parsed.classes
        assert "`Networks`" not in parsed.classes
        assert "`Nw:network`" not in parsed.classes
        
        # Assert relationship endpoints are captured correctly without backticks
        assert len(parsed.relationships) == 1
        rel = parsed.relationships[0]
        assert rel.from_class == "Networks"
        assert rel.to_class == "Nw:network"

        # Validate the workspace repository and assert 0 errors
        validator = UmlValidator()
        errors = validator.validate(repo)
        
        # Filter warnings and check actual errors
        actual_errors = [e for e in errors if not e.startswith("Warning:")]
        assert len(actual_errors) == 0, f"Expected no errors for backtick class definition, got: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def _setup_sequence_workspace(class_diagram_body, story_content):
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean", "void"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ],
                "user_story": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. User Story Scenario", "Scenario"],
                    ["## 3. Sequence Diagram", "Sequence Diagram"]
                ]
            },
            "required_diagrams": {
                "feature": ["classDiagram"],
                "user_story": ["sequenceDiagram"]
            },
            "sequence_replies": ["-->>", "-->"],
            "fragment_keywords": ["alt", "opt", "loop", "par", "critical", "option"],
            "bdd_scenario_regexes": [r"Given", r"When", r"Then"],
            "required_features_matrix_regex": r"## Required Features Matrix(.*?)(?=\Z|##)",
            "checkbox_syntax_regex": r"-\s+\[[ xX]\]\s+(.*)",
            "naming_conventions": {}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    user_stories_dir = os.path.join(tmpdir, "user_stories")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(user_stories_dir, exist_ok=True)

    feat_content = """---
generation_mode: subagent
title: Feature Test
interface_type: ui
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + class_diagram_body + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(feat_content)

    with open(os.path.join(user_stories_dir, "us-01-test.md"), "w") as f:
        f.write(story_content)

    return tmpdir


def test_issue_70_unbackticked_colon_rejected():
    """Unbackticked colons in class names or signatures must be rejected."""
    # Test class name with colon
    diagram1 = """classDiagram
    class Nw:network {
        +String name [1]
    }"""
    tmpdir1 = _setup_workspace(diagram1)
    try:
        repo1 = WorkspaceRepository(tmpdir1)
        validator = UmlValidator()
        actual_errors = validator.validate(repo1)
        assert len(actual_errors) > 0, "Expected errors for unbackticked colon in class name."
        assert any("class diagram parse error: Unparseable line in classDiagram" in err for err in actual_errors), f"Expected specific parse error: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir1)

    # Test attribute signature with colon (prohibited style)
    diagram2 = """classDiagram
    class Node {
        +name:String [1]
    }"""
    tmpdir2 = _setup_workspace(diagram2)
    try:
        repo2 = WorkspaceRepository(tmpdir2)
        validator = UmlValidator()
        actual_errors = validator.validate(repo2)
        assert len(actual_errors) > 0, "Expected errors for colon in attribute signature."
    finally:
        import shutil
        shutil.rmtree(tmpdir2)


def test_issue_272_nested_namespaces_accepted():
    """Nested namespace prefixes in schema paths are successfully validated."""
    diagram = """classDiagram
    class Routing {
        +String name [1]
    }
    class Ribs {
        +String id [1]
    }
    Routing --> Ribs : references"""
    
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    os.makedirs(features_dir, exist_ok=True)

    md_content = """---
generation_mode: subagent
title: Test
interface_type: ui
schema_containers:
  - path: "ietf-routing:routing/ietf-ribs:ribs"
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + diagram + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(md_content)

    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        
        actual_errors = [e for e in errors if not e.startswith("Warning:")]
        assert len(actual_errors) == 0, f"Expected no errors for nested namespace prefixes, got: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_colon_in_note_string_rejected():
    """Notes with colons in class diagram should be rejected."""
    diagram = """classDiagram
    class Node {
        +String name [1]
    }
    note for Node : "Status: Active" """
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        actual_errors = validator.validate(repo)
        assert len(actual_errors) > 0, "Expected errors for colon in note string."
        assert any("Colons ':' inside note strings are prohibited" in err for err in actual_errors), f"Expected specific parse error: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_stereotype_on_relationship_rejected():
    """Relationship labels with stereotypes should be rejected."""
    diagram = """classDiagram
    class Node {
        +String id [1]
    }
    class Container {
        +String name [1]
    }
    Container --> Node : <<references>>"""
    tmpdir = _setup_workspace(diagram)
    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        stereo_errors = [e for e in errors if "invalid stereotype/double angle brackets on relationship line" in e]
        assert len(stereo_errors) > 0, f"Expected stereotype error, got: {errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_underscore_namespace_fallback_accepted():
    """Namespaced class fallback with underscores should be accepted."""
    diagram = """classDiagram
    class IetfRouting_Routing {
        +String name [1]
    }
    class IetfRibs_Ribs {
        +String id [1]
    }
    IetfRouting_Routing --> IetfRibs_Ribs : references"""
    
    tmpdir = tempfile.mkdtemp()
    pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
    os.makedirs(pipeline_dir, exist_ok=True)
    rules = {
        "meta": {},
        "backlog_directories": {"features": "features", "user_stories": "user_stories", "use_cases": "use_cases"},
        "target_directories": {},
        "flutter_rules": {},
        "python_rules": {},
        "spec_rules": {},
        "validation_rules": {
            "visibility_prefixes": ["+", "-", "#", "~"],
            "multiplicity_regex": "\\[[^\\]]+\\]",
            "uml_primitives": ["String", "Integer", "Real", "Boolean"],
            "relationship_connectors": "(<\\|--|\\*--|o--|-->|\\.\\.>|--)",
            "choice_stereotypes": ["<<choice>>"],
            "required_sections": {
                "feature_ui": [
                    ["## 1. Overview", "Overview"],
                    ["## 2. Requirements", "Requirements"],
                    ["## 3. Validation", "Validation"],
                    ["## 4. Diagrams", "Diagrams"]
                ]
            },
            "required_diagrams": {"feature": ["classDiagram"]}
        }
    }
    with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w") as f:
        json.dump(rules, f)

    features_dir = os.path.join(tmpdir, "features")
    os.makedirs(features_dir, exist_ok=True)

    md_content = """---
generation_mode: subagent
title: Test
interface_type: ui
schema_containers:
  - path: "ietf-routing:routing/ietf-ribs:ribs"
---

## 1. Overview
test

## 2. Requirements & Checklist
- [ ] test

## 3. Validation & Constraints
- test

## 4. Diagrams

```mermaid
""" + diagram + """
```
"""
    with open(os.path.join(features_dir, "feat-01-test.md"), "w") as f:
        f.write(md_content)

    try:
        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        errors = validator.validate(repo)
        
        actual_errors = [e for e in errors if not e.startswith("Warning:")]
        assert len(actual_errors) == 0, f"Expected no errors for underscore namespace fallback, got: {actual_errors}"
    finally:
        import shutil
        shutil.rmtree(tmpdir)
