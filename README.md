# OpenBragg

**An open-source, proton-focused treatment planning system (TPS) for radiotherapy — clinical-grade dose physics, engine-agnostic architecture, built in the open.**

OpenBragg is a Python-first TPS aimed at proton therapy. It is developed as a learning-driven, research-grade project toward eventual collaboration with the [Danish Center for Particle Therapy (DCPT)](https://www.en.auh.dk/departments/the-danish-centre-for-particle-therapy/) in Skejby, Aarhus.

> **Status:** early scoping. See [`PRD.md`](./PRD.md) for the full product requirements and design decisions.

## What it is

The near-term goal (Phase 1) is a correct, validatable, **end-to-end dose recalculation / verification pipeline**:

> DICOM-RT proton case → patient/plan data model → dose via a wrapped engine (MCsquare) → DVH → dose-on-CT & DVH display → RTDOSE export — with full provenance logging and a gamma-analysis regression harness.

This is immediately useful as an **independent dose-verification tool**. Inverse-planning **optimization** (spot-weight/IMPT, then robust optimization) is deferred to Phase 2 but architecturally protected today.

## Design principles

- **Python-first**, with native (C++/CUDA) code only behind a narrow dose-engine seam, later.
- **Engine-agnostic:** external engines (MCsquare, OpenTOPAS, …) are wrapped across a **process boundary**, never linked — keeping the seam clean and the project insulated from their licenses.
- **Dij-first:** the dose engine's fundamental output is a sparse voxels×spots **dose-influence matrix**; total dose is `Dij · w`. Plan recomputation and future optimization share the same representation.
- **Provenance-first:** every dose calculation records its inputs, engine version, parameters, and software version, so results are reproducible and auditable.
- **Clinical-*grade*, not clinically cleared:** OpenBragg targets clinical accuracy and traceability; it does not itself pursue FDA/CE clearance. That path remains open to downstream adopters.

## Relationship to the existing ecosystem

OpenBragg overlaps [OpenTPS](https://opentps.org/) **by design**. Its reason to exist is *architectural* (engine-agnostic seam, Dij-first everywhere, provenance-first) and *educational*, not raw feature count. OpenTPS, [MCsquare](http://www.openmcsquare.org/), and [OpenTOPAS](https://opentopas.readthedocs.io/) are used as **reference and validation oracles** — never as sources of copied code.

## Validation

Open-data / open-software validation, layered:

1. **Analytic** — proton depth-dose in water vs the Bortfeld Bragg-peak model; stopping powers vs NIST PSTAR.
2. **Reference-engine** — gamma analysis (3%/3 mm, 2%/2 mm) vs MCsquare and OpenTOPAS.
3. **Full-pipeline** — cross-check vs OpenTPS on identical cases.
4. **(Future)** — DCPT measured phantom data and delivered-plan recomputation.

## License

[Apache License 2.0](./LICENSE).

## Author

Emil Brinch Holm — cosmology PhD transitioning into medical physics.
