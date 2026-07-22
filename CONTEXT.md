# OpenBragg

A Python-first, proton-focused treatment planning system. This glossary is the
canonical naming source for the whole package; consult it before naming a symbol
and reuse its terms over synonyms.

## Language

### Visualization surfaces

**Viz**:
The *static, non-interactive* visualization surface — figures rendered once for
notebooks, reports, and dose review (DVH plots, dose-on-CT images).
_Avoid_: GUI, viewer (for static output).

**GUI**:
The *live, interactive* visualization surface — a windowed session for exploring
a Case in 3D (slice navigation, rotation, layered CT / structure / dose overlays).
Distinct from Viz: interactive session, not a rendered figure.
_Avoid_: viz, app.

**Slice plane**:
In the GUI, a single planar cross-section of a volume shown inside a rotatable 3D
scene. Its *normal* is the depth axis; moving it along the normal changes depth.
All layers (CT, structures) share one slice plane, kept in lockstep.
_Avoid_: slice (ambiguous with a fixed 2D axial view), MPR.
