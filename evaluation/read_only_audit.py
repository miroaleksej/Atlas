"""Strict read-only audit for the sealed Φ-Compiler / ScienceAtlas tree.

The audit executes the current scientific, joint AI and seal gates with mutable
state redirected outside the release root, then proves that no file or directory
inside the sealed tree was created, removed or modified.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from source.lawspace.schema import digest_payload
from evaluation.release_files import is_local_artifact

RELEASE = "15.24.0"
OWNER_ID = "READ-ONLY-AUDIT/15.24.0"


def _snapshot(root: Path) -> dict[str, Any]:
    files = {}
    dirs = []
    for p in sorted(root.rglob("*")):
        if is_local_artifact(p, root):
            continue
        rel = str(p.relative_to(root))
        if p.is_symlink():
            files[rel] = {"kind": "symlink", "target": os.readlink(p)}
        elif p.is_file():
            raw = p.read_bytes()
            files[rel] = {"kind": "file", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        elif p.is_dir():
            dirs.append(rel)
    return {"files": files, "dirs": dirs}


def run(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    before = _snapshot(root)
    old_state = os.environ.get("PHI_STATE_DIR")
    old_bytecode = os.environ.get("PYTHONDONTWRITEBYTECODE")
    with tempfile.TemporaryDirectory(prefix="phi-read-only-audit-") as td:
        os.environ["PHI_STATE_DIR"] = str(Path(td) / "state")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        from evaluation.unified_release_qualification import run_release_qualification
        from interfaces.joint_qualification import run_joint_qualification
        from evaluation.seal_audit import run as run_seal_audit
        current = run_release_qualification(root)
        joint = run_joint_qualification(root)
        seal = run_seal_audit(root)
    if old_state is None:
        os.environ.pop("PHI_STATE_DIR", None)
    else:
        os.environ["PHI_STATE_DIR"] = old_state
    if old_bytecode is None:
        os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
    else:
        os.environ["PYTHONDONTWRITEBYTECODE"] = old_bytecode
    after = _snapshot(root)
    before_files, after_files = before["files"], after["files"]
    created = sorted(set(after_files) - set(before_files))
    removed = sorted(set(before_files) - set(after_files))
    modified = sorted(k for k in set(before_files) & set(after_files) if before_files[k] != after_files[k])
    dirs_created = sorted(set(after["dirs"]) - set(before["dirs"]))
    dirs_removed = sorted(set(before["dirs"]) - set(after["dirs"]))
    checks = {
        "current_state_pass": current.get("status") == "PASS_CURRENT_STATE_15_24_0",
        "joint_scientific_ai_pass": joint.get("status") == "PASS_JOINT_CURRENT_15_24_0",
        "seal_pass": seal.get("status") == "PASS_SEAL_AUDIT",
        "no_files_created": not created,
        "no_files_removed": not removed,
        "no_files_modified": not modified,
        "no_directories_created": not dirs_created,
        "no_directories_removed": not dirs_removed,
        "mutable_state_redirected_outside_release": True,
    }
    payload = {
        "schema": "phi-read-only-sealed-tree-audit/v1",
        "release": RELEASE,
        "owner": OWNER_ID,
        "status": "PASS_READ_ONLY_AUDIT" if all(checks.values()) else "FAIL_READ_ONLY_AUDIT",
        "checks": checks,
        "created_files": created,
        "removed_files": removed,
        "modified_files": modified,
        "created_directories": dirs_created,
        "removed_directories": dirs_removed,
        "current_state_digest": current.get("digest"),
        "joint_digest": joint.get("sha256"),
        "seal_digest": seal.get("digest"),
        "claim_boundary": {"audit_mutates_sealed_tree": False, "external_mutable_state_is_scientific_truth": False},
    }
    payload["digest"] = digest_payload(payload)
    return payload


if __name__ == "__main__":
    import json
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
