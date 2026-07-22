# openkbp-opt sample (curated subset)

A small, committable subset of the **openkbp-opt** dataset for OpenBragg tests
and demo notebooks. The full ~23 GB dataset is git-ignored; this holds only a
few patients so the pipeline can run on real data without a large download.

Regenerate with:

    uv run python scripts/fetch_openkbp.py --zip <base.zip> --zip <optional.zip>
    uv run python scripts/make_openkbp_sample.py

## Patients

- `pt_329`
- `pt_318`
- `pt_278`

## Source & attribution

- Dataset: **OpenKBP-Opt** (Babier et al., *Phys. Med. Biol.* 67(18):185012,
  2022), https://github.com/ababier/open-kbp-opt -- released under **CC BY 4.0**.
- Underlying anatomy: the OpenKBP Grand Challenge (Babier et al., *Medical
  Physics* 48(9), 2021), https://github.com/ababier/open-kbp.
- Upstream repository code (data format) is MIT-licensed.

These are anonymized, downsampled (128x128x128) head-and-neck IMRT (photon)
research cases, not clinical PHI. Attribution is required under CC BY 4.0.
