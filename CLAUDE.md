# Agent Instructions

## Required reads, in this order

Read these before starting any task:

1. `.agents/AGENTS.md` — project-scoped agent rules, including the **Strict Planning
   Gate**. Read this FIRST. It is the strictest authorization rule in the repository.
2. `.pipeline/constitution.md` — Tier 1 functional constitution.
3. All `SKILL.md` files in `skills/` — the pipeline workflows.
4. All rule files in `rules/` — mandatory constraints applying to every task.

For implementation work, additionally read
`.pipeline/profiles/<platform>.md` for the target platform.

## Hidden directories

`.agents/` and `.pipeline/` are hidden. Glob and ripgrep index queries skip them, so
they will not appear in search results. Read them by explicit path. A file that is
absent from the list above and invisible to search is effectively invisible — that is
how the strictest authorization rule came to be missed (issue #295).

## Before writing anything

No file may be created, modified, or deleted unless that specific file and its exact
changes are documented in an approved `implementation_plan.md`. An authorization
keyword such as "PROCEED" alone is **not** sufficient. Writing or updating the plan
itself is the sole exception. See `.agents/AGENTS.md` § *Strict Planning Gate*.

## Issue lifecycle

Agents stop at `Fixed / Resolved`. `Closed` requires Product Owner validation and is
unreachable by an agent. See `.pipeline/constitution.md` § *CMMI Level 3 & Scrum Issue
Lifecycle Rules*.
