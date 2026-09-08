"""Read-only bridge from ScienceAtlas AI to a real Φ-Compiler/ScienceAtlas distribution.

The external Atlas remains authoritative for its law passports, domain registries
and service owners.  This module does not copy or reinterpret Atlas laws.  It
mounts deterministic contracts into the AI OwnerBus and delegates selected
service calls to the real source tree.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import sys
import itertools
from pathlib import Path
from enum import Enum
from typing import Any, Mapping, Sequence

from .owners import OwnerBus, OwnerSpec
from .provenance import digest_json


BRIDGE_SCHEMA = "scienceatlas-ai-real-atlas-mount/v1"


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _plain(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(v) for v in value]
    if isinstance(value, Enum):
        return _plain(value.value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _manifest_identity(root: Path) -> dict[str, Any]:
    path = root / "RELEASE_MANIFEST.json"
    if not path.is_file():
        raise FileNotFoundError(f"ScienceAtlas release manifest missing: {path}")
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return {
        "release": str(payload.get("release", "UNKNOWN")),
        "status": str(payload.get("status", "UNKNOWN")),
        "schema": str(payload.get("schema", "UNKNOWN")),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "controlled_file_count": int(payload.get("controlled_file_count", 0)),
    }


def _knowledge_evolution_overlay(root: Path) -> dict[str, Any]:
    """Read qualified Atlas Knowledge-Evolution bindings without inventing routes.

    These receipts are semantic owner<->axis attestations already qualified by
    Atlas.  They are exposed to the AI as read-only context only.  They do NOT
    become exact quantity/unit/dimension symbol bindings and do NOT authorize a
    cross-domain bridge.
    """
    path = root / "data" / "knowledge" / "knowledge_evolution_state.json"
    if not path.is_file():
        return {"state_digest": "", "owner_axis_bindings": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for raw in payload.get("owner_axis_bindings", ()):
        row = dict(raw)
        checks = dict(row.get("checks", {}) or {})
        boundary = dict(row.get("claim_boundary", {}) or {})
        if str(row.get("status")) != "OWNER_AXIS_BINDING_QUALIFIED":
            continue
        if not all(bool(checks.get(k)) for k in ("CANONICAL_AXIS", "OWNER_ID", "OWNER_DIGEST", "OWNER_DOMAIN", "SAME_DOMAIN", "INTERNAL_SEMANTIC_SUPPORT")):
            continue
        if bool(boundary.get("cross_domain_bridge_created", False)):
            # A binding receipt is not the authority for cross-domain bridges.
            continue
        rows.append({
            "axis_id": str(row.get("axis_id", "")),
            "owner_id": str(row.get("owner_id", "")),
            "owner_domain_id": str(row.get("owner_domain_id", "")),
            "owner_digest": str(row.get("owner_digest", "")),
            "binding_digest": str(row.get("digest", "")),
            "status": str(row.get("status", "")),
            "support_rows": _plain(row.get("support_rows", [])),
            "claim_boundary": {
                "cross_domain_bridge_created": False,
                "new_law_established": bool(boundary.get("new_law_established", False)),
                "world_measurement_established": bool(boundary.get("world_measurement_established", False)),
            },
        })
    rows.sort(key=lambda r: (r["axis_id"], r["owner_id"], r["binding_digest"]))
    return {
        "state_digest": str(payload.get("digest", "")),
        "owner_axis_bindings": rows,
        "overlay_digest": digest_json(rows, namespace=b"SCIENCEATLAS_AI_QUALIFIED_OWNER_AXIS_OVERLAY_V1"),
    }


def _ensure_real_atlas_import(root: Path) -> None:
    runtime_file = root / "source" / "lawspace" / "runtime.py"
    if not runtime_file.is_file():
        raise FileNotFoundError(f"not a ScienceAtlas distribution root: {root}")
    root_s = str(root.resolve())
    loaded = sys.modules.get("source.lawspace.runtime")
    if loaded is not None:
        loaded_file = Path(str(getattr(loaded, "__file__", ""))).resolve()
        try:
            loaded_file.relative_to(root.resolve())
        except ValueError as exc:
            raise RuntimeError(
                "a different ScienceAtlas source tree is already imported; "
                "refusing cross-release module aliasing in one process"
            ) from exc
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    importlib.invalidate_caches()


def _passport_payload(passport: Any) -> dict[str, Any]:
    return _plain(dataclasses.asdict(passport))


class AtlasPassportProxy:
    """Read-only executable contract for one real canonical Atlas law passport."""

    def __init__(self, passport: Any) -> None:
        self._passport = passport
        self.spec = OwnerSpec(
            owner_id=str(passport.owner_id),
            capability=f"atlas.passport::{passport.owner_id}",
            input_types=("passport_query",),
            output_types=("canonical_law_passport",),
            validity_domain=str(passport.validity_domain or "declared_by_atlas_passport"),
            uncertainty_contract=str(passport.uncertainty_model or "NOT_DECLARED"),
            cost_model="read_only_registry_lookup",
            deterministic=True,
            replayable=True,
            falsification_contract="delegated_to_canonical_atlas_passport_and_its_evidence_contract",
            owner_kind="atlas_law_passport",
        )

    def invoke(self, *, action: str = "get") -> Mapping[str, Any]:
        if action not in {"get", "contract"}:
            raise ValueError(f"unsupported passport proxy action: {action}")
        return _passport_payload(self._passport)


class AtlasCatalogService:
    def __init__(self, atlas_runtime: Any, release: str) -> None:
        self._runtime = atlas_runtime
        self.spec = OwnerSpec(
            owner_id="ATLAS-LAW-CATALOG-BRIDGE/1.0.0",
            capability="atlas.registry.catalog",
            input_types=("catalog_query",),
            output_types=("law_passport_set",),
            validity_domain=f"mounted ScienceAtlas release {release}",
            uncertainty_contract="preserve_passport_epistemic_state_and_uncertainty_model",
            cost_model="catalog_lookup",
            deterministic=True,
            replayable=True,
            falsification_contract="result owner_ids and catalog digest must replay against mounted release",
            owner_kind="atlas_registry_service",
        )

    def invoke(
        self,
        *,
        action: str = "summary",
        owner_id: str | None = None,
        query: str = "",
        domain_id: str | None = None,
        limit: int = 20,
    ) -> Mapping[str, Any]:
        catalog = self._runtime.catalog
        if action == "summary":
            return {
                "owner_count": len(catalog.passports),
                "catalog_digest": catalog.digest(),
                "domains": sorted({p.domain_id for p in catalog.passports.values()}),
            }
        if action == "get":
            if not owner_id:
                raise ValueError("owner_id is required for catalog get")
            return _passport_payload(catalog.get_passport(owner_id))
        if action == "search":
            rows = catalog.search(query, domain_id=domain_id, limit=limit)
            return {
                "query": query,
                "domain_id": domain_id,
                "count": len(rows),
                "owner_ids": [p.owner_id for p in rows],
                "passports": [_passport_payload(p) for p in rows],
            }
        raise ValueError(f"unsupported catalog action: {action}")


class AtlasDomainBridgeService:
    """Read-only registry of Atlas cross-domain bridge contracts."""

    def __init__(self, atlas_runtime: Any, release: str) -> None:
        self._runtime = atlas_runtime
        self.spec = OwnerSpec(
            owner_id="ATLAS-DOMAIN-BRIDGE-REGISTRY/1.0.0",
            capability="atlas.registry.domain_bridges",
            input_types=("domain_bridge_query",),
            output_types=("typed_domain_bridge_contract_set",),
            validity_domain=f"mounted ScienceAtlas release {release}",
            uncertainty_contract="bridge only authorizes its declared domains/mapping/dimensional contract; no structural-similarity inference",
            cost_model="registry_lookup",
            deterministic=True,
            replayable=True,
            falsification_contract="bridge contract must replay exactly from mounted Atlas release",
            owner_kind="atlas_registry_service",
        )

    def invoke(
        self, *, action: str = "summary", bridge_id: str | None = None,
        source_domains: list[str] | tuple[str, ...] | None = None
    ) -> Mapping[str, Any]:
        bridges = self._runtime.bridges
        if action == "summary":
            return {"bridge_count": len(bridges), "bridge_ids": sorted(bridges)}
        if action == "get":
            if not bridge_id:
                raise ValueError("bridge_id is required")
            return _plain(dataclasses.asdict(bridges[bridge_id]))
        if action == "find":
            wanted = set(str(x) for x in (source_domains or ()))
            rows = []
            for bid, bridge in sorted(bridges.items()):
                declared = set(str(x) for x in bridge.source_domains)
                if wanted and not wanted.issubset(declared):
                    continue
                rows.append(_plain(dataclasses.asdict(bridge)))
            return {"source_domains": sorted(wanted), "count": len(rows), "bridges": rows}
        raise ValueError(f"unsupported domain-bridge action: {action}")


class AdaptiveAxisService:
    def __init__(self, real_owner: Any, release: str) -> None:
        self._owner = real_owner
        self.spec = OwnerSpec(
            owner_id=str(real_owner.owner_id),
            capability="atlas.representation.adaptive_axis_scan",
            input_types=("domain_id", "structured_evidence_records"),
            output_types=("atlas_axis_scan",),
            validity_domain=f"real ScienceAtlas adaptive-axis owner; release {release}",
            uncertainty_contract="uses Atlas independent-study, grouped-permutation, LOSO and identifiability gates",
            cost_model="depends_on_evidence_rows_and_exact_permutation_cardinality",
            deterministic=True,
            replayable=True,
            falsification_contract="NO_CANONICAL_MUTATION; proposals remain research-local unless Atlas promotion owner qualifies them",
            owner_kind="atlas_service",
        )

    def invoke(self, *, action: str = "contract", **kwargs: Any) -> Mapping[str, Any]:
        if action == "contract":
            return _plain(self._owner.contract())
        if action == "scan":
            return _plain(self._owner.scan(**kwargs))
        raise ValueError(f"unsupported adaptive-axis action: {action}")


class UniversalLawDiscoveryService:
    def __init__(self, real_owner: Any, release: str) -> None:
        self._owner = real_owner
        self.spec = OwnerSpec(
            owner_id=str(real_owner.owner_id),
            capability="atlas.law.discover_xy",
            input_types=("x_series", "y_series"),
            output_types=("atlas_law_discovery_result",),
            validity_domain=f"real ScienceAtlas UniversalLawDiscoveryOwner; release {release}",
            uncertainty_contract="preserve Atlas discovery qualification and expressibility boundaries",
            cost_model="family_fit_and_qualification_dependent",
            deterministic=True,
            replayable=True,
            falsification_contract="candidate discovery is not truth; Atlas qualification/holdout boundaries remain authoritative",
            owner_kind="atlas_service",
        )

    def invoke(self, *, action: str = "contract", **kwargs: Any) -> Mapping[str, Any]:
        if action == "contract":
            return _plain(self._owner.contract())
        if action == "discover_from_xy":
            return _plain(self._owner.discover_from_xy(kwargs["x"], kwargs["y"]))
        if action == "expressibility_certificate":
            return _plain(self._owner.expressibility_certificate(kwargs["expression"]))
        raise ValueError(f"unsupported law-discovery action: {action}")


class ScienceAtlasCoreService:
    def __init__(self, real_owner: Any, release: str) -> None:
        self._owner = real_owner
        self.spec = OwnerSpec(
            owner_id="SCIENCE-ATLAS-CORE-KERNEL/1.0.0",
            capability="atlas.frontier.current",
            input_types=("atlas_core_action",),
            output_types=("atlas_core_contract_or_qualification",),
            validity_domain=f"real ScienceAtlas core kernel; release {release}",
            uncertainty_contract="preserve core proof/prospective/frontier claim boundaries",
            cost_model="action_dependent",
            deterministic=True,
            replayable=True,
            falsification_contract="frontier/proof output must replay from mounted Atlas data and code",
            owner_kind="atlas_service",
        )

    def invoke(self, *, action: str = "frontier_contract") -> Mapping[str, Any]:
        allowed = {
            "frontier_contract": self._owner.frontier_contract,
            "proof_contract": self._owner.proof_contract,
            "prospective_contract": self._owner.prospective_contract,
            "compile_role_typed_charts": self._owner.compile_role_typed_charts,
            "infer_recurrent_operators": self._owner.infer_recurrent_operators,
            "run_qualification": self._owner.run_qualification,
        }
        if action not in allowed:
            raise ValueError(f"unsupported Atlas core action: {action}")
        return _plain(allowed[action]())



class AtlasSemanticHypergraphService:
    """Read-only typed structural hypergraph projected from canonical Atlas.

    Lowering is exact-only: an AI axis must declare quantity_id, unit and a
    seven-component dimension vector. Name similarity never creates a binding.
    Cross-domain routes require an ACTIVE Atlas DomainBridge whose dimensional
    contract admits every bound symbol.
    """

    def __init__(self, atlas_runtime: Any, release: str, *, owner_axis_bindings: Sequence[Mapping[str, Any]] = ()) -> None:
        self._runtime = atlas_runtime
        self._owner_axis_bindings = tuple(dict(row) for row in owner_axis_bindings)
        self.spec = OwnerSpec(
            owner_id="ATLAS-SEMANTIC-HYPERGRAPH-BRIDGE/1.1.0",
            capability="atlas.registry.semantic_hypergraph",
            input_types=("typed_axis_contract_set",),
            output_types=("owner_axis_symbol_bridge_route_set",),
            validity_domain=f"mounted ScienceAtlas release {release}; exact typed symbols and ACTIVE bridges only",
            uncertainty_contract="missing quantity/unit/dimension or unknown bridge semantics => no route/UNKNOWN",
            cost_model="registry traversal over typed symbols and bridge contracts; no semantic route-count ceiling",
            deterministic=True,
            replayable=True,
            falsification_contract="every binding and bridge must replay exactly against the mounted Atlas registry",
            owner_kind="atlas_registry_service",
        )

    @staticmethod
    def _axis_contract(row: Mapping[str, Any]) -> dict[str, Any]:
        dim_raw = row.get("dimension")
        dim = None if dim_raw is None else tuple(str(x) for x in dim_raw)
        if dim is not None and len(dim) != 7:
            raise ValueError("axis dimension must contain seven SI exponents")
        return {
            "axis_id": str(row.get("axis_id", "")),
            "name": str(row.get("name", "")),
            "semantic_type": str(row.get("semantic_type", "")),
            "domain": str(row.get("domain", "")),
            "quantity_id": None if row.get("quantity_id") is None else str(row.get("quantity_id")),
            "unit": str(row.get("unit", "")),
            "dimension": dim,
            "aliases": tuple(str(x) for x in row.get("aliases", ())),
        }

    def _bindings(self, axis_row: Mapping[str, Any]) -> list[dict[str, Any]]:
        axis = self._axis_contract(axis_row)
        if not axis["axis_id"] or not axis["domain"] or not axis["unit"] or axis["quantity_id"] is None or axis["dimension"] is None:
            return []
        rows: list[dict[str, Any]] = []
        for owner_id, passport in sorted(self._runtime.catalog.passports.items()):
            if str(passport.domain_id) != axis["domain"]:
                continue
            for symbol in passport.symbols:
                if symbol.quantity_id is None or symbol.dimension is None or symbol.unit is None:
                    continue
                dim = tuple(str(x) for x in symbol.dimension.as_tuple())
                if str(symbol.quantity_id) != axis["quantity_id"]:
                    continue
                if str(symbol.unit) != axis["unit"]:
                    continue
                if dim != axis["dimension"]:
                    continue
                payload = {
                    "axis_id": axis["axis_id"],
                    "owner_id": str(owner_id),
                    "domain": str(passport.domain_id),
                    "symbol_id": str(symbol.symbol_id),
                    "display": str(symbol.display),
                    "quantity_id": str(symbol.quantity_id),
                    "unit": str(symbol.unit),
                    "dimension": list(dim),
                    "passport_digest": str(passport.digest),
                }
                payload["binding_id"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_AXIS_SYMBOL_BINDING_V1")[:24]
                rows.append(payload)
        return rows

    def _qualified_owner_axis_bindings(self, axis_id: str | None = None) -> list[dict[str, Any]]:
        rows = [dict(row) for row in self._owner_axis_bindings if axis_id is None or str(row.get("axis_id")) == str(axis_id)]
        rows.sort(key=lambda r: (str(r.get("axis_id", "")), str(r.get("owner_id", "")), str(r.get("binding_digest", ""))))
        return rows

    @staticmethod
    def _bridge_admits(bridge: Any, bindings: Sequence[Mapping[str, Any]]) -> bool:
        if str(getattr(bridge, "status", "")) != "ACTIVE":
            return False
        domains = {str(row["domain"]) for row in bindings}
        if not domains.issubset(set(str(x) for x in bridge.source_domains)):
            return False
        try:
            contract = json.loads(str(bridge.dimensional_contract))
        except (TypeError, json.JSONDecodeError):
            return False
        status = str(contract.get("status", ""))
        if status == "VALIDATED_SYMBOLIC":
            common = tuple(str(x) for x in contract.get("common_dimension", ()))
            return len(common) == 7 and all(tuple(str(x) for x in row["dimension"]) == common for row in bindings)
        if status == "VALIDATED_TYPED_MULTI_OBJECT":
            components = contract.get("components", {}) or {}
            admitted = {
                (str(row.get("quantity_id", "")), tuple(str(x) for x in row.get("dimension", ())))
                for row in components.values()
            }
            return all((str(row["quantity_id"]), tuple(str(x) for x in row["dimension"])) in admitted for row in bindings)
        return False

    def invoke(
        self,
        *,
        action: str = "summary",
        axis_contract: Mapping[str, Any] | None = None,
        input_axes: Sequence[Mapping[str, Any]] | None = None,
        target_axis: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if action == "summary":
            typed_symbols = sum(
                1 for p in self._runtime.catalog.passports.values()
                for s in p.symbols if s.quantity_id is not None and s.dimension is not None and s.unit is not None
            )
            return {
                "passport_count": len(self._runtime.catalog.passports),
                "bridge_count": len(self._runtime.bridges),
                "typed_symbol_count": typed_symbols,
                "qualified_owner_axis_binding_count": len(self._owner_axis_bindings),
                "lowering_policy": "EXACT_QUANTITY_ID_UNIT_DIMENSION_ONLY",
                "qualified_owner_axis_binding_policy": "READ_ONLY_CONTEXT_NOT_A_TYPED_SYMBOL_OR_CROSS_DOMAIN_ROUTE",
            }
        if action == "lower_axis":
            if axis_contract is None:
                raise ValueError("axis_contract is required")
            rows = self._bindings(axis_contract)
            axis_id = str(axis_contract.get("axis_id", ""))
            qualified = self._qualified_owner_axis_bindings(axis_id)
            return {
                "axis_id": axis_id,
                "count": len(rows),
                "bindings": rows,
                "qualified_owner_axis_binding_count": len(qualified),
                "qualified_owner_axis_bindings": qualified,
                "claim_boundary": {
                    "qualified_owner_axis_binding_is_exact_symbol_lowering": False,
                    "qualified_owner_axis_binding_creates_cross_domain_route": False,
                },
            }
        if action == "qualified_owner_axis_bindings":
            rows = self._qualified_owner_axis_bindings()
            payload = {
                "count": len(rows),
                "bindings": rows,
                "status": "QUALIFIED_OWNER_AXIS_BINDINGS_AVAILABLE" if rows else "NO_QUALIFIED_OWNER_AXIS_BINDINGS",
                "claim_boundary": {
                    "bindings_are_cross_domain_bridges": False,
                    "bindings_are_world_measurements": False,
                    "bindings_mutate_atlas": False,
                },
            }
            payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_QUALIFIED_OWNER_AXIS_BINDING_QUERY_V1")
            return payload
        if action == "bridge_typing_audit":
            from source.lawspace.candidates import BRIDGE_REQUIRED_ANY_TAGS, _bridge_domain_eligible
            rows = []
            for bridge_id in sorted(BRIDGE_REQUIRED_ANY_TAGS):
                bridge = self._runtime.bridges.get(bridge_id)
                if bridge is None:
                    rows.append({
                        "bridge_id": bridge_id,
                        "status": "MISSING_BRIDGE_CONTRACT",
                        "domains": [],
                    })
                    continue
                domain_rows = []
                for domain in tuple(str(x) for x in bridge.source_domains):
                    passports = [p for p in self._runtime.catalog.passports.values() if str(p.domain_id) == domain]
                    eligible = [p for p in passports if _bridge_domain_eligible(p, bridge_id)]
                    typed_eligible = [
                        p for p in eligible
                        if any(s.quantity_id is not None and s.dimension is not None and s.unit is not None for s in p.symbols)
                    ]
                    domain_rows.append({
                        "domain": domain,
                        "semantic_eligible_owner_count": len(eligible),
                        "typed_semantic_eligible_owner_count": len(typed_eligible),
                        "semantic_eligible_owner_ids": sorted(str(p.owner_id) for p in eligible),
                        "typed_semantic_eligible_owner_ids": sorted(str(p.owner_id) for p in typed_eligible),
                    })
                fully_typed = bool(domain_rows) and all(row["typed_semantic_eligible_owner_count"] > 0 for row in domain_rows)
                rows.append({
                    "bridge_id": bridge_id,
                    "status": "TYPED_BRIDGE_READY" if fully_typed else "OWNER_BRIDGE_LOWERING_GAP",
                    "domains": domain_rows,
                })
            ready = [row["bridge_id"] for row in rows if row["status"] == "TYPED_BRIDGE_READY"]
            payload = {
                "standard_bridge_count": len(rows),
                "fully_typed_bridge_count": len(ready),
                "fully_typed_bridge_ids": ready,
                "qualified_owner_axis_binding_count": len(self._owner_axis_bindings),
                "rows": rows,
                "status": "PASS_TYPED_BRIDGE_READY" if len(ready) == len(rows) else "OWNER_BRIDGE_LOWERING_GAP",
                "next_action": "TYPE_EXISTING_BRIDGE_ELIGIBLE_SYMBOLS_OR_PROVE_BRIDGE_ROLE_FOR_TYPED_OWNER" if len(ready) != len(rows) else "NONE",
            }
            payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_BRIDGE_TYPING_AUDIT_V1")
            return payload
        if action != "plan_routes":
            raise ValueError(f"unsupported semantic-hypergraph action: {action}")
        if not input_axes or target_axis is None:
            raise ValueError("input_axes and target_axis are required")
        source_contracts = [self._axis_contract(x) for x in input_axes]
        target_contract = self._axis_contract(target_axis)
        all_contracts = [*source_contracts, target_contract]
        from source.lawspace.candidates import (
            BRIDGE_REQUIRED_ANY_TAGS,
            DirectedResearchQuery,
            _bridge_domain_eligible,
            directed_owner_hypergraph_research,
        )
        required_domains = tuple(sorted({row["domain"] for row in all_contracts if row["domain"]}))
        question_parts: list[str] = []
        for row in all_contracts:
            question_parts.extend([
                row["axis_id"], row["name"], row["semantic_type"], row["domain"],
                row["quantity_id"] or "", row["unit"], *row["aliases"],
            ])
        directed_query = DirectedResearchQuery(
            question=" ".join(x for x in question_parts if x),
            required_observables=tuple(row["name"] or row["axis_id"] for row in all_contracts),
            required_domains=required_domains,
            include_all_connected_owners=True,
            discovery_mode="SEMANTIC_OWNER_FRONTIER",
        )
        directed = directed_owner_hypergraph_research(
            self._runtime.catalog, self._runtime.bridges, directed_query, {}
        )
        selected_owner_ids = set(str(x) for x in directed.get("selected_source_owner_ids", ()))
        selected_bridge_ids = set(str(x) for x in directed.get("selected_bridge_ids", ()))
        source_sets_all = [self._bindings(x) for x in source_contracts]
        target_set_all = self._bindings(target_contract)
        source_sets = [[row for row in rows if row["owner_id"] in selected_owner_ids] for rows in source_sets_all]
        target_set = [row for row in target_set_all if row["owner_id"] in selected_owner_ids]
        unlowered = [row["axis_id"] for row, bindings in zip(source_contracts, source_sets_all, strict=True) if not bindings]
        if not target_set_all:
            unlowered.append(target_contract["axis_id"])
        frontier_filtered_axes = [row["axis_id"] for row, raw, filtered in zip(source_contracts, source_sets_all, source_sets, strict=True) if raw and not filtered]
        if target_set_all and not target_set:
            frontier_filtered_axes.append(target_contract["axis_id"])

        contracts_by_domain: dict[str, list[dict[str, Any]]] = {}
        for row in all_contracts:
            contracts_by_domain.setdefault(row["domain"], []).append(row)
        semantic_gap_rows: list[dict[str, Any]] = []
        for bridge_id in sorted(selected_bridge_ids):
            bridge = self._runtime.bridges.get(bridge_id)
            if bridge is None:
                continue
            bridge_domains = tuple(str(x) for x in bridge.source_domains)
            domain_rows = []
            for domain in bridge_domains:
                passports = [p for p in self._runtime.catalog.passports.values() if p.domain_id == domain and p.owner_id in selected_owner_ids]
                if bridge_id in BRIDGE_REQUIRED_ANY_TAGS:
                    eligible = [p for p in passports if _bridge_domain_eligible(p, bridge_id)]
                else:
                    eligible = passports
                typed_eligible = [p for p in eligible if any(s.quantity_id is not None and s.dimension is not None and s.unit is not None for s in p.symbols)]
                exact_binding_owners = sorted({
                    b["owner_id"] for contract in contracts_by_domain.get(domain, ())
                    for b in self._bindings(contract)
                })
                exact_eligible = sorted(set(exact_binding_owners) & {p.owner_id for p in eligible})
                domain_rows.append({
                    "domain": domain,
                    "ai_axis_ids": [x["axis_id"] for x in contracts_by_domain.get(domain, ())],
                    "semantic_eligible_owner_count": len(eligible),
                    "typed_semantic_eligible_owner_count": len(typed_eligible),
                    "exact_binding_owner_count": len(exact_binding_owners),
                    "exact_semantic_eligible_owner_count": len(exact_eligible),
                    "exact_semantic_eligible_owner_ids": exact_eligible,
                })
            semantic_gap_rows.append({
                "bridge_id": bridge_id,
                "required_domains": list(bridge_domains),
                "domain_coverage_exact": set(bridge_domains) == set(required_domains),
                "domains": domain_rows,
                "status": "LOWERABLE" if set(bridge_domains) == set(required_domains) and all(r["exact_semantic_eligible_owner_count"] > 0 for r in domain_rows) else "OWNER_BRIDGE_LOWERING_GAP",
            })

        routes: list[dict[str, Any]] = []
        if not unlowered and not frontier_filtered_axes:
            for source_combo in itertools.product(*source_sets):
                for target_binding in target_set:
                    bindings = [*source_combo, target_binding]
                    domains = {str(row["domain"]) for row in bindings}
                    for bridge_id in sorted(selected_bridge_ids):
                        bridge = self._runtime.bridges.get(bridge_id)
                        if bridge is None or set(str(x) for x in bridge.source_domains) != domains:
                            continue
                        # Reuse Atlas bridge semantic-role qualification instead
                        # of inventing a second AI eligibility rule.
                        passports = [self._runtime.catalog.passports[str(row["owner_id"])] for row in bindings]
                        if bridge_id in BRIDGE_REQUIRED_ANY_TAGS and not all(_bridge_domain_eligible(p, bridge_id) for p in passports):
                            continue
                        if not self._bridge_admits(bridge, bindings):
                            continue
                        source_owner_ids = tuple(dict.fromkeys(str(row["owner_id"]) for row in source_combo))
                        payload = {
                            "input_axes": [row["axis_id"] for row in source_contracts],
                            "target_axis": target_contract["axis_id"],
                            "source_owner_ids": list(source_owner_ids),
                            "target_owner_id": str(target_binding["owner_id"]),
                            "bridge_id": str(bridge_id),
                            "binding_ids": [str(row["binding_id"]) for row in bindings],
                            "bridge_contract": str(bridge.dimensional_contract),
                            "atlas_directed_research_digest": str(directed.get("digest", "")),
                        }
                        route_id = digest_json(payload, namespace=b"SCIENCEATLAS_AI_STRUCTURAL_HYPERGRAPH_ROUTE_V2")[:24]
                        routes.append({
                            "route_id": route_id,
                            "input_axes": payload["input_axes"],
                            "target_axis": payload["target_axis"],
                            "source_owner_ids": list(source_owner_ids),
                            "target_owner_id": str(target_binding["owner_id"]),
                            "bridge_id": str(bridge_id),
                            "bindings": [{k: v for k, v in row.items() if k != "passport_digest"} for row in bindings],
                            "source_passport_digests": [str(row["passport_digest"]) for row in source_combo],
                            "target_passport_digest": str(target_binding["passport_digest"]),
                            "bridge_contract_digest": digest_json(_plain(dataclasses.asdict(bridge)), namespace=b"SCIENCEATLAS_AI_BRIDGE_CONTRACT_V1"),
                            "atlas_directed_research_digest": str(directed.get("digest", "")),
                            "dimensional_status": "PASS",
                            "lowering_status": "PASS",
                            "path_cost": len(set((*source_owner_ids, str(target_binding["owner_id"])))) + len(bindings) + 1,
                        })
        dedup = {row["route_id"]: row for row in routes}
        ordered = [dedup[k] for k in sorted(dedup)]
        if ordered:
            status = "ROUTES"
        elif unlowered:
            status = "UNKNOWN_TYPED_LOWERING"
        elif frontier_filtered_axes:
            status = "OWNER_FRONTIER_FILTERED_TYPED_BINDING"
        elif any(row["status"] == "OWNER_BRIDGE_LOWERING_GAP" for row in semantic_gap_rows):
            status = "OWNER_BRIDGE_LOWERING_GAP"
        else:
            status = "NO_ADMISSIBLE_BRIDGE"
        receipt = {
            "input_axis_ids": [row["axis_id"] for row in source_contracts],
            "target_axis_id": target_contract["axis_id"],
            "required_domains": list(required_domains),
            "unlowered_axes": sorted(set(unlowered)),
            "frontier_filtered_typed_axes": sorted(set(frontier_filtered_axes)),
            "route_count": len(ordered),
            "routes": ordered,
            "status": status,
            "atlas_directed_research": {
                "digest": str(directed.get("digest", "")),
                "schema": str(directed.get("schema", "")),
                "selected_source_owner_count": int(directed.get("selected_source_owner_count", 0)),
                "selected_bridge_ids": sorted(selected_bridge_ids),
                "selected_domains": list(directed.get("selected_domains", ())),
                "registered_axis_count": int(directed.get("registered_axis_count", 0)),
                "all_registered_axes_visited": bool(directed.get("all_registered_axes_visited", False)),
                "fixed_owner_visit_budget": directed.get("fixed_owner_visit_budget"),
                "fixed_candidate_axis_order_ceiling": directed.get("fixed_candidate_axis_order_ceiling"),
            },
            "semantic_lowering_gaps": semantic_gap_rows,
            "next_action": "TYPE_EXISTING_BRIDGE_ELIGIBLE_SYMBOLS_OR_PROVE_BRIDGE_ROLE_FOR_TYPED_OWNER" if status == "OWNER_BRIDGE_LOWERING_GAP" else "NONE",
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_SEMANTIC_HYPERGRAPH_QUERY_V2")
        return receipt

def _registry_snapshot(atlas_runtime: Any, identity: Mapping[str, Any], *, knowledge_overlay: Mapping[str, Any] | None = None) -> dict[str, Any]:
    registries = atlas_runtime.registries
    axis_counts = {domain_id: len(registry.axes) for domain_id, registry in sorted(registries.items())}
    passport_rows = {
        owner_id: {
            "digest": str(passport.digest),
            "domain_id": str(passport.domain_id),
            "home_cell_id": str(passport.home_cell_id),
            "epistemic_state": str(passport.epistemic_state),
        }
        for owner_id, passport in sorted(atlas_runtime.catalog.passports.items())
    }
    payload = {
        "schema": "scienceatlas-ai-atlas-registry-snapshot/v1",
        "release_identity": dict(identity),
        "catalog_digest": str(atlas_runtime.catalog.digest()),
        "passport_count": len(atlas_runtime.catalog.passports),
        "domain_count": len(registries),
        "axis_count": sum(axis_counts.values()),
        "axis_counts_by_domain": axis_counts,
        "bridge_count": len(atlas_runtime.bridges),
        "bridge_registry_digest": digest_json(
            {
                bid: {
                    "source_domains": list(bridge.source_domains),
                    "output_entity_type": str(bridge.output_entity_type),
                    "dimensional_contract": str(bridge.dimensional_contract),
                    "status": str(bridge.status),
                }
                for bid, bridge in sorted(atlas_runtime.bridges.items())
            },
            namespace=b"SCIENCEATLAS_AI_ATLAS_BRIDGE_INDEX_V1",
        ),
        "computational_method_count": len(atlas_runtime.computational_methods),
        "manifest_count": len(atlas_runtime.manifests),
        "quantity_count": len(atlas_runtime.quantities),
        "constant_count": len(atlas_runtime.constants),
        "passport_index_digest": digest_json(passport_rows, namespace=b"SCIENCEATLAS_AI_ATLAS_PASSPORT_INDEX_V1"),
        "knowledge_overlay": {
            "state_digest": str((knowledge_overlay or {}).get("state_digest", "")),
            "overlay_digest": str((knowledge_overlay or {}).get("overlay_digest", "")),
            "qualified_owner_axis_binding_count": len((knowledge_overlay or {}).get("owner_axis_bindings", ())),
            "policy": "READ_ONLY_SEMANTIC_CONTEXT_NOT_CROSS_DOMAIN_ROUTE",
        },
    }
    payload["registry_snapshot_digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_ATLAS_REGISTRY_SNAPSHOT_V1")
    return payload


def mount_real_scienceatlas(owner_bus: OwnerBus, root: str | Path) -> dict[str, Any]:
    """Mount the real external ScienceAtlas owner registry into ``owner_bus``.

    The source distribution is never copied into the AI package and the bridge
    never mutates its canonical registry. Persisted AI states retain the complete
    OwnerSpec set but restore external executors as detached/fail-closed owners.
    """
    root_p = Path(root).expanduser().resolve()
    _ensure_real_atlas_import(root_p)

    from source.lawspace.adaptive_axis import AdaptiveAxisDiscoveryOwner
    from source.lawspace.law_discovery import UniversalLawDiscoveryOwner
    from source.lawspace.runtime import LawSpaceRuntime
    from source.lawspace.science_atlas_core import ScienceAtlasCoreKernel

    identity = _manifest_identity(root_p)
    atlas_runtime = LawSpaceRuntime(root_p)
    knowledge_overlay = _knowledge_evolution_overlay(root_p)
    snapshot = _registry_snapshot(atlas_runtime, identity, knowledge_overlay=knowledge_overlay)

    live_owners: list[Any] = [
        AtlasPassportProxy(passport)
        for _, passport in sorted(atlas_runtime.catalog.passports.items())
    ]
    live_owners.extend(
        [
            AtlasCatalogService(atlas_runtime, identity["release"]),
            AtlasDomainBridgeService(atlas_runtime, identity["release"]),
            AtlasSemanticHypergraphService(
                atlas_runtime, identity["release"],
                owner_axis_bindings=knowledge_overlay.get("owner_axis_bindings", ()),
            ),
            AdaptiveAxisService(AdaptiveAxisDiscoveryOwner(), identity["release"]),
            UniversalLawDiscoveryService(UniversalLawDiscoveryOwner(root_p), identity["release"]),
            ScienceAtlasCoreService(ScienceAtlasCoreKernel(root_p), identity["release"]),
        ]
    )

    # Validate all external contracts before mutating the bus, so a duplicate ID
    # or capability fails atomically from the caller's perspective.
    ids = [owner.spec.owner_id for owner in live_owners]
    caps = [owner.spec.capability for owner in live_owners]
    if len(ids) != len(set(ids)):
        raise ValueError("real Atlas mount produced duplicate owner IDs")
    if len(caps) != len(set(caps)):
        raise ValueError("real Atlas mount produced duplicate capabilities")

    for owner in live_owners:
        owner_bus.attach(owner)

    receipt = {
        "schema": BRIDGE_SCHEMA,
        "registry_snapshot": snapshot,
        "mounted_owner_count": len(live_owners),
        "mounted_passport_owner_count": len(atlas_runtime.catalog.passports),
        "mounted_service_owner_count": len(live_owners) - len(atlas_runtime.catalog.passports),
        "qualified_owner_axis_binding_count": len(knowledge_overlay.get("owner_axis_bindings", ())),
        "knowledge_overlay_digest": str(knowledge_overlay.get("overlay_digest", "")),
        "service_capabilities": [
            "atlas.registry.catalog",
            "atlas.registry.domain_bridges",
            "atlas.registry.semantic_hypergraph",
            "atlas.representation.adaptive_axis_scan",
            "atlas.law.discover_xy",
            "atlas.frontier.current",
        ],
        "mutation_policy": "READ_ONLY_EXTERNAL_CANONICAL_REGISTRY",
        "execution_policy_after_restore": "DETACHED_FAIL_CLOSED_UNTIL_SAME_CONTRACT_REMOUNTED",
    }
    receipt["receipt_digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ATLAS_MOUNT_RECEIPT_V1")
    return receipt
