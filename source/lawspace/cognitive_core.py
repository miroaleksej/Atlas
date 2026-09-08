"""Φ-Cognitive Core: structural learning over the existing Φ-LawSpace owners.

The cognitive core is deliberately a meta-orchestrator, not a second scientific
solver.  It delegates missing-axis discovery and research-local mounting to the
existing AdaptiveAxisDiscoveryOwner / DynamicAxisAdmissionOwner, preserves the
ScientificResearchCycleOwner and ScientificPromotionCore boundaries, and adds
capabilities that were absent from v9.3.0 and v9.4.0:

* persistent provenance-bound episodic/procedural memory;
* a runtime-derived self model of capabilities and epistemic boundaries;
* question reformulation when the current coordinate system is insufficient;
* skill-macro formation/reuse over already-authoritative owner operations;
* representation-first communication induction, grounded semantics, receiver modelling and compositional code synthesis.

No internet/literature access exists in this module.  Materialized candidate and
axis counts are treated as executed anchors, never as ceilings of Φ-space.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .adaptive_axis import AdaptiveAxisDiscoveryOwner
from .axis_modeling import AxisModelingOwner
from .domains import DOMAIN_REGISTRIES, canonical_axis_count
from .research_cycle import ScientificResearchCycleOwner
from .schema import digest_payload

SCHEMA = "phi-cognitive-core/v3"
OWNER_ID = "PHI-COGNITIVE-CORE/1.2.0"
MEMORY_OWNER_ID = "PERSISTENT-EPISTEMIC-MEMORY/1.0.0"
SELF_MODEL_OWNER_ID = "PHI-SELF-MODEL/1.0.0"
QUESTION_REFORMULATION_OWNER_ID = "QUESTION-REFORMULATION/1.0.0"
SKILL_FORMATION_OWNER_ID = "STRUCTURAL-SKILL-FORMATION/1.0.0"
GOAL_ACTION_OWNER_ID = "EPISTEMIC-GOAL-ACTION-POLICY/1.0.0"
COMMUNICATION_OWNER_ID = "PHI-COMMUNICATION-GROUNDING/1.0.0"
MODEL_OF_OTHER_OWNER_ID = "MODEL-OF-OTHER/1.0.0"
COMMUNICATION_CODE_OWNER_ID = "COMMUNICATION-CODE-SYNTHESIS/1.0.0"
STATE_SCHEMA = "phi-cognitive-state/v1"
RELEASE = "9.7.0"


class PersistentEpistemicMemoryOwner:
    """Atomic content-addressed state ledger for cognitive episodes and skills."""

    owner_id = MEMORY_OWNER_ID

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _empty(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": STATE_SCHEMA,
            "owner": self.owner_id,
            "release": RELEASE,
            "state_origin": "NO_PRIOR_RESIDENT_COGNITIVE_STATE_PRESENT_IN_9_3_0",
            "episodes": [],
            "skills": [],
            "self_model": {},
        }
        payload["state_digest"] = digest_payload(payload)
        return payload

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema") != STATE_SCHEMA or state.get("owner") != self.owner_id:
            raise ValueError("unsupported cognitive-state schema/owner")
        expected = digest_payload({k: v for k, v in state.items() if k != "state_digest"})
        if state.get("state_digest") != expected:
            raise ValueError("cognitive-state digest mismatch")
        if not isinstance(state.get("episodes"), list) or not isinstance(state.get("skills"), list):
            raise ValueError("cognitive state requires episodes and skills lists")
        return state

    def commit(
        self,
        *,
        episode: Mapping[str, Any],
        skills: Sequence[Mapping[str, Any]],
        self_model: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        state = self.load()
        episode_row = dict(episode)
        episode_id = str(episode_row.get("episode_id", "")).strip()
        if not episode_id:
            raise ValueError("episode_id is required")
        if any(str(row.get("episode_id")) == episode_id for row in state["episodes"]):
            raise ValueError(f"duplicate cognitive episode_id {episode_id!r}")
        previous = str(state["episodes"][-1].get("digest", "")) if state["episodes"] else "GENESIS"
        episode_row["previous_episode_digest"] = previous
        episode_row["digest"] = digest_payload({k: v for k, v in episode_row.items() if k != "digest"})
        state["episodes"].append(episode_row)

        skill_by_id = {str(row.get("skill_id")): dict(row) for row in state.get("skills", ())}
        for raw in skills:
            row = dict(raw)
            skill_id = str(row.get("skill_id", "")).strip()
            if not skill_id:
                raise ValueError("persisted skill requires skill_id")
            row["digest"] = digest_payload({k: v for k, v in row.items() if k != "digest"})
            skill_by_id[skill_id] = row
        state["skills"] = [skill_by_id[k] for k in sorted(skill_by_id)]
        state["self_model"] = dict(self_model)
        state["state_digest"] = digest_payload({k: v for k, v in state.items() if k != "state_digest"})

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return {
            "owner": self.owner_id,
            "status": "COGNITIVE_STATE_COMMITTED",
            "path": str(self.path),
            "episode_count": len(state["episodes"]),
            "skill_count": len(state["skills"]),
            "state_digest": state["state_digest"],
            "episode_digest": episode_row["digest"],
        }


class PhiSelfModelOwner:
    """Derive what the current executable system can and cannot claim/do."""

    owner_id = SELF_MODEL_OWNER_ID

    def derive(self, runtime: Any, memory_state: Mapping[str, Any], *, current_episode: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        research_contract = ScientificResearchCycleOwner(runtime).contract()
        payload = {
            "schema": "phi-self-model/v1",
            "owner": self.owner_id,
            "runtime": {
                "source_owner_passports": len(runtime.catalog.passports),
                "materialized_candidates": len(runtime.candidates),
                "canonical_axes": canonical_axis_count(),
                "registered_domains": len(DOMAIN_REGISTRIES),
            },
            "space_boundary": {
                "materialized_candidates_are_space_ceiling": False,
                "canonical_axis_count_is_space_ceiling": False,
                "adaptive_axis_birth_allowed": True,
                "unmaterialized_regions_may_exist": True,
                "future_axes_may_be_created_under_gates": True,
                "fully_unobserved_generated_coordinates_can_be_proposed_from_residual_geometry": True,
            },
            "authoritative_owners": {
                "scientific_research_cycle": research_contract.get("owner"),
                "adaptive_axis_discovery": AdaptiveAxisDiscoveryOwner.owner_id,
                "axis_modeling": AxisModelingOwner.owner_id,
                "persistent_memory": MEMORY_OWNER_ID,
                "question_reformulation": QUESTION_REFORMULATION_OWNER_ID,
                "skill_formation": SKILL_FORMATION_OWNER_ID,
                "epistemic_goal_action": GOAL_ACTION_OWNER_ID,
                "communication_grounding": COMMUNICATION_OWNER_ID,
                "model_of_other": MODEL_OF_OTHER_OWNER_ID,
                "communication_code_synthesis": COMMUNICATION_CODE_OWNER_ID,
            },
            "memory": {
                "episode_count": len(memory_state.get("episodes", ())),
                "skill_count": len(memory_state.get("skills", ())),
            },
            "current_episode": {
                "episode_id": current_episode.get("episode_id") if current_episode else None,
                "question_class_after": current_episode.get("question_reformulation", {}).get("question_class_after") if current_episode else None,
                "research_local_axes": list(current_episode.get("research_region", {}).get("research_local_axis_ids", ())) if current_episode else [],
            },
            "hard_boundaries": {
                "scientific_truth_can_be_assigned_by_cognitive_core": False,
                "canonical_axis_can_be_mutated_by_cognitive_core": False,
                "general_world_actuator_bound": False,
                "consciousness_claimed": False,
                "human_understanding_claimed_complete": False,
                "unknown_language_decipherment_claimed_complete": False,
                "animal_language_translation_claimed": False,
                "generated_axis_is_independent_physical_dimension": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload


class QuestionReformulationOwner:
    """Change the *type of question* when the old coordinates are insufficient."""

    owner_id = QUESTION_REFORMULATION_OWNER_ID
    provenance_axis_ids = (
        "model_failure_class",
        "identifiability",
        "observability",
        "experiment_design",
        "next_measurement_policy",
        "truth_access_boundary",
    )

    def __init__(self) -> None:
        missing = [x for x in self.provenance_axis_ids if x not in DOMAIN_REGISTRIES["systems_control"].axes]
        if missing:
            raise RuntimeError(f"question reformulation provenance axes missing: {missing}")

    @staticmethod
    def classify(scan_result: Mapping[str, Any]) -> str:
        summary = dict(scan_result.get("scan_summary", {}) or {})
        ready = list(summary.get("causal_ready_candidate_dimensions", ()))
        candidates = list(summary.get("high_information_candidate_dimensions", ()))
        if len(ready) == 1:
            return "REPRESENTATION_DEFICIENCY_IDENTIFIED"
        if len(ready) > 1:
            return "IDENTIFIABILITY_DEFICIENCY_MULTIPLE_AXES"
        if candidates:
            return "OBSERVATION_OR_IDENTIFIABILITY_DEFICIENCY"
        return "SEARCH_SPACE_OR_OBSERVATION_DEFICIENCY_UNRESOLVED"

    def reformulate(self, *, question: str, scan_result: Mapping[str, Any]) -> Mapping[str, Any]:
        original = str(question).strip()
        if not original:
            raise ValueError("question is required")
        summary = dict(scan_result.get("scan_summary", {}) or {})
        ready = list(summary.get("causal_ready_candidate_dimensions", ()))
        candidates = list(summary.get("high_information_candidate_dimensions", ()))
        rows = {str(r.get("context_dimension")): dict(r) for r in scan_result.get("candidate_axes", ())}
        failure = self.classify(scan_result)

        if len(ready) == 1:
            axis_id = ready[0]
            values = list(rows.get(axis_id, {}).get("values", ()))
            value_text = ", ".join(values[:8]) if values else "наблюдаемые значения"
            rewritten = (
                f"При условии, что исследовательская координата «{axis_id}» измерена до outcome "
                f"(наблюдаемые значения: {value_text}), {original} "
                "Как меняется ответ между значениями этой координаты и исчезает ли исходный residual "
                "на независимых studies / OOD-наблюдениях?"
            )
            after = "CONDITIONAL_COUNTERFACTUAL_BY_DISCOVERED_AXIS"
            status = "QUESTION_REFORMULATED_BY_SINGLE_CAUSAL_READY_AXIS"
            selected = [axis_id]
        elif len(ready) > 1:
            joined = ", ".join(f"«{x}»" for x in ready)
            rewritten = (
                f"Исходный вопрос «{original}» неидентифицируем в текущей форме: какие из координат {joined} "
                "имеют независимый причинно-различимый вклад, и какое заранее определённое измерение различит "
                "их до выбора объяснения?"
            )
            after = "DISCRIMINATING_IDENTIFIABILITY_QUESTION"
            status = "QUESTION_REFORMULATED_FOR_AXIS_IDENTIFIABILITY"
            selected = ready
        elif candidates:
            joined = ", ".join(f"«{x}»" for x in candidates[:8])
            rewritten = (
                f"Для вопроса «{original}» найдена residual-структура по координатам {joined}, но causal-readiness "
                "не пройден. Какие независимые наблюдения/репликации сделают эти координаты различимыми и "
                "проверят переносимость вне исходных records?"
            )
            after = "MEASUREMENT_AND_REPLICATION_QUESTION"
            status = "QUESTION_REFORMULATED_FOR_MISSING_EVIDENCE"
            selected = candidates
        else:
            rewritten = (
                f"Какая дополнительная наблюдаемая координата или новый owner-connected region может сделать "
                f"вопрос «{original}» идентифицируемым, не предполагая заранее форму ответа?"
            )
            after = "REPRESENTATION_SEARCH_QUESTION"
            status = "QUESTION_REFORMULATED_FOR_SPACE_EXPANSION"
            selected = []

        evidence_rows = [rows[x] for x in selected if x in rows]
        payload = {
            "schema": "phi-question-reformulation/v1",
            "owner": self.owner_id,
            "question_before": original,
            "question_after": rewritten,
            "question_class_before": "USER_OR_RESEARCH_QUESTION",
            "question_class_after": after,
            "model_failure_class": failure,
            "selected_axis_ids": selected,
            "provenance_systems_control_axes": list(self.provenance_axis_ids),
            "reformulation_evidence": [
                {
                    "axis_id": row.get("context_dimension"),
                    "information_gain_bits": row.get("information_gain_bits"),
                    "grouped_permutation_p": row.get("grouped_study_exact_permutation", {}).get("p_value"),
                    "loso_gain": row.get("leave_one_study_out", {}).get("gain"),
                    "causal_readiness_pass": row.get("causal_readiness_pass"),
                }
                for row in evidence_rows
            ],
            "status": status,
            "claim_boundary": {
                "reformulated_question_is_true_answer": False,
                "selected_research_axis_is_world_truth": False,
                "question_reformulation_may_change_research_coordinates": True,
            },
        }
        payload["question_before_digest"] = digest_payload(original)
        payload["question_after_digest"] = digest_payload(rewritten)
        payload["digest"] = digest_payload(payload)
        return payload


    def reformulate_generated(self, *, question: str, axis_modeling_result: Mapping[str, Any]) -> Mapping[str, Any]:
        """Reframe a question around a generated coordinate without treating it as truth."""
        original = str(question).strip()
        if not original:
            raise ValueError("question is required")
        best = dict(axis_modeling_result.get("best_axis_birth") or {})
        admission = dict(axis_modeling_result.get("semantic_axis_admission") or {})
        status0 = str(best.get("status", ""))
        admitted = admission.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS"
        if status0 in {"AXIS_BIRTH_OOD_VALIDATED", "AXIS_BIRTH_PROMISING_EXPLORATORY"} and admitted:
            axis_id = str(best.get("axis_id"))
            source_axis = str(best.get("source_axis_id"))
            rewritten = (
                f"Для вопроса «{original}» текущая измеренная координатная система оставляет устойчивый residual. "
                f"Owner AXIS-MODELING синтезировал research-local координату «{axis_id}» из residual geometry по "
                f"наблюдаемой оси «{source_axis}». Сохраняется ли её predictive advantage на независимых regimes/replications, "
                "какое независимо измеримое состояние или механизм даёт этой координате grounding, и исчезает ли residual "
                "после такого grounding без превращения derived feature в заранее объявленную физическую ось?"
            )
            qclass = "GENERATED_AXIS_CONDITIONAL_AND_GROUNDING_QUESTION"
            failure = "LATENT_REPRESENTATION_DEFICIENCY_IDENTIFIED"
            status = "QUESTION_REFORMULATED_BY_GENERATED_AXIS"
            selected = [axis_id]
        else:
            rewritten = (
                f"Для вопроса «{original}» AXIS-MODELING не нашёл OOD-устойчивой generated coordinate. "
                "Какой другой owner-connected region, измерение или тип residual representation может сделать задачу "
                "идентифицируемой, не выбирая форму скрытой переменной заранее?"
            )
            qclass = "REPRESENTATION_SEARCH_QUESTION"
            failure = "GENERATED_AXIS_SEARCH_FAILED_OR_NOT_REQUIRED"
            status = "QUESTION_REFORMULATED_FOR_SPACE_EXPANSION"
            selected = []
        payload = {
            "schema": "phi-question-reformulation/v2",
            "owner": self.owner_id,
            "question_before": original,
            "question_after": rewritten,
            "question_class_before": "USER_OR_RESEARCH_QUESTION",
            "question_class_after": qclass,
            "model_failure_class": failure,
            "selected_axis_ids": selected,
            "axis_modeling_digest": axis_modeling_result.get("digest"),
            "generated_axis_evidence": {
                "axis_id": best.get("axis_id"),
                "source_axis_id": best.get("source_axis_id"),
                "status": best.get("status"),
                "ood_rmse_fractional_improvement": best.get("ood_rmse_fractional_improvement"),
                "local_multiscale_robust_fraction": best.get("local_multiscale_robust_fraction"),
                "derived_feature_identifiability_pass": best.get("derived_feature_identifiability_pass"),
                "semantic_admission_status": admission.get("status"),
            },
            "status": status,
            "claim_boundary": {
                "reformulated_question_is_true_answer": False,
                "generated_axis_is_world_truth": False,
                "generated_axis_is_independent_physical_dimension": False,
                "independent_grounding_required": bool(selected),
                "question_reformulation_may_change_research_coordinates": True,
            },
        }
        payload["question_before_digest"] = digest_payload(original)
        payload["question_after_digest"] = digest_payload(rewritten)
        payload["digest"] = digest_payload(payload)
        return payload


class StructuralSkillFormationOwner:
    """Compress repeated successful owner traces into reusable macro skills."""

    owner_id = SKILL_FORMATION_OWNER_ID
    minimum_independent_environments = 2

    def _signature(self, episode: Mapping[str, Any]) -> str:
        payload = {
            "trace": list(episode.get("transition_trace", ())),
            "question_class_after": episode.get("question_reformulation", {}).get("question_class_after"),
            "guard_class": episode.get("question_reformulation", {}).get("model_failure_class"),
            "representation_route": episode.get("representation_route", "MEASURED_ADAPTIVE_AXIS"),
        }
        return digest_payload(payload)

    def find_reusable(self, memory_state: Mapping[str, Any], *, guard_class: str) -> Mapping[str, Any] | None:
        for row in memory_state.get("skills", ()):
            guard = dict(row.get("application_guard", {}) or {})
            if row.get("status") == "PROMOTED_REUSABLE_SKILL" and guard.get("model_failure_class") == guard_class:
                return dict(row)
        return None

    def form(self, episodes: Sequence[Mapping[str, Any]], existing_skills: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]:
        groups: dict[str, list[Mapping[str, Any]]] = {}
        for episode in episodes:
            if not str(episode.get("question_reformulation", {}).get("status", "")).startswith("QUESTION_REFORMULATED"):
                continue
            signature = self._signature(episode)
            groups.setdefault(signature, []).append(episode)
        existing = {str(row.get("pattern_signature")): dict(row) for row in existing_skills}
        new_skills: list[Mapping[str, Any]] = []
        rows = []
        for signature, support in sorted(groups.items()):
            environments = sorted({str(e.get("environment_id", "")) for e in support if str(e.get("environment_id", ""))})
            independent = len(environments)
            qualifies = independent >= self.minimum_independent_environments
            if qualifies:
                exemplar = support[0]
                q = dict(exemplar.get("question_reformulation", {}))
                skill_id = "SKILL-" + signature[:24].upper()
                skill = {
                    "skill_id": skill_id,
                    "owner": self.owner_id,
                    "pattern_signature": signature,
                    "status": "PROMOTED_REUSABLE_SKILL",
                    "support_episode_ids": sorted(str(e.get("episode_id")) for e in support),
                    "independent_environment_ids": environments,
                    "macro_steps": (
                        [
                            {"owner": AxisModelingOwner.owner_id, "operation": "run"},
                            {"owner": "DYNAMIC-AXIS-ADMISSION/6.24.0", "operation": "assess"},
                            {"owner": QUESTION_REFORMULATION_OWNER_ID, "operation": "reformulate_generated"},
                            {"owner": OWNER_ID, "operation": "mount_generated_research_region"},
                        ]
                        if exemplar.get("representation_route") == "GENERATED_AXIS_MODELING"
                        else [
                            {"owner": AdaptiveAxisDiscoveryOwner.owner_id, "operation": "scan"},
                            {"owner": AdaptiveAxisDiscoveryOwner.owner_id, "operation": "build_proposal_from_scan"},
                            {"owner": "DYNAMIC-AXIS-ADMISSION/6.24.0", "operation": "assess"},
                            {"owner": QUESTION_REFORMULATION_OWNER_ID, "operation": "reformulate"},
                            {"owner": AdaptiveAxisDiscoveryOwner.owner_id, "operation": "mount_research_region"},
                        ]
                    ),
                    "application_guard": {
                        "model_failure_class": q.get("model_failure_class"),
                        "question_class_after": q.get("question_class_after"),
                        "requires_gate_evidence": True,
                        "axis_identity_is_not_part_of_skill": True,
                        "representation_route": exemplar.get("representation_route", "MEASURED_ADAPTIVE_AXIS"),
                    },
                    "claim_boundary": {
                        "skill_is_new_scientific_law": False,
                        "skill_can_bypass_axis_gates": False,
                        "skill_reuses_authoritative_owners": True,
                    },
                }
                skill["digest"] = digest_payload(skill)
                new_skills.append(existing.get(signature, skill))
            rows.append({
                "pattern_signature": signature,
                "support_count": len(support),
                "independent_environment_count": independent,
                "qualified": qualifies,
            })
        payload = {
            "schema": "phi-structural-skill-formation/v1",
            "owner": self.owner_id,
            "minimum_independent_environments": self.minimum_independent_environments,
            "patterns": rows,
            "skills": new_skills,
            "status": "SKILL_FORMATION_EVALUATED",
        }
        payload["digest"] = digest_payload(payload)
        return payload


class EpistemicGoalActionPolicyOwner:
    """Choose only epistemic actions justified by already-computed gates."""

    owner_id = GOAL_ACTION_OWNER_ID

    def choose(self, *, scan_result: Mapping[str, Any], reformulation: Mapping[str, Any]) -> Mapping[str, Any]:
        summary = dict(scan_result.get("scan_summary", {}) or {})
        ready = list(summary.get("causal_ready_candidate_dimensions", ()))
        candidates = list(summary.get("high_information_candidate_dimensions", ()))
        if len(ready) == 1:
            action = "REENTER_RESEARCH_WITH_REFORMULATED_QUESTION"
            reason = "one research-local axis passed the positive causal-readiness contract"
        elif len(ready) > 1:
            action = "DESIGN_DISCRIMINATING_MEASUREMENT_BEFORE_AXIS_SELECTION"
            reason = "multiple axes passed readiness and remain mutually non-identifiable"
        elif candidates:
            action = "COLLECT_INDEPENDENT_REPLICATION_AND_OOD_EVIDENCE"
            reason = "residual structure exists but positive causal-readiness gates are incomplete"
        else:
            action = "EXPAND_OWNER_CONNECTED_SPACE_WITHOUT_PRESELECTING_ANSWER"
            reason = "current measured context contains no qualified missing-axis signal"
        payload = {
            "schema": "phi-epistemic-goal-action-policy/v1",
            "owner": self.owner_id,
            "selected_action": action,
            "reason": reason,
            "question_digest": reformulation.get("question_after_digest"),
            "utility_invented": False,
            "truth_access_used": False,
            "general_world_actuation_claimed": False,
            "status": "EPISTEMIC_ACTION_SELECTED",
        }
        payload["digest"] = digest_payload(payload)
        return payload


    def choose_generated(self, *, axis_modeling_result: Mapping[str, Any], reformulation: Mapping[str, Any]) -> Mapping[str, Any]:
        best = dict(axis_modeling_result.get("best_axis_birth") or {})
        status0 = str(best.get("status", ""))
        admission = dict(axis_modeling_result.get("semantic_axis_admission") or {})
        if status0 == "AXIS_BIRTH_OOD_VALIDATED" and admission.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS":
            action = "SEEK_INDEPENDENT_GROUNDING_AND_REENTER_RESEARCH"
            reason = "generated coordinate survived regime-OOD and provisional semantic admission; independent grounding remains required"
        elif status0 == "AXIS_BIRTH_PROMISING_EXPLORATORY":
            action = "REPLICATE_GENERATED_AXIS_OOD_BEFORE_GROUNDING"
            reason = "generated coordinate improves OOD prediction but lacks measurement-uncertainty-qualified validation"
        else:
            action = "EXPAND_OWNER_CONNECTED_SPACE_WITHOUT_PRESELECTING_ANSWER"
            reason = "residual modeling did not justify mounting a generated research coordinate"
        payload = {
            "schema": "phi-epistemic-goal-action-policy/v2",
            "owner": self.owner_id,
            "selected_action": action,
            "reason": reason,
            "question_digest": reformulation.get("question_after_digest"),
            "utility_invented": False,
            "truth_access_used": False,
            "general_world_actuation_claimed": False,
            "status": "EPISTEMIC_ACTION_SELECTED",
        }
        payload["digest"] = digest_payload(payload)
        return payload


def _comm_entropy(values: Sequence[str]) -> float:
    n = len(values)
    if not n:
        return 0.0
    counts = Counter(values)
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def _comm_conditional_entropy(labels: Sequence[str], groups: Sequence[str]) -> float:
    n = len(labels)
    if not n:
        return 0.0
    buckets: dict[str, list[str]] = defaultdict(list)
    for y, g in zip(labels, groups):
        buckets[str(g)].append(str(y))
    return sum((len(v) / n) * _comm_entropy(v) for v in buckets.values())


def _comm_information_gain(labels: Sequence[str], groups: Sequence[str]) -> float:
    if len(labels) != len(groups) or len(set(labels)) < 2:
        return 0.0
    return max(0.0, _comm_entropy(labels) - _comm_conditional_entropy(labels, groups))


def _comm_majority(values: Sequence[str]) -> str:
    counts = Counter(str(x) for x in values)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if counts else ""


def _comm_distribution(values: Sequence[str]) -> dict[str, float]:
    counts = Counter(str(x) for x in values)
    n = sum(counts.values())
    return {k: v / n for k, v in sorted(counts.items())} if n else {}


def _comm_tv(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


def _comm_signal_units(signal: Any) -> tuple[str, ...]:
    """Return observed atomic units without assuming words or morphemes.

    Strings are normalized to NFC and exposed as Unicode code-point observations.
    A caller may supply a sequence of already-observed acoustic/gesture/event units.
    Neither path claims that the atomic observations are linguistic tokens.
    """
    if isinstance(signal, str):
        text = unicodedata.normalize("NFC", signal)
        return tuple(ch for ch in text if not ch.isspace())
    if isinstance(signal, Sequence) and not isinstance(signal, (bytes, bytearray)):
        units = tuple(str(x) for x in signal if str(x) not in ("", "UNKNOWN", "UNRESOLVED"))
        return units
    raise ValueError("signal must be a string or a sequence of observed units")


def _comm_context_signature(context: Mapping[str, Any]) -> str:
    return digest_payload({str(k): context[k] for k in sorted(context)})


class PhiCommunicationOwner:
    """Representation-first communication inference over unknown signal systems.

    This owner never assumes that a signal is a human language, that words exist,
    or that an observed receiver response is a mental state. It discovers repeated
    motifs from atomic observations, delegates candidate signal-coordinate scans to
    the existing AdaptiveAxisDiscoveryOwner, separates structural from grounded
    claims, and requires interventional matched-context contrasts before assigning
    a research-level communicative function.
    """

    owner_id = COMMUNICATION_OWNER_ID
    model_of_other_owner_id = MODEL_OF_OTHER_OWNER_ID
    code_owner_id = COMMUNICATION_CODE_OWNER_ID

    def __init__(self, axis_discovery: AdaptiveAxisDiscoveryOwner | None = None) -> None:
        self.axis_discovery = axis_discovery or AdaptiveAxisDiscoveryOwner()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-communication-grounding/v1",
            "owner": self.owner_id,
            "purpose": "species/language-neutral signal structure induction, grounding, receiver modelling and compositional code synthesis",
            "delegation": {
                "adaptive_signal_axis_scan": AdaptiveAxisDiscoveryOwner.owner_id,
                "canonical_axis_promotion": "DYNAMIC-AXIS-PROMOTION/8.0.0",
                "scientific_promotion": "SCIENTIFIC-PROMOTION-CORE/9.0.0",
            },
            "subowners": {
                "model_of_other": self.model_of_other_owner_id,
                "communication_code_synthesis": self.code_owner_id,
            },
            "observation_policy": {
                "human_language_assumed": False,
                "word_boundaries_assumed": False,
                "symbol_meanings_assumed": False,
                "animal_signals_assumed_to_be_language": False,
                "multimodal_observed_units_allowed": True,
                "adaptive_research_local_signal_axes_allowed": True,
            },
            "hard_boundaries": {
                "structure_implies_semantics": False,
                "association_implies_causation": False,
                "receiver_behavior_equals_mental_state": False,
                "semantic_translation_without_grounding_allowed": False,
                "generated_axis_is_world_truth": False,
                "generated_axis_requires_independent_grounding": True,
                "full_natural_language_synthesis_claimed": False,
                "canonical_registry_mutated": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    @staticmethod
    def _normalize_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if len(observations) < 2:
            raise ValueError("communication analysis requires at least two observations")
        rows: list[dict[str, Any]] = []
        for i, raw in enumerate(observations):
            row = dict(raw)
            rid = str(row.get("record_id") or f"COMM-R{i+1}")
            units = _comm_signal_units(row.get("signal"))
            if not units:
                raise ValueError(f"communication observation {rid!r} has an empty signal")
            environment_id = str(row.get("environment_id") or row.get("study_id") or rid)
            receiver_id = str(row.get("receiver_id") or "UNRESOLVED_RECEIVER")
            normalized = {
                **row,
                "record_id": rid,
                "environment_id": environment_id,
                "study_id": str(row.get("study_id") or environment_id),
                "receiver_id": receiver_id,
                "units": units,
                "context": dict(row.get("context", {}) or {}),
                "intervention": bool(row.get("intervention", False)),
            }
            rows.append(normalized)
        return rows

    @staticmethod
    def _discover_motifs(rows: Sequence[Mapping[str, Any]], *, max_order: int, minimum_episode_support: int) -> list[dict[str, Any]]:
        counts: Counter[tuple[str, ...]] = Counter()
        episode_support: Counter[tuple[str, ...]] = Counter()
        env_support: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for row in rows:
            units = tuple(row["units"])
            seen: set[tuple[str, ...]] = set()
            for order in range(1, min(max_order, len(units)) + 1):
                for start in range(len(units) - order + 1):
                    motif = units[start:start + order]
                    counts[motif] += 1
                    seen.add(motif)
            for motif in seen:
                episode_support[motif] += 1
                env_support[motif].add(str(row["environment_id"]))
        out = []
        for motif, support in episode_support.items():
            if support < minimum_episode_support:
                continue
            out.append({
                "motif": motif,
                "motif_id": "MOTIF-" + digest_payload(list(motif))[:16].upper(),
                "order": len(motif),
                "occurrence_count": int(counts[motif]),
                "episode_support": int(support),
                "environment_support": len(env_support[motif]),
            })
        return out

    @staticmethod
    def _annotate_motif_information(rows: Sequence[Mapping[str, Any]], motifs: Sequence[Mapping[str, Any]], *, meaning_key: str, response_key: str) -> list[dict[str, Any]]:
        meaning = [str(r.get(meaning_key, "")).strip() for r in rows]
        response = [str(r.get(response_key, "")).strip() for r in rows]
        meaning_available = all(meaning) and len(set(meaning)) >= 2
        response_available = all(response) and len(set(response)) >= 2
        annotated = []
        for raw in motifs:
            motif = tuple(raw["motif"])
            flags = []
            for row in rows:
                units = tuple(row["units"])
                present = any(units[i:i + len(motif)] == motif for i in range(len(units) - len(motif) + 1))
                flags.append("PRESENT" if present else "ABSENT")
            row = dict(raw)
            row["meaning_information_gain_bits"] = _comm_information_gain(meaning, flags) if meaning_available else 0.0
            row["response_information_gain_bits"] = _comm_information_gain(response, flags) if response_available else 0.0
            row["presence_count"] = sum(x == "PRESENT" for x in flags)
            row["absence_count"] = sum(x == "ABSENT" for x in flags)
            annotated.append(row)
        return sorted(
            annotated,
            key=lambda r: (
                -float(r["meaning_information_gain_bits"] + r["response_information_gain_bits"]),
                -int(r["environment_support"]), -int(r["episode_support"]), -int(r["order"]), str(r["motif_id"]),
            ),
        )

    @staticmethod
    def _transition_graph(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        edges: Counter[tuple[str, str]] = Counter()
        outgoing: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            units = tuple(row["units"])
            for a, b in zip(units, units[1:]):
                edges[(a, b)] += 1
                outgoing[a][b] += 1
        edge_rows = [
            {"from": a, "to": b, "count": c}
            for (a, b), c in sorted(edges.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        conditional_entropy = 0.0
        total = sum(edges.values())
        if total:
            for a, next_counts in outgoing.items():
                n = sum(next_counts.values())
                conditional_entropy += (n / total) * _comm_entropy([x for x, c in next_counts.items() for _ in range(c)])
        return {
            "edge_count": len(edge_rows),
            "edges": edge_rows[:128],
            "successor_conditional_entropy_bits": conditional_entropy,
        }

    @staticmethod
    def _composition_candidates(rows: Sequence[Mapping[str, Any]], motifs: Sequence[Mapping[str, Any]], *, target_key: str) -> list[Mapping[str, Any]]:
        labels = [str(r.get(target_key, "")).strip() for r in rows]
        if not all(labels) or len(set(labels)) < 2:
            return []
        top = list(motifs[:12])
        flags_by_id: dict[str, list[str]] = {}
        for m in top:
            motif = tuple(m["motif"])
            flags = []
            for row in rows:
                units = tuple(row["units"])
                present = any(units[i:i + len(motif)] == motif for i in range(len(units) - len(motif) + 1))
                flags.append("1" if present else "0")
            flags_by_id[str(m["motif_id"])] = flags
        out = []
        for a, b in itertools.combinations(top, 2):
            fa = flags_by_id[str(a["motif_id"])]
            fb = flags_by_id[str(b["motif_id"])]
            joint = [x + y for x, y in zip(fa, fb)]
            ig_a = _comm_information_gain(labels, fa)
            ig_b = _comm_information_gain(labels, fb)
            ig_joint = _comm_information_gain(labels, joint)
            synergy = ig_joint - max(ig_a, ig_b)
            if synergy > 1e-12:
                out.append({
                    "motif_a": a["motif_id"], "motif_b": b["motif_id"],
                    "individual_information_gain_bits": [ig_a, ig_b],
                    "joint_information_gain_bits": ig_joint,
                    "synergy_over_best_individual_bits": synergy,
                    "status": "COMPOSITIONAL_INTERACTION_CANDIDATE",
                })
        return sorted(out, key=lambda r: (-float(r["synergy_over_best_individual_bits"]), str(r["motif_a"]), str(r["motif_b"])))[:32]

    def _adaptive_signal_axis_scan(self, rows: Sequence[Mapping[str, Any]], motifs: Sequence[Mapping[str, Any]], *, target_key: str) -> Mapping[str, Any] | None:
        labels = [str(r.get(target_key, "")).strip() for r in rows]
        if not all(labels) or len(set(labels)) < 2:
            return None
        selected = [m for m in motifs[:12] if int(m.get("presence_count", 0)) and int(m.get("absence_count", 0))]
        if not selected:
            return None
        synthetic = []
        axis_to_motif: dict[str, Mapping[str, Any]] = {}
        for row, label in zip(rows, labels):
            context = {}
            units = tuple(row["units"])
            for m in selected:
                motif = tuple(m["motif"])
                present = any(units[i:i + len(motif)] == motif for i in range(len(units) - len(motif) + 1))
                axis_id = "signal_" + str(m["motif_id"]).lower().replace("-", "_")
                context[axis_id] = "PRESENT" if present else "ABSENT"
                axis_to_motif[axis_id] = {"motif_id": m["motif_id"], "motif": list(motif)}
            synthetic.append({
                "record_id": row["record_id"],
                "study_id": row["study_id"],
                "outcome_class": label,
                "context": context,
            })
        scan = dict(self.axis_discovery.scan(
            domain_id="systems_control",
            evidence_records=synthetic,
            minimum_coverage=1.0,
            minimum_information_gain_bits=0.01,
        ))
        scan["signal_axis_to_motif"] = axis_to_motif
        scan["canonical_registry_mutated"] = False
        return scan

    @staticmethod
    def _causal_signal_effects(rows: Sequence[Mapping[str, Any]], motifs: Sequence[Mapping[str, Any]], *, response_key: str, minimum_tv: float, minimum_independent_environments: int) -> Mapping[str, Any]:
        intervention_rows = [r for r in rows if r.get("intervention") and str(r.get(response_key, "")).strip()]
        if len(intervention_rows) < 4:
            return {
                "status": "CAUSAL_GROUNDING_BLOCKED_NO_INTERVENTIONAL_CONTRAST",
                "qualified_motif_ids": [], "motif_effects": [],
                "minimum_total_variation": minimum_tv,
                "minimum_independent_environments": minimum_independent_environments,
            }
        results = []
        for m in motifs[:16]:
            motif = tuple(m["motif"])
            by_env_context: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: {"treated": [], "control": []})
            for row in intervention_rows:
                units = tuple(row["units"])
                present = any(units[i:i + len(motif)] == motif for i in range(len(units) - len(motif) + 1))
                key = (str(row["environment_id"]), _comm_context_signature(dict(row.get("context", {}) or {})))
                by_env_context[key]["treated" if present else "control"].append(str(row[response_key]))
            env_effects: dict[str, list[float]] = defaultdict(list)
            matched_strata = []
            for (env, ctx), groups in sorted(by_env_context.items()):
                if not groups["treated"] or not groups["control"]:
                    continue
                tv = _comm_tv(_comm_distribution(groups["treated"]), _comm_distribution(groups["control"]))
                env_effects[env].append(tv)
                matched_strata.append({
                    "environment_id": env, "context_digest": ctx,
                    "treated_n": len(groups["treated"]), "control_n": len(groups["control"]),
                    "total_variation": tv,
                })
            per_env = {env: max(vals) for env, vals in env_effects.items() if vals}
            passing_envs = sorted(env for env, tv in per_env.items() if tv >= minimum_tv)
            qualified = len(passing_envs) >= minimum_independent_environments
            results.append({
                "motif_id": m["motif_id"], "motif": list(motif),
                "matched_context_stratum_count": len(matched_strata),
                "independent_environment_count": len(per_env),
                "passing_environment_ids": passing_envs,
                "environment_total_variation": per_env,
                "qualified_research_level_communicative_effect": qualified,
                "status": "INTERVENTIONAL_RECEIVER_EFFECT_REPLICATED" if qualified else "INTERVENTIONAL_EFFECT_NOT_REPLICATED",
            })
        qualified_ids = [r["motif_id"] for r in results if r["qualified_research_level_communicative_effect"]]
        return {
            "status": "CAUSAL_COMMUNICATIVE_EFFECT_QUALIFIED_RESEARCH_LEVEL" if qualified_ids else "CAUSAL_GROUNDING_NOT_QUALIFIED",
            "qualified_motif_ids": qualified_ids,
            "motif_effects": results,
            "minimum_total_variation": minimum_tv,
            "minimum_independent_environments": minimum_independent_environments,
            "claim_boundary": {
                "causal_effect_equals_dictionary_meaning": False,
                "matched_context_intervention_required": True,
                "scientific_truth_promoted": False,
            },
        }

    @staticmethod
    def _receiver_model(rows: Sequence[Mapping[str, Any]], motifs: Sequence[Mapping[str, Any]], *, response_key: str) -> Mapping[str, Any]:
        usable = [r for r in rows if str(r.get(response_key, "")).strip() and str(r.get("receiver_id", "")) not in ("", "UNRESOLVED_RECEIVER")]
        receivers = sorted(set(str(r["receiver_id"]) for r in usable))
        selected = list(motifs[:10])
        if len(receivers) < 3 or not selected:
            return {
                "owner": MODEL_OF_OTHER_OWNER_ID,
                "status": "MODEL_OF_OTHER_BLOCKED_INSUFFICIENT_INDEPENDENT_RECEIVERS",
                "receiver_count": len(receivers), "leave_one_receiver_out_gain": 0.0,
                "mental_state_claimed": False,
            }

        def signature(row: Mapping[str, Any]) -> str:
            units = tuple(row["units"])
            bits = []
            for m in selected:
                motif = tuple(m["motif"])
                bits.append("1" if any(units[i:i + len(motif)] == motif for i in range(len(units) - len(motif) + 1)) else "0")
            return "".join(bits)

        correct = baseline_correct = total = 0
        folds = []
        for held in receivers:
            train = [r for r in usable if str(r["receiver_id"]) != held]
            test = [r for r in usable if str(r["receiver_id"]) == held]
            train_y = [str(r[response_key]) for r in train]
            baseline = _comm_majority(train_y)
            by_sig: dict[str, list[str]] = defaultdict(list)
            for r in train:
                by_sig[signature(r)].append(str(r[response_key]))
            mapper = {k: _comm_majority(v) for k, v in by_sig.items()}
            fold_correct = fold_base = 0
            for r in test:
                y = str(r[response_key])
                pred = mapper.get(signature(r), baseline)
                fold_correct += int(pred == y)
                fold_base += int(baseline == y)
            correct += fold_correct; baseline_correct += fold_base; total += len(test)
            folds.append({"held_receiver_id": held, "n": len(test), "accuracy": fold_correct / len(test) if test else 0.0, "baseline_accuracy": fold_base / len(test) if test else 0.0})
        acc = correct / total if total else 0.0
        base = baseline_correct / total if total else 0.0
        gain = acc - base
        return {
            "owner": MODEL_OF_OTHER_OWNER_ID,
            "status": "BEHAVIORAL_RECEIVER_MODEL_GENERALIZES" if gain > 0 else "BEHAVIORAL_RECEIVER_MODEL_NOT_GENERALIZING",
            "receiver_count": len(receivers), "leave_one_receiver_out_accuracy": acc,
            "baseline_accuracy": base, "leave_one_receiver_out_gain": gain,
            "folds": folds,
            "mental_state_claimed": False,
            "behavioral_response_is_internal_belief_state": False,
        }

    def analyze(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        rows = self._normalize_observations(tuple(dict(x) for x in request.get("observations", ())))
        max_order = max(1, min(int(request.get("max_motif_order", 4)), 8))
        minimum_episode_support = max(2, int(request.get("minimum_episode_support", 2)))
        meaning_key = str(request.get("meaning_key", "world_state"))
        response_key = str(request.get("response_key", "receiver_response"))
        motifs0 = self._discover_motifs(rows, max_order=max_order, minimum_episode_support=minimum_episode_support)
        motifs = self._annotate_motif_information(rows, motifs0, meaning_key=meaning_key, response_key=response_key)
        transition = self._transition_graph(rows)
        meaning_labels = [str(r.get(meaning_key, "")).strip() for r in rows]
        response_labels = [str(r.get(response_key, "")).strip() for r in rows]
        grounding_present = all(meaning_labels) and len(set(meaning_labels)) >= 2
        response_present = all(response_labels) and len(set(response_labels)) >= 2
        target_key = meaning_key if grounding_present else response_key
        adaptive_scan = self._adaptive_signal_axis_scan(rows, motifs, target_key=target_key) if (grounding_present or response_present) else None
        composition = self._composition_candidates(rows, motifs, target_key=meaning_key) if grounding_present else []
        causal = self._causal_signal_effects(
            rows, motifs, response_key=response_key,
            minimum_tv=float(request.get("minimum_interventional_total_variation", 0.5)),
            minimum_independent_environments=max(2, int(request.get("minimum_independent_environments", 2))),
        )
        receiver_model = self._receiver_model(rows, motifs, response_key=response_key)
        causal_ids = set(causal.get("qualified_motif_ids", ()))
        grounded_ids = {
            str(m["motif_id"]) for m in motifs
            if float(m.get("meaning_information_gain_bits", 0.0)) > 0.0
        }
        grounded_causal = sorted(causal_ids & grounded_ids)
        if not grounding_present:
            grounding_status = "SEMANTICS_UNIDENTIFIABLE_NO_EXTERNAL_GROUNDING"
        elif grounded_causal:
            grounding_status = "GROUNDED_COMMUNICATIVE_FUNCTION_QUALIFIED_RESEARCH_LEVEL"
        else:
            grounding_status = "ASSOCIATIVE_GROUNDING_ONLY_NOT_CAUSALLY_IDENTIFIED"
        atomic_modes = sorted({"UNICODE_CODEPOINT_OBSERVATIONS" if isinstance(r.get("signal"), str) else "CALLER_SUPPLIED_OBSERVED_UNITS" for r in rows})
        payload = {
            "schema": "phi-communication-analysis/v1",
            "owner": self.owner_id,
            "contract": self.contract(),
            "observation_count": len(rows),
            "environment_count": len(set(str(r["environment_id"]) for r in rows)),
            "receiver_count": len(set(str(r["receiver_id"]) for r in rows if str(r["receiver_id"]) != "UNRESOLVED_RECEIVER")),
            "representation": {
                "atomic_observation_modes": atomic_modes,
                "word_boundaries_assumed": False,
                "alphabet_size": len({u for r in rows for u in r["units"]}),
                "transition_graph": transition,
                "motif_candidates": [{**m, "motif": list(m["motif"])} for m in motifs[:64]],
                "composition_candidates": composition,
                "status": "UNKNOWN_SIGNAL_STRUCTURE_INDUCED_FROM_OBSERVATIONS",
            },
            "adaptive_signal_axis_scan": adaptive_scan,
            "grounding": {
                "meaning_key": meaning_key,
                "grounding_observed": grounding_present,
                "status": grounding_status,
                "associative_grounded_motif_ids": sorted(grounded_ids),
                "causal_and_grounded_motif_ids": grounded_causal,
                "interventional_effects": causal,
            },
            "model_of_other": receiver_model,
            "claim_boundary": {
                "dictionary_translation_claimed": False,
                "unknown_human_language_fully_deciphered": False,
                "animal_language_claimed": False,
                "receiver_mental_state_inferred_as_fact": False,
                "semantic_claim_without_grounding": False,
                "canonical_axis_registry_mutated": False,
                "scientific_truth_promoted": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    @staticmethod
    def _minimal_distinguishing_axes(meanings: Sequence[Mapping[str, Any]]) -> tuple[list[str], str]:
        feature_ids = sorted({str(k) for row in meanings for k in dict(row.get("features", {}) or {})})
        varying = [f for f in feature_ids if len({str(dict(r.get("features", {}) or {}).get(f, "UNRESOLVED")) for r in meanings}) > 1]
        def unique_for(axes: Sequence[str]) -> bool:
            sigs = [tuple(str(dict(r.get("features", {}) or {}).get(a, "UNRESOLVED")) for a in axes) for r in meanings]
            return len(set(sigs)) == len(meanings)
        if len(varying) <= 16:
            for k in range(1, len(varying) + 1):
                for axes in itertools.combinations(varying, k):
                    if unique_for(axes):
                        return list(axes), "EXACT_MINIMUM_AXIS_SUBSET"
        selected: list[str] = []
        remaining = list(varying)
        while remaining and not unique_for(selected):
            best = None
            best_partitions = -1
            for axis in remaining:
                axes = [*selected, axis]
                partitions = len({tuple(str(dict(r.get("features", {}) or {}).get(a, "UNRESOLVED")) for a in axes) for r in meanings})
                if partitions > best_partitions:
                    best_partitions, best = partitions, axis
            if best is None:
                break
            selected.append(best); remaining.remove(best)
        if not selected or not unique_for(selected):
            raise ValueError("meaning features do not uniquely identify all meanings")
        return selected, "GREEDY_PARTITION_REFINEMENT"

    @staticmethod
    def _segment_codebook(values: Sequence[str], alphabet: Sequence[str], *, min_distance: int, max_length: int) -> tuple[dict[str, str], int]:
        values = sorted(set(str(x) for x in values))
        alphabet = tuple(str(x) for x in alphabet)
        if len(alphabet) < 2:
            raise ValueError("communication-code alphabet requires at least two symbols")
        for length in range(1, max_length + 1):
            capacity = len(alphabet) ** length
            if capacity > 200000:
                break
            candidates = ["".join(chars) for chars in itertools.product(alphabet, repeat=length)]
            selected: list[str] = []
            for code in candidates:
                if all(sum(a != b for a, b in zip(code, prior)) >= min_distance for prior in selected):
                    selected.append(code)
                    if len(selected) == len(values):
                        return dict(zip(values, selected)), length
        raise ValueError("cannot satisfy code capacity/minimum-distance constraints within max_segment_length")

    def synthesize_code(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        meanings = [dict(x) for x in request.get("meanings", ())]
        if len(meanings) < 2:
            raise ValueError("at least two meanings are required")
        ids = [str(r.get("meaning_id", "")).strip() for r in meanings]
        if any(not x for x in ids) or len(set(ids)) != len(ids):
            raise ValueError("meaning_id values must be non-empty and unique")
        alphabet = tuple(str(x) for x in request.get("alphabet", ("0", "1")))
        if len(set(alphabet)) != len(alphabet) or any(not x for x in alphabet):
            raise ValueError("alphabet symbols must be non-empty and unique")
        min_distance = max(1, int(request.get("minimum_segment_hamming_distance", 1)))
        max_segment_length = max(1, min(int(request.get("max_segment_length", 8)), 12))
        axes, selection_mode = self._minimal_distinguishing_axes(meanings)
        segments: dict[str, Mapping[str, Any]] = {}
        for axis in axes:
            values = [str(dict(r.get("features", {}) or {}).get(axis, "UNRESOLVED")) for r in meanings]
            book, length = self._segment_codebook(values, alphabet, min_distance=min_distance, max_length=max_segment_length)
            segments[axis] = {"segment_length": length, "value_to_code": book}
        codes = {}
        for row in meanings:
            feature_map = dict(row.get("features", {}) or {})
            code = "".join(str(segments[a]["value_to_code"][str(feature_map.get(a, "UNRESOLVED"))]) for a in axes)
            codes[str(row["meaning_id"])] = code
        if len(set(codes.values())) != len(codes):
            raise AssertionError("internal code synthesis failure: codes are not uniquely decodable")
        distances = []
        for a, b in itertools.combinations(codes.values(), 2):
            if len(a) != len(b):
                raise AssertionError("internal code synthesis failure: unequal complete code lengths")
            distances.append(sum(x != y for x, y in zip(a, b)))
        minimum_complete_distance = min(distances) if distances else 0
        payload = {
            "schema": "phi-communication-code-synthesis/v1",
            "owner": COMMUNICATION_CODE_OWNER_ID,
            "source_owner": self.owner_id,
            "meaning_count": len(meanings),
            "alphabet": list(alphabet),
            "semantic_geometry": {
                "selected_distinguishing_axes": axes,
                "axis_selection_mode": selection_mode,
                "all_meanings_distinguished": True,
            },
            "segment_codebooks": segments,
            "meaning_codes": codes,
            "verification": {
                "unique_decodability": len(set(codes.values())) == len(codes),
                "minimum_complete_code_hamming_distance": minimum_complete_distance,
                "requested_minimum_segment_hamming_distance": min_distance,
                "fixed_axis_order_decoder": axes,
                "compositionality_by_axis_factorization": True,
            },
            "objective_realized": "minimum distinguishing semantic axis subset + shortest per-axis segment satisfying requested error distance",
            "claim_boundary": {
                "full_natural_language_generated": False,
                "pragmatics_generated": False,
                "social_convention_emerged": False,
                "finite_compositional_communication_code_generated": True,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload


@dataclass(frozen=True)
class CognitiveCycleRequest:
    episode_id: str
    environment_id: str
    question: str
    domain_id: str
    evidence_records: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "CognitiveCycleRequest":
        return cls(
            episode_id=str(row.get("episode_id", "")).strip(),
            environment_id=str(row.get("environment_id", "")).strip(),
            question=str(row.get("question", "")).strip(),
            domain_id=str(row.get("domain_id", "")).strip(),
            evidence_records=tuple(dict(x) for x in row.get("evidence_records", ())),
        )

    def validate(self) -> None:
        if not self.episode_id or not self.environment_id or not self.question or not self.domain_id:
            raise ValueError("episode_id, environment_id, question and domain_id are required")
        if self.domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain {self.domain_id!r}")
        if len(self.evidence_records) < 2:
            raise ValueError("cognitive cycle requires at least two evidence records")


class PhiCognitiveCore:
    """One owner for Observe→Fail→DiscoverAxis→Reframe→Learn→Reuse."""

    owner_id = OWNER_ID

    def __init__(self, runtime: Any, memory_path: str | Path | None = None) -> None:
        self.runtime = runtime
        default = Path(runtime.external_state_path("cognitive_state")) if hasattr(runtime, "external_state_path") else (Path.home() / ".local" / "state" / "phi-compiler" / RELEASE / "cognitive_state.json")
        if memory_path is None:
            try:
                default.resolve(strict=False).relative_to(Path(runtime.root).resolve(strict=False))
            except ValueError:
                pass
            else:
                raise ValueError("cognitive mutable state must be outside the sealed runtime root")
        self.memory = PersistentEpistemicMemoryOwner(memory_path or default)
        self.axis_discovery = AdaptiveAxisDiscoveryOwner()
        self.axis_modeling = AxisModelingOwner()
        self.reformulation = QuestionReformulationOwner()
        self.skills = StructuralSkillFormationOwner()
        self.self_model = PhiSelfModelOwner()
        self.action_policy = EpistemicGoalActionPolicyOwner()
        self.communication = PhiCommunicationOwner(self.axis_discovery)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": self.owner_id,
            "pipeline": [
                "OBSERVE", "DETECT_REPRESENTATION_FAILURE", "DISCOVER_OR_REFINE_AXIS", "SYNTHESIZE_GENERATED_AXIS_IF_NEEDED",
                "PROVISIONAL_ADMISSION", "REFORMULATE_QUESTION", "MOUNT_RESEARCH_REGION",
                "SELECT_EPISTEMIC_ACTION", "PERSIST_EPISODE", "FORM_SKILL", "REUSE_SKILL",
            ],
            "delegation": {
                "adaptive_axis_discovery": AdaptiveAxisDiscoveryOwner.owner_id,
                "axis_modeling": AxisModelingOwner.owner_id,
                "scientific_research_cycle": ScientificResearchCycleOwner.owner_id,
                "scientific_promotion": "SCIENTIFIC-PROMOTION-CORE/9.0.0",
            },
            "cognitive_owners": {
                "persistent_memory": MEMORY_OWNER_ID,
                "self_model": SELF_MODEL_OWNER_ID,
                "question_reformulation": QUESTION_REFORMULATION_OWNER_ID,
                "skill_formation": SKILL_FORMATION_OWNER_ID,
                "goal_action_policy": GOAL_ACTION_OWNER_ID,
                "communication_grounding": COMMUNICATION_OWNER_ID,
                "model_of_other": MODEL_OF_OTHER_OWNER_ID,
                "communication_code_synthesis": COMMUNICATION_CODE_OWNER_ID,
            },
            "space_policy": {
                "materialized_registry_is_search_space_ceiling": False,
                "canonical_axis_registry_is_search_space_ceiling": False,
                "adaptive_axis_count_has_fixed_ceiling": False,
                "anchors_guide_but_do_not_define_space": True,
            },
            "hard_boundaries": {
                "parallel_scientific_solver_created": False,
                "parallel_axis_promotion_owner_created": False,
                "canonical_registry_mutated_implicitly": False,
                "skill_can_bypass_scientific_gates": False,
                "question_reformulation_is_answer": False,
                "internet_required": False,
                "communication_structure_implies_semantics": False,
                "receiver_behavior_equals_mental_state": False,
                "semantic_translation_without_grounding_allowed": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run(self, request: Mapping[str, Any], *, commit: bool = True) -> Mapping[str, Any]:
        req = CognitiveCycleRequest.from_mapping(request)
        req.validate()
        state_before = self.memory.load()
        self_before = self.self_model.derive(self.runtime, state_before)

        scan = self.axis_discovery.scan(domain_id=req.domain_id, evidence_records=req.evidence_records)
        candidate_dimensions = list(scan.get("scan_summary", {}).get("high_information_candidate_dimensions", ()))
        provisional = []
        for dimension in candidate_dimensions:
            proposal = self.axis_discovery.build_proposal_from_scan(
                scan_result=scan,
                source_dimension=str(dimension),
                evidence_records=req.evidence_records,
            )
            provisional.append(self.axis_discovery.admit_provisional_axis(
                scan_result=scan,
                source_dimension=str(dimension),
                proposal=proposal,
            ))
        research_region = self.axis_discovery.mount_research_region(
            domain_id=req.domain_id,
            provisional_admissions=provisional,
        )
        reform = self.reformulation.reformulate(question=req.question, scan_result=scan)
        guard_class = str(reform.get("model_failure_class", ""))
        reusable = self.skills.find_reusable(state_before, guard_class=guard_class)
        execution_route = "LEARNED_SKILL_MACRO" if reusable is not None else "DIRECT_AUTHORITATIVE_OWNER_ORCHESTRATION"
        action = self.action_policy.choose(scan_result=scan, reformulation=reform)

        trace = ["OBSERVE", "DETECT_REPRESENTATION_FAILURE"]
        if candidate_dimensions:
            trace += ["DISCOVER_AXIS", "PROVISIONAL_ADMIT"]
        trace.append("REFORMULATE_QUESTION")
        if research_region.get("research_local_axis_ids"):
            trace.append("MOUNT_LOCAL_RESEARCH_REGION")
        trace.append("SELECT_EPISTEMIC_ACTION")

        episode = {
            "episode_id": req.episode_id,
            "environment_id": req.environment_id,
            "domain_id": req.domain_id,
            "representation_route": "MEASURED_ADAPTIVE_AXIS",
            "question_before": req.question,
            "evidence_record_count": len(req.evidence_records),
            "evidence_digest": digest_payload(list(req.evidence_records)),
            "axis_scan": {
                "digest": scan.get("digest"),
                "scan_summary": scan.get("scan_summary"),
                "selected_rows": [
                    row for row in scan.get("candidate_axes", ())
                    if row.get("context_dimension") in candidate_dimensions
                ],
            },
            "provisional_axis_admissions": provisional,
            "research_region": research_region,
            "question_reformulation": reform,
            "epistemic_action": action,
            "transition_trace": trace,
            "execution_route": execution_route,
            "reused_skill_id": reusable.get("skill_id") if reusable else None,
            "claim_boundary": {
                "scientific_truth_promoted": False,
                "canonical_axis_registry_mutated": False,
                "world_novelty_claimed": False,
            },
        }
        episode["digest"] = digest_payload(episode)

        formation = self.skills.form(
            [*state_before.get("episodes", ()), episode],
            existing_skills=state_before.get("skills", ()),
        )
        merged_skill_rows: dict[str, Mapping[str, Any]] = {
            str(row.get("skill_id")): dict(row) for row in state_before.get("skills", ())
        }
        for row in formation.get("skills", ()):
            merged_skill_rows[str(row.get("skill_id"))] = dict(row)
        projected_state = {
            **state_before,
            "episodes": [*state_before.get("episodes", ()), episode],
            "skills": [merged_skill_rows[k] for k in sorted(merged_skill_rows)],
        }
        self_after = self.self_model.derive(self.runtime, projected_state, current_episode=episode)
        commit_receipt = None
        if commit:
            commit_receipt = self.memory.commit(
                episode=episode,
                skills=list(merged_skill_rows.values()),
                self_model=self_after,
            )

        payload = {
            "schema": SCHEMA,
            "owner": self.owner_id,
            "contract": self.contract(),
            "episode": episode,
            "self_model_before": self_before,
            "skill_formation": formation,
            "self_model_after": self_after,
            "memory_commit": commit_receipt,
            "status": "COGNITIVE_CYCLE_COMPLETE" if commit or commit_receipt is None else "COGNITIVE_CYCLE_BLOCKED",
            "claim_boundary": {
                "AGI_claimed": False,
                "consciousness_claimed": False,
                "general_world_actuation_available": False,
                "question_reformulation_executable": True,
                "persistent_structural_learning_executable": True,
                "skill_reuse_executable": True,
                "canonical_scientific_promotion_preserved": True,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload


    @staticmethod
    def _mount_generated_research_region(axis_modeling_result: Mapping[str, Any]) -> Mapping[str, Any]:
        admission = dict(axis_modeling_result.get("semantic_axis_admission") or {})
        axis = dict(admission.get("provisional_axis_definition") or {})
        proposal = dict(admission.get("proposal") or {})
        domain_id = str(proposal.get("domain_id", ""))
        mount = admission.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS" and bool(axis) and domain_id in DOMAIN_REGISTRIES
        ids = [str(axis.get("axis_id"))] if mount else []
        payload = {
            "schema": "phi-generated-axis-research-region/v1",
            "owner_id": OWNER_ID,
            "source_owner": AxisModelingOwner.owner_id,
            "domain_id": domain_id or None,
            "canonical_axis_count": DOMAIN_REGISTRIES[domain_id].axis_count if domain_id in DOMAIN_REGISTRIES else None,
            "research_local_axis_ids": ids,
            "research_region_axis_count": (DOMAIN_REGISTRIES[domain_id].axis_count + len(ids)) if domain_id in DOMAIN_REGISTRIES else None,
            "canonical_registry_mutated": False,
            "research_region_axes": [axis] if mount else [],
            "mount_allowed": mount,
            "independent_grounding_required": mount,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_generated_axis_cycle(self, request: Mapping[str, Any], *, commit: bool = True) -> Mapping[str, Any]:
        """Observe residual geometry -> generate research axis -> reframe -> persist/reuse.

        The input dataset contains only observed axes.  Any selected generated axis
        is created by AXIS-MODELING and remains research-local until the existing
        DynamicAxisPromotionOwner is independently satisfied.
        """
        episode_id = str(request.get("episode_id", "")).strip()
        environment_id = str(request.get("environment_id", "")).strip()
        question = str(request.get("question", "")).strip()
        modeling_request = dict(request.get("axis_modeling_request") or {})
        if not episode_id or not environment_id or not question or not modeling_request:
            raise ValueError("episode_id, environment_id, question and axis_modeling_request are required")
        state_before = self.memory.load()
        self_before = self.self_model.derive(self.runtime, state_before)
        modeling = self.axis_modeling.run(modeling_request)
        reform = self.reformulation.reformulate_generated(question=question, axis_modeling_result=modeling)
        guard_class = str(reform.get("model_failure_class", ""))
        reusable = self.skills.find_reusable(state_before, guard_class=guard_class)
        execution_route = "LEARNED_SKILL_MACRO" if reusable is not None else "DIRECT_AUTHORITATIVE_OWNER_ORCHESTRATION"
        research_region = self._mount_generated_research_region(modeling)
        action = self.action_policy.choose_generated(axis_modeling_result=modeling, reformulation=reform)
        best = dict(modeling.get("best_axis_birth") or {})
        trace = ["OBSERVE", "DETECT_REPRESENTATION_FAILURE", "AXIS_MODELING_RESIDUAL_SEARCH"]
        if research_region.get("research_local_axis_ids"):
            trace += ["GENERATE_AXIS", "PROVISIONAL_ADMIT", "MOUNT_LOCAL_RESEARCH_REGION"]
        trace += ["REFORMULATE_QUESTION", "SELECT_EPISTEMIC_ACTION"]
        episode = {
            "episode_id": episode_id,
            "environment_id": environment_id,
            "domain_id": research_region.get("domain_id"),
            "representation_route": "GENERATED_AXIS_MODELING",
            "question_before": question,
            "axis_modeling": {
                "digest": modeling.get("digest"),
                "final_status": modeling.get("final_status"),
                "dataset": modeling.get("dataset"),
                "best_axis_birth": best,
                "semantic_axis_admission": modeling.get("semantic_axis_admission"),
            },
            "research_region": research_region,
            "question_reformulation": reform,
            "epistemic_action": action,
            "transition_trace": trace,
            "execution_route": execution_route,
            "reused_skill_id": reusable.get("skill_id") if reusable else None,
            "claim_boundary": {
                "scientific_truth_promoted": False,
                "canonical_axis_registry_mutated": False,
                "generated_axis_is_world_truth": False,
                "generated_axis_is_independent_physical_dimension": False,
                "independent_grounding_required": bool(research_region.get("research_local_axis_ids")),
                "world_novelty_claimed": False,
            },
        }
        episode["digest"] = digest_payload(episode)
        formation = self.skills.form([*state_before.get("episodes", ()), episode], existing_skills=state_before.get("skills", ()))
        merged = {str(row.get("skill_id")): dict(row) for row in state_before.get("skills", ())}
        for row in formation.get("skills", ()):
            merged[str(row.get("skill_id"))] = dict(row)
        projected = {**state_before, "episodes": [*state_before.get("episodes", ()), episode], "skills": [merged[k] for k in sorted(merged)]}
        self_after = self.self_model.derive(self.runtime, projected, current_episode=episode)
        commit_receipt = None
        if commit:
            commit_receipt = self.memory.commit(episode=episode, skills=list(merged.values()), self_model=self_after)
        payload = {
            "schema": SCHEMA,
            "owner": self.owner_id,
            "contract": self.contract(),
            "episode": episode,
            "axis_modeling_result": modeling,
            "self_model_before": self_before,
            "skill_formation": formation,
            "self_model_after": self_after,
            "memory_commit": commit_receipt,
            "status": "COGNITIVE_GENERATED_AXIS_CYCLE_COMPLETE",
            "claim_boundary": {
                "AGI_claimed": False,
                "generated_axis_birth_executable": True,
                "generated_axis_grounded_as_world_mechanism": False,
                "canonical_scientific_promotion_preserved": True,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    @staticmethod
    def _hidden_world(axis_id: str, values: tuple[str, str], outcomes: tuple[str, str], prefix: str) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for i in range(8):
            side = i % 2
            rows.append({
                "study_id": f"{prefix}-S{i+1}",
                "record_id": f"{prefix}-R{i+1}",
                "outcome_class": outcomes[side],
                "context": {axis_id: values[side]},
            })
        return rows

    @classmethod
    def run_qualification(cls, root: str | Path) -> Mapping[str, Any]:
        from .runtime import LawSpaceRuntime

        root = Path(root)
        runtime = LawSpaceRuntime(root)
        axis_ids = ("latent_partition_alpha", "hidden_regime_beta", "context_switch_gamma")
        source_text = Path(__file__).read_text(encoding="utf-8")
        algorithm_text = source_text.split("    @classmethod\n    def run_qualification", 1)[0]
        canonical_before = canonical_axis_count()
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "cognitive_state.json"
            core = cls(runtime, memory_path=state_path)
            r1 = core.run({
                "episode_id": "COG-Q1", "environment_id": "HIDDEN-WORLD-A",
                "question": "Почему одинаковое входное воздействие даёт два устойчиво разных исхода?",
                "domain_id": "systems_control",
                "evidence_records": cls._hidden_world(axis_ids[0], ("A0", "A1"), ("LOW", "HIGH"), "WA"),
            })
            r2 = core.run({
                "episode_id": "COG-Q2", "environment_id": "HIDDEN-WORLD-B",
                "question": "Почему одна и та же модель управления меняет знак ошибки между сериями?",
                "domain_id": "systems_control",
                "evidence_records": cls._hidden_world(axis_ids[1], ("B0", "B1"), ("NEG", "POS"), "WB"),
            })
            # A new core instance must recover the learned macro from disk.
            core2 = cls(runtime, memory_path=state_path)
            r3 = core2.run({
                "episode_id": "COG-Q3", "environment_id": "HIDDEN-WORLD-C",
                "question": "Почему одинаковый регулятор переносится между режимами непоследовательно?",
                "domain_id": "systems_control",
                "evidence_records": cls._hidden_world(axis_ids[2], ("C0", "C1"), ("FAIL", "PASS"), "WC"),
            })
            # Negative control: two perfectly confounded candidate coordinates.
            confounded = []
            for i in range(8):
                side = i % 2
                confounded.append({
                    "study_id": f"WD-S{i+1}", "record_id": f"WD-R{i+1}",
                    "outcome_class": ("LEFT", "RIGHT")[side],
                    "context": {"confound_delta": ("D0", "D1")[side], "confound_epsilon": ("E0", "E1")[side]},
                })
            neg = core2.run({
                "episode_id": "COG-Q4", "environment_id": "HIDDEN-WORLD-D-CONFOUNDED",
                "question": "Какая скрытая координата объясняет расщепление исходов?",
                "domain_id": "systems_control", "evidence_records": confounded,
            })
            final_state = core2.memory.load()

            # Communication qualification: hidden compositional code, three independent
            # receivers/environments, matched-context playback interventions.  The
            # symbols and semantic mapping occur only in this qualification fixture,
            # outside the algorithm text hashed above.
            hidden_entity = ("⊙", "△")
            hidden_direction = ("↖", "↘")
            communication_observations = []
            for env in range(3):
                for entity_i, entity_symbol in enumerate(hidden_entity):
                    for direction_i, direction_symbol in enumerate(hidden_direction):
                        communication_observations.append({
                            "record_id": f"COMM-R{env}-{entity_i}-{direction_i}",
                            "study_id": f"COMM-S{env}-{entity_i}-{direction_i}",
                            "environment_id": f"COMM-ENV-{env}",
                            "receiver_id": f"COMM-RECEIVER-{env}",
                            "signal": entity_symbol + direction_symbol,
                            "world_state": f"ENTITY-{entity_i}|DIRECTION-{direction_i}",
                            "receiver_response": f"ENTITY-{entity_i}|DIRECTION-{direction_i}",
                            "intervention": True,
                            "context": {"scene": "MATCHED_PLAYBACK"},
                        })
            communication = core2.communication.analyze({
                "observations": communication_observations,
                "max_motif_order": 2,
                "minimum_episode_support": 2,
                "minimum_interventional_total_variation": 0.5,
                "minimum_independent_environments": 2,
            })
            ungrounded = core2.communication.analyze({
                "observations": [
                    {k: v for k, v in row.items() if k != "world_state"}
                    for row in communication_observations
                ],
                "max_motif_order": 2,
            })
            synthesized_code = core2.communication.synthesize_code({
                "meanings": [
                    {"meaning_id": f"M-{entity_i}-{direction_i}", "features": {"entity": str(entity_i), "direction": str(direction_i)}}
                    for entity_i in range(2) for direction_i in range(2)
                ],
                "alphabet": ["0", "1"],
                "minimum_segment_hamming_distance": 2,
                "max_segment_length": 4,
            })


            # Stronger representation frontier: the useful coordinate is not an
            # input field.  AXIS-MODELING must synthesize it from residual geometry.
            import numpy as np

            def generated_request(axis_id: str, seed: int, *, hidden_structure: bool = True) -> Mapping[str, Any]:
                rng = np.random.default_rng(seed)
                x0 = np.linspace(0.0, 10.0, 60)
                x = np.concatenate([x0, x0])
                regimes = ["train"] * len(x0) + ["ood"] * len(x0)
                sigma = np.full_like(x, 0.08)
                hidden = np.exp(-0.5 * ((x - 5.6) / 0.65) ** 2) if hidden_structure else np.zeros_like(x)
                y = 1.0 + 0.25 * x + 2.2 * hidden + rng.normal(0.0, sigma)
                return {
                    "seed": seed,
                    "ood_regime_ids": ["ood"],
                    "dataset": {
                        "dataset_id": "COG-GEN-" + axis_id,
                        "observable_id": "Y",
                        "observable_units": "arb",
                        "y": y.tolist(),
                        "sigma": sigma.tolist(),
                        "regime_ids": regimes,
                        "provenance": "COGNITIVE_GENERATED_AXIS_QUALIFICATION_" + axis_id,
                        "axes": [{
                            "axis_id": axis_id,
                            "domain": "systems_control",
                            "units": "arb",
                            "role": "observed",
                            "values": x.tolist(),
                            "provenance": "qualification observed coordinate",
                        }],
                    },
                }

            generated_source_axes = ("probe_coordinate_u", "forcing_coordinate_v", "state_coordinate_w")
            generated_state_path = Path(td) / "generated_cognitive_state.json"
            core_g = cls(runtime, memory_path=generated_state_path)
            g1 = core_g.run_generated_axis_cycle({
                "episode_id": "COG-G1", "environment_id": "GENERATED-WORLD-A",
                "question": "Какая отсутствующая координата объясняет устойчивый локальный residual?",
                "axis_modeling_request": generated_request(generated_source_axes[0], 960101),
            })
            g2 = core_g.run_generated_axis_cycle({
                "episode_id": "COG-G2", "environment_id": "GENERATED-WORLD-B",
                "question": "Почему базовое представление систематически промахивается в локальном режиме?",
                "axis_modeling_request": generated_request(generated_source_axes[1], 960102),
            })
            core_g2 = cls(runtime, memory_path=generated_state_path)
            g3 = core_g2.run_generated_axis_cycle({
                "episode_id": "COG-G3", "environment_id": "GENERATED-WORLD-C",
                "question": "Нужно ли расширить координатную систему для переноса модели на OOD режим?",
                "axis_modeling_request": generated_request(generated_source_axes[2], 960103),
            })
            gnull = core_g2.run_generated_axis_cycle({
                "episode_id": "COG-G0", "environment_id": "GENERATED-WORLD-NULL",
                "question": "Нужно ли рождать новую координату, если residual не содержит устойчивой структуры?",
                "axis_modeling_request": generated_request("null_probe_coordinate", 960199, hidden_structure=False),
            })
            generated_final_state = core_g2.memory.load()

        canonical_after = canonical_axis_count()
        receipts = (r1, r2, r3)
        generated_receipts = (g1, g2, g3)
        checks = {
            "three_unseen_axis_names_not_hardcoded_in_cognitive_algorithm": all(x not in algorithm_text for x in axis_ids),
            "each_hidden_world_discovers_its_own_axis": all(
                r["episode"]["axis_scan"]["scan_summary"]["causal_ready_candidate_dimensions"] == [axis]
                for r, axis in zip(receipts, axis_ids)
            ),
            "question_type_changes_conditionally_on_discovered_axis": all(
                r["episode"]["question_reformulation"]["question_class_after"] == "CONDITIONAL_COUNTERFACTUAL_BY_DISCOVERED_AXIS"
                and axis in r["episode"]["question_reformulation"]["question_after"]
                for r, axis in zip(receipts, axis_ids)
            ),
            "axis_signal_generalizes_leave_one_study_out": all(
                r["episode"]["axis_scan"]["selected_rows"][0]["leave_one_study_out"]["gain"] == 1.0
                for r in receipts
            ),
            "exact_grouped_permutation_gate_passes": all(
                r["episode"]["axis_scan"]["selected_rows"][0]["grouped_study_exact_permutation"]["p_value"] <= 0.05
                for r in receipts
            ),
            "research_local_axis_is_mounted_not_canonicalized": all(
                r["episode"]["research_region"]["research_local_axis_ids"] == [axis]
                and r["episode"]["research_region"]["canonical_registry_mutated"] is False
                for r, axis in zip(receipts, axis_ids)
            ),
            "skill_forms_after_independent_environments": any(
                row.get("independent_environment_count", 0) >= 2 and row.get("qualified") is True
                for row in r2["skill_formation"]["patterns"]
            ),
            "third_world_reuses_persisted_axis_agnostic_skill": r3["episode"]["execution_route"] == "LEARNED_SKILL_MACRO" and bool(r3["episode"]["reused_skill_id"]),
            "persistent_memory_survives_core_reinstantiation": len(final_state.get("episodes", ())) == 4 and len(final_state.get("skills", ())) >= 1,
            "self_model_knows_counts_are_not_space_ceiling": r3["self_model_after"]["space_boundary"]["materialized_candidates_are_space_ceiling"] is False and r3["self_model_after"]["space_boundary"]["canonical_axis_count_is_space_ceiling"] is False,
            "epistemic_action_reenters_search_after_single_axis_birth": all(r["episode"]["epistemic_action"]["selected_action"] == "REENTER_RESEARCH_WITH_REFORMULATED_QUESTION" for r in receipts),
            "confounded_axes_fail_closed": neg["episode"]["axis_scan"]["scan_summary"]["automatic_causal_axis_selection_allowed"] is False,
            "confounded_question_becomes_measurement_identifiability_problem": neg["episode"]["question_reformulation"]["question_class_after"] == "MEASUREMENT_AND_REPLICATION_QUESTION",
            "canonical_axis_registry_unchanged": canonical_before == canonical_after,
            "no_scientific_or_agi_promotion_claim": all(r["claim_boundary"]["AGI_claimed"] is False and r["episode"]["claim_boundary"]["scientific_truth_promoted"] is False for r in (*receipts, neg)),
            "generated_source_axis_names_not_hardcoded_in_cognitive_algorithm": all(x not in algorithm_text for x in generated_source_axes),
            "generated_coordinate_absent_from_input_schema": all(
                r["episode"]["axis_modeling"]["best_axis_birth"]["axis_id"] not in r["episode"]["axis_modeling"]["dataset"]["axis_ids"]
                for r in generated_receipts
            ),
            "axis_modeling_generates_ood_validated_coordinate": all(
                r["episode"]["axis_modeling"]["best_axis_birth"]["status"] == "AXIS_BIRTH_OOD_VALIDATED"
                and float(r["episode"]["axis_modeling"]["best_axis_birth"]["ood_rmse_fractional_improvement"]) > 0.5
                for r in generated_receipts
            ),
            "generated_axis_is_research_local_not_canonical": all(
                len(r["episode"]["research_region"]["research_local_axis_ids"]) == 1
                and r["episode"]["research_region"]["canonical_registry_mutated"] is False
                for r in generated_receipts
            ),
            "generated_axis_reformulates_into_grounding_question": all(
                r["episode"]["question_reformulation"]["question_class_after"] == "GENERATED_AXIS_CONDITIONAL_AND_GROUNDING_QUESTION"
                and r["episode"]["question_reformulation"]["claim_boundary"]["independent_grounding_required"] is True
                for r in generated_receipts
            ),
            "generated_axis_skill_forms_after_two_environments": any(
                row.get("independent_environment_count", 0) >= 2 and row.get("qualified") is True
                for row in g2["skill_formation"]["patterns"]
            ),
            "third_generated_world_reuses_persisted_structural_skill": g3["episode"]["execution_route"] == "LEARNED_SKILL_MACRO" and bool(g3["episode"]["reused_skill_id"]),
            "generated_skill_macro_uses_axis_modeling_owner": any(
                any(step.get("owner") == AxisModelingOwner.owner_id for step in skill.get("macro_steps", ()))
                for skill in generated_final_state.get("skills", ())
            ),
            "null_residual_world_rejects_axis_birth": gnull["episode"]["axis_modeling"]["best_axis_birth"]["status"] == "AXIS_BIRTH_REJECTED" and not gnull["episode"]["research_region"]["research_local_axis_ids"],
            "generated_axis_path_preserves_scientific_claim_boundary": all(
                r["episode"]["claim_boundary"]["generated_axis_is_world_truth"] is False
                and r["claim_boundary"]["generated_axis_grounded_as_world_mechanism"] is False
                for r in generated_receipts
            ),
            "hidden_communication_symbols_not_hardcoded_in_algorithm": all(symbol not in algorithm_text for symbol in (*hidden_entity, *hidden_direction)),
            "unknown_signal_motifs_discovered": len(communication["representation"]["motif_candidates"]) >= 4 and communication["representation"]["status"] == "UNKNOWN_SIGNAL_STRUCTURE_INDUCED_FROM_OBSERVATIONS",
            "compositional_signal_interaction_discovered": any(float(row.get("synergy_over_best_individual_bits", 0.0)) >= 0.99 for row in communication["representation"]["composition_candidates"]),
            "grounding_separated_from_structure": communication["grounding"]["status"] == "GROUNDED_COMMUNICATIVE_FUNCTION_QUALIFIED_RESEARCH_LEVEL",
            "matched_context_interventional_receiver_effect_replicates": communication["grounding"]["interventional_effects"]["status"] == "CAUSAL_COMMUNICATIVE_EFFECT_QUALIFIED_RESEARCH_LEVEL",
            "model_of_other_generalizes_across_receivers": communication["model_of_other"]["status"] == "BEHAVIORAL_RECEIVER_MODEL_GENERALIZES" and float(communication["model_of_other"]["leave_one_receiver_out_gain"]) > 0.0,
            "model_of_other_does_not_claim_mental_state": communication["model_of_other"]["mental_state_claimed"] is False and communication["claim_boundary"]["receiver_mental_state_inferred_as_fact"] is False,
            "missing_external_grounding_abstains_from_semantics": ungrounded["grounding"]["status"] == "SEMANTICS_UNIDENTIFIABLE_NO_EXTERNAL_GROUNDING" and ungrounded["claim_boundary"]["semantic_claim_without_grounding"] is False,
            "new_code_uses_minimum_semantic_axis_subset": synthesized_code["semantic_geometry"]["axis_selection_mode"] == "EXACT_MINIMUM_AXIS_SUBSET" and len(synthesized_code["semantic_geometry"]["selected_distinguishing_axes"]) == 2,
            "new_code_is_compositional_and_uniquely_decodable": synthesized_code["verification"]["compositionality_by_axis_factorization"] is True and synthesized_code["verification"]["unique_decodability"] is True,
            "new_code_meets_requested_error_distance": int(synthesized_code["verification"]["minimum_complete_code_hamming_distance"]) >= 2,
            "communication_layer_preserves_canonical_axis_registry": canonical_before == canonical_after,
        }
        payload = {
            "schema": "phi-cognitive-core-qualification/v1",
            "owner": OWNER_ID,
            "release": RELEASE,
            "status": "PASS_PHI_COGNITIVE_CORE_QUALIFICATION" if all(checks.values()) else "FAIL_PHI_COGNITIVE_CORE_QUALIFICATION",
            "passed": sum(bool(x) for x in checks.values()),
            "total": len(checks),
            "checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()],
            "demonstration": {
                "episodes": [r["episode"] for r in receipts],
                "negative_control": neg["episode"],
                "generated_axis_episodes": [r["episode"] for r in generated_receipts],
                "generated_axis_null_control": gnull["episode"],
                "generated_axis_final_memory": {
                    "episode_count": len(generated_final_state.get("episodes", ())),
                    "skill_count": len(generated_final_state.get("skills", ())),
                    "skills": generated_final_state.get("skills", ()),
                },
                "final_memory": {
                    "episode_count": len(final_state.get("episodes", ())),
                    "skill_count": len(final_state.get("skills", ())),
                    "skills": final_state.get("skills", ()),
                },
                "canonical_axis_count_before": canonical_before,
                "canonical_axis_count_after": canonical_after,
                "communication": communication,
                "communication_ungrounded_negative_control": ungrounded,
                "synthesized_communication_code": synthesized_code,
            },
            "claim_boundary": {
                "AGI_demonstrated": False,
                "general_natural_language_understanding_demonstrated": False,
                "unknown_signal_structure_induction_demonstrated": True,
                "grounded_communicative_function_research_gate_demonstrated": True,
                "behavioral_model_of_other_generalization_demonstrated": True,
                "finite_compositional_code_synthesis_demonstrated": True,
                "unknown_human_language_fully_deciphered": False,
                "animal_language_translation_demonstrated": False,
                "question_reformulation_from_unseen_axis_demonstrated": True,
                "generated_axis_birth_from_residual_geometry_demonstrated": True,
                "generated_axis_independent_grounding_demonstrated": False,
                "persistent_structural_skill_reuse_demonstrated": True,
                "canonical_axis_mutation_demonstrated": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload
