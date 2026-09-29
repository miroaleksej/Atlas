"""Domain-neutral provider capabilities, WORLD trust metadata and evidence planning.

This module is deliberately declarative.  It does not fetch network resources,
does not import provider SDKs, does not hold private keys, and does not promote
scientific claims.  It lets the existing research/execution owners choose among
known capabilities or fail closed with ``NO_CAPABLE_PROVIDER``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import digest_payload

PROVIDER_REGISTRY_SCHEMA = "phi-source-provider-capability-registry/v1"
WORLD_TRUST_SCHEMA = "phi-world-trust-public-registry/v1"
CAMPAIGN_SCHEMA = "phi-world-evidence-campaign-plan/v1"


def _root(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = digest_payload({k: v for k, v in payload.items() if k != "digest"})
    return payload


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _provider_registry_path(root: str | Path | None = None) -> Path:
    return _root(root) / "data" / "source_providers" / "providers.json"


def _world_trust_path(root: str | Path | None = None) -> Path:
    return _root(root) / "data" / "world_trust" / "attestors.json"


def load_provider_capability_registry(root: str | Path | None = None) -> Mapping[str, Any]:
    path = _provider_registry_path(root)
    doc = dict(_read_json(path))
    if doc.get("schema") != PROVIDER_REGISTRY_SCHEMA:
        raise ValueError(f"unsupported provider capability registry schema: {doc.get('schema')!r}")
    providers = doc.get("providers")
    if not isinstance(providers, list):
        raise ValueError("providers must be a list")
    ids: set[str] = set()
    required = {
        "provider_id", "source_class", "domains", "observable_types", "supported_axes",
        "query_schema", "spatial_temporal_resolution", "uncertainty_available",
        "authentication_mode", "cost_rate_limit", "artifact_format",
        "world_attestation_mode",
    }
    for row in providers:
        if not isinstance(row, Mapping):
            raise ValueError("provider rows must be mappings")
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(f"provider capability missing fields: {missing}")
        provider_id = str(row.get("provider_id", "")).strip()
        if not provider_id or provider_id in ids:
            raise ValueError(f"duplicate or empty provider_id: {provider_id!r}")
        ids.add(provider_id)
        if str(row.get("source_class", "")).upper() not in {"FORWARD_ORACLE", "OBSERVATIONAL_ARCHIVE"}:
            raise ValueError(f"{provider_id}: invalid source_class")
        for key in ("domains", "observable_types", "supported_axes"):
            values = row.get(key)
            if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
                raise ValueError(f"{provider_id}: {key} must be a nonempty string list")
        if not isinstance(row.get("uncertainty_available"), bool):
            raise ValueError(f"{provider_id}: uncertainty_available must be boolean")
        if not isinstance(row.get("query_schema"), Mapping):
            raise ValueError(f"{provider_id}: query_schema must be an object")
    return _with_digest(doc)


def load_world_trust_registry(root: str | Path | None = None) -> Mapping[str, Any]:
    path = _world_trust_path(root)
    doc = dict(_read_json(path))
    if doc.get("schema") != WORLD_TRUST_SCHEMA:
        raise ValueError(f"unsupported WORLD trust registry schema: {doc.get('schema')!r}")
    entries = doc.get("attestors")
    if not isinstance(entries, list):
        raise ValueError("attestors must be a list")
    ids: set[str] = set()
    for row in entries:
        if not isinstance(row, Mapping):
            raise ValueError("attestor rows must be mappings")
        forbidden = sorted(k for k in row if "private" in str(k).lower() or "secret" in str(k).lower())
        if forbidden:
            raise ValueError(f"WORLD trust registry must not contain secret material: {forbidden}")
        key_id = str(row.get("key_id", "")).strip()
        if not key_id or key_id in ids:
            raise ValueError(f"duplicate or empty key_id: {key_id!r}")
        ids.add(key_id)
        if not str(row.get("public_key", "")).strip():
            raise ValueError(f"{key_id}: public_key required")
        if not isinstance(row.get("provider_scope"), list):
            raise ValueError(f"{key_id}: provider_scope must be a list")
        if str(row.get("role", "")).upper() != "WORLD_ATTESTOR":
            raise ValueError(f"{key_id}: role must be WORLD_ATTESTOR")
    return _with_digest(doc)


def match_source_provider(intent: Mapping[str, Any], root: str | Path | None = None) -> Mapping[str, Any]:
    registry = load_provider_capability_registry(root)
    domain = str(intent.get("domain_id") or intent.get("domain") or "").strip()
    source_class = str(intent.get("source_class") or "OBSERVATIONAL_ARCHIVE").strip().upper()
    observable = str(intent.get("needed_observable") or intent.get("observable_type") or "").strip()
    axis = str(intent.get("axis_id") or intent.get("supported_axis") or observable).strip()
    require_uncertainty = bool(intent.get("require_uncertainty", False))
    candidates = []
    for provider in registry["providers"]:
        if source_class and provider["source_class"] != source_class:
            continue
        if domain and domain not in provider["domains"]:
            continue
        observable_ok = (not observable) or observable in provider["observable_types"]
        axis_ok = (not axis) or axis in provider["supported_axes"]
        if not (observable_ok or axis_ok):
            continue
        if require_uncertainty and provider["uncertainty_available"] is not True:
            continue
        candidates.append(provider)
    candidates = sorted(candidates, key=lambda row: str(row["provider_id"]))
    if not candidates:
        return _with_digest({
            "schema": "phi-source-provider-match/v1",
            "status": "NO_CAPABLE_PROVIDER",
            "intent": dict(intent),
            "provider_registry_digest": registry["digest"],
            "selected_provider": None,
            "candidate_count": 0,
            "atlas_invented_provider": False,
        })
    return _with_digest({
        "schema": "phi-source-provider-match/v1",
        "status": "CAPABLE_PROVIDER_SELECTED",
        "intent": dict(intent),
        "provider_registry_digest": registry["digest"],
        "selected_provider": candidates[0],
        "candidate_count": len(candidates),
        "atlas_invented_provider": False,
    })


def plan_world_evidence_campaign(
    candidates: Sequence[Mapping[str, Any]],
    root: str | Path | None = None,
    *,
    max_items: int = 10,
) -> Mapping[str, Any]:
    """Rank U4-style candidates whose missing evidence can be obtained.

    Candidate rows are read-only planning records.  Supported inputs:
    ``candidate_id``, ``scientific_value`` and either ``measurement_intent`` or
    ``missing_evidence`` entries containing provider-match fields.
    """
    if int(max_items) < 1:
        raise ValueError("max_items must be >= 1")
    trust = load_world_trust_registry(root)
    rows = []
    for candidate in candidates:
        cid = str(candidate.get("candidate_id") or candidate.get("proposal_id") or "").strip()
        if not cid:
            continue
        intents = candidate.get("missing_evidence")
        if isinstance(candidate.get("measurement_intent"), Mapping):
            intents = [candidate["measurement_intent"]]
        if not isinstance(intents, list):
            intents = []
        matches = [match_source_provider(intent, root) for intent in intents if isinstance(intent, Mapping)]
        capable = [m for m in matches if m["status"] == "CAPABLE_PROVIDER_SELECTED"]
        value = float(candidate.get("scientific_value", 0.0) or 0.0)
        rows.append({
            "candidate_id": cid,
            "scientific_value": value,
            "u_stage": candidate.get("u_stage", candidate.get("stage", "U4")),
            "match_count": len(capable),
            "matches": capable,
            "blocked_matches": [m for m in matches if m["status"] != "CAPABLE_PROVIDER_SELECTED"],
            "status": "EVIDENCE_OBTAINABLE" if capable else "NO_CAPABLE_PROVIDER",
        })
    rows.sort(key=lambda row: (-int(row["match_count"] > 0), -row["scientific_value"], row["candidate_id"]))
    selected = rows[: int(max_items)]
    return _with_digest({
        "schema": CAMPAIGN_SCHEMA,
        "status": "CAMPAIGN_PLAN_READY",
        "selected": selected,
        "source_provider_registry": load_provider_capability_registry(root),
        "world_trust_registry_digest": trust["digest"],
        "active_world_attestor_count": len(trust.get("attestors", ())),
        "mutation_performed": False,
        "scientific_promotion_allowed": False,
        "atlas_invents_provider": False,
        "private_key_in_repository": False,
    })
