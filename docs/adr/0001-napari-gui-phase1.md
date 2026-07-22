# Interactive napari GUI promoted into Phase 1

**Status:** accepted (2026-07-22)

We are building an interactive 3D viewer as a Phase-1 deliverable, on **napari**,
exposed as an `openbragg.gui` submodule (`view(case)` + an `openbragg view` CLI).
This **reverses the prior "Heavy GUI" Phase-1 non-goal**, which scoped visualization
to matplotlib/notebook only. The GUI is a pure consumer of the modality-agnostic
`Case` model — it never reads dataset formats directly — so the same viewer serves
photon (openkbp) and, later, proton DICOM cases unchanged.

## Considered options

- **napari (chosen)** — Python library-first, BSD-3, native Image/Labels layers that
  match the `Case` model (CT + per-ROI masks + later a dose overlay), 2D-slice and
  3D-rotate built in. We own the app loop and embed it in the package.
- **pyvista / vedo (VTK)** — strong general 3D, permissive, but slice navigation,
  per-ROI label overlays, and window/level are all hand-rolled.
- **3D Slicer scripting** — powerful but a monolithic application scripted from within,
  not a library we can embed; off-strategy and heavyweight.
- **Qt + VTK from scratch** — maximum control, maximum effort; only if napari limits us.

## Consequences

- **Qt binding is pinned to PySide6 (LGPL), never PyQt5 (GPL).** The obvious
  `napari[all]` extra silently pulls PyQt5 and would contaminate the project's
  Apache-2.0 licensing — it must not be used. The dependency lives behind an optional
  `openbragg[gui] = ["napari", "pyside6"]` extra, so the core install and headless CI
  recompute stay Qt-free.
- **Interaction model:** slice-plane-in-3D ("plane depiction") — one rotatable scene
  where a moving slice plane gives depth. All layers share one plane, kept in lockstep
  by a plane-position sync listener.
- **Testability:** logic lives in a pure, Qt-free `build_layers(case) -> [LayerSpec]`
  adapter (unit-tested on external behavior); `view()` is a thin napari shell with one
  optional headless smoke test. Keeps the "assert external behavior" + pyright-strict
  standards satisfiable for a GUI.
- If packaging ever demands it, the `gui` submodule can be split into a separate
  `openbragg-gui` distribution; deferred until then (YAGNI).
