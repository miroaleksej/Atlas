"""Φ-Knowledge Evolution Kernel.

This module is the single transaction layer for ontology evolution and evidence binding:
WORLD-ATTESTATION, AXIS-LIFECYCLE, DOMAIN-ONTOGENESIS, CROSS-DOMAIN-BRIDGE,
OWNER-AXIS-BINDING and CANDIDATE-WORLD-BINDING.
It does not duplicate scientific verification, dynamic-axis promotion or the
owner-hypergraph search.  It consumes their frozen receipts and adds durable,
fail-closed ontology evolution on top.

External/network material is never a pre-freeze candidate selector here.
Production canonical transactions require WORLD-tier scientific verification;
qualification fixtures may exercise the transaction machinery only inside an
explicit QUALIFICATION_ONLY sandbox.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .schema import digest_payload, canonical_json
from .domains import DOMAIN_REGISTRIES, load_domain_plugin_manifests
from .scientific_rules import OWNER_ID as COMMON_RULES_OWNER
from .scientific_verification import ScientificVerificationCore

KERNEL_OWNER_ID = "PHI-KNOWLEDGE-EVOLUTION-KERNEL/1.3.0"
WORLD_ATTESTATION_OWNER_ID = "WORLD-ATTESTATION/1.0.0"
AXIS_LIFECYCLE_OWNER_ID = "AXIS-LIFECYCLE/1.0.0"
DOMAIN_ONTOGENESIS_OWNER_ID = "DOMAIN-ONTOGENESIS/1.0.0"
CROSS_DOMAIN_BRIDGE_OWNER_ID = "CROSS-DOMAIN-BRIDGE/1.0.0"
OWNER_AXIS_BINDING_OWNER_ID = "OWNER-AXIS-BINDING/1.0.0"
CANDIDATE_WORLD_BINDING_OWNER_ID = "CANDIDATE-WORLD-BINDING/1.3.0"
SCHEMA = "phi-knowledge-evolution-kernel/v1"
STATE_SCHEMA = "phi-knowledge-evolution-state/v1"

_ALLOWED_AXIS_STATES = {"RESEARCH", "PROVISIONAL", "CANONICAL", "DEPRECATED", "REPLACED", "RETIRED"}
_ALLOWED_AXIS_TRANSITIONS = {
    "RESEARCH": {"PROVISIONAL", "RETIRED"},
    "PROVISIONAL": {"CANONICAL", "RETIRED"},
    "CANONICAL": {"DEPRECATED", "REPLACED"},
    "DEPRECATED": {"REPLACED", "RETIRED"},
    "REPLACED": set(),
    "RETIRED": set(),
}


def _sha256_hex(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def _default_state_path(root: str | Path | None = None) -> Path:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    return Path(root) / "data" / "knowledge" / "knowledge_evolution_state.json"


def _empty_state() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "owner": KERNEL_OWNER_ID,
        "world_attestations": [],
        "axis_lifecycle": [],
        "research_axis_proposals": [],
        "domain_transactions": [],
        "cross_domain_bridges": [],
        "owner_axis_bindings": [],
        "candidate_world_bindings": [],
        "candidate_response_projections": [],
        "candidate_measurement_executions": [],
        "candidate_prediction_lowerings": [],
        "candidate_prediction_discriminations": [],
        "hypothesis_materializations": [],
    }
    payload["digest"] = digest_payload({k: v for k, v in payload.items() if k != "digest"})
    return payload


def _load_state(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _empty_state()
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != STATE_SCHEMA:
        raise ValueError(f"unsupported knowledge evolution state schema: {doc.get('schema')!r}")
    expected = digest_payload({k: v for k, v in doc.items() if k != "digest"})
    if doc.get("digest") != expected:
        raise ValueError("knowledge evolution state digest mismatch")
    return dict(doc)


def _atomic_write_state(path: str | Path, state: Mapping[str, Any]) -> Mapping[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(state)
    doc["schema"] = STATE_SCHEMA
    doc["owner"] = KERNEL_OWNER_ID
    doc["digest"] = digest_payload({k: v for k, v in doc.items() if k != "digest"})
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return doc


def _append_state(path: str | Path, section: str, row: Mapping[str, Any]) -> Mapping[str, Any]:
    state = _load_state(path)
    values = list(state.get(section, ()))
    values.append(dict(row))
    state[section] = values
    return _atomic_write_state(path, state)


def _distinct(values: Iterable[Any]) -> list[str]:
    return sorted({str(x) for x in values if str(x)})


class WorldAttestationOwner:
    owner_id = WORLD_ATTESTATION_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-world-attestation/v1",
            "owner_id": self.owner_id,
            "delegation": {
                "scientific_verification": "SCIENTIFIC-VERIFICATION-CORE/8.0.0",
                "data_ingestion": "SCIENTIFIC-DATA-INGESTION/5.9.0",
            },
            "pipeline": ["sources", "provenance", "claims", "conflicts", "measurements", "domain_axes", "qualification"],
            "rules": {
                "serialized_identifiers_are_not_world_evidence": True,
                "qualification_tier_may_not_be_relabelled_world": True,
                "conflicts_are_preserved_not_silently_resolved": True,
                "internet_used_for_prefreeze_candidate_selection": False,
                "world_ready_requires_existing_world_tier_verification": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def attest(
        self,
        *,
        verification_bundles: Sequence[Mapping[str, Any]],
        measurements: Sequence[Mapping[str, Any]] = (),
        qualification_mode: bool = False,
        persist_path: str | Path | None = None,
    ) -> Mapping[str, Any]:
        receipts: list[dict[str, Any]] = []
        claims: list[dict[str, Any]] = []
        all_sources: set[str] = set()
        world_receipt_count = 0
        engine_receipt_count = 0
        rejected_receipt_count = 0
        for i, bundle0 in enumerate(verification_bundles):
            bundle = dict(bundle0)
            receipt = dict(ScientificVerificationCore().verify_bundle(bundle))
            if receipt.get("scientific_candidate_allowed") is True:
                tier = "WORLD"
                world_receipt_count += 1
            elif receipt.get("evidence_ready_for_domain") is True:
                tier = "ENGINE_OR_QUALIFICATION"
                engine_receipt_count += 1
            else:
                tier = "REJECTED"
                rejected_receipt_count += 1
            valid_sources = [sid for sid, row in receipt.get("source_results", {}).items() if row.get("valid") is True]
            all_sources.update(valid_sources)
            environment_id = str(bundle.get("environment_id") or f"VERIFICATION-{i}")
            for key, value in sorted(dict(receipt.get("sanitized_claim_values", {})).items()):
                if value == "INSUFFICIENT":
                    continue
                claims.append({
                    "claim_key": str(key),
                    "claim_value": value,
                    "claim_value_digest": digest_payload(value),
                    "environment_id": environment_id,
                    "source_receipt_ids": valid_sources,
                    "verification_digest": receipt.get("verification_digest"),
                    "attestation_tier": tier,
                })
            receipts.append({
                "environment_id": environment_id,
                "verification_digest": receipt.get("verification_digest"),
                "overall_status": receipt.get("overall_status"),
                "evidence_ready_for_domain": receipt.get("evidence_ready_for_domain"),
                "scientific_candidate_allowed": receipt.get("scientific_candidate_allowed"),
                "world_attestation_ready": receipt.get("world_attestation_ready"),
                "attestation_tier": tier,
                "source_receipt_ids": valid_sources,
            })

        measurement_rows: list[dict[str, Any]] = []
        for m0 in measurements:
            m = dict(m0)
            checks = {
                "MEASUREMENT_ID": bool(str(m.get("measurement_id", "")).strip()),
                "OBSERVABLE_ID": bool(str(m.get("observable_id", "")).strip()),
                "ENVIRONMENT_ID": bool(str(m.get("environment_id", "")).strip()),
                "MEASUREMENT_OWNER": bool(str(m.get("measurement_owner", "")).strip()),
                "PROTOCOL_DIGEST": _sha256_hex(m.get("protocol_digest")),
                "DATA_DIGEST": _sha256_hex(m.get("data_digest")),
                "VALUE_OR_VALUE_DIGEST": m.get("value") is not None or _sha256_hex(m.get("value_digest")),
                "UNCERTAINTY_DECLARED": m.get("uncertainty") is not None,
            }
            measurement_rows.append({**m, "checks": checks, "structurally_valid": all(checks.values())})

        conflicts: list[dict[str, Any]] = []
        by_key: dict[str, list[dict[str, Any]]] = {}
        for row in claims:
            by_key.setdefault(row["claim_key"], []).append(row)
        for key, rows in sorted(by_key.items()):
            values = {}
            for row in rows:
                values.setdefault(row["claim_value_digest"], row["claim_value"])
            if len(values) > 1:
                conflicts.append({
                    "claim_key": key,
                    "status": "UNRESOLVED_ATTESTED_CONFLICT",
                    "claim_value_digests": sorted(values),
                    "environments": _distinct(r["environment_id"] for r in rows),
                    "source_receipt_ids": _distinct(s for r in rows for s in r["source_receipt_ids"]),
                })

        valid_measurement_owners = _distinct(
            r.get("measurement_owner") for r in measurement_rows if r.get("structurally_valid")
        )
        valid_measurement_envs = _distinct(
            r.get("environment_id") for r in measurement_rows if r.get("structurally_valid")
        )
        world_ready = world_receipt_count > 0 and len(all_sources) >= 2
        qualification_ready = bool(
            qualification_mode
            and not world_ready
            and engine_receipt_count >= 2
            and len(all_sources) >= 2
        )
        status = (
            "WORLD_ATTESTATION_READY"
            if world_ready else
            "QUALIFICATION_ATTESTATION_READY_NOT_WORLD"
            if qualification_ready else
            "ENGINE_ATTESTED_WORLD_CLAIM_BLOCKED"
            if engine_receipt_count else
            "WORLD_ATTESTATION_BLOCKED"
        )
        payload = {
            "schema": "phi-world-attestation-snapshot/v1",
            "owner_id": self.owner_id,
            "status": status,
            "world_ready": world_ready,
            "qualification_ready": qualification_ready,
            "qualification_mode": bool(qualification_mode),
            "verification_receipts": receipts,
            "claims": claims,
            "conflicts": conflicts,
            "measurements": measurement_rows,
            "distinct_verified_source_count": len(all_sources),
            "distinct_measurement_owner_count": len(valid_measurement_owners),
            "distinct_measurement_environment_count": len(valid_measurement_envs),
            "world_receipt_count": world_receipt_count,
            "engine_or_qualification_receipt_count": engine_receipt_count,
            "rejected_receipt_count": rejected_receipt_count,
            "claim_boundary": {
                "qualification_fixture_is_world_attestation": False,
                "attestation_is_scientific_promotion": False,
                "conflict_presence_is_resolution": False,
                "internet_used_for_prefreeze_candidate_selection": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        if persist_path is not None:
            _append_state(persist_path, "world_attestations", payload)
        return payload


class AxisLifecycleOwner:
    owner_id = AXIS_LIFECYCLE_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-axis-lifecycle/v1",
            "owner_id": self.owner_id,
            "states": sorted(_ALLOWED_AXIS_STATES),
            "transitions": {k: sorted(v) for k, v in _ALLOWED_AXIS_TRANSITIONS.items()},
            "addressability_rule": "DEPRECATED_REPLACED_AXES_REMAIN_ADDRESSABLE_THROUGH_LEDGER",
            "canonical_rule": "CANONICAL_IS_BEST_QUALIFIED_CURRENT_REPRESENTATION_NOT_ETERNAL_TRUTH",
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _fq(domain_id: str, axis_id: str) -> str:
        return f"{domain_id}.{axis_id}"

    def commit_research_proposal(
        self,
        proposal: Mapping[str, Any],
        *,
        state_path: str | Path,
        source_owner_id: str,
        evidence_digest: str,
        domain_scope_candidates: Sequence[str] = (),
    ) -> Mapping[str, Any]:
        """Persist a research-local axis proposal without canonical promotion.

        A proposal may be worth preserving before a unique canonical domain,
        measurement protocol, OOD gain or WORLD attestation is available.  This
        ledger closes the historical gap where valid research-local axis births
        could live only inside one regression payload and therefore remain
        invisible to the central knowledge state.
        """
        axis_id = str(proposal.get("axis_id", "")).strip()
        semantic_class = str(proposal.get("semantic_class", "")).strip()
        original_status = str(proposal.get("status", "")).strip()
        if not axis_id or not semantic_class or not original_status:
            raise ValueError("research axis proposal requires axis_id, semantic_class and status")
        if not _sha256_hex(evidence_digest):
            raise ValueError("research axis proposal requires a SHA-256 evidence digest")
        domains = _distinct(str(x) for x in domain_scope_candidates if str(x).strip())
        unknown_domains = [d for d in domains if d not in DOMAIN_REGISTRIES]
        if unknown_domains:
            raise ValueError(f"unknown research axis proposal domain scopes: {unknown_domains}")
        core = {
            "schema": "phi-research-axis-proposal/v1",
            "owner_id": self.owner_id,
            "proposal_id": "AXPROP-" + digest_payload({
                "axis_id": axis_id,
                "semantic_class": semantic_class,
                "source_owner_id": str(source_owner_id),
                "evidence_digest": str(evidence_digest),
            })[:24].upper(),
            "axis_id": axis_id,
            "semantic_class": semantic_class,
            "definition": proposal.get("definition"),
            "reason": str(proposal.get("reason", "")),
            "source_status": original_status,
            "source_owner_id": str(source_owner_id),
            "domain_scope_candidates": domains,
            "canonical_domain_id": None,
            "lifecycle_status": "RESEARCH",
            "evidence_digest": str(evidence_digest),
            "canonical_registry_mutated": False,
            "canonical_promotion_attempted": False,
            "canonical_promotion_block_reason": "REQUIRES_DYNAMIC_AXIS_PROMOTION_GATES_AND_WORLD_ATTESTATION",
            "claim_boundary": {
                "research_proposal_is_canonical_axis": False,
                "research_proposal_is_established_measurand": False,
                "source_local_qualification_is_world_attestation": False,
                "future_promotion_requires_existing_dynamic_axis_owner": True,
            },
        }
        row = {**core, "digest": digest_payload(core)}
        state = _load_state(state_path)
        existing = [r for r in state.get("research_axis_proposals", ()) if str(r.get("proposal_id")) == row["proposal_id"]]
        if existing:
            if existing[-1].get("digest") != row["digest"]:
                raise ValueError("research axis proposal id collision")
            return dict(existing[-1])
        _append_state(state_path, "research_axis_proposals", row)
        return row

    def state_of(self, domain_id: str, axis_id: str, *, state_path: str | Path) -> Mapping[str, Any]:
        fq = self._fq(domain_id, axis_id)
        state = _load_state(state_path)
        rows = [r for r in state.get("axis_lifecycle", ()) if r.get("qualified_axis_id") == fq and r.get("committed") is True]
        if rows:
            row = dict(rows[-1])
            return {"qualified_axis_id": fq, "status": row.get("to_status"), "replacement_axis_id": row.get("replacement_axis_id"), "source": "LIFECYCLE_LEDGER", "transition_digest": row.get("digest")}
        if domain_id in DOMAIN_REGISTRIES and axis_id in DOMAIN_REGISTRIES[domain_id].axes:
            return {"qualified_axis_id": fq, "status": "CANONICAL", "replacement_axis_id": None, "source": "CANONICAL_REGISTRY"}
        return {"qualified_axis_id": fq, "status": "RESEARCH", "replacement_axis_id": None, "source": "UNREGISTERED_RESEARCH_COORDINATE"}

    def propose_transition(
        self,
        *,
        domain_id: str,
        axis_id: str,
        to_status: str,
        evidence: Mapping[str, Any],
        state_path: str | Path,
        replacement_axis_id: str | None = None,
        qualification_mode: bool = False,
    ) -> Mapping[str, Any]:
        to_status = str(to_status).upper()
        if to_status not in _ALLOWED_AXIS_STATES:
            raise ValueError(f"unsupported axis lifecycle state {to_status!r}")
        current = self.state_of(domain_id, axis_id, state_path=state_path)
        from_status = str(current["status"])
        envs = _distinct(evidence.get("environment_ids", ()))
        owners = _distinct(evidence.get("owner_ids", ()))
        digests = _distinct(evidence.get("evidence_digests", ()))
        replacement_exists = True
        if replacement_axis_id:
            if "." not in replacement_axis_id:
                replacement_axis_id = f"{domain_id}.{replacement_axis_id}"
            rd, ra = replacement_axis_id.split(".", 1)
            replacement_exists = rd in DOMAIN_REGISTRIES and ra in DOMAIN_REGISTRIES[rd].axes
        checks = {
            "TRANSITION_ALLOWED": to_status in _ALLOWED_AXIS_TRANSITIONS.get(from_status, set()),
            "EVIDENCE_DIGEST_PRESENT": len(digests) >= 1 and all(_sha256_hex(d) for d in digests),
            "INDEPENDENT_ENVIRONMENTS_FOR_POSTCANONICAL_CHANGE": from_status not in {"CANONICAL", "DEPRECATED"} or len(envs) >= 2,
            "INDEPENDENT_OWNERS_FOR_POSTCANONICAL_CHANGE": from_status not in {"CANONICAL", "DEPRECATED"} or len(owners) >= 2,
            "REPLACEMENT_DECLARED_WHEN_REPLACED": to_status != "REPLACED" or bool(replacement_axis_id),
            "REPLACEMENT_AXIS_EXISTS": to_status != "REPLACED" or replacement_exists,
            "REPLACEMENT_EQUIVALENCE_QUALIFIED": to_status != "REPLACED" or float(evidence.get("equivalence_score", 0.0)) >= 0.95,
            "PROMOTION_RECEIPT_REQUIRED_FOR_CANONICAL": to_status != "CANONICAL" or bool(evidence.get("canonical_promotion_receipt_digest")) or qualification_mode,
        }
        allowed = all(checks.values())
        payload = {
            "schema": "phi-axis-lifecycle-transition/v1",
            "owner_id": self.owner_id,
            "qualified_axis_id": self._fq(domain_id, axis_id),
            "from_status": from_status,
            "to_status": to_status,
            "replacement_axis_id": replacement_axis_id,
            "checks": checks,
            "transition_allowed": allowed,
            "status": "AXIS_LIFECYCLE_TRANSITION_QUALIFIED" if allowed else "AXIS_LIFECYCLE_TRANSITION_BLOCKED",
            "evidence": {
                "environment_ids": envs,
                "owner_ids": owners,
                "evidence_digests": digests,
                "equivalence_score": evidence.get("equivalence_score"),
            },
            "qualification_mode": bool(qualification_mode),
            "committed": False,
            "claim_boundary": {
                "axis_definition_deleted": False,
                "old_axis_addressability_preserved": True,
                "canonical_status_is_immutable": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def commit_transition(self, receipt: Mapping[str, Any], *, state_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        expected = digest_payload({k: v for k, v in row.items() if k != "digest"})
        if row.get("digest") != expected:
            raise ValueError("axis lifecycle receipt digest mismatch")
        if row.get("transition_allowed") is not True:
            raise ValueError("blocked axis lifecycle transition cannot be committed")
        committed = dict(row)
        committed["committed"] = True
        committed["status"] = "AXIS_LIFECYCLE_TRANSITION_COMMITTED"
        committed["digest"] = digest_payload({k: v for k, v in committed.items() if k != "digest"})
        _append_state(state_path, "axis_lifecycle", committed)
        return committed

    def resolve_axis(self, qualified_axis_id: str, *, state_path: str | Path) -> Mapping[str, Any]:
        if "." not in qualified_axis_id:
            raise ValueError("qualified axis id must be domain.axis")
        seen: list[str] = []
        current = qualified_axis_id
        while True:
            if current in seen:
                return {"status": "AXIS_REPLACEMENT_CYCLE_BLOCKED", "path": [*seen, current]}
            seen.append(current)
            domain_id, axis_id = current.split(".", 1)
            state = self.state_of(domain_id, axis_id, state_path=state_path)
            replacement = state.get("replacement_axis_id")
            if state.get("status") != "REPLACED" or not replacement:
                return {"status": "AXIS_RESOLUTION_COMPLETE", "input_axis_id": qualified_axis_id, "resolved_axis_id": current, "resolved_status": state.get("status"), "path": seen}
            current = str(replacement)

    def active_view(self, *, state_path: str | Path) -> Mapping[str, Any]:
        rows = []
        for domain_id, registry in sorted(DOMAIN_REGISTRIES.items()):
            for axis_id in sorted(registry.axes):
                state = self.state_of(domain_id, axis_id, state_path=state_path)
                rows.append(state)
        active = [r for r in rows if r.get("status") not in {"DEPRECATED", "REPLACED", "RETIRED"}]
        payload = {
            "schema": "phi-axis-lifecycle-active-view/v1",
            "owner_id": self.owner_id,
            "addressable_axis_count": len(rows),
            "active_axis_count": len(active),
            "inactive_addressable_axis_count": len(rows) - len(active),
            "rows": rows,
            "canonical_registry_mutated": False,
        }
        return {**payload, "digest": digest_payload(payload)}


class CrossDomainBridgeOwner:
    owner_id = CROSS_DOMAIN_BRIDGE_OWNER_ID
    _FIELDS = ("dimension", "measurement_kind", "observable_role", "causal_role", "normalization")
    _WEIGHTS = {"dimension": 0.25, "measurement_kind": 0.20, "observable_role": 0.20, "causal_role": 0.20, "normalization": 0.15}

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-cross-domain-bridge/v1",
            "owner_id": self.owner_id,
            "bridge_object": ["source_axis", "target_axis", "Preserve", "Lose", "Conditions", "Evidence"],
            "canonical_merge_policy": "BRIDGE_NEVER_MERGES_CANONICAL_AXES",
            "minimum_score": 0.92,
        }
        return {**payload, "digest": digest_payload(payload)}

    def discover(
        self,
        signatures: Sequence[Mapping[str, Any]],
        *,
        minimum_score: float = 0.92,
        persist_path: str | Path | None = None,
    ) -> Mapping[str, Any]:
        rows = [dict(r) for r in signatures]
        edges: list[dict[str, Any]] = []
        for i, a in enumerate(rows):
            for b in rows[i + 1 :]:
                if a.get("domain_id") == b.get("domain_id"):
                    continue
                preserve = [f for f in self._FIELDS if canonical_json(a.get(f)) == canonical_json(b.get(f)) and a.get(f) is not None]
                lose = [f for f in self._FIELDS if f not in preserve]
                score = sum(self._WEIGHTS[f] for f in preserve)
                evidence = _distinct([*a.get("evidence_digests", ()), *b.get("evidence_digests", ())])
                environments = _distinct([*a.get("environment_ids", ()), *b.get("environment_ids", ())])
                owners = _distinct([*a.get("owner_ids", ()), *b.get("owner_ids", ())])
                if score + 1e-12 < minimum_score or len(evidence) < 2 or len(environments) < 2 or len(owners) < 2:
                    continue
                edge_seed = {
                    "a": f"{a.get('domain_id')}.{a.get('axis_id')}",
                    "b": f"{b.get('domain_id')}.{b.get('axis_id')}",
                    "preserve": preserve,
                    "lose": lose,
                    "score": round(score, 12),
                    "evidence": evidence,
                }
                edge = {
                    "bridge_id": "XDB-" + digest_payload(edge_seed)[:20].upper(),
                    "source_axis_id": edge_seed["a"],
                    "target_axis_id": edge_seed["b"],
                    "score": round(score, 12),
                    "Preserve": preserve,
                    "Lose": lose,
                    "Conditions": {"minimum_score": minimum_score, "independent_environments": environments, "independent_owners": owners},
                    "Evidence": evidence,
                    "status": "BRIDGE_QUALIFIED_NONMERGING",
                    "canonical_axes_merged": False,
                }
                edge["digest"] = digest_payload(edge)
                edges.append(edge)
        edges.sort(key=lambda x: (-float(x["score"]), x["source_axis_id"], x["target_axis_id"]))
        payload = {
            "schema": "phi-cross-domain-bridge-graph/v1",
            "owner_id": self.owner_id,
            "status": "CROSS_DOMAIN_BRIDGE_GRAPH_BUILT",
            "edge_count": len(edges),
            "edges": edges,
            "claim_boundary": {
                "bridge_implies_domain_merge": False,
                "bridge_implies_identity_of_world_entities": False,
                "canonical_axes_mutated": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        if persist_path is not None:
            for edge in edges:
                _append_state(persist_path, "cross_domain_bridges", edge)
        return payload

    def certify_typed_law_bridge(self, *, source: Mapping[str, Any], target: Mapping[str, Any], mapping: Mapping[str, str], consequence_transfer: bool, independent_oos_validation: bool = False) -> Mapping[str, Any]:
        """Certify a law/chart bridge by the ScienceAtlas evidence ladder.

        Formula/AST similarity is never sufficient.  Role mapping, dimensional or
        explicit functor compatibility, validity overlap and consequence transfer
        are required before a bridge is scientifically typed.
        """
        roles_ok = bool(mapping) and all(str(k) and str(v) for k, v in mapping.items())
        dims_ok = source.get("dimension_signature") == target.get("dimension_signature") or bool(source.get("typed_dimension_functor") and target.get("typed_dimension_functor"))
        validity_ok = bool(set(source.get("validity_tags", ())) & set(target.get("validity_tags", ())))
        operator_ok = source.get("operator_family") == target.get("operator_family") and source.get("operator_family") is not None
        gates = {
            "role_typed_mapping": roles_ok, "dimension_or_typed_functor": dims_ok,
            "validity_overlap": validity_ok, "operator_commutation_proxy": operator_ok,
            "consequence_transfer": bool(consequence_transfer),
        }
        level = 6 if all(gates.values()) and independent_oos_validation else 5 if all(gates.values()) else 2 if roles_ok else 1
        status = "TYPED_BRIDGE_OOS_VALIDATED" if level == 6 else "TYPED_BRIDGE_CONSEQUENCE_TRANSFER" if level == 5 else "MATHEMATICAL_ANALOGY_ONLY"
        payload = {
            "schema": "phi-cross-domain-typed-law-bridge/v2", "owner_id": self.owner_id,
            "status": status, "evidence_level": level, "gates": gates, "mapping": dict(mapping),
            "canonical_axes_merged": False,
            "claim_boundary": {"formula_match_is_bridge": False, "ast_match_is_bridge": False, "world_entity_identity_claimed": False},
        }
        return {**payload, "digest": digest_payload(payload)}

    def domain_pair_coverage(self, graph: Mapping[str, Any], *, domain_a: str, domain_b: str, axis_counts: Mapping[str, int]) -> Mapping[str, Any]:
        edges = [e for e in graph.get("edges", ()) if {str(e.get("source_axis_id", "")).split(".", 1)[0], str(e.get("target_axis_id", "")).split(".", 1)[0]} == {domain_a, domain_b}]
        denominator = max(min(int(axis_counts.get(domain_a, 0)), int(axis_counts.get(domain_b, 0))), 1)
        coverage = min(len(edges) / denominator, 1.0)
        return {"domain_a": domain_a, "domain_b": domain_b, "qualified_bridge_count": len(edges), "coverage": coverage, "status": "BRIDGE_COVERAGE_COMPUTED"}


class DomainOntogenesisOwner:
    owner_id = DOMAIN_ONTOGENESIS_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-domain-ontogenesis/v1",
            "owner_id": self.owner_id,
            "transaction": ["proposal", "qualification", "canonical_domain_manifest"],
            "birth_gates": ["internal_phi_scan_frozen", "world_attestation", "nonredundancy", "closure", "owner_coherence", "predictive_gain", "axis_minimum"],
            "restructure": ["split", "merge_as_nondestructive_superdomain"],
            "generic_rules_owner": COMMON_RULES_OWNER,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _manifest(domain_id: str, description_ru: str, axes: Sequence[Mapping[str, Any]], domain_role: str, provenance: str) -> Mapping[str, Any]:
        normalized_axes = []
        seen = set()
        for row0 in axes:
            row = dict(row0)
            axis_id = str(row.get("axis_id", "")).strip()
            if not axis_id or axis_id in seen:
                raise ValueError("domain ontogenesis axes require unique nonempty axis_id")
            seen.add(axis_id)
            normalized_axes.append({
                "axis_id": axis_id,
                "description_ru": str(row.get("description_ru") or f"Исследовательская ось {axis_id}"),
                "value_kind": str(row.get("value_kind", "TEXT")),
                "allowed_values": list(row.get("allowed_values", ())),
                "required_for": list(row.get("required_for", ())),
                "forbidden_for": list(row.get("forbidden_for", ())),
                "provenance": str(row.get("provenance") or provenance),
            })
        return {
            "schema": "phi-domain-plugin-manifest/v1",
            "domain_id": domain_id,
            "domain_role": domain_role,
            "description_ru": description_ru,
            "axis_schema_version": "1",
            "common_rules_owner": COMMON_RULES_OWNER,
            "axes": normalized_axes,
            "entity_profiles": [],
            "constraints": [],
            "owner": {},
        }

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot=sum(float(x)*float(y) for x,y in zip(a,b))
        na=math.sqrt(sum(float(x)*float(x) for x in a)); nb=math.sqrt(sum(float(y)*float(y) for y in b))
        return dot/(na*nb) if na>0 and nb>0 else 0.0

    def derive_birth_metrics(self, evidence_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        rows=[dict(r) for r in evidence_rows]
        if len(rows)<2:
            return {"status":"INSUFFICIENT_DOMAIN_EVIDENCE","row_count":len(rows),"metrics_valid":False}
        vectors=[]; existing: dict[str,list[float]]={}; clusters=[]; gains=[]; envs=[]
        for row in rows:
            vec=tuple(float(x) for x in row.get("feature_vector",()))
            if not vec:
                return {"status":"INVALID_DOMAIN_EVIDENCE_FEATURE_VECTOR","metrics_valid":False}
            vectors.append(vec)
            for domain,score in dict(row.get("existing_domain_scores",{})).items(): existing.setdefault(str(domain),[]).append(float(score))
            clusters.append(str(row.get("owner_cluster_id","")))
            gains.append(float(row.get("prospective_predictive_gain",0.0)))
            envs.append(str(row.get("environment_id","")))
        sims=[]
        for i,a in enumerate(vectors):
            for b in vectors[i+1:]: sims.append((self._cosine(a,b)+1.0)/2.0)
        closure=sum(sims)/len(sims) if sims else 0.0
        domain_means={d:sum(v)/len(v) for d,v in existing.items() if v}
        existing_fit=max(domain_means.values(),default=0.0)
        nonempty=[c for c in clusters if c]
        owner_coherence=max((nonempty.count(c) for c in set(nonempty)),default=0)/len(rows)
        predictive_gain=sum(gains)/len(gains)
        payload={
            "status":"DOMAIN_BIRTH_METRICS_DERIVED","metrics_valid":True,"row_count":len(rows),
            "existing_domain_fit_max":existing_fit,"existing_domain_mean_scores":domain_means,
            "closure_score":closure,"owner_coherence_score":owner_coherence,"predictive_gain":predictive_gain,
            "independent_environment_count":len(set(e for e in envs if e)),
            "evidence_digest":digest_payload(rows),
        }
        return {**payload,"digest":digest_payload(payload)}

    def assess_birth(
        self,
        *,
        scan_receipt: Mapping[str, Any],
        attestation: Mapping[str, Any],
        domain_id: str,
        description_ru: str,
        axes: Sequence[Mapping[str, Any]],
        evidence_rows: Sequence[Mapping[str, Any]],
        domain_role: str = "natural_science",
        qualification_mode: bool = False,
    ) -> Mapping[str, Any]:
        domain_id = str(domain_id).strip()
        attestation_ok = attestation.get("world_ready") is True or (qualification_mode and attestation.get("qualification_ready") is True)
        metrics=dict(self.derive_birth_metrics(evidence_rows))
        existing_domain_fit_max=float(metrics.get("existing_domain_fit_max",1.0))
        closure_score=float(metrics.get("closure_score",0.0))
        owner_coherence_score=float(metrics.get("owner_coherence_score",0.0))
        predictive_gain=float(metrics.get("predictive_gain",0.0))
        checks = {
            "DOMAIN_ID_NEW": bool(domain_id) and domain_id not in DOMAIN_REGISTRIES,
            "INTERNAL_PHI_SCAN_FROZEN": bool(scan_receipt.get("digest")) and scan_receipt.get("all_registered_axes_visited") is True,
            "INTERNET_NOT_PREFREEZE_SELECTOR": scan_receipt.get("knowledge_firewall", {}).get("literature_novelty_used_for_source_scoring") in {False, None},
            "ATTESTATION_READY_FOR_MODE": attestation_ok,
            "METRICS_DERIVED_FROM_FROZEN_EVIDENCE": metrics.get("metrics_valid") is True and int(metrics.get("independent_environment_count",0)) >= 2,
            "NONREDUNDANT_WITH_EXISTING_DOMAIN": existing_domain_fit_max < 0.75,
            "INTERNAL_CLOSURE": closure_score >= 0.80,
            "OWNER_COHERENCE": owner_coherence_score >= 0.80,
            "PREDICTIVE_GAIN": predictive_gain > 0.0,
            "MULTIPLE_AXES": len(axes) >= 2,
        }
        warranted = all(checks.values())
        manifest = self._manifest(domain_id, description_ru, axes, domain_role, f"DOMAIN_ONTOGENESIS:{scan_receipt.get('digest')}") if warranted else None
        payload = {
            "schema": "phi-domain-birth-qualification/v1",
            "owner_id": self.owner_id,
            "domain_id": domain_id,
            "status": "NEW_DOMAIN_WARRANTED" if warranted else "NEW_DOMAIN_NOT_WARRANTED",
            "checks": checks,
            "canonical_transaction_allowed": warranted,
            "attestation_tier": "WORLD" if attestation.get("world_ready") else "QUALIFICATION_ONLY" if qualification_mode and attestation.get("qualification_ready") else "NONE",
            "scan_digest": scan_receipt.get("digest"),
            "attestation_digest": attestation.get("digest"),
            "metrics": metrics,
            "manifest": manifest,
            "qualification_mode": bool(qualification_mode),
            "claim_boundary": {
                "one_new_axis_is_new_domain": False,
                "canonical_domain_created_before_qualification": False,
                "qualification_mode_is_world_domain_promotion": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def commit_birth(
        self,
        receipt: Mapping[str, Any],
        *,
        manifest_dir: str | Path,
        state_path: str | Path,
    ) -> Mapping[str, Any]:
        row = dict(receipt)
        expected = digest_payload({k: v for k, v in row.items() if k != "digest"})
        if row.get("digest") != expected:
            raise ValueError("domain birth qualification digest mismatch")
        if row.get("canonical_transaction_allowed") is not True:
            raise ValueError("unqualified domain birth cannot be committed")
        if row.get("attestation_tier") not in {"WORLD", "QUALIFICATION_ONLY"}:
            raise ValueError("domain birth lacks attestation tier")
        if row.get("attestation_tier") == "QUALIFICATION_ONLY" and row.get("qualification_mode") is not True:
            raise ValueError("qualification attestation cannot commit a production domain")
        root = Path(manifest_dir)
        root.mkdir(parents=True, exist_ok=True)
        domain_id = str(row["domain_id"])
        path = root / f"{domain_id}.json"
        if path.exists():
            raise FileExistsError(f"domain manifest already exists: {path.name}")
        manifest = dict(row["manifest"])
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        loaded = load_domain_plugin_manifests(root)
        if domain_id not in loaded:
            path.unlink(missing_ok=True)
            raise RuntimeError("domain manifest transaction failed reload validation")
        transaction = {
            "schema": "phi-domain-transaction/v1",
            "owner_id": self.owner_id,
            "transaction_type": "BIRTH",
            "domain_id": domain_id,
            "status": "CANONICAL_DOMAIN_MANIFEST_COMMITTED" if row.get("attestation_tier") == "WORLD" else "QUALIFICATION_SANDBOX_DOMAIN_MANIFEST_COMMITTED",
            "manifest_path": str(path),
            "manifest_digest": digest_payload(manifest),
            "qualification_digest": row.get("digest"),
            "attestation_tier": row.get("attestation_tier"),
            "restart_required_for_global_registry_activation": True,
            "existing_canonical_domains_deleted": False,
        }
        transaction["digest"] = digest_payload(transaction)
        _append_state(state_path, "domain_transactions", transaction)
        return transaction

    def derive_split_metrics(
        self,
        *,
        partition_a: Sequence[str],
        partition_b: Sequence[str],
        affinity_rows: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        a=set(partition_a); b=set(partition_b); rows=[dict(r) for r in affinity_rows]
        within_a=[]; within_b=[]; cross=[]; seen=set()
        for row in rows:
            x=str(row.get("axis_a","")); y=str(row.get("axis_b","")); score=float(row.get("affinity",-1.0))
            if not x or not y or x==y or not (0.0<=score<=1.0): continue
            key=tuple(sorted((x,y))); seen.add(key)
            if x in a and y in a: within_a.append(score)
            elif x in b and y in b: within_b.append(score)
            elif (x in a and y in b) or (x in b and y in a): cross.append(score)
        def mean(v): return sum(v)/len(v) if v else 0.0
        expected_pairs=(len(a)*(len(a)-1)//2)+(len(b)*(len(b)-1)//2)+(len(a)*len(b))
        payload={
            "status":"DOMAIN_SPLIT_METRICS_DERIVED","within_a":mean(within_a),"within_b":mean(within_b),"cross":mean(cross),
            "pair_count":len(seen),"expected_pair_count":expected_pairs,"complete_pair_evidence":len(seen)==expected_pairs,
            "evidence_digest":digest_payload(rows),
        }
        return {**payload,"digest":digest_payload(payload)}

    def assess_split(
        self,
        *,
        parent_domain_id: str,
        partition_a: Sequence[str],
        partition_b: Sequence[str],
        affinity_rows: Sequence[Mapping[str, Any]],
        attestation: Mapping[str, Any],
        qualification_mode: bool = False,
    ) -> Mapping[str, Any]:
        if parent_domain_id not in DOMAIN_REGISTRIES:
            raise KeyError(parent_domain_id)
        current_axes = set(DOMAIN_REGISTRIES[parent_domain_id].axes)
        a, b = set(partition_a), set(partition_b)
        metrics=dict(self.derive_split_metrics(partition_a=partition_a, partition_b=partition_b, affinity_rows=affinity_rows))
        attestation_ok = attestation.get("world_ready") is True or (qualification_mode and attestation.get("qualification_ready") is True)
        checks = {
            "PARTITIONS_DISJOINT": not (a & b),
            "PARTITIONS_COVER_PARENT": a | b == current_axes,
            "NONEMPTY_CHILDREN": bool(a) and bool(b),
            "AFFINITY_METRICS_DERIVED_FROM_COMPLETE_EVIDENCE": metrics.get("complete_pair_evidence") is True,
            "WITHIN_COHERENCE_HIGH": min(float(metrics.get("within_a",0.0)), float(metrics.get("within_b",0.0))) >= 0.80,
            "CROSS_COHERENCE_LOW": float(metrics.get("cross",1.0)) <= 0.50,
            "ATTESTATION_READY": attestation_ok,
        }
        allowed = all(checks.values())
        payload = {
            "schema": "phi-domain-split-qualification/v1",
            "owner_id": self.owner_id,
            "parent_domain_id": parent_domain_id,
            "status": "DOMAIN_SPLIT_WARRANTED" if allowed else "DOMAIN_SPLIT_NOT_WARRANTED",
            "checks": checks,
            "split_allowed": allowed,
            "child_partitions": {"A": sorted(a), "B": sorted(b)},
            "metrics": metrics,
            "attestation_tier": "WORLD" if attestation.get("world_ready") else "QUALIFICATION_ONLY" if qualification_mode and attestation.get("qualification_ready") else "NONE",
            "qualification_mode": bool(qualification_mode),
            "canonical_parent_deleted": False,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def commit_split(
        self,
        receipt: Mapping[str, Any],
        *,
        manifest_dir: str | Path,
        state_path: str | Path,
        child_domain_ids: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        row = dict(receipt)
        expected = digest_payload({k: v for k, v in row.items() if k != "digest"})
        if row.get("digest") != expected or row.get("split_allowed") is not True:
            raise ValueError("unqualified domain split cannot be committed")
        if row.get("attestation_tier") not in {"WORLD", "QUALIFICATION_ONLY"}:
            raise ValueError("domain split lacks attestation tier")
        if row.get("attestation_tier") == "QUALIFICATION_ONLY" and row.get("qualification_mode") is not True:
            raise ValueError("qualification split cannot commit production manifests")
        parent = str(row["parent_domain_id"])
        registry = DOMAIN_REGISTRIES[parent]
        ids = tuple(child_domain_ids or (f"{parent}__part_a", f"{parent}__part_b"))
        if len(ids) != 2 or ids[0] == ids[1]:
            raise ValueError("split requires two distinct child domain ids")
        root = Path(manifest_dir); root.mkdir(parents=True, exist_ok=True)
        paths=[]
        try:
            for key, child_id in zip(("A", "B"), ids):
                axes=[]
                for axis_id in row["child_partitions"][key]:
                    axis=registry.axes[axis_id]
                    axes.append({
                        "axis_id": axis.axis_id, "description_ru": axis.description_ru,
                        "value_kind": axis.value_kind.value, "allowed_values": list(axis.allowed_values),
                        "required_for": list(axis.required_for), "forbidden_for": list(axis.forbidden_for),
                        "provenance": f"DOMAIN_SPLIT:{parent}:{axis.provenance}",
                    })
                manifest=self._manifest(str(child_id), f"Child domain of {parent} produced by qualified split", axes, registry.domain_role, f"DOMAIN_SPLIT:{row.get('digest')}")
                path=root/f"{child_id}.json"
                if path.exists(): raise FileExistsError(path)
                tmp=path.with_suffix('.json.tmp'); tmp.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)
                paths.append(path)
            loaded=load_domain_plugin_manifests(root)
            if not all(str(x) in loaded for x in ids): raise RuntimeError("split manifest reload validation failed")
        except Exception:
            for path in paths: path.unlink(missing_ok=True)
            raise
        tx={
            "schema":"phi-domain-transaction/v1","owner_id":self.owner_id,"transaction_type":"SPLIT",
            "parent_domain_id":parent,"child_domain_ids":list(ids),
            "status":"CANONICAL_CHILD_DOMAIN_MANIFESTS_COMMITTED" if row.get("attestation_tier")=="WORLD" else "QUALIFICATION_SANDBOX_CHILD_DOMAINS_COMMITTED",
            "parent_domain_deleted":False,"qualification_digest":row.get("digest"),"attestation_tier":row.get("attestation_tier"),
            "restart_required_for_global_registry_activation":True,
        }
        tx["digest"]=digest_payload(tx); _append_state(state_path,"domain_transactions",tx); return tx

    def derive_merge_predictive_equivalence(self, prediction_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        rows=[dict(r) for r in prediction_rows]; errors=[]; envs=[]
        for row in rows:
            a=[float(x) for x in row.get("domain_a_predictions",())]; b=[float(x) for x in row.get("domain_b_predictions",())]
            if not a or len(a)!=len(b): continue
            rmse=math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a))
            scale=max(math.sqrt(sum(x*x for x in a)/len(a)), math.sqrt(sum(y*y for y in b)/len(b)), 1e-12)
            errors.append(min(rmse/scale,1.0)); envs.append(str(row.get("environment_id","")))
        equivalence=1.0-(sum(errors)/len(errors) if errors else 1.0)
        payload={"status":"DOMAIN_MERGE_PREDICTIVE_EQUIVALENCE_DERIVED","predictive_equivalence":equivalence,"valid_environment_count":len(set(e for e in envs if e)),"evidence_digest":digest_payload(rows)}
        return {**payload,"digest":digest_payload(payload)}

    def assess_merge(
        self,
        *,
        domain_a: str,
        domain_b: str,
        bridge_coverage: float,
        prediction_rows: Sequence[Mapping[str, Any]],
        attestation: Mapping[str, Any],
        qualification_mode: bool = False,
    ) -> Mapping[str, Any]:
        predictive=dict(self.derive_merge_predictive_equivalence(prediction_rows))
        predictive_equivalence=float(predictive.get("predictive_equivalence",0.0))
        attestation_ok = attestation.get("world_ready") is True or (qualification_mode and attestation.get("qualification_ready") is True)
        checks = {
            "DOMAINS_EXIST": domain_a in DOMAIN_REGISTRIES and domain_b in DOMAIN_REGISTRIES and domain_a != domain_b,
            "BRIDGE_COVERAGE_HIGH": float(bridge_coverage) >= 0.90,
            "PREDICTIVE_EQUIVALENCE_DERIVED_IN_MULTIPLE_ENVIRONMENTS": int(predictive.get("valid_environment_count",0)) >= 2,
            "PREDICTIVE_EQUIVALENCE_HIGH": predictive_equivalence >= 0.95,
            "ATTESTATION_READY": attestation_ok,
        }
        allowed = all(checks.values())
        payload = {
            "schema": "phi-domain-merge-qualification/v1",
            "owner_id": self.owner_id,
            "domains": sorted([domain_a, domain_b]),
            "status": "NONDESTRUCTIVE_SUPERDOMAIN_MERGE_WARRANTED" if allowed else "DOMAIN_MERGE_NOT_WARRANTED",
            "checks": checks,
            "merge_allowed": allowed,
            "merge_policy": "CREATE_SUPERDOMAIN_PRESERVE_SOURCE_CANONICALS",
            "predictive_equivalence": predictive,
            "source_domains_deleted": False,
            "attestation_tier": "WORLD" if attestation.get("world_ready") else "QUALIFICATION_ONLY" if qualification_mode and attestation.get("qualification_ready") else "NONE",
            "qualification_mode": bool(qualification_mode),
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def commit_merge(
        self,
        receipt: Mapping[str, Any],
        *,
        merged_domain_id: str,
        manifest_dir: str | Path,
        state_path: str | Path,
    ) -> Mapping[str, Any]:
        row=dict(receipt)
        expected=digest_payload({k:v for k,v in row.items() if k!="digest"})
        if row.get("digest")!=expected or row.get("merge_allowed") is not True:
            raise ValueError("unqualified domain merge cannot be committed")
        if row.get("attestation_tier") not in {"WORLD","QUALIFICATION_ONLY"}:
            raise ValueError("domain merge lacks attestation tier")
        if row.get("attestation_tier")=="QUALIFICATION_ONLY" and row.get("qualification_mode") is not True:
            raise ValueError("qualification merge cannot commit production manifest")
        source_domains=tuple(row["domains"]); merged_domain_id=str(merged_domain_id).strip()
        if not merged_domain_id or merged_domain_id in DOMAIN_REGISTRIES: raise ValueError("merged domain id must be new")
        counts={}
        for d in source_domains:
            for axis_id in DOMAIN_REGISTRIES[d].axes: counts[axis_id]=counts.get(axis_id,0)+1
        axes=[]
        for d in source_domains:
            for axis_id,axis in sorted(DOMAIN_REGISTRIES[d].axes.items()):
                out_id=f"{d}__{axis_id}" if counts[axis_id]>1 else axis_id
                axes.append({
                    "axis_id":out_id,"description_ru":axis.description_ru,"value_kind":axis.value_kind.value,
                    "allowed_values":list(axis.allowed_values),"required_for":list(axis.required_for),"forbidden_for":list(axis.forbidden_for),
                    "provenance":f"NONDESTRUCTIVE_DOMAIN_MERGE:{d}.{axis_id}:{axis.provenance}",
                })
        manifest=self._manifest(merged_domain_id, f"Non-destructive superdomain over {', '.join(source_domains)}", axes, "cross_domain_superdomain", f"DOMAIN_MERGE:{row.get('digest')}")
        root=Path(manifest_dir); root.mkdir(parents=True,exist_ok=True); path=root/f"{merged_domain_id}.json"
        if path.exists(): raise FileExistsError(path)
        tmp=path.with_suffix('.json.tmp'); tmp.write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)
        loaded=load_domain_plugin_manifests(root)
        if merged_domain_id not in loaded:
            path.unlink(missing_ok=True); raise RuntimeError("merge manifest reload validation failed")
        tx={
            "schema":"phi-domain-transaction/v1","owner_id":self.owner_id,"transaction_type":"MERGE_SUPERDOMAIN",
            "source_domains":list(source_domains),"merged_domain_id":merged_domain_id,
            "status":"CANONICAL_SUPERDOMAIN_MANIFEST_COMMITTED" if row.get("attestation_tier")=="WORLD" else "QUALIFICATION_SANDBOX_SUPERDOMAIN_COMMITTED",
            "source_domains_deleted":False,"qualification_digest":row.get("digest"),"attestation_tier":row.get("attestation_tier"),
            "restart_required_for_global_registry_activation":True,
        }
        tx["digest"]=digest_payload(tx); _append_state(state_path,"domain_transactions",tx); return tx


class OwnerAxisBindingOwner:
    """Qualify forgotten owner→axis semantics without inventing a new law."""
    owner_id = OWNER_AXIS_BINDING_OWNER_ID
    _INTERNAL_SUPPORT_KINDS = {"SCIENTIFIC_COORDINATE", "FORMULA", "ASSUMPTION", "OBSERVABLE"}

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-owner-axis-binding/v1", "owner_id": self.owner_id,
            "rules": {
                "same_domain_required": True, "canonical_axis_required": True,
                "current_owner_digest_required": True, "internal_semantic_support_required": True,
                "binding_is_new_law_evidence": False, "binding_is_world_evidence": False,
                "binding_can_create_cross_domain_bridge": False, "unqualified_gap_remains_pending": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess(self, *, owner_id: str, owner_domain_id: str, owner_digest: str, axis_id: str,
               support_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        owner_id=str(owner_id).strip(); owner_domain_id=str(owner_domain_id).strip(); axis_id=str(axis_id).strip()
        fq = axis_id if "." in axis_id else (f"{owner_domain_id}.{axis_id}" if owner_domain_id and axis_id else axis_id)
        axis_domain, local_axis = fq.split(".",1) if "." in fq else ("","")
        registry=DOMAIN_REGISTRIES.get(owner_domain_id)
        rows=[dict(r) for r in support_rows if isinstance(r, Mapping)]
        internal=[r for r in rows if str(r.get("support_kind","")) in self._INTERNAL_SUPPORT_KINDS and bool(str(r.get("evidence","")).strip())]
        checks={
            "OWNER_ID":bool(owner_id), "OWNER_DOMAIN":owner_domain_id in DOMAIN_REGISTRIES,
            "OWNER_DIGEST":_sha256_hex(owner_digest), "SAME_DOMAIN":bool(axis_domain and axis_domain==owner_domain_id),
            "CANONICAL_AXIS":bool(registry and local_axis in registry.axes), "INTERNAL_SEMANTIC_SUPPORT":bool(internal),
        }
        qualified=all(checks.values())
        payload={
            "schema":"phi-owner-axis-binding-receipt/v1", "owner":self.owner_id, "owner_id":owner_id,
            "owner_domain_id":owner_domain_id, "owner_digest":str(owner_digest), "axis_id":fq,
            "support_rows":rows, "checks":checks,
            "status":"OWNER_AXIS_BINDING_QUALIFIED" if qualified else "OWNER_AXIS_BINDING_PENDING",
            "claim_boundary":{"new_law_established":False,"world_measurement_established":False,"novelty_established":False,"cross_domain_bridge_created":False},
        }
        return {**payload,"digest":digest_payload(payload)}

    def commit(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row=dict(receipt)
        if row.get("status") != "OWNER_AXIS_BINDING_QUALIFIED": raise ValueError("only qualified owner-axis bindings may be committed")
        if row.get("digest") != digest_payload({k:v for k,v in row.items() if k!="digest"}): raise ValueError("owner-axis binding receipt digest mismatch")
        state=_load_state(persist_path); values=list(state.get("owner_axis_bindings",()))
        key=(str(row.get("owner_id")),str(row.get("axis_id"))); replaced=False
        for i,old in enumerate(values):
            if (str(old.get("owner_id")),str(old.get("axis_id")))==key: values[i]=row; replaced=True; break
        if not replaced: values.append(row)
        state["owner_axis_bindings"]=sorted(values,key=lambda r:(str(r.get("owner_id")),str(r.get("axis_id"))))
        return _atomic_write_state(persist_path,state)


class CandidateWorldBindingOwner:
    """Bind a frozen candidate/hypothesis to a real ExperimentDataIR without promoting it.

    Binding is exact and fail-closed.  Canonical axes are instantiated only by
    source owners whose frozen scientific_coordinate contains that axis; dataset
    compatibility comes from exact provenance source-family identifiers; measurable
    overlap comes from exact canonical quantity_id values.  No fuzzy label matching
    is used and a successful data binding is not U5/world scientific evidence.
    """
    owner_id = CANDIDATE_WORLD_BINDING_OWNER_ID
    _NONDISCRIMINATING_QUANTITIES = {"QTY-DIMENSIONLESS"}

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-candidate-world-binding/v2",
            "owner_id": self.owner_id,
            "rules": {
                "candidate_and_hypothesis_digest_required": True,
                "experiment_data_ir_digest_required": True,
                "exact_axis_owner_coordinate_required": True,
                "exact_source_family_overlap_required": True,
                "exact_quantity_id_overlap_required": True,
                "fuzzy_text_matching_allowed": False,
                "response_projection_must_be_declared_by_experiment_data_ir": True,
                "response_projection_must_be_frozen_before_execution": True,
                "derived_response_execution_remains_in_domain_owner": True,
                "candidate_prediction_required_before_scientific_discrimination": True,
                "manual_prediction_lowering_must_be_digest_frozen_before_heldout_reveal": True,
                "manual_one_off_lowering_is_not_automatic_class_lowering": True,
                "heldout_refit_for_manual_prediction_example_allowed": False,
                "distinct_retry_lowering_for_same_candidate_requires_multiplicity_alpha_ledger": True,
                "retry_until_lucky_without_alpha_spending_allowed": False,
                "data_binding_is_world_measurement": False,
                "data_binding_is_u5_pass": False,
                "data_binding_is_new_law_evidence": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _valid_candidate(row: Mapping[str, Any]) -> bool:
        embedded = str(row.get("record_digest", ""))
        return _sha256_hex(embedded) and embedded == digest_payload({k: v for k, v in row.items() if k != "record_digest"})

    @staticmethod
    def _valid_hypothesis(row: Mapping[str, Any]) -> bool:
        embedded = str(row.get("digest", ""))
        return _sha256_hex(embedded) and embedded == digest_payload({k: v for k, v in row.items() if k != "digest"})

    @staticmethod
    def _valid_ir(row: Mapping[str, Any]) -> bool:
        embedded = str(row.get("digest", ""))
        return _sha256_hex(embedded) and embedded == digest_payload({k: v for k, v in row.items() if k != "digest"})

    def assess(
        self, *, root: str | Path, candidate: Mapping[str, Any], hypothesis: Mapping[str, Any],
        experiment_data_ir: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        from .runtime import LawSpaceRuntime

        c = dict(candidate); h = dict(hypothesis); ir = dict(experiment_data_ir)
        candidate_id = str(c.get("candidate_id", "")); dataset_id = str(ir.get("dataset_id", ""))
        checks = {
            "CANDIDATE_DIGEST": self._valid_candidate(c),
            "HYPOTHESIS_DIGEST": self._valid_hypothesis(h),
            "CANDIDATE_HYPOTHESIS_ID_MATCH": candidate_id != "" and candidate_id == str(h.get("candidate_id", "")),
            "EXPERIMENT_DATA_IR_DIGEST": self._valid_ir(ir),
            "EXPERIMENT_DATA_IR_READY": str(ir.get("status", "")) == "PASS_EXPERIMENT_DATA_IR",
            "FIELD_LEVEL_OBSERVABLE_CATALOG": str(ir.get("measurement_projection_status", "")) == "PASS_FIELD_LEVEL_OBSERVABLE_CATALOG",
        }
        axis_ids = tuple(str(x) for x in (c.get("payload", {}) or {}).get("axis_ids", ()))
        source_owner_ids = tuple(str(x) for x in c.get("source_owner_ids", ()))
        dataset_source_families = set(str(x) for x in ir.get("source_family_ids", ()))
        dataset_observables = [dict(x) for x in ir.get("observable_catalog", ()) if isinstance(x, Mapping) and x.get("available") is True]
        dataset_quantity_ids = {str(x.get("quantity_id")) for x in dataset_observables if str(x.get("quantity_id", ""))}

        runtime = LawSpaceRuntime(root)
        owner_rows: dict[str, Mapping[str, Any]] = {}
        for owner_id in source_owner_ids:
            passport = runtime.catalog.passports.get(owner_id)
            if passport is None:
                continue
            provenance = dict(passport.provenance or {})
            families = {str(x) for x in provenance.get("primary_source_ids", ())}
            quantity_ids = {str(sym.quantity_id) for sym in passport.symbols if getattr(sym, "quantity_id", None)}
            owner_rows[owner_id] = {
                "domain_id": passport.domain_id,
                "passport_digest": passport.digest,
                "scientific_coordinate": dict(passport.scientific_coordinate),
                "primary_source_ids": tuple(sorted(families)),
                "dataset_source_family_overlap": tuple(sorted(families & dataset_source_families)),
                "quantity_ids": tuple(sorted(quantity_ids)),
                "dataset_quantity_overlap": tuple(sorted((quantity_ids & dataset_quantity_ids) - self._NONDISCRIMINATING_QUANTITIES)),
            }

        axis_bindings: list[Mapping[str, Any]] = []
        uncovered_axes: list[str] = []
        for axis_id in axis_ids:
            if "." not in axis_id:
                uncovered_axes.append(axis_id); continue
            domain_id, local_axis = axis_id.split(".", 1)
            providers = []
            for owner_id, row in owner_rows.items():
                coord = dict(row.get("scientific_coordinate", {}))
                if row.get("domain_id") != domain_id or local_axis not in coord or coord.get(local_axis) in (None, "", (), [], {}):
                    continue
                providers.append({
                    "owner_id": owner_id,
                    "axis_id": axis_id,
                    "axis_value": coord.get(local_axis),
                    "passport_digest": row.get("passport_digest"),
                    "primary_source_ids": row.get("primary_source_ids"),
                    "dataset_source_family_overlap": row.get("dataset_source_family_overlap"),
                    "dataset_quantity_overlap": row.get("dataset_quantity_overlap"),
                    "dataset_compatible": bool(row.get("dataset_source_family_overlap")),
                })
            compatible = [row for row in providers if row.get("dataset_compatible") is True]
            if compatible:
                chosen = sorted(compatible, key=lambda row: (str(row.get("owner_id")), str(row.get("axis_value"))))[0]
                axis_bindings.append(chosen)
            else:
                uncovered_axes.append(axis_id)

        compatible_owners = [
            (owner_id, row) for owner_id, row in owner_rows.items()
            if row.get("dataset_source_family_overlap")
        ]
        shared_quantity_ids = sorted({
            q for _, row in compatible_owners for q in row.get("dataset_quantity_overlap", ())
        })
        quantity_bindings = []
        for quantity_id in shared_quantity_ids:
            owner_ids = sorted(owner_id for owner_id, row in compatible_owners if quantity_id in row.get("dataset_quantity_overlap", ()))
            observable_ids = sorted(str(row.get("observable_id")) for row in dataset_observables if row.get("quantity_id") == quantity_id)
            quantity_bindings.append({"quantity_id": quantity_id, "source_owner_ids": owner_ids, "observable_ids": observable_ids})

        checks.update({
            "ALL_CANDIDATE_AXES_INSTANTIATED_BY_DATASET_COMPATIBLE_OWNERS": bool(axis_ids) and not uncovered_axes,
            "SOURCE_FAMILY_OVERLAP": bool(compatible_owners),
            "MEASURABLE_QUANTITY_OVERLAP": bool(shared_quantity_ids),
            "MEASUREMENT_PROTOCOL_FROZEN": bool(str((h.get("measurement_contract", {}) or {}).get("protocol", "")).strip()),
        })
        response_projection_options = []
        compatible_owner_ids = {owner_id for owner_id, _ in compatible_owners}
        for projection0 in ir.get("response_projection_catalog", ()):
            if not isinstance(projection0, Mapping):
                continue
            projection = dict(projection0)
            required_inputs = {str(x) for x in projection.get("required_input_quantity_ids", ())}
            source_owner_id = str(projection.get("source_owner_id", ""))
            if source_owner_id not in compatible_owner_ids:
                continue
            if not required_inputs.issubset(dataset_quantity_ids):
                continue
            if projection.get("input_quantities_available") is not True:
                continue
            response_projection_options.append(projection)
        response_projection_options.sort(key=lambda row: str(row.get("response_projection_id", "")))
        checks["RESPONSE_PROJECTION_OPTION_AVAILABLE"] = bool(response_projection_options)
        # Binding alone never makes the experiment executable.  A separate
        # digest-bound precommit must select one declared response projection
        # before the derived response is evaluated by the domain owner.
        experiment_executable = False
        checks["FROZEN_RESPONSE_OBSERVABLE_PROJECTED"] = False

        structural = all(checks[k] for k in (
            "CANDIDATE_DIGEST", "HYPOTHESIS_DIGEST", "CANDIDATE_HYPOTHESIS_ID_MATCH",
            "EXPERIMENT_DATA_IR_DIGEST", "EXPERIMENT_DATA_IR_READY", "FIELD_LEVEL_OBSERVABLE_CATALOG",
        ))
        data_compatible = structural and checks["ALL_CANDIDATE_AXES_INSTANTIATED_BY_DATASET_COMPATIBLE_OWNERS"] and checks["SOURCE_FAMILY_OVERLAP"] and checks["MEASURABLE_QUANTITY_OVERLAP"] and checks["MEASUREMENT_PROTOCOL_FROZEN"]
        if not structural:
            status = "CANDIDATE_WORLD_BINDING_BLOCKED_INTEGRITY_OR_IR"
        elif not checks["SOURCE_FAMILY_OVERLAP"]:
            status = "CANDIDATE_WORLD_BINDING_BLOCKED_DATASET_SOURCE_FAMILY_MISMATCH"
        elif not checks["ALL_CANDIDATE_AXES_INSTANTIATED_BY_DATASET_COMPATIBLE_OWNERS"]:
            status = "CANDIDATE_WORLD_BINDING_BLOCKED_AXIS_CONTEXT_COVERAGE_GAP"
        elif not checks["MEASURABLE_QUANTITY_OVERLAP"]:
            status = "CANDIDATE_WORLD_BINDING_BLOCKED_MEASURABLE_QUANTITY_GAP"
        elif not checks["MEASUREMENT_PROTOCOL_FROZEN"]:
            status = "CANDIDATE_WORLD_BINDING_BLOCKED_MEASUREMENT_PROTOCOL_GAP"
        elif response_projection_options:
            status = "DATASET_BINDING_QUALIFIED_RESPONSE_PROJECTION_AVAILABLE"
        else:
            status = "DATASET_BINDING_QUALIFIED_EXPERIMENT_RESPONSE_PROJECTION_PENDING"

        payload = {
            "schema": "phi-candidate-world-binding-receipt/v2",
            "owner": self.owner_id,
            "candidate_id": candidate_id,
            "candidate_record_digest": c.get("record_digest"),
            "hypothesis_digest": h.get("digest"),
            "dataset_id": dataset_id,
            "experiment_data_ir_digest": ir.get("digest"),
            "dataset_domain": ir.get("domain"),
            "dataset_source_family_ids": tuple(sorted(dataset_source_families)),
            "axis_bindings": axis_bindings,
            "uncovered_axis_ids": tuple(sorted(uncovered_axes)),
            "quantity_bindings": quantity_bindings,
            "response_projection_options": response_projection_options,
            "checks": checks,
            "data_binding_qualified": bool(data_compatible),
            "experiment_executable": bool(experiment_executable),
            "status": status,
            "claim_boundary": {
                "world_measurement_established": False,
                "u5_passed": False,
                "new_law_established": False,
                "dataset_compatibility_is_hypothesis_confirmation": False,
                "published_dataset_parameter_is_new_measurement_result": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _valid_receipt(row: Mapping[str, Any]) -> bool:
        embedded = str(row.get("digest", ""))
        return _sha256_hex(embedded) and embedded == digest_payload({k: v for k, v in row.items() if k != "digest"})

    def freeze_response_projection(
        self, *, candidate: Mapping[str, Any], hypothesis: Mapping[str, Any],
        experiment_data_ir: Mapping[str, Any], binding_receipt: Mapping[str, Any],
        response_projection_id: str,
    ) -> Mapping[str, Any]:
        """Pre-freeze one exact derived response before executing the domain owner."""
        c = dict(candidate); h = dict(hypothesis); ir = dict(experiment_data_ir); binding = dict(binding_receipt)
        projection_id = str(response_projection_id).strip()
        options = [dict(row) for row in ir.get("response_projection_catalog", ()) if isinstance(row, Mapping)]
        projection = next((row for row in options if str(row.get("response_projection_id", "")) == projection_id), None)
        axis_owner_ids = {str(row.get("owner_id", "")) for row in binding.get("axis_bindings", ()) if isinstance(row, Mapping)}
        available_observables = [dict(row) for row in ir.get("observable_catalog", ()) if isinstance(row, Mapping) and row.get("available") is True]
        required_inputs = {str(x) for x in (projection or {}).get("required_input_quantity_ids", ())}
        input_rows = [row for row in available_observables if str(row.get("quantity_id", "")) in required_inputs]
        input_quantities = {str(row.get("quantity_id", "")) for row in input_rows}
        checks = {
            "CANDIDATE_DIGEST": self._valid_candidate(c),
            "HYPOTHESIS_DIGEST": self._valid_hypothesis(h),
            "EXPERIMENT_DATA_IR_DIGEST": self._valid_ir(ir),
            "BINDING_RECEIPT_DIGEST": self._valid_receipt(binding),
            "BINDING_QUALIFIED": binding.get("data_binding_qualified") is True,
            "CANDIDATE_CHAIN_MATCH": str(c.get("candidate_id", "")) == str(h.get("candidate_id", "")) == str(binding.get("candidate_id", "")),
            "HYPOTHESIS_CHAIN_MATCH": str(binding.get("hypothesis_digest", "")) == str(h.get("digest", "")),
            "IR_CHAIN_MATCH": str(binding.get("experiment_data_ir_digest", "")) == str(ir.get("digest", "")),
            "RESPONSE_PROJECTION_DECLARED": projection is not None,
            "PROJECTION_SOURCE_OWNER_BINDS_CANDIDATE_AXES": bool(projection) and str(projection.get("source_owner_id", "")) in axis_owner_ids,
            "REQUIRED_INPUT_QUANTITIES_AVAILABLE": bool(projection) and required_inputs == input_quantities,
            "PROJECTION_DESCRIPTOR_DIGEST_VALID": bool(projection) and str(projection.get("descriptor_digest", "")) == digest_payload({k: v for k, v in projection.items() if k not in {"descriptor_digest", "input_quantities_available"}}),
            "MEASUREMENT_PROTOCOL_FROZEN": bool(str((h.get("measurement_contract", {}) or {}).get("protocol", "")).strip()),
            "NO_RESPONSE_VALUE_OBSERVED_AT_FREEZE": bool(projection) and "response_value" not in projection,
        }
        qualified = all(checks.values())
        input_observable_ids = tuple(sorted(str(row.get("observable_id")) for row in input_rows))
        input_value_digests = {str(row.get("observable_id")): str(row.get("value_digest")) for row in input_rows}
        contract = {
            "schema": "phi-executable-measurement-contract/v1",
            "candidate_id": str(c.get("candidate_id", "")),
            "candidate_record_digest": c.get("record_digest"),
            "hypothesis_digest": h.get("digest"),
            "binding_receipt_digest": binding.get("digest"),
            "dataset_id": ir.get("dataset_id"),
            "experiment_data_ir_digest": ir.get("digest"),
            "response_projection_id": projection_id,
            "response_projection_descriptor_digest": (projection or {}).get("descriptor_digest"),
            "source_owner_id": (projection or {}).get("source_owner_id"),
            "execution_owner_id": (projection or {}).get("execution_owner_id"),
            "execution_operation": (projection or {}).get("execution_operation"),
            "response_quantity_id": (projection or {}).get("response_quantity_id"),
            "response_key": (projection or {}).get("response_key"),
            "input_observable_ids": input_observable_ids,
            "input_observable_value_digests": input_value_digests,
            "protocol": (h.get("measurement_contract", {}) or {}).get("protocol"),
            "required_controls": list((h.get("measurement_contract", {}) or {}).get("required_controls", ())),
            "freeze_before_execution": True,
        }
        contract["digest"] = digest_payload(contract)
        payload = {
            "schema": "phi-candidate-response-projection-receipt/v1",
            "owner": self.owner_id,
            "candidate_id": str(c.get("candidate_id", "")),
            "dataset_id": str(ir.get("dataset_id", "")),
            "response_projection_id": projection_id,
            "candidate_record_digest": c.get("record_digest"),
            "hypothesis_digest": h.get("digest"),
            "binding_receipt_digest": binding.get("digest"),
            "experiment_data_ir_digest": ir.get("digest"),
            "projection_descriptor": projection or {},
            "measurement_contract": contract,
            "checks": checks,
            "measurement_executable": bool(qualified),
            "scientific_discrimination_executable": False,
            "candidate_prediction_status": "PENDING_MECHANISM_TO_FORWARD_MODEL_LOWERING",
            "observed_response_value": None,
            "status": "FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING" if qualified else "CANDIDATE_RESPONSE_PROJECTION_BLOCKED",
            "claim_boundary": {
                "response_selected_before_execution": bool(qualified),
                "derived_response_already_observed": False,
                "candidate_specific_prediction_established": False,
                "world_attestation_established": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def execute_frozen_measurement(self, *, root: str | Path, projection_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        """Execute only a previously frozen measurement contract in its domain owner."""
        frozen = dict(projection_receipt)
        checks = {
            "PROJECTION_RECEIPT_DIGEST": self._valid_receipt(frozen),
            "PROJECTION_FROZEN": frozen.get("status") == "FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING",
            "MEASUREMENT_EXECUTABLE": frozen.get("measurement_executable") is True,
            "NO_RESPONSE_VALUE_IN_PRECOMMIT": frozen.get("observed_response_value") is None,
        }
        contract = dict(frozen.get("measurement_contract", {}) or {})
        embedded_contract_digest = str(contract.get("digest", ""))
        checks["MEASUREMENT_CONTRACT_DIGEST"] = _sha256_hex(embedded_contract_digest) and embedded_contract_digest == digest_payload({k: v for k, v in contract.items() if k != "digest"})
        from .scientific_data_ingestion import ScientificDataIngestionOwner
        ir = ScientificDataIngestionOwner(root).to_experiment_data_ir(str(contract.get("dataset_id", "")))
        checks["CURRENT_IR_MATCHES_FREEZE"] = str(ir.get("digest", "")) == str(contract.get("experiment_data_ir_digest", ""))
        if not all(checks.values()):
            payload = {
                "schema": "phi-candidate-measurement-execution-receipt/v1", "owner": self.owner_id,
                "candidate_id": frozen.get("candidate_id"), "dataset_id": frozen.get("dataset_id"),
                "response_projection_id": frozen.get("response_projection_id"), "projection_receipt_digest": frozen.get("digest"),
                "checks": checks, "measurement_executed": False, "status": "CANDIDATE_MEASUREMENT_EXECUTION_BLOCKED_PRECOMMIT_OR_IR_MISMATCH",
                "claim_boundary": {"world_attestation_established": False, "u5_passed": False, "new_law_established": False},
            }
            return {**payload, "digest": digest_payload(payload)}

        executor = (str(contract.get("execution_owner_id", "")), str(contract.get("execution_operation", "")))
        if executor == ("DAYA-BAY-FULL-LIKELIHOOD", "FIT_PUBLIC_DATA_PROFILE"):
            from .dayabay_full_likelihood import DayaBayFullLikelihoodOwner
            execution = dict(DayaBayFullLikelihoodOwner(root).fit_public_data_profile())
        else:
            payload = {
                "schema": "phi-candidate-measurement-execution-receipt/v1", "owner": self.owner_id,
                "candidate_id": frozen.get("candidate_id"), "dataset_id": frozen.get("dataset_id"),
                "response_projection_id": frozen.get("response_projection_id"), "projection_receipt_digest": frozen.get("digest"),
                "checks": {**checks, "EXECUTION_ADAPTER_SUPPORTED": False}, "measurement_executed": False,
                "status": "CANDIDATE_MEASUREMENT_EXECUTION_BLOCKED_UNSUPPORTED_DOMAIN_EXECUTOR",
                "claim_boundary": {"world_attestation_established": False, "u5_passed": False, "new_law_established": False},
            }
            return {**payload, "digest": digest_payload(payload)}

        response_key = str(contract.get("response_key", ""))
        value = execution.get(response_key)
        executable_status = str(execution.get("status", "")).startswith("PASS_") and isinstance(value, (int, float)) and math.isfinite(float(value))
        response = {
            "response_quantity_id": contract.get("response_quantity_id"),
            "response_key": response_key,
            "value": float(value) if executable_status else None,
            "unit": "1" if str(contract.get("response_quantity_id", "")) == "QTY-CHI-SQUARED" else "OWNER_DECLARED",
            "execution_owner_id": contract.get("execution_owner_id"),
            "execution_owner_result_digest": execution.get("digest"),
            "auxiliary": {k: execution.get(k) for k in ("ndf", "reduced_chi2") if k in execution},
        }
        response["value_digest"] = digest_payload(response)
        payload = {
            "schema": "phi-candidate-measurement-execution-receipt/v1",
            "owner": self.owner_id,
            "candidate_id": frozen.get("candidate_id"),
            "dataset_id": frozen.get("dataset_id"),
            "response_projection_id": frozen.get("response_projection_id"),
            "projection_receipt_digest": frozen.get("digest"),
            "measurement_contract_digest": contract.get("digest"),
            "experiment_data_ir_digest": ir.get("digest"),
            "checks": {**checks, "DOMAIN_OWNER_EXECUTION_PASS": executable_status},
            "response": response,
            "measurement_executed": bool(executable_status),
            "candidate_specific_prediction_used": False,
            "scientific_discrimination_executed": False,
            "status": "PASS_EXECUTABLE_MEASUREMENT_RESPONSE_ACQUIRED_CANDIDATE_DISCRIMINATION_PENDING" if executable_status else "CANDIDATE_MEASUREMENT_EXECUTION_BLOCKED_DOMAIN_OWNER",
            "claim_boundary": {
                "public_world_data_consumed": bool(executable_status),
                "retrospective_public_data_reanalysis": True,
                "candidate_specific_prediction_established": False,
                "world_attestation_established": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def freeze_manual_prediction_lowering(
        self, *, root: str | Path, candidate: Mapping[str, Any], hypothesis: Mapping[str, Any],
        binding_receipt: Mapping[str, Any], response_projection_receipt: Mapping[str, Any],
        lowering_contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Freeze one explicit candidate→ŷ mapping; do not generalize it to the class."""
        c = dict(candidate); h = dict(hypothesis); binding = dict(binding_receipt)
        projection = dict(response_projection_receipt); contract = dict(lowering_contract)
        existing_state = _load_state(_default_state_path(root))
        existing_lowerings = [
            dict(row) for row in existing_state.get("candidate_prediction_lowerings", ())
            if str(row.get("candidate_id", "")) == str(c.get("candidate_id", ""))
        ]
        same_contract_replay = any(str(row.get("lowering_contract_digest", "")) == str(contract.get("digest", "")) for row in existing_lowerings)
        distinct_retry = bool(existing_lowerings) and not same_contract_replay
        multiplicity = dict(contract.get("multiplicity_control", {}) or {})
        prior_debits = [float(x) for x in multiplicity.get("prior_attempt_alpha_debits", ()) if isinstance(x, (int, float))]
        family_alpha = float(multiplicity.get("family_alpha_budget", 0.0) or 0.0)
        allocated_alpha = float(multiplicity.get("allocated_alpha_this_attempt", 0.0) or 0.0)
        expected_attempt_index = len(existing_lowerings) + 1
        retry_alpha_ok = (
            not distinct_retry
            or (
                str(multiplicity.get("family_id", "")).strip() != ""
                and int(multiplicity.get("attempt_index", 0) or 0) == expected_attempt_index
                and len(prior_debits) == len(existing_lowerings)
                and all(x > 0.0 for x in prior_debits)
                and 0.0 < family_alpha <= 1.0
                and 0.0 < allocated_alpha <= family_alpha
                and sum(prior_debits) + allocated_alpha <= family_alpha + 1e-15
                and str(multiplicity.get("allocation_rule", "")).strip() != ""
            )
        )
        checks = {
            "CANDIDATE_DIGEST": self._valid_candidate(c),
            "HYPOTHESIS_DIGEST": self._valid_hypothesis(h),
            "BINDING_RECEIPT_DIGEST": self._valid_receipt(binding),
            "RESPONSE_PROJECTION_RECEIPT_DIGEST": self._valid_receipt(projection),
            "LOWERING_CONTRACT_DIGEST": self._valid_receipt(contract),
            "CHAIN_CANDIDATE_MATCH": str(c.get("candidate_id", "")) == str(h.get("candidate_id", "")) == str(binding.get("candidate_id", "")) == str(projection.get("candidate_id", "")) == str(contract.get("candidate_id", "")),
            "CHAIN_HYPOTHESIS_MATCH": str(h.get("digest", "")) == str(binding.get("hypothesis_digest", "")) == str(projection.get("hypothesis_digest", "")) == str(contract.get("hypothesis_digest", "")),
            "CHAIN_BINDING_MATCH": str(binding.get("digest", "")) == str(projection.get("binding_receipt_digest", "")) == str(contract.get("binding_receipt_digest", "")),
            "CHAIN_PROJECTION_MATCH": str(projection.get("digest", "")) == str(contract.get("response_projection_receipt_digest", "")),
            "DATA_BINDING_QUALIFIED": binding.get("data_binding_qualified") is True,
            "RESPONSE_PROJECTION_FROZEN": projection.get("status") == "FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING",
            "ONE_OFF_MANUAL_MODE": contract.get("scope") == "ONE_CANDIDATE_ONE_MANUAL_LOWERING_NOT_GENERALIZED",
            "NO_HELDOUT_REFIT": contract.get("heldout_refit_allowed") is False,
            "NO_OBSERVED_HELDOUT_RESULT_IN_CONTRACT": all(k not in contract for k in ("heldout_chi2", "heldout_reduced_chi2", "collapse_result", "observed_counts")),
            "DISTINCT_RETRY_ALPHA_LEDGER": retry_alpha_ok,
        }
        if not all(checks.values()):
            payload = {
                "schema": "phi-candidate-manual-prediction-lowering/v1", "owner": self.owner_id,
                "candidate_id": c.get("candidate_id"), "checks": checks,
                "status": "CANDIDATE_MANUAL_PREDICTION_LOWERING_BLOCKED_PRECOMMIT",
                "claim_boundary": {"u5_passed": False, "new_law_established": False},
            }
            return {**payload, "digest": digest_payload(payload)}
        operation = str(contract.get("lowering_operation", ""))
        if operation != "DAYABAY_CNP_DISCOVERY_TO_HELDOUT_COUNT_VECTOR":
            payload = {
                "schema": "phi-candidate-manual-prediction-lowering/v1", "owner": self.owner_id,
                "candidate_id": c.get("candidate_id"), "checks": {**checks, "SUPPORTED_MANUAL_ADAPTER": False},
                "status": "CANDIDATE_MANUAL_PREDICTION_LOWERING_BLOCKED_UNSUPPORTED_ADAPTER",
                "claim_boundary": {"u5_passed": False, "new_law_established": False},
            }
            return {**payload, "digest": digest_payload(payload)}
        from .dayabay_full_likelihood import DayaBayFullLikelihoodOwner
        domain_receipt = dict(DayaBayFullLikelihoodOwner(root).freeze_manual_metrology_prediction(contract))
        qualified = domain_receipt.get("status") == "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED"
        payload = {
            "schema": "phi-candidate-manual-prediction-lowering/v1",
            "owner": self.owner_id,
            "candidate_id": c.get("candidate_id"),
            "candidate_record_digest": c.get("record_digest"),
            "hypothesis_digest": h.get("digest"),
            "binding_receipt_digest": binding.get("digest"),
            "response_projection_receipt_digest": projection.get("digest"),
            "lowering_contract": contract,
            "lowering_contract_digest": contract.get("digest"),
            "retry_multiplicity_audit": {
                "existing_attempt_count_before_freeze": len(existing_lowerings),
                "same_contract_replay": same_contract_replay,
                "distinct_retry": distinct_retry,
                "alpha_ledger_required": distinct_retry,
                "alpha_ledger_pass": retry_alpha_ok,
                "multiplicity_control": multiplicity if distinct_retry else {},
            },
            "checks": {**checks, "DOMAIN_PREDICTION_FREEZE_PASS": qualified},
            "domain_prediction_freeze": domain_receipt,
            "candidate_specific_prediction_frozen": bool(qualified),
            "heldout_revealed": False,
            "status": "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED" if qualified else "CANDIDATE_MANUAL_PREDICTION_LOWERING_BLOCKED_DOMAIN_OWNER",
            "claim_boundary": {
                "manual_one_off_lowering": True,
                "automatic_class_lowering_established": False,
                "retry_until_lucky_without_alpha_spending_allowed": False,
                "candidate_specific_prediction_established": bool(qualified),
                "independent_world_attestation_established": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def execute_manual_prediction_discrimination(self, *, root: str | Path, lowering_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        """Reveal held-out target data only after a committed manual prediction freeze."""
        frozen = dict(lowering_receipt)
        checks = {
            "LOWERING_RECEIPT_DIGEST": self._valid_receipt(frozen),
            "LOWERING_FROZEN": frozen.get("status") == "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED",
            "CANDIDATE_SPECIFIC_PREDICTION_FROZEN": frozen.get("candidate_specific_prediction_frozen") is True,
            "HELDOUT_NOT_REVEALED_AT_FREEZE": frozen.get("heldout_revealed") is False,
        }
        if not all(checks.values()):
            payload = {
                "schema": "phi-candidate-manual-prediction-discrimination/v1", "owner": self.owner_id,
                "candidate_id": frozen.get("candidate_id"), "lowering_receipt_digest": frozen.get("digest"),
                "checks": checks, "status": "CANDIDATE_MANUAL_PREDICTION_DISCRIMINATION_BLOCKED_PRECOMMIT",
                "claim_boundary": {"u5_passed": False, "new_law_established": False},
            }
            return {**payload, "digest": digest_payload(payload)}
        from .dayabay_full_likelihood import DayaBayFullLikelihoodOwner
        domain = dict(DayaBayFullLikelihoodOwner(root).score_frozen_manual_metrology_prediction(frozen.get("domain_prediction_freeze", {})))
        executed = str(domain.get("status", "")).endswith("MANUAL_CANDIDATE_PREDICTION_COLLAPSE_DIAGNOSTIC")
        payload = {
            "schema": "phi-candidate-manual-prediction-discrimination/v1",
            "owner": self.owner_id,
            "candidate_id": frozen.get("candidate_id"),
            "lowering_receipt_digest": frozen.get("digest"),
            "lowering_contract_digest": frozen.get("lowering_contract_digest"),
            "checks": {**checks, "DOMAIN_HELDOUT_EXECUTION_COMPLETED": bool(executed)},
            "domain_discrimination_receipt": domain,
            "candidate_specific_prediction_used": bool(executed),
            "heldout_prediction_check_executed": bool(executed),
            "scientific_discrimination_executed": False,
            "status": "PASS_MANUAL_CANDIDATE_PREDICTION_HELDOUT_CHECK_EXECUTED" if executed else "CANDIDATE_MANUAL_PREDICTION_HELDOUT_CHECK_BLOCKED",
            "claim_boundary": {
                "candidate_specific_prediction_exists_for_one_manual_example": bool(executed),
                "collapse_diagnostic_result_is_world_attestation": False,
                "retrospective_public_data_is_prospective_replication": False,
                "automatic_lowering_generalized": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def commit_prediction_lowering(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        if row.get("status") != "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED" or row.get("candidate_specific_prediction_frozen") is not True:
            raise ValueError("only frozen manual candidate predictions may be committed")
        if not self._valid_receipt(row):
            raise ValueError("manual candidate prediction lowering receipt digest mismatch")
        state = _load_state(persist_path)
        values = list(state.get("candidate_prediction_lowerings", ()))
        key = (str(row.get("candidate_id")), str(row.get("lowering_contract_digest")))
        values = [old for old in values if (str(old.get("candidate_id")), str(old.get("lowering_contract_digest"))) != key]
        values.append(row)
        state["candidate_prediction_lowerings"] = sorted(values, key=lambda r: (str(r.get("candidate_id")), str(r.get("lowering_contract_digest"))))
        return _atomic_write_state(persist_path, state)

    def commit_prediction_discrimination(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        if row.get("status") != "PASS_MANUAL_CANDIDATE_PREDICTION_HELDOUT_CHECK_EXECUTED" or row.get("heldout_prediction_check_executed") is not True:
            raise ValueError("only executed manual held-out prediction checks may be committed")
        if not self._valid_receipt(row):
            raise ValueError("manual prediction discrimination receipt digest mismatch")
        state = _load_state(persist_path)
        lowerings = list(state.get("candidate_prediction_lowerings", ()))
        if not any(str(old.get("digest")) == str(row.get("lowering_receipt_digest")) for old in lowerings):
            raise ValueError("manual held-out discrimination must reference a committed prediction lowering")
        values = list(state.get("candidate_prediction_discriminations", ()))
        key = (str(row.get("candidate_id")), str(row.get("lowering_contract_digest")))
        values = [old for old in values if (str(old.get("candidate_id")), str(old.get("lowering_contract_digest"))) != key]
        values.append(row)
        state["candidate_prediction_discriminations"] = sorted(values, key=lambda r: (str(r.get("candidate_id")), str(r.get("lowering_contract_digest"))))
        return _atomic_write_state(persist_path, state)

    def commit_response_projection(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        if row.get("status") != "FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING" or row.get("measurement_executable") is not True:
            raise ValueError("only qualified frozen response projections may be committed")
        if not self._valid_receipt(row):
            raise ValueError("candidate response projection receipt digest mismatch")
        state = _load_state(persist_path)
        values = list(state.get("candidate_response_projections", ()))
        key = (str(row.get("candidate_id")), str(row.get("dataset_id")), str(row.get("response_projection_id")))
        values = [old for old in values if (str(old.get("candidate_id")), str(old.get("dataset_id")), str(old.get("response_projection_id"))) != key]
        values.append(row)
        state["candidate_response_projections"] = sorted(values, key=lambda r: (str(r.get("candidate_id")), str(r.get("dataset_id")), str(r.get("response_projection_id"))))
        return _atomic_write_state(persist_path, state)

    def commit_measurement_execution(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        if row.get("status") != "PASS_EXECUTABLE_MEASUREMENT_RESPONSE_ACQUIRED_CANDIDATE_DISCRIMINATION_PENDING" or row.get("measurement_executed") is not True:
            raise ValueError("only successful executable measurement receipts may be committed")
        if not self._valid_receipt(row):
            raise ValueError("candidate measurement execution receipt digest mismatch")
        state = _load_state(persist_path)
        projections = list(state.get("candidate_response_projections", ()))
        if not any(str(p.get("digest")) == str(row.get("projection_receipt_digest")) for p in projections):
            raise ValueError("measurement execution must reference a committed frozen response projection")
        values = list(state.get("candidate_measurement_executions", ()))
        key = (str(row.get("candidate_id")), str(row.get("dataset_id")), str(row.get("response_projection_id")))
        values = [old for old in values if (str(old.get("candidate_id")), str(old.get("dataset_id")), str(old.get("response_projection_id"))) != key]
        values.append(row)
        state["candidate_measurement_executions"] = sorted(values, key=lambda r: (str(r.get("candidate_id")), str(r.get("dataset_id")), str(r.get("response_projection_id"))))
        return _atomic_write_state(persist_path, state)

    def commit(self, receipt: Mapping[str, Any], *, persist_path: str | Path) -> Mapping[str, Any]:
        row = dict(receipt)
        embedded = str(row.get("digest", ""))
        if not _sha256_hex(embedded) or embedded != digest_payload({k: v for k, v in row.items() if k != "digest"}):
            raise ValueError("candidate-world binding receipt digest mismatch")
        if str(row.get("owner")) != self.owner_id or not str(row.get("candidate_id", "")) or not str(row.get("dataset_id", "")):
            raise ValueError("candidate-world binding receipt identity incomplete")
        state = _load_state(persist_path)
        values = list(state.get("candidate_world_bindings", ()))
        key = (str(row.get("candidate_id")), str(row.get("dataset_id")))
        values = [old for old in values if (str(old.get("candidate_id")), str(old.get("dataset_id"))) != key]
        values.append(row)
        state["candidate_world_bindings"] = sorted(values, key=lambda r: (str(r.get("candidate_id")), str(r.get("dataset_id"))))
        return _atomic_write_state(persist_path, state)


class KnowledgeEvolutionKernel:
    owner_id = KERNEL_OWNER_ID

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2])
        self.state_path = _default_state_path(self.root)
        self.world = WorldAttestationOwner()
        self.axis_lifecycle = AxisLifecycleOwner()
        self.domain_ontogenesis = DomainOntogenesisOwner()
        self.bridge = CrossDomainBridgeOwner()
        self.owner_axis_binding = OwnerAxisBindingOwner()
        self.candidate_world_binding = CandidateWorldBindingOwner()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "owners": {
                "world_attestation": self.world.contract(),
                "axis_lifecycle": self.axis_lifecycle.contract(),
                "domain_ontogenesis": self.domain_ontogenesis.contract(),
                "cross_domain_bridge": self.bridge.contract(),
                "owner_axis_binding": self.owner_axis_binding.contract(),
                "candidate_world_binding": self.candidate_world_binding.contract(),
            },
            "dependency_chain": [
                "SCIENTIFIC-VERIFICATION-CORE/8.0.0",
                "owner-connected Φ-space scan",
                WORLD_ATTESTATION_OWNER_ID,
                AXIS_LIFECYCLE_OWNER_ID,
                DOMAIN_ONTOGENESIS_OWNER_ID,
                CROSS_DOMAIN_BRIDGE_OWNER_ID,
                OWNER_AXIS_BINDING_OWNER_ID,
                CANDIDATE_WORLD_BINDING_OWNER_ID,
            ],
            "claim_boundary": {
                "internet_is_prefreeze_solution_selector": False,
                "qualification_fixture_is_world_attestation": False,
                "domain_birth_without_world_attestation_allowed_in_production": False,
                "bridge_merges_canonical_axes": False,
                "owner_axis_binding_is_new_law_evidence": False,
                "candidate_world_binding_is_u5_or_new_law_evidence": False,
                "executable_measurement_response_without_candidate_prediction_is_u5": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_candidate_world_binding(self, *, candidate_id: str, dataset_id: str) -> Mapping[str, Any]:
        """Assess one persisted candidate against one typed ExperimentDataIR.

        This is deliberately a read-only diagnostic.  It never creates candidates,
        never selects a response post hoc, and never promotes U5.
        """
        candidate_id = str(candidate_id).strip(); dataset_id = str(dataset_id).strip()
        if not candidate_id or not dataset_id:
            raise ValueError("candidate_id and dataset_id are required")
        ledger_path = self.root / "data" / "frontiers" / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
        candidate = None
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if str(row.get("candidate_id", "")) == candidate_id:
                    candidate = row; break
        if candidate is None:
            raise KeyError(f"candidate not found in authoritative frontier ledger: {candidate_id}")
        state = _load_state(self.state_path)
        hypothesis = next((dict(row) for row in state.get("hypothesis_materializations", ()) if str(row.get("candidate_id", "")) == candidate_id), None)
        if hypothesis is None:
            raise KeyError(f"typed hypothesis not materialized for candidate: {candidate_id}")
        from .scientific_data_ingestion import ScientificDataIngestionOwner
        experiment_ir = ScientificDataIngestionOwner(self.root).to_experiment_data_ir(dataset_id)
        return self.candidate_world_binding.assess(root=self.root, candidate=candidate, hypothesis=hypothesis, experiment_data_ir=experiment_ir)

    def commit_candidate_world_binding(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        """Persist an integrity-checked binding receipt without changing promotion status."""
        return self.candidate_world_binding.commit(receipt, persist_path=self.state_path)

    def assess_candidate_response_projection(self, *, candidate_id: str, dataset_id: str, response_projection_id: str) -> Mapping[str, Any]:
        """Build a response precommit only from a current persisted data-binding receipt."""
        candidate_id = str(candidate_id).strip(); dataset_id = str(dataset_id).strip(); response_projection_id = str(response_projection_id).strip()
        ledger_path = self.root / "data" / "frontiers" / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
        candidate = None
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    if str(row.get("candidate_id", "")) == candidate_id:
                        candidate = row; break
        if candidate is None:
            raise KeyError(f"candidate not found in authoritative frontier ledger: {candidate_id}")
        state = _load_state(self.state_path)
        hypothesis = next((dict(row) for row in state.get("hypothesis_materializations", ()) if str(row.get("candidate_id", "")) == candidate_id), None)
        binding = next((dict(row) for row in state.get("candidate_world_bindings", ()) if str(row.get("candidate_id", "")) == candidate_id and str(row.get("dataset_id", "")) == dataset_id), None)
        if hypothesis is None:
            raise KeyError(f"typed hypothesis not materialized for candidate: {candidate_id}")
        if binding is None:
            raise KeyError(f"candidate-world binding must be committed before response freeze: {candidate_id} / {dataset_id}")
        from .scientific_data_ingestion import ScientificDataIngestionOwner
        ir = ScientificDataIngestionOwner(self.root).to_experiment_data_ir(dataset_id)
        current_binding = self.candidate_world_binding.assess(root=self.root, candidate=candidate, hypothesis=hypothesis, experiment_data_ir=ir)
        if str(current_binding.get("digest", "")) != str(binding.get("digest", "")):
            raise ValueError("persisted candidate-world binding is stale relative to current candidate/hypothesis/ExperimentDataIR")
        return self.candidate_world_binding.freeze_response_projection(
            candidate=candidate, hypothesis=hypothesis, experiment_data_ir=ir,
            binding_receipt=binding, response_projection_id=response_projection_id,
        )

    def commit_candidate_response_projection(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.candidate_world_binding.commit_response_projection(receipt, persist_path=self.state_path)

    def execute_candidate_measurement(self, *, candidate_id: str, dataset_id: str, response_projection_id: str) -> Mapping[str, Any]:
        """Execute and persist exactly one already-committed response projection."""
        state = _load_state(self.state_path)
        projection = next((dict(row) for row in state.get("candidate_response_projections", ()) if str(row.get("candidate_id", "")) == str(candidate_id) and str(row.get("dataset_id", "")) == str(dataset_id) and str(row.get("response_projection_id", "")) == str(response_projection_id)), None)
        if projection is None:
            raise KeyError("frozen candidate response projection not found")
        receipt = self.candidate_world_binding.execute_frozen_measurement(root=self.root, projection_receipt=projection)
        if receipt.get("measurement_executed") is True:
            self.candidate_world_binding.commit_measurement_execution(receipt, persist_path=self.state_path)
        return receipt

    def assess_manual_candidate_prediction_lowering(self, *, candidate_id: str, lowering_contract: Mapping[str, Any]) -> Mapping[str, Any]:
        """Freeze one manually supplied lowering contract for the already-bound candidate."""
        candidate_id = str(candidate_id).strip(); contract = dict(lowering_contract)
        ledger_path = self.root / "data" / "frontiers" / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
        candidate = None
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    if str(row.get("candidate_id", "")) == candidate_id:
                        candidate = row; break
        if candidate is None:
            raise KeyError(f"candidate not found in authoritative frontier ledger: {candidate_id}")
        state = _load_state(self.state_path)
        hypothesis = next((dict(row) for row in state.get("hypothesis_materializations", ()) if str(row.get("candidate_id", "")) == candidate_id), None)
        binding = next((dict(row) for row in state.get("candidate_world_bindings", ()) if str(row.get("candidate_id", "")) == candidate_id and row.get("data_binding_qualified") is True), None)
        projection = next((dict(row) for row in state.get("candidate_response_projections", ()) if str(row.get("candidate_id", "")) == candidate_id and row.get("measurement_executable") is True), None)
        if hypothesis is None or binding is None or projection is None:
            raise KeyError("manual lowering requires existing typed hypothesis, qualified data binding and frozen response projection")
        return self.candidate_world_binding.freeze_manual_prediction_lowering(
            root=self.root, candidate=candidate, hypothesis=hypothesis, binding_receipt=binding,
            response_projection_receipt=projection, lowering_contract=contract,
        )

    def commit_manual_candidate_prediction_lowering(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.candidate_world_binding.commit_prediction_lowering(receipt, persist_path=self.state_path)

    def execute_manual_candidate_prediction_discrimination(self, *, candidate_id: str, lowering_contract_digest: str) -> Mapping[str, Any]:
        state = _load_state(self.state_path)
        frozen = next((dict(row) for row in state.get("candidate_prediction_lowerings", ()) if str(row.get("candidate_id", "")) == str(candidate_id) and str(row.get("lowering_contract_digest", "")) == str(lowering_contract_digest)), None)
        if frozen is None:
            raise KeyError("committed manual candidate prediction lowering not found")
        receipt = self.candidate_world_binding.execute_manual_prediction_discrimination(root=self.root, lowering_receipt=frozen)
        if receipt.get("heldout_prediction_check_executed") is True:
            self.candidate_world_binding.commit_prediction_discrimination(receipt, persist_path=self.state_path)
        return receipt

    def commit_hypothesis_materialization(self, hypothesis: Mapping[str, Any]) -> Mapping[str, Any]:
        row=dict(hypothesis)
        if row.get("status") != "TYPED_RELATIONAL_HYPOTHESIS_MATERIALIZED": raise ValueError("only materialized typed relational hypotheses may be persisted")
        embedded=str(row.get("digest",""))
        if not _sha256_hex(embedded) or embedded != digest_payload({k:v for k,v in row.items() if k!="digest"}): raise ValueError("hypothesis materialization digest mismatch")
        state=_load_state(self.state_path); rows=list(state.get("hypothesis_materializations",()))
        cid=str(row.get("candidate_id","")); rows=[old for old in rows if str(old.get("candidate_id",""))!=cid]; rows.append(row)
        state["hypothesis_materializations"]=sorted(rows,key=lambda r:str(r.get("candidate_id","")))
        return _atomic_write_state(self.state_path,state)

    def state(self) -> Mapping[str, Any]:
        return _load_state(self.state_path)


__all__ = [
    "KERNEL_OWNER_ID", "WORLD_ATTESTATION_OWNER_ID", "AXIS_LIFECYCLE_OWNER_ID",
    "DOMAIN_ONTOGENESIS_OWNER_ID", "CROSS_DOMAIN_BRIDGE_OWNER_ID", "OWNER_AXIS_BINDING_OWNER_ID", "CANDIDATE_WORLD_BINDING_OWNER_ID",
    "WorldAttestationOwner", "AxisLifecycleOwner", "DomainOntogenesisOwner",
    "CrossDomainBridgeOwner", "OwnerAxisBindingOwner", "CandidateWorldBindingOwner", "KnowledgeEvolutionKernel",
]
