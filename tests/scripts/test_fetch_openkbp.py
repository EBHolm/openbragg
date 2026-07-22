"""Behavioral test for scripts/fetch_openkbp.py.

The script is dev tooling that lives outside the package, so it is exercised as
a black box: zip up a synthetic openkbp-opt tree, run the script against the
zip, and assert the extracted tree is recompute-ready. Both the flat layout and
an ``open-kbp-opt-data/`` wrapper are covered.
"""

import subprocess
import sys
import zipfile
from pathlib import Path

from conftest import write_synthetic_openkbp_opt_case

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fetch_openkbp.py"


def _zip_tree(tree_root: Path, zip_path: Path, *, arc_prefix: str = "") -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for path in tree_root.rglob("*"):
            if path.is_file():
                arcname = Path(arc_prefix) / path.relative_to(tree_root)
                zf.write(path, arcname)


def _run(zip_path: Path, dest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--zip", str(zip_path), "--dest", str(dest)],
        capture_output=True,
        text=True,
    )


def test_fetch_extracts_flat_bundle(tmp_path: Path) -> None:
    src = tmp_path / "src"
    write_synthetic_openkbp_opt_case(src)
    bundle = tmp_path / "flat.zip"
    _zip_tree(src, bundle)

    dest = tmp_path / "out" / "open-kbp-opt-data"
    result = _run(bundle, dest)

    assert result.returncode == 0, result.stderr
    assert "recompute-ready: True" in result.stdout
    assert "patients (base bundle): 1" in result.stdout
    assert (dest / "reference-plans" / "pt_test" / "ct.csv").is_file()
    assert (dest / "reference-plans" / "pt_test" / "dij.npz").is_file()


def test_fetch_extracts_wrapped_bundle(tmp_path: Path) -> None:
    # Bundle wraps the dataset dirs in a top-level open-kbp-opt-data/ folder.
    src = tmp_path / "src"
    write_synthetic_openkbp_opt_case(src)
    bundle = tmp_path / "wrapped.zip"
    _zip_tree(src, bundle, arc_prefix="open-kbp-opt-data")

    dest = tmp_path / "out" / "open-kbp-opt-data"
    result = _run(bundle, dest)

    assert result.returncode == 0, result.stderr
    assert "recompute-ready: True" in result.stdout
    assert (dest / "paper-plans").is_dir()


def test_fetch_missing_zip_errors(tmp_path: Path) -> None:
    result = _run(tmp_path / "nope.zip", tmp_path / "out")
    assert result.returncode == 2
    assert "not found" in result.stderr
