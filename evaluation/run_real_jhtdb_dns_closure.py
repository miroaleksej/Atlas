"""One-command launcher for the real JHTDB cross-Re turbulence closure experiment."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_MANIFEST = Path("examples/turbulence_dns_closure_manifest.real.json")
DEFAULT_OUTPUT = Path("reports/TURBULENCE_DNS_CLOSURE_CURRENT.json")


def _manifest_ready(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for entry in manifest.get("datasets", []):
            p = Path(str(entry["path"]))
            if not p.is_absolute():
                p = path.parent / p
            if not p.is_file():
                return False
        return bool(manifest.get("datasets"))
    except Exception:
        return False


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--components", default="x,y,z")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--skip-null-control", action="store_true")
    args = parser.parse_args(argv)

    manifest = Path(args.manifest)
    if args.force_download or not _manifest_ready(manifest):
        fetch_cmd = [
            sys.executable, "-m", "evaluation.fetch_jhtdb_real_snapshots",
            "--manifest", str(manifest),
        ]
        if args.force_download:
            fetch_cmd.append("--force")
        _run(fetch_cmd)
    else:
        print(f"real JHTDB manifest and all referenced NPZ files already exist: {manifest}", flush=True)

    if args.download_only:
        return 0

    run_cmd = [
        sys.executable, "-m", "evaluation.turbulence_dns_closure_experiment",
        "--manifest", str(manifest),
        "--components", args.components,
        "--output", args.output,
        "--summary",
    ]
    if args.skip_null_control:
        run_cmd.append("--skip-null-control")
    _run(run_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
