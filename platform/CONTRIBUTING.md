# Contributing

Personal repo, but written like a contributing doc so future-me (or a future collaborator) doesn't have to reverse-engineer the conventions.

## Dev workflow

### Branches

- `main` is the working branch. Direct commits are normal for personal work.
- For larger or experimental work, branch from main: `git checkout -b feat/<thing>`. Merge with `--no-ff` once stable so the merge commit captures the unit of work.
- Never force-push `main`. Force-push of feature branches is fine.

### Commit messages

Conventional Commits style:

- `feat(<scope>):` - new functionality
- `fix(<scope>):` - bug fix
- `refactor(<scope>):` - restructuring without behavior change
- `docs:` - docs only
- `chore:` - repo housekeeping
- `test:` - test additions

Subject line <=72 chars, present tense, imperative mood. Body explains *why* if non-obvious. Co-author tag at the bottom if AI-assisted.

Scope is usually the package name (`kb`, `intel`, `config`, `tools`) or a cross-cutting concern (`mcp`, `infra`, `docs`).

### Tags

Annotated tags mark release-equivalent milestones. Format: `v<major>.<minor>-<short-descriptor>`. Example: `v0.6-cli-tools`, `v0.7-organized`. The descriptor should describe what shipped, not the context (avoid context-specific names like `v0.6-demo-ready`).

## Code style

### Formatting

`ruff` configured at the workspace root (`pyproject.toml [tool.ruff]`). Line length 110. Run `ruff check` and `ruff format` before committing significant changes.

### Type hints

Required on public functions. Pydantic models for any data structure that crosses a layer boundary. `from __future__ import annotations` at the top of every module so forward references work without quoting.

### SQLAlchemy

- Use `select()` + `await session.execute()` - sync ORM is forbidden in this codebase, all DB access is async.
- `session_scope()` is the entrypoint (from `dayzstack_shared.db`). Don't construct sessions or engines directly.
- Schema lives via `__table_args__ = ({"schema": "<name>"},)` per layer.
- Migrations are owned per-package; each package has its own `alembic.ini` and `migrations/`.

### Logging

`structlog` configured in `dayzstack_shared.logging`. Call `setup_logging()` at the top of any CLI entrypoint. Use `structlog.get_logger()` rather than `logging.getLogger()`.

## Testing approach

Currently there is essentially no test suite (a placeholder dir in `config_mod`, that's it). This is acknowledged technical debt; see `docs/reference/known-debt.md`.

When you do add tests, the layered approach:

- **Parsers** - contract tests with bundled fixture files. Parse -> assert structure -> diff against expected.
- **Snapshotters** - integration tests against recorded API responses (record once with VCR or similar, replay always).
- **CLI tools** - smoke tests that invoke the CLI as a subprocess, assert exit code and presence of expected substrings in output.

Don't aim for 100% coverage. Aim for coverage of the things that, if they regressed, would silently corrupt the database.

## How to add a new layer or module

1. **Decide the package name.** Format: `dayzstack_<noun>`. The directory under the workspace root usually matches (with the `dayzstack_` prefix dropped, e.g. `kb/` -> `dayzstack_kb`). The exception is `config_mod/` -> `dayzstack_config` because `config` was a builtin Python package concern at scaffold time; new packages don't need that workaround.

2. **Decide the schema name.** If the layer owns Postgres tables, give them their own schema (`kb`, `intel`, `config`, etc.). Don't share schemas across packages.

3. **Create the workspace member.** Pattern:
   ```
   <pkg>/
   |-- pyproject.toml         # name = dayzstack-<noun>, deps include dayzstack-shared
   |-- alembic.ini            # if owns tables
   |-- migrations/
   |   |-- env.py
   |   `-- versions/
   `-- src/dayzstack_<noun>/
       |-- __init__.py
       |-- cli.py             # if has CLI
       |-- models.py          # SQLAlchemy ORM
       `-- ...
   ```

4. **Register in workspace.** Add to `pyproject.toml` `[tool.uv.workspace] members` and `[tool.uv.sources]`. Run `uv sync`.

5. **Write the alembic migration.** `cd <pkg> && uv run alembic revision -m "initial schema" --autogenerate` is the start. Verify by hand; alembic gets schema-aware migrations *almost* right but not always.

6. **Add MCP tools (optional).** If the layer should expose tools to agents, register them in `kb/src/dayzstack_kb/mcp/server.py`. The MCP server is centralized - don't spin up a second one per layer. Lazy-import the new module to avoid hard cross-layer dependency.

7. **Document it.** Add `docs/architecture/<noun>-layer.md` with: what / why / storage / surface / decisions.

## Session-based development

This codebase has been built across numbered sessions, each with a planning prompt and a handoff doc. The pattern:

- Session prompts and per-session planning artifacts live in `~/Dayz/dayz-stack-planning/` - **outside the repo on purpose**, so context-specific framing doesn't pollute the durable repo content.
- Each session ends with an updated `02-handoff.md` covering: what got built, current state, pickup priorities for next session.
- Tags mark significant session boundaries (`v0.6-cli-tools`, `v0.7-organized`, etc.).

If continuing this pattern:

- Read `~/Dayz/dayz-stack-planning/02-handoff.md` first when starting a session.
- Update it at the end. Don't drop the historical numbered planning docs - they're the build log.
- Keep the framing in repo docs durable (third-person, generalized, no "private interpersonal specifics" specifics). Sensitive personal context should stay out of repo docs.

## Pull request expectations (if collaborating)

- One concern per PR. If a PR touches multiple layers, split it.
- Tests are not yet required. Smoke-test by hand and document what you did in the PR description.
- Reviewer-friendly commit history. Squash trivial WIP commits before opening.
