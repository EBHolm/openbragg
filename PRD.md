# OpenBragg — Product Requirements Document

> **Status:** Draft / scoping complete. Repo not yet created.
> **Author:** Emil Brinch Holm
> **Context:** Learning-driven open-source treatment planning system (TPS), proton-therapy-focused, developed toward eventual collaboration with the Danish Center for Particle Therapy (DCPT), Skejby, Aarhus.
> **License (intended):** Apache-2.0
> **Package/repo name (reserved, verified free on GitHub + PyPI):** `openbragg`

---

## Problem Statement

Radiotherapy treatment planning systems that meet clinical accuracy standards (e.g. RayStation) are closed, commercial, and inaccessible for open research, teaching, and independent verification. The existing open ecosystem for **proton** therapy (matRad, OpenTPS, MCsquare, OpenTOPAS, FRED) is scientifically strong but fragmented: each tool couples its architecture tightly to a particular engine, language, or workflow, and none is designed from the ground up around a clean, engine-agnostic, provenance-first architecture.

Separately, the author is a cosmology PhD transitioning into medical physics and needs to build genuine, deep understanding of how a proton TPS works end-to-end — the clinical data flow, the dose physics, and the inverse-planning optimization that will be the core of his research — by building one, not merely using one.

There is no open proton TPS that simultaneously: (a) provides an end-to-end, clinically-accurate dose pathway; (b) is architected so that individual scientific modules (especially the dose engine and the optimizer) can be swapped and independently validated; and (c) treats reproducibility/traceability as a first-class concern so that downstream adopters could, in principle, pursue their own regulatory clearance.

## Solution

**OpenBragg** — a Python-first, open-source, proton-focused treatment planning system built in phases.

- **Phase 1 (this PRD's primary target):** a correct, validatable, end-to-end **dose recalculation / verification** pipeline. It ingests a DICOM-RT proton case, builds an in-memory patient/plan data model, computes dose by orchestrating a proven external engine (MCsquare) behind a narrow interface, computes DVHs, displays dose-on-CT and DVH, and exports RTDOSE — with full provenance logging and a gamma-analysis regression harness. This is immediately useful as an **independent dose-verification tool**, without requiring the two hardest modules (in-house dose engine, optimizer).
- **Phase 2 and beyond (architecturally protected now, built later):** inverse-planning **optimization** (spot-weight / IMPT, then robust optimization), and selective **reimplementation** of individual modules — starting with the dose engine — as swappable components validated against the wrapped reference engine they replace.

OpenBragg's differentiators versus the existing ecosystem are architectural rather than feature-count: an **engine-agnostic dose seam**, a **Dij-first (dose-influence-matrix) data model everywhere**, **process-boundary engine wrapping**, and **provenance/traceability as a built-in concern**.

The scope target is **(C): a clinical-*grade* engine**. OpenBragg aims for clinical accuracy on the physics and traceability in the architecture, but the author will not seek FDA 510(k) / CE-MDR clearance, ISO 13485 QMS, or IEC 62304 compliance himself. Those remain available to downstream adopters who fork it.

## User Stories

### Learning & research (author / medical physicists)
1. As a physicist learning TPS internals, I want an end-to-end pipeline I can read and step through, so that I understand what each TPS module actually does and where the hard parts hide.
2. As a researcher, I want to swap the dose engine behind a stable interface, so that I can compare a wrapped reference engine against my own reimplementation without changing the rest of the system.
3. As a researcher, I want the dose engine to emit a beamlet/spot-resolved influence matrix (Dij), so that I can build inverse-planning optimization on top of it later without re-architecting.
4. As a researcher, I want to compute total dose as `Dij · w`, so that plan recomputation and optimization share exactly the same dose representation.
5. As a physicist, I want to validate proton depth-dose in water against the Bortfeld analytical Bragg-peak model and NIST PSTAR stopping powers, so that I can trust the physics at the most basic level.
6. As a physicist, I want to cross-check my full pipeline against OpenTPS and reference engines (MCsquare, OpenTOPAS) on identical cases, so that I can quantify where OpenBragg agrees and disagrees.

### Clinical data handling (planner / verifier)
7. As a verifier, I want to load a DICOM-RT proton case (CT, RTSTRUCT, RTPLAN/RTIONPLAN, RTDOSE), so that I can work with real clinical data.
8. As a verifier, I want an in-memory patient/plan data model (image, structures, beams, plan, dose) that every module operates on, so that data flows consistently through the pipeline.
9. As a verifier, I want HU-to-relative-stopping-power conversion for protons, so that range calculations are physically correct.
10. As a verifier, I want to resample and align images/dose grids correctly, so that comparisons are geometrically valid.
11. As a verifier, I want to recompute the dose of an already-delivered proton plan using its delivered spot weights, so that I can independently verify the delivered dose.
12. As a verifier, I want to export the recomputed dose as RTDOSE, so that it can be compared in other tools or record-and-verify systems.

### Evaluation & visualization
13. As a user, I want DVHs computed from dose and structures, so that I can evaluate a plan clinically.
14. As a user, I want dose statistics and clinical goal checks, so that I can judge plan quality quantitatively.
15. As a user, I want to display dose-on-CT with isodose lines and a DVH plot, so that I can inspect results visually.
16. As a user, I want gamma analysis (e.g. 3%/3mm, 2%/2mm) between two dose distributions, so that I can quantify agreement with a reference in the field-standard way.
17. As a user, I want to compare two plans/doses side by side, so that I can assess differences.

### Reproducibility & QA (target-(C) traceability)
18. As an adopter, I want every dose calculation to record its inputs, engine version, parameters, and software version, so that any result is reproducible and auditable.
19. As an adopter, I want deterministic runs where the engine allows, so that regressions are detectable.
20. As a maintainer, I want a gamma-analysis regression harness wired into CI, so that changes that degrade accuracy are caught automatically.
21. As a maintainer, I want benchmark phantom and analytic reference cases in the test suite, so that correctness is continuously verified against known answers.

### Optimization (phase 2 — enabled now, built later)
22. As a researcher, I want to optimize spot weights against DVH-based objectives using the Dij matrix, so that I can generate IMPT plans.
23. As a researcher, I want robust optimization against range/setup-uncertainty scenarios, so that plans are proton-appropriate.
24. As a researcher, I want to plug in different optimizers and objective functions, so that I can pursue my PhD research on planning optimization.

### Ecosystem / open-source citizenship
25. As a contributor, I want the README to state honestly that OpenBragg overlaps OpenTPS by design and that its differentiators are architectural, so that I understand why the project exists and how it relates to the ecosystem.
26. As a contributor, I want external engines wrapped across a process boundary (subprocess/CLI), so that the project stays insulated from their licenses and the engine seam stays clean.
27. As an adopter, I want an Apache-2.0 license with a patent grant, so that I (including a company or hospital) can build on it, potentially toward my own certification.

## Implementation Decisions

### Scope & positioning
- **Target level (C):** clinical-*grade* engine — clinical accuracy + traceability, but no self-pursued FDA/CE clearance, QMS, or IEC 62304 compliance. Architected so downstream adopters *could* pursue clearance.
- **Modality:** protons are the true north; architecture kept modality-agnostic so photons/electrons/other particles can slot in later. Note: the *name* is proton-flavored (Bragg peak) but the *architecture* is neutral.
- **Relationship to prior art:** clean-room new build (option B). OpenTPS, MCsquare, and OpenTOPAS are used as **reference and validation oracles only** — no code copying. The **GPLv3 OpenTPS GUI is off-limits** even for reference, to keep OpenBragg permissive.

### Architecture & stack
- **Python-first core.** Data model, DICOM-RT I/O (`pydicom`), image handling (`SimpleITK`/`numpy`), workflow orchestration, DVH/evaluation, optimization glue (`scipy`/`numpy`, later `cvxpy`/`jax`), and visualization (matplotlib/notebook in Phase 1).
- **Narrow, language-agnostic dose-engine seam.** External engines are invoked across a **process boundary (subprocess/CLI)**, never linked. This dodges license coupling and enforces the seam. Any future in-house C++/CUDA engine sits behind the *same* interface (via a process boundary or a thin `pybind11` layer).
- **Dij-first data model.** The dose engine's fundamental output is a **sparse voxels×spots dose-influence matrix (Dij)**. "Total dose for a plan" is `Dij · w`. Phase 1 uses this only to reproduce a delivered plan's dose (`w` = delivered weights); Phase-2 optimization consumes the identical object. A **sparse influence-matrix representation** and its storage location (in-memory vs on-disk for large cases) are designed in Phase 1, not deferred.

### Modules (the TPS decomposition)
Data & I/O: (1) DICOM-RT I/O; (2) patient/plan data model. Pre-planning: (3) image handling; (4) contouring/segmentation *(deferred — external/Slicer)*; (5) CT-to-material / HU→RSP conversion. Beam & machine: (6) machine/beam model *(Phase 1 borrows an existing/generic model — no commissioning)*; (7) beam geometry. Physics core: (8) dose calculation engine *(Phase 1 = wrapped MCsquare; Phase 2 = swappable in-house)*; (9) dose accumulation/grid. Optimization: (10) plan optimization *(Phase 2)*; (11) robust optimization *(Phase 2)*. Evaluation & output: (12) plan evaluation / DVH; (13) visualization; (14) reporting / RTDOSE export. Cross-cutting: (15) reproducibility/provenance; (16) validation/QA harness.

### The primary seam
- The **dose-engine interface is the single most important seam** and the one to get right first. It takes (image + material map + beam/geometry + plan spots) and returns a **Dij influence matrix** plus geometry/units metadata. All engines (wrapped or in-house) conform to it. Testing and swapping happen at this seam. This is deliberately the *highest and fewest-seam* design: the rest of the pipeline never talks to an engine directly, only to `Dij`.

### Provenance
- Every dose calculation writes a **run manifest** capturing: input identifiers/hashes, engine identity + version, all engine parameters, OpenBragg version, and grid/units metadata — sufficient to reproduce the result.

### License & naming
- **Apache-2.0** (permissive + patent grant; adoption-friendly for target C).
- **OpenBragg** / `openbragg` — chosen as a deliberate, honest sibling to OpenTPS and OpenTOPAS.
- **Repo topology (recommended):** single monorepo package for now, with a `viz` submodule that is matplotlib/notebook-only in Phase 1. Split into `openbragg-core` / `openbragg-gui` only if a real GUI later justifies it — and if split, keep the GUI Apache-2.0, not GPL.
- **Repo home (recommended, undecided):** a new GitHub org `openbragg` rather than a personal repo, to support contributors and DCPT collaboration later.

## Testing Decisions

- **Good tests exercise external behavior, not implementation details.** For a TPS this means: given known inputs, assert on dose distributions, DVH metrics, gamma pass rates, and exported DICOM — not on internal data structures.
- **Layered validation (open data/software only, for now):**
  1. **Analytic:** proton depth-dose in water vs the Bortfeld analytical Bragg-peak model; stopping powers vs NIST PSTAR.
  2. **Reference-engine agreement:** OpenBragg dose vs MCsquare and OpenTOPAS on public phantom/patient cases, quantified by **gamma analysis** (3%/3mm and 2%/2mm pass rates) and DVH-metric deltas.
  3. **Full-pipeline cross-check:** end-to-end OpenBragg result vs OpenTPS on identical cases.
  4. **(Future, higher authority):** DCPT measured phantom data and recomputation of delivered RayStation plans — deferred until DCPT data/RayStation access is available.
- **Modules under test:** DICOM-RT I/O (round-trip), HU→RSP conversion, the dose-engine seam (Dij correctness vs reference), DVH/gamma computation, and provenance manifests.
- **Regression harness:** the gamma-analysis + DVH-comparison harness is a **first-class module built in Phase 1** and wired into CI, with benchmark phantom and analytic cases as fixtures.
- **Prior art:** matRad and OpenTPS ship example proton cases with a generic machine model; these serve as initial fixtures and cross-check references.

## Out of Scope

- **Regulatory clearance / QMS / IEC 62304** — explicitly not pursued by the author (target C).
- **Phase 1 excludes:** plan optimization (modules 10/11), any in-house dose engine (Phase 2), auto-segmentation/contouring, and machine commissioning (Phase 1 borrows an existing/generic beam model).
- **DCPT/RayStation data and validation** — deferred; not available in the near term. Near-term validation is open-data/open-software only.
- **Photon/electron and brachytherapy modalities** — architecture must not preclude them, but they are not built now.
- **Heavy GUI** — Phase 1 visualization is matplotlib/notebook only.
- **Repo creation** — intentionally not done yet; this PRD precedes it.

## Further Notes

- **Parked for a dedicated later session (author's request):** how OpenBragg can meaningfully *differentiate from and potentially outperform* OpenTPS — to be grilled before committing to differentiating features.
- **Ecosystem honesty:** the README should openly acknowledge overlap with OpenTPS and state that the justification for a new build is learning + architectural control (engine-agnostic seam, Dij-first, provenance-first), not raw feature utility.
- **Author background:** cosmology PhD → medical physics. Numpy/scipy/HPC/sparse-linear-algebra fluency is an asset; the Dij-first sparse-matrix plumbing and large-array memory management play directly to that strength.
- **Sequencing principle:** get a correct end-to-end pipeline running on wrapped engines *first* (to learn what each module must do), *then* reimplement modules behind their now-understood interfaces. Building the dose engine first, in a vacuum, is the failure mode to avoid.
