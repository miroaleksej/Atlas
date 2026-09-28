#!/usr/bin/env python3
"""Thin MCP gateway for the existing Atlas / Phi-Compiler organism.

The gateway owns transport and response shaping only. Scientific algorithms,
owner routing, representation birth, axis birth, hypothesis handling and
resident learning remain owned by the existing Atlas core.

The official MCP Python SDK is intentionally NOT vendored into this clean
distribution. Install it in the runtime environment with
`python -m pip install "mcp>=2,<3"` or `python -m pip install -e ".[mcp]"`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

# A clean/sealed distribution must not be mutated merely by importing Atlas.
# Set this before importing any Atlas modules so Python cannot create __pycache__
# entries inside the distribution tree.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source.lawspace.api import LawSpaceAPI

GATEWAY_VERSION = "1.4.0"
DISTRIBUTION_ID = "0.15.29.0+selfstudy.persistent-multiworld.prediction-lowering.mcp6.formal-verification.external-attestation.open-ended-math.semantic-gap-birth.proof-discharge.semantic-obligation-compiler"


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _compact_research_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Return a bounded, model-readable view without changing the core receipt."""
    cycle = dict(receipt.get("research_cycle") or {})
    typed = dict(receipt.get("semantic_typed_ir") or {})
    competitive = dict(cycle.get("competitive_set") or {})
    info_gain = dict(cycle.get("information_gain") or {})
    experiment = dict(cycle.get("experiment") or {})
    representation = dict(receipt.get("representation_invention") or {})
    primitive = dict(receipt.get("primitive_synthesis") or {})
    open_world = dict(receipt.get("open_world") or {})
    learned_action = dict(receipt.get("learned_world_action") or {})
    heartbeat = dict(receipt.get("resident_heartbeat") or {})
    formal = dict(receipt.get("formal_mathematical_verification") or {})
    handoff = dict(receipt.get("formal_kernel_handoff") or {})
    external_attestation = dict(receipt.get("external_formal_kernel_attestation") or {})
    counterexamples = [dict(x) for x in (receipt.get("counterexample_search_receipts") or ()) if isinstance(x, Mapping)]
    proof_memory = dict(receipt.get("universal_proof_mechanism_memory") or {})

    candidates = []
    for row in competitive.get("candidates") or ():
        if isinstance(row, Mapping):
            candidates.append({
                "candidate_id": row.get("candidate_id"),
                "owner_id": row.get("owner_id") or row.get("source_owner_id"),
                "domain_id": row.get("domain_id"),
                "status": row.get("status"),
            })

    return {
        "schema": "atlas-mcp-research-view/v1",
        "gateway_version": GATEWAY_VERSION,
        "core_receipt_digest": receipt.get("digest"),
        "status": receipt.get("status"),
        "question": receipt.get("question"),
        "next_required_external_input": receipt.get("next_required_external_input"),
        "semantic_typed_ir": {
            "status": typed.get("status"),
            "required_domains": typed.get("required_domains"),
            "target_axis_ids": typed.get("target_axis_ids"),
            "required_observables": typed.get("required_observables"),
            "capability_gap_detected": typed.get("capability_gap_detected"),
            "digest": typed.get("digest"),
        },
        "research_cycle": {
            "status": cycle.get("status"),
            "digest": cycle.get("digest"),
            "gates": cycle.get("gates"),
            "competitive_set_status": competitive.get("status"),
            "candidate_count": len(candidates),
            "candidates": candidates[:20],
            "information_gain_status": info_gain.get("status"),
            "selected_experiment_id": experiment.get("selected_experiment_id"),
        },
        "representation_invention": {
            "status": representation.get("status"),
            "digest": representation.get("digest"),
            "claim_boundary": representation.get("claim_boundary"),
            "representation_signature": representation.get("representation_signature")
                or representation.get("generated_representation_signature"),
        },
        "primitive_synthesis": {
            "status": primitive.get("status"),
            "digest": primitive.get("digest"),
            "claim_boundary": primitive.get("claim_boundary"),
        },
        "open_world": {
            "status": open_world.get("status"),
            "digest": open_world.get("digest"),
        },
        "learned_world_action": {
            "status": learned_action.get("status"),
            "selected_action": learned_action.get("selected_action"),
            "digest": learned_action.get("digest"),
        },
        "resident_heartbeat": {
            "status": heartbeat.get("status"),
            "digest": heartbeat.get("digest"),
        },
        "formal_mathematical_verification": {
            "status": formal.get("status"),
            "verified": formal.get("verified"),
            "proof_obligation_count": len(formal.get("proof_obligations") or ()),
            "digest": formal.get("digest"),
        },
        "formal_kernel_handoff": {
            "status": handoff.get("status"),
            "target_kernel": handoff.get("target_kernel"),
            "digest": handoff.get("digest"),
        },
        "external_formal_kernel_attestation": {
            "status": external_attestation.get("status"),
            "external_attestation_accepted": external_attestation.get("external_attestation_accepted"),
            "locally_kernel_verified": external_attestation.get("locally_kernel_verified"),
            "kernel_replay_evidence_count": external_attestation.get("kernel_replay_evidence_count"),
            "digest": external_attestation.get("digest"),
        },
        "counterexample_search": {
            "search_count": len(counterexamples),
            "counterexample_count": sum(1 for x in counterexamples if x.get("counterexample_found") is True),
        },
        "universal_proof_mechanism_memory": {
            "owner_id": proof_memory.get("owner_id"),
            "mechanism_count": proof_memory.get("mechanism_count"),
            "mechanism_ids": proof_memory.get("mechanism_ids"),
            "digest": proof_memory.get("digest"),
        },
        "claim_boundary": receipt.get("claim_boundary"),
    }


def _compact_campaign_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    last = receipt.get("last_research_receipt")
    return {
        "schema": "atlas-mcp-open-ended-campaign-view/v1",
        "gateway_version": GATEWAY_VERSION,
        "campaign_digest": receipt.get("digest"),
        "status": receipt.get("status"),
        "question": receipt.get("question"),
        "terminal": receipt.get("terminal"),
        "terminal_reason": receipt.get("terminal_reason"),
        "slice_budget": receipt.get("slice_budget"),
        "slices_executed": receipt.get("slices_executed"),
        "unique_candidate_count_observed": receipt.get("unique_candidate_count_observed"),
        "unique_research_local_axis_count_observed": receipt.get("unique_research_local_axis_count_observed"),
        "operation_alphabet_count_observed": receipt.get("operation_alphabet_count_observed"),
        "slice_receipts": list(receipt.get("slice_receipts") or ()),
        "continuation": dict(receipt.get("continuation") or {}),
        "last_research": _compact_research_receipt(last) if isinstance(last, Mapping) else None,
        "claim_boundary": receipt.get("claim_boundary"),
    }


class AtlasMCPBridge:
    """Protocol-neutral bridge used by MCP tools and local smoke tests."""

    def __init__(self, root: str | Path = ROOT) -> None:
        self.root = Path(root).resolve()
        self.api = LawSpaceAPI(self.root)

    @staticmethod
    def _bounded_limit(limit: int) -> int:
        return max(1, min(int(limit), 50))

    def system_status(self, *, include_contracts: bool = False) -> dict[str, Any]:
        release = dict(_read_json(self.root / "RELEASE_MANIFEST.json"))
        capabilities = dict(_read_json(self.root / "capabilities.json"))
        distribution = dict(_read_json(self.root / "DISTRIBUTION_MANIFEST.json"))
        result: dict[str, Any] = {
            "schema": "atlas-mcp-system-status/v1",
            "gateway_version": GATEWAY_VERSION,
            "distribution_id": distribution.get("distribution_id", DISTRIBUTION_ID),
            "core_release": release.get("release") or capabilities.get("release"),
            "core_declared_status": release.get("current_state_qualification_status") or release.get("status"),
            "distribution_integrity_status": distribution.get("integrity_status"),
            "authoritative_research_kernel": capabilities.get("authoritative_research_kernel"),
            "formal_mathematical_verification": capabilities.get("formal_mathematical_verification", {}).get("owner"),
            "universal_proof_mechanism_memory": capabilities.get("universal_proof_mechanism_memory", {}).get("owner"),
            "active_candidate_count": release.get("active_candidate_count"),
            "claim_boundary": {
                "gateway_is_scientific_solver": False,
                "gateway_can_stamp_atlas_native": False,
                "gateway_mutates_sealed_core": False,
            },
        }
        if include_contracts:
            result["research_contract"] = self.api.get_scientific_research_cycle_contract()
            result["adaptive_kernel_contract"] = self.api.get_adaptive_research_kernel_contract()
            result["formal_verification_contract"] = self.api.get_phi_formal_mathematical_verification_contract()
            result["universal_proof_mechanism_memory"] = self.api.get_phi_universal_proof_mechanisms()
        return result

    def search_knowledge(self, query: str, domain_id: str | None = None, limit: int = 20) -> dict[str, Any]:
        q = str(query or "").strip()
        if not q:
            raise ValueError("query is required")
        rows = self.api.search_entities(q, domain_id=domain_id, limit=self._bounded_limit(limit))
        return {
            "schema": "atlas-mcp-knowledge-search/v1",
            "query": q,
            "domain_id": domain_id,
            "results": rows,
        }

    def research(
        self,
        question: str,
        *,
        required_domains: Sequence[str] | None = None,
        target_axis_ids: Sequence[str] | None = None,
        required_observables: Sequence[str] | None = None,
        include_all_connected_owners: bool = False,
        detail_level: str = "summary",
        commit_resident_state: bool = False,
        proof_artifact: Mapping[str, Any] | None = None,
        formal_kernel_target: str = "LEAN",
        formal_kernel_attestation: Mapping[str, Any] | None = None,
        counterexample_search_specs: Sequence[Mapping[str, Any]] | None = None,
        campaign_slice_budget: int = 1,
    ) -> Mapping[str, Any]:
        q = str(question or "").strip()
        if not q:
            raise ValueError("question is required")
        if detail_level not in {"summary", "full"}:
            raise ValueError("detail_level must be 'summary' or 'full'")
        request: dict[str, Any] = {
            "question": q,
            "commit_resident_state": bool(commit_resident_state),
            "include_all_connected_owners": bool(include_all_connected_owners),
        }
        if required_domains is not None:
            request["required_domains"] = [str(x) for x in required_domains]
        if target_axis_ids is not None:
            request["target_axis_ids"] = [str(x) for x in target_axis_ids]
        if required_observables is not None:
            request["required_observables"] = [str(x) for x in required_observables]
        if proof_artifact is not None:
            request["proof_artifact"] = dict(proof_artifact)
            request["formal_kernel_target"] = str(formal_kernel_target or "LEAN").upper()
        if formal_kernel_attestation is not None:
            request["formal_kernel_attestation"] = dict(formal_kernel_attestation)
        if counterexample_search_specs:
            request["counterexample_search_specs"] = [dict(x) for x in counterexample_search_specs]
        campaign_slice_budget = max(1, int(campaign_slice_budget or 1))
        if campaign_slice_budget > 1:
            request["campaign_slice_budget"] = campaign_slice_budget
        receipt = self.api.run_autonomous_research(request)
        if receipt.get("schema") == "phi-open-ended-autonomous-research-campaign/v1":
            return receipt if detail_level == "full" else _compact_campaign_receipt(receipt)
        return receipt if detail_level == "full" else _compact_research_receipt(receipt)


def build_server(root: str | Path = ROOT):
    """Build the MCP server lazily so importing/testing Atlas needs no MCP package."""
    try:
        from mcp.server import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as exc:
        raise RuntimeError(
            "Official MCP Python SDK v2 is not installed. "
            "Install it in the runtime environment: python -m pip install 'mcp>=2,<3'"
        ) from exc

    bridge = AtlasMCPBridge(root)
    mcp = MCPServer(
        name="atlas-scientific-discovery",
        title="Atlas Scientific Discovery",
        description="Thin MCP gateway to the existing Atlas scientific research organism.",
        instructions=(
            "Use atlas_research as the default research action. "
            "Use atlas_research_and_learn only when the user explicitly asks Atlas "
            "to retain the research experience. The MCP layer never promotes a scientific "
            "claim or replaces Atlas owners."
        ),
        version=GATEWAY_VERSION,
    )

    read_only = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    resident_write = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )

    @mcp.tool(annotations=read_only)
    def atlas_system_status(include_contracts: bool = False) -> dict[str, Any]:
        """Inspect Atlas release, gateway and research-kernel status. Read-only."""
        return bridge.system_status(include_contracts=include_contracts)

    @mcp.tool(annotations=read_only)
    def atlas_search_knowledge(query: str, domain_id: str | None = None, limit: int = 20) -> dict[str, Any]:
        """Search Atlas' existing scientific entities without running a new research cycle."""
        return bridge.search_knowledge(query, domain_id=domain_id, limit=limit)

    @mcp.tool(annotations=read_only)
    def atlas_research(
        question: str,
        required_domains: list[str] | None = None,
        target_axis_ids: list[str] | None = None,
        required_observables: list[str] | None = None,
        include_all_connected_owners: bool = False,
        detail_level: str = "summary",
        proof_artifact: dict[str, Any] | None = None,
        formal_kernel_target: str = "LEAN",
        formal_kernel_attestation: dict[str, Any] | None = None,
        counterexample_search_specs: list[dict[str, Any]] | None = None,
        campaign_slice_budget: int = 1,
    ) -> dict[str, Any]:
        """Run Atlas' authoritative autonomous research owner without committing Resident state."""
        return dict(bridge.research(
            question,
            required_domains=required_domains,
            target_axis_ids=target_axis_ids,
            required_observables=required_observables,
            include_all_connected_owners=include_all_connected_owners,
            detail_level=detail_level,
            commit_resident_state=False,
            proof_artifact=proof_artifact,
            formal_kernel_target=formal_kernel_target,
            formal_kernel_attestation=formal_kernel_attestation,
            counterexample_search_specs=counterexample_search_specs,
            campaign_slice_budget=campaign_slice_budget,
        ))

    @mcp.tool(annotations=resident_write)
    def atlas_research_and_learn(
        question: str,
        required_domains: list[str] | None = None,
        target_axis_ids: list[str] | None = None,
        required_observables: list[str] | None = None,
        include_all_connected_owners: bool = False,
        detail_level: str = "summary",
        proof_artifact: dict[str, Any] | None = None,
        formal_kernel_target: str = "LEAN",
        formal_kernel_attestation: dict[str, Any] | None = None,
        counterexample_search_specs: list[dict[str, Any]] | None = None,
        campaign_slice_budget: int = 1,
    ) -> dict[str, Any]:
        """Run the same Atlas research cycle and explicitly commit only external Resident state.

        The Atlas core enforces that mutable Resident state is outside the sealed system tree.
        Use this tool only when the user wants the research experience retained by Atlas.
        """
        return dict(bridge.research(
            question,
            required_domains=required_domains,
            target_axis_ids=target_axis_ids,
            required_observables=required_observables,
            include_all_connected_owners=include_all_connected_owners,
            detail_level=detail_level,
            commit_resident_state=True,
            proof_artifact=proof_artifact,
            formal_kernel_target=formal_kernel_target,
            formal_kernel_attestation=formal_kernel_attestation,
            counterexample_search_specs=counterexample_search_specs,
            campaign_slice_budget=campaign_slice_budget,
        ))

    return mcp


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Atlas MCP Gateway for ChatGPT/Codex")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument(
        "--allow-nonloopback-http",
        action="store_true",
        help=(
            "Allow an unauthenticated Streamable HTTP listener on a non-loopback host. "
            "Use only behind a trusted authenticated reverse proxy/tunnel."
        ),
    )
    args = parser.parse_args(argv)

    if (
        args.transport == "streamable-http"
        and args.host not in {"127.0.0.1", "localhost", "::1"}
        and not args.allow_nonloopback_http
    ):
        parser.error(
            "refusing unauthenticated non-loopback MCP bind; use a Secure MCP Tunnel/"
            "authenticated reverse proxy or pass --allow-nonloopback-http explicitly"
        )

    server = build_server(ROOT)
    if args.transport == "stdio":
        server.run()
    else:
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path=args.path,
            stateless_http=True,
            json_response=True,
        )


if __name__ == "__main__":
    main()
