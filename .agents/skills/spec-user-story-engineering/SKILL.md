<!-- Copyright Gint Atkinson, gint.atkinson@gmail.com -->

---
name: spec-user-story-engineering
description: "Extracts BDD User Stories from normative specification documents using OOA/OOD modeling. Use when you need to derive behavioral scenarios (Given-When-Then) from protocol specs and matrix them against existing Feature issues in the repository."
compatibility: "Requires issue tracker CLI and git. Works with modern agentic development environments."
metadata:
  title: "Specification User Story Engineering (Behavioral Extraction)"
  category: architecture
  risk: low
  source: custom
  version: "2.0"
---

# Specification User Story Engineering (Behavioral Extraction)

This skill enables a sub-agent to autonomously read a normative specification document (e.g., domain-specific specifications and API documentation) and extract its behavioral deployment scenarios into pure Behavior-Driven Development (BDD) User Stories modeled according to Object-Oriented Analysis and Design (OOA/OOD) principles, linking them dynamically to structural features already defined in the repository.

## Execution Trigger
You should invoke this skill ONLY after the structural Features have been extracted using the `schema-specification-engineering` skill.

### Algorithmic & Calculation Story Extraction Trigger (Mandatory)
In addition to standard deployment scenarios, you MUST scan the specification and schema for any derived, computed, or calculated values (e.g. performing unit conversions, coordinate transformations, validation ranges, formulas, or elapsed time checks). For every calculated or derived value identified, you MUST extract a dedicated, mandatory User Story that details the calculations, formulas, or algorithmic transformations required, ensuring that these dynamic behaviors are fully captured.

### Temporal & Lifecycle Expiration Story Extraction Trigger (Mandatory)
In addition to standard deployment scenarios, you MUST scan the specification and schema for any temporal/lifecycle expirations, state-decay lifecycles, or timeout transitions (e.g. token expiration, data staleness, status-based data access rules, or lifecycle decay). For every temporal or lifecycle expiration identified, you MUST extract a dedicated, mandatory User Story detailing the transition to the expired state and any postconditions for accessing data in that state.

## Step 1: Context Ingestion (Operational Text & Schemas)
1. Ingest the target normative specification document AND the target structural schemas (e.g., structural or protocol schemas).
2. **Scan the structural schema definitions** (specifically node descriptions, comments, type restrictions, and validation constraints) to identify:
   - Any derived, calculated, or computed data fields.
   - Any mathematical formulas, equations, unit conversions, or derivations.
   - Any temporal attributes or state lifecycles.
3. Target and analyze the following operational chapters of the normative specification:
   - Introduction & Applicability
   - Deployment Scenarios
   - Operational Considerations
   - Security Considerations
   - Algorithmic, Calculation, or Derivation clauses

## Step 2: Isolated User Story Modeling (Subagent Dispatch Loop)

1. **Identify Scenarios & Triggers:** Analyze the specification chapters and structural schemas to determine all required deployment scenarios, calculations/derivations, and temporal/state lifecycles. Compile the list of target User Stories to be engineered.
2. **Dispatch User Story Subagent:** For each identified User Story, invoke a **new, fresh subagent with an isolated context**. Pass ONLY the specific operational text, relevant schema definitions, related Feature specs, and the User Story template. The subagent must have no visibility or knowledge of other User Stories.
3. **Execution within Subagent Context:**
   - **Compliance Table Mandate:** Before writing the file, you MUST output a structured compliance table checking for lifeline aliasing (e.g. 'actorName : Classifier'), open return arrows ('-->'), return value assignment signatures (no method call format), and Given-When-Then BDD scenarios.
   - **Behavioral Modeling:** Model the scenario as a formal User Story integrated with OOA/OOD principles:
     - Identify the Actor/Role (the object or entity initiating the action).
     - Formulate the core scenario using strict BDD syntax mapped to object interactions (`Given`/`When`/`Then` or `As a`/`I want to`/`So that`).
     - Map the story to specific Domain Objects (the structural schema entities affected).
     - **UML Sequence Diagram**: Include a **UML Sequence Diagram** (using Mermaid `sequenceDiagram`) illustrating the dynamic interaction between the Actor and specific Domain Objects.
       - *Lifeline Notation*: All sequence diagrams must use the standard UML lifeline notation `name : Classifier` or `: Classifier` (using Mermaid alias syntax: `actor userActor as "userActor : UserActor"` or `participant domainRegistry as "domainRegistry : DomainRegistry"`). Do not use naked classifier names or simple `Actor` names.
       - *Actor vs Participant (enforced — issue #277)*: The choice of keyword is semantic, not cosmetic, and determines whether the classifier must exist in a Feature class diagram.
         - Declare a lifeline `actor` **only** when it represents an entity **outside the system boundary** — a human role, or a third-party system you do not model. An `actor` classifier is **exempt** from the structural-definition requirement, because external entities are correctly absent from the structural models.
         - Declare a lifeline `participant` for every **internal** object. A `participant` classifier **MUST** be defined as a class in some Feature's UML Class Diagram, and every message sent to it must map to a public operation on that class. A lifeline referenced in a message without being declared defaults to `participant` and is therefore also required to resolve.
         - The exemption keys on the **role**, never on the classifier's name. Naming an internal object `SessionManager` or `PaymentValidator` does not exempt it; declaring it `participant` requires it to resolve.
       - *Open Return Arrow*: Return/reply messages must use the open arrowhead (`-->` in Mermaid) instead of the filled/closed arrowhead (`-->>`).
       - *Return Value Signatures*: Return messages must represent assignments/return values (e.g. `isValid : Boolean`) rather than method/operation calls.
       - *Operation Matching*: Every call/message in a sequence diagram must map to a public operation/method (with camelCase signature and typed arguments) on the receiver lifeline's classifier in the class diagrams.
       - *Combined Fragment Guards*: Guards on conditional/looping blocks (e.g. `alt`, `loop`, `opt`) must be enclosed in standard UML square brackets `[guard]`.
       - *Validation Loops/Conditional Blocks*: Use Mermaid `alt` or `loop` blocks to explicitly illustrate input validation loops.
       - *Helper/Calculator Object Delegation*: Do not model the main container handling complex computations directly; delegate to specialized helper or utility objects.
     - **UML State Machine Diagram**: Include state transitions, guards, events, and actions using Mermaid `stateDiagram-v2` (mandatory if the story involves state transitions or lifecycle expirations).
       - *Notation*: States must be in PascalCase. Transitions must be annotated with `event [guard] / action` on the transition arrow. Use `[*]` for entry/exit points. Use `-. label .->` syntax for dotted links.
   - **The Cross-Cutting Matrix (Feature Linking):**
     - Inspect the provided structural features to determine exactly which of those `#IssueID`s are prerequisites for the current User Story.
     - Construct the `## Required Features` matrix containing a markdown tasklist of these intersecting links referencing BOTH the Issue ID and the absolute URL of the feature document.
     - Every checklist item in the matrix MUST include a concise parenthetical justification explaining the semantic linkage.
   - **Markdown Generation:** Write the User Story as a local markdown file (e.g., `docs/user-stories/us-01-register-entity.md`).
4. **Return Control:** The subagent completes the task and returns control to the worker agent.

## Step 4: Markdown Generation
Create a new file in `docs/user-stories/us-[XX]-[name].md` (zero-padded, dash-separated, e.g., `us-01-register-entity.md`).
> **Unified Slugification Mandate:** When generating filenames from titles (e.g., `us-29-fiber-cable-and-strand-inventory.md`), you MUST preserve all stop-words (like 'and', 'the', 'of', etc.) consistently. Do NOT strip stop-words when converting titles to lowercase hyphen-separated slugs.

Format strictly:

````markdown
---
title: "[User Story Title]"
type: "user-story"
generation_mode: "subagent"
spec_source: "[Spec Reference]"
---

# User Story: [Title]

## Parent Epic
- [ ] #[EpicIssueID] - [Epic Title]([Repository Base URL]/<blob_path>/[Branch Name]/docs/epics/epic-XX-name.md) (semantic linkage justification)

## Domain Object Mapping
- **Primary Domain Objects:** [List affected structural schema entities]
- **Actor/Role:** [The object/entity initiating the action]

## BDD Scenario (OOA/OOD Realization)
**Given** [Initial system/object state]
**When** [Triggering action/event/message]
**Then** [Resulting system/object state]

*(Alternatively)*
**As a** [Actor]
**I want to** [Action]
**So that** [Outcome/State Change]

## UML Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor userActor as "userActor : UserActor"
    participant domainRegistry as "domainRegistry : DomainRegistry"
    participant businessLogicService as "businessLogicService : BusinessLogicService"

    userActor->>domainRegistry: operationName(attributeName: DataType)
    alt [payloadIsValid == true]
        domainRegistry->>businessLogicService: validateBounds(attributeName: DataType)
        businessLogicService-->domainRegistry: isValid : Boolean
        alt [isValid == true]
            Note over domainRegistry: Store value
            domainRegistry-->userActor: status : Status
        else [isValid == false]
            domainRegistry-->userActor: "status : Status"
        end
    else [payloadIsValid == false]
        domainRegistry-->userActor: status : Status
    end
```

## UML State Machine Diagram
*(Mandatory if the story involves state transitions or lifecycle expirations)*
```mermaid
stateDiagram-v2
    [*] --> InitialState
    InitialState --> ActiveState : "activate [activationCodeIsValid == true] / initializeSession"
    ActiveState --> TerminatedState : "expire [timeElapsed >= timeoutLimit] / cleanupResources"
    TerminatedState --> [*]
```

## Operational Context
[Verbatim operational constraints or deployment scenarios quoted from the specification]

## Required Features Matrix
- [ ] #[IssueID] - [Feature Title]([Repository Base URL]/<blob_path>/[Branch Name]/docs/features/feat-XX-name.md) (semantic linkage justification)
- [ ] #[IssueID] - [Feature Title]([Repository Base URL]/<blob_path>/[Branch Name]/docs/features/feat-XX-name.md) (semantic linkage justification)

## Logical UI & Interface Bindings
*(Required for UI/LUMI features. Raw 'N/A' fallback strings and literal placeholder strings ('#X', 'Task Y') are strictly prohibited.)*
<!-- Single-Channel (Visual GUI) Format -->
- **Target LUI Component:** [Specify canonical LUI component e.g. StringInputField, TableView, PropertyGrid, OR 'Unbound (Deferred to Implementation Profile)']
- **Target Layout Container ID:** [Specify container ID from logical-layout.json, OR 'Unbound (Deferred to Implementation Profile)']
- **Data Source Bindings:** [Specify exact, authoritative schema path locator e.g. /nwi:network-inventory/nil:locations/nil:location/nil:geo-location/nil:reference-frame, OR 'Unbound (Deferred to Implementation Profile)']

<!-- OR Multi-Channel (Multi-Interface) Format -->
| Interface Channel | Category | Target Component / Handler | Target Container / Endpoint | Data Source Binding |
| --- | --- | --- | --- | --- |
| gui | Visual GUI | StringInputField | elements_view | /schema:path |
| mcp | M2M API | MCPToolHandler | /mcp/tool | /schema:path |

## Source References
> [!IMPORTANT]
> **Dynamic Schema Locator**: You MUST inspect the active workspace directories (e.g. `schema/`) to build schema locators dynamically. Do NOT hardcode legacy paths like `standard/ietf/RFC/`.

Structural Schema: [Target Schema File](link-to-schema)
Normative Specification: [Normative Specification](link-to-specification)
````

> [!WARNING]
> **Mermaid Block Closing Constraints & Code Fence Integrity:**
> - Every Mermaid diagram MUST be strictly closed with ```` ``` ```` on a new line. Leaking Mermaid blocks (e.g. having headings like `##` inside an unclosed diagram) or stray/unclosed code fences will fail downstream validation checks.
> - Ensure there are no stray backticks or unmatched code fences in the document.
> - **All Mermaid syntax constraints are defined in `rules/platform-independence.md` and MUST be observed in full** — including the prohibition on semicolons in `Note` and message text, colons in class members and note strings, stereotypes on relationship lines, and curly braces in class member lines. Do not maintain a local subset here; subsets drift (issue #289).



## Step 5: Zero-Fault Backlog Synchronization
1. **Mandatory Local Validation Gate:** Before committing, pushing, or creating issues in the backlog, the subagent MUST execute the local validation check:
   ```bash
   ./skills/spec-orchestrator/scripts/verify_model_coverage.py --spec-only --allow-missing-specs
   ```
   If the linter fails (returns a non-zero exit code), the subagent MUST parse the errors, fix all generated User Story markdown files, and re-run the linter until it passes with exit code 0.
   Before committing the generated markdown files, the agent MUST run a check for untracked pipeline infrastructure files. If untracked files are found in `.pipeline/`, `skills/`, `rules/`, or `scripts/`, they must be staged and committed alongside the markdown files using `git add` to prevent remote divergence:
   ```bash
   UNTRACKED_INFRA=$(git ls-files --others --exclude-standard .pipeline/ skills/ rules/ scripts/)
   if [ -n "$UNTRACKED_INFRA" ]; then
     git add .pipeline/ skills/ rules/ scripts/
   fi
   ```
   Once the linter passes, commit and push the Markdown files to the remote repository.
2. Verify the `user-story` label exists in the tracker repository, bootstrapping it if necessary.
3. **Duplicate Detection:** Before creating, query the active tracker provider for all existing user story issues to check if an issue with an identical or semantically equivalent title already exists. If found, skip creation and reuse the existing Issue ID.
4. Register the User Story issue natively with the active tracker provider.
   - **Crucial Verification & Body Synchronization:**
     1. Backlog issues MUST be registered using the deterministic title extraction step:
        ```bash
        TITLE=$(awk -F': ' '/^title:/ {print $2}' <local-md-file> | tr -d '"' | tr -d "'")
        gh issue create --title "$TITLE" --body-file <local-md-file>
        ```
        (to ensure they start with the full markdown content, including diagrams and references).
     2. Immediately after placeholder resolution (when the live issue ID is injected back into the file), the subagent MUST execute `gh issue edit <ID> --body-file <local-md-file>` to sync the resolved ID body.
     3. The subagent MUST run a post-creation verification check:
        `gh issue view <ID> --json body | python3 -c "import sys,json; b=json.load(sys.stdin)['body']; assert 'Source References' in b or 'References' in b, 'Body is a stub'"`
        and retry/halt if this verification fails.
5. Verify the creation and return the generated issue URLs/IDs to the Orchestrator or User.
