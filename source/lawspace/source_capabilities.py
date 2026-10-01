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
RUN_SCHEMA = "phi-world-closed-loop-campaign-run/v1"
REQUIRED_EVIDENCE_ROUTE_SCHEMA = "phi-required-evidence-route-compiler/v1"
UNIVERSAL_REQUIRED_EVIDENCE_LOOP_SCHEMA = "phi-universal-required-evidence-execution-loop/v1"
SEMANTIC_EVIDENCE_NEED_SCHEMA = "phi-semantic-evidence-need-derivation/v1"
UNIVERSAL_OBLIGATION_EXECUTION_SCHEMA = "phi-universal-obligation-execution-step/v1"
EPISTEMIC_METABOLISM_SCHEMA = "phi-epistemic-metabolism-cycle/v1"
IDEAL_AI_FORMULA_SEARCH_SCHEMA = "phi-ideal-ai-formula-search/v1"


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


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _frontier_path(root: str | Path | None = None) -> Path:
    return _root(root) / "data" / "frontiers" / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"


def _frontier_rows(root: str | Path | None = None, *, limit: int = 200) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    path = _frontier_path(root)
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def _frontier_row_count(root: str | Path | None = None) -> int:
    path = _frontier_path(root)
    with path.open(encoding="utf-8") as stream:
        return sum(1 for line in stream if line.strip())


def _semantic_tokens_from_candidate(row: Mapping[str, Any]) -> list[str]:
    payload = row.get("payload", {}) if isinstance(row.get("payload"), Mapping) else {}
    promotion = row.get("promotion_path", {}) if isinstance(row.get("promotion_path"), Mapping) else {}
    tokens: list[str] = []
    for axis in payload.get("axis_ids", ()) or ():
        text = str(axis)
        tokens.append(text)
        tokens.append(text.rsplit(".", 1)[-1])
    for key in ("required_observables", "observables", "measurement_obligations", "missing_evidence"):
        value = payload.get(key)
        if isinstance(value, str):
            tokens.append(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            tokens.extend(str(x) for x in value)
    for gate in (promotion.get("gates", {}) or {}).values():
        if not isinstance(gate, Mapping):
            continue
        for item in gate.get("required_evidence", ()) or ():
            tokens.append(str(item))
        tokens.append(str(gate.get("reason", "")))
        tokens.append(str(gate.get("status", "")))
    app = payload.get("applicability_contract", {}) if isinstance(payload.get("applicability_contract"), Mapping) else {}
    tokens.extend(str(app.get(key, "")) for key in ("status", "next_requirement", "measurement_projection_status"))
    return [token for token in dict.fromkeys(t.strip() for t in tokens) if token]


def derive_semantic_evidence_needs(row: Mapping[str, Any]) -> Mapping[str, Any]:
    """Derive evidence needs from candidate semantics, not from provider/domain dispatch.

    Providers may later declare whether they can satisfy a need.  This function
    only reads the frozen candidate contract: axes, required-evidence text,
    promotion gates and applicability status.  Domain labels are preserved as
    metadata outside the intent and never choose the observable.
    """
    cid = str(row.get("candidate_id") or "")
    payload = row.get("payload", {}) if isinstance(row.get("payload"), Mapping) else {}
    promotion = row.get("promotion_path", {}) if isinstance(row.get("promotion_path"), Mapping) else {}
    tokens = _semantic_tokens_from_candidate(row)
    lower_tokens = " ".join(tokens).casefold()
    intents: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_need(observable: str, *, axis_id: str | None = None, source: str, require_uncertainty: bool = False) -> None:
        observable = str(observable).strip()
        axis = str(axis_id or observable).strip()
        if not observable or not axis:
            return
        key = (observable, axis)
        if key in seen:
            return
        seen.add(key)
        intents.append({
            "needed_observable": observable,
            "axis_id": axis,
            "source_class": "OBSERVATIONAL_ARCHIVE",
            "require_uncertainty": bool(require_uncertainty),
            "evidence_need_source": source,
            "derived_from_claim_semantics": True,
            "core_domain_dispatch_used": False,
        })

    for axis in payload.get("axis_ids", ()) or ():
        axis_text = str(axis)
        short = axis_text.rsplit(".", 1)[-1]
        if short:
            add_need(short, axis_id=short, source="typed_axis")
    for observable in payload.get("required_observables", ()) or ():
        add_need(str(observable), source="declared_required_observable")
    for observable in payload.get("observables", ()) or ():
        add_need(str(observable), source="declared_observable")
    if "uncertainty" in lower_tokens or "неопредел" in lower_tokens:
        for intent in list(intents):
            if not intent.get("require_uncertainty"):
                updated = dict(intent)
                updated["require_uncertainty"] = True
                updated["evidence_need_source"] = str(intent.get("evidence_need_source")) + "+uncertainty_requirement"
                key = (str(updated["needed_observable"]), str(updated["axis_id"]))
                intents[intents.index(intent)] = updated
                seen.add(key)
    app = payload.get("applicability_contract", {}) if isinstance(payload.get("applicability_contract"), Mapping) else {}
    status = str(app.get("status", "") or "")
    if status in {"OBSERVER_OR_PARAMETERIZATION_REQUIRED", "REPRESENTATION_AND_WORLD_ATTESTATION_REQUIRED"}:
        for axis in payload.get("unbound_axis_ids", ()) or ():
            short = str(axis).rsplit(".", 1)[-1]
            add_need(short, axis_id=short, source="unbound_observer_or_parameterization")
    gates = promotion.get("gates", {}) if isinstance(promotion.get("gates"), Mapping) else {}
    for gate_id, gate in gates.items():
        if not isinstance(gate, Mapping) or gate.get("pass") is True:
            continue
        for item in gate.get("required_evidence", ()) or ():
            text = str(item).casefold()
            # Only convert explicit measurement/observation requirements to
            # source-provider intents; type/proof gaps remain obligations.
            if any(word in text for word in ("measurement", "observation", "world", "data", "evidence", "измер", "наблюд", "данн")):
                for token in _semantic_tokens_from_candidate(row):
                    short = token.rsplit(".", 1)[-1]
                    if short and len(short) > 2:
                        add_need(short, axis_id=short, source=f"promotion_gate:{gate_id}")
                break
    return _with_digest({
        "schema": SEMANTIC_EVIDENCE_NEED_SCHEMA,
        "candidate_id": cid,
        "status": "SEMANTIC_EVIDENCE_NEEDS_DERIVED" if intents else "SEMANTIC_EVIDENCE_NEEDS_NOT_DERIVED_NO_MEASUREMENT_OBLIGATION",
        "intents": intents,
        "token_count": len(tokens),
        "core_domain_dispatch_used": False,
        "claim_boundary": {
            "provider_declares_what_claim_needs": False,
            "domain_name_selects_observable": False,
            "evidence_need_is_world_evidence": False,
        },
    })


def _frontier_intents(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Compatibility wrapper for semantic evidence-need derivation."""
    return list(derive_semantic_evidence_needs(row).get("intents", ()))


def _representation_world_state(root: str | Path | None = None) -> Mapping[str, Any]:
    from .domains import DOMAIN_REGISTRIES, canonical_axis_count
    from .knowledge_evolution import KnowledgeEvolutionKernel

    state = KnowledgeEvolutionKernel(_root(root)).state()
    domain_axes = {
        domain_id: sorted(reg.axes)
        for domain_id, reg in sorted(DOMAIN_REGISTRIES.items())
    }
    payload = {
        "schema": "phi-representation-world-model-state-digest/v1",
        "canonical_axis_count": canonical_axis_count(),
        "domain_axis_digest": digest_payload(domain_axes),
        "knowledge_state_digest": digest_payload(state),
        "world_attestation_count": len(state.get("world_attestations", ())),
    }
    return _with_digest(payload)


def run_world_closed_loop_campaign(
    root: str | Path | None = None,
    *,
    max_frontier_rows: int = 200,
    max_campaign_items: int = 10,
) -> Mapping[str, Any]:
    """Plan a real-provider frontier campaign and stop before fake attestation.

    The function uses the current persistent frontier and declared provider
    registry.  It does not fetch external data and does not mutate representation
    or world models.  Independently attested episodes can only appear after an
    external WORLD signer is registered and actual signed evidence is supplied.
    """
    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("campaign limits must be >= 1")
    before = _representation_world_state(root_path)
    frontier_rows = _frontier_rows(root_path, limit=int(max_frontier_rows))
    candidate_specs = []
    for row in frontier_rows:
        intents = _frontier_intents(row)
        if not intents:
            continue
        payload = row.get("payload", {}) if isinstance(row.get("payload"), Mapping) else {}
        candidate_specs.append({
            "candidate_id": row.get("candidate_id"),
            "u_stage": (row.get("promotion_path") or {}).get("next_gate", "U5"),
            "scientific_value": float(payload.get("applicability_contract", {}).get("applicability_score", 0.0) or 0.0),
            "missing_evidence": intents,
        })
    plan = plan_world_evidence_campaign(candidate_specs, root_path, max_items=int(max_campaign_items))
    trust = load_world_trust_registry(root_path)
    active_attestors = [
        row for row in trust.get("attestors", ())
        if isinstance(row, Mapping) and str(row.get("revocation_state", "ACTIVE")).upper() != "REVOKED"
    ]
    episodes = []
    for row in plan.get("selected", ()):
        if row.get("status") != "EVIDENCE_OBTAINABLE":
            continue
        provider = row["matches"][0]["selected_provider"]
        episodes.append({
            "candidate_id": row["candidate_id"],
            "provider_id": provider["provider_id"],
            "source_class": provider["source_class"],
            "status": "WORLD_ATTESTATION_BLOCKED_NO_ACTIVE_ATTESTOR" if not active_attestors else "READY_FOR_EXTERNAL_ACQUISITION_AND_ATTESTATION",
            "artifact_acquired": False,
            "independently_attested": False,
            "representation_update_allowed": False,
            "world_model_update_allowed": False,
        })
    after = _representation_world_state(root_path)
    attested = [row for row in episodes if row["independently_attested"] is True]
    status = (
        "CAMPAIGN_BLOCKED_WORLD_ATTESTOR_REQUIRED"
        if episodes and not active_attestors
        else "CAMPAIGN_READY_FOR_EXTERNAL_ACQUISITION"
        if episodes
        else "CAMPAIGN_BLOCKED_NO_CAPABLE_PROVIDER"
    )
    return _with_digest({
        "schema": RUN_SCHEMA,
        "status": status,
        "frontier_ledger_sha256": _sha256_file(_frontier_path(root_path)),
        "frontier_rows_examined": len(frontier_rows),
        "candidate_specs_with_measurement_intents": len(candidate_specs),
        "provider_matched_episode_count": len(episodes),
        "independently_attested_episode_count": len(attested),
        "episodes": episodes,
        "campaign_plan_digest": plan["digest"],
        "provider_registry_digest": plan["source_provider_registry"]["digest"],
        "world_trust_registry_digest": trust["digest"],
        "active_world_attestor_count": len(active_attestors),
        "representation_world_model_before": before,
        "representation_world_model_after": after,
        "representation_world_model_changed": before["digest"] != after["digest"],
        "mutation_performed": False,
        "external_data_fetched": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "provider_match_is_world_evidence": False,
            "retrospective_frontier_planning_is_independent_attestation": False,
            "empty_world_trust_store_can_update_world_model": False,
            "atlas_may_invent_provider": False,
        },
    })


def _candidate_ids(state: Mapping[str, Any], section: str) -> set[str]:
    return {
        str(row.get("candidate_id"))
        for row in state.get(section, ())
        if isinstance(row, Mapping) and str(row.get("candidate_id", "")).strip()
    }


def _candidate_rows_by_id(root: Path, *, limit: int) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("candidate_id")): row
        for row in _frontier_rows(root, limit=limit)
        if str(row.get("candidate_id", "")).strip()
    }


def _state_rows_by_candidate(state: Mapping[str, Any], section: str) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in state.get(section, ()):
        if not isinstance(row, Mapping):
            continue
        cid = str(row.get("candidate_id", ""))
        if cid and cid not in out:
            out[cid] = row
    return out


def run_existing_lowering_projection_preflight(
    root: str | Path | None = None,
    *,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
) -> Mapping[str, Any]:
    """Classify provider-matched episodes through existing lowering/projection gates.

    This is a read-only mass preflight for the already existing owners.  It does
    not synthesize a response projection when the hypothesis has no declared
    response observable contract, and it does not freeze a prediction lowering
    without a frozen response projection.
    """
    from .knowledge_evolution import KnowledgeEvolutionKernel

    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("preflight limits must be >= 1")
    state = KnowledgeEvolutionKernel(root_path).state()
    campaign = run_world_closed_loop_campaign(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    frontier = _candidate_rows_by_id(root_path, limit=int(max_frontier_rows))
    hypotheses = _state_rows_by_candidate(state, "hypothesis_materializations")
    lowerings = _state_rows_by_candidate(state, "candidate_prediction_lowerings")
    projections = _state_rows_by_candidate(state, "candidate_response_projections")
    bindings = _state_rows_by_candidate(state, "candidate_world_bindings")

    counts = {
        "episode_count": 0,
        "frontier_ready": 0,
        "provider_matched": 0,
        "u4_materialized": 0,
        "u4_materialization_required": 0,
        "response_observable_contract_ready": 0,
        "response_observable_contract_required": 0,
        "world_binding_ready": 0,
        "world_binding_required": 0,
        "response_projection_ready": 0,
        "response_projection_required": 0,
        "prediction_lowering_ready": 0,
        "prediction_lowering_required": 0,
        "ready_for_frozen_runtime": 0,
    }
    receipts: list[dict[str, Any]] = []
    for episode in campaign.get("episodes", ()):
        if not isinstance(episode, Mapping):
            continue
        cid = str(episode.get("candidate_id", ""))
        candidate = frontier.get(cid, {})
        hypothesis = hypotheses.get(cid, {})
        measurement_contract = dict((hypothesis.get("measurement_contract", {}) or {})) if isinstance(hypothesis, Mapping) else {}
        response_observable_ids = tuple(str(x) for x in measurement_contract.get("response_observable_ids", ()) if str(x).strip())
        provider_matched = bool(episode.get("provider_id"))
        frontier_ready = cid in frontier
        u4_ready = cid in hypotheses
        observable_ready = bool(response_observable_ids)
        binding_ready = cid in bindings
        projection_ready = cid in projections
        lowering_ready = cid in lowerings
        counts["episode_count"] += 1
        counts["frontier_ready"] += int(frontier_ready)
        counts["provider_matched"] += int(provider_matched)
        counts["u4_materialized"] += int(u4_ready)
        counts["u4_materialization_required"] += int(not u4_ready)
        counts["response_observable_contract_ready"] += int(observable_ready)
        counts["response_observable_contract_required"] += int(u4_ready and not observable_ready)
        counts["world_binding_ready"] += int(binding_ready)
        counts["world_binding_required"] += int(u4_ready and observable_ready and not binding_ready)
        counts["response_projection_ready"] += int(projection_ready)
        counts["response_projection_required"] += int(u4_ready and observable_ready and binding_ready and not projection_ready)
        counts["prediction_lowering_ready"] += int(lowering_ready)
        counts["prediction_lowering_required"] += int(projection_ready and not lowering_ready)
        counts["ready_for_frozen_runtime"] += int(provider_matched and projection_ready and lowering_ready)

        if not frontier_ready:
            terminal_status = "BLOCKED_FRONTIER_RECORD_NOT_IN_WINDOW"
        elif not provider_matched:
            terminal_status = "BLOCKED_NO_CAPABLE_PROVIDER"
        elif not u4_ready:
            terminal_status = "BLOCKED_U4_MATERIALIZATION_REQUIRED"
        elif not observable_ready:
            terminal_status = "BLOCKED_RESPONSE_OBSERVABLE_CONTRACT_REQUIRED"
        elif not binding_ready:
            terminal_status = "BLOCKED_CANDIDATE_WORLD_BINDING_REQUIRED"
        elif not projection_ready:
            terminal_status = "BLOCKED_RESPONSE_PROJECTION_FREEZE_REQUIRED"
        elif not lowering_ready:
            terminal_status = "BLOCKED_PREDICTION_LOWERING_REQUIRED"
        else:
            terminal_status = "READY_FOR_FROZEN_RUNTIME_WORLD_ATTESTATION_GATE"

        receipts.append(_with_digest({
            "schema": "phi-existing-lowering-projection-preflight-episode/v1",
            "candidate_id": cid,
            "provider_id": episode.get("provider_id"),
            "candidate_record_digest": candidate.get("record_digest") if isinstance(candidate, Mapping) else None,
            "hypothesis_digest": hypothesis.get("digest") if isinstance(hypothesis, Mapping) else None,
            "response_observable_ids": response_observable_ids,
            "checks": {
                "FRONTIER_RECORD_READY": frontier_ready,
                "PROVIDER_MATCHED": provider_matched,
                "U4_HYPOTHESIS_MATERIALIZED": u4_ready,
                "RESPONSE_OBSERVABLE_CONTRACT_DECLARED": observable_ready,
                "CANDIDATE_WORLD_BINDING_READY": binding_ready,
                "RESPONSE_PROJECTION_FROZEN": projection_ready,
                "PREDICTION_LOWERING_FROZEN": lowering_ready,
            },
            "terminal_status": terminal_status,
            "claim_boundary": {
                "preflight_is_world_evidence": False,
                "preflight_mutates_knowledge_state": False,
                "missing_projection_may_be_faked": False,
                "prediction_lowering_without_projection_allowed": False,
            },
        }))

    status = (
        "LOWERING_PROJECTION_PREFLIGHT_READY_FOR_FROZEN_RUNTIME"
        if counts["ready_for_frozen_runtime"] == counts["episode_count"] and counts["episode_count"] > 0
        else "LOWERING_PROJECTION_PREFLIGHT_CLASSIFIED_EXISTING_GAPS"
    )
    return _with_digest({
        "schema": "phi-existing-lowering-projection-preflight/v1",
        "status": status,
        "campaign_digest": campaign.get("digest"),
        "frontier_ledger_sha256": campaign.get("frontier_ledger_sha256"),
        "counts": counts,
        "episodes": receipts,
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "uses_existing_owners_only": True,
            "preflight_can_replace_u4_materialization": False,
            "preflight_can_replace_response_projection": False,
            "preflight_can_replace_world_attestation": False,
        },
    })


def _route_from_preflight_status(status: str, *, active_attestors: int) -> Mapping[str, Any]:
    route_table: dict[str, Mapping[str, Any]] = {
        "BLOCKED_FRONTIER_RECORD_NOT_IN_WINDOW": {
            "current_stage": "FRONTIER_WINDOW_MISSING",
            "current_layer": "DISCOVERY_SEARCH_CORE",
            "next_required_object": "frontier_candidate_record",
            "blocked_reason": "candidate is not present in the inspected frontier window",
            "eligible_existing_modules": [
                "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl",
                "CandidateGenerationPipeline/6.27.0",
            ],
        },
        "BLOCKED_NO_CAPABLE_PROVIDER": {
            "current_stage": "MEASUREMENT_INTENT_COMPILED",
            "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
            "next_required_object": "source_capability_provider_match",
            "blocked_reason": "measurement intent has no declared capable source provider",
            "eligible_existing_modules": [
                "SourceProviderCapabilityRegistry",
                "match_source_provider",
            ],
        },
        "BLOCKED_U4_MATERIALIZATION_REQUIRED": {
            "current_stage": "PROVIDER_MATCHED",
            "current_layer": "DISCOVERY_SEARCH_CORE",
            "next_required_object": "u4_hypothesis_materialization",
            "blocked_reason": "provider-matched frontier candidate has not been materialized as a typed U4 hypothesis",
            "eligible_existing_modules": [
                "SCIENTIFIC-EXPLOITATION-ORCHESTRATOR",
                "KnowledgeEvolutionKernel.hypothesis_materializations",
                "qualify_frontier_promotion_path",
            ],
        },
        "BLOCKED_RESPONSE_OBSERVABLE_CONTRACT_REQUIRED": {
            "current_stage": "U4_READY",
            "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
            "next_required_object": "response_observable_contract",
            "blocked_reason": "typed U4 hypothesis has no declared response observable ids for frozen projection",
            "eligible_existing_modules": [
                "KnowledgeEvolutionKernel.hypothesis_materializations.measurement_contract",
                "DiscriminatingExperimentAutopilotOwner",
                "assess_phi_candidate_response_projection",
            ],
        },
        "BLOCKED_CANDIDATE_WORLD_BINDING_REQUIRED": {
            "current_stage": "RESPONSE_OBSERVABLE_CONTRACT_READY",
            "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
            "next_required_object": "candidate_world_binding",
            "blocked_reason": "response observable contract exists but candidate is not bound to a world/data contract",
            "eligible_existing_modules": [
                "KnowledgeEvolutionKernel.candidate_world_bindings",
                "assess_phi_candidate_world_binding",
                "commit_phi_candidate_world_binding",
            ],
        },
        "BLOCKED_RESPONSE_PROJECTION_FREEZE_REQUIRED": {
            "current_stage": "WORLD_BINDING_READY",
            "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
            "next_required_object": "frozen_response_projection",
            "blocked_reason": "world binding exists but response projection is not frozen",
            "eligible_existing_modules": [
                "KnowledgeEvolutionKernel.candidate_response_projections",
                "assess_phi_candidate_response_projection",
                "commit_phi_candidate_response_projection",
            ],
        },
        "BLOCKED_PREDICTION_LOWERING_REQUIRED": {
            "current_stage": "RESPONSE_PROJECTION_READY",
            "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
            "next_required_object": "prediction_lowering",
            "blocked_reason": "frozen response projection exists but candidate prediction lowering is not frozen",
            "eligible_existing_modules": [
                "SCIENTIFIC-EXPLOITATION-ORCHESTRATOR",
                "KnowledgeEvolutionKernel.candidate_prediction_lowerings",
            ],
        },
    }
    if status == "READY_FOR_FROZEN_RUNTIME_WORLD_ATTESTATION_GATE":
        if active_attestors > 0:
            return {
                "current_stage": "FROZEN_RUNTIME_READY",
                "current_layer": "EXPERIMENT_EVIDENCE_RUNTIME",
                "next_required_object": "external_artifact_acquisition",
                "blocked_reason": None,
                "eligible_existing_modules": [
                    "freeze_experiment_execution",
                    "execute_frozen_experiment",
                    "ScientificVerificationCore",
                ],
            }
        return {
            "current_stage": "FROZEN_RUNTIME_READY",
            "current_layer": "PROMOTION_TRUST_CORE",
            "next_required_object": "active_world_attestor",
            "blocked_reason": "WORLD trust registry has no active external attestor",
            "eligible_existing_modules": [
                "data/world_trust/attestors.json",
                "WorldAttestationOwner",
                "ScientificVerificationCore",
            ],
        }
    return route_table.get(status, {
        "current_stage": "UNKNOWN_ROUTE_STAGE",
        "current_layer": "DISCOVERY_SEARCH_CORE",
        "next_required_object": "route_diagnosis",
        "blocked_reason": f"unmapped preflight terminal status: {status}",
        "eligible_existing_modules": ["compile_required_evidence_routes"],
    })


def _candidate_route_policy(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = candidate.get("payload", {}) if isinstance(candidate.get("payload"), Mapping) else {}
    applicability = payload.get("applicability_contract", {}) if isinstance(payload.get("applicability_contract"), Mapping) else {}
    candidate_class = str(candidate.get("candidate_class") or payload.get("candidate_class") or "")
    axis_ids = tuple(str(x) for x in payload.get("axis_ids", ()) if str(x).strip())
    if str(applicability.get("measurement_projection_status", "")) == "REQUIRES_CANDIDATE_WORLD_BINDING_OWNER":
        selected_route = "typed_hypothesis_measurement_projection_route"
    elif "SCALAR" in candidate_class.upper():
        selected_route = "scalar_pi_route"
    elif int(payload.get("nullity", 0) or 0) > 1:
        selected_route = "multi_pi_function_form_route"
    elif axis_ids:
        selected_route = "adaptive_subspace_route"
    else:
        selected_route = "generic_frontier_route"
    return {
        "selected_route": selected_route,
        "candidate_class": candidate_class,
        "axis_count": len(axis_ids),
        "applicability_status": applicability.get("status"),
        "data_binding_ready": bool(applicability.get("data_binding_ready", False)),
        "routing_rules": {
            "p_equals_1": "scalar_pi_route",
            "p_greater_than_1": "multi_pi_function_form_route",
            "residual_present": "representation_birth_route",
            "provider_matched": "evidence_route",
            "no_active_world_attestor": "fail_closed_promotion_trust_route",
        },
    }


def compile_required_evidence_routes(
    root: str | Path | None = None,
    *,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
) -> Mapping[str, Any]:
    """Compile one read-only route graph from current candidates to evidence gates.

    The compiler is intentionally a dispatcher, not a new scientific owner.  It
    reuses the existing frontier campaign, lowering/projection preflight and
    closed-loop glue diagnostics to identify the next required object for each
    provider-matched candidate without activating every subsystem or fabricating
    missing receipts.
    """
    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("route compiler limits must be >= 1")
    campaign = run_world_closed_loop_campaign(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    preflight = run_existing_lowering_projection_preflight(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    glue = run_existing_closed_loop_glue(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    frontier = _candidate_rows_by_id(root_path, limit=int(max_frontier_rows))
    active_attestors = int(campaign.get("active_world_attestor_count", 0) or 0)
    glue_by_candidate = {
        str(row.get("candidate_id")): row
        for row in glue.get("episodes", ())
        if isinstance(row, Mapping)
    }
    routes: list[dict[str, Any]] = []
    layer_counts = {
        "DISCOVERY_SEARCH_CORE": 0,
        "EXPERIMENT_EVIDENCE_RUNTIME": 0,
        "PROMOTION_TRUST_CORE": 0,
    }
    next_object_counts: dict[str, int] = {}
    ready_for_runtime = 0
    for row in preflight.get("episodes", ()):
        if not isinstance(row, Mapping):
            continue
        cid = str(row.get("candidate_id", ""))
        terminal_status = str(row.get("terminal_status", ""))
        route_step = dict(_route_from_preflight_status(terminal_status, active_attestors=active_attestors))
        current_layer = str(route_step["current_layer"])
        layer_counts[current_layer] = layer_counts.get(current_layer, 0) + 1
        next_object = str(route_step["next_required_object"])
        next_object_counts[next_object] = next_object_counts.get(next_object, 0) + 1
        ready = terminal_status == "READY_FOR_FROZEN_RUNTIME_WORLD_ATTESTATION_GATE" and active_attestors > 0
        ready_for_runtime += int(ready)
        candidate = frontier.get(cid, {})
        routes.append(_with_digest({
            "schema": "phi-required-evidence-route/v1",
            "candidate_id": cid,
            "provider_id": row.get("provider_id"),
            "route_policy": _candidate_route_policy(candidate) if isinstance(candidate, Mapping) else {},
            "current_stage": route_step["current_stage"],
            "current_layer": current_layer,
            "next_required_object": next_object,
            "eligible_existing_modules": tuple(route_step["eligible_existing_modules"]),
            "blocked_reason": route_step["blocked_reason"],
            "preflight_terminal_status": terminal_status,
            "glue_terminal_status": glue_by_candidate.get(cid, {}).get("terminal_status"),
            "no_new_module_required": True,
            "activate_all_modules": False,
            "route_layers": {
                "A_DISCOVERY_SEARCH_CORE": {
                    "purpose": "hypothesis, coordinate, representation and U4 materialization",
                    "active_for_this_candidate": current_layer == "DISCOVERY_SEARCH_CORE",
                },
                "B_EXPERIMENT_EVIDENCE_RUNTIME": {
                    "purpose": "response observable, projection, source/provider, frozen execution and evidence acquisition",
                    "active_for_this_candidate": current_layer == "EXPERIMENT_EVIDENCE_RUNTIME",
                },
                "C_PROMOTION_TRUST_CORE": {
                    "purpose": "WORLD attestation, U5 replay, representation revision and promotion gates",
                    "active_for_this_candidate": current_layer == "PROMOTION_TRUST_CORE",
                },
            },
            "claim_boundary": {
                "route_compiler_is_scientific_owner": False,
                "route_compiler_executes_measurement": False,
                "route_compiler_mutates_knowledge_state": False,
                "route_compiler_can_skip_missing_gate": False,
            },
        }))
    status = (
        "REQUIRED_EVIDENCE_ROUTES_READY_FOR_EXTERNAL_ACQUISITION"
        if routes and ready_for_runtime == len(routes)
        else "REQUIRED_EVIDENCE_ROUTES_COMPILED_WITH_FAIL_CLOSED_NEXT_STEPS"
        if routes
        else "REQUIRED_EVIDENCE_ROUTES_BLOCKED_NO_PROVIDER_MATCHED_EPISODES"
    )
    return _with_digest({
        "schema": REQUIRED_EVIDENCE_ROUTE_SCHEMA,
        "status": status,
        "campaign_digest": campaign.get("digest"),
        "lowering_projection_preflight_digest": preflight.get("digest"),
        "glue_run_digest": glue.get("digest"),
        "frontier_ledger_sha256": campaign.get("frontier_ledger_sha256"),
        "route_count": len(routes),
        "counts": {
            "routes": len(routes),
            "ready_for_external_acquisition": ready_for_runtime,
            "by_current_layer": layer_counts,
            "by_next_required_object": dict(sorted(next_object_counts.items())),
            "provider_matched_episode_count": campaign.get("provider_matched_episode_count", 0),
            "active_world_attestor_count": active_attestors,
        },
        "routes": routes,
        "architecture_layers": [
            "DISCOVERY_SEARCH_CORE",
            "EXPERIMENT_EVIDENCE_RUNTIME",
            "PROMOTION_TRUST_CORE",
        ],
        "routing_policy": {
            "single_universal_route_graph": True,
            "new_scientific_owner_created": False,
            "use_existing_modules_before_new_code": True,
            "activate_all_modules_for_every_question": False,
            "delete_historical_tests_without_replacement": False,
        },
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "route_match_is_world_evidence": False,
            "route_compilation_changes_representation": False,
            "missing_receipts_may_be_fabricated": False,
        },
    })


_NEXT_OBJECT_TO_OBLIGATION = {
    "u4_hypothesis_materialization": "TYPED_HYPOTHESIS_MATERIALIZATION",
    "response_observable_contract": "OBSERVABLE_CONTRACT",
    "candidate_world_binding": "WORLD_BINDING",
    "frozen_response_projection": "RESPONSE_PROJECTION",
    "prediction_lowering": "PREDICTION_LOWERING",
    "source_capability_provider_match": "SOURCE_CAPABILITY",
    "external_artifact_acquisition": "EXTERNAL_ARTIFACT_ACQUISITION",
    "active_world_attestor": "WORLD_ATTESTATION",
    "frontier_candidate_record": "FRONTIER_CONTINUATION",
    "route_diagnosis": "CAPABILITY_GAP",
}


_STATUS_TO_OBLIGATION = {
    "TYPED_CROSS_DOMAIN_BRIDGE_REQUIRED": "SEMANTIC_BRIDGE_BIRTH",
    "READY_FOR_TYPED_HYPOTHESIS_MEASUREMENT_PROJECTION_REQUIRED": "TYPED_HYPOTHESIS_MATERIALIZATION",
    "OBSERVER_OR_PARAMETERIZATION_REQUIRED": "REPRESENTATION_BIRTH",
    "NO_CAPABLE_PROVIDER": "SOURCE_CAPABILITY",
    "CAPABILITY_GAP": "CAPABILITY_GAP",
}


_UNIVERSAL_CAPABILITY_REGISTRY = {
    "TYPED_HYPOTHESIS_MATERIALIZATION": {
        "capability_id": "typed-hypothesis-materialization",
        "owners": ("SCIENTIFIC-EXPLOITATION-ORCHESTRATOR", "ScientificPromotionCore", "KnowledgeEvolutionKernel"),
        "action_type": "compile_typed_hypothesis",
        "required_evidence_schema": "phi-u4-hypothesis-materialization/v1",
        "verifier": "ScientificPromotionCore.U0_U4",
        "residual_policy": "if U4 cannot bind typed quantities, emit SEMANTIC_BRIDGE_BIRTH or REPRESENTATION_BIRTH",
        "birth_path": ("representation_birth", "semantic_bridge_birth"),
        "frontier_continuation": "frontier retains candidate with explicit next obligation",
    },
    "OBSERVABLE_CONTRACT": {
        "capability_id": "claim-observable-measurement-contract",
        "owners": ("DiscriminatingExperimentAutopilotOwner", "KnowledgeEvolutionKernel"),
        "action_type": "declare_response_observable_contract",
        "required_evidence_schema": "phi-response-observable-contract/v1",
        "verifier": "ScientificVerificationCore.contract_digest_check",
        "residual_policy": "if no observable can be declared, emit REPRESENTATION_BIRTH",
        "birth_path": ("axis_birth", "observable_birth", "representation_birth"),
        "frontier_continuation": "candidate advances only after frozen observable contract exists",
    },
    "WORLD_BINDING": {
        "capability_id": "candidate-world-binding",
        "owners": ("KnowledgeEvolutionKernel",),
        "action_type": "bind_candidate_to_world_data_contract",
        "required_evidence_schema": "phi-candidate-world-binding/v1",
        "verifier": "ScientificVerificationCore.source_binding_check",
        "residual_policy": "unbound quantities return to capability/provider resolution",
        "birth_path": ("measurement_adapter_contract", "source_capability"),
        "frontier_continuation": "candidate remains pre-execution until binding is digest-bound",
    },
    "RESPONSE_PROJECTION": {
        "capability_id": "frozen-response-projection",
        "owners": ("DiscriminatingExperimentAutopilotOwner", "KnowledgeEvolutionKernel"),
        "action_type": "freeze_candidate_response_projection",
        "required_evidence_schema": "phi-candidate-response-projection/v1",
        "verifier": "ScientificVerificationCore.projection_freeze_check",
        "residual_policy": "projection residual can request observable or representation birth",
        "birth_path": ("axis_birth", "function_language_birth"),
        "frontier_continuation": "projection digest becomes input to frozen execution runtime",
    },
    "PREDICTION_LOWERING": {
        "capability_id": "prediction-lowering",
        "owners": ("SCIENTIFIC-EXPLOITATION-ORCHESTRATOR", "KnowledgeEvolutionKernel"),
        "action_type": "lower_prediction_to_frozen_response_space",
        "required_evidence_schema": "phi-candidate-prediction-lowering/v1",
        "verifier": "ScientificVerificationCore.lowering_digest_check",
        "residual_policy": "lowering residual returns to hypothesis/function representation",
        "birth_path": ("function_language_birth", "operator_birth"),
        "frontier_continuation": "lowered prediction becomes frozen evaluation input",
    },
    "SOURCE_CAPABILITY": {
        "capability_id": "source-capability-resolution",
        "owners": ("SourceProviderCapabilityRegistry",),
        "action_type": "resolve_provider_for_typed_measurement_intent",
        "required_evidence_schema": "phi-source-provider-match/v1",
        "verifier": "ScientificVerificationCore.provider_capability_check",
        "residual_policy": "unmatched intent becomes CAPABILITY_GAP rather than failed science",
        "birth_path": ("measurement_adapter_contract", "provider_registration"),
        "frontier_continuation": "candidate waits for provider or adapter without changing truth state",
    },
    "EXTERNAL_ARTIFACT_ACQUISITION": {
        "capability_id": "external-artifact-acquisition",
        "owners": ("FrozenExperimentExecution", "EvidenceAcquisitionOwner"),
        "action_type": "acquire_frozen_external_artifact",
        "required_evidence_schema": "phi-frozen-experiment-evidence/v1",
        "verifier": "ScientificVerificationCore.evidence_authenticity_check",
        "residual_policy": "artifact mismatch becomes verification residual, not refit permission",
        "birth_path": ("retry_backoff_transport", "adapter_repair"),
        "frontier_continuation": "artifact digest feeds independent verification",
    },
    "TYPED_WORLD_ACTION": {
        "capability_id": "typed-world-action",
        "owners": ("ResidentCognitiveOrganism.prepare_typed_world_action", "TypedWorldActionAdapterOwner", "FrozenExperimentExecution"),
        "action_type": "prepare_execute_and_bind_typed_world_action",
        "required_evidence_schema": "phi-typed-world-action-result/v1",
        "verifier": "TypedWorldActionAdapterOwner.bind_result",
        "residual_policy": "unresolved or OOD action result returns to learning or representation birth",
        "birth_path": ("measurement_adapter_birth", "representation_birth", "operator_birth"),
        "frontier_continuation": "bound action result becomes post-freeze evidence; no action result is scientific promotion",
    },
    "LEARNING_UPDATE": {
        "capability_id": "postfreeze-world-model-learning",
        "owners": ("ResidentCognitiveOrganism.record_world_action_experience", "ResidentCognitiveOrganism.online_update_world_action_model"),
        "action_type": "validate_record_and_update_postfreeze_world_action_model",
        "required_evidence_schema": "phi-postfreeze-resolved-world-action-experience/v1",
        "verifier": "LearnedWorldActionModelOwner.validate_experience",
        "residual_policy": "insufficient support or drift remains an explicit learning gap; pre-freeze truth leakage is rejected",
        "birth_path": ("experience_acquisition", "model_family_birth", "representation_birth"),
        "frontier_continuation": "calibrated learned likelihoods may inform EIG but never establish scientific truth",
    },
    "WORLD_ATTESTATION": {
        "capability_id": "world-attestation",
        "owners": ("WorldAttestationOwner", "ScientificVerificationCore"),
        "action_type": "verify_independent_world_signature",
        "required_evidence_schema": "phi-world-attestation/v1",
        "verifier": "external_ed25519_world_attestor",
        "residual_policy": "missing attestor is fail-closed trust residual",
        "birth_path": ("world_trust_registration",),
        "frontier_continuation": "no representation update before attested evidence",
    },
    "EVIDENCE_VERIFICATION": {
        "capability_id": "evidence-verification",
        "owners": ("ScientificVerificationCore",),
        "action_type": "verify_evidence_against_frozen_claim",
        "required_evidence_schema": "phi-scientific-evidence-verification/v1",
        "verifier": "ScientificVerificationCore",
        "residual_policy": "verification residual enters U5 replay or representation revision",
        "birth_path": ("verification_method_birth",),
        "frontier_continuation": "verified evidence becomes U5 input",
    },
    "RESIDUAL_ATTRIBUTION": {
        "capability_id": "residual-attribution",
        "owners": ("ClosedLoopResearchOwner", "AxisModelingOwner", "MathematicalInventionKernel"),
        "action_type": "attribute_residual_to_missing_object",
        "required_evidence_schema": "phi-residual-attribution/v1",
        "verifier": "heldout_residual_replay",
        "residual_policy": "residual is preserved and routed to birth or rejection",
        "birth_path": ("axis_birth", "operator_birth", "method_birth", "ontology_birth"),
        "frontier_continuation": "residual-born object re-enters frontier as candidate capability",
    },
    "REPRESENTATION_BIRTH": {
        "capability_id": "representation-birth",
        "owners": ("MathematicalInventionKernel", "AxisModelingOwner", "birth_phi_representation_language"),
        "action_type": "birth_missing_representation_or_axis",
        "required_evidence_schema": "phi-representation-birth-candidate/v1",
        "verifier": "postfreeze_holdout_and_claim_boundary",
        "residual_policy": "new representation is research-local until promoted by evidence",
        "birth_path": ("axis_birth", "function_language_birth", "operator_birth", "ontology_birth"),
        "frontier_continuation": "born representation expands capability set only after verification",
    },
    "SEMANTIC_BRIDGE_BIRTH": {
        "capability_id": "semantic-bridge-birth",
        "owners": ("discover_phi_cross_domain_bridges", "COMMON-SCIENTIFIC-RULES/1.0.0"),
        "action_type": "birth_or_qualify_typed_semantic_bridge",
        "required_evidence_schema": "phi-typed-semantic-bridge/v1",
        "verifier": "typed_dimension_role_compatibility_check",
        "residual_policy": "unbridged relation remains typed gap, not false candidate",
        "birth_path": ("semantic_bridge_birth", "ontology_birth"),
        "frontier_continuation": "bridge candidate feeds reusable cross-domain capability",
    },
    "PROOF_OBLIGATION": {
        "capability_id": "formal-proof-obligation",
        "owners": ("compile_phi_semantic_proof_obligation", "verify_phi_proof", "run_phi_lean_kernel"),
        "action_type": "compile_and_verify_formal_proof_obligation",
        "required_evidence_schema": "phi-formal-proof-obligation/v1",
        "verifier": "external_or_kernel_formal_verifier",
        "residual_policy": "failed proof obligation returns counterexample/residual region",
        "birth_path": ("proof_mechanism_birth", "counterexample_search"),
        "frontier_continuation": "verified proof evidence can feed mathematical frontier",
    },
    "FRONTIER_CONTINUATION": {
        "capability_id": "frontier-continuation",
        "owners": ("CandidateGenerationPipeline/6.27.0",),
        "action_type": "continue_frontier_after_obligation_state",
        "required_evidence_schema": "phi-frontier-continuation/v1",
        "verifier": "frontier_ledger_digest_check",
        "residual_policy": "unknown frontier state is retained as open candidate",
        "birth_path": ("frontier_expansion",),
        "frontier_continuation": "candidate remains in fair dovetail traversal",
    },
    "CAPABILITY_GAP": {
        "capability_id": "capability-gap",
        "owners": ("UniversalResearchKernel", "MathematicalInventionKernel", "AxisModelingOwner"),
        "action_type": "classify_missing_capability_for_birth",
        "required_evidence_schema": "phi-capability-gap/v1",
        "verifier": "gap_is_not_failed_science_claim_boundary",
        "residual_policy": "gap is preserved as birth input",
        "birth_path": ("representation_birth", "operator_birth", "method_birth", "measurement_adapter_birth"),
        "frontier_continuation": "capability gap becomes a research-local birth task",
    },
}


def _normalize_universal_obligation(record: Mapping[str, Any]) -> str:
    explicit = str(record.get("required_obligation") or record.get("obligation_type") or "").strip().upper()
    if explicit:
        return explicit if explicit in _UNIVERSAL_CAPABILITY_REGISTRY else "CAPABILITY_GAP"
    next_object = str(record.get("next_required_object") or record.get("missing_object") or "").strip()
    if next_object:
        return _NEXT_OBJECT_TO_OBLIGATION.get(next_object, "CAPABILITY_GAP")
    status = str(
        record.get("applicability_status")
        or record.get("status")
        or record.get("preflight_terminal_status")
        or ""
    ).strip()
    if status in _STATUS_TO_OBLIGATION:
        return _STATUS_TO_OBLIGATION[status]
    if status.startswith("BLOCKED_"):
        return _NEXT_OBJECT_TO_OBLIGATION.get(str(record.get("next_required_object", "")), "CAPABILITY_GAP")
    return "CAPABILITY_GAP"


def _universal_loop_receipt(record: Mapping[str, Any], *, source: str) -> Mapping[str, Any]:
    cid = str(record.get("candidate_id") or record.get("claim_id") or record.get("problem_id") or "UNSPECIFIED")
    obligation = _normalize_universal_obligation(record)
    capability = dict(_UNIVERSAL_CAPABILITY_REGISTRY.get(obligation, _UNIVERSAL_CAPABILITY_REGISTRY["CAPABILITY_GAP"]))
    resolved = obligation != "CAPABILITY_GAP"
    planning_raw = record.get("planning_features") if isinstance(record.get("planning_features"), Mapping) else {}
    try:
        expected_information_gain_bits = max(0.0, float(planning_raw.get("expected_information_gain_bits", 0.0) or 0.0))
    except (TypeError, ValueError):
        expected_information_gain_bits = 0.0
    try:
        residual_pressure = max(0.0, float(planning_raw.get("residual_pressure", 0.0) or 0.0))
    except (TypeError, ValueError):
        residual_pressure = 0.0
    current_layer = (
        "DISCOVERY_SEARCH_CORE"
        if obligation in {"TYPED_HYPOTHESIS_MATERIALIZATION", "SEMANTIC_BRIDGE_BIRTH", "REPRESENTATION_BIRTH", "FRONTIER_CONTINUATION", "CAPABILITY_GAP", "PROOF_OBLIGATION", "LEARNING_UPDATE"}
        else "PROMOTION_TRUST_CORE"
        if obligation in {"WORLD_ATTESTATION", "EVIDENCE_VERIFICATION", "RESIDUAL_ATTRIBUTION"}
        else "EXPERIMENT_EVIDENCE_RUNTIME"
    )
    return _with_digest({
        "schema": "phi-universal-required-evidence-obligation/v1",
        "candidate_id": cid,
        "source": source,
        "obligation_type": obligation,
        "current_layer": current_layer,
        "capability_resolution_status": "CAPABILITY_RESOLVED" if resolved else "CAPABILITY_GAP",
        "capability": capability,
        "planning": {
            "blocks_progress": bool(planning_raw.get("blocks_progress", False)),
            "expected_information_gain_bits": expected_information_gain_bits,
            "residual_pressure": residual_pressure,
            "source": str(planning_raw.get("source", "UNIVERSAL_RESEARCH_STATE")),
            "truth_probability_claimed": False,
        },
        "action": {
            "action_type": capability["action_type"],
            "executes_now": False,
            "requires_external_world": obligation in {"EXTERNAL_ARTIFACT_ACQUISITION", "WORLD_ATTESTATION"},
        },
        "evidence": {
            "required_schema": capability["required_evidence_schema"],
            "synthetic_substitution_allowed": False,
            "verification_independent_from_candidate_generator": True,
        },
        "verification": {
            "verifier": capability["verifier"],
            "same_mechanism_as_candidate_generator": False,
        },
        "residual": {
            "preserved": True,
            "policy": capability["residual_policy"],
            "birth_path": tuple(capability["birth_path"]),
        },
        "frontier_continuation": capability["frontier_continuation"],
        "domain_conditionals_used": False,
        "claim_boundary": {
            "obligation_is_domain_specific": False,
            "capability_gap_is_scientific_failure": False,
            "world_is_replaced_by_synthetic_evidence": False,
            "route_loop_is_scientific_promotion": False,
        },
    })


def compile_universal_required_evidence_loop(
    root: str | Path | None = None,
    *,
    candidate_specs: Sequence[Mapping[str, Any]] | None = None,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
) -> Mapping[str, Any]:
    """Compile the universal research loop from obligations to reusable capabilities.

    This read-only loop is deliberately not a workflow engine and contains no
    domain-specific branches.  It resolves typed obligations against the current
    Atlas capability/owner registry, preserves gaps as birth tasks, and routes
    residuals back into discovery/frontier continuation.
    """
    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("universal loop limits must be >= 1")
    if candidate_specs is None:
        route_report = compile_required_evidence_routes(
            root_path,
            max_frontier_rows=int(max_frontier_rows),
            max_campaign_items=int(max_campaign_items),
        )
        input_records = tuple(route_report.get("routes", ()))
        input_digest = route_report.get("digest")
        input_source = "required_evidence_routes"
    else:
        input_records = tuple(row for row in candidate_specs if isinstance(row, Mapping))
        input_digest = digest_payload(input_records)
        input_source = "explicit_candidate_specs"

    obligations = [
        _universal_loop_receipt(row, source=input_source)
        for row in input_records
    ]
    by_obligation: dict[str, int] = {}
    by_layer: dict[str, int] = {
        "DISCOVERY_SEARCH_CORE": 0,
        "EXPERIMENT_EVIDENCE_RUNTIME": 0,
        "PROMOTION_TRUST_CORE": 0,
    }
    gaps = 0
    for row in obligations:
        obligation = str(row["obligation_type"])
        by_obligation[obligation] = by_obligation.get(obligation, 0) + 1
        layer = str(row["current_layer"])
        by_layer[layer] = by_layer.get(layer, 0) + 1
        gaps += int(row["capability_resolution_status"] == "CAPABILITY_GAP")

    return _with_digest({
        "schema": UNIVERSAL_REQUIRED_EVIDENCE_LOOP_SCHEMA,
        "status": (
            "UNIVERSAL_REQUIRED_EVIDENCE_LOOP_HAS_CAPABILITY_GAPS"
            if gaps
            else "UNIVERSAL_REQUIRED_EVIDENCE_LOOP_COMPILED"
        ),
        "input_source": input_source,
        "input_digest": input_digest,
        "obligation_count": len(obligations),
        "capability_gap_count": gaps,
        "counts": {
            "by_obligation_type": dict(sorted(by_obligation.items())),
            "by_layer": by_layer,
        },
        "loop": [
            "QUESTION",
            "FRONTIER",
            "REQUIRED_EVIDENCE_ROUTE",
            "OBLIGATION",
            "RESOLVE_CAPABILITY",
            "MIND_PLAN",
            "ACTION_OR_GAP",
            "WORLD_OR_PROOF_OR_COMPUTATION",
            "EVIDENCE",
            "LEARNING_UPDATE",
            "INDEPENDENT_VERIFICATION",
            "RESIDUAL_ATTRIBUTION",
            "REVISION_OR_BIRTH",
            "FRONTIER_CONTINUATION",
        ],
        "obligations": obligations,
        "capability_registry_digest": digest_payload(_UNIVERSAL_CAPABILITY_REGISTRY),
        "routing_policy": {
            "route_determined_by_scientific_obligation_not_domain": True,
            "domain_specific_if_branches_allowed": False,
            "domain_adapters_only_describe_quantities_actions_evidence": True,
            "capability_gap_becomes_birth_input": True,
            "residual_returns_to_discovery": True,
            "verified_new_capabilities_become_cross_domain_memory": True,
            "mind_plans_from_typed_obligations_not_domain_names": True,
            "learning_requires_postfreeze_resolved_experience": True,
            "learned_likelihoods_may_rank_actions_but_never_establish_truth": True,
            "representation_birth_remains_research_local_until_verified": True,
        },
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "universal_loop_is_workflow_engine": False,
            "universal_loop_replaces_scientific_owners": False,
            "provider_match_is_world_evidence": False,
            "synthetic_evidence_can_replace_world": False,
        },
    })


def execute_universal_obligation_step(
    root: str | Path | None = None,
    *,
    obligation_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Execute one safe, typed obligation step through an existing owner boundary.

    The step is intentionally single-obligation and fail-closed.  It may compile
    an owner input contract or run a read-only verifier/compiler where all inputs
    are present.  It never fetches external data, never stores WORLD signatures,
    and never grants scientific promotion.
    """
    root_path = _root(root)
    source = str(obligation_record.get("source", "explicit_obligation_execution"))
    obligation = (
        dict(obligation_record)
        if obligation_record.get("schema") == "phi-universal-required-evidence-obligation/v1"
        else dict(_universal_loop_receipt(obligation_record, source=source))
    )
    capability = dict(obligation.get("capability") or {})
    obligation_type = str(obligation.get("obligation_type", "CAPABILITY_GAP"))
    candidate_id = str(obligation.get("candidate_id", "UNSPECIFIED"))
    owners = [str(x) for x in capability.get("owners", ()) if str(x)]
    selected_owner = owners[0] if owners else "UniversalResearchKernel"
    input_state_digest = _representation_world_state(root_path)["digest"]
    owner_input_contract = {
        "candidate_id": candidate_id,
        "obligation_type": obligation_type,
        "capability_id": capability.get("capability_id", "capability-gap"),
        "required_evidence_schema": capability.get("required_evidence_schema"),
        "action_type": capability.get("action_type"),
        "source_obligation_digest": obligation.get("digest"),
    }
    produced_object: Mapping[str, Any]
    execution_status = "OWNER_INPUT_CONTRACT_COMPILED_FAIL_CLOSED"
    verification_status = "VERIFICATION_PENDING_REQUIRED_EVIDENCE"
    next_obligation = "EVIDENCE_VERIFICATION"
    state_transition_allowed = False
    residual = {
        "present": True,
        "kind": "REQUIRED_EVIDENCE_PENDING",
        "policy": capability.get("residual_policy", "preserve residual for next obligation"),
    }

    if obligation_type == "CAPABILITY_GAP":
        execution_status = "CAPABILITY_GAP_PRESERVED_FOR_BIRTH"
        verification_status = "GAP_CLASSIFIED_NOT_SCIENTIFIC_FAILURE"
        produced_object = {
            "schema": "phi-capability-gap/v1",
            "candidate_id": candidate_id,
            "birth_path": list(capability.get("birth_path", ())),
            "research_local": True,
        }
        next_obligation = "REPRESENTATION_BIRTH"
    elif obligation_type in {"EXTERNAL_ARTIFACT_ACQUISITION", "WORLD_ATTESTATION", "TYPED_WORLD_ACTION"}:
        execution_status = "BLOCKED_AT_EXTERNAL_OR_AUTHORIZED_ACTION_BOUNDARY"
        verification_status = "EXTERNAL_EVIDENCE_OR_AUTHORIZATION_REQUIRED"
        produced_object = {
            "schema": capability.get("required_evidence_schema"),
            "candidate_id": candidate_id,
            "prepared_boundary": True,
            "external_data_fetched": False,
            "authorization_or_attestation_required": True,
        }
        next_obligation = "WORLD_ATTESTATION" if obligation_type != "WORLD_ATTESTATION" else "EVIDENCE_VERIFICATION"
    elif obligation_type == "SOURCE_CAPABILITY":
        intent = obligation_record.get("measurement_intent") if isinstance(obligation_record.get("measurement_intent"), Mapping) else None
        intent = intent or obligation_record.get("intent") if isinstance(obligation_record.get("intent"), Mapping) else intent
        if intent:
            produced_object = match_source_provider(intent, root_path)
            execution_status = "SOURCE_CAPABILITY_MATCH_EXECUTED"
            verification_status = "PROVIDER_CAPABILITY_RESOLVED" if produced_object.get("status") == "CAPABLE_PROVIDER_SELECTED" else "NO_CAPABLE_PROVIDER"
            next_obligation = "EXTERNAL_ARTIFACT_ACQUISITION" if produced_object.get("status") == "CAPABLE_PROVIDER_SELECTED" else "CAPABILITY_GAP"
        else:
            execution_status = "SOURCE_CAPABILITY_BLOCKED_MEASUREMENT_INTENT_REQUIRED"
            verification_status = "MISSING_TYPED_MEASUREMENT_INTENT"
            produced_object = {"schema": "phi-source-provider-match/v1", "status": "MEASUREMENT_INTENT_REQUIRED"}
            next_obligation = "OBSERVABLE_CONTRACT"
    elif obligation_type == "PROOF_OBLIGATION":
        from .mathematical_invention import MathematicalInventionKernel

        semantic_claim = (
            obligation_record.get("semantic_claim")
            or obligation_record.get("statement")
            or obligation_record.get("claim")
            or f"Resolve proof obligation for {candidate_id}"
        )
        compiler = MathematicalInventionKernel(root_path).semantic_obligation_compiler
        produced_object = compiler.compile(
            obligation={
                "obligation_id": "OBL-" + digest_payload(obligation)[:20].upper(),
                "semantic_claim": semantic_claim,
            },
            candidate={"candidate_id": candidate_id, "semantic_context": obligation_record.get("semantic_context", {})},
        )
        execution_status = "PROOF_OBLIGATION_COMPILED_BY_EXISTING_FORMAL_OWNER"
        verification_status = (
            "EXECUTABLE_PROOF_SPEC_AVAILABLE"
            if produced_object.get("executable_verification")
            else "PROOF_OBLIGATION_REQUIRES_BINDINGS_OR_EXTERNAL_PROOF"
        )
        next_obligation = "EVIDENCE_VERIFICATION" if produced_object.get("executable_verification") else "CAPABILITY_GAP"
    elif obligation_type == "LEARNING_UPDATE":
        experience = obligation_record.get("world_action_experience")
        if isinstance(experience, Mapping):
            from .resident_cognitive import LearnedWorldActionModelOwner

            produced_object = LearnedWorldActionModelOwner().validate_experience(experience)
            execution_status = "POSTFREEZE_EXPERIENCE_VALIDATED_READ_ONLY"
            verification_status = str(produced_object.get("status", "EXPERIENCE_VALIDATION_RESULT"))
            next_obligation = "FRONTIER_CONTINUATION" if produced_object.get("status") == "WORLD_ACTION_EXPERIENCE_ADMITTED" else "LEARNING_UPDATE"
        else:
            execution_status = "LEARNING_UPDATE_BLOCKED_EXPERIENCE_REQUIRED"
            verification_status = "NO_POSTFREEZE_RESOLVED_EXPERIENCE"
            produced_object = {"schema": "phi-postfreeze-resolved-world-action-experience/v1", "status": "EXPERIENCE_REQUIRED"}
            next_obligation = "LEARNING_UPDATE"
    else:
        produced_object = {
            "schema": capability.get("required_evidence_schema"),
            "candidate_id": candidate_id,
            "owner_input_contract": owner_input_contract,
            "research_local": obligation_type in {"REPRESENTATION_BIRTH", "SEMANTIC_BRIDGE_BIRTH"},
        }
        if obligation_type in {"REPRESENTATION_BIRTH", "SEMANTIC_BRIDGE_BIRTH"}:
            execution_status = "RESEARCH_LOCAL_BIRTH_INPUT_PREPARED"
            verification_status = "POSTFREEZE_VALIDATION_REQUIRED_BEFORE_REUSE"
            next_obligation = "EVIDENCE_VERIFICATION"

    produced_object_digest = digest_payload(produced_object)
    receipt = {
        "schema": UNIVERSAL_OBLIGATION_EXECUTION_SCHEMA,
        "obligation_id": "OBL-" + digest_payload(obligation)[:20].upper(),
        "candidate_id": candidate_id,
        "input_state_digest": input_state_digest,
        "capability_id": capability.get("capability_id", "capability-gap"),
        "selected_owner": selected_owner,
        "owner_input_contract": owner_input_contract,
        "execution_status": execution_status,
        "produced_object": produced_object,
        "produced_object_digest": produced_object_digest,
        "verification_status": verification_status,
        "residual": residual,
        "next_obligation": next_obligation,
        "state_transition_allowed": state_transition_allowed,
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "one_step_executes_more_than_next_obligation": False,
            "missing_owner_or_input_means_false_hypothesis": False,
            "world_boundary_is_crossed_without_attestation": False,
            "research_local_birth_is_canonical": False,
        },
    }
    return _with_digest(receipt)


def run_universal_obligation_execution_loop(
    root: str | Path | None = None,
    *,
    candidate_specs: Sequence[Mapping[str, Any]] | None = None,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
    max_execution_steps: int | None = None,
) -> Mapping[str, Any]:
    """Compile the universal loop and execute exactly one safe step per item."""
    compiled = compile_universal_required_evidence_loop(
        root,
        candidate_specs=candidate_specs,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )
    obligations = list(compiled.get("obligations", ()))
    limit = len(obligations) if max_execution_steps is None else max(0, int(max_execution_steps))
    steps = [
        execute_universal_obligation_step(root, obligation_record=row)
        for row in obligations[:limit]
        if isinstance(row, Mapping)
    ]
    blocked = [row for row in steps if str(row.get("execution_status", "")).startswith("BLOCKED") or "REQUIRED" in str(row.get("verification_status", ""))]
    return _with_digest({
        "schema": "phi-universal-obligation-execution-loop/v1",
        "status": "UNIVERSAL_OBLIGATION_EXECUTION_STEPPED_FAIL_CLOSED",
        "compiled_loop_digest": compiled.get("digest"),
        "step_count": len(steps),
        "blocked_or_pending_count": len(blocked),
        "steps": steps,
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "execution_loop_is_scientific_promotion": False,
            "external_world_substituted_by_local_receipt": False,
            "capability_gap_is_failed_science": False,
        },
    })


def _metabolism_growth_vector(compiled: Mapping[str, Any], execution: Mapping[str, Any]) -> Mapping[str, Any]:
    obligations = [row for row in compiled.get("obligations", ()) if isinstance(row, Mapping)]
    steps = [row for row in execution.get("steps", ()) if isinstance(row, Mapping)]
    by_type = dict(compiled.get("counts", {}).get("by_obligation_type", {}) or {})
    by_layer = dict(compiled.get("counts", {}).get("by_layer", {}) or {})
    next_obligations: dict[str, int] = {}
    residual_kinds: dict[str, int] = {}
    for row in steps:
        nxt = str(row.get("next_obligation", "UNSPECIFIED"))
        next_obligations[nxt] = next_obligations.get(nxt, 0) + 1
        residual = row.get("residual") if isinstance(row.get("residual"), Mapping) else {}
        kind = str(residual.get("kind", "UNSPECIFIED"))
        residual_kinds[kind] = residual_kinds.get(kind, 0) + 1

    missing = []
    if by_type.get("TYPED_HYPOTHESIS_MATERIALIZATION", 0):
        missing.append({
            "missing_object": "typed_u4_hypothesis_materialization",
            "count": by_type.get("TYPED_HYPOTHESIS_MATERIALIZATION", 0),
            "growth_axis": "semantic_binding_and_u4_materialization",
        })
    if by_type.get("OBSERVABLE_CONTRACT", 0):
        missing.append({
            "missing_object": "response_observable_contract",
            "count": by_type.get("OBSERVABLE_CONTRACT", 0),
            "growth_axis": "measurement_semantics_and_response_projection",
        })
    if by_type.get("WORLD_ATTESTATION", 0) or next_obligations.get("WORLD_ATTESTATION", 0):
        missing.append({
            "missing_object": "independent_world_attestation",
            "count": by_type.get("WORLD_ATTESTATION", 0) + next_obligations.get("WORLD_ATTESTATION", 0),
            "growth_axis": "world_trust",
        })
    if compiled.get("capability_gap_count", 0):
        missing.append({
            "missing_object": "new_capability_or_adapter",
            "count": compiled.get("capability_gap_count", 0),
            "growth_axis": "capability_birth",
        })

    if not missing and obligations:
        missing.append({
            "missing_object": "external_evidence_or_verification",
            "count": len(obligations),
            "growth_axis": "evidence_execution",
        })

    return {
        "schema": "phi-epistemic-growth-vector/v1",
        "obligation_distribution": by_type,
        "layer_distribution": by_layer,
        "next_obligation_distribution": dict(sorted(next_obligations.items())),
        "residual_distribution": dict(sorted(residual_kinds.items())),
        "missing_objects": missing,
        "recommended_next_growth_order": [
            row["growth_axis"] for row in missing
        ],
    }


def run_epistemic_metabolism_cycle(
    root: str | Path | None = None,
    *,
    candidate_specs: Sequence[Mapping[str, Any]] | None = None,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
    max_execution_steps: int | None = None,
) -> Mapping[str, Any]:
    """Run a read-only Atlas self-gap metabolism cycle.

    The cycle is the concrete form of the research-organism idea: it ingests the
    current frontier or explicit candidate specs, compiles typed obligations,
    resolves each obligation through existing owners, executes at most one safe
    step, preserves residuals, and returns the next growth vector.  It does not
    create a new scientific owner, fetch external data, mutate knowledge state,
    or grant promotion.
    """
    compiled = compile_universal_required_evidence_loop(
        root,
        candidate_specs=candidate_specs,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )
    execution = run_universal_obligation_execution_loop(
        root,
        candidate_specs=candidate_specs,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
        max_execution_steps=max_execution_steps,
    )
    growth = _metabolism_growth_vector(compiled, execution)
    status = (
        "EPISTEMIC_METABOLISM_CYCLE_PRESERVED_RESIDUALS_FAIL_CLOSED"
        if execution.get("blocked_or_pending_count", 0)
        else "EPISTEMIC_METABOLISM_CYCLE_READY_FOR_NEXT_EVIDENCE"
    )
    return _with_digest({
        "schema": EPISTEMIC_METABOLISM_SCHEMA,
        "status": status,
        "definition": "unknown_to_typed_obligation_to_existing_owner_step_to_residual_to_next_growth",
        "cycle": [
            "UNKNOWN_OR_FRONTIER_CANDIDATE",
            "TYPED_GAP",
            "RESEARCH_OBLIGATION",
            "EXISTING_OWNER_ROUTE",
            "SAFE_ONE_STEP_EXECUTION",
            "RESIDUAL_CLASSIFICATION",
            "NEXT_GROWTH_VECTOR",
            "FRONTIER_CONTINUATION",
        ],
        "compiled_loop_digest": compiled.get("digest"),
        "execution_loop_digest": execution.get("digest"),
        "obligation_count": compiled.get("obligation_count", 0),
        "executed_step_count": execution.get("step_count", 0),
        "blocked_or_pending_count": execution.get("blocked_or_pending_count", 0),
        "capability_gap_count": compiled.get("capability_gap_count", 0),
        "growth_vector": growth,
        "compiled_loop": compiled,
        "execution_loop": execution,
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "new_scientific_owner_created": False,
        "claim_boundary": {
            "metabolism_cycle_is_agi_claim": False,
            "metabolism_cycle_is_scientific_promotion": False,
            "residual_is_failure": False,
            "missing_world_evidence_can_be_fabricated": False,
            "new_representation_is_canonical_without_evidence": False,
            "all_modules_must_activate_for_every_problem": False,
        },
    })


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _safe_ratio(numerator: float, denominator: float, *, empty: float = 0.0) -> float:
    if float(denominator) == 0.0:
        return float(empty)
    return _clamp01(float(numerator) / float(denominator))


def _harmonic_mean(values: Sequence[float], *, epsilon: float = 1e-9) -> float:
    vals = [max(float(epsilon), _clamp01(v)) for v in values]
    if not vals:
        return 0.0
    return _clamp01(len(vals) / sum(1.0 / v for v in vals))


def search_ideal_ai_formula_candidates(
    root: str | Path | None = None,
    *,
    candidate_specs: Sequence[Mapping[str, Any]] | None = None,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
    max_execution_steps: int | None = None,
) -> Mapping[str, Any]:
    """Search and compare candidate formulae for an ideal scientific AI.

    The formulae are architecture metrics, not claims of AGI or natural law.
    They are derived from Atlas' own multidimensional state: frontier
    obligationization, safe owner routing, residual preservation, evidence
    closure, world trust and promotion discipline.
    """
    root_path = _root(root)
    metabolism = run_epistemic_metabolism_cycle(
        root_path,
        candidate_specs=candidate_specs,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
        max_execution_steps=max_execution_steps,
    )
    compiled = metabolism.get("compiled_loop", {}) if isinstance(metabolism.get("compiled_loop"), Mapping) else {}
    execution = metabolism.get("execution_loop", {}) if isinstance(metabolism.get("execution_loop"), Mapping) else {}
    growth = metabolism.get("growth_vector", {}) if isinstance(metabolism.get("growth_vector"), Mapping) else {}
    obligations = float(metabolism.get("obligation_count", 0) or 0)
    steps = float(metabolism.get("executed_step_count", 0) or 0)
    blocked = float(metabolism.get("blocked_or_pending_count", 0) or 0)
    gaps = float(metabolism.get("capability_gap_count", 0) or 0)
    trust = load_world_trust_registry(root_path)
    active_attestors = [
        row for row in trust.get("attestors", ())
        if isinstance(row, Mapping) and str(row.get("status", "ACTIVE")).upper() == "ACTIVE"
    ]
    by_obligation = dict(growth.get("obligation_distribution", {}) or {})
    typed_missing = float(by_obligation.get("TYPED_HYPOTHESIS_MATERIALIZATION", 0) or 0)
    observable_missing = float(by_obligation.get("OBSERVABLE_CONTRACT", 0) or 0)
    world_missing = 1.0 if len(active_attestors) == 0 else 0.0

    axes = {
        "O_obligationization": _safe_ratio(obligations, max(obligations, 1.0), empty=0.0),
        "C_capability_resolution": _safe_ratio(obligations - gaps, obligations, empty=1.0),
        "X_safe_owner_step": _safe_ratio(steps, obligations, empty=0.0),
        "R_residual_preservation": _safe_ratio(blocked, steps, empty=1.0),
        "V_evidence_closure": _safe_ratio(steps - blocked, steps, empty=0.0),
        "T_world_trust": 1.0 if active_attestors else 0.0,
        "B_semantic_binding": _safe_ratio(obligations - typed_missing, obligations, empty=1.0),
        "Q_response_projection": _safe_ratio(obligations - observable_missing, obligations, empty=1.0),
        "P_promotion_discipline": 1.0 if metabolism.get("scientific_promotion_allowed") is False and metabolism.get("knowledge_state_mutated") is False else 0.0,
        "M_lineage_memory": 1.0 if metabolism.get("digest") and compiled.get("digest") and execution.get("digest") else 0.0,
    }
    closure_axes = [
        axes["B_semantic_binding"],
        axes["Q_response_projection"],
        axes["V_evidence_closure"],
        axes["T_world_trust"],
    ]
    safety_axes = [
        axes["O_obligationization"],
        axes["C_capability_resolution"],
        axes["X_safe_owner_step"],
        axes["R_residual_preservation"],
        axes["P_promotion_discipline"],
        axes["M_lineage_memory"],
    ]
    arithmetic = sum(axes.values()) / len(axes)
    product = 1.0
    for value in axes.values():
        product *= value
    strict_gate = min(axes["V_evidence_closure"], axes["T_world_trust"]) * _harmonic_mean(safety_axes)
    metabolism_formula = (
        _harmonic_mean(safety_axes)
        * (0.35 * axes["B_semantic_binding"] + 0.25 * axes["Q_response_projection"] + 0.20 * axes["C_capability_resolution"] + 0.20 * axes["R_residual_preservation"])
        * (1.0 / (1.0 + world_missing + _safe_ratio(typed_missing + observable_missing, obligations, empty=0.0)))
    )
    frontier_pressure_formula = (
        _harmonic_mean([axes["O_obligationization"], axes["R_residual_preservation"], axes["P_promotion_discipline"], axes["M_lineage_memory"]])
        * (1.0 - _harmonic_mean(closure_axes))
    )
    candidates = [
        {
            "formula_id": "F1_STRICT_TRUTH_PRODUCT",
            "formula_role": "strict_truth_gate",
            "expression": "Π(O,C,X,R,V,T,B,Q,P,M)",
            "meaning": "ideal only when every discovery, evidence, trust and promotion axis is closed",
            "current_score": _clamp01(product),
            "selection_score": _clamp01(product + 0.10),
            "strength": "maximally conservative truth gate",
            "weakness": "collapses to zero while world trust or evidence closure is missing",
        },
        {
            "formula_id": "F2_WORLD_TRUST_GATE",
            "formula_role": "strict_world_evidence_gate",
            "expression": "min(V,T) · harmonic(O,C,X,R,P,M)",
            "meaning": "scientific AI is ideal only after verified world evidence and active trust",
            "current_score": _clamp01(strict_gate),
            "selection_score": _clamp01(strict_gate + 0.20),
            "strength": "excellent false-promotion firewall",
            "weakness": "does not measure productive growth before first attested world contact",
        },
        {
            "formula_id": "F3_EPISTEMIC_METABOLISM",
            "formula_role": "ideal_architecture_metric",
            "expression": "H(O,C,X,R,P,M) · (0.35B+0.25Q+0.20C+0.20R) / (1 + W_missing + G_required)",
            "meaning": "ideal scientific AI converts unknowns into typed obligations, executes safe owner steps, preserves residuals and lowers remaining growth debt",
            "current_score": _clamp01(metabolism_formula),
            "selection_score": _clamp01(metabolism_formula + 0.55),
            "strength": "scores both productive ignorance processing and fail-closed discipline",
            "weakness": "is an architectural research metric, not a proof of intelligence",
        },
        {
            "formula_id": "F4_FRONTIER_PRESSURE",
            "formula_role": "planner_pressure_signal",
            "expression": "H(O,R,P,M) · (1 - H(B,Q,V,T))",
            "meaning": "measures how much unresolved scientific pressure remains available for the next growth cycle",
            "current_score": _clamp01(frontier_pressure_formula),
            "selection_score": _clamp01(frontier_pressure_formula + 0.35),
            "strength": "good planner signal for what to work on next",
            "weakness": "high score can mean incompleteness, not ideality",
        },
        {
            "formula_id": "F5_BALANCED_ORGANISM_MEAN",
            "formula_role": "baseline_diagnostic",
            "expression": "mean(O,C,X,R,V,T,B,Q,P,M)",
            "meaning": "simple average of organism axes",
            "current_score": _clamp01(arithmetic),
            "selection_score": _clamp01(arithmetic + 0.05),
            "strength": "easy to read and compare",
            "weakness": "can hide fatal bottlenecks such as missing WORLD trust",
        },
    ]
    candidates = sorted(candidates, key=lambda row: (float(row["selection_score"]), float(row["current_score"]), str(row["formula_id"])), reverse=True)
    selected_pool = [row for row in candidates if row.get("formula_role") == "ideal_architecture_metric"]
    selected = dict(selected_pool[0] if selected_pool else candidates[0]) if candidates else {}
    missing = list(growth.get("missing_objects", ()) or ())
    if world_missing:
        missing.append({"missing_object": "active_world_attestor", "growth_axis": "world_trust", "count": 1})
    return _with_digest({
        "schema": IDEAL_AI_FORMULA_SEARCH_SCHEMA,
        "status": "IDEAL_AI_FORMULA_CANDIDATES_COMPARED",
        "owner": "ATLAS-EPISTEMIC-METABOLISM-FORMULA-SEARCH/1.0.0",
        "selected_formula_id": selected.get("formula_id"),
        "selected_formula": selected,
        "selection_policy": {
            "primary_role": "ideal_architecture_metric",
            "planner_pressure_signal_is_not_selected_as_ideal_formula": True,
            "baseline_mean_is_not_selected_when_it_hides_world_trust_gap": True,
            "strict_truth_gate_is_retained_as_negative_control": True,
        },
        "formula_candidates": candidates,
        "parameters": axes,
        "missing_growth_objects": missing,
        "metabolism_digest": metabolism.get("digest"),
        "world_trust_registry_digest": trust.get("digest"),
        "active_world_attestor_count": len(active_attestors),
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "formula_is_agi_proof": False,
            "formula_is_scientific_law": False,
            "formula_can_replace_world_evidence": False,
            "formula_can_promote_candidate": False,
            "new_metric_is_research_local_until_validated": True,
        },
    })


def run_existing_closed_loop_glue(
    root: str | Path | None = None,
    *,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
) -> Mapping[str, Any]:
    """Execute the internal glue path across already-existing Atlas systems.

    This runner does not create a new scientific owner and does not acquire
    external data.  It binds the frontier/provider campaign to the existing
    frozen-experiment runtime as an explicit stage in the route, then stops
    per candidate at the first missing precondition.
    """
    from .experiment_execution import SCHEMA as EXPERIMENT_EXECUTION_SCHEMA, STAGES as EXPERIMENT_EXECUTION_STAGES
    from .knowledge_evolution import KnowledgeEvolutionKernel

    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("glue limits must be >= 1")
    state = KnowledgeEvolutionKernel(root_path).state()
    campaign = run_world_closed_loop_campaign(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    preflight = run_existing_lowering_projection_preflight(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    preflight_by_candidate = {
        str(row.get("candidate_id")): row
        for row in preflight.get("episodes", ())
        if isinstance(row, Mapping)
    }
    frontier_ids = {
        str(row.get("candidate_id"))
        for row in _frontier_rows(root_path, limit=int(max_frontier_rows))
        if str(row.get("candidate_id", "")).strip()
    }
    materialized_ids = _candidate_ids(state, "hypothesis_materializations")
    lowering_ids = _candidate_ids(state, "candidate_prediction_lowerings")
    projection_ids = _candidate_ids(state, "candidate_response_projections")
    measurement_ids = _candidate_ids(state, "candidate_measurement_executions")
    discrimination_ids = _candidate_ids(state, "candidate_prediction_discriminations")
    active_attestors = int(campaign.get("active_world_attestor_count", 0) or 0)

    receipts: list[dict[str, Any]] = []
    counts = {
        "frontier_ready": 0,
        "u4_materialized": 0,
        "prediction_lowering_ready": 0,
        "response_projection_ready": 0,
        "measurement_execution_seen": 0,
        "prediction_discrimination_seen": 0,
        "provider_matched": 0,
        "bound_to_frozen_execution_runtime": 0,
        "ready_for_external_acquisition": 0,
        "blocked_u4_materialization_required": 0,
        "blocked_prediction_lowering_required": 0,
        "blocked_response_projection_required": 0,
        "blocked_world_attestor_required": 0,
        "blocked_world_evidence_required": 0,
    }

    for episode in campaign.get("episodes", ()):
        if not isinstance(episode, Mapping):
            continue
        cid = str(episode.get("candidate_id", ""))
        preflight_episode = dict(preflight_by_candidate.get(cid, {}))
        stages: list[dict[str, Any]] = []

        frontier_ready = cid in frontier_ids
        counts["frontier_ready"] += int(frontier_ready)
        stages.append({"stage": "FRONTIER", "status": "READY" if frontier_ready else "BLOCKED_FRONTIER_RECORD_NOT_IN_WINDOW"})

        u4_ready = cid in materialized_ids
        counts["u4_materialized"] += int(u4_ready)
        if not u4_ready:
            counts["blocked_u4_materialization_required"] += 1
        stages.append({"stage": "U4_MATERIALIZATION", "status": "READY" if u4_ready else "BLOCKED_U4_MATERIALIZATION_REQUIRED"})

        lowering_ready = cid in lowering_ids
        counts["prediction_lowering_ready"] += int(lowering_ready)
        projection_ready = cid in projection_ids
        if projection_ready and not lowering_ready:
            counts["blocked_prediction_lowering_required"] += 1
        stages.append({
            "stage": "PREDICTION_LOWERING",
            "status": (
                "READY" if lowering_ready
                else "BLOCKED_PREDICTION_LOWERING_REQUIRED" if projection_ready
                else "WAITING_FOR_RESPONSE_PROJECTION" if u4_ready
                else "WAITING_FOR_U4_MATERIALIZATION"
            ),
        })

        counts["response_projection_ready"] += int(projection_ready)
        if lowering_ready and not projection_ready:
            counts["blocked_response_projection_required"] += 1
        elif u4_ready and not projection_ready:
            counts["blocked_response_projection_required"] += 1
        response_projection_block = (
            "BLOCKED_RESPONSE_OBSERVABLE_CONTRACT_REQUIRED"
            if str(preflight_episode.get("terminal_status", "")) == "BLOCKED_RESPONSE_OBSERVABLE_CONTRACT_REQUIRED"
            else "BLOCKED_RESPONSE_PROJECTION_REQUIRED"
        )
        stages.append({
            "stage": "RESPONSE_PROJECTION",
            "status": "READY" if projection_ready else (response_projection_block if u4_ready else "WAITING_FOR_U4_MATERIALIZATION"),
            "lowering_projection_preflight_status": preflight_episode.get("terminal_status"),
        })

        provider_ready = bool(episode.get("provider_id"))
        counts["provider_matched"] += int(provider_ready)
        stages.append({
            "stage": "PROVIDER_MATCHING",
            "status": "READY" if provider_ready else "BLOCKED_NO_CAPABLE_PROVIDER",
            "provider_id": episode.get("provider_id"),
            "source_class": episode.get("source_class"),
        })

        runtime_bound = provider_ready
        counts["bound_to_frozen_execution_runtime"] += int(runtime_bound)
        frozen_block = (
            "BLOCKED_U4_MATERIALIZATION_REQUIRED"
            if str(preflight_episode.get("terminal_status", "")) == "BLOCKED_U4_MATERIALIZATION_REQUIRED"
            else response_projection_block
        )
        frozen_status = (
            "READY_FOR_FROZEN_PROTOCOL_COMPILATION"
            if projection_ready and provider_ready
            else frozen_block
            if provider_ready
            else "BLOCKED_PROVIDER_REQUIRED"
        )
        stages.append({
            "stage": "FROZEN_EXECUTION_RUNTIME",
            "status": frozen_status,
            "runtime_schema": EXPERIMENT_EXECUTION_SCHEMA,
            "runtime_stages": list(EXPERIMENT_EXECUTION_STAGES),
            "runtime_bound_to_frontier_provider_route": runtime_bound,
        })

        measurement_seen = cid in measurement_ids
        discrimination_seen = cid in discrimination_ids
        counts["measurement_execution_seen"] += int(measurement_seen)
        counts["prediction_discrimination_seen"] += int(discrimination_seen)
        stages.append({
            "stage": "EXISTING_MEASUREMENT_MEMORY",
            "status": "FOUND_PRIOR_MEASUREMENT_EXECUTION" if measurement_seen else "NO_PRIOR_MEASUREMENT_EXECUTION_FOR_THIS_CANDIDATE",
        })

        if projection_ready and provider_ready and active_attestors > 0:
            world_status = "READY_FOR_EXTERNAL_ACQUISITION_AND_WORLD_ATTESTATION"
            counts["ready_for_external_acquisition"] += 1
        elif active_attestors == 0:
            world_status = "BLOCKED_NO_ACTIVE_EXTERNAL_ATTESTOR"
            counts["blocked_world_attestor_required"] += 1
        else:
            world_status = "BLOCKED_FROZEN_EXECUTION_PRECONDITION_REQUIRED"
        stages.append({"stage": "WORLD_ATTESTATION", "status": world_status, "active_world_attestor_count": active_attestors})

        counts["blocked_world_evidence_required"] += 1
        stages.append({
            "stage": "U5_REPLAY",
            "status": "BLOCKED_WORLD_EVIDENCE_REQUIRED",
            "u5_replay_owner": "U5-ATTEMPT-SCHEDULER/1.2.0",
        })

        terminal = next((row["status"] for row in stages if str(row["status"]).startswith("BLOCKED_")), "READY_FOR_EXTERNAL_ACQUISITION")
        receipts.append(_with_digest({
            "schema": "phi-existing-closed-loop-glue-episode/v1",
            "candidate_id": cid,
            "provider_id": episode.get("provider_id"),
            "terminal_status": terminal,
            "lowering_projection_preflight_digest": preflight_episode.get("digest"),
            "stages": stages,
            "external_data_fetched": False,
            "knowledge_state_mutated": False,
            "scientific_promotion_allowed": False,
        }))

    status = (
        "EXISTING_GLUE_EXECUTED_TO_WORLD_BOUNDARY"
        if counts["ready_for_external_acquisition"] > 0
        else "EXISTING_GLUE_EXECUTED_FAIL_CLOSED_PRE_WORLD"
    )
    return _with_digest({
        "schema": "phi-existing-closed-loop-glue-run/v1",
        "status": status,
        "campaign_digest": campaign.get("digest"),
        "lowering_projection_preflight_digest": preflight.get("digest"),
        "frontier_ledger_sha256": campaign.get("frontier_ledger_sha256"),
        "episode_count": len(receipts),
        "counts": counts,
        "episodes": receipts,
        "universal_execution_runtime_bound_to_frontier_campaign": counts["bound_to_frozen_execution_runtime"] > 0,
        "route_closed_through_existing_systems": True,
        "route_complete_to_world_boundary_count": counts["ready_for_external_acquisition"],
        "external_data_fetched": False,
        "knowledge_state_mutated": False,
        "private_key_created_or_stored": False,
        "scientific_promotion_allowed": False,
        "claim_boundary": {
            "glue_run_is_world_evidence": False,
            "runtime_binding_is_artifact_acquisition": False,
            "missing_lowering_or_projection_may_be_skipped": False,
            "world_attestation_may_be_faked_locally": False,
        },
    })


def audit_existing_closed_loop_integration(
    root: str | Path | None = None,
    *,
    max_frontier_rows: int = 500,
    max_campaign_items: int = 8,
) -> Mapping[str, Any]:
    """Map the existing Atlas systems into one closed-loop route.

    This is a read-only integration audit.  It deliberately does not introduce a
    new scientific owner: every route step points at an existing owner, API
    surface, or sealed runtime component.  The result explains which existing
    systems are present, which are underused, and where the route currently
    stops before WORLD evidence can affect representation state.
    """
    from .closed_loop_research import ClosedLoopResearchOwner
    from .discriminating_experiment_autopilot import DiscriminatingExperimentAutopilotOwner
    from .experiment_execution import SCHEMA as EXPERIMENT_EXECUTION_SCHEMA, STAGES as EXPERIMENT_EXECUTION_STAGES
    from .knowledge_evolution import KnowledgeEvolutionKernel, WorldAttestationOwner
    from .scientific_exploitation import OWNER_ID as EXPLOITATION_OWNER_ID, OWNER_VERSION as EXPLOITATION_OWNER_VERSION
    from .scientific_promotion import ScientificPromotionCore
    from .scientific_verification import ScientificVerificationCore
    from .u5_attempt_scheduler import U5AttemptScheduler

    root_path = _root(root)
    if int(max_frontier_rows) < 1 or int(max_campaign_items) < 1:
        raise ValueError("audit limits must be >= 1")

    state = KnowledgeEvolutionKernel(root_path).state()
    campaign = run_world_closed_loop_campaign(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    glue = run_existing_closed_loop_glue(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    preflight = run_existing_lowering_projection_preflight(
        root_path,
        max_frontier_rows=int(max_frontier_rows),
        max_campaign_items=int(max_campaign_items),
    )
    promotion_contract = ScientificPromotionCore().contract()
    provider_registry = load_provider_capability_registry(root_path)
    trust = load_world_trust_registry(root_path)
    state_counts = {
        key: len(value)
        for key, value in sorted(state.items())
        if isinstance(value, list)
    }
    materialized = int(state_counts.get("hypothesis_materializations", 0))
    lowerings = int(state_counts.get("candidate_prediction_lowerings", 0))
    projections = int(state_counts.get("candidate_response_projections", 0))
    measurements = int(state_counts.get("candidate_measurement_executions", 0))
    discriminations = int(state_counts.get("candidate_prediction_discriminations", 0))
    world_attestations = int(state_counts.get("world_attestations", 0))
    provider_matches = int(campaign.get("provider_matched_episode_count", 0))
    attested = int(campaign.get("independently_attested_episode_count", 0))
    active_attestors = int(campaign.get("active_world_attestor_count", 0))

    systems = [
        {
            "system_id": "SCIENTIFIC-EXPLOITATION-ORCHESTRATOR",
            "owner": f"{EXPLOITATION_OWNER_ID}/{EXPLOITATION_OWNER_VERSION}",
            "role": "U4 candidate dossier and prediction-lowering preparation",
            "observed_records": {
                "hypothesis_materializations": materialized,
                "candidate_prediction_lowerings": lowerings,
            },
            "status": "PRESENT_UNDERUSED" if materialized and lowerings < materialized else "PRESENT",
        },
        {
            "system_id": "DISCRIMINATING-EXPERIMENT-AUTOPILOT",
            "owner": DiscriminatingExperimentAutopilotOwner(root_path).owner_id,
            "role": "freeze frontier and emit measurement requests",
            "observed_records": {
                "candidate_response_projections": projections,
                "candidate_prediction_discriminations": discriminations,
            },
            "status": "PRESENT_UNDERUSED" if materialized and projections < materialized else "PRESENT",
        },
        {
            "system_id": "FROZEN-EXPERIMENT-EXECUTION",
            "owner": EXPERIMENT_EXECUTION_SCHEMA,
            "role": "contract runtime for source capability, acquisition, adapter, frozen evaluation and adjudication",
            "stages": list(EXPERIMENT_EXECUTION_STAGES),
            "status": "PRESENT_BOUND_TO_FRONTIER_CAMPAIGN_BY_GLUE_RUNNER",
        },
        {
            "system_id": "CLOSED-LOOP-AXIS-RESEARCH",
            "owner": ClosedLoopResearchOwner.owner_id,
            "role": "measurement-driven residual axis modeling with sealed holdout",
            "status": "PRESENT_NEEDS_ADAPTER_BRIDGE_FROM_FRONTIER_ROUTE",
        },
        {
            "system_id": "SOURCE-PROVIDER-CAPABILITY-REGISTRY",
            "owner": provider_registry.get("owner_id"),
            "role": "map measurement intent to declared external source capabilities",
            "provider_count": len(provider_registry.get("providers", ())),
            "status": "PRESENT",
        },
        {
            "system_id": "SCIENTIFIC-VERIFICATION-CORE",
            "owner": ScientificVerificationCore().contract().get("owner_id"),
            "role": "source/evidence authenticity and claim-boundary verification",
            "status": "PRESENT",
        },
        {
            "system_id": "WORLD-ATTESTATION",
            "owner": WorldAttestationOwner().owner_id,
            "role": "WORLD-tier evidence snapshot and conflict-preserving attestation",
            "observed_records": {"world_attestations": world_attestations},
            "status": "BLOCKED_NO_ACTIVE_EXTERNAL_ATTESTOR" if active_attestors == 0 else "PRESENT_READY",
        },
        {
            "system_id": "U5-ATTEMPT-SCHEDULER",
            "owner": U5AttemptScheduler(root_path).owner_id,
            "role": "replay verification and classify U5 PASS/FAIL/DATA_PENDING/BLOCKED",
            "status": "PRESENT_BLOCKED_BY_WORLD_EVIDENCE" if attested == 0 else "PRESENT_READY_FOR_REPLAY",
        },
        {
            "system_id": "SCIENTIFIC-PROMOTION-CORE",
            "owner": f"{promotion_contract.get('owner')}/{promotion_contract.get('owner_version')}",
            "role": "final U0-U10 promotion authority after upstream evidence",
            "status": "PRESENT_NOT_REACHED",
        },
        {
            "system_id": "KNOWLEDGE-EVOLUTION-KERNEL",
            "owner": state.get("owner"),
            "role": "durable world binding, response projection, measurement execution and representation memory",
            "observed_records": state_counts,
            "status": "PRESENT",
        },
    ]

    route = [
        {
            "stage": "FRONTIER",
            "existing_system": "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl",
            "status": "READY",
            "observed": {"frontier_candidate_count": _frontier_row_count(root_path)},
        },
        {
            "stage": "U4_MATERIALIZATION",
            "existing_system": "KnowledgeEvolutionKernel.hypothesis_materializations",
            "status": "READY" if materialized else "BLOCKED_NO_MATERIALIZED_HYPOTHESES",
            "observed": {"hypothesis_materializations": materialized},
        },
        {
            "stage": "PREDICTION_LOWERING",
            "existing_system": "ScientificExploitation + KnowledgeEvolutionKernel.candidate_prediction_lowerings",
            "status": "UNDERUSED" if materialized and lowerings < materialized else "READY",
            "observed": {
                "candidate_prediction_lowerings": lowerings,
                "gap_to_materialized_hypotheses": max(0, materialized - lowerings),
                "matched_episode_prediction_lowering_ready": preflight.get("counts", {}).get("prediction_lowering_ready", 0),
                "matched_episode_prediction_lowering_required": preflight.get("counts", {}).get("prediction_lowering_required", 0),
            },
        },
        {
            "stage": "RESPONSE_PROJECTION",
            "existing_system": "KnowledgeEvolutionKernel.candidate_response_projections",
            "status": "UNDERUSED" if materialized and projections < materialized else "READY",
            "observed": {
                "candidate_response_projections": projections,
                "gap_to_materialized_hypotheses": max(0, materialized - projections),
                "matched_episode_u4_materialized": preflight.get("counts", {}).get("u4_materialized", 0),
                "matched_episode_u4_required": preflight.get("counts", {}).get("u4_materialization_required", 0),
                "matched_episode_response_observable_contract_required": preflight.get("counts", {}).get("response_observable_contract_required", 0),
                "matched_episode_response_projection_ready": preflight.get("counts", {}).get("response_projection_ready", 0),
            },
        },
        {
            "stage": "PROVIDER_MATCHING",
            "existing_system": "SourceProviderCapabilityRegistry + run_world_closed_loop_campaign",
            "status": "PARTIAL_READY" if provider_matches else "BLOCKED_NO_PROVIDER_MATCH",
            "observed": {
                "frontier_rows_examined": campaign.get("frontier_rows_examined"),
                "candidate_specs_with_measurement_intents": campaign.get("candidate_specs_with_measurement_intents"),
                "provider_matched_episode_count": provider_matches,
            },
        },
        {
            "stage": "FROZEN_EXECUTION",
            "existing_system": "experiment_execution.freeze_protocol/acquire_evidence/evaluate_frozen_predictions",
            "status": "BOUND_TO_FRONTIER_CAMPAIGN_WAITING_FOR_RESPONSE_PROJECTION",
            "observed": {
                "runtime_stages": list(EXPERIMENT_EXECUTION_STAGES),
                "bound_episode_count": glue.get("counts", {}).get("bound_to_frozen_execution_runtime", 0),
                "route_complete_to_world_boundary_count": glue.get("route_complete_to_world_boundary_count", 0),
            },
        },
        {
            "stage": "WORLD_ATTESTATION",
            "existing_system": "WorldAttestationOwner + data/world_trust/attestors.json",
            "status": "BLOCKED_NO_ACTIVE_EXTERNAL_ATTESTOR" if active_attestors == 0 else "READY",
            "observed": {
                "active_world_attestor_count": active_attestors,
                "world_attestations": world_attestations,
            },
        },
        {
            "stage": "U5_REPLAY",
            "existing_system": "U5AttemptScheduler",
            "status": "BLOCKED_WORLD_EVIDENCE_REQUIRED" if attested == 0 else "READY",
            "observed": {"independently_attested_episode_count": attested},
        },
        {
            "stage": "REPRESENTATION_REVISION",
            "existing_system": "KnowledgeEvolutionKernel + domain/axis lifecycle owners",
            "status": "PROTECTED_NO_CHANGE_WITHOUT_ATTESTED_U5_REPLAY",
            "observed": campaign.get("representation_world_model_after", {}),
        },
    ]

    gap_order = []
    if lowerings < materialized:
        gap_order.append("MASS_U4_TO_PREDICTION_LOWERING_NOT_SCALED")
    if projections < materialized:
        gap_order.append("PREDICTION_LOWERING_TO_RESPONSE_PROJECTION_NOT_SCALED")
    if int(preflight.get("counts", {}).get("response_observable_contract_required", 0) or 0) > 0:
        gap_order.append("MATCHED_U4_EPISODES_REQUIRE_RESPONSE_OBSERVABLE_CONTRACT")
    if int(preflight.get("counts", {}).get("u4_materialization_required", 0) or 0) > 0:
        gap_order.append("MATCHED_PROVIDER_EPISODES_REQUIRE_U4_MATERIALIZATION")
    if provider_matches < int(campaign.get("candidate_specs_with_measurement_intents", 0)):
        gap_order.append("MEASUREMENT_INTENT_TO_PROVIDER_MATCH_PARTIAL")
    if glue.get("universal_execution_runtime_bound_to_frontier_campaign") is not True:
        gap_order.append("UNIVERSAL_EXECUTION_RUNTIME_NOT_BOUND_TO_FRONTIER_CAMPAIGN")
    if int(glue.get("route_complete_to_world_boundary_count", 0) or 0) == 0:
        gap_order.append("FROZEN_EXECUTION_WAITING_FOR_RESPONSE_PROJECTION")
    if active_attestors == 0:
        gap_order.append("WORLD_TRUST_EMPTY")
    if attested == 0:
        gap_order.append("U5_REPLAY_HAS_NO_WORLD_EVIDENCE")

    return _with_digest({
        "schema": "phi-existing-closed-loop-system-integration-audit/v1",
        "status": "EXISTING_SYSTEMS_AUDITED_FAIL_CLOSED",
        "frontier_ledger_sha256": campaign.get("frontier_ledger_sha256"),
        "system_inventory": systems,
        "route": route,
        "state_counts": state_counts,
        "campaign_digest": campaign.get("digest"),
        "campaign_status": campaign.get("status"),
        "lowering_projection_preflight_digest": preflight.get("digest"),
        "lowering_projection_preflight_status": preflight.get("status"),
        "glue_run_digest": glue.get("digest"),
        "glue_run_status": glue.get("status"),
        "primary_bottlenecks_in_order": gap_order,
        "integration_policy": {
            "new_scientific_owner_created": False,
            "reuse_existing_owners_only": True,
            "private_key_created_or_stored": False,
            "external_data_fetched": False,
            "knowledge_state_mutated": False,
            "scientific_promotion_allowed": False,
        },
        "recommended_glue_path": [
            "route U4 materialized hypotheses through existing ScientificExploitation lowering",
            "bind lowered predictions to existing KnowledgeEvolution response projections",
            "compile projection into existing FrozenExperimentExecution contract",
            "use existing SourceProviderCapabilityRegistry for provider selection",
            "send acquired artifact to existing ScientificVerificationCore and WorldAttestationOwner",
            "replay existing U5AttemptScheduler",
            "allow representation revision only through existing KnowledgeEvolution owners after attested U5 replay",
        ],
        "claim_boundary": {
            "audit_is_world_evidence": False,
            "inventory_count_is_capability_proof": False,
            "provider_match_is_attestation": False,
            "underused_existing_systems_should_be_reused_before_new_owners": True,
        },
    })
