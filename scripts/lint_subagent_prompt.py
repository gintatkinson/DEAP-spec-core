#!/usr/bin/env python3
"""
Physical Subagent Prompt Payload Linter (`scripts/lint_subagent_prompt.py`)

Mechanically enforces prompt payload invariants for subagent dispatch:
1. Rule 1 (Single-Task Enforcement):
   - Rejects prompts containing multi-item numbered task lists (e.g., Work Items: 1... 2... 3... or multiple \\n[0-9]+\\.\\s+).
   - Rejects prompts containing multiple imperative task verbs across disparate domains (e.g., combining authoring + filing + coding).
   - Rejects prompts referencing > 1 target specification item / file (e.g. multiple FEAT-xxx IDs or spec markdown files).
2. Rule 2 (Skill Template Match):
   - When a prompt invokes a standardized skill like `adversarial-code-auditor`, enforces exact compliance with the skill's
     documented Section 5 dispatch template (starts with `Execute adversarial-code-auditor skill.` and contains
     `FILE_PATH: ... PILLAR: ... MODE: ... REPO: ... PROCEED`).
3. Rule 3 (Zero Inline Issue Body):
   - Flags any prompt attempting to pass inline `--body "..."` or `-b "..."` issue commands instead of `--body-file`.

Usage:
    python3 scripts/lint_subagent_prompt.py [--transcript path.jsonl | --file path | --prompt "text"] [--json-report report.json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


# ==============================================================================
# Helper Functions & Strippers
# ==============================================================================

def strip_code_blocks(text: str) -> str:
    """Strips markdown fenced code blocks and inline code spans to prevent false positives in code snippets."""
    # Strip multi-line fenced code blocks ```...```
    cleaned = re.sub(r'```[\s\S]*?```', '', text)
    # Strip inline code spans `...`
    cleaned = re.sub(r'`[^`\n]+`', '', cleaned)
    return cleaned


def extract_task_payload(prompt: str) -> str:
    """Extracts the task payload portion of a prompt, stripping the governance preamble if present."""
    if "---GOVERNANCE-END---" in prompt:
        parts = prompt.split("---GOVERNANCE-END---", 1)
        return parts[1]
    return prompt


# ==============================================================================
# Rule 1: Single-Task Enforcement
# ==============================================================================

def lint_single_task_enforcement(prompt: str) -> List[str]:
    """Enforces that subagent prompts are strictly single, atomic tasks."""
    violations: List[str] = []
    task_payload = extract_task_payload(prompt)
    clean_task = strip_code_blocks(task_payload)

    # 1. Multi-item numbered task lists
    # Check for explicit list headers: e.g. "Work Items:", "Tasks:", "Subtasks:", "TODO list:"
    header_pattern = re.search(
        r'(?i)\b(?:work\s*items?|tasks?|subtasks?|todo\s*list|action\s*items?)\s*:\s*(?:\n\s*[-*0-9]+|\s*[0-9]+[\.\)])',
        clean_task
    )
    if header_pattern:
        violations.append(
            "Rule 1 Violation (Single-Task Enforcement): Multi-item numbered task list detected in prompt. "
            "Subagent prompts must specify a single, atomic task."
        )

    # Check for 2 or more numbered lines in the task payload
    numbered_lines = re.findall(r'^\s*[0-9]+[\.\)]\s+\S+', clean_task, re.MULTILINE)
    if len(numbered_lines) >= 2 and not header_pattern:
        violations.append(
            f"Rule 1 Violation (Single-Task Enforcement): Multiple numbered task items ({len(numbered_lines)}) "
            "detected in prompt. Subagent prompts must be single, atomic tasks."
        )

    # 2. Multiple imperative task verbs across disparate domains
    domains_found: List[str] = []

    # Domain A: Authoring / Specification Domain
    if re.search(r'(?i)\b(?:author\s+(?:the\s+|a\s+)?(?:feature|spec|epic|user\s+story|use\s+case|documentation)|draft\s+(?:the\s+|a\s+)?(?:feature|spec|epic|user\s+story|use\s+case)|create\s+(?:a\s+|the\s+)?(?:feature|spec(?:ification)?|epic)|generate\s+(?:a\s+|the\s+)?(?:feature|spec(?:ification)?|epic)|spec(?:ification)?\s+authoring)\b', clean_task):
        domains_found.append("Authoring")

    # Domain B: Filing / Issue Tracking Domain
    if re.search(r'(?i)\b(?:file\s+(?:an?\s+)?(?:issue|ticket|bug|finding)|create\s+(?:an?\s+)?(?:issue|ticket|bug)|submit\s+(?:an?\s+)?(?:issue|ticket|bug)|gh\s+issue\s+create|glab\s+issue\s+create|filing\s+(?:issues?|tickets?|bugs?))\b', clean_task):
        domains_found.append("Filing")

    # Domain C: Coding / Implementation Domain
    if re.search(r'(?i)\b(?:implement(?:ation|ing)?|develop(?:ing)?|refactor(?:ing)?|write\s+(?:the\s+)?(?:code|backend|frontend|logic)|build\s+(?:the\s+)?(?:feature|component|code)|fix\s+(?:the\s+)?bug|coding)\b', clean_task):
        domains_found.append("Coding")

    if len(domains_found) >= 2:
        violations.append(
            f"Rule 1 Violation (Single-Task Enforcement): Multiple disparate domain task verbs detected ({', '.join(domains_found)}). "
            "Subagents must focus on a single domain."
        )

    # 3. References to > 1 target specification item / file
    # Distinct spec identifiers (e.g. FEAT-001A, EPIC-002, US-003, UC-004)
    spec_id_matches = re.findall(r'\b(?:FEAT|EPIC|US|UC)-[0-9]+[A-Za-z]?\b', clean_task, re.IGNORECASE)
    unique_spec_ids = {s.upper() for s in spec_id_matches}

    # Distinct spec files (e.g. docs/features/feat-001a-fuselage.md)
    spec_file_matches = re.findall(r'\bdocs/(?:features|epics|user-stories|use-cases)/[a-zA-Z0-9_\-\.]+\.md\b', clean_task, re.IGNORECASE)
    unique_spec_files = {f.lower() for f in spec_file_matches}

    if len(unique_spec_ids) > 1 or len(unique_spec_files) > 1:
        detected_items = sorted(list(unique_spec_ids | unique_spec_files))
        violations.append(
            f"Rule 1 Violation (Single-Task Enforcement): References to multiple target specification items/files detected ({', '.join(detected_items)}). "
            "Subagent prompts must target at most one specification item."
        )

    return violations


# ==============================================================================
# Rule 2: Skill Template Match
# ==============================================================================

def lint_skill_template_match(prompt: str) -> Tuple[bool, List[str]]:
    """Enforces exact Section 5 dispatch template match when standardized skills are invoked.
    
    Returns (is_skill_prompt, violations_list).
    """
    violations: List[str] = []
    stripped = prompt.strip()

    # Check if prompt invokes adversarial-code-auditor
    is_adversarial_auditor = "adversarial-code-auditor" in prompt.lower() or stripped.startswith("Execute adversarial-code-auditor")
    if not is_adversarial_auditor:
        return False, []

    # 1. Must start with exact Section 5 opening line
    if not stripped.startswith("Execute adversarial-code-auditor skill."):
        violations.append(
            "Rule 2 Violation (Skill Template Match): Prompt invoking 'adversarial-code-auditor' must start with "
            "'Execute adversarial-code-auditor skill.'"
        )

    # 2. Must contain required field placeholders with values
    for field in ("FILE_PATH", "PILLAR", "MODE", "REPO"):
        pattern = rf'\b{field}:\s*(\S+)'
        match = re.search(pattern, prompt)
        if not match:
            violations.append(
                f"Rule 2 Violation (Skill Template Match): Missing required field '{field}:' in adversarial-code-auditor dispatch template."
            )

    # 3. Must contain PROCEED token
    if not re.search(r'\bPROCEED\b', prompt, re.IGNORECASE):
        violations.append(
            "Rule 2 Violation (Skill Template Match): Missing 'PROCEED' authorization token in adversarial-code-auditor dispatch template."
        )

    return True, violations


# ==============================================================================
# Rule 3: Zero Inline Issue Body
# ==============================================================================

def lint_zero_inline_issue_body(prompt: str) -> List[str]:
    """Flags any prompt attempting to pass inline --body issue commands instead of --body-file."""
    violations: List[str] = []

    # Detect inline --body or -b flag (excluding --body-file)
    # Matches --body "...", --body '...', --body=..., -b "...", -b '...'
    inline_body_pattern = re.search(
        r'(?<![\w\-])(?:--body(?!\s*-\s*file\b)|-b)\s*(?:=\s*["\']|\s+["\']|=?\s*[^\s\-]+)',
        prompt
    )
    # Also check simpler direct matches:
    # 1. Any --body that is not --body-file
    has_raw_body = re.search(r'(?<![\w\-])--body(?!-file\b)(?:[\s=]|$)', prompt)
    # 2. Any -b followed by a quoted string or argument
    has_short_b = re.search(r'(?<![\w\-])-b\s*[\s=]\s*["\']|(?<![\w\-])-b\s+["\']', prompt)

    if inline_body_pattern or has_raw_body or has_short_b:
        violations.append(
            "Rule 3 Violation (Zero Inline Issue Body): Inline issue body detected (--body / -b). "
            "All issue creation in subagent prompts must use --body-file instead of inline body arguments."
        )

    return violations


# ==============================================================================
# Main Public Function: lint_prompt_payload
# ==============================================================================

def lint_prompt_payload(prompt: str) -> List[str]:
    """Lints a subagent prompt payload for compliance with physical dispatch invariants:
    - Rule 1: Single-Task Enforcement (no multi-task lists, no multi-domain verbs, max 1 spec item/file).
    - Rule 2: Skill Template Match (exact compliance for standardized skills like adversarial-code-auditor).
    - Rule 3: Zero Inline Issue Body (enforces --body-file over inline --body).

    Returns:
        List of error violation strings (empty list [] if compliant).
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        return ["Prompt payload is empty or invalid."]

    violations: List[str] = []

    # Rule 3: Zero Inline Issue Body (always checked)
    violations.extend(lint_zero_inline_issue_body(prompt))

    # Rule 2: Standardized Skill Template Match
    is_skill_dispatch, skill_violations = lint_skill_template_match(prompt)
    if is_skill_dispatch:
        violations.extend(skill_violations)
        # If it is a standardized skill dispatch template, Rule 1 domain checks do not apply to the fixed template text
        return violations

    # Rule 1: Single-Task Enforcement
    violations.extend(lint_single_task_enforcement(prompt))

    return violations


# ==============================================================================
# Transcript Extraction Helpers
# ==============================================================================

def _extract_prompt_from_dict(obj: Dict[str, Any]) -> Optional[str]:
    """Extracts subagent prompt payload from a dictionary structure."""
    # Check for direct prompt key
    if obj.get("name") in ("invoke_subagent", "subagent_dispatch", "dispatch_subagent"):
        if "prompt" in obj and isinstance(obj["prompt"], str):
            return obj["prompt"]
        if "payload" in obj and isinstance(obj["payload"], str):
            return obj["payload"]
        if "task" in obj and isinstance(obj["task"], str):
            return obj["task"]
        if "input" in obj and isinstance(obj["input"], dict) and "prompt" in obj["input"]:
            return obj["input"]["prompt"]
        if "parameters" in obj and isinstance(obj["parameters"], dict) and "prompt" in obj["parameters"]:
            return obj["parameters"]["prompt"]
        if "arguments" in obj:
            args = obj["arguments"]
            if isinstance(args, str):
                try:
                    parsed_args = json.loads(args)
                    if isinstance(parsed_args, dict) and "prompt" in parsed_args:
                        return parsed_args["prompt"]
                except json.JSONDecodeError:
                    pass
            elif isinstance(args, dict) and "prompt" in args:
                return args["prompt"]

    # Check for Anthropic style tool_use
    if obj.get("type") == "tool_use" and obj.get("name") in ("invoke_subagent", "subagent_dispatch"):
        tool_input = obj.get("input", {})
        if isinstance(tool_input, dict) and "prompt" in tool_input:
            return tool_input["prompt"]

    # Check for OpenAI style tool_calls
    if "tool_calls" in obj and isinstance(obj["tool_calls"], list):
        for tc in obj["tool_calls"]:
            if isinstance(tc, dict):
                fn = tc.get("function", {})
                if isinstance(fn, dict) and fn.get("name") in ("invoke_subagent", "subagent_dispatch"):
                    args = fn.get("arguments")
                    if isinstance(args, str):
                        try:
                            parsed = json.loads(args)
                            if isinstance(parsed, dict) and "prompt" in parsed:
                                return parsed["prompt"]
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(args, dict) and "prompt" in args:
                        return args["prompt"]

    return None


def extract_prompts_from_transcript(transcript_input: Union[str, Path, Iterable[str]]) -> List[Tuple[int, str]]:
    """Extracts all `invoke_subagent` prompt payloads from a transcript (JSONL file, path, or string lines).
    
    Returns:
        List of tuples (line_number_or_call_index, prompt_text).
    """
    prompts: List[Tuple[int, str]] = []

    lines: List[str] = []
    if isinstance(transcript_input, (str, Path)) and os.path.exists(str(transcript_input)):
        with open(str(transcript_input), "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    elif isinstance(transcript_input, str):
        lines = transcript_input.splitlines()
    elif isinstance(transcript_input, Iterable):
        lines = list(transcript_input)

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                p = _extract_prompt_from_dict(data)
                if p:
                    prompts.append((idx, p))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        p = _extract_prompt_from_dict(item)
                        if p:
                            prompts.append((idx, p))
        except json.JSONDecodeError:
            # If not valid JSON, check if line contains prompt marker or treat non-empty line
            if "Execute adversarial-code-auditor" in stripped or "TASK:" in stripped:
                prompts.append((idx, stripped))

    return prompts


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Physical Subagent Prompt Payload Linter enforcing single-task atomicity, template matching, and zero inline issue bodies."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to transcript JSONL file, prompt file, or raw prompt string."
    )
    parser.add_argument(
        "-t", "--transcript", "-f", "--file",
        dest="file_path",
        help="Path to transcript JSONL file or prompt text file."
    )
    parser.add_argument(
        "-p", "--prompt",
        dest="prompt_str",
        help="Raw prompt string to lint directly."
    )
    parser.add_argument(
        "-r", "--json-report", "--report",
        dest="report_path",
        help="Optional path to output structured JSON report."
    )

    args = parser.parse_args()

    prompts_to_lint: List[Tuple[str, str]] = []

    # Priority 1: Explicit --prompt argument
    if args.prompt_str:
        prompts_to_lint.append(("cli_prompt", args.prompt_str))

    # Priority 2: Explicit --transcript or --file argument
    elif args.file_path:
        target = Path(args.file_path)
        if target.is_file():
            if target.suffix == ".jsonl":
                extracted = extract_prompts_from_transcript(target)
                for line_no, p in extracted:
                    prompts_to_lint.append((f"{target.name}:L{line_no}", p))
            else:
                content = target.read_text(encoding="utf-8", errors="replace")
                # Try parsing as JSONL first, fallback to raw text
                extracted = extract_prompts_from_transcript(target)
                if extracted:
                    for line_no, p in extracted:
                        prompts_to_lint.append((f"{target.name}:L{line_no}", p))
                else:
                    prompts_to_lint.append((str(target), content))
        else:
            print(f"Error: File not found: {args.file_path}", file=sys.stderr)
            sys.exit(1)

    # Priority 3: Positional input argument
    elif args.input:
        target = Path(args.input)
        if target.is_file():
            if target.suffix == ".jsonl":
                extracted = extract_prompts_from_transcript(target)
                for line_no, p in extracted:
                    prompts_to_lint.append((f"{target.name}:L{line_no}", p))
            else:
                content = target.read_text(encoding="utf-8", errors="replace")
                extracted = extract_prompts_from_transcript(target)
                if extracted:
                    for line_no, p in extracted:
                        prompts_to_lint.append((f"{target.name}:L{line_no}", p))
                else:
                    prompts_to_lint.append((str(target), content))
        else:
            # Treat positional argument as raw prompt string
            prompts_to_lint.append(("raw_input", args.input))

    # Priority 4: Stdin if piped
    elif not sys.stdin.isatty():
        stdin_content = sys.stdin.read()
        extracted = extract_prompts_from_transcript(stdin_content)
        if extracted:
            for line_no, p in extracted:
                prompts_to_lint.append((f"stdin:L{line_no}", p))
        else:
            prompts_to_lint.append(("stdin", stdin_content))

    else:
        parser.print_help()
        sys.exit(1)

    # Lint all gathered prompts
    total_violations = 0
    results: List[Dict[str, Any]] = []

    for source_label, prompt_text in prompts_to_lint:
        violations = lint_prompt_payload(prompt_text)
        is_pass = (len(violations) == 0)
        if not is_pass:
            total_violations += len(violations)

        results.append({
            "source": source_label,
            "passed": is_pass,
            "violations": violations,
            "prompt_preview": prompt_text.strip()[:120] + "..." if len(prompt_text.strip()) > 120 else prompt_text.strip()
        })

    # Terminal output
    print(f"\nSubagent Prompt Payload Linter: Processed {len(prompts_to_lint)} prompt(s).")
    for r in results:
        if r["passed"]:
            print(f"  [PASS] {r['source']}: {r['prompt_preview']}")
        else:
            print(f"  [FAIL] {r['source']}:")
            for v in r["violations"]:
                print(f"    - {v}")

    # Generate JSON report if requested
    report_data = {
        "status": "PASS" if total_violations == 0 else "FAIL",
        "total_prompts": len(prompts_to_lint),
        "total_violations": total_violations,
        "results": results
    }

    if args.report_path:
        out_path = Path(args.report_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        print(f"\nReport written to: {args.report_path}")

    if total_violations > 0:
        print(f"\nLinter FAILED with {total_violations} violation(s).\n")
        sys.exit(1)
    else:
        print("\nAll subagent prompt payloads PASSED.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
