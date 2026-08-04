---
title: "Feature 06: Upstream Ingestion and Auto-Regression Testing"
type: "feature"
interface_type: "api"
generation_mode: "subagent"
spec_source: "Project Constitution"
---

# Feature: Upstream Ingestion and Auto-Regression Testing

## Parent Epic
- [ ] #[EpicID] - [Epic Title](../epics/epic-XX-name.md) (semantic linkage justification)

## Description
Ensures that filed bugs are ingested into the upstream repository's test suite to verify fixes and prevent future regression of reported tooling issues.

## UML Class Diagram
```mermaid
classDiagram
    class IngestionSubsystem {
        +IngestionWorkflow workflow [1]
    }
    class IngestionWorkflow {
        +Boolean[1] parseIssueBody(String body)
        +void writeReproCase(String snippet, String filename)
        +Boolean[1] runRegressionTests(String repoUrl)
        +void closeIssue(String issueId)
    }
    IngestionSubsystem *-- IngestionWorkflow
```

## Interface Requirements
### 1. Payload Schema
- Input: GitHub Issue created by Feature 05.
- Output: Test file written to `tests/repro_cases/[issue_number].md`.

### 2. Test Data Shape
- See feat-01 for base payload schema and validation rules.

### 3. Logical Operations & Interface Messages
1. Upstream GitHub Action triggers on issue creation with `bug` or `feature` labels.
2. The Action parses the JSON payload from the issue description.
3. The Action writes the `snippet_content` to a local test file.
4. The Action executes the validators against the new test file to verify failure.
5. Post-patching, the suite ensures the case passes, merges the fix, and automatically closes the issue.

### 4. Logical Exception States & Validation Failures
1. If the Action receives a corrupted or unparsable JSON payload, it comments on the issue requesting manual formatting and exits.
