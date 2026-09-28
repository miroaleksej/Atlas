"""Automated U4→U5 verification attempts without scientific promotion.

The scheduler replays ScientificVerificationCore on every attempt, evaluates the
shared OOD/replication/falsification progression gates, and emits one of four
research outcomes only.  It never mutates canonical registries and never
promotes a scientific law.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .execution_policy import load_execution_policy, require_action
from .research_progression_gates import ProgressionGateConfig, evaluate_progression_gates
from .schema import digest_payload

OWNER_ID = "U5-ATTEMPT-SCHEDULER/1.2.0"
SCHEMA = "phi-u5-attempt-scheduler/v1.2"
ALLOWED_OUTCOMES = frozenset({"U5_PASS", "U5_FAIL", "U5_DATA_PENDING", "U5_BLOCKED"})


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = digest_payload({k: v for k, v in payload.items() if k != "digest"})
    return payload


@dataclass(frozen=True)
class U5AttemptConfig:
    max_attempts: int = 50
    require_ood: bool = True
    require_replication: bool = True
    require_falsification_protocol: bool = True
    min_ood_fractional_improvement: float = 0.0
    min_complexity_penalized_delta_ll: float = 0.0
    write_canonical_registry: bool = False
    auto_promote_scientific_law: bool = False

    def validate(self) -> None:
        if int(self.max_attempts) < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.write_canonical_registry:
            raise PermissionError("U5AttemptScheduler must not write canonical registry")
        if self.auto_promote_scientific_law:
            raise PermissionError("U5AttemptScheduler must not auto-promote scientific law")
        ProgressionGateConfig(
            require_ood=self.require_ood,
            require_replication=self.require_replication,
            require_falsification_protocol=self.require_falsification_protocol,
            min_ood_fractional_improvement=self.min_ood_fractional_improvement,
            min_complexity_penalized_delta_ll=self.min_complexity_penalized_delta_ll,
        ).validate()

    def progression_config(self) -> ProgressionGateConfig:
        return ProgressionGateConfig(
            require_ood=self.require_ood,
            require_replication=self.require_replication,
            require_falsification_protocol=self.require_falsification_protocol,
            min_ood_fractional_improvement=self.min_ood_fractional_improvement,
            min_complexity_penalized_delta_ll=self.min_complexity_penalized_delta_ll,
        )


@dataclass
class U5AttemptResult:
    candidate_id: str
    outcome: str
    gates: dict[str, bool] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    pending_reasons: list[str] = field(default_factory=list)
    verification_digest: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        if self.outcome not in ALLOWED_OUTCOMES:
            raise ValueError(f"illegal outcome: {self.outcome}")
        return {
            "candidate_id": self.candidate_id,
            "outcome": self.outcome,
            "gates": dict(self.gates),
            "reasons": list(self.reasons),
            "pending_reasons": list(self.pending_reasons),
            "verification_digest": self.verification_digest,
            "details": dict(self.details),
        }


class U5AttemptScheduler:
    owner_id = OWNER_ID

    def __init__(self, root: str | Path | None = None, *, verifier: Any | None = None) -> None:
        self.root = Path(root) if root is not None else None
        if verifier is None:
            from .scientific_verification import ScientificVerificationCore
            verifier = ScientificVerificationCore()
        self.verifier = verifier

    def _policy(self) -> Mapping[str, Any]:
        if self.root is None:
            return {
                "automatic_scientific_law_promotion": False,
                "automatic_research_triage": True,
                "automatic_u5_attempts": True,
                "human_gated_promotion": True,
                "engineering_model_acceptance": True,
                "sandbox_profiles_allowed": ["STRICT", "RESEARCH", "WIDE"],
                "u5_attempt_writes_canonical_registry": False,
                "discriminating_experiment_may_auto_promote": False,
                "human_confirmation_is_scientific_evidence": False,
                "engineering_acceptance_is_scientific_law": False,
            }
        return load_execution_policy(self.root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "purpose": "run U4->U5 verification attempts; never promote",
            "allowed_outcomes": sorted(ALLOWED_OUTCOMES),
            "hard_boundaries": {
                "canonical_registry_mutated": False,
                "scientific_law_promoted": False,
                "axis_canonicalized": False,
                "automatic_scientific_promotion": False,
                "verification_replayed_each_attempt": True,
            },
            "pipeline": [
                "LOAD_CANDIDATE", "REPLAY_VERIFY_BUNDLE", "SHARED_PROGRESSION_GATES",
                "CLASSIFY_OUTCOME", "RECEIPT",
            ],
        }
        return _with_digest(payload)

    @staticmethod
    def _classify(
        verification: Mapping[str, Any],
        progression: Mapping[str, Any],
    ) -> tuple[str, list[str], list[str]]:
        overall = str(verification.get("overall_status", "")).strip().upper()
        evidence_ready = verification.get("evidence_ready_for_domain") is True
        candidate_allowed = verification.get("scientific_candidate_allowed") is True
        world_ready = verification.get("world_attestation_ready") is True
        evidence_class = str(verification.get("evidence_class", "")).strip().upper()
        verification_digest = bool(str(verification.get("verification_digest", "")).strip())
        hard_reasons = list(progression.get("hard_fail_reasons", ()))
        pending_reasons = list(progression.get("pending_reasons", ()))

        if not verification:
            return "U5_BLOCKED", ["scientific verification unavailable"], pending_reasons
        if not verification_digest:
            pending_reasons.append("verification_digest missing")

        # A central evidence failure is fail-closed.  This is distinct from an
        # otherwise-valid bundle that merely lacks WORLD attestation.
        if (not evidence_ready) or overall.startswith("FAIL_") or overall.startswith("REJECT_"):
            return "U5_FAIL", hard_reasons + [f"scientific_verification={overall or 'NOT_READY'}"], pending_reasons

        if hard_reasons:
            return "U5_FAIL", hard_reasons, pending_reasons
        if progression.get("all_required_progression_gates_pass") is not True:
            return "U5_DATA_PENDING", [], pending_reasons or ["required progression gate incomplete"]

        # MODEL_DERIVED / QUALIFICATION evidence can validate machinery but can
        # never itself become a world candidate.  More world evidence is needed,
        # so this is pending rather than a falsification of the hypothesis.
        non_world_classes = {"MODEL_DERIVED", "QUALIFICATION_FIXTURE", "SYNTHETIC_CONTROL"}
        if evidence_class in non_world_classes and not candidate_allowed:
            pending_reasons.append(f"world-class evidence required; current evidence_class={evidence_class}")
            return "U5_DATA_PENDING", [], pending_reasons

        if evidence_ready and not world_ready and not candidate_allowed:
            pending_reasons.append("WORLD attestation not ready")
            return "U5_DATA_PENDING", [], pending_reasons
        if not candidate_allowed:
            pending_reasons.append("scientific_candidate_allowed is false")
            return "U5_DATA_PENDING", [], pending_reasons
        if not verification_digest:
            return "U5_DATA_PENDING", [], pending_reasons
        return "U5_PASS", [], pending_reasons

    def attempt_one(
        self,
        candidate: Mapping[str, Any],
        *,
        config: U5AttemptConfig | None = None,
    ) -> Mapping[str, Any]:
        cfg = config or U5AttemptConfig()
        cfg.validate()
        require_action(self._policy(), "U5_ATTEMPT")

        candidate_id = str(candidate.get("candidate_id") or candidate.get("proposal_id") or "").strip()
        if not candidate_id:
            result = U5AttemptResult(candidate_id="", outcome="U5_BLOCKED", reasons=["candidate_id missing"])
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id, "result": result.to_dict(),
                "promotion_allowed": False, "mutation_performed": False,
                "claim_boundary": self._claim_boundary(),
            })

        bundle = dict(candidate.get("scientific_verification_bundle") or {})
        if not bundle:
            result = U5AttemptResult(candidate_id=candidate_id, outcome="U5_BLOCKED", reasons=["missing scientific_verification_bundle"])
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id, "result": result.to_dict(),
                "promotion_allowed": False, "mutation_performed": False,
                "claim_boundary": self._claim_boundary(),
            })

        verification = dict(self.verifier.verify_bundle(bundle))
        progression = dict(evaluate_progression_gates(candidate, config=cfg.progression_config()))
        outcome, hard, pending = self._classify(verification, progression)
        result = U5AttemptResult(
            candidate_id=candidate_id,
            outcome=outcome,
            gates=dict(progression.get("gates", {})),
            reasons=hard,
            pending_reasons=pending,
            verification_digest=str(verification.get("verification_digest", "")),
            details={
                "verification_overall_status": verification.get("overall_status"),
                "evidence_class": verification.get("evidence_class"),
                "evidence_ready_for_domain": verification.get("evidence_ready_for_domain"),
                "world_attestation_ready": verification.get("world_attestation_ready"),
                "scientific_candidate_allowed": verification.get("scientific_candidate_allowed"),
                "progression_gate_digest": progression.get("digest"),
            },
        )
        return _with_digest({
            "schema": SCHEMA, "owner_id": self.owner_id, "result": result.to_dict(),
            "promotion_allowed": False, "mutation_performed": False,
            "claim_boundary": self._claim_boundary(),
        })

    def run_batch(
        self,
        candidates: Sequence[Mapping[str, Any]],
        *,
        config: U5AttemptConfig | None = None,
    ) -> Mapping[str, Any]:
        cfg = config or U5AttemptConfig()
        cfg.validate()
        require_action(self._policy(), "U5_ATTEMPT")
        rows: list[dict[str, Any]] = []
        counts = {name: 0 for name in ALLOWED_OUTCOMES}
        for candidate in list(candidates)[: int(cfg.max_attempts)]:
            row = dict(self.attempt_one(candidate, config=cfg)["result"])
            rows.append(row)
            counts[row["outcome"]] += 1
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": "U5_BATCH_COMPLETE",
            "attempted": len(rows),
            "max_attempts": int(cfg.max_attempts),
            "counts": counts,
            "results": rows,
            "promotion_allowed": False,
            "mutation_performed": False,
            "claim_boundary": self._claim_boundary(),
        })

    @staticmethod
    def _claim_boundary() -> dict[str, Any]:
        return {
            "scientific_law_promoted": False,
            "canonical_registry_mutated": False,
            "axis_canonicalized": False,
            "u5_pass_is_not_law": True,
            "u5_pass_is_not_human_authorization": True,
            "next_step_if_pass": "read-only promotion qualification, then digest-bound human authorization",
        }
