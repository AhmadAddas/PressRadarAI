# AGENTS.md

This file is the **always-on instruction router** for coding agents working in this repository.

Keep this file short.

Do not copy the full product specification, technology stack, or detailed engineering handbook into this file.

The goal is to load only the context required for the current task.

---

# 1. Sources of Truth

Each repository document owns a different kind of decision.

## `PROJECT.md` — Product

Authoritative for:

- Product requirements
- Business rules
- User workflows
- Domain behavior
- Feature scope
- MVP boundaries
- Acceptance criteria
- In-scope / out-of-scope behavior

Use it to answer:

> What should the product do, and why?

Do **not** read all of `PROJECT.md` by default.

Read only the sections relevant to the current task.

---

## `TECHSTACK.md` — Technology

Authoritative for:

- Languages
- Frameworks
- Databases
- AI providers
- Runtime modes
- Cloud/infrastructure choices
- External integrations
- Deployment architecture
- Tooling constraints

Use it to answer:

> What technology should be used?

Do **not** read all of `TECHSTACK.md` by default.

Read only the sections relevant to the current task.

---

## `docs/ENGINEERING.md` — Detailed Engineering Reference

Authoritative for detailed engineering guidance such as:

- Clean Architecture
- SOLID
- Clean Code
- KISS / YAGNI / DRY
- Testing
- ACID / transactions
- Concurrency
- Security
- Error handling
- Observability
- Refactoring
- Git workflow
- Conventional Commits
- Deployment safety
- Definition of Done

Do **not** read this file from top to bottom for every task.

Search or read only the sections relevant to the current work.

---

## Current Task — Immediate Scope

The user's current instruction defines:

> What should be changed now?

The current task is the implementation scope.

Do not implement unrelated requirements merely because they appear in `PROJECT.md`, `TECHSTACK.md`, or `docs/ENGINEERING.md`.

---

# 2. Context Loading Strategy

Before making changes:

1. Understand the current task.
2. Inspect the files likely affected.
3. Inspect nearby tests and similar existing implementations.
4. Read only the relevant section(s) of `PROJECT.md`.
5. Read only the relevant section(s) of `TECHSTACK.md`.
6. Read only the relevant section(s) of `docs/ENGINEERING.md`.
7. Apply any more specific nested `AGENTS.md` governing files you modify.
8. Implement the smallest complete change.

Do not front-load the entire repository documentation into context.

Use headings, search, and targeted reads.

---

# 3. Context Routing

Use this routing table.

| Current work touches | Read |
|---|---|
| Product behavior / business rules / user workflow | Relevant `PROJECT.md` section |
| Framework / provider / runtime / infrastructure choice | Relevant `TECHSTACK.md` section |
| Architecture / dependency direction / layering | `docs/ENGINEERING.md` architecture sections |
| Naming / abstractions / code organization | `docs/ENGINEERING.md` Clean Code / SOLID sections |
| Tests / mocking / deterministic behavior | `docs/ENGINEERING.md` testing sections |
| Database integrity / transactions / concurrency / idempotency | `docs/ENGINEERING.md` ACID / concurrency sections |
| Authentication / authorization / secrets / validation | `docs/ENGINEERING.md` security sections |
| External APIs / retries / failure handling | `docs/ENGINEERING.md` robustness / external-service sections |
| Performance | `docs/ENGINEERING.md` performance sections |
| Git / commit boundaries / Conventional Commits | `docs/ENGINEERING.md` Git sections |
| Deployment / migrations / operations | Relevant `TECHSTACK.md` + deployment sections of `docs/ENGINEERING.md` |

If a concern is not relevant to the task, do not load its detailed guidance.

---

# 4. Conflict Resolution

When instructions appear to conflict, use this order:

```text
Current explicit user task
        ↓
Most specific applicable AGENTS.md
        ↓
Document ownership
        ├── Product / business behavior → PROJECT.md
        ├── Technology / runtime        → TECHSTACK.md
        └── Engineering practice        → docs/ENGINEERING.md
        ↓
Existing repository conventions
        ↓
Smallest reasonable documented assumption
```

Do not silently guess when a conflict materially affects:

- Product behavior
- Security
- Data integrity
- Public contracts
- Architecture
- Technology selection
- Destructive operations

For minor, reversible implementation details, choose the simplest option consistent with the authoritative documents and continue.

---

# 5. Always-On Engineering Rules

These rules apply to every task without requiring the full engineering handbook.

- Inspect before changing.
- Do not invent APIs, file paths, fields, environment variables, functions, or project conventions.
- Reuse existing patterns before creating new ones.
- Preserve existing behavior unless the task explicitly changes it.
- Make the smallest complete change that satisfies the requirement.
- Keep business logic out of presentation and vendor-specific infrastructure where practical.
- Prefer simple, explicit, testable code over clever abstractions.
- Validate external input.
- Handle expected failures deliberately.
- Never commit secrets.
- Do not weaken security controls to make development easier.
- Add or update appropriate tests for behavior changes.
- Do not weaken tests merely to make them pass.
- Review the final diff.
- Do not modify unrelated files.
- Do not perform destructive Git operations without explicit permission.
- Do not claim tests, linting, type checks, or builds passed unless they were actually run.

---

# 6. Architecture Defaults

Use the existing repository architecture first.

Do not introduce a second architecture because another approach is theoretically cleaner.

Where the project uses layered or Clean Architecture boundaries, preserve dependency direction conceptually:

```text
Presentation
    ↓
Application / Use Cases
    ↓
Domain / Business Rules
    ↑
Infrastructure / Providers
```

Architecture is about dependency boundaries, not folder ceremony.

Do not create interfaces, repositories, factories, services, or wrappers unless they solve a real problem.

Prefer:

- KISS
- YAGNI
- Meaningful DRY
- Composition over inheritance
- Explicit dependencies
- Moderate abstraction

---

# 7. Task Sizing

## Small Tasks

For small, obvious, low-risk changes:

- Inspect the relevant area.
- Make the smallest safe change.
- Run relevant validation.
- Review the diff.
- Commit appropriately.

Do not create unnecessary plans or architecture documents.

## Non-Trivial Tasks

For larger work, identify:

- Scope
- Affected layers
- Data changes
- Public contract impact
- Integration impact
- Security implications
- Failure modes
- Backward compatibility
- Test strategy
- Logical commit boundaries

Then implement incrementally.

Do not stop after planning unless explicitly asked only for a plan.

---

# 8. Git Rules

Use Git incrementally.

Do **not** place an entire feature, project, or unrelated set of changes into one giant commit.

Each commit should represent one coherent change.

Use Conventional Commit style:

```text
feat:
fix:
refactor:
test:
docs:
chore:
build:
ci:
perf:
style:
```

Examples:

```text
feat(clients): add client creation flow
fix(opportunities): prevent duplicate ingestion
refactor(ai): extract provider boundary
test(pitches): add approval workflow regression tests
docs: document local setup
chore: configure linting
```

Avoid vague messages such as:

```text
update
changes
fix stuff
final
done
misc
wip
```

Before each commit:

1. Inspect `git status`.
2. Review the staged diff.
3. Remove unrelated or accidental files.
4. Check for secrets and debug code.
5. Run relevant validation.
6. Confirm the commit is one coherent change.
7. Use an accurate Conventional Commit message.

Do not rewrite existing history, force-push, hard-reset, rebase, or amend existing commits unless explicitly requested.

---

# 9. Validation

Before completion, run the relevant repository-provided checks when available.

Examples:

```text
formatter
linter
type checker
unit tests
integration tests
build
security checks
```

Use existing repository scripts and tooling instead of inventing parallel commands.

If a validation step cannot be run, state that clearly.

Never fake successful verification.

---

# 10. Required Workflow

For substantial coding tasks:

```text
1. Understand the current task
2. Inspect affected code and nearby tests
3. Read relevant PROJECT.md sections
4. Read relevant TECHSTACK.md sections
5. Read relevant docs/ENGINEERING.md sections
6. Apply nested AGENTS.md rules if present
7. Plan only as much as needed
8. Implement the smallest complete change
9. Add/update tests
10. Run validation
11. Review the diff
12. Fix discovered issues
13. Commit the logical unit
14. Repeat only if additional logical units remain
15. Perform final repository review
```

Do not load unrelated documentation merely because it exists.

---

# 11. Required Final Handoff

For substantial work, summarize:

## Implemented

What changed.

## Architecture

Only meaningful architectural decisions or boundaries affected.

## Files

Important files created or modified.

## Tests

Tests added or updated.

## Validation

Exactly what was run.

Do not claim commands were run if they were not.

## Git

List the exact commit messages created.

## Remaining

List genuine limitations, risks, TODOs, or follow-up work.

If nothing relevant remains, say so.

---

# 12. Responsibility Map

Keep responsibilities distinct:

```text
PROJECT.md              = WHAT the product does and WHY
TECHSTACK.md            = WITH WHAT technologies and runtime modes
AGENTS.md               = HOW to route and execute work
docs/ENGINEERING.md     = DETAILED engineering reference
Nested AGENTS.md        = AREA-SPECIFIC engineering rules
Current task            = WHAT must change NOW
README.md               = HOW humans set up, run, and use the repository
```

Do not create multiple sources of truth.

---

# 13. Final Rule

Do not merely make code work.

Make the smallest appropriate solution that is:

- Correct
- Understandable
- Maintainable
- Testable
- Secure
- Consistent with the existing repository

Load only the context needed to do that well.
