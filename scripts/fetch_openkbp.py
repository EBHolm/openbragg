#!/usr/bin/env python3
"""Fetch and organize the openkbp-opt dataset into a local, git-ignored tree.

openkbp-opt ships as two OneDrive zip bundles and has *no* upstream download
script (its README says: download the zips by hand, unzip into
``open-kbp-opt-data``). This tool extracts those bundles into the
``open-kbp-opt-data`` layout that ``openbragg.io.openkbp_opt`` loads, and
verifies the result.

Because the bundles are OneDrive *personal* share links, headless download is
unreliable (the anonymous OneDrive share API now returns 401; TLS-intercepting
corporate proxies block it too). The reliable path is to download both zips in
a browser, then point this script at them::

    uv run python scripts/fetch_openkbp.py \\
        --zip ~/Downloads/base.zip --zip ~/Downloads/optional.zip

A best-effort direct download is attempted when no ``--zip`` is given; if it
fails, the browser links and target paths are printed. Set ``SSL_CERT_FILE`` to
your corporate CA bundle to let the auto-download traverse an intercepting proxy.
"""

from __future__ import annotations

import argparse
import base64
import shutil
import ssl
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from openbragg.io.openkbp_opt import verify_dataset

DATASET_DIRNAME = "open-kbp-opt-data"

# Recognized top-level dataset directories inside the bundles (see dataset README).
DATASET_SUBDIRS: tuple[str, ...] = (
    "reference-plans",
    "paper-predictions",
    "paper-plans",
    "results-data",
    "results",
)


@dataclass(frozen=True)
class Bundle:
    key: str
    url: str
    size_gb: float
    contents: str


# OneDrive share links + sizes taken verbatim from the open-kbp-opt README.
BUNDLES: dict[str, Bundle] = {
    "base": Bundle(
        key="base",
        url="https://1drv.ms/u/c/2150c5a213e729e3/EeMp5xOixVAggCFvAAAAAAABEDPNyGWc32_OuGeTHUFZkw?e=x3V3fq",
        size_gb=10.19,
        contents="reference-plans + paper-predictions (CT, masks, dij, reference/predicted doses)",
    ),
    "optional": Bundle(
        key="optional",
        url="https://1drv.ms/u/c/2150c5a213e729e3/EeMp5xOixVAggCFwAAAAAAABgPUYh9eHaIT0pv-w-8yF6A?e=2QDrwB",
        size_gb=13.08,
        contents="paper-plans + results (plan-fluence = the beamlet weights w, plan-dose, gaps)",
    ),
}


def _onedrive_direct_url(share_url: str) -> str:
    """Encode a OneDrive share URL into its (legacy) direct-content API URL."""
    token = base64.b64encode(share_url.encode("utf-8")).decode("utf-8")
    token = "u!" + token.rstrip("=").replace("/", "_").replace("+", "-")
    return f"https://api.onedrive.com/v1.0/shares/{token}/root/content"


def attempt_download(bundle: Bundle, out_path: Path) -> bool:
    """Best-effort headless download. Returns True on success, False otherwise.

    OneDrive personal shares routinely reject non-browser clients, so failure
    here is expected and handled by falling back to manual download.
    """
    print(f"[{bundle.key}] attempting best-effort download (~{bundle.size_gb} GB)...")
    try:
        ctx = ssl.create_default_context()  # honors SSL_CERT_FILE for corporate CAs
        req = urllib.request.Request(
            _onedrive_direct_url(bundle.url), headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            with open(out_path, "wb") as fh:
                shutil.copyfileobj(resp, fh)
    except Exception as exc:  # report and fall back to manual download
        print(f"[{bundle.key}] auto-download failed: {type(exc).__name__}: {exc}")
        out_path.unlink(missing_ok=True)
        return False
    if not zipfile.is_zipfile(out_path):
        out_path.unlink(missing_ok=True)
        print(f"[{bundle.key}] response was not a zip (likely a login/redirect page).")
        return False
    return True


def _find_dataset_root(extracted: Path) -> Path:
    """Return the directory in *extracted* that directly holds dataset subdirs.

    Handles both a bundle that wraps everything in ``open-kbp-opt-data/`` and one
    that places the dataset subdirs at the archive root.
    """
    candidates = [extracted, *(p for p in extracted.rglob("*") if p.is_dir())]
    for candidate in candidates:
        if any((candidate / name).is_dir() for name in DATASET_SUBDIRS):
            return candidate
    raise SystemExit(
        f"archive contained none of the expected dataset dirs {DATASET_SUBDIRS}"
    )


def _merge_dir(src: Path, dst: Path) -> None:
    """Move the contents of *src* into *dst*, merging into existing directories."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _merge_dir(item, target)
        else:
            shutil.move(str(item), str(target))


def extract_bundle(zip_path: Path, dest: Path) -> None:
    """Extract *zip_path* and merge its recognized dataset dirs into *dest*."""
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        print(f"    unzipping {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        src_root = _find_dataset_root(tmp_path)
        for name in DATASET_SUBDIRS:
            src = src_root / name
            if src.is_dir():
                _merge_dir(src, dest / name)


def _print_manual_instructions(failed: list[Bundle], dest: Path) -> None:
    line = "=" * 78
    print(f"\n{line}")
    print("Automatic download unavailable — download these in a browser, then re-run:")
    for bundle in failed:
        print(f"\n  {bundle.key} bundle (~{bundle.size_gb} GB): {bundle.contents}")
        print(f"    {bundle.url}")
    zips = " ".join(f"--zip <{bundle.key}.zip>" for bundle in failed)
    print(f"\nThen re-run pointing at the downloaded zip(s):")
    print(f"    uv run python scripts/fetch_openkbp.py {zips} --dest {dest}")
    print(
        "\n(Behind a TLS-intercepting proxy? Point SSL_CERT_FILE at your corporate CA"
        "\n bundle to let the auto-download succeed.)"
    )
    print(line)


def _report(dest: Path) -> int:
    report = verify_dataset(dest)
    fluence = "present" if report.has_plan_fluence else "MISSING (optional bundle)"
    print()
    print(f"dataset root: {dest}")
    print(f"  patients (base bundle): {len(report.patient_ids)}")
    print(f"  plan-fluence (optional bundle): {fluence}")
    print(f"  recompute-ready: {report.recompute_ready}")
    return 0 if report.patient_ids else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data") / DATASET_DIRNAME,
        help="target dataset directory (git-ignored; default: data/open-kbp-opt-data)",
    )
    parser.add_argument(
        "--zip",
        dest="zips",
        action="append",
        type=Path,
        default=[],
        metavar="PATH",
        help="local bundle zip to extract (repeatable); when given, skips download",
    )
    parser.add_argument(
        "--bundle",
        choices=["base", "optional", "both"],
        default="both",
        help="which bundle(s) to auto-download when no --zip is given (default: both)",
    )
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=Path("data") / "downloads",
        help="where to place/cache downloaded zips (default: data/downloads)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="only verify --dest and report; download/extract nothing",
    )
    args = parser.parse_args(argv)
    dest: Path = args.dest

    if args.verify_only:
        return _report(dest)

    if args.zips:
        for zip_path in args.zips:
            if not zip_path.is_file():
                print(f"error: {zip_path} not found", file=sys.stderr)
                return 2
            extract_bundle(zip_path, dest)
    else:
        wanted = ["base", "optional"] if args.bundle == "both" else [args.bundle]
        args.downloads_dir.mkdir(parents=True, exist_ok=True)
        failed: list[Bundle] = []
        for key in wanted:
            bundle = BUNDLES[key]
            zip_path = args.downloads_dir / f"open-kbp-opt-{key}.zip"
            if zip_path.is_file() and zipfile.is_zipfile(zip_path):
                print(f"[{key}] using cached {zip_path}")
            elif not attempt_download(bundle, zip_path):
                failed.append(bundle)
                continue
            extract_bundle(zip_path, dest)
        if failed:
            _print_manual_instructions(failed, dest)

    return _report(dest)


if __name__ == "__main__":
    raise SystemExit(main())
