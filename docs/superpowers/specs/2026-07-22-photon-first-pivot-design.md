# Photon-first pivot — OpenBragg Phase 1 design

Date: 2026-07-22

Author: Emil Brinch Holm

Status: Approved (brainstorming complete) — supersedes the *modality* of the Phase-1
milestone in `PRD.md`, not its architecture. A dated **photon-first addendum** will be
added to `PRD.md`; the proton spec itself is left intact.

Informed by: [`docs/research/openkbp-radiant-for-openbragg.md`](../../research/openkbp-radiant-for-openbragg.md)
(primary-source research on OpenKBP / openkbp-opt).

## Summary

Bring the Phase-1 **dose-recalculation / verification** pipeline up **on photon data first**,
anchored on the **openkbp-opt** open dataset, keeping **proton as the project's true-north**.
This cashes in the PRD's existing claim that the architecture is modality-agnostic
("photons/electrons can slot in later"), earlier than originally sequenced, because the
open-data story for photons is decisively better than for protons.

The Phase-1 photon milestone is **recompute-only**: ingest an openkbp-opt patient → load its
precomputed photon dose-influence matrix `Dij` behind the dose-engine seam → compute total
dose `Dij·w` from the shipped optimized beamlet weights → compute DVH + gamma against the
shipped `plan-dose` → visualize dose-on-CT + DVH → export RTDOSE → write a provenance manifest.
No optimizer is built (optimization stays Phase 2, per the PRD).

## Motivation

- **The proton open-data bottleneck is real.** OpenBragg's pipeline needs a case with a plan
  (spot/beamlet weights `w`) *and* a reference dose to have anything to recompute and compare
  against. For protons, the research found **no verified fully-open dataset** shipping an RTION
  plan + reference RTDOSE; you would have to synthesize one via matRad/OpenTPS.
- **openkbp-opt supplies exactly the object OpenBragg is built around.** For 100 head-and-neck
  IMRT patients it ships a **precomputed sparse `Dij` (voxels × beamlets)**, a reference
  (clinical ground-truth) dose, 21 predicted doses, CT, structure masks, a feasible-dose mask,
  and voxel dimensions. Its dose model is `d_v = Σ_b D_{v,b} · w_b` — in code
  `dose = patient.dij * w_opt` — the **identical** object and algebra as OpenBragg's Dij-first
  design.
- **This exercises the "after the seam" half of the pipeline on real data now**, and defers the
  proton-specific hard parts (dose physics, engine seam) to when a computing engine goes behind
  the seam.

## Decisions (locked in brainstorming)

1. **Scope of pivot: photon-first, proton still true-north.** A sequencing change, not a
   reorientation. The OpenBragg name, the DCPT collaboration framing, and the proton PRD all
   stand. Recorded as a PRD *addendum*, not a rewrite.
2. **Anchor dataset: openkbp-opt.** Consume its precomputed `Dij` + reference/plan doses.
   Ingest reads its CSV/`.npz` array format (**not** DICOM). The engine behind the seam is a
   **loader** that sources the shipped `Dij`.
3. **Milestone scope: recompute-only.** Use the shipped optimized weights `w` and verify
   `Dij·w` reproduces the shipped `plan-dose` via gamma + DVH. No optimizer built now.
4. **Issue tracking: new photon issues + a `phase:` label split.** Do **not** edit the proton
   issues (#4–#13) in place; open new photon-phase issues and split the tracker with
   `phase:photon` / `phase:proton` labels so the proton work is preserved and the frontier query
   stays honest.
5. **RTDOSE export: kept in the photon milestone**, with an explicit synthesized-frame caveat
   (openkbp-opt has no DICOM patient coordinate frame; we synthesize a minimal valid one).

## Scope

**In scope (photon Phase-1 milestone):**

- openkbp-opt ingest into a modality-agnostic in-memory data model.
- Dose-engine **seam** (interface) + an `OpenKBPOptEngine` loader implementing it.
- Total-dose accumulation `dose = Dij · w` on the dose grid, units Gy.
- DVH from dose + structure masks.
- Gamma analysis (3%/3mm, 2%/2mm) of `Dij·w` vs the shipped `plan-dose`.
- Dose statistics + clinical-goal checks against the known H&N prescription.
- Visualization: dose-on-CT with isodose lines + DVH plot.
- RTDOSE export (with synthesized frame-of-reference).
- Provenance run manifest.
- Gamma + DVH regression harness wired into CI, on a tiny committed fixture.

**Out of scope (deferred to the proton phase or Phase 2):**

- HU→RSP material mapping (a proton concept; a precomputed `Dij` needs no HU→material step).
- Wrapping a real physics engine (MCsquare) — i.e. the *produce-a-`Dij`* seam path.
- Analytic Bragg-peak / PSTAR validation (no Bragg peak in photons).
- DICOM-RT ingest (openkbp-opt is arrays, not DICOM).
- Any inverse-planning optimizer (Phase 2).

## Architecture

Same module spine as the proton PRD, re-pointed at openkbp-opt. Indicative package layout
(to be firmed up in the implementation plan), under the existing `src/openbragg/`:

- **Data model** (`model/`) — modality-agnostic: `image` (CT on the 128³ grid + geometry from
  `voxels.csv`), `structures` (mask arrays keyed by ROI name), `plan` (beamlets + weights `w`),
  `dose` (reference / plan / predicted). Designed so proton spots and a DICOM frame slot in
  later without rework.
- **Ingest / IO** (`io/`) — an openkbp-opt loader reading `reference-plans/pt_*`
  (CT, masks, feasible-dose mask, voxel dims, `Dij`) and, from the optional bundle,
  `paper-plans/<model>/plan-fluence/<pred-set>/<pt>.csv` (the beamlet weight vector `w`) plus
  the matching `plan-dose/<pred-set>/<pt>.csv` (the recompute target). Normalizes the `Dij` into
  a `scipy.sparse` matrix and aligns dimensions (`Dij` rows = flattened 128³ = 2,097,152 voxels;
  cols = per-patient beamlet count = `len(w)`; sparse `plan-dose` expanded to the full grid for
  comparison).
- **Dose-engine seam** (`engine/`) — the interface
  `(image, material_map, beam/geometry, spots/beamlets) → (sparse Dij, geometry/units metadata)`,
  defined exactly as the PRD specifies. `OpenKBPOptEngine` implements it by **sourcing** the
  `Dij` from disk rather than computing it. The seam *contract* is real and tested; a future
  computing engine (photon pencil-beam, or proton MCsquare) drops in behind the identical
  interface. See "Validation semantics" for what this does and does not prove.
- **Dose accumulation** (`dose/`) — `dose = Dij · w` (sparse matvec), reshaped flat-128³ → 3D,
  units Gy, on a defined dose-calculation grid.
- **Evaluation** (`eval/`) — DVH from dose + masks; gamma (3%/3mm, 2%/2mm) using per-patient
  voxel spacing from `voxels.csv`; dose statistics + clinical-goal checks against the H&N
  prescription (PTV70/63/56 target coverage; brainstem / spinal cord / parotid / larynx /
  esophagus / mandible OAR limits).
- **Export** (`export/`) — RTDOSE writer building a minimal valid DICOM RTDOSE from the computed
  dose grid + voxel dims, synthesizing a consistent frame-of-reference (documented caveat).
- **Provenance** (`provenance/`) — run manifest: input identifiers/hashes (patient id, `Dij`,
  `w`), engine identity + version ("openkbp-opt loader"), OpenBragg version, grid/units metadata.
- **Visualization** (`viz/`) — matplotlib/notebook: dose-on-CT with isodose lines, DVH plot.

Data flow: `loader → data model → engine.seam(→ Dij) → Dij·w → dose grid → {DVH, gamma, stats}
→ {RTDOSE, viz} + provenance manifest`.

## Data & fixtures

- The full dataset is ~23 GB (base **10.19 GB** = `reference-plans` + `paper-predictions`;
  optional **13.08 GB** = `paper-plans` + `results-data` + `results`). **The beamlet weight
  vector `w` lives only in the optional `paper-plans` bundle**, in `plan-fluence/` — a per-patient
  CSV whose `data` column is the beamlet-intensity vector (`w_opt` in the optimizer). It is **not**
  `plan-weights/`, which holds per-*objective* dual weights (a DataFrame indexed by objective
  name) and is irrelevant to recompute. So the recompute loop requires the optional bundle too.
  Verified in `provided_code/optimizer.py::save_fluence_and_dose`: `w_opt` is written to the
  fluence path and `dose = patient.dij * w_opt` is written to the dose path — i.e.
  `plan-dose = Dij · (plan-fluence)` **by construction**.
- Nothing large is committed. `.gitignore` already blocks `*.npz`, `data/`, `cases/`, and large
  arrays. Strategy:
  - A **download/fetch script** pulling both bundles into an ignored `data/` directory.
  - A **tiny committed fixture** — one patient cropped/downsampled to a small grid, or a
    synthetic mini-`Dij` + `w` + dose with a known product — so CI runs the full
    recompute→gamma loop with no large download.
- **Licensing / attribution:** openkbp-opt code is MIT; the underlying OpenKBP dataset is
  CC BY 4.0. Both are compatible with OpenBragg's Apache-2.0 as test fixtures. Attribute the
  dataset; never commit the data itself.

## Validation semantics (the honest limit)

Stated explicitly because it governs what a green result means:

- The Phase-1 gamma pass-rate here proves the **Dij-consumer machinery is correct** — sparse
  matvec, grid reshaping, DVH, gamma, RTDOSE export, provenance — because
  `Dij · plan-fluence` reproduces `plan-dose` to floating-point precision (openkbp-opt itself
  computes and saves `dose = dij * w_opt`, so this is a cross-implementation check of the
  identical linear algebra — expect a near-exact match, not merely a high gamma pass rate).
  Note openkbp-opt's own metrics are dose-score (MAE over the feasible-dose mask) + DVH-score,
  **not** gamma; gamma (3%/3mm, 2%/2mm) is OpenBragg's own field-standard addition.
- It does **not** validate dose **physics** or the engine **seam**, because the `Dij` was
  computed externally (CERR IMRTP) and OpenBragg only re-multiplies it. A near-perfect gamma is
  therefore *expected* and must never be read as "the physics is verified."
- Physics/seam validation returns in the proton phase, when a *computing* engine (MCsquare +
  Bortfeld/PSTAR analytics) goes behind the seam and *produces* a `Dij`.

Caveats carried from the data (see research note): the openkbp-opt CT is an offset/clipped
12-bit range (0–4095) spatially downsampled to a coarse 128³ (~3–4 mm) grid — acceptable here
because we consume a precomputed `Dij` rather than recomputing dose from HU.

## Issue-tracker & PRD impact

**PRD:** add a dated photon-first addendum section referencing this design; leave the proton
spec intact.

**Tracker:** introduce `phase:photon` / `phase:proton` labels. Open new photon-phase issues;
do not overwrite the proton issues. Mapping of the existing proton issues to photon-phase work:

| Proton issue | Photon-phase fate |
|---|---|
| #4 DICOM-RT ingest + data model | New photon issue → openkbp-opt array ingest + modality-agnostic data model |
| #5 Dose-engine seam + stub engine | New photon issue → seam + openkbp-opt **loader** engine (returns real precomputed `Dij`) |
| #6 RTDOSE export + provenance | New photon issue → keep, with synthesized-frame caveat |
| #10 RTSTRUCT ingest + DVH | New photon issue → structure-mask ingest + DVH |
| #11 Dose statistics + clinical goals | New photon issue → keep (PTV70/63/56 + OAR goals) |
| #12 Visualization dose-on-CT + DVH | New photon issue → keep |
| #13 Gamma + DVH regression harness (CI) | New photon issue → keep; the recompute self-consistency fixture |
| #7 HU→RSP material map | Stays proton-only (`phase:proton`); deferred |
| #8 Wrap MCsquare (real physics) | Stays proton-only; deferred (the produce-a-`Dij` seam path) |
| #9 Analytic Bragg-peak validation | Stays proton-only; deferred (no Bragg peak in photons) |

## On-disk formats (RESOLVED — verified against `provided_code/`)

Reconciled the research note against the repo source (`general_functions.py::load_file`,
`resources.py`, `optimizer.py`). The README's `*.csv` tree is illustrative; `load_file`
dispatches on extension. Per-patient formats:

| Artifact | File | On-disk form | Reconstruct to |
|---|---|---|---|
| `Dij` | `reference-plans/pt_*/dij.npz` | `scipy.sparse` (`load_npz` → `coo`, used as `csr`) | sparse (2,097,152 × n_beamlets) |
| CT | `reference-plans/pt_*/ct.csv` | CSV `{index=raveled voxel idx, "data"=HU}` (nonzero only) | dense 128³ via `np.put` |
| Reference dose | `reference-plans/pt_*/dose.csv` | CSV `{index=voxel idx, "data"=Gy}` (sparse) | dense 128³ |
| Structure mask | `reference-plans/pt_*/<ROI>.csv` | CSV of raveled voxel indices where mask==1 (index-only, null "data") | bool 128³ |
| Feasible-dose mask | `reference-plans/pt_*/possible_dose_mask.csv` | index-only CSV (as above) | bool 128³ |
| Voxel dims (mm) | `reference-plans/pt_*/voxel_dimensions.csv` | `np.loadtxt` → 3-vector | `(dx,dy,dz)` |
| Beamlet coords | `reference-plans/pt_*/beamlet_indices.csv` | CSV → df of `(row,col,angle)` per beamlet | `(n_beamlets, 3)` |
| Weight vector `w` | `paper-plans/<model>/plan-fluence/<set>/<pt>.csv` | CSV `{index=0..n_beamlets-1, "data"=intensity}` | dense `w` (n_beamlets,) |
| Recompute target | `paper-plans/<model>/plan-dose/<set>/<pt>.csv` | CSV `{index=voxel idx, "data"=Gy}` (sparse) | dense 128³ |

All raveled indices are **C-order over `(128,128,128)`** (numpy default) — the same order `Dij`
rows use — so `(Dij @ w).reshape(128,128,128)` is directly comparable to the reconstructed
`plan-dose`. Units are **Gy** throughout.

### Still open (verify at implementation time)

- **Dimension/units alignment** on a real patient — confirm `Dij.shape[1] == len(w)` and that
  `(Dij @ w)` matches the reconstructed `plan-dose` within fp tolerance before wiring gamma.
- **RTDOSE frame synthesis** — choose a minimal, self-consistent origin/orientation/spacing so
  the exported RTDOSE is valid and re-loadable, and document that it is synthetic.

## Reference facts (from primary sources; see research note for citations)

- openkbp-opt: 100 head-and-neck IMRT patients (the OpenKBP *test* set). 6 MV step-and-shoot
  IMRT, 9 equidistant coplanar beams (0°, 40°, …, 320°), fluence grid 64×64, beamlet region
  ≤32×32, SPG ≤ 65.
- Grid: 128×128×128 (2,097,152 voxels). `Dij` from CERR IMRTP (MATLAB), `scipy.sparse`.
- Dose model: `d_v = Σ_b D_{v,b} w_b`; repo code `dose = patient.dij * w_opt`.
- Structures: OARs (brainstem, spinal cord, R/L parotid, larynx, esophagus, mandible);
  targets PTV70 / PTV63 / PTV56 (70 Gy in 35 fx).
- Base bundle 10.19 GB (`reference-plans` + `paper-predictions`) has **no** `w`; the optional
  13.08 GB bundle (`paper-plans`) holds `plan-fluence` (the beamlet weight vector `w`),
  `plan-dose`, `plan-weights` (per-objective dual weights — *not* `w`), and `plan-gap`.
- openkbp-opt scores plans with dose-score (MAE over the feasible-dose mask) + DVH-score, not
  gamma. DVH metrics used: OARs `D_0.1_cc`, `mean`; targets `D_99`, `D_95`, `D_1`. Clinical
  criteria (`plan_criteria_dict`): Brainstem/SpinalCord/Mandible `D_0.1_cc` ≤ 50/45/73.5 Gy;
  RightParotid/LeftParotid/Esophagus/Larynx `mean` ≤ 26/26/45/45 Gy; PTV56/63/70 `D_99` ≥
  53.2/59.85/66.5 Gy.
- Licenses: repo MIT; OpenKBP dataset CC BY 4.0.
