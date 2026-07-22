# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Keep this file an index and a rule set — point to the canonical doc rather than duplicating code-shaped content. `PRD.md` is the canonical product/architecture spec; per-context `CONTEXT.md` files are the canonical domain glossaries.

## Project Overview

OpenBragg is a Python-first, open-source, proton-focused treatment planning system (TPS) for radiotherapy. Phase 1 targets a correct, validatable, end-to-end **dose recalculation / verification** pipeline (DICOM-RT proton case → data model → wrapped dose engine → DVH → visualization → RTDOSE export, with provenance logging and a gamma-analysis regression harness). See `PRD.md` for the full spec and design decisions.

## Architecture

The design principles are architectural, not feature-count — read `PRD.md` before working across modules. The load-bearing ideas:

- **Dose-engine seam is the primary seam.** It takes (image + material map + beam/geometry + plan spots) and returns a `Dij` influence matrix plus geometry/units metadata. The rest of the pipeline never talks to an engine directly — only to `Dij`. Get this seam right first; don't add a parallel path around it.
- **Dij-first everywhere.** The engine's fundamental output is a sparse voxels×spots dose-influence matrix; total dose is `Dij · w`. Plan recomputation (Phase 1) and future optimization (Phase 2) consume the identical object.
- **Engine-agnostic, process-boundary wrapping.** External engines (MCsquare, OpenTOPAS, …) are invoked across a subprocess/CLI boundary, never linked — this insulates the project from their licenses and enforces the seam. Any future in-house engine sits behind the *same* interface.
- **Provenance-first.** Every dose calculation writes a run manifest (input hashes, engine identity + version, parameters, OpenBragg version, grid/units) sufficient to reproduce the result.
- Reference engines (MCsquare, OpenTOPAS) and OpenTPS are **validation oracles only** — never sources of copied code. The GPLv3 OpenTPS GUI is off-limits even for reference.

## Development Commands

Don't run Python scripts, pytest, and similar Python-based commands directly. Instead prepend those commands with `uv run` to ensure the proper environment is created/updated and used.

```bash
# Setup
uv sync                              # Explicitly create/update virtual environment
uv run pre-commit install            # Setup pre-commit hooks

# Testing
uv run pytest                        # Run all tests
uv run pytest path/to/test.py::test_name  # Run a single test

# Code quality
uv run black .                       # Format code inplace
uv run isort --only-modified .       # Sort imports in modified files only
uv run pyright                       # Type check
```

_(The project isn't scaffolded yet — `pyproject.toml`, the test tree, and pre-commit config land with the first code. These are the intended tools; wire them as part of that first scaffold.)_

### Run the checks constantly — this is your feedback loop

Run these early and often, not as a final checklist.

- **After any change, before moving on:** `uv run pyright` and the tests you touched.
- **Fix lint, type errors, test failures, and flakiness you encounter — even if unrelated to your task.** A red signal is never someone else's problem to leave behind.
- **Write tests first; red-green-refactor.** Reproduce every bug with a failing test in the most end-user-aligned (E2E) setting you can before fixing — this surfaces the real problem so the fix actually solves it.
- **Redirect long-running command output** (dose-engine runs, full test suites, gamma sweeps) to a log file rather than letting it flood your context — inspect the log, don't stream everything back.

## Coding Standards

### Code Style
- Python 3.12+ (numpy/scipy/sparse-linear-algebra fluency is an asset here — lean on it for the Dij plumbing).
- Type-checked with pyright (follow the `pyproject.toml` config once it exists rather than assuming a mode).
- KISS/YAGNI: implement only what's needed. Phase-2 optimization is *architecturally protected*, not built now.
- **Imports at module top** — place all `import` statements at the top of the file. Do not inline imports inside functions. If moving an import to the top triggers a circular import, fix the dependency direction (the cycle is the real problem) rather than hiding it with a function-body import.

### Tests
- **Tests live in the top-level `tests/` tree**, mirroring the package layout — never under `src/`. Test code must not ship inside the installed package.
- **Assert on external behavior, not implementation details.** For a TPS this means: given known inputs, assert on dose distributions, DVH metrics, gamma pass rates, and exported DICOM — not on internal data structures.
- **Layered validation** (open data/software only, for now): analytic (Bortfeld Bragg-peak model, NIST PSTAR stopping powers) → reference-engine gamma analysis (3%/3mm, 2%/2mm) vs MCsquare/OpenTOPAS → full-pipeline cross-check vs OpenTPS. The gamma + DVH regression harness is a first-class Phase-1 module, wired into CI.
- **Don't weaken tests to make them pass.** A failing test is a signal — diagnose the root cause first. Adding new tests and cases is expected (TDD); but before changing or deleting an *existing* test's assertions or intent, confirm the change preserves what the test was protecting.

## Domain Terms & Decisions

Per-context `CONTEXT.md` files (indexed by `CONTEXT-MAP.md` at the repo root) are the glossary **and canonical naming source** — consult before naming a symbol, reuse their terms over synonyms, sharpen entries as you go. Record hard-to-reverse, surprising trade-offs as ADRs under `docs/adr/` (system-wide) or `src/<context>/docs/adr/` (context-specific). The `/domain-modeling` skill maintains both; see `docs/agents/domain.md` for the consumer rules.

## Collaboration

Always ask me questions to clarify relevant aspects of the code you are unsure about — the purpose of an abstraction you're refactoring, or domain knowledge about a physics model you're implementing.

When domain knowledge about proton therapy is important (dose physics, Bragg-peak/range behavior, HU→RSP conversion, DVH/gamma metrics, DICOM-RT semantics), **search primary sources to inform yourself** before implementing — don't guess at the physics.

## Debugging

When debugging, always investigate the actual root cause before implementing a fix. Do not assume the first hypothesis is correct — trace the error through the full call stack, verify with diagnostic scripts, and confirm the fix addresses the true cause (not a symptom).

## Git & Files

- Commit only files relevant to the task — never `git add .`.
- **Never hand-edit auto-generated files** — regenerate instead (e.g. `uv.lock` via `uv lock`).
- **Don't commit working/user-local files** — plan docs, scratch analysis, session-local files. Note `.gitignore` already excludes patient data (`*.dcm`, `*.nii*`, `data/`, `cases/`) and large engine artifacts (`*.npz`, `influence/`, `engine_runs/`) — never commit clinical data or large simulation output.

## Review Your Own Work

After a **large body of work** (feature, refactor, multi-file bugfix), run `/code-review` — it reviews the branch against this repo's standards and against the originating issue/PRD. Trigger at a work-phase boundary, not per-commit.

## PR Demo Notebooks

Every PR that adds user-facing functionality ships a demo notebook under `notebooks/`, named `pr<NUM>_<slug>.ipynb` (e.g. `pr17_photon_recompute_demo.ipynb`). It should:

- **Be self-contained and runnable without clinical data** — synthesize any input in the notebook (in the real on-disk format), since datasets are git-ignored. Note where the same API points at real data.
- **Exercise the actual package API** end-to-end (import from `openbragg.*`, not copied logic), and state honest limits (plumbing vs. physics validation).
- **Ship with outputs embedded** — execute before committing: `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/pr<NUM>_<slug>.ipynb`. `ipykernel`/`nbconvert` are dev deps.

## Signal a Good Time to Compact

When context usage is ~30% or more and you reach a good checkpoint (a work-phase boundary, or a big fan-out just returned), flag that it's a good moment to compact and suggest a one-line focus for what to carry forward. Commit or note state first so the checkpoint is clean.

## Agent skills

### Issue tracker

Issues and PRDs are tracked as GitHub issues via the `gh` CLI (repo `EBHolm/openbragg`). External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary — `needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context — `CONTEXT-MAP.md` at the repo root points to a `CONTEXT.md` per context. See `docs/agents/domain.md`.
