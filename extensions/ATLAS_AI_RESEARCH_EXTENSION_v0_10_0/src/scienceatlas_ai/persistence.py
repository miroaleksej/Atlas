"""Transactional persistence for authoritative ScienceAtlas AI state."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .provenance import canonical_bytes, digest_json, sha256_hex
from .runtime import ScienceAtlasAI


def build_manifest(
    state_payload: Mapping[str, Any],
    *,
    code_digest: str,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    config_payload = dict(config or {})
    body = {
        "schema": "scienceatlas-ai-state-manifest-v1",
        "version": ScienceAtlasAI.VERSION,
        "snapshot_root": str(state_payload["snapshot_root"]),
        "trace_head": str(state_payload["trace"]["head"]),
        "state_digest": sha256_hex(canonical_bytes(dict(state_payload))),
        "runtime_contract_digest": str(state_payload["runtime_contract_digest"]),
        "code_digest": str(code_digest),
        "config_digest": digest_json(config_payload, namespace=b"SCIENCEATLAS_AI_CONFIG_V1"),
    }
    body["manifest_root"] = digest_json(body, namespace=b"SCIENCEATLAS_AI_MANIFEST_V1")
    return body


def save_state(
    path: str | Path,
    ai: ScienceAtlasAI,
    *,
    code_digest: str | None = None,
    config: Mapping[str, Any] | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    state_payload = ai.to_json()
    manifest = build_manifest(
        state_payload,
        code_digest=code_digest or ai.runtime_contract_digest,
        config=config,
    )
    envelope = {
        "schema": "scienceatlas-ai-transactional-envelope-v1",
        "state": state_payload,
        "manifest": manifest,
    }
    data = canonical_bytes(envelope)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
        try:
            dir_fd = os.open(target.parent, os.O_DIRECTORY)
        except (AttributeError, OSError):
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return target


def load_state(
    path: str | Path,
    *,
    expected_code_digest: str | None = None,
    config: Mapping[str, Any] | None = None,
) -> ScienceAtlasAI:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != "scienceatlas-ai-transactional-envelope-v1":
        raise ValueError("unsupported persistence envelope")
    state = dict(payload["state"])
    manifest = dict(payload["manifest"])
    supplied_root = str(manifest.pop("manifest_root", ""))
    expected_root = digest_json(manifest, namespace=b"SCIENCEATLAS_AI_MANIFEST_V1")
    if supplied_root != expected_root:
        raise ValueError("manifest root mismatch")
    if sha256_hex(canonical_bytes(state)) != str(manifest.get("state_digest", "")):
        raise ValueError("state digest mismatch")
    if str(state.get("snapshot_root", "")) != str(manifest.get("snapshot_root", "")):
        raise ValueError("snapshot root/manifest mismatch")
    if str(state.get("trace", {}).get("head", "")) != str(manifest.get("trace_head", "")):
        raise ValueError("trace head/manifest mismatch")
    config_digest = digest_json(dict(config or {}), namespace=b"SCIENCEATLAS_AI_CONFIG_V1")
    if config_digest != str(manifest.get("config_digest", "")):
        raise ValueError("configuration digest mismatch")
    if expected_code_digest is not None and str(manifest.get("code_digest", "")) != expected_code_digest:
        raise ValueError("code digest mismatch")
    ai = ScienceAtlasAI.from_json(state)
    if ai.snapshot_root() != str(manifest.get("snapshot_root", "")):
        raise ValueError("restored state root mismatch")
    return ai
