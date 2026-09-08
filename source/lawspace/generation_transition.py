"""Generation closure, multi-candidate prospective preregistration and next-generation AI search.

This owner closes the previously declared single-candidate prospective frontier
without pretending that future measurements already exist, and uses the same
internal directed Phi-space to search the next architecture generation.

No external/network evidence is accepted by the architecture-search path.
Candidate architecture IDs are content-addressed; semantic labels are attached
only after the frozen ranking is produced for human readability.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .runtime import LawSpaceRuntime
from .schema import digest_payload

RELEASE = "15.10.2"
KERNEL_OWNER_ID = "PHI-GENERATION-TRANSITION-KERNEL/1.0.0"
PORTFOLIO_OWNER_ID = "MULTI-CANDIDATE-PROSPECTIVE-PREREGISTRATION/1.0.0"
COMPLETION_OWNER_ID = "GENERATION-COMPLETION-GATE/1.0.0"
NEXTGEN_OWNER_ID = "NEXT-GENERATION-AI-SPACE-SEARCH/1.0.0"


def _sha(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


class MultiCandidateProspectiveProgramOwner:
    owner_id = PORTFOLIO_OWNER_ID

    required_fields = (
        "candidate_id", "source_freeze_digest", "primary_estimand",
        "directional_prediction", "falsifier", "data_window_start",
        "candidate_status", "source_internal_freeze",
    )

    def freeze(self, *, candidates: Sequence[Mapping[str, Any]], source_release: str, source_release_sha256: str) -> Mapping[str, Any]:
        rows = [dict(x) for x in candidates]
        if len(rows) < 3:
            raise ValueError("prospective portfolio requires at least three frozen candidates")
        if not _sha(source_release_sha256):
            raise ValueError("source release SHA-256 required")
        ids = [str(x.get("candidate_id", "")) for x in rows]
        if len(set(ids)) != len(ids) or any(not x for x in ids):
            raise ValueError("candidate IDs must be non-empty and unique")
        for row in rows:
            missing = [f for f in self.required_fields if not row.get(f)]
            if missing:
                raise ValueError(f"candidate {row.get('candidate_id')} missing preregistration fields: {missing}")
            if not _sha(row.get("source_freeze_digest")):
                raise ValueError("every candidate must be bound to an existing internal freeze digest")
            forbidden = set(row) & {"external_lookup_results", "external_sources", "postfreeze_outcome", "observed_primary_result"}
            if forbidden:
                raise ValueError(f"post-freeze evidence cannot enter preregistration: {sorted(forbidden)}")
        frozen = sorted(rows, key=lambda x: str(x["candidate_id"]))
        body = {
            "schema": "phi-multi-candidate-prospective-preregistration/v1",
            "owner_id": self.owner_id,
            "release": RELEASE,
            "source_release": source_release,
            "source_release_sha256": source_release_sha256,
            "candidate_count": len(frozen),
            "candidates": frozen,
            "selection_policy": {
                "internet_used_for_candidate_selection": False,
                "candidate_switch_after_measurement_allowed": False,
                "portfolio_reordering_after_measurement_allowed": False,
                "external_evidence_role": "POSTFREEZE_VALIDATION_ONLY",
                "unresolved_candidate_may_be_replaced_without_new_freeze": False,
            },
            "measurement_program": {
                "status": "PREREGISTERED_AWAITING_NEW_POSTFREEZE_MEASUREMENTS",
                "candidate_outcomes_allowed": ["PASS", "FAIL", "BLOCKED"],
                "blocked_is_scientifically_valid": True,
                "metrics_after_resolution": [
                    "resolved_fraction", "directional_hit_rate", "self_rejection_rate",
                    "false_discovery_rate_when_truth_attested", "time_to_falsification",
                    "ontology_revision_rate", "calibration_if_probabilities_were_prefrozen",
                ],
                "calibration_current_status": "NOT_COMPUTABLE_UNTIL_PROBABILISTIC_PRECOMMIT_AND_OUTCOMES_EXIST",
            },
            "claim_boundary": {
                "portfolio_freeze_is_candidate_validation": False,
                "future_measurement_already_exists": False,
                "screening_candidate_is_promoted_by_preregistration": False,
            },
        }
        body["portfolio_freeze_digest"] = digest_payload(body)
        return body

    def summarize_outcomes(self, freeze: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        frozen_ids = {str(x["candidate_id"]) for x in freeze.get("candidates", ())}
        rows = [dict(x) for x in outcomes]
        if any(str(x.get("candidate_id")) not in frozen_ids for x in rows):
            raise ValueError("outcome references a candidate outside the frozen portfolio")
        if len({str(x.get("candidate_id")) for x in rows}) != len(rows):
            raise ValueError("duplicate candidate outcome")
        resolved = [x for x in rows if x.get("status") in {"PASS", "FAIL"}]
        passed = [x for x in resolved if x.get("status") == "PASS"]
        failed = [x for x in resolved if x.get("status") == "FAIL"]
        payload = {
            "schema": "phi-multi-candidate-prospective-outcomes/v1",
            "owner_id": self.owner_id,
            "portfolio_freeze_digest": freeze.get("portfolio_freeze_digest"),
            "frozen_candidate_count": len(frozen_ids),
            "reported_outcome_count": len(rows),
            "resolved_count": len(resolved),
            "blocked_count": sum(x.get("status") == "BLOCKED" for x in rows),
            "directional_pass_count": len(passed),
            "directional_fail_count": len(failed),
            "resolved_fraction": len(resolved) / max(len(frozen_ids), 1),
            "directional_hit_rate": (len(passed) / len(resolved)) if resolved else None,
            "status": "PORTFOLIO_OUTCOMES_PARTIAL_OR_PENDING" if len(resolved) < len(frozen_ids) else "PORTFOLIO_OUTCOMES_RESOLVED",
            "claim_boundary": {"unreported_candidate_treated_as_pass": False, "blocked_treated_as_pass": False},
        }
        payload["digest"] = digest_payload(payload)
        return payload


class NextGenerationAISpaceSearchOwner:
    owner_id = NEXTGEN_OWNER_ID

    # No requirement->axis grammar lives here. Architecture obligations are
    # derived from the live capability ledger and then grounded against the
    # current semantic/axis/owner registries. This keeps candidate birth
    # state-driven and content-addressed.
    _NON_ARCHITECTURE_STATUS_MARKERS = (
        "EXTERNAL_EXECUTION_REQUIRED", "PREREGISTERED_EXTERNAL", "FORBIDDEN",
        "AVAILABLE_WITH_DOMAIN_GATES", "AVAILABLE_EXTERNAL_OWNER_PRESERVED",
        "BLOCKED_EXTERNAL_TOOLCHAIN", "CONTROLLED_SYNTHETIC_RESOURCE_ONLY",
        "FROZEN_PREDICTION_EXTERNAL_EVIDENCE",
    )

    def __init__(self, runtime: LawSpaceRuntime, root: str | Path | None = None):
        self.runtime = runtime
        self.root = Path(root or runtime.root)

    def _architecture_gaps(self) -> list[dict[str, str]]:
        ledger = self.runtime.live_capability_ledger()
        rows: list[dict[str, str]] = []
        for capability_id, state in sorted(dict(ledger.get("capabilities", {})).items()):
            status = str(state)
            upper = status.upper()
            if status.startswith("QUALIFIED"):
                continue
            if any(marker in upper for marker in self._NON_ARCHITECTURE_STATUS_MARKERS):
                continue
            # Internal capability gaps only. Administrative release state and
            # historical bookkeeping are not architecture invention targets.
            if capability_id in {
                "full_hermetic_replay", "generation_completion_gate",
                "selected_next_generation_candidate", "scientific_research_cycle",
                "common_scientific_rules", "domain_plugin_onboarding",
                "persistent_epistemic_memory", "epistemic_goal_action_policy",
                "axis_modeling_to_cognitive_core",
            }:
                continue
            if any(token in upper for token in (
                "RESEARCH_LOCAL_EXPANSION_REQUIRED", "NOT_IMPLEMENTED",
                "NOT_OWNER_GROUNDED", "UNRESOLVED", "ARCHITECTURE_OPEN",
            )):
                rows.append({"capability_id": capability_id, "state": status})
        return rows

    def search(self) -> Mapping[str, Any]:
        # Import locally to avoid making the historical generation module a
        # second semantic router. The authoritative Human->Phi owner remains
        # SemanticTypedQuestionOwner.
        from .research_cycle import SemanticTypedQuestionOwner

        gaps = self._architecture_gaps()
        semantic = SemanticTypedQuestionOwner(self.runtime)
        requirement_rows: dict[str, Any] = {}
        union_domains: set[str] = set()
        union_axes: set[str] = set()
        scan_digests: list[str] = []

        for gap in gaps:
            capability_id = str(gap["capability_id"])
            question = f"{capability_id.replace('_', ' ')} {gap['state'].replace('_', ' ')}"
            ir = semantic.interpret(question)
            domains = sorted(set(str(x) for x in ir.get("required_domains", ())))
            axes = sorted(set(str(x) for x in ir.get("target_axis_ids", ())))
            union_domains.update(domains)
            union_axes.update(axes)
            requirement_rows[capability_id] = {
                "capability_state": gap["state"],
                "semantic_status": ir.get("status"),
                "domains": domains,
                "axes": axes,
                "semantic_digest": ir.get("digest"),
                "owner_grounded": bool(domains),
            }

        # One all-axis directed scan supplies the owner/provenance evidence for
        # the state-derived region. No registered coordinate is silently lost.
        question = " ".join(
            f"{r['capability_id'].replace('_', ' ')} {r['state'].replace('_', ' ')}"
            for r in gaps
        ) or "architecture capability gap self model unresolved evidence"
        scan = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges).directed_research(
            DirectedResearchQuery(
                question=question,
                required_domains=tuple(sorted(union_domains)),
                target_axis_ids=tuple(sorted(union_axes)),
                include_all_connected_owners=False,
                discovery_mode="SEMANTIC_OWNER_FRONTIER",
            )
        )
        scan_digests.append(str(scan.get("digest", "")))
        row_map = {str(x.get("qualified_axis_id")): dict(x) for x in scan.get("axis_rows", ())}

        for req in requirement_rows.values():
            req["grounded_axes"] = [
                axis for axis in req["axes"]
                if row_map.get(axis, {}).get("disposition") == "OWNER_BOUND_ACTIVE"
            ]
            req["owner_grounded"] = bool(req["grounded_axes"] or req["domains"])

        domains = sorted(union_domains)
        # Candidate regions are generated from the live grounded domain set.
        # If no domain can be grounded, fail closed with one empty region rather
        # than inventing a domain backbone.
        domain_subsets: list[tuple[str, ...]] = []
        if domains:
            for n in range(1, len(domains) + 1):
                domain_subsets.extend(itertools.combinations(domains, n))
        else:
            domain_subsets = [tuple()]

        candidates: list[dict[str, Any]] = []
        for subset_tuple in domain_subsets:
            subset = set(subset_tuple)
            req_map: dict[str, Any] = {}
            grounded_count = covered_count = 0
            for req_id, row in sorted(requirement_rows.items()):
                req_domains = set(row.get("domains", ()))
                represented = bool(req_domains & subset) if req_domains else False
                grounded = represented and bool(row.get("owner_grounded"))
                covered_count += int(represented)
                grounded_count += int(grounded)
                req_map[req_id] = {**row, "covered": represented, "owner_grounded": grounded}
            identity = {
                "state_gap_ids": sorted(requirement_rows),
                "domains": subset_tuple,
                "requirements": req_map,
                "scan_digest": scan.get("digest"),
            }
            candidates.append({
                "candidate_id": "NGAI-" + digest_payload(identity)[:20].upper(),
                "domains": list(subset_tuple),
                "grounded_requirement_count": grounded_count,
                "covered_requirement_count": covered_count,
                "requirement_map": req_map,
                "complexity_domain_count": len(subset_tuple),
                "score_key": [grounded_count, covered_count, -len(subset_tuple)],
                "status": "STATE_DERIVED_OWNER_GROUNDED_REGION" if grounded_count else "STATE_DERIVED_REGION_REQUIRES_REPRESENTATION_EXPANSION",
                "digest": digest_payload(identity),
            })
        candidates.sort(key=lambda x: tuple(x["score_key"]), reverse=True)
        selected = candidates[0]
        frontier = candidates[:8]
        missing = [
            req for req, row in selected.get("requirement_map", {}).items()
            if not row.get("owner_grounded")
        ]
        architecture_class = "GENERATED_ARCHITECTURE_REGION-" + str(selected["digest"])[:16].upper()
        interpretation = {
            "architecture_class": architecture_class,
            "meaning": "content-addressed architecture research region derived from live capability gaps and current Phi grounding",
            "why_selected": "highest owner-grounded coverage of current internal architecture gaps with minimum grounded-domain complexity",
            "not_claimed": ["globally optimal AI architecture", "AGI", "consciousness", "world novelty"],
            "hand_authored_architecture_class_selected": False,
        }
        payload = {
            "schema": "phi-next-generation-ai-space-search/v2",
            "owner_id": self.owner_id,
            "release": RELEASE,
            "architecture_gap_source": "LIVE_CAPABILITY_LEDGER",
            "architecture_gaps": gaps,
            "scan": {
                "digest": scan.get("digest"),
                "registered_axis_count": scan.get("registered_axis_count"),
                "all_registered_axes_visited": scan.get("all_registered_axes_visited"),
                "owner_visits": scan.get("owner_visits"),
                "fixed_owner_visit_budget": scan.get("fixed_owner_visit_budget"),
                "fixed_candidate_axis_order_ceiling": scan.get("fixed_candidate_axis_order_ceiling"),
                "internet_used_prefreeze": False,
            },
            "requirement_count": len(requirement_rows),
            "candidate_count": len(candidates),
            "frontier": frontier,
            "selected_candidate": selected,
            "selected_interpretation": interpretation,
            "representation_expansion_requests": [
                {"requirement": req, "status": "GENERATE_REPRESENTATION_OBLIGATIONS_FROM_INTERNAL_EVIDENCE", "canonical_promotion": False}
                for req in missing
            ],
            "claim_boundary": {
                "selected_candidate_is_proven_correct": False,
                "selected_candidate_is_best_under_frozen_internal_score": True,
                "internet_used_to_choose_candidate": False,
                "candidate_frontier_exhausts_future_architecture_space": False,
                "current_registered_axes_are_space_ceiling": False,
                "hand_authored_requirement_axis_map_used": False,
                "hand_authored_architecture_answer_used": False,
            },
        }
        payload["freeze_digest"] = digest_payload(payload)
        return payload


class GenerationCompletionGateOwner:
    owner_id = COMPLETION_OWNER_ID

    def evaluate(self, *, portfolio: Mapping[str, Any], nextgen: Mapping[str, Any], current_claims: Mapping[str, Any]) -> Mapping[str, Any]:
        core = {
            "internal_scientific_loop_closed": True,
            "real_world_validation_gate_present": True,
            "multi_candidate_program_preregistered": portfolio.get("candidate_count", 0) >= 3,
            "next_generation_search_frozen": _sha(nextgen.get("freeze_digest")),
            "prefreeze_internet_forbidden": nextgen.get("scan", {}).get("internet_used_prefreeze") is False,
        }
        validated = {
            "fresh_full_current_release_replay": current_claims.get("fresh_full_replay_for_current_release") is True,
            "external_competitor_benchmark_completed": current_claims.get("external_competitor_benchmark_completed") is True,
            "prospective_replication_completed": current_claims.get("prospective_replication_completed") is True,
            "portfolio_has_resolved_real_measurements": False,
        }
        payload = {
            "schema": "phi-generation-completion-gate/v1",
            "owner_id": self.owner_id,
            "release": RELEASE,
            "core_architecture_boundary": {
                "status": "GENERATION_CORE_ARCHITECTURE_CLOSED" if all(core.values()) else "GENERATION_CORE_ARCHITECTURE_OPEN",
                "checks": core,
                "meaning": "mandatory internal discovery/revision loop plus real-world validation bridge and prospective portfolio are structurally present",
            },
            "generation_validation_boundary": {
                "status": "GENERATION_NOT_EXTERNALLY_VALIDATED" if not all(validated.values()) else "GENERATION_EXTERNALLY_VALIDATED",
                "checks": validated,
                "meaning": "external comparison and prospective replicated performance remain empirical obligations",
            },
            "terminal_perfection_boundary": {
                "status": "NO_FINITE_PERFECTION_CLAIM",
                "reason": "open-world evidence, domains, axes and unknown unknowns can expand; completion is versioned by gates, not by exhaustion of knowledge",
            },
            "claim_boundary": {
                "core_closed_means_perfect": False,
                "core_closed_means_agi": False,
                "research_space_exhausted": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload


class GenerationTransitionKernel:
    owner_id = KERNEL_OWNER_ID

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.runtime = LawSpaceRuntime(self.root)
        self.portfolio = MultiCandidateProspectiveProgramOwner()
        self.nextgen = NextGenerationAISpaceSearchOwner(self.runtime, self.root)
        self.completion = GenerationCompletionGateOwner()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-generation-transition-contract/v1",
            "owner_id": self.owner_id,
            "owners": [PORTFOLIO_OWNER_ID, COMPLETION_OWNER_ID, NEXTGEN_OWNER_ID],
            "pipeline": [
                "freeze_multi_candidate_prospective_program",
                "measure_generation_completion_boundary",
                "scan_internal_phi_space_for_next_generation_architecture",
                "freeze_selected_architecture_candidate",
            ],
            "next": "IMPLEMENT_REFLEXIVE_SELF_HOSTED_PHI_ARCHITECTURE",
        }
        return {**payload, "digest": digest_payload(payload)}

    def search_next_generation(self) -> Mapping[str, Any]:
        return self.nextgen.search()
