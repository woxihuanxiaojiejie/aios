# Repository Guidelines

## Project Structure & Module Organization

AIOS is a pure Python 3.12 kernel under `src/aios`. Core Pydantic entities,
enums, and errors live in `src/aios/kernel`. Adapter protocols live in
`src/aios/adapters`, storage implementations in `src/aios/storage`, and lifecycle
coordination in `src/aios/workflows`. Tests are split into `tests/unit` and
`tests/integration`.

Do not add API servers, databases, trading integrations, schedulers, Docker
files, UI code, or framework scaffolding for future tasks.

## Build, Test, and Development Commands

- `uv sync`: create the virtual environment and install runtime/dev
  dependencies.
- `uv run ruff check .`: run lint checks.
- `uv run ruff format --check .`: verify formatting without rewriting files.
- `uv run mypy src`: type-check the package.
- `uv run pytest -q`: run tests with coverage enforcement.

## Coding Style & Naming Conventions

Use ruff formatting with 4-space indentation and 88-character lines. Keep models
small, explicit, and side-effect free. Entity IDs must use UUID-backed prefixes:
`ev_`, `ex_`, `dc_`, `rv_`, and `lr_`. Store all datetimes as timezone-aware UTC
values; never accept naive datetimes.

## Testing Guidelines

Use pytest. Unit tests should cover model validation, enum constraints, ID
prefixes, storage behavior, and missing reference failures. Integration tests
should run the complete lifecycle:
`Evidence -> Experiment -> Decision -> Review -> Learning`. Coverage must stay at
or above 90%.

## Commit & Pull Request Guidelines

This repository has no commit history yet. Use concise, imperative commit
messages such as `Add minimal decision lifecycle kernel`. Pull requests should
state scope, list verification commands run, and call out any intentionally
deferred AIOS V0.1 requirements.

## Agent-Specific Instructions

Treat the current repository as the only source of truth. Do not read, migrate,
or reference old project code. Keep each change scoped to the V0.1 kernel unless
the user explicitly starts a later task.

## Long-Term Development Rules

- Prefer reusing current project implementations before adding new code.
- Prefer mature, actively maintained open source components with clear licenses.
- Build original implementations only when existing options cannot satisfy AIOS
  core business needs.
- Do not use mock data in production runtime paths.
- Do not reimplement backend business logic in the frontend for Decision,
  Settlement, Evaluation, Review, Learning, or related lifecycle behavior.
- Do not modify, delete, or submit files unrelated to the current task.
- Do not run `git clean` or `git reset --hard`.
- Do not modify user-created untracked files.
- Execute only the currently specified Milestone.
- After each Milestone, run build, test, type-check, and `git diff --check`.
- Do not continue into the next phase unless explicitly requested.
- Keep exactly one frontend project: `frontend/`.
- Do not introduce a second React project, a second UI framework, or a low-code
  production frontend.
- Do not scatter hard-coded API URLs across pages or call `fetch` directly from
  pages.
- Do not copy backend data into multiple independent frontend state sources.
- Production commits must contain only files related to the current phase.
