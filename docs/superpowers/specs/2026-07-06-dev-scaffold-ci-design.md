# Dev scaffold & CI — design

Originating issue: [#3 — Dev scaffold & CI: test tree, pre-commit, pytest, GitHub Actions](https://github.com/EBHolm/openbragg/issues/3)

Date: 2026-07-06

## Goal

Stand up the development feedback loop and CI so every later slice builds against a
green baseline. This is prefactoring — it lands before any domain code. Success is
issue #3's acceptance criteria: `pytest`, `pyright`, `black --check`, and
`isort --check-only` all pass locally; `pre-commit install` wires those tools;
a GitHub Actions workflow runs on push/PR and is green; `uv run openbragg --help`
executes; and `tests/` mirrors the package layout with no test code under `src/`.

## Starting point

Already present: `pyproject.toml` (deps `numpy`, `matplotlib`; hatchling build;
`requires-python >=3.12`) and `src/openbragg/__init__.py` (`__version__ = "0.0.0"`).
Missing: dev dependencies, tool config, `tests/` tree, `.pre-commit-config.yaml`,
`.github/workflows/`, a CLI entry point, and `.python-version`.

## Decisions

- **CLI framework: Typer.** The `openbragg` command is where Phase-1 slices
  (`ingest`, `recompute`, `export`) will hang subcommands. Typer derives the CLI
  from type-hinted function signatures, so the CLI surface is the same thing pyright
  checks — no drift between parser and function. It ships as a runtime dependency
  (built on Click). Chosen over stdlib `argparse` (zero-dep but hand-synced,
  `str`/`Namespace` output) and `click` (decorators declared separately from the
  function) because the project's trajectory is a growing, type-checked subcommand tree.
- **pyright mode: strict.** Greenfield, numpy/scipy-heavy, correctness-critical
  (dose math, units, Dij shapes). Keep the type checker maximally loud while the code
  is small and habits are forming. Relax specific rules per-module (e.g. untyped
  third-party engine wrappers) rather than lowering the global bar.
- **Dev dependencies via PEP 735 `[dependency-groups]`.** uv-native `dev` group,
  installed by default on `uv sync`, excluded from the shipped wheel.
- **Local `uv run` pre-commit hooks (not upstream mirror repos).** Tool versions
  come from `uv.lock`, so pre-commit, `uv run <tool>`, and CI share a single source
  of truth and cannot drift.
- **CI runs `pre-commit run --all-files` + `pytest`.** Same lint/type coverage as
  local dev with no duplicated tool invocations.
- **Single Python 3.12 in CI (no matrix).** YAGNI; a 3.13 row is a trivial later add.

## Components

### `pyproject.toml`
- Add `typer` to `[project.dependencies]`.
- Add `[dependency-groups]` `dev = ["pytest", "black", "isort", "pyright", "pre-commit"]`.
- `[project.scripts]` → `openbragg = "openbragg.cli:app"`.
- Tool config:
  - `[tool.pyright]`: `typeCheckingMode = "strict"`, `include = ["src", "tests"]`.
  - `[tool.isort]`: `profile = "black"`.
  - `[tool.black]`: defaults (line length 88).
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`.

### `src/openbragg/cli.py`
- A Typer `app` with a `--version` callback that reads `openbragg.__version__` and a
  built-in `--help`. No real subcommands yet — later slices register onto this `app`.
- Satisfies "`uv run openbragg --help` executes".

### `tests/openbragg/test_cli.py`
- Top-level `tests/` tree mirroring the package layout; no test code under `src/`.
- Smoke test via Typer's `CliRunner`: `--help` exits 0; `--version` exits 0 and prints
  the version. Asserts on external CLI behavior (per the repo testing rule) and gives
  CI a non-trivial green suite.

### `.pre-commit-config.yaml`
- Local hooks invoking `uv run black`, `uv run isort`, `uv run pyright`.
- black and isort run on pre-commit-supplied changed files (matching the
  "only-modified" intent); pyright runs project-wide.

### `.github/workflows/ci.yml`
- Triggers: push and pull_request.
- One job on `ubuntu-latest`, Python 3.12.
- Steps: checkout → `astral-sh/setup-uv` → `uv sync` →
  `uv run pre-commit run --all-files` → `uv run pytest`.

### `.python-version`
- `3.12`, so uv provisions a consistent interpreter locally and in CI.

## Out of scope (YAGNI)

Coverage / `pytest-cov`, a Python version matrix, release/publish workflows, and
dependabot. Each is a trivial add once a real need appears.

## Acceptance criteria (from issue #3)

- [ ] `uv run pytest`, `uv run pyright`, `uv run black --check .`, and
  `uv run isort --check-only .` all pass locally.
- [ ] `uv run pre-commit install` works and the hooks run black/isort/pyright.
- [ ] A GitHub Actions workflow runs on push/PR and is green.
- [ ] `uv run openbragg --help` executes.
- [ ] `tests/` mirrors the package layout and contains no code under `src/`.
