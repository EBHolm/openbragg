#!/usr/bin/env python3
"""Curate a small, committable openkbp-opt sample from a full local dataset.

Copies a handful of patients out of a downloaded ``open-kbp-opt-data`` tree into
``sample_data/openkbp_opt`` so tests and notebooks have real data without
committing the full ~23 GB. Each sampled patient keeps its whole reference-plans
directory (CT, masks, dij, reference dose, voxel dims) plus one model's
plan-fluence + plan-dose (the beamlet weights ``w`` and the dose it produces) --
everything ``openbragg.io.openkbp_opt.load_case`` consumes.

    uv run python scripts/make_openkbp_sample.py                     # first 3 patients
    uv run python scripts/make_openkbp_sample.py --patients pt_1 pt_42 pt_99
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from openbragg.io.openkbp_opt import (
    find_patient_dirs,
    resolve_plan_paths,
    verify_dataset,
)

GITHUB_FILE_LIMIT_BYTES = 100 * 1024 * 1024  # GitHub rejects pushes with larger files

_ATTRIBUTION = """# openkbp-opt sample (curated subset)

A small, committable subset of the **openkbp-opt** dataset for OpenBragg tests
and demo notebooks. The full ~23 GB dataset is git-ignored; this holds only a
few patients so the pipeline can run on real data without a large download.

Regenerate with:

    uv run python scripts/fetch_openkbp.py --zip <base.zip> --zip <optional.zip>
    uv run python scripts/make_openkbp_sample.py

## Patients

{patients}

## Source & attribution

- Dataset: **OpenKBP-Opt** (Babier et al., *Phys. Med. Biol.* 67(18):185012,
  2022), https://github.com/ababier/open-kbp-opt -- released under **CC BY 4.0**.
- Underlying anatomy: the OpenKBP Grand Challenge (Babier et al., *Medical
  Physics* 48(9), 2021), https://github.com/ababier/open-kbp.
- Upstream repository code (data format) is MIT-licensed.

These are anonymized, downsampled (128x128x128) head-and-neck IMRT (photon)
research cases, not clinical PHI. Attribution is required under CC BY 4.0.
"""


def _human(nbytes: int) -> str:
    mb = nbytes / (1024 * 1024)
    return f"{mb:,.1f} MB" if mb < 1024 else f"{mb / 1024:,.2f} GB"


def _copy_into_sample(path: Path, source_root: Path, sample_root: Path) -> Path:
    """Copy *path* into *sample_root*, preserving its path relative to *source_root*."""
    target = sample_root / path.relative_to(source_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return target


def curate(
    source_root: Path, sample_root: Path, patient_ids: list[str], model: str | None
) -> list[Path]:
    """Copy the given patients into the sample tree; return the copied file paths."""
    copied: list[Path] = []
    for pid in patient_ids:
        patient_dir = source_root / "reference-plans" / pid
        if not patient_dir.is_dir():
            raise SystemExit(f"patient {pid!r} not found under {source_root}")
        for item in sorted(patient_dir.iterdir()):
            if item.is_file():
                copied.append(_copy_into_sample(item, source_root, sample_root))
        fluence, dose = resolve_plan_paths(source_root, pid, model=model)
        copied.append(_copy_into_sample(fluence, source_root, sample_root))
        if dose.is_file():
            copied.append(_copy_into_sample(dose, source_root, sample_root))
        else:
            print(
                f"  note: no plan-dose beside {fluence.name}; skipping reference dose"
            )
    return copied


def _write_attribution(sample_root: Path, patient_ids: list[str]) -> None:
    listing = "\n".join(f"- `{pid}`" for pid in patient_ids)
    (sample_root / "README.md").write_text(_ATTRIBUTION.format(patients=listing))


def _report_sizes(sample_root: Path, copied: list[Path]) -> None:
    total = sum(f.stat().st_size for f in copied)
    print(f"\ncopied {len(copied)} files, {_human(total)} total")
    for dij in sorted(sample_root.rglob("dij.npz")):
        print(f"  {dij.relative_to(sample_root)}: {_human(dij.stat().st_size)}")
    oversized = [
        (f, f.stat().st_size)
        for f in copied
        if f.stat().st_size >= GITHUB_FILE_LIMIT_BYTES
    ]
    if oversized:
        print(
            "\nWARNING: files exceed GitHub's 100 MB push limit -- use Git LFS or crop:"
        )
        for f, size in oversized:
            print(f"  {f.relative_to(sample_root)}: {_human(size)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data") / "open-kbp-opt-data",
        help="dataset root to sample from (default: data/open-kbp-opt-data)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("sample_data") / "openkbp_opt",
        help="committable sample directory (default: sample_data/openkbp_opt)",
    )
    parser.add_argument(
        "-n", "--num", type=int, default=3, help="number of patients (default: 3)"
    )
    parser.add_argument(
        "--patients",
        nargs="+",
        default=None,
        metavar="PT",
        help="explicit patient ids to sample (overrides --num)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="restrict plan-fluence/dose to this optimization-model dir",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing sample dir"
    )
    args = parser.parse_args(argv)

    source: Path = args.source
    dest: Path = args.dest
    if not (source / "reference-plans").is_dir():
        print(
            f"error: {source} is not a dataset root; run scripts/fetch_openkbp.py first",
            file=sys.stderr,
        )
        return 2

    if dest.exists():
        if not args.force:
            print(f"error: {dest} exists; pass --force to overwrite", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    if args.patients:
        patient_ids = list(args.patients)
    else:
        patient_ids = [d.name for d in find_patient_dirs(source)][: args.num]
    if not patient_ids:
        print("error: no patients selected or available", file=sys.stderr)
        return 1

    print(
        f"curating {len(patient_ids)} patient(s) into {dest}: {', '.join(patient_ids)}"
    )
    copied = curate(source, dest, patient_ids, args.model)
    _write_attribution(dest, patient_ids)
    _report_sizes(dest, copied)

    report = verify_dataset(dest)
    print(f"\nsample recompute-ready: {report.recompute_ready}")
    return 0 if report.recompute_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
