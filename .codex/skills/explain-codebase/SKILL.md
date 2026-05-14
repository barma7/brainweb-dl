---
name: explain-codebase
description: Read-only codebase investigation and explanation. Use when Codex needs to answer focused questions such as "how does this work?", "where is this implemented?", "why does this behavior happen?", "what calls this API?", "what would be affected by changing this?", or when a primary agent wants a subagent thinking partner to explain relevant code behavior without modifying files.
---

# Explain Codebase

## Overview

Use this skill to investigate a repository and explain the behavior, structure, data flow, tests, APIs, or implementation details relevant to a focused user question. Treat the session as read-only: gather evidence, reason from code, and return an explanation the primary agent or user can act on.

## Read-Only Contract

- Do not create, edit, delete, move, format, or generate files.
- Do not use `apply_patch`, redirect output to files, install dependencies, run migrations, start services, or execute commands whose normal purpose is to mutate the workspace.
- Avoid test commands unless the user explicitly asks for verification; tests often write caches or generated artifacts.
- If the request asks for implementation, fixing, refactoring, committing, or any other change, explain that this skill is for investigation only and return the relevant findings for the primary agent to use.
- If a command unexpectedly changes files, stop, report the command, and include `git status --short` if available.

## Investigation Workflow

1. Restate the focused question in operational terms, including the code paths or behavior to inspect.
2. Read repository guidance first when present: `AGENTS.md`, relevant OpenSpec files, package metadata, and local docs that clearly apply to the question.
3. Locate code with read-only search commands. Prefer `rg`, `rg --files`, `git grep`, `Get-Content`, `Select-String`, `git show`, and `git status --short`.
4. Follow the execution path across definitions, call sites, configuration, tests, and data models until the behavior is explained.
5. Distinguish facts directly supported by code from inferences. Say what evidence supports each important conclusion.
6. Stop when the question is answered; do not broaden into unrelated refactors or speculative design work.

## Evidence Standards

- Cite concrete files and line numbers for important claims whenever possible.
- Prefer local source, tests, and specs over memory or assumptions.
- When code and documentation disagree, call out the disagreement and treat the code as the behavior currently implemented.
- Mention uncertainty explicitly when dynamic dispatch, generated files, external services, missing dependencies, or inaccessible files prevent a complete answer.
- Keep examples small and anchored to the actual codebase.

## Answer Shape

Return a concise explanation that leads with the answer, then the supporting evidence.

For most questions, include:

- Direct answer: the relevant behavior or structure.
- Evidence: file and line references that support the explanation.
- Flow: a short sequence of how data/control moves through the relevant code, when useful.
- Caveats: missing context, assumptions, or risks.
- No-change note: state that no files were modified.

Avoid long inventories. If many files are involved, group them by role instead of listing every match.

## Subagent Usage

When used as a subagent from a primary agent:

- Stay within the delegated question and do not duplicate unrelated primary-agent work.
- Do not make changes in the forked workspace.
- Return findings in a form the primary agent can reuse directly, especially paths, symbols, call chains, and caveats.
- If the primary prompt is ambiguous, choose the most likely interpretation and state it. Ask a question only when answering would otherwise require guessing at a risky or irreversible fact.
