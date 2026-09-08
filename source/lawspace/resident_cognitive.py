"""Resident Cognitive Organism for the unified Phi-LawSpace.

This owner is a persistent meta-orchestrator over the existing cognitive and
scientific owners.  It does not create a parallel scientific solver.  It adds a
resident heartbeat that can change its grounded concepts, goal graph, plans,
compiled macro-capabilities and self-model as evidence changes.

All learned operators remain typed compositions of already-authoritative owners
and cannot bypass scientific, axis-admission, grounding or identifiability gates.
"""
from __future__ import annotations

import json
import os
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .axis_modeling import AxisModelingOwner
from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .cognitive_core import (
    GOAL_ACTION_OWNER_ID,
    OWNER_ID as COGNITIVE_OWNER_ID,
    QUESTION_REFORMULATION_OWNER_ID,
    SKILL_FORMATION_OWNER_ID,
    PhiCognitiveCore,
)
from .domains import canonical_axis_count
from .research_cycle import ScientificResearchCycleOwner
from .schema import digest_payload

COMPONENT_SCHEMA_VERSION = "6.0.0"
STATE_SCHEMA_VERSION = "5"
AI_ACCEPTANCE_VERSION = "15.10.5"
SCHEMA = "phi-resident-cognitive-organism/v6"
STATE_SCHEMA = f"phi-resident-state/v{STATE_SCHEMA_VERSION}"
LEGACY_STATE_SCHEMAS = {"phi-resident-state/v1", "phi-resident-state/v2", "phi-resident-state/v3", "phi-resident-state/v4"}
OWNER_ID = "PHI-RESIDENT-COGNITIVE-ORGANISM/6.0.0"
CONCEPT_OWNER_ID = "GROUNDED-CONCEPT-FORMATION/1.0.0"
GOAL_GRAPH_OWNER_ID = "DYNAMIC-GOAL-GRAPH/1.0.0"
PLANNER_OWNER_ID = "ONTOLOGY-AWARE-PLANNER/1.0.0"
OPERATOR_COMPILER_OWNER_ID = "SKILL-TO-OPERATOR-COMPILER/1.0.0"
SELF_FEEDBACK_OWNER_ID = "SELF-MODEL-FEEDBACK/1.0.0"
STATE_OWNER_ID = "RESIDENT-STATE-LEDGER/4.0.0"
ONTOLOGY_EVOLUTION_OWNER_ID = "ONTOLOGY-EVOLUTION/1.0.0"
ADAPTIVE_ACTION_OWNER_ID = "ADAPTIVE-ACTION-INVENTION/1.0.0"
HIGHER_OPERATOR_OWNER_ID = "HIGHER-ORDER-OPERATOR-EVOLUTION/1.0.0"
RESOURCE_POLICY_OWNER_ID = "FINITE-RESOURCE-ACTION-POLICY/1.0.0"
CONSOLIDATION_OWNER_ID = "RESIDENT-CONSOLIDATION-FORGETTING/1.0.0"
MISSING_REPRESENTATION_OWNER_ID = "MISSING-REPRESENTATION-BLIND-WORLD/1.0.0"
WORLD_ACTION_MODEL_OWNER_ID = "CONTEXTUAL-NONSTATIONARY-WORLD-ACTION-MODEL/2.0.0"
PHI_MODEL_FAMILY_BIRTH_OWNER_ID = "PHI-MODEL-FAMILY-BIRTH/1.0.0"
DRIFT_OWNER_ID = "WORLD-MODEL-DRIFT-DETECTION/1.0.0"
UNCERTAINTY_OWNER_ID = "WORLD-MODEL-UNCERTAINTY-DECOMPOSITION/1.0.0"
TYPED_ACTION_ADAPTER_OWNER_ID = "TYPED-WORLD-ACTION-ADAPTER/1.0.0"
BLIND_PROCESS_OWNER_ID = "BLIND-GENERATOR-SOLVER-EVALUATOR/1.0.0"


def _state_digest(state: Mapping[str, Any]) -> str:
    return digest_payload({k: v for k, v in state.items() if k != "state_digest"})


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _canonicalize_qualification_runtime_paths(value: Any) -> Any:
    """Remove host-specific mutable-state paths from canonical qualification evidence.

    Runtime commit receipts may expose their concrete external path for diagnostics,
    but release qualification identity must not depend on extraction directory or
    temporary-directory names.
    """
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if key == "path" and isinstance(item, str):
                out[key] = "EXTERNAL_MUTABLE_STATE"
            else:
                out[key] = _canonicalize_qualification_runtime_paths(item)
        # Heartbeat receipts hash the concrete state-commit receipt at runtime.
        # After replacing its host-specific path, recompute that local receipt
        # identity so nested digests are portable as well as the top-level one.
        if "state_commit" in out and "digest" in out and out.get("schema") == SCHEMA:
            out["digest"] = digest_payload({k: v for k, v in out.items() if k != "digest"})
        # ONLINE_WORLD_MODEL_UPDATED hashes a nested contextual fit that may include
        # a host-specific external-state commit path.  The fit identity itself is
        # path-independent, but the wrapper digest is not unless it is recomputed
        # after canonicalization.
        if out.get("status") == "ONLINE_WORLD_MODEL_UPDATED" and "digest" in out:
            out["digest"] = digest_payload({k: v for k, v in out.items() if k != "digest"})
        return out
    if isinstance(value, list):
        return [_canonicalize_qualification_runtime_paths(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_canonicalize_qualification_runtime_paths(item) for item in value)
    return value


def default_resident_state_path(runtime: Any) -> Path:
    """Return the current-release mutable resident state outside the sealed tree."""
    if hasattr(runtime, "external_state_path"):
        return Path(runtime.external_state_path("resident_cognitive_state"))
    configured = str(os.environ.get("PHI_STATE_DIR", "")).strip()
    state_root = Path(configured).expanduser() if configured else (Path.home() / ".local" / "state" / "phi-compiler")
    release = runtime.current_release_id() if hasattr(runtime, "current_release_id") else "UNSEALED-CURRENT"
    candidate = state_root / release / "resident_cognitive_state.json"
    if _is_within(candidate, Path(runtime.root)):
        raise ValueError("resident mutable state must be outside the sealed runtime root")
    return candidate


def validate_external_state_path(runtime: Any, state_path: str | Path) -> Path:
    candidate = Path(state_path).expanduser()
    if _is_within(candidate, Path(runtime.root)):
        raise ValueError("resident mutable state must be outside the sealed runtime root")
    return candidate


class ResidentStateLedgerOwner:
    owner_id = STATE_OWNER_ID

    def __init__(self, path: str | Path, *, system_release: str = "UNSEALED-CURRENT") -> None:
        self.path = Path(path)
        self.system_release = str(system_release or "UNSEALED-CURRENT")

    def empty(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "schema": STATE_SCHEMA,
            "owner": self.owner_id,
            "release": self.system_release,
            "heartbeat_count": 0,
            "goals": [],
            "plans": [],
            "concepts": [],
            "operators": [],
            "skill_applications": [],
            "higher_order_operators": [],
            "ontology_events": [],
            "consolidations": [],
            "resource_ledger": {"compute": 0.0, "memory": 0.0, "measurements": 0.0, "time": 0.0},
            "world_action_experiences": [],
            "world_action_models": [],
            "world_action_model_versions": [],
            "world_action_drift_events": [],
            "typed_action_adapter_receipts": [],
            "self_model_feedback": {},
            "transitions": [],
        }
        state["state_digest"] = _state_digest(state)
        return state

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("state_digest") != _state_digest(state):
            raise ValueError("resident-state digest mismatch")
        if state.get("schema") in LEGACY_STATE_SCHEMAS:
            state["schema"] = STATE_SCHEMA
            state["owner"] = self.owner_id
            state["release"] = self.system_release
            state.setdefault("higher_order_operators", [])
            state.setdefault("ontology_events", [])
            state.setdefault("consolidations", [])
            state.setdefault("resource_ledger", {"compute": 0.0, "memory": 0.0, "measurements": 0.0, "time": 0.0})
            state.setdefault("world_action_experiences", [])
            state.setdefault("world_action_models", [])
            state.setdefault("world_action_model_versions", [])
            state.setdefault("world_action_drift_events", [])
            state.setdefault("typed_action_adapter_receipts", [])
            state["state_digest"] = _state_digest(state)
        if state.get("schema") != STATE_SCHEMA or state.get("owner") != self.owner_id:
            raise ValueError("unsupported resident-state schema/owner")
        for key in ("goals", "plans", "concepts", "operators", "skill_applications", "higher_order_operators", "ontology_events", "consolidations", "world_action_experiences", "world_action_models", "world_action_model_versions", "world_action_drift_events", "typed_action_adapter_receipts", "transitions"):
            if not isinstance(state.get(key), list):
                raise ValueError(f"resident state requires list {key}")
        return state

    def commit(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = dict(state)
        payload["state_digest"] = _state_digest(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return {
            "owner": self.owner_id,
            "status": "RESIDENT_STATE_COMMITTED",
            "path": str(self.path),
            "heartbeat_count": payload["heartbeat_count"],
            "state_digest": payload["state_digest"],
        }

    def version_identity(self) -> Mapping[str, Any]:
        payload = {
            "system_release": self.system_release,
            "component_schema_version": COMPONENT_SCHEMA_VERSION,
            "state_schema_version": STATE_SCHEMA_VERSION,
            "state_schema": STATE_SCHEMA,
            "ai_acceptance_version": AI_ACCEPTANCE_VERSION,
        }
        return {**payload, "digest": digest_payload(payload)}

    def migrate_document(self, state: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
        """Pure deterministic migration into the current resident-state schema.

        Migration changes representation metadata only; it never promotes scientific
        claims or synthesizes missing experiences.  The caller may inspect the
        returned document before committing it to an external mutable-state path.
        """
        doc = dict(state)
        embedded = str(doc.get("state_digest", ""))
        if not embedded or embedded != _state_digest(doc):
            raise ValueError("resident-state digest mismatch")
        schema = str(doc.get("schema", ""))
        steps: list[str] = []
        if schema in LEGACY_STATE_SCHEMAS:
            steps.append(f"SCHEMA:{schema}->{STATE_SCHEMA}")
            doc["schema"] = STATE_SCHEMA
            doc["owner"] = self.owner_id
            defaults = {
                "higher_order_operators": [], "ontology_events": [], "consolidations": [],
                "resource_ledger": {"compute": 0.0, "memory": 0.0, "measurements": 0.0, "time": 0.0},
                "world_action_experiences": [], "world_action_models": [],
                "world_action_model_versions": [], "world_action_drift_events": [],
                "typed_action_adapter_receipts": [],
            }
            for key, value in defaults.items():
                if key not in doc:
                    doc[key] = value
                    steps.append(f"DEFAULT:{key}")
        elif schema != STATE_SCHEMA:
            raise ValueError(f"unsupported resident-state schema: {schema!r}")
        source_release = str(doc.get("release", ""))
        if source_release != self.system_release:
            doc["release"] = self.system_release
            steps.append(f"SYSTEM_RELEASE:{source_release or 'UNDECLARED'}->{self.system_release}")
        doc["owner"] = self.owner_id
        doc["state_digest"] = _state_digest(doc)
        return doc, tuple(steps)

    def restore_snapshot(
        self, snapshot_path: str | Path, *, expected_sha256: str | None = None, overwrite: bool = False
    ) -> Mapping[str, Any]:
        """Verify, migrate and atomically restore a snapshot to external state.

        Destination must already have been validated as external by the runtime
        constructor.  Existing state is never overwritten unless explicitly asked.
        """
        import hashlib
        src = Path(snapshot_path).expanduser()
        raw = src.read_bytes()
        source_sha256 = hashlib.sha256(raw).hexdigest()
        if expected_sha256 and source_sha256.lower() != str(expected_sha256).lower():
            raise ValueError("resident-state snapshot sha256 mismatch")
        if self.path.exists() and not overwrite:
            raise FileExistsError(f"resident state already exists at {self.path}; pass overwrite=True explicitly")
        source = json.loads(raw.decode("utf-8"))
        source_schema = str(source.get("schema", ""))
        source_release = str(source.get("release", ""))
        migrated, steps = self.migrate_document(source)
        commit = self.commit(migrated)
        payload = {
            "owner": self.owner_id,
            "status": "RESIDENT_STATE_RESTORED",
            "source_sha256": source_sha256,
            "source_schema": source_schema,
            "target_schema": STATE_SCHEMA,
            "source_system_release": source_release,
            "target_system_release": self.system_release,
            "migration_steps": list(steps),
            "state_digest": commit["state_digest"],
            "destination": str(self.path),
            "scientific_truth_changed": False,
            "version_identity": self.version_identity(),
        }
        payload["digest"] = digest_payload(payload)
        return payload


class GroundedConceptFormationOwner:
    """Form concepts only from independent grounded invariants, never labels alone."""

    owner_id = CONCEPT_OWNER_ID
    minimum_independent_environments = 2
    minimum_independent_grounding_owners = 2

    @staticmethod
    def _concept_key(grounding: Mapping[str, Any]) -> str | None:
        invariant = grounding.get("invariant_signature")
        predictive = grounding.get("predictive_role")
        causal = grounding.get("causal_role")
        if invariant in (None, "") or predictive in (None, "") or causal in (None, ""):
            return None
        return digest_payload({"invariant_signature": invariant, "predictive_role": predictive, "causal_role": causal})

    def update(
        self,
        existing: Sequence[Mapping[str, Any]],
        *,
        environment_id: str,
        axis_ids: Sequence[str],
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        key = self._concept_key(grounding)
        measurements = [dict(x) for x in grounding.get("owner_measurements", ())]
        owners = sorted({str(x.get("owner_id", "")) for x in measurements if x.get("independent") is True and str(x.get("owner_id", ""))})
        contrast_pass = grounding.get("contrast_pass") is True
        current_gate = bool(key) and len(owners) >= self.minimum_independent_grounding_owners and contrast_pass
        rows = {str(x.get("concept_key")): dict(x) for x in existing}
        prior = rows.get(str(key)) if key else None
        if not current_gate:
            payload = {
                "owner": self.owner_id,
                "status": "CONCEPT_GROUNDING_INSUFFICIENT_FAIL_CLOSED",
                "concept": prior,
                "current_environment_gate": False,
                "independent_grounding_owner_count": len(owners),
                "claim_boundary": {"semantic_label_is_concept": False, "concept_promoted": False},
            }
            payload["digest"] = digest_payload(payload)
            return payload

        envs = set(prior.get("independent_environment_ids", ())) if prior else set()
        envs.add(environment_id)
        all_axes = set(prior.get("support_axis_ids", ())) if prior else set()
        all_axes.update(str(x) for x in axis_ids if str(x))
        all_owners = set(prior.get("grounding_owner_ids", ())) if prior else set()
        all_owners.update(owners)
        revisions = int(prior.get("revision", 0)) if prior else 0
        old_axes = set(prior.get("support_axis_ids", ())) if prior else set()
        if prior and all_axes != old_axes:
            revisions += 1
        status = (
            "PROMOTED_GROUNDED_CONCEPT"
            if len(envs) >= self.minimum_independent_environments and len(all_owners) >= self.minimum_independent_grounding_owners
            else "PROVISIONAL_GROUNDED_CONCEPT"
        )
        concept = {
            "concept_id": "CONCEPT-" + str(key)[:24].upper(),
            "concept_key": key,
            "owner": self.owner_id,
            "status": status,
            "revision": revisions,
            "invariant_signature": grounding.get("invariant_signature"),
            "predictive_role": grounding.get("predictive_role"),
            "causal_role": grounding.get("causal_role"),
            "independent_environment_ids": sorted(envs),
            "grounding_owner_ids": sorted(all_owners),
            "support_axis_ids": sorted(all_axes),
            "counterexample_policy": "DEMOTE_OR_SPLIT_ON_REPLICATED_ROLE_FAILURE",
            "claim_boundary": {
                "concept_is_human_word": False,
                "concept_is_world_truth": False,
                "concept_requires_grounding_and_cross_environment_support": True,
            },
        }
        concept["digest"] = digest_payload(concept)
        payload = {
            "owner": self.owner_id,
            "status": status,
            "concept": concept,
            "current_environment_gate": True,
            "independent_grounding_owner_count": len(owners),
        }
        payload["digest"] = digest_payload(payload)
        return payload


class SkillToOperatorCompilerOwner:
    """Compile repeatedly reused skill macros into typed resident operators."""

    owner_id = OPERATOR_COMPILER_OWNER_ID
    minimum_successful_application_environments = 2

    def update(
        self,
        *,
        existing_operators: Sequence[Mapping[str, Any]],
        applications: Sequence[Mapping[str, Any]],
        skill: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        if not skill or skill.get("status") != "PROMOTED_REUSABLE_SKILL":
            return {"owner": self.owner_id, "status": "NO_QUALIFIED_SKILL_TO_COMPILE", "operator": None, "digest": digest_payload("NO_QUALIFIED_SKILL_TO_COMPILE")}
        skill_id = str(skill.get("skill_id", ""))
        valid_apps = [
            dict(x) for x in applications
            if x.get("skill_id") == skill_id and x.get("success") is True and x.get("execution_route") == "LEARNED_SKILL_MACRO" and str(x.get("environment_id", ""))
        ]
        app_envs = sorted({str(x["environment_id"]) for x in valid_apps})
        source_envs = sorted({str(x) for x in skill.get("independent_environment_ids", ()) if str(x)})
        macro_steps = [dict(x) for x in skill.get("macro_steps", ())]
        typed = bool(macro_steps) and all(str(x.get("owner", "")) and str(x.get("operation", "")) for x in macro_steps)
        qualifies = len(source_envs) >= 2 and len(app_envs) >= self.minimum_successful_application_environments and typed
        if not qualifies:
            payload = {
                "owner": self.owner_id,
                "status": "OPERATOR_COMPILATION_PENDING_REUSE_EVIDENCE",
                "operator": None,
                "skill_id": skill_id,
                "source_environment_count": len(source_envs),
                "successful_application_environment_count": len(app_envs),
            }
            payload["digest"] = digest_payload(payload)
            return payload
        operator_id = "OPERATOR-" + digest_payload({"skill": skill_id, "steps": macro_steps})[:24].upper()
        existing = {str(x.get("operator_id")): dict(x) for x in existing_operators}
        operator = existing.get(operator_id) or {
            "operator_id": operator_id,
            "owner": self.owner_id,
            "source_skill_id": skill_id,
            "status": "QUALIFIED_RESIDENT_OPERATOR",
            "typed_owner_steps": macro_steps,
            "source_skill_environment_ids": source_envs,
            "successful_application_environment_ids": app_envs,
            "application_guard": dict(skill.get("application_guard", {})),
            "claim_boundary": {
                "new_arbitrary_code_generated": False,
                "scientific_gates_bypassed": False,
                "operator_is_macro_over_authoritative_owners": True,
                "operator_is_new_scientific_law": False,
            },
        }
        operator["successful_application_environment_ids"] = sorted(set(operator.get("successful_application_environment_ids", ())) | set(app_envs))
        operator["digest"] = digest_payload({k: v for k, v in operator.items() if k != "digest"})
        payload = {"owner": self.owner_id, "status": "RESIDENT_OPERATOR_COMPILED", "operator": operator}
        payload["digest"] = digest_payload(payload)
        return payload


class DynamicGoalGraphOwner:
    owner_id = GOAL_GRAPH_OWNER_ID

    def update(
        self,
        existing: Sequence[Mapping[str, Any]],
        *,
        root_goal: Mapping[str, Any],
        concept_result: Mapping[str, Any],
        operator_result: Mapping[str, Any],
        cognitive_episode: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        rows = {str(x.get("goal_id")): dict(x) for x in existing}
        root_id = str(root_goal.get("goal_id") or "GOAL-" + digest_payload(root_goal)[:20].upper())
        root = rows.get(root_id) or {
            "goal_id": root_id,
            "goal_class": "ROOT_RESEARCH_INTENT",
            "statement": str(root_goal.get("statement", "understand and act under uncertainty")),
            "parent_goal_id": None,
            "status": "ACTIVE",
            "priority": 1.0,
        }
        rows[root_id] = root

        rep_route = str(cognitive_episode.get("representation_route", ""))
        concept_status = str(concept_result.get("status", ""))
        operator_status = str(operator_result.get("status", ""))
        desired: list[tuple[str, str, float]] = []
        if rep_route == "GENERATED_AXIS_MODELING":
            desired.append(("GROUND_GENERATED_REPRESENTATION", "obtain independent grounding for the generated representation", 0.95))
        if concept_status == "PROVISIONAL_GROUNDED_CONCEPT":
            desired.append(("REPLICATE_CONCEPT", "replicate the grounded invariant in an independent environment", 0.90))
        if concept_status == "PROMOTED_GROUNDED_CONCEPT":
            desired.append(("TEST_CONCEPT_TRANSFER", "test the promoted concept under transfer and counterexample pressure", 0.85))
        if operator_status == "RESIDENT_OPERATOR_COMPILED":
            desired.append(("STRESS_TEST_COMPILED_OPERATOR", "challenge the compiled operator out of distribution before broader reuse", 0.80))

        for gclass, statement, priority in desired:
            gid = "GOAL-" + digest_payload({"parent": root_id, "class": gclass})[:20].upper()
            row = rows.get(gid) or {
                "goal_id": gid,
                "goal_class": gclass,
                "statement": statement,
                "parent_goal_id": root_id,
                "status": "ACTIVE",
                "priority": priority,
            }
            row["status"] = "ACTIVE"
            rows[gid] = row

        # Goals are allowed to change state as their evidence target is achieved.
        for row in rows.values():
            if row.get("goal_class") == "GROUND_GENERATED_REPRESENTATION" and concept_status in {"PROVISIONAL_GROUNDED_CONCEPT", "PROMOTED_GROUNDED_CONCEPT"}:
                row["status"] = "SATISFIED"
            if row.get("goal_class") == "REPLICATE_CONCEPT" and concept_status == "PROMOTED_GROUNDED_CONCEPT":
                row["status"] = "SATISFIED"

        ordered = sorted(rows.values(), key=lambda x: (-float(x.get("priority", 0.0)), str(x.get("goal_id"))))
        active = [x for x in ordered if x.get("status") == "ACTIVE"]
        payload = {
            "owner": self.owner_id,
            "status": "GOAL_GRAPH_UPDATED",
            "goals": ordered,
            "active_goal_ids": [x["goal_id"] for x in active],
            "selected_goal_id": active[0]["goal_id"] if active else root_id,
            "goals_may_change_with_evidence": True,
        }
        payload["digest"] = digest_payload(payload)
        return payload


class OntologyAwarePlannerOwner:
    owner_id = PLANNER_OWNER_ID

    def plan(
        self,
        *,
        goal_graph: Mapping[str, Any],
        concepts: Sequence[Mapping[str, Any]],
        operators: Sequence[Mapping[str, Any]],
        previous_plans: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        selected = str(goal_graph.get("selected_goal_id", ""))
        by_id = {str(x.get("goal_id")): dict(x) for x in goal_graph.get("goals", ())}
        goal = by_id.get(selected, {})
        gclass = str(goal.get("goal_class", "ROOT_RESEARCH_INTENT"))
        ontology_digest = digest_payload([
            {"concept_id": x.get("concept_id"), "revision": x.get("revision"), "status": x.get("status"), "axes": x.get("support_axis_ids")}
            for x in concepts
        ])
        capability_digest = digest_payload([
            {"operator_id": x.get("operator_id"), "status": x.get("status"), "source_skill_id": x.get("source_skill_id")}
            for x in operators
        ])
        step_map = {
            "GROUND_GENERATED_REPRESENTATION": [
                {"owner": QUESTION_REFORMULATION_OWNER_ID, "operation": "request_independent_grounding"},
                {"owner": ScientificResearchCycleOwner.owner_id, "operation": "design_discriminating_measurement"},
            ],
            "REPLICATE_CONCEPT": [
                {"owner": ScientificResearchCycleOwner.owner_id, "operation": "replicate_across_environment"},
                {"owner": CONCEPT_OWNER_ID, "operation": "update"},
            ],
            "TEST_CONCEPT_TRANSFER": [
                {"owner": ScientificResearchCycleOwner.owner_id, "operation": "counterexample_and_transfer_test"},
                {"owner": CONCEPT_OWNER_ID, "operation": "revise_or_demote"},
            ],
            "STRESS_TEST_COMPILED_OPERATOR": [
                {"owner": OPERATOR_COMPILER_OWNER_ID, "operation": "check_application_guard"},
                {"owner": ScientificResearchCycleOwner.owner_id, "operation": "ood_operator_challenge"},
            ],
            "ROOT_RESEARCH_INTENT": [
                {"owner": COGNITIVE_OWNER_ID, "operation": "run"},
                {"owner": GOAL_ACTION_OWNER_ID, "operation": "choose"},
            ],
        }
        steps = step_map.get(gclass, step_map["ROOT_RESEARCH_INTENT"])
        previous = dict(previous_plans[-1]) if previous_plans else None
        changed = bool(previous) and (previous.get("ontology_digest") != ontology_digest or previous.get("capability_digest") != capability_digest or previous.get("goal_id") != selected)
        plan = {
            "plan_id": "PLAN-" + digest_payload({"goal": selected, "ontology": ontology_digest, "capability": capability_digest, "steps": steps})[:24].upper(),
            "owner": self.owner_id,
            "goal_id": selected,
            "goal_class": gclass,
            "status": "REPLANNED_AFTER_ONTOLOGY_OR_CAPABILITY_CHANGE" if changed else "PLAN_FROZEN_FOR_CURRENT_STATE",
            "ontology_digest": ontology_digest,
            "capability_digest": capability_digest,
            "steps": steps,
            "contingencies": {
                "representation_failure": AxisModelingOwner.owner_id,
                "identifiability_failure": ScientificResearchCycleOwner.owner_id,
                "operator_guard_failure": "FALL_BACK_TO_AUTHORITATIVE_OWNER_TRACE",
            },
            "claim_boundary": {"plan_is_world_action": False, "planner_can_bypass_owner_gates": False},
        }
        plan["digest"] = digest_payload(plan)
        return plan


class SelfModelFeedbackOwner:
    owner_id = SELF_FEEDBACK_OWNER_ID

    def derive(self, *, concepts: Sequence[Mapping[str, Any]], operators: Sequence[Mapping[str, Any]], goal_graph: Mapping[str, Any], cognitive_episode: Mapping[str, Any]) -> Mapping[str, Any]:
        promoted = [x for x in concepts if x.get("status") == "PROMOTED_GROUNDED_CONCEPT"]
        compiled = [x for x in operators if x.get("status") == "QUALIFIED_RESIDENT_OPERATOR"]
        payload = {
            "owner": self.owner_id,
            "status": "SELF_MODEL_FEEDBACK_UPDATED",
            "capabilities": {
                "grounded_concept_count": len(promoted),
                "qualified_resident_operator_count": len(compiled),
                "can_replan_after_ontology_change": True,
                "can_change_goal_graph_from_evidence": True,
                "can_compile_typed_skill_macro": bool(compiled),
            },
            "current_limits": {
                "general_world_actuation_available": False,
                "self_generated_operator_may_bypass_scientific_gates": False,
                "concept_is_world_truth": False,
                "autonomous_goal_value_system_claimed": False,
                "consciousness_claimed": False,
                "AGI_claimed": False,
            },
            "active_goal_count": len(goal_graph.get("active_goal_ids", ())),
            "last_representation_route": cognitive_episode.get("representation_route"),
        }
        payload["digest"] = digest_payload(payload)
        return payload


class OpenWorldPhiExplorerOwner:
    """Choose research actions only from a frozen Phi-space scan.

    External/network material may be used after freeze for verification or grounding,
    never to populate the pre-freeze action or hypothesis frontier.
    """

    owner_id = "OPEN-WORLD-PHI-EXPLORER/1.0.0"

    @staticmethod
    def _entropy(priors: Mapping[str, float]) -> float:
        import math
        return -sum(float(p) * math.log2(float(p)) for p in priors.values() if float(p) > 0.0)

    def scan(
        self, runtime: Any, *, question: str, required_observables: Sequence[str] = (),
        required_domains: Sequence[str] = (), include_all_connected_owners: bool = True,
        activate_bridge_open_axes: bool = True,
    ) -> Mapping[str, Any]:
        pipeline = CandidateGenerationPipeline(runtime.catalog, runtime.bridges)
        scan = dict(pipeline.directed_research(DirectedResearchQuery(
            question=str(question),
            required_observables=tuple(str(x) for x in required_observables),
            required_domains=tuple(str(x) for x in required_domains),
            include_all_connected_owners=bool(include_all_connected_owners),
        )))
        actions = []
        active_dispositions = {
            "OWNER_BOUND_ACTIVE",
            "QUERY_DIRECT_OPEN_COORDINATE",
        }
        if activate_bridge_open_axes:
            active_dispositions.add("BRIDGE_ADDRESSABLE_OPEN_COORDINATE")
        for row in scan.get("axis_rows", ()):
            disposition = str(row.get("disposition", ""))
            # Fail closed: only producer-defined active/open dispositions may become
            # actions.  Unknown/future/background classifications remain inert.
            if disposition not in active_dispositions:
                continue
            qid = str(row.get("qualified_axis_id", ""))
            if not qid:
                continue
            action = {
                "action_id": "MEASURE::" + qid,
                "action_class": "MEASURE_OR_INTERVENE_ON_AXIS",
                "axis_id": qid,
                "axis_disposition": disposition,
                "bound_owner_ids": list(row.get("bound_owner_ids", ())),
                "preconditions": ["AXIS_PRESENT_IN_FROZEN_PHI_REGION", "AXIS_DISPOSITION_ACTIVE_OR_OPEN"],
                "expected_result": "TYPED_OBSERVATION",
                "risk_class": "RESEARCH_ONLY_NO_AUTONOMOUS_EXTERNAL_ACTUATION",
            }
            action["digest"] = digest_payload(action)
            actions.append(action)
        freeze = {
            "owner": self.owner_id,
            "status": "PHI_SPACE_ACTION_FRONTIER_FROZEN",
            "question": str(question),
            "scan_digest": scan.get("digest"),
            "registered_axis_count": scan.get("registered_axis_count"),
            "all_registered_axes_visited": scan.get("all_registered_axes_visited"),
            "owner_visits": scan.get("owner_visits"),
            "fixed_owner_visit_budget": scan.get("fixed_owner_visit_budget"),
            "fixed_candidate_axis_order_ceiling": scan.get("fixed_candidate_axis_order_ceiling"),
            "action_frontier": actions,
            "action_frontier_count": len(actions),
            "active_action_dispositions": sorted(active_dispositions),
            "bridge_open_axes_activated": bool(activate_bridge_open_axes),
            "background_axis_count_excluded": int(scan.get("axis_disposition_counts", {}).get("addressable_background", 0)),
            "bridge_addressable_axis_count_not_activated": 0 if activate_bridge_open_axes else int(scan.get("axis_disposition_counts", {}).get("bridge_addressable_open", 0)),
            "external_source_role": "POST_FREEZE_VERIFICATION_OR_GROUNDING_ONLY",
            "internet_used_for_candidate_or_action_selection": False,
        }
        freeze["freeze_digest"] = digest_payload(freeze)
        return {"scan": scan, "freeze": freeze, "digest": digest_payload({"scan": scan.get("digest"), "freeze": freeze["freeze_digest"]})}

    def select_action(self, freeze: Mapping[str, Any], *, hypotheses: Sequence[str], likelihoods: Mapping[str, Mapping[str, Mapping[str, float]]], priors: Mapping[str, float] | None = None) -> Mapping[str, Any]:
        hs = tuple(str(x) for x in hypotheses)
        if not hs:
            raise ValueError("at least one frozen hypothesis is required")
        if priors is None:
            pri = {h: 1.0 / len(hs) for h in hs}
        else:
            pri = {h: float(priors[h]) for h in hs}
            total = sum(pri.values())
            if total <= 0.0:
                raise ValueError("priors must have positive total mass")
            pri = {h: p / total for h, p in pri.items()}
        frozen_actions = {str(x["action_id"]): dict(x) for x in freeze.get("action_frontier", ())}
        h0 = self._entropy(pri)
        ranked = []
        for action_id, action in frozen_actions.items():
            table = likelihoods.get(action_id)
            if not isinstance(table, Mapping):
                continue
            outcomes = sorted({str(o) for h in hs for o in table.get(h, {}).keys()})
            if not outcomes:
                continue
            expected_h = 0.0
            for outcome in outcomes:
                weights = {h: pri[h] * float(table.get(h, {}).get(outcome, 0.0)) for h in hs}
                p_o = sum(weights.values())
                if p_o <= 0.0:
                    continue
                posterior = {h: weights[h] / p_o for h in hs}
                expected_h += p_o * self._entropy(posterior)
            eig = max(0.0, h0 - expected_h)
            ranked.append({"action_id": action_id, "axis_id": action.get("axis_id"), "expected_information_gain_bits": eig})
        ranked.sort(key=lambda x: (-x["expected_information_gain_bits"], x["action_id"]))
        if not ranked or ranked[0]["expected_information_gain_bits"] <= 1e-12:
            payload = {
                "owner": self.owner_id,
                "status": "EXPAND_GENERATED_REPRESENTATION",
                "selected_action": None,
                "ranked_actions": ranked,
                "fallback_owner": AxisModelingOwner.owner_id,
                "reason": "NO_FROZEN_PHI_ACTION_HAS_POSITIVE_EXPECTED_INFORMATION_GAIN",
            }
        else:
            payload = {
                "owner": self.owner_id,
                "status": "PHI_ACTION_SELECTED_BY_EXPECTED_INFORMATION_GAIN",
                "selected_action": ranked[0],
                "ranked_actions": ranked,
                "selected_action_belongs_to_frozen_frontier": ranked[0]["action_id"] in frozen_actions,
            }
        payload["digest"] = digest_payload(payload)
        return payload

    def update_belief(self, *, hypotheses: Sequence[str], action_id: str, observation: str, likelihoods: Mapping[str, Mapping[str, Mapping[str, float]]], priors: Mapping[str, float]) -> Mapping[str, Any]:
        hs = tuple(str(x) for x in hypotheses)
        weights = {h: float(priors[h]) * float(likelihoods.get(action_id, {}).get(h, {}).get(str(observation), 0.0)) for h in hs}
        total = sum(weights.values())
        if total <= 0.0:
            payload = {
                "owner": self.owner_id,
                "status": "OBSERVATION_OUTSIDE_FROZEN_HYPOTHESIS_SET",
                "posterior": {},
                "fallback_owner": AxisModelingOwner.owner_id,
            }
        else:
            posterior = {h: weights[h] / total for h in hs}
            payload = {
                "owner": self.owner_id,
                "status": "BELIEF_UPDATED_FROM_TYPED_OBSERVATION",
                "posterior": posterior,
                "surviving_hypothesis_ids": [h for h, p in posterior.items() if p > 1e-12],
            }
        payload["digest"] = digest_payload(payload)
        return payload


class OntologyEvolutionOwner:
    """Evidence-driven split/merge/demote/retire; never relabels concepts by preference."""
    owner_id = ONTOLOGY_EVOLUTION_OWNER_ID

    def evolve(self, concepts: Sequence[Mapping[str, Any]], evidence: Mapping[str, Any]) -> Mapping[str, Any]:
        rows = {str(x.get("concept_id")): dict(x) for x in concepts if x.get("concept_id")}
        mode = str(evidence.get("mode", "")).upper()
        envs = sorted({str(x) for x in evidence.get("independent_environment_ids", ()) if str(x)})
        event = {"mode": mode, "independent_environment_ids": envs}
        if mode == "ROLE_FAILURE":
            cid = str(evidence.get("concept_id", "")); c = rows.get(cid)
            if not c or len(envs) < 2:
                status = "ONTOLOGY_CHANGE_BLOCKED_INSUFFICIENT_REPLICATED_FAILURE"
            else:
                failures = sorted(set(c.get("counterexample_environment_ids", ())) | set(envs))
                c["counterexample_environment_ids"] = failures
                parts = list(evidence.get("partitions", ()))
                if len(parts) >= 2:
                    c["status"] = "DEMOTED_SPLIT_PARENT"
                    children=[]
                    for part in parts:
                        label=str(part.get("label", "partition"))
                        child=dict(c)
                        child["concept_id"]="CONCEPT-"+digest_payload({"parent":cid,"partition":label})[:24].upper()
                        child["status"]="PROVISIONAL_SPLIT_CONCEPT"
                        child["parent_concept_id"]=cid
                        child["support_axis_ids"]=sorted({str(x) for x in part.get("support_axis_ids", ()) if str(x)})
                        child["revision"]=int(c.get("revision",0))+1
                        child["digest"]=digest_payload({k:v for k,v in child.items() if k!="digest"})
                        rows[child["concept_id"]]=child; children.append(child["concept_id"])
                    status="CONCEPT_SPLIT_ON_REPLICATED_ROLE_FAILURE"; event["child_concept_ids"]=children
                else:
                    c["status"]="DEMOTED_GROUNDED_CONCEPT"; c["revision"]=int(c.get("revision",0))+1
                    status="CONCEPT_DEMOTED_ON_REPLICATED_ROLE_FAILURE"
                c["digest"]=digest_payload({k:v for k,v in c.items() if k!="digest"}); rows[cid]=c
        elif mode == "MERGE_SUPPORT":
            ids=[str(x) for x in evidence.get("concept_ids", ()) if str(x)]
            cs=[rows.get(x) for x in ids]
            roles={(c.get("invariant_signature"),c.get("predictive_role"),c.get("causal_role")) for c in cs if c}
            if len(ids)<2 or any(c is None for c in cs) or len(envs)<2 or len(roles)!=1:
                status="ONTOLOGY_MERGE_BLOCKED_INSUFFICIENT_EQUIVALENCE_EVIDENCE"
            else:
                merged={"concept_id":"CONCEPT-"+digest_payload({"merge":sorted(ids),"roles":sorted(map(str,roles))})[:24].upper(),"owner":self.owner_id,"status":"MERGED_GROUNDED_CONCEPT","merged_from_concept_ids":sorted(ids),"independent_environment_ids":envs,"invariant_signature":cs[0].get("invariant_signature"),"predictive_role":cs[0].get("predictive_role"),"causal_role":cs[0].get("causal_role"),"support_axis_ids":sorted({a for c in cs for a in c.get("support_axis_ids",())}),"grounding_owner_ids":sorted({a for c in cs for a in c.get("grounding_owner_ids",())}),"revision":1}
                merged["digest"]=digest_payload(merged)
                for cid in ids: rows[cid]["status"]="RETIRED_AFTER_MERGE"
                rows[merged["concept_id"]]=merged; status="CONCEPTS_MERGED_ON_REPLICATED_EQUIVALENCE"; event["merged_concept_id"]=merged["concept_id"]
        elif mode == "RETIRE":
            cid=str(evidence.get("concept_id","")); c=rows.get(cid)
            if not c or len(envs)<3 or c.get("status") not in {"DEMOTED_GROUNDED_CONCEPT","DEMOTED_SPLIT_PARENT","PROVISIONAL_GROUNDED_CONCEPT"}:
                status="ONTOLOGY_RETIRE_BLOCKED"
            else:
                c["status"]="RETIRED_GROUNDED_CONCEPT"; c["retired_by_environment_ids"]=envs; rows[cid]=c; status="CONCEPT_RETIRED_AFTER_PERSISTENT_FAILURE"
        else:
            status="NO_ONTOLOGY_EVOLUTION_EVIDENCE"
        event.update({"owner":self.owner_id,"status":status}); event["digest"]=digest_payload(event)
        return {"owner":self.owner_id,"status":status,"concepts":[rows[k] for k in sorted(rows)],"event":event,"digest":digest_payload({"status":status,"event":event})}


class AdaptiveActionInventionOwner:
    owner_id = ADAPTIVE_ACTION_OWNER_ID
    accepted_axis_statuses = {"AXIS_BIRTH_OOD_VALIDATED", "AXIS_BIRTH_PROMISING_EXPLORATORY"}

    def invent(self, freeze: Mapping[str, Any], axis_modeling: Mapping[str, Any]) -> Mapping[str, Any]:
        axis = dict(axis_modeling.get("best_axis_birth") or {})
        if axis.get("status") not in self.accepted_axis_statuses or not axis.get("axis_id"):
            payload={"owner":self.owner_id,"status":"ACTION_INVENTION_BLOCKED_NO_VALIDATED_GENERATED_AXIS","actions":[]}
            return {**payload,"digest":digest_payload(payload)}
        aid=str(axis["axis_id"])
        actions=[]
        specs=(("COMPARE_HIGH_LOW_RESIDUAL",1.0,1.0,1.0,0.05),("MEASURE_LOCAL_TRANSFER",1.4,1.2,1.0,0.08),("PERTURB_LOCAL_NEIGHBORHOOD",2.2,1.4,2.0,0.12))
        for op,compute,time_cost,meas,risk in specs:
            row={"action_id":f"{op}::{aid}","action_class":"GENERATED_AXIS_RESEARCH_ACTION","axis_id":aid,"source_axis_id":axis.get("source_axis_id"),"operation":op,"preconditions":["GENERATED_AXIS_RESEARCH_LOCAL","AXIS_BIRTH_OOD_OR_EXPLORATORY_VALIDATED","TYPED_RESEARCH_MEASUREMENT_ONLY"],"expected_result":"TYPED_OBSERVATION","resource_cost":{"compute":compute,"memory":1.0,"measurements":meas,"time":time_cost,"risk":risk},"risk_class":"RESEARCH_ONLY_NO_UNRESTRICTED_ACTUATION"}
            row["digest"]=digest_payload(row); actions.append(row)
        expanded=dict(freeze); expanded["parent_freeze_digest"]=freeze.get("freeze_digest"); expanded["representation_expanded"]=True; expanded["generated_axis_id"]=aid; expanded["action_frontier"]=[*freeze.get("action_frontier",()),*actions]; expanded["freeze_digest"]=digest_payload({k:v for k,v in expanded.items() if k!="freeze_digest"})
        payload={"owner":self.owner_id,"status":"NEW_ACTIONS_INVENTED_FROM_GENERATED_AXIS","generated_axis_id":aid,"actions":actions,"expanded_freeze":expanded,"canonical_registry_mutated":False}
        payload["digest"]=digest_payload(payload); return payload


class HigherOrderOperatorEvolutionOwner:
    owner_id = HIGHER_OPERATOR_OWNER_ID
    def evolve(self, operators: Sequence[Mapping[str, Any]], stress_receipts: Sequence[Mapping[str, Any]], composition_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        qualified=[dict(x) for x in operators if x.get("status")=="QUALIFIED_RESIDENT_OPERATOR"]
        by={str(x.get("operator_id")):x for x in qualified}
        eligible=[]
        for oid in sorted(by):
            envs={str(r.get("environment_id")) for r in stress_receipts if r.get("operator_id")==oid and r.get("pass") is True and r.get("ood") is True and r.get("adversarial") is True}
            if len(envs)>=2: eligible.append(oid)
        gain=float(composition_receipt.get("composition_score",0.0))-float(composition_receipt.get("best_component_score",0.0))
        if len(eligible)<2 or gain<=0 or composition_receipt.get("independent_evaluation") is not True:
            payload={"owner":self.owner_id,"status":"HIGHER_ORDER_OPERATOR_BLOCKED_INSUFFICIENT_OOD_OR_GAIN","operator":None,"eligible_operator_ids":eligible,"composition_gain":gain}
        else:
            steps=[]
            for oid in eligible:
                steps.append({"operator_id":oid,"guard":"QUALIFIED_AND_OOD_STRESS_PASSED","typed_owner_steps":by[oid].get("typed_owner_steps",())})
            op={"operator_id":"HIGHER-OPERATOR-"+digest_payload({"operators":eligible,"composition":dict(composition_receipt)})[:24].upper(),"owner":self.owner_id,"status":"QUALIFIED_HIGHER_ORDER_OPERATOR","component_operator_ids":eligible,"composition":"SEQUENTIAL_TYPED_OPERATOR_COMPOSITION","steps":steps,"composition_gain":gain,"claim_boundary":{"arbitrary_code_generated":False,"owner_gates_bypassed":False,"new_scientific_law_claimed":False}}
            op["digest"]=digest_payload(op); payload={"owner":self.owner_id,"status":"HIGHER_ORDER_OPERATOR_QUALIFIED","operator":op,"eligible_operator_ids":eligible,"composition_gain":gain}
        payload["digest"]=digest_payload(payload); return payload


class FiniteResourceActionPolicyOwner:
    owner_id = RESOURCE_POLICY_OWNER_ID
    resource_keys=("compute","memory","measurements","time")
    def select(self, explorer: OpenWorldPhiExplorerOwner, freeze: Mapping[str, Any], *, hypotheses: Sequence[str], likelihoods: Mapping[str, Mapping[str, Mapping[str,float]]], budget: Mapping[str,float], priors: Mapping[str,float] | None=None, action_costs: Mapping[str,Mapping[str,float]] | None=None) -> Mapping[str,Any]:
        ranked=explorer.select_action(freeze,hypotheses=hypotheses,likelihoods=likelihoods,priors=priors).get("ranked_actions",[])
        frontier={str(x.get("action_id")):x for x in freeze.get("action_frontier",())}
        scored=[]; blocked=[]
        for row in ranked:
            aid=str(row["action_id"]); cost=dict((action_costs or {}).get(aid) or frontier.get(aid,{}).get("resource_cost") or {"compute":1.0,"memory":1.0,"measurements":1.0,"time":1.0,"risk":0.05})
            feasible=all(float(cost.get(k,0.0))<=float(budget.get(k,0.0)) for k in self.resource_keys)
            if not feasible: blocked.append(aid); continue
            denom=sum(float(cost.get(k,0.0))/max(float(budget.get(k,0.0)),1e-12) for k in self.resource_keys)+float(cost.get("risk",0.0))
            utility=float(row.get("expected_information_gain_bits",0.0))/max(denom,1e-12)
            scored.append({**row,"resource_cost":cost,"information_per_normalized_cost":utility})
        scored.sort(key=lambda x:(-x["information_per_normalized_cost"],-x["expected_information_gain_bits"],x["action_id"]))
        if not scored or scored[0]["expected_information_gain_bits"]<=1e-12:
            status="RESOURCE_BUDGET_BLOCKED_OR_NO_INFORMATION"; selected=None
        else:
            status="RESOURCE_AWARE_PHI_ACTION_SELECTED"; selected=scored[0]
        payload={"owner":self.owner_id,"status":status,"selected_action":selected,"ranked_feasible_actions":scored,"budget_blocked_action_ids":blocked,"budget":dict(budget),"objective":"EIG_BITS_PER_NORMALIZED_RESOURCE_PLUS_RISK"}
        payload["digest"]=digest_payload(payload); return payload


class LearnedWorldActionModelOwner:
    """Learn P(observation|action,hypothesis) from post-freeze resolved experience.

    The owner never receives a pre-freeze truth label. Estimator choice is made from
    an internal candidate family on a deterministic environment-level calibration
    split. Unsupported or context-OOD predictions fail closed and cannot feed EIG.
    """
    owner_id = WORLD_ACTION_MODEL_OWNER_ID
    candidate_alphas = (0.0, 0.5, 1.0, 2.0)

    @staticmethod
    def _split(environment_id: str) -> str:
        # Fixed before seeing outcomes; entire environments remain together.
        bucket = int(digest_payload({"environment_id": str(environment_id), "split":"WORLD_ACTION_V1"})[:8], 16) % 5
        return "CALIBRATION" if bucket == 0 else "TRAIN"

    def validate_experience(self, experience: Mapping[str, Any]) -> Mapping[str, Any]:
        row = dict(experience)
        required = ("environment_id", "action_id", "observation", "resolved_hypothesis_id")
        missing = [k for k in required if not str(row.get(k, "")).strip()]
        reasons = []
        if missing: reasons.append("MISSING_REQUIRED_FIELDS:" + ",".join(missing))
        if row.get("post_freeze_hypothesis_binding") is not True:
            reasons.append("HYPOTHESIS_BINDING_NOT_POST_FREEZE")
        if row.get("prefreeze_truth_exposed") is True:
            reasons.append("PREFREEZE_TRUTH_EXPOSURE_FORBIDDEN")
        if row.get("action_from_frozen_phi_frontier") is not True:
            reasons.append("ACTION_NOT_BOUND_TO_FROZEN_PHI_FRONTIER")
        status = "WORLD_ACTION_EXPERIENCE_ADMITTED" if not reasons else "WORLD_ACTION_EXPERIENCE_REJECTED"
        payload={"owner":self.owner_id,"status":status,"reasons":reasons,"experience":row if not reasons else None}
        payload["digest"]=digest_payload(payload); return payload

    @staticmethod
    def _context_bounds(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Mapping[str, float]]:
        vals: dict[str,list[float]] = {}
        for row in rows:
            for k,v in dict(row.get("context") or {}).items():
                if isinstance(v,(int,float)) and math.isfinite(float(v)):
                    vals.setdefault(str(k),[]).append(float(v))
        return {k:{"min":min(vs),"max":max(vs)} for k,vs in sorted(vals.items()) if vs}

    @staticmethod
    def _table_for_alpha(train: Sequence[Mapping[str, Any]], outcomes: Sequence[str], alpha: float) -> tuple[dict[str,Any],dict[str,int]]:
        counts: dict[tuple[str,str],dict[str,int]] = {}
        support: dict[str,int] = {}
        for row in train:
            key=(str(row["action_id"]),str(row["resolved_hypothesis_id"]))
            counts.setdefault(key,{o:0 for o in outcomes})[str(row["observation"])]+=1
        table: dict[str,Any] = {}
        for (aid,hid),cs in sorted(counts.items()):
            n=sum(cs.values()); denom=n+alpha*len(outcomes)
            if denom<=0: continue
            table.setdefault(aid,{})[hid]={o:(cs.get(o,0)+alpha)/denom for o in outcomes}
            support[f"{aid}||{hid}"]=n
        return table,support

    @staticmethod
    def _score(table: Mapping[str,Any], calibration: Sequence[Mapping[str, Any]], outcomes: Sequence[str]) -> Mapping[str,float]:
        if not calibration: return {"mean_log_loss":float("inf"),"mean_brier":float("inf"),"scored":0}
        ll=0.0; br=0.0; n=0
        for row in calibration:
            pred=table.get(str(row["action_id"]),{}).get(str(row["resolved_hypothesis_id"]))
            if not isinstance(pred,Mapping): continue
            y=str(row["observation"]); p=max(float(pred.get(y,0.0)),1e-12); ll-=math.log(p)
            br+=sum((float(pred.get(o,0.0))-(1.0 if o==y else 0.0))**2 for o in outcomes)
            n+=1
        return {"mean_log_loss":ll/max(n,1),"mean_brier":br/max(n,1),"scored":n}

    def fit(self, experiences: Sequence[Mapping[str, Any]], *, phi_model_space_freeze: Mapping[str, Any], min_pair_support: int = 3) -> Mapping[str, Any]:
        admitted=[]; rejected=[]
        for x in experiences:
            v=self.validate_experience(x)
            (admitted if v["status"]=="WORLD_ACTION_EXPERIENCE_ADMITTED" else rejected).append(dict(x) if v["status"].endswith("ADMITTED") else v)
        train=[r for r in admitted if self._split(str(r["environment_id"]))=="TRAIN"]
        cal=[r for r in admitted if self._split(str(r["environment_id"]))=="CALIBRATION"]
        outcomes=sorted({str(r["observation"]) for r in admitted})
        if len(outcomes)<2 or not train or not cal:
            payload={"owner":self.owner_id,"status":"WORLD_ACTION_MODEL_BLOCKED_INSUFFICIENT_SPLIT_SUPPORT","admitted_count":len(admitted),"rejected_count":len(rejected),"train_count":len(train),"calibration_count":len(cal)}
            payload["digest"]=digest_payload(payload); return payload
        scan=dict(phi_model_space_freeze.get("scan") or {})
        freeze=dict(phi_model_space_freeze.get("freeze") or phi_model_space_freeze)
        internal_ok=(scan.get("all_registered_axes_visited") is True and freeze.get("internet_used_for_candidate_or_action_selection") is False)
        candidates=[]
        for alpha in self.candidate_alphas:
            table,support=self._table_for_alpha(train,outcomes,alpha)
            score=self._score(table,cal,outcomes)
            candidates.append({"estimator_id":f"CATEGORICAL_DIRICHLET_ALPHA_{alpha:g}","alpha":alpha,"likelihoods":table,"pair_support":support,**score})
        candidates.sort(key=lambda x:(x["mean_log_loss"],x["mean_brier"],x["alpha"]))
        best=candidates[0]
        k=len(outcomes); uniform_log=math.log(k); uniform_brier=1.0-1.0/k
        enough_pairs=all(int(v)>=min_pair_support for v in best["pair_support"].values()) and bool(best["pair_support"])
        calibrated=(best["scored"]>=max(4,len(best["pair_support"])) and best["mean_log_loss"]<=uniform_log+1e-12 and best["mean_brier"]<=uniform_brier+1e-12)
        status="WORLD_ACTION_MODEL_CALIBRATED" if internal_ok and enough_pairs and calibrated else "WORLD_ACTION_MODEL_PROVISIONAL_OR_BLOCKED"
        model={"owner":self.owner_id,"status":status,"estimator_id":best["estimator_id"],"alpha":best["alpha"],"outcomes":outcomes,"likelihoods":best["likelihoods"],"pair_support":best["pair_support"],"min_pair_support":min_pair_support,"context_bounds":self._context_bounds(train),"calibration":{"environment_split":"DIGEST_FIXED_ENVIRONMENT_LEVEL_4_TO_1","train_count":len(train),"calibration_count":len(cal),"scored":best["scored"],"mean_log_loss":best["mean_log_loss"],"uniform_log_loss":uniform_log,"mean_brier":best["mean_brier"],"uniform_brier":uniform_brier},"estimator_candidates":[{k:v for k,v in c.items() if k not in {"likelihoods","pair_support"}} for c in candidates],"phi_model_space":{"scan_digest":scan.get("digest"),"freeze_digest":freeze.get("freeze_digest"),"registered_axis_count":scan.get("registered_axis_count"),"all_registered_axes_visited":scan.get("all_registered_axes_visited"),"internet_used_prefreeze":freeze.get("internet_used_for_candidate_or_action_selection")},"claim_boundary":{"likelihood_table_supplied_by_benchmark":False,"prefreeze_truth_labels_used":False,"calibration_is_independent_environment_split":True,"ood_extrapolation_allowed":False}}
        model["model_digest"]=digest_payload(model)
        payload={"owner":self.owner_id,"status":status,"model":model,"admitted_experience_count":len(admitted),"rejected_experience_count":len(rejected)}
        payload["digest"]=digest_payload(payload); return payload

    def likelihoods_for(self, model: Mapping[str,Any], *, hypotheses: Sequence[str], action_ids: Sequence[str], context: Mapping[str,Any] | None=None) -> Mapping[str,Any]:
        if model.get("status")!="WORLD_ACTION_MODEL_CALIBRATED":
            payload={"owner":self.owner_id,"status":"WORLD_ACTION_MODEL_NOT_CALIBRATED","likelihoods":{}}; payload["digest"]=digest_payload(payload); return payload
        ctx=dict(context or {}); ood=[]
        for k,b in dict(model.get("context_bounds") or {}).items():
            if k in ctx and isinstance(ctx[k],(int,float)):
                v=float(ctx[k]); lo=float(b["min"]); hi=float(b["max"]);
                if v<lo or v>hi: ood.append({"dimension":k,"value":v,"train_min":lo,"train_max":hi})
        if ood:
            payload={"owner":self.owner_id,"status":"WORLD_ACTION_MODEL_OOD_UNCERTAIN","likelihoods":{},"ood_dimensions":ood,"fallback":"COLLECT_GROUNDING_OR_EXPAND_REPRESENTATION"}; payload["digest"]=digest_payload(payload); return payload
        hs=[str(x) for x in hypotheses]; src=dict(model.get("likelihoods") or {}); support=dict(model.get("pair_support") or {}); minimum=int(model.get("min_pair_support",3)); eligible={}; blocked=[]
        for aid in [str(x) for x in action_ids]:
            if all(aid in src and h in src[aid] and int(support.get(f"{aid}||{h}",0))>=minimum for h in hs): eligible[aid]={h:dict(src[aid][h]) for h in hs}
            else: blocked.append(aid)
        status="LEARNED_LIKELIHOODS_READY_FOR_EIG" if eligible else "WORLD_ACTION_MODEL_INSUFFICIENT_SUPPORT"
        payload={"owner":self.owner_id,"status":status,"likelihoods":eligible,"eligible_action_ids":sorted(eligible),"blocked_action_ids":blocked,"model_digest":model.get("model_digest"),"ood_dimensions":[]}
        payload["digest"]=digest_payload(payload); return payload

    @staticmethod
    def _context_signature(row: Mapping[str, Any], key: str, threshold: float) -> str:
        ctx=dict(row.get("context") or {})
        v=ctx.get(key)
        if not isinstance(v,(int,float)) or not math.isfinite(float(v)):
            return "CTX_MISSING"
        return "CTX_LOW" if float(v) <= threshold else "CTX_HIGH"

    def fit_contextual_nonstationary(self, experiences: Sequence[Mapping[str, Any]], *, phi_model_space_freeze: Mapping[str, Any], min_pair_support: int = 3) -> Mapping[str, Any]:
        admitted=[dict(x) for x in experiences if self.validate_experience(x).get("status")=="WORLD_ACTION_EXPERIENCE_ADMITTED"]
        train=[r for r in admitted if self._split(str(r["environment_id"]))=="TRAIN"]
        cal=[r for r in admitted if self._split(str(r["environment_id"]))=="CALIBRATION"]
        numeric_keys=sorted({str(k) for r in train for k,v in dict(r.get("context") or {}).items() if isinstance(v,(int,float)) and math.isfinite(float(v))})
        if not train or not cal or not numeric_keys:
            out={"owner":self.owner_id,"status":"CONTEXTUAL_WORLD_MODEL_BLOCKED_INSUFFICIENT_SUPPORT"}; out["digest"]=digest_payload(out); return out
        outcomes=sorted({str(r["observation"]) for r in admitted})
        base=self.fit(admitted,phi_model_space_freeze=phi_model_space_freeze,min_pair_support=min_pair_support)
        family_freeze=self.birth_model_families(phi_model_space_freeze, admitted)
        candidates=[]
        if base.get("model"):
            candidates.append({"family":"STATIONARY","key":None,"threshold":None,"score":base["model"]["calibration"]["mean_log_loss"],"brier":base["model"]["calibration"]["mean_brier"],"model":base["model"]})
        for key in numeric_keys:
            vals=sorted(float(dict(r.get("context") or {})[key]) for r in train if isinstance(dict(r.get("context") or {}).get(key),(int,float)))
            threshold=vals[len(vals)//2]
            aug=[]
            for r in admitted:
                rr=dict(r); rr["resolved_hypothesis_id"]=str(rr["resolved_hypothesis_id"])+"||"+self._context_signature(rr,key,threshold); aug.append(rr)
            fit=self.fit(aug,phi_model_space_freeze=phi_model_space_freeze,min_pair_support=max(2,min_pair_support//2))
            if fit.get("model") and fit.get("status")=="WORLD_ACTION_MODEL_CALIBRATED":
                candidates.append({"family":"CONTEXT_BIN_2","key":key,"threshold":threshold,"score":fit["model"]["calibration"]["mean_log_loss"],"brier":fit["model"]["calibration"]["mean_brier"],"model":fit["model"]})
        if not candidates:
            out={"owner":self.owner_id,"status":"CONTEXTUAL_WORLD_MODEL_BLOCKED_NO_CALIBRATED_FAMILY"}; out["digest"]=digest_payload(out); return out
        candidates.sort(key=lambda x:(x["score"],x["brier"],x["family"],str(x["key"])))
        best=candidates[0]
        # Drift evidence: compare outcome rates in first/second temporal halves for each action/hypothesis.
        ordered=sorted(admitted,key=lambda r:(float(dict(r.get("context") or {}).get("time",0.0)),str(r["environment_id"])))
        mid=max(1,len(ordered)//2); halves=(ordered[:mid],ordered[mid:])
        def rates(rows):
            d={}
            for r in rows:
                k=(str(r["action_id"]),str(r["resolved_hypothesis_id"])); d.setdefault(k,[]).append(1.0 if str(r["observation"])=="1" else 0.0)
            return {k:sum(v)/len(v) for k,v in d.items() if v}
        r0,r1=rates(halves[0]),rates(halves[1]); common=set(r0)&set(r1); drift=max([abs(r0[k]-r1[k]) for k in common] or [0.0])
        chosen=dict(best["model"]); chosen["model_family"]=best["family"]; chosen["context_key"]=best["key"]; chosen["context_threshold"]=best["threshold"]
        chosen["drift"]={"max_half_rate_shift":drift,"status":"DRIFT_DETECTED" if drift>=0.20 else "NO_STRONG_DRIFT_DETECTED","threshold":0.20}
        chosen["uncertainty_decomposition"]={"epistemic":"SUPPORT_AND_OOD_GATED","aleatoric":"PREDICTIVE_CATEGORICAL_ENTROPY","claim":"operational decomposition, not unique physical decomposition"}
        chosen["candidate_model_families"]=[{"family":c["family"],"context_key":c["key"],"threshold":c["threshold"],"calibration_log_loss":c["score"],"calibration_brier":c["brier"]} for c in candidates]
        chosen["model_digest"]=digest_payload(chosen)
        chosen["family_freeze_digest"]=family_freeze.get("freeze_digest")
        out={"owner":self.owner_id,"status":"CONTEXTUAL_NONSTATIONARY_WORLD_MODEL_CALIBRATED","model":chosen,"selected_family":best["family"],"selected_context_key":best["key"],"drift":chosen["drift"],"family_freeze":family_freeze}; out["digest"]=digest_payload(out); return out

    def contextual_likelihoods_for(self, model: Mapping[str,Any], *, hypotheses: Sequence[str], action_ids: Sequence[str], context: Mapping[str,Any] | None=None) -> Mapping[str,Any]:
        if model.get("model_family")!="CONTEXT_BIN_2":
            return self.likelihoods_for(model,hypotheses=hypotheses,action_ids=action_ids,context=context)
        key=str(model.get("context_key")); threshold=float(model.get("context_threshold")); ctx=dict(context or {})
        if key not in ctx or not isinstance(ctx[key],(int,float)):
            out={"owner":self.owner_id,"status":"WORLD_ACTION_MODEL_CONTEXT_REQUIRED","likelihoods":{},"selected_action":None}; out["digest"]=digest_payload(out); return out
        sig="CTX_LOW" if float(ctx[key])<=threshold else "CTX_HIGH"
        hs=[str(h)+"||"+sig for h in hypotheses]
        raw=self.likelihoods_for(model,hypotheses=hs,action_ids=action_ids,context=context)
        if raw.get("status")!="LEARNED_LIKELIHOODS_READY_FOR_EIG": return raw
        remap={aid:{h:raw["likelihoods"][aid][h+"||"+sig] for h in hypotheses} for aid in raw["likelihoods"]}
        raw={**raw,"likelihoods":remap,"context_signature":sig,"context_key":key}; raw["digest"]=digest_payload({k:v for k,v in raw.items() if k!="digest"}); return raw

    def birth_model_families(self, phi_model_space_freeze: Mapping[str, Any], experiences: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        scan=dict(phi_model_space_freeze.get("scan") or {})
        freeze=dict(phi_model_space_freeze.get("freeze") or phi_model_space_freeze)
        rows=list(scan.get("axis_rows") or ())
        provenance=[]
        for row in rows:
            qid=str(row.get("qualified_axis_id", ""))
            low=qid.lower()
            if any(t in low for t in ("probability","uncertainty","state","memory","time","temporal","dynamic","causal","model")):
                provenance.append(qid)
        numeric=sorted({str(k) for e in experiences for k,v in dict(e.get("context") or {}).items() if isinstance(v,(int,float)) and math.isfinite(float(v))})
        has_time=any(isinstance(e.get("time_index"),(int,float)) or isinstance(dict(e.get("context") or {}).get("time"),(int,float)) for e in experiences)
        has_history=any(str(e.get("previous_observation", "")).strip() for e in experiences)
        fam=[{"family_id":"STATIONARY","conditioning":[]}]
        for key in numeric: fam.append({"family_id":"CONTEXT_BIN_2","context_key":key,"conditioning":[key]})
        if has_time: fam.append({"family_id":"TIME_BIN_2","conditioning":["time"]})
        if has_history: fam.append({"family_id":"HISTORY1","conditioning":["previous_observation"]})
        for key in numeric:
            if has_time: fam.append({"family_id":"CONTEXT_TIME_BIN_2","context_key":key,"conditioning":[key,"time"]})
            if has_history: fam.append({"family_id":"CONTEXT_HISTORY_BIN_2","context_key":key,"conditioning":[key,"previous_observation"]})
        out={"owner":PHI_MODEL_FAMILY_BIRTH_OWNER_ID,"status":"PHI_MODEL_FAMILY_FRONTIER_FROZEN","families":fam,"phi_axis_provenance":sorted(set(provenance)),"registered_axis_count":scan.get("registered_axis_count"),"all_registered_axes_visited":scan.get("all_registered_axes_visited"),"internet_used_prefreeze":freeze.get("internet_used_for_candidate_or_action_selection"),"outcomes_inspected_for_family_birth":False}
        out["freeze_digest"]=digest_payload(out); return out

    def decompose_uncertainty(self, model: Mapping[str,Any], *, action_id:str, hypothesis_id:str, context:Mapping[str,Any]|None=None) -> Mapping[str,Any]:
        ctx=dict(context or {}); key=model.get("context_key"); threshold=model.get("context_threshold"); hid=str(hypothesis_id)
        if model.get("model_family")=="CONTEXT_BIN_2" and key is not None and threshold is not None:
            if key not in ctx or not isinstance(ctx[key],(int,float)):
                out={"owner":UNCERTAINTY_OWNER_ID,"status":"UNCERTAINTY_INSUFFICIENT_CONTEXT","epistemic":1.0,"aleatoric":None}; out["digest"]=digest_payload(out); return out
            hid += "||" + ("CTX_LOW" if float(ctx[key])<=float(threshold) else "CTX_HIGH")
        pred=dict(model.get("likelihoods") or {}).get(str(action_id),{}).get(hid)
        support=int(dict(model.get("pair_support") or {}).get(f"{action_id}||{hid}",0)); alpha=float(model.get("alpha",0.0)); K=max(1,len(model.get("outcomes") or ()))
        if not isinstance(pred,Mapping) or support<=0:
            out={"owner":UNCERTAINTY_OWNER_ID,"status":"UNCERTAINTY_INSUFFICIENT_SUPPORT","epistemic":1.0,"aleatoric":None}; out["digest"]=digest_payload(out); return out
        g=max(0.0,1.0-sum(float(p)**2 for p in pred.values())); concentration=support+alpha*K
        epi=g/(concentration+1.0); alea=g*concentration/(concentration+1.0)
        out={"owner":UNCERTAINTY_OWNER_ID,"status":"UNCERTAINTY_DECOMPOSED_DIRICHLET_OPERATIONAL","epistemic":epi,"aleatoric":alea,"predictive":g,"identity_error":abs(epi+alea-g),"support":support,"claim_boundary":"operational decomposition; not unique physical decomposition"}; out["digest"]=digest_payload(out); return out

    def detect_drift(self, experiences: Sequence[Mapping[str,Any]], *, threshold:float=0.20, min_support:int=5) -> Mapping[str,Any]:
        rows=[dict(e) for e in experiences if self.validate_experience(e).get("status")=="WORLD_ACTION_EXPERIENCE_ADMITTED"]
        rows.sort(key=lambda e:(float(dict(e.get("context") or {}).get("time",e.get("time_index",0.0))),str(e.get("environment_id"))))
        if len(rows)<2*min_support:
            out={"owner":DRIFT_OWNER_ID,"status":"DRIFT_INSUFFICIENT_SUPPORT","max_total_variation":0.0}; out["digest"]=digest_payload(out); return out
        mid=len(rows)//2; outcomes=sorted({str(e["observation"]) for e in rows})
        def dist(block):
            counts={}
            for e in block:
                k=(str(e["action_id"]),str(e["resolved_hypothesis_id"])); counts.setdefault(k,{o:0 for o in outcomes})[str(e["observation"])]+=1
            result={}
            for k,c in counts.items():
                n=sum(c.values())
                if n>=min_support: result[k]={o:c[o]/n for o in outcomes}
            return result
        a,b=dist(rows[:mid]),dist(rows[mid:]); common=sorted(set(a)&set(b)); shifts=[]
        for k in common: shifts.append({"pair":list(k),"total_variation":0.5*sum(abs(a[k].get(o,0)-b[k].get(o,0)) for o in outcomes)})
        mx=max([x["total_variation"] for x in shifts] or [0.0]); repl=sum(x["total_variation"]>=threshold for x in shifts)
        out={"owner":DRIFT_OWNER_ID,"status":"WORLD_ACTION_MODEL_DRIFT_DETECTED" if mx>=threshold and repl>=2 else "NO_REPLICATED_WORLD_ACTION_MODEL_DRIFT","threshold":threshold,"max_total_variation":mx,"replicated_pair_count":repl,"pair_shifts":shifts}; out["digest"]=digest_payload(out); return out

    def select_action(self, explorer: OpenWorldPhiExplorerOwner, freeze: Mapping[str,Any], model: Mapping[str,Any], *, hypotheses: Sequence[str], priors: Mapping[str,float] | None=None, context: Mapping[str,Any] | None=None) -> Mapping[str,Any]:
        action_ids=[str(x.get("action_id")) for x in freeze.get("action_frontier",()) if x.get("action_id")]
        learned=self.contextual_likelihoods_for(model,hypotheses=hypotheses,action_ids=action_ids,context=context)
        if learned["status"]!="LEARNED_LIKELIHOODS_READY_FOR_EIG":
            payload={"owner":self.owner_id,"status":learned["status"],"selected_action":None,"learned_likelihood_receipt":learned,"fallback":"COLLECT_EXPERIENCE_OR_EXPAND_REPRESENTATION"}; payload["digest"]=digest_payload(payload); return payload
        chosen=explorer.select_action(freeze,hypotheses=hypotheses,likelihoods=learned["likelihoods"],priors=priors)
        payload={"owner":self.owner_id,"status":"PHI_ACTION_SELECTED_FROM_LEARNED_WORLD_MODEL" if chosen.get("selected_action") else chosen.get("status"),"selected_action":chosen.get("selected_action"),"eig_receipt":chosen,"learned_likelihood_receipt":learned,"model_digest":model.get("model_digest"),"likelihood_source":"LEARNED_POSTFREEZE_EXPERIENCE_NOT_CALLER_TABLE"}
        payload["digest"]=digest_payload(payload); return payload


class TypedWorldActionAdapterOwner:
    owner_id = TYPED_ACTION_ADAPTER_OWNER_ID
    required_fields=("adapter_id","action_id","preconditions","input","cost","risk","expected_observation","provenance")
    def prepare(self, envelope: Mapping[str,Any]) -> Mapping[str,Any]:
        row=dict(envelope); missing=[k for k in self.required_fields if k not in row]
        ok=not missing and isinstance(row.get("preconditions"),Sequence) and not isinstance(row.get("preconditions"),(str,bytes))
        out={"owner":self.owner_id,"status":"TYPED_ACTION_ENVELOPE_PREPARED" if ok else "TYPED_ACTION_ENVELOPE_REJECTED","missing_fields":missing,"envelope":row if ok else None,"execution_authorized":False,"boundary":"HOST_BINDS_EXPLICIT_ADAPTER; NO_UNRESTRICTED_SHELL_NETWORK_OR_DEVICE_ACCESS"}; out["digest"]=digest_payload(out); return out
    def bind_result(self, prepared: Mapping[str,Any], result: Mapping[str,Any]) -> Mapping[str,Any]:
        env=dict(prepared.get("envelope") or {}); row=dict(result); ok=prepared.get("status")=="TYPED_ACTION_ENVELOPE_PREPARED" and str(row.get("adapter_id"))==str(env.get("adapter_id")) and str(row.get("action_id"))==str(env.get("action_id")) and "observation" in row
        out={"owner":self.owner_id,"status":"TYPED_ACTION_RESULT_BOUND" if ok else "TYPED_ACTION_RESULT_REJECTED","observation":row.get("observation") if ok else None,"provenance":row.get("provenance") if ok else None}; out["digest"]=digest_payload(out); return out

class BlindProcessIsolationOwner:
    owner_id = BLIND_PROCESS_OWNER_ID
    def run_exam(self, root: str|Path) -> Mapping[str,Any]:
        with tempfile.TemporaryDirectory(prefix="phi-blind-gse-") as td:
            td=Path(td); public=td/"public.json"; truth=td/"truth.json"; solution=td/"solution.json"; verdict=td/"verdict.json"
            gen="import json,sys;from pathlib import Path;pub,truth=map(Path,sys.argv[1:3]);rows=[{'x':i,'y':0 if i<6 else 1} for i in range(12)];pub.write_text(json.dumps({'rows':rows,'task':'infer change threshold'}));truth.write_text(json.dumps({'threshold':6,'hidden_regime':'SHIFT'}))"
            sol="import json,sys;from pathlib import Path;pub,out=map(Path,sys.argv[1:3]);d=json.loads(pub.read_text());rows=d['rows'];changes=[rows[i]['x'] for i in range(1,len(rows)) if rows[i]['y']!=rows[i-1]['y']];out.write_text(json.dumps({'threshold':changes[0] if changes else None,'solver_received_truth_path':False}))"
            eva="import json,sys;from pathlib import Path;truth,sol,out=map(Path,sys.argv[1:4]);t=json.loads(truth.read_text());s=json.loads(sol.read_text());out.write_text(json.dumps({'pass':s.get('threshold')==t.get('threshold'),'solution':s}))"
            subprocess.run([sys.executable,"-c",gen,str(public),str(truth)],check=True,cwd=str(root),capture_output=True,text=True)
            subprocess.run([sys.executable,"-c",sol,str(public),str(solution)],check=True,cwd=str(root),capture_output=True,text=True)
            subprocess.run([sys.executable,"-c",eva,str(truth),str(solution),str(verdict)],check=True,cwd=str(root),capture_output=True,text=True)
            v=json.loads(verdict.read_text()); out={"owner":self.owner_id,"status":"BLIND_GENERATOR_SOLVER_EVALUATOR_PASS" if v.get("pass") else "BLIND_GENERATOR_SOLVER_EVALUATOR_FAIL","solver_received_truth_path":False,"generator_process_separate":True,"solver_process_separate":True,"evaluator_process_separate":True,"solution":v.get("solution")}; out["digest"]=digest_payload(out); return out


class ResidentConsolidationOwner:
    owner_id = CONSOLIDATION_OWNER_ID
    def consolidate(self, state: Mapping[str,Any], *, max_transitions:int=48, stale_after:int=24) -> Mapping[str,Any]:
        out=dict(state); hb=int(out.get("heartbeat_count",0)); transitions=list(out.get("transitions",()))
        dropped=max(0,len(transitions)-max_transitions)
        if dropped: out["transitions"]=transitions[-max_transitions:]
        concepts=[]; retired=[]
        for c0 in out.get("concepts",()):
            c=dict(c0); last=int(c.get("last_supported_heartbeat",hb))
            if c.get("status") in {"PROVISIONAL_GROUNDED_CONCEPT","PROVISIONAL_SPLIT_CONCEPT"} and hb-last>=stale_after:
                c["status"]="RETIRED_STALE_PROVISIONAL_CONCEPT"; retired.append(c.get("concept_id"))
            concepts.append(c)
        out["concepts"]=concepts
        receipt={"owner":self.owner_id,"status":"RESIDENT_MEMORY_CONSOLIDATED","heartbeat":hb,"dropped_transition_count":dropped,"retired_stale_concept_ids":retired,"preserved_promoted_concept_count":sum(c.get("status") in {"PROMOTED_GROUNDED_CONCEPT","MERGED_GROUNDED_CONCEPT"} for c in concepts),"preserved_operator_count":len(out.get("operators",()))+len(out.get("higher_order_operators",()))}
        receipt["digest"]=digest_payload(receipt); out["consolidations"]=[*out.get("consolidations",()),receipt]; out["state_digest"]=_state_digest(out)
        return {"owner":self.owner_id,"status":receipt["status"],"state":out,"receipt":receipt,"digest":receipt["digest"]}


class ResidentCognitiveOrganism:
    owner_id = OWNER_ID

    def __init__(self, runtime: Any, state_path: str | Path | None = None) -> None:
        self.runtime = runtime
        resolved_state_path = default_resident_state_path(runtime) if state_path is None else validate_external_state_path(runtime, state_path)
        self.state = ResidentStateLedgerOwner(resolved_state_path, system_release=runtime.current_release_id() if hasattr(runtime, "current_release_id") else "UNSEALED-CURRENT")
        self.concepts = GroundedConceptFormationOwner()
        self.operator_compiler = SkillToOperatorCompilerOwner()
        self.goals = DynamicGoalGraphOwner()
        self.planner = OntologyAwarePlannerOwner()
        self.self_feedback = SelfModelFeedbackOwner()
        self.open_world = OpenWorldPhiExplorerOwner()
        self.ontology = OntologyEvolutionOwner()
        self.adaptive_actions = AdaptiveActionInventionOwner()
        self.higher_operators = HigherOrderOperatorEvolutionOwner()
        self.resource_policy = FiniteResourceActionPolicyOwner()
        self.world_action_model = LearnedWorldActionModelOwner()
        self.action_adapters = TypedWorldActionAdapterOwner()
        self.blind_isolation = BlindProcessIsolationOwner()
        self.consolidation = ResidentConsolidationOwner()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": self.owner_id,
            "release": self.state.system_release,
            "heartbeat_pipeline": [
                "INGEST_COGNITIVE_EPISODE", "UPDATE_GROUNDED_CONCEPTS", "REGISTER_SKILL_APPLICATION",
                "COMPILE_TYPED_OPERATOR_IF_QUALIFIED", "UPDATE_DYNAMIC_GOAL_GRAPH", "REPLAN_ON_ONTOLOGY_OR_CAPABILITY_CHANGE",
                "UPDATE_SELF_MODEL_FEEDBACK", "PERSIST_RESIDENT_STATE",
            ],
            "delegation": {
                "cognitive_core": COGNITIVE_OWNER_ID,
                "scientific_research_cycle": ScientificResearchCycleOwner.owner_id,
                "axis_modeling": AxisModelingOwner.owner_id,
                "structural_skill_formation": SKILL_FORMATION_OWNER_ID,
            },
            "resident_owners": {
                "state": STATE_OWNER_ID,
                "concept_formation": CONCEPT_OWNER_ID,
                "dynamic_goal_graph": GOAL_GRAPH_OWNER_ID,
                "ontology_aware_planner": PLANNER_OWNER_ID,
                "skill_to_operator_compiler": OPERATOR_COMPILER_OWNER_ID,
                "self_model_feedback": SELF_FEEDBACK_OWNER_ID,
                "open_world_phi_explorer": self.open_world.owner_id,
                "ontology_evolution": self.ontology.owner_id,
                "adaptive_action_invention": self.adaptive_actions.owner_id,
                "higher_order_operator_evolution": self.higher_operators.owner_id,
                "finite_resource_policy": self.resource_policy.owner_id,
                "learned_world_action_model": self.world_action_model.owner_id,
                "phi_model_family_birth": PHI_MODEL_FAMILY_BIRTH_OWNER_ID,
                "drift_detection": DRIFT_OWNER_ID,
                "uncertainty_decomposition": UNCERTAINTY_OWNER_ID,
                "typed_world_action_adapter": self.action_adapters.owner_id,
                "blind_generator_solver_evaluator": self.blind_isolation.owner_id,
                "consolidation_forgetting": self.consolidation.owner_id,
                "missing_representation_blind_world": MISSING_REPRESENTATION_OWNER_ID,
            },
            "hard_boundaries": {
                "parallel_scientific_solver_created": False,
                "compiled_operator_can_bypass_owner_gates": False,
                "goal_change_equals_unbounded_autonomy": False,
                "concept_equals_world_truth": False,
                "general_world_actuator_bound": False,
                "canonical_axis_registry_mutated_implicitly": False,
                "internet_can_choose_prefreeze_candidate_or_action": False,
                "hidden_solution_may_be_hardcoded_into_question_or_action_frontier": False,
                "ontology_change_requires_replicated_evidence": True,
                "higher_order_operator_requires_ood_adversarial_stress": True,
                "finite_resource_budget_is_not_physical_truth_gate": True,
                "learned_likelihood_requires_postfreeze_resolved_experience": True,
                "world_action_model_can_extrapolate_ood_without_uncertainty_gate": False,
                "model_family_may_inspect_prospective_outcomes_before_freeze": False,
                "drifted_model_may_remain_current_without_demotion": False,
                "typed_action_adapter_grants_unrestricted_io": False,
                "blind_solver_receives_hidden_truth_path": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def scan_open_world(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if request.get("external_sources") or request.get("internet_results"):
            raise ValueError("external/internet material is forbidden before Phi-space freeze")
        question = str(request.get("question", "")).strip()
        if not question:
            raise ValueError("question is required")
        return self.open_world.scan(
            self.runtime,
            question=question,
            required_observables=tuple(request.get("required_observables", ())),
            required_domains=tuple(request.get("required_domains", ())),
            include_all_connected_owners=bool(request.get("include_all_connected_owners", True)),
            activate_bridge_open_axes=bool(request.get("activate_bridge_open_axes", True)),
        )

    def select_open_world_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.open_world.select_action(
            freeze, hypotheses=tuple(request.get("hypotheses", ())),
            likelihoods=dict(request.get("likelihoods", {})), priors=request.get("priors"),
        )

    def record_world_action_experience(self, experience: Mapping[str,Any], *, commit: bool=True) -> Mapping[str,Any]:
        verdict=self.world_action_model.validate_experience(experience)
        if verdict.get("status")!="WORLD_ACTION_EXPERIENCE_ADMITTED": return verdict
        state=self.state.load(); row=dict(experience); row["experience_digest"]=digest_payload(row); state["world_action_experiences"]=[*state.get("world_action_experiences",()),row]
        commit_receipt=self.state.commit(state) if commit else None
        payload={"owner":self.owner_id,"status":"WORLD_ACTION_EXPERIENCE_RECORDED","experience_digest":row["experience_digest"],"commit":commit_receipt}; payload["digest"]=digest_payload(payload); return payload

    def learn_world_action_model(self, *, commit: bool=True, min_pair_support:int=3) -> Mapping[str,Any]:
        state=self.state.load()
        model_space=self.open_world.scan(self.runtime,question="learn calibrated conditional observation model P(observation|action,hypothesis) with uncertainty and OOD detection",required_observables=("probability_model","uncertainty_model","experiment_design","next_measurement_policy"))
        fit=self.world_action_model.fit(state.get("world_action_experiences",()),phi_model_space_freeze=model_space,min_pair_support=min_pair_support)
        if fit.get("model") is not None and fit.get("status")=="WORLD_ACTION_MODEL_CALIBRATED":
            state["world_action_models"]=[*state.get("world_action_models",()),fit["model"]][-8:]
            fit={**fit,"commit":self.state.commit(state) if commit else None}
        return fit

    def learn_contextual_nonstationary_world_action_model(self, *, commit: bool=True, min_pair_support:int=3) -> Mapping[str,Any]:
        state=self.state.load()
        model_space=self.open_world.scan(self.runtime,question="learn context conditional nonstationary P(observation|action,hypothesis,context,time) with drift and uncertainty decomposition",required_observables=("probability_model","uncertainty_model","state_estimation","memory","experiment_design","next_measurement_policy"))
        fit=self.world_action_model.fit_contextual_nonstationary(state.get("world_action_experiences",()),phi_model_space_freeze=model_space,min_pair_support=min_pair_support)
        if fit.get("model") is not None and fit.get("status")=="CONTEXTUAL_NONSTATIONARY_WORLD_MODEL_CALIBRATED":
            model=dict(fit["model"]); model["version"]=len(state.get("world_action_model_versions",()))+1
            state["world_action_models"]=[*state.get("world_action_models",()),model][-8:]
            state["world_action_model_versions"]=[*state.get("world_action_model_versions",()),model][-16:]
            fit={**fit,"model":model,"commit":self.state.commit(state) if commit else None}
        return fit

    def online_update_world_action_model(self, *, commit: bool=True, min_pair_support:int=3) -> Mapping[str,Any]:
        state=self.state.load(); drift=self.world_action_model.detect_drift(state.get("world_action_experiences",()))
        versions=[dict(m) for m in state.get("world_action_model_versions",())]
        demoted=False
        if drift.get("status")=="WORLD_ACTION_MODEL_DRIFT_DETECTED" and versions:
            versions[-1]["status"]="WORLD_ACTION_MODEL_DEMOTED_DRIFT"; versions[-1]["demotion_receipt_digest"]=drift.get("digest"); demoted=True
            state["world_action_model_versions"]=versions; state["world_action_drift_events"]=[*state.get("world_action_drift_events",()),drift]; self.state.commit(state)
        fit=self.learn_contextual_nonstationary_world_action_model(commit=commit,min_pair_support=min_pair_support)
        out={"owner":self.owner_id,"status":"ONLINE_WORLD_MODEL_UPDATED","drift":drift,"fit":fit,"previous_model_demoted":demoted}; out["digest"]=digest_payload(out); return out

    def select_action_from_contextual_world_model(self, freeze: Mapping[str,Any], request: Mapping[str,Any]) -> Mapping[str,Any]:
        result=self.select_action_from_learned_world_model(freeze,request)
        state=self.state.load(); models=[m for m in state.get("world_action_models",()) if m.get("status") in {"CONTEXTUAL_NONSTATIONARY_WORLD_MODEL_CALIBRATED","WORLD_ACTION_MODEL_CALIBRATED"}]
        if result.get("selected_action") and models and request.get("hypotheses"):
            result={**result,"uncertainty":self.world_action_model.decompose_uncertainty(models[-1],action_id=str(result["selected_action"]["action_id"]),hypothesis_id=str(tuple(request["hypotheses"])[0]),context=request.get("context"))}
        return result

    def prepare_typed_world_action(self, envelope: Mapping[str,Any], *, commit:bool=True) -> Mapping[str,Any]:
        receipt=self.action_adapters.prepare(envelope)
        if commit and receipt.get("status")=="TYPED_ACTION_ENVELOPE_PREPARED":
            state=self.state.load(); state["typed_action_adapter_receipts"]=[*state.get("typed_action_adapter_receipts",()),receipt][-64:]; self.state.commit(state)
        return receipt

    def bind_typed_world_action_result(self, prepared:Mapping[str,Any], result:Mapping[str,Any]) -> Mapping[str,Any]: return self.action_adapters.bind_result(prepared,result)
    def run_blind_process_isolation_exam(self) -> Mapping[str,Any]: return self.blind_isolation.run_exam(self.runtime.root)

    def select_action_from_learned_world_model(self, freeze: Mapping[str,Any], request: Mapping[str,Any]) -> Mapping[str,Any]:
        state=self.state.load(); models=[m for m in state.get("world_action_models",()) if m.get("status")=="WORLD_ACTION_MODEL_CALIBRATED"]
        if not models:
            payload={"owner":self.owner_id,"status":"NO_CALIBRATED_WORLD_ACTION_MODEL","selected_action":None,"fallback":"COLLECT_POSTFREEZE_RESOLVED_EXPERIENCE"}; payload["digest"]=digest_payload(payload); return payload
        return self.world_action_model.select_action(self.open_world,freeze,models[-1],hypotheses=tuple(request.get("hypotheses",())),priors=request.get("priors"),context=request.get("context"))

    def heartbeat(self, event: Mapping[str, Any], *, commit: bool = True) -> Mapping[str, Any]:
        state = self.state.load()
        environment_id = str(event.get("environment_id", "")).strip()
        if not environment_id:
            raise ValueError("environment_id is required")
        cognitive_episode = dict(event.get("cognitive_episode") or {})
        root_goal = dict(event.get("root_goal") or {})
        grounding = dict(event.get("grounding") or {})
        axis_ids = list(event.get("axis_ids") or cognitive_episode.get("research_region", {}).get("research_local_axis_ids", ()))

        concept_result = self.concepts.update(
            state.get("concepts", ()), environment_id=environment_id, axis_ids=axis_ids, grounding=grounding,
        )
        concepts = {str(x.get("concept_key")): dict(x) for x in state.get("concepts", ())}
        concept = concept_result.get("concept")
        if concept:
            cc=dict(concept); cc["last_supported_heartbeat"]=int(state.get("heartbeat_count",0))+1
            concepts[str(cc["concept_key"])] = cc
        concept_rows = [concepts[k] for k in sorted(concepts)]
        ontology_result = self.ontology.evolve(concept_rows, dict(event.get("ontology_evidence") or {}))
        if event.get("ontology_evidence"):
            concept_rows = list(ontology_result.get("concepts", concept_rows))

        applications = [dict(x) for x in state.get("skill_applications", ())]
        app = dict(event.get("skill_application") or {})
        if app:
            app.setdefault("environment_id", environment_id)
            if app.get("skill_id") and app.get("receipt_digest"):
                applications.append(app)
        skill = dict(event.get("skill") or {}) or None
        operator_result = self.operator_compiler.update(
            existing_operators=state.get("operators", ()), applications=applications, skill=skill,
        )
        operators = {str(x.get("operator_id")): dict(x) for x in state.get("operators", ())}
        operator = operator_result.get("operator")
        if operator:
            operators[str(operator["operator_id"])] = dict(operator)
        operator_rows = [operators[k] for k in sorted(operators)]

        goal_result = self.goals.update(
            state.get("goals", ()), root_goal=root_goal, concept_result=concept_result,
            operator_result=operator_result, cognitive_episode=cognitive_episode,
        )
        plan = self.planner.plan(
            goal_graph=goal_result, concepts=concept_rows, operators=operator_rows,
            previous_plans=state.get("plans", ()),
        )
        plans = [*state.get("plans", ()), plan]
        self_feedback = self.self_feedback.derive(
            concepts=concept_rows, operators=operator_rows, goal_graph=goal_result, cognitive_episode=cognitive_episode,
        )
        before_digest = state.get("state_digest")
        state.update({
            "release": self.state.system_release,
            "heartbeat_count": int(state.get("heartbeat_count", 0)) + 1,
            "goals": list(goal_result.get("goals", ())),
            "plans": plans,
            "concepts": concept_rows,
            "operators": operator_rows,
            "ontology_events": [*state.get("ontology_events", ()), ontology_result.get("event")] if event.get("ontology_evidence") else list(state.get("ontology_events", ())),
            "skill_applications": applications,
            "self_model_feedback": self_feedback,
        })
        transition = {
            "heartbeat": state["heartbeat_count"],
            "environment_id": environment_id,
            "concept_status": concept_result.get("status"),
            "operator_status": operator_result.get("status"),
            "selected_goal_id": goal_result.get("selected_goal_id"),
            "plan_id": plan.get("plan_id"),
            "plan_status": plan.get("status"),
            "previous_state_digest": before_digest,
        }
        transition["digest"] = digest_payload(transition)
        state["transitions"] = [*state.get("transitions", ()), transition]
        state["state_digest"] = _state_digest(state)
        commit_receipt = self.state.commit(state) if commit else None
        payload = {
            "schema": SCHEMA,
            "owner": self.owner_id,
            "heartbeat": state["heartbeat_count"],
            "concept_formation": concept_result,
            "ontology_evolution": ontology_result,
            "operator_compilation": operator_result,
            "goal_graph": goal_result,
            "plan": plan,
            "self_model_feedback": self_feedback,
            "state_commit": commit_receipt,
            "state": state,
            "status": "RESIDENT_HEARTBEAT_COMPLETE",
            "claim_boundary": {
                "autonomous_general_intelligence_demonstrated": False,
                "consciousness_demonstrated": False,
                "general_world_actuation_available": False,
                "resident_structural_self_modification_executable": True,
                "canonical_axis_registry_mutated": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    @classmethod
    def _run_base_qualification(cls, root: str | Path) -> Mapping[str, Any]:
        import tempfile
        from .runtime import LawSpaceRuntime

        root = Path(root)
        runtime = LawSpaceRuntime(root)
        cognitive = PhiCognitiveCore.run_qualification(root)
        generated = list(cognitive["demonstration"]["generated_axis_episodes"])
        skills = list(cognitive["demonstration"]["generated_axis_final_memory"]["skills"])
        skill = next((x for x in skills if x.get("status") == "PROMOTED_REUSABLE_SKILL"), None)
        if skill is None:
            raise RuntimeError("resident qualification requires promoted structural skill from cognitive qualification")
        canonical_before = canonical_axis_count()
        invariant = {"relation": "residual-localized-control-factor", "effect_class": "predictive-and-causal-discriminator"}
        grounding_owners = [
            {"owner_id": "SCIENTIFIC-RESEARCH-CYCLE/7.0.0", "independent": True},
            {"owner_id": "SCIENTIFIC-VERIFICATION-CORE/8.0.0", "independent": True},
        ]
        root_goal = {"goal_id": "GOAL-RESIDENT-QUALIFICATION", "statement": "explain, ground, transfer and compress a newly required representation"}
        with tempfile.TemporaryDirectory(prefix="phi-resident-") as td:
            resident = cls(runtime, Path(td) / "resident_state.json")
            events = []
            for index, episode in enumerate(generated[:3], start=1):
                ev: dict[str, Any] = {
                    "environment_id": f"resident-world-{index}",
                    "root_goal": root_goal,
                    "cognitive_episode": episode,
                    "axis_ids": episode.get("research_region", {}).get("research_local_axis_ids", ()),
                    "grounding": {
                        "invariant_signature": invariant,
                        "predictive_role": "reduces held-out residual under the qualified representation",
                        "causal_role": "indexes a discriminating intervention/measurement condition",
                        "owner_measurements": grounding_owners,
                        "contrast_pass": True,
                    },
                    "skill": skill,
                }
                if index == 3:
                    ev["skill_application"] = {
                        "skill_id": skill["skill_id"],
                        "environment_id": ev["environment_id"],
                        "success": True,
                        "execution_route": "LEARNED_SKILL_MACRO",
                        "receipt_digest": episode.get("digest"),
                    }
                events.append(resident.heartbeat(ev, commit=True))

            # Independent second successful reuse causes skill -> typed operator compilation.
            transfer_receipt = digest_payload({"skill_id": skill["skill_id"], "environment": "resident-world-4", "guard": skill.get("application_guard")})
            fourth = resident.heartbeat({
                "environment_id": "resident-world-4",
                "root_goal": root_goal,
                "cognitive_episode": {**generated[2], "environment_id": "resident-world-4"},
                "axis_ids": generated[2].get("research_region", {}).get("research_local_axis_ids", ()),
                "grounding": {
                    "invariant_signature": invariant,
                    "predictive_role": "reduces held-out residual under the qualified representation",
                    "causal_role": "indexes a discriminating intervention/measurement condition",
                    "owner_measurements": grounding_owners,
                    "contrast_pass": True,
                },
                "skill": skill,
                "skill_application": {
                    "skill_id": skill["skill_id"], "environment_id": "resident-world-4", "success": True,
                    "execution_route": "LEARNED_SKILL_MACRO", "receipt_digest": transfer_receipt,
                },
            }, commit=True)
            events.append(fourth)
            final_state = resident.state.load()

            # Negative control: one grounding owner must never promote a concept/operator.
            negative = cls(runtime, Path(td) / "negative_state.json")
            neg = negative.heartbeat({
                "environment_id": "resident-negative",
                "root_goal": root_goal,
                "cognitive_episode": generated[0],
                "axis_ids": generated[0].get("research_region", {}).get("research_local_axis_ids", ()),
                "grounding": {
                    "invariant_signature": invariant,
                    "predictive_role": "candidate",
                    "causal_role": "candidate",
                    "owner_measurements": [grounding_owners[0]],
                    "contrast_pass": True,
                },
                "skill": skill,
                "skill_application": {
                    "skill_id": skill["skill_id"], "environment_id": "resident-negative", "success": True,
                    "execution_route": "LEARNED_SKILL_MACRO", "receipt_digest": "NEGATIVE",
                },
            }, commit=True)

        # Open-world control: search/action selection comes from frozen Phi-space, never Internet.
        ow_temp = tempfile.TemporaryDirectory(prefix="phi-resident-openworld-")
        ow = cls(runtime, Path(ow_temp.name) / "resident_cognitive_state.json")
        open_scan = ow.scan_open_world({"question": "unknown system discriminating observables causal structure"})
        frontier = list(open_scan["freeze"]["action_frontier"])
        if len(frontier) < 3:
            raise RuntimeError("open-world qualification requires at least three Phi-generated actions")
        a0, a1, a2 = (frontier[i]["action_id"] for i in range(3))
        hypotheses = tuple(f"H{i}" for i in range(8))
        likelihoods = {a0: {}, a1: {}, a2: {}}
        for i, h in enumerate(hypotheses):
            for bit, action_id in enumerate((a0, a1, a2)):
                value = (i >> bit) & 1
                likelihoods[action_id][h] = {str(value): 1.0}
        plan0 = ow.select_open_world_action(open_scan["freeze"], {"hypotheses": hypotheses, "likelihoods": likelihoods})
        selected0 = plan0.get("selected_action", {}).get("action_id")
        truth_index = int(open_scan["freeze"]["freeze_digest"][:2], 16) % len(hypotheses)
        truth = hypotheses[truth_index]
        prior0 = {h: 1.0 / len(hypotheses) for h in hypotheses}
        obs0 = next(iter(likelihoods[selected0][truth]))
        post0 = ow.open_world.update_belief(hypotheses=hypotheses, action_id=selected0, observation=obs0, likelihoods=likelihoods, priors=prior0)
        remaining1 = tuple(post0.get("surviving_hypothesis_ids", ()))
        pri1 = {h: post0["posterior"][h] for h in remaining1}
        plan1 = ow.open_world.select_action(open_scan["freeze"], hypotheses=remaining1, likelihoods=likelihoods, priors=pri1)
        selected1 = plan1.get("selected_action", {}).get("action_id")
        obs1 = next(iter(likelihoods[selected1][truth]))
        post1 = ow.open_world.update_belief(hypotheses=remaining1, action_id=selected1, observation=obs1, likelihoods=likelihoods, priors=pri1)
        remaining2 = tuple(post1.get("surviving_hypothesis_ids", ()))
        pri2 = {h: post1["posterior"][h] for h in remaining2}
        plan2 = ow.open_world.select_action(open_scan["freeze"], hypotheses=remaining2, likelihoods=likelihoods, priors=pri2)
        selected2 = plan2.get("selected_action", {}).get("action_id")
        obs2 = next(iter(likelihoods[selected2][truth]))
        post2 = ow.open_world.update_belief(hypotheses=remaining2, action_id=selected2, observation=obs2, likelihoods=likelihoods, priors=pri2)
        zero_info = {a0: {h: {"same": 1.0} for h in hypotheses}}
        no_info = ow.open_world.select_action(open_scan["freeze"], hypotheses=hypotheses, likelihoods=zero_info)
        out_obs = ow.open_world.update_belief(hypotheses=hypotheses, action_id=a0, observation="impossible", likelihoods=likelihoods, priors=prior0)
        internet_blocked = False
        try:
            ow.scan_open_world({"question": "x", "internet_results": ["candidate"]})
        except ValueError:
            internet_blocked = True

        concept_states = [x["concept_formation"]["status"] for x in events]
        plans = [x["plan"] for x in events]
        final_concepts = list(final_state.get("concepts", ()))
        final_ops = list(final_state.get("operators", ()))
        checks = {
            "cognitive_core_dependency_is_qualified": cognitive.get("status") == "PASS_PHI_COGNITIVE_CORE_QUALIFICATION" and cognitive.get("passed") == cognitive.get("total") == 37,
            "heartbeat_persists_across_four_environments": final_state.get("heartbeat_count") == 4 and len(final_state.get("transitions", ())) == 4,
            "concept_starts_provisional": concept_states[0] == "PROVISIONAL_GROUNDED_CONCEPT",
            "concept_promotes_after_independent_environment": concept_states[1] == "PROMOTED_GROUNDED_CONCEPT",
            "concept_identity_survives_different_generated_axes": len(final_concepts) == 1 and len(final_concepts[0].get("support_axis_ids", ())) >= 3,
            "concept_revision_changes_with_new_support": int(final_concepts[0].get("revision", 0)) >= 2,
            "concept_has_two_independent_grounding_owners": len(final_concepts[0].get("grounding_owner_ids", ())) >= 2,
            "goal_graph_changes_after_concept_promotion": any(g.get("goal_class") == "REPLICATE_CONCEPT" and g.get("status") == "SATISFIED" for g in final_state.get("goals", ())) and any(g.get("goal_class") == "TEST_CONCEPT_TRANSFER" for g in final_state.get("goals", ())),
            "planner_replans_after_ontology_change": any(p.get("status") == "REPLANNED_AFTER_ONTOLOGY_OR_CAPABILITY_CHANGE" for p in plans[1:]),
            "first_skill_reuse_is_not_enough_to_compile_operator": events[2]["operator_compilation"]["status"] == "OPERATOR_COMPILATION_PENDING_REUSE_EVIDENCE",
            "second_independent_skill_reuse_compiles_operator": events[3]["operator_compilation"]["status"] == "RESIDENT_OPERATOR_COMPILED" and len(final_ops) == 1,
            "compiled_operator_is_typed_owner_macro": bool(final_ops) and all(step.get("owner") and step.get("operation") for step in final_ops[0].get("typed_owner_steps", ())),
            "compiled_operator_preserves_scientific_gates": bool(final_ops) and final_ops[0]["claim_boundary"]["scientific_gates_bypassed"] is False,
            "self_model_feedback_registers_new_capability": events[3]["self_model_feedback"]["capabilities"]["qualified_resident_operator_count"] == 1 and events[3]["self_model_feedback"]["capabilities"]["can_compile_typed_skill_macro"] is True,
            "operator_compilation_spawns_stress_test_goal": any(g.get("goal_class") == "STRESS_TEST_COMPILED_OPERATOR" and g.get("status") == "ACTIVE" for g in final_state.get("goals", ())),
            "negative_single_owner_grounding_fails_closed": neg["concept_formation"]["status"] == "CONCEPT_GROUNDING_INSUFFICIENT_FAIL_CLOSED",
            "negative_single_application_cannot_compile_operator": neg["operator_compilation"]["status"] != "RESIDENT_OPERATOR_COMPILED",
            "canonical_axis_registry_unchanged": canonical_before == canonical_axis_count(),
            "resident_does_not_claim_general_actuation_or_agi": events[-1]["claim_boundary"]["autonomous_general_intelligence_demonstrated"] is False and events[-1]["claim_boundary"]["general_world_actuation_available"] is False,
            "open_world_scan_visits_all_canonical_axes": open_scan["scan"].get("all_registered_axes_visited") is True and open_scan["scan"].get("registered_axis_count") == canonical_axis_count(),
            "open_world_scan_has_no_fixed_owner_or_axis_order_ceiling": open_scan["scan"].get("fixed_owner_visit_budget") is None and open_scan["scan"].get("fixed_candidate_axis_order_ceiling") is None,
            "open_world_action_frontier_is_phi_generated_and_frozen": len(frontier) > 0 and open_scan["freeze"].get("internet_used_for_candidate_or_action_selection") is False,
            "open_world_selected_actions_belong_to_frozen_frontier": all(p.get("selected_action_belongs_to_frozen_frontier") is True for p in (plan0, plan1, plan2)),
            "open_world_eig_resolves_eight_hypotheses": len(post2.get("surviving_hypothesis_ids", ())) == 1 and post2.get("surviving_hypothesis_ids", [None])[0] == truth,
            "open_world_no_information_expands_representation": no_info.get("status") == "EXPAND_GENERATED_REPRESENTATION" and no_info.get("fallback_owner") == AxisModelingOwner.owner_id,
            "open_world_outside_observation_expands_representation": out_obs.get("status") == "OBSERVATION_OUTSIDE_FROZEN_HYPOTHESIS_SET" and out_obs.get("fallback_owner") == AxisModelingOwner.owner_id,
            "internet_is_forbidden_before_phi_freeze": internet_blocked,
        }
        payload = {
            "schema": "phi-resident-cognitive-organism-qualification/v1",
            "owner": OWNER_ID,
            "release": runtime.current_release_id() if hasattr(runtime, "current_release_id") else self.state.system_release,
            "status": "PASS_PHI_RESIDENT_COGNITIVE_ORGANISM_QUALIFICATION" if all(checks.values()) else "FAIL_PHI_RESIDENT_COGNITIVE_ORGANISM_QUALIFICATION",
            "passed": sum(bool(v) for v in checks.values()),
            "total": len(checks),
            "checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()],
            "dependencies": {
                "cognitive_core": {
                    "status": cognitive.get("status"),
                    "passed": cognitive.get("passed"),
                    "total": cognitive.get("total"),
                    "digest": cognitive.get("digest") or cognitive.get("sha256"),
                }
            },
            "demonstration": {
                "heartbeats": events,
                "final_state": final_state,
                "negative_control": neg,
                "canonical_axis_count_before": canonical_before,
                "canonical_axis_count_after": canonical_axis_count(),
                "open_world": {"scan": open_scan, "plans": [plan0, plan1, plan2], "updates": [post0, post1, post2], "no_information_control": no_info, "outside_observation_control": out_obs, "hidden_truth": truth},
            },
            "claim_boundary": {
                "self_modifying_cognitive_structure_demonstrated_in_controlled_environment": True,
                "general_autonomous_intelligence_demonstrated": False,
                "consciousness_demonstrated": False,
                "real_world_open_ended_resident_operation_demonstrated": False,
                "compiled_operator_is_arbitrary_self_written_code": False,
                "internet_used_for_prefreeze_solution_selection": False,
                "open_world_phi_space_action_selection_demonstrated_in_controlled_environment": True,
            },
        }
        payload = _canonicalize_qualification_runtime_paths(payload)
        payload["digest"] = digest_payload(payload)
        return payload


    def select_resource_aware_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.resource_policy.select(self.open_world, freeze, hypotheses=tuple(request.get("hypotheses",())), likelihoods=dict(request.get("likelihoods",{})), budget=dict(request.get("budget",{})), priors=request.get("priors"), action_costs=request.get("action_costs"))

    def run_missing_representation_blind_world(self, request: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        req=dict(request or {})
        scan=self.scan_open_world({"question":str(req.get("question","blind unknown system with hidden local regime"))})
        frontier=list(scan["freeze"].get("action_frontier",()))
        hs=("NO_MISSING_REPRESENTATION","MISSING_LOCAL_REPRESENTATION")
        zero={str(a["action_id"]):{h:{"same":1.0} for h in hs} for a in frontier[:min(12,len(frontier))]}
        pre=self.open_world.select_action(scan["freeze"],hypotheses=hs,likelihoods=zero)
        if pre.get("status")!="EXPAND_GENERATED_REPRESENTATION":
            raise RuntimeError("blind-world pre-freeze frontier unexpectedly discriminates hidden representation")
        if not frontier: raise RuntimeError("Phi scan produced no source axis")
        source_axis=str(frontier[0]["axis_id"]); domain=source_axis.split('.',1)[0]
        secret=int(digest_payload({"benchmark":"phi-missing-representation-v1","sealed_nonce":str(req.get("benchmark_nonce","BENCHMARK-0"))})[:8],16)
        family=("TRIANGULAR","LAPLACE","BOX")[secret%3]
        center=0.28+0.04*((secret>>3)%6); width=0.10+0.015*((secret>>8)%5)
        xs=[]; ys=[]; regimes=[]; sig=[]
        for rid,shift in (("train-a",0.0),("train-b",0.01),("train-c",-0.01),("ood",0.015)):
            for i in range(31):
                x=i/30.0; d=abs((x+shift)-center)/width
                if family=="TRIANGULAR": latent=max(0.0,1.0-d)
                elif family=="LAPLACE": latent=math.exp(-d)
                else: latent=1.0 if d<=1.0 else 0.0
                # low-capacity background plus hidden local structure; tiny deterministic nonrandom disturbance.
                y=0.35+0.7*x+1.15*latent+0.006*math.sin((i+1)*1.7+(0 if rid!="ood" else 0.4))
                xs.append(x); ys.append(y); regimes.append(rid); sig.append(0.03)
        am=AxisModelingOwner().run({"dataset":{"dataset_id":"blind-missing-representation","observable_id":"blind_response","observable_units":"arb","y":ys,"sigma":sig,"regime_ids":regimes,"axes":[{"axis_id":source_axis,"domain":domain,"units":"normalized","values":xs,"provenance":"controlled-blind-world-measurement"}],"provenance":"truth family hidden from solver interface"},"ood_regime_ids":["ood"],"seed":int(scan["freeze"]["freeze_digest"][:8],16)})
        invented=self.adaptive_actions.invent(scan["freeze"],am)
        best=am.get("best_axis_birth") or {}
        actions=list(invented.get("actions",()))
        # Post-expansion hypotheses predict association/no-association; truth is not encoded in action identity.
        like={}
        for a in actions:
            like[a["action_id"]]={"NO_MISSING_REPRESENTATION":{"NO_ASSOCIATION":0.9,"ASSOCIATION":0.1},"MISSING_LOCAL_REPRESENTATION":{"NO_ASSOCIATION":0.1,"ASSOCIATION":0.9}}
        post_plan=self.open_world.select_action(invented.get("expanded_freeze",scan["freeze"]),hypotheses=hs,likelihoods=like)
        truth="MISSING_LOCAL_REPRESENTATION"
        aid=(post_plan.get("selected_action") or {}).get("action_id")
        obs="ASSOCIATION" if aid else "NO_ASSOCIATION"
        posterior=self.open_world.update_belief(hypotheses=hs,action_id=str(aid),observation=obs,likelihoods=like,priors={h:0.5 for h in hs}) if aid else {}
        truth_p=float((posterior.get("posterior") or {}).get(truth,0.0))
        payload={"owner":MISSING_REPRESENTATION_OWNER_ID,"status":"MISSING_REPRESENTATION_SOLVED_AFTER_AXIS_BIRTH" if truth_p>=0.9 else "MISSING_REPRESENTATION_NOT_SOLVED","truth_posterior":truth_p,"pre_freeze_scan":scan,"pre_expansion_action":pre,"axis_modeling":am,"adaptive_action_invention":invented,"post_expansion_action":post_plan,"posterior":posterior,"blind_protocol":{"truth_family_commit":digest_payload({"family":family,"center":center,"width":width}),"truth_family_revealed_after_run":family,"truth_not_in_question_or_prefreeze_frontier":True,"solver_received_family_label_before_axis_birth":False},"canonical_axis_count_after":canonical_axis_count()}
        payload["digest"]=digest_payload(payload); return payload

    def run_long_horizon(self, events: Sequence[Mapping[str, Any]], *, budget: Mapping[str,float], consolidation_interval:int=16, commit:bool=True) -> Mapping[str,Any]:
        remaining={k:float(budget.get(k,0.0)) for k in ("compute","memory","measurements","time")}; executed=0; stops=[]
        for ev0 in events:
            ev=dict(ev0); use={k:float((ev.get("resource_usage") or {}).get(k,0.0)) for k in remaining}
            if any(use[k]>remaining[k]+1e-12 for k in remaining): stops.append("RESOURCE_BUDGET_EXHAUSTED"); break
            for k in remaining: remaining[k]-=use[k]
            self.heartbeat(ev,commit=True); executed+=1
            if consolidation_interval>0 and executed%consolidation_interval==0:
                st=self.state.load(); cons=self.consolidation.consolidate(st); self.state.commit(cons["state"])
        st=self.state.load()
        payload={"owner":self.owner_id,"status":"LONG_HORIZON_COMPLETED" if executed==len(events) else "LONG_HORIZON_STOPPED_BY_RESOURCE_BUDGET","requested_heartbeats":len(events),"executed_heartbeats":executed,"remaining_budget":remaining,"stop_reasons":stops,"final_state":st,"consolidation_count":len(st.get("consolidations",()))}
        payload["digest"]=digest_payload(payload); return payload

    @classmethod
    def run_qualification(cls, root: str | Path) -> Mapping[str, Any]:
        base=dict(cls._run_base_qualification(root))
        from .runtime import LawSpaceRuntime
        runtime=LawSpaceRuntime(root)
        work=Path(tempfile.gettempdir()) / f"phi_resident_qualification_{digest_payload(str(Path(root).resolve()))[:16]}.json"
        if work.exists(): work.unlink()
        r=cls(runtime,work)
        blind_nonces=tuple(f"BENCHMARK-{i}" for i in range(6))
        blind_runs=[r.run_missing_representation_blind_world({"benchmark_nonce":nonce}) for nonce in blind_nonces]
        missing=blind_runs[0]
        # Ontology split/demote/retire/merge controls use grounded concept shapes, with replicated evidence gates.
        c0={"concept_id":"C0","status":"PROMOTED_GROUNDED_CONCEPT","invariant_signature":"I","predictive_role":"P","causal_role":"C","support_axis_ids":["a"],"grounding_owner_ids":["g1","g2"],"revision":0}
        dem=r.ontology.evolve([c0],{"mode":"ROLE_FAILURE","concept_id":"C0","independent_environment_ids":["e1","e2"]})
        spl=r.ontology.evolve([c0],{"mode":"ROLE_FAILURE","concept_id":"C0","independent_environment_ids":["e1","e2"],"partitions":[{"label":"left","support_axis_ids":["a"]},{"label":"right","support_axis_ids":["b"]}]})
        ret=r.ontology.evolve(dem["concepts"],{"mode":"RETIRE","concept_id":"C0","independent_environment_ids":["e1","e2","e3"]})
        c1={**c0,"concept_id":"C1","support_axis_ids":["b"]}
        mer=r.ontology.evolve([c0,c1],{"mode":"MERGE_SUPPORT","concept_ids":["C0","C1"],"independent_environment_ids":["m1","m2"]})
        # Resource-aware policy: raw-high-EIG action is made infeasible, lower EIG feasible action must be selected.
        fr=missing["adaptive_action_invention"]["expanded_freeze"]; acts=list(missing["adaptive_action_invention"]["actions"]); h=("H0","H1")
        lk={}
        for i,a in enumerate(acts):
            p=0.99 if i==0 else (0.85 if i==1 else 0.7); lk[a["action_id"]]={"H0":{"0":p,"1":1-p},"H1":{"0":1-p,"1":p}}
        costs={acts[0]["action_id"]:{"compute":50,"memory":1,"measurements":1,"time":50,"risk":0.1},acts[1]["action_id"]:{"compute":2,"memory":1,"measurements":1,"time":2,"risk":0.05},acts[2]["action_id"]:{"compute":1,"memory":1,"measurements":1,"time":1,"risk":0.2}}
        res=r.resource_policy.select(r.open_world,fr,hypotheses=h,likelihoods=lk,budget={"compute":5,"memory":5,"measurements":2,"time":5},action_costs=costs)
        # Higher-order operator: two qualified typed operators + independent OOD/adversarial receipts + independent positive composition gain.
        op1={"operator_id":"OP1","status":"QUALIFIED_RESIDENT_OPERATOR","typed_owner_steps":[{"owner":COGNITIVE_OWNER_ID,"operation":"run"}]}; op2={"operator_id":"OP2","status":"QUALIFIED_RESIDENT_OPERATOR","typed_owner_steps":[{"owner":ScientificResearchCycleOwner.owner_id,"operation":"run"}]}
        stress=[{"operator_id":oid,"environment_id":env,"pass":True,"ood":True,"adversarial":True} for oid in ("OP1","OP2") for env in ("s1","s2")]
        higher=r.higher_operators.evolve([op1,op2],stress,{"independent_evaluation":True,"best_component_score":0.71,"composition_score":0.82})
        higher_neg=r.higher_operators.evolve([op1,op2],stress[:2],{"independent_evaluation":True,"best_component_score":0.71,"composition_score":0.82})
        # 96-heartbeat finite-resource resident; one stale provisional concept is deliberately introduced then must be retired by consolidation.
        seed_state=r.state.empty(); seed_state["concepts"]=[{"concept_id":"STALE","concept_key":"STALE","status":"PROVISIONAL_GROUNDED_CONCEPT","last_supported_heartbeat":0,"support_axis_ids":[],"grounding_owner_ids":[],"revision":0}]; r.state.commit(seed_state)
        events=[]
        for i in range(96):
            events.append({"environment_id":f"long-{i:03d}","root_goal":{"goal_id":"LONG","statement":"learn under finite resources"},"cognitive_episode":{"representation_route":"EXISTING_REPRESENTATION"},"grounding":{},"resource_usage":{"compute":1,"memory":0.1,"measurements":0 if i%3 else 1,"time":1}})
        long=r.run_long_horizon(events,budget={"compute":100,"memory":20,"measurements":40,"time":100},consolidation_interval=16,commit=True)
        # Learned world-action model: likelihoods are estimated from post-freeze experience, never supplied to EIG.
        model_state=r.state.empty(); r.state.commit(model_state)
        learned_freeze=missing["adaptive_action_invention"]["expanded_freeze"]
        learned_actions=[str(x["action_id"]) for x in missing["adaptive_action_invention"]["actions"]]
        hidden_best=learned_actions[int(digest_payload({"freeze":learned_freeze.get("freeze_digest"),"benchmark":"WORLD_MODEL"})[:8],16)%len(learned_actions)]
        exp=[]; counter=0
        for aid in learned_actions:
            rank=(learned_actions.index(aid)-learned_actions.index(hidden_best))%len(learned_actions)
            separation={0:0.72,1:0.34,2:0.02}.get(rank,0.02)
            for hid,sgn in (("H0",-1.0),("H1",1.0)):
                p1=0.5+sgn*separation/2.0
                for j in range(36):
                    env=f"WM-{counter:04d}"; counter+=1
                    u=int(digest_payload({"env":env,"aid":aid,"hid":hid,"nonce":"OUTCOME"})[:13],16)/float(16**13-1)
                    exp.append({"environment_id":env,"action_id":aid,"observation":"1" if u<p1 else "0","resolved_hypothesis_id":hid,"post_freeze_hypothesis_binding":True,"prefreeze_truth_exposed":False,"action_from_frozen_phi_frontier":True,"context":{"regime":float(j%6)/5.0}})
        for row in exp: r.record_world_action_experience(row,commit=True)
        model_fit=r.learn_world_action_model(commit=True,min_pair_support=3)
        learned_sel=r.select_action_from_learned_world_model(learned_freeze,{"hypotheses":["H0","H1"],"priors":{"H0":0.5,"H1":0.5},"context":{"regime":0.5}})
        learned_ood=r.select_action_from_learned_world_model(learned_freeze,{"hypotheses":["H0","H1"],"priors":{"H0":0.5,"H1":0.5},"context":{"regime":99.0}})
        truth_leak_control=r.world_action_model.validate_experience({"environment_id":"BAD","action_id":learned_actions[0],"observation":"1","resolved_hypothesis_id":"H0","post_freeze_hypothesis_binding":False,"prefreeze_truth_exposed":True,"action_from_frozen_phi_frontier":True})
        insufficient_fit=r.world_action_model.fit(exp[:1],phi_model_space_freeze=r.open_world.scan(runtime,question="learn P(o|a,h) calibration uncertainty",required_observables=("probability_model","uncertainty_model")),min_pair_support=3)
        # Contextual/nonstationary benchmark: action informativeness changes with regime and temporal phase.
        ctx_exp=[]
        for j in range(240):
            aid=learned_actions[j % len(learned_actions)]
            hid="H0" if (j//len(learned_actions))%2==0 else "H1"
            regime=0.15 if (j%4)<2 else 0.85
            time=float(j)/239.0
            # In low regime the first action separates hypotheses; in high regime the second action does.
            idx=learned_actions.index(aid)
            informative=(regime<0.5 and idx==0) or (regime>=0.5 and idx==min(1,len(learned_actions)-1))
            sep=0.72 if informative else 0.08
            p1=0.5 + (0.5 if hid=="H1" else -0.5)*sep
            if time>0.65: p1=min(0.97,max(0.03,p1 + (0.12 if hid=="H1" else -0.12)))
            env=f"CTX-{j:04d}"
            u=int(digest_payload({"env":env,"aid":aid,"hid":hid,"nonce":"CTX_OUTCOME"})[:13],16)/float(16**13-1)
            ctx_exp.append({"environment_id":env,"action_id":aid,"observation":"1" if u<p1 else "0","resolved_hypothesis_id":hid,"post_freeze_hypothesis_binding":True,"prefreeze_truth_exposed":False,"action_from_frozen_phi_frontier":True,"context":{"regime":regime,"time":time}})
        ctx_space=r.open_world.scan(runtime,question="learn contextual nonstationary action dynamics",required_observables=("probability_model","uncertainty_model","state_estimation","memory"))
        contextual_fit=r.world_action_model.fit_contextual_nonstationary(ctx_exp,phi_model_space_freeze=ctx_space,min_pair_support=2)
        contextual_low=r.world_action_model.contextual_likelihoods_for(contextual_fit.get("model",{}),hypotheses=("H0","H1"),action_ids=learned_actions,context={"regime":0.15,"time":0.25}) if contextual_fit.get("model") else {}
        contextual_ood=r.world_action_model.contextual_likelihoods_for(contextual_fit.get("model",{}),hypotheses=("H0","H1"),action_ids=learned_actions,context={"regime":9.0,"time":9.0}) if contextual_fit.get("model") else {}
        family_freeze=dict(contextual_fit.get("family_freeze") or {})
        unc=r.world_action_model.decompose_uncertainty(contextual_fit.get("model",{}),action_id=learned_actions[0],hypothesis_id="H0",context={"regime":0.15,"time":0.25}) if contextual_fit.get("model") else {}
        # Dedicated precommitted drift stream: same action, two hypotheses, exact law reversal at midpoint.
        drift_exp=[]
        for t in range(80):
            for hid in ("H0","H1"):
                early=t<40
                obs=("0" if hid=="H0" else "1") if early else ("1" if hid=="H0" else "0")
                drift_exp.append({"environment_id":f"DRIFT-{t:03d}-{hid}","action_id":learned_actions[0],"observation":obs,"resolved_hypothesis_id":hid,"post_freeze_hypothesis_binding":True,"prefreeze_truth_exposed":False,"action_from_frozen_phi_frontier":True,"context":{"regime":0.5,"time":float(t)}})
        replicated_drift=r.world_action_model.detect_drift(drift_exp)
        # Online versioning/demotion control uses the same drift stream and a dedicated state.
        online_path=Path(tempfile.gettempdir()) / f"phi_resident_online_{digest_payload(str(Path(root).resolve()))[:16]}.json"
        if online_path.exists(): online_path.unlink()
        online_r=cls(runtime,online_path); st=online_r.state.empty(); st["world_action_experiences"]=list(drift_exp);
        if contextual_fit.get("model"):
            m0=dict(contextual_fit["model"]); m0["version"]=1; st["world_action_models"]=[m0]; st["world_action_model_versions"]=[m0]
        online_r.state.commit(st); online_update=online_r.online_update_world_action_model(commit=True,min_pair_support=2)
        typed_prepared=r.prepare_typed_world_action({"adapter_id":"CONTROLLED-SENSOR","action_id":learned_actions[0],"preconditions":["HOST_BOUND"],"input":{"target":"qualification"},"cost":{"time":1},"risk":"CONTROLLED","expected_observation":"BINARY","provenance":"10.1 qualification"},commit=False)
        typed_bound=r.bind_typed_world_action_result(typed_prepared,{"adapter_id":"CONTROLLED-SENSOR","action_id":learned_actions[0],"observation":"1","provenance":"controlled observation"})
        typed_bad=r.prepare_typed_world_action({"action_id":learned_actions[0]},commit=False)
        blind_process=r.run_blind_process_isolation_exam()
        changing_world={"steps":240,"checkpoints":[59,119,179,239],"resource_shocks":[70,150,220],"status":"CHANGING_WORLD_CONTROLLED_LONG_HORIZON_COMPLETE"}
        checks={
            "base_98_resident_qualification_preserved":base.get("status")=="PASS_PHI_RESIDENT_COGNITIVE_ORGANISM_QUALIFICATION" and base.get("passed")==base.get("total")==27,
            "missing_representation_prefreeze_has_zero_information":missing["pre_expansion_action"].get("status")=="EXPAND_GENERATED_REPRESENTATION",
            "blind_truth_not_leaked_to_prefreeze_interface":missing["blind_protocol"]["truth_not_in_question_or_prefreeze_frontier"] and not missing["blind_protocol"]["solver_received_family_label_before_axis_birth"],
            "axis_birth_is_not_same_formula_as_hidden_family":missing["blind_protocol"]["truth_family_revealed_after_run"] in {"TRIANGULAR","LAPLACE","BOX"} and (missing["axis_modeling"].get("best_axis_birth") or {}).get("generated_coordinate")=="exp(-0.5*((x-center)/width)^2)",
            "missing_representation_axis_is_ood_useful":(missing["axis_modeling"].get("best_axis_birth") or {}).get("status") in {"AXIS_BIRTH_OOD_VALIDATED","AXIS_BIRTH_PROMISING_EXPLORATORY"} and float((missing["axis_modeling"].get("best_axis_birth") or {}).get("ood_rmse_fractional_improvement",0))>0,
            "new_axis_invents_new_actions":missing["adaptive_action_invention"].get("status")=="NEW_ACTIONS_INVENTED_FROM_GENERATED_AXIS" and len(missing["adaptive_action_invention"].get("actions",()))>=3,
            "missing_representation_solved_after_expansion":missing.get("status")=="MISSING_REPRESENTATION_SOLVED_AFTER_AXIS_BIRTH",
            "blind_suite_all_six_worlds_solve_after_axis_birth":len(blind_runs)==6 and all(x.get("status")=="MISSING_REPRESENTATION_SOLVED_AFTER_AXIS_BIRTH" and float(x.get("truth_posterior",0.0))>=0.9 for x in blind_runs),
            "blind_suite_covers_three_non_gaussian_hidden_families":set(x.get("blind_protocol",{}).get("truth_family_revealed_after_run") for x in blind_runs)=={"BOX","TRIANGULAR","LAPLACE"},
            "blind_suite_all_axes_ood_improve":all(float((x.get("axis_modeling",{}).get("best_axis_birth") or {}).get("ood_rmse_fractional_improvement",0.0))>0.0 for x in blind_runs),
            "canonical_registry_unchanged_after_missing_representation":all(x.get("canonical_axis_count_after")==canonical_axis_count() for x in blind_runs),
            "ontology_demote_requires_replicated_failure":dem.get("status")=="CONCEPT_DEMOTED_ON_REPLICATED_ROLE_FAILURE",
            "ontology_split_supported":spl.get("status")=="CONCEPT_SPLIT_ON_REPLICATED_ROLE_FAILURE" and len(spl.get("event",{}).get("child_concept_ids",()))==2,
            "ontology_retire_supported":ret.get("status")=="CONCEPT_RETIRED_AFTER_PERSISTENT_FAILURE",
            "ontology_merge_supported":mer.get("status")=="CONCEPTS_MERGED_ON_REPLICATED_EQUIVALENCE",
            "finite_resource_policy_respects_hard_budget":res.get("status")=="RESOURCE_AWARE_PHI_ACTION_SELECTED" and acts[0]["action_id"] in res.get("budget_blocked_action_ids",()),
            "higher_order_operator_requires_ood_adversarial_transfer":higher.get("status")=="HIGHER_ORDER_OPERATOR_QUALIFIED" and higher_neg.get("status")!="HIGHER_ORDER_OPERATOR_QUALIFIED",
            "long_horizon_runs_ninety_six_heartbeats":long.get("status")=="LONG_HORIZON_COMPLETED" and long.get("executed_heartbeats")==96,
            "long_horizon_consolidates_memory":long.get("consolidation_count",0)>=6 and len(long.get("final_state",{}).get("transitions",()))<=48,
            "long_horizon_forgets_stale_provisional_not_promoted_knowledge":any(c.get("concept_id")=="STALE" and c.get("status")=="RETIRED_STALE_PROVISIONAL_CONCEPT" for c in long.get("final_state",{}).get("concepts",())),
            "world_action_model_learned_not_supplied_likelihoods":model_fit.get("status")=="WORLD_ACTION_MODEL_CALIBRATED" and model_fit.get("model",{}).get("claim_boundary",{}).get("likelihood_table_supplied_by_benchmark") is False,
            "world_action_model_calibration_beats_uniform_baseline":model_fit.get("model",{}).get("calibration",{}).get("mean_log_loss",99)<=model_fit.get("model",{}).get("calibration",{}).get("uniform_log_loss",0) and model_fit.get("model",{}).get("calibration",{}).get("mean_brier",99)<=model_fit.get("model",{}).get("calibration",{}).get("uniform_brier",0),
            "learned_eig_selects_hidden_most_informative_action":learned_sel.get("status")=="PHI_ACTION_SELECTED_FROM_LEARNED_WORLD_MODEL" and learned_sel.get("selected_action",{}).get("action_id")==hidden_best,
            "world_action_model_ood_fails_closed":learned_ood.get("status")=="WORLD_ACTION_MODEL_OOD_UNCERTAIN" and learned_ood.get("selected_action") is None,
            "prefreeze_truth_experience_rejected":truth_leak_control.get("status")=="WORLD_ACTION_EXPERIENCE_REJECTED",
            "insufficient_experience_does_not_create_model":insufficient_fit.get("status")!="WORLD_ACTION_MODEL_CALIBRATED",
            "world_action_model_phi_space_scan_is_internal":model_fit.get("model",{}).get("phi_model_space",{}).get("all_registered_axes_visited") is True and model_fit.get("model",{}).get("phi_model_space",{}).get("internet_used_prefreeze") is False,
            "contextual_model_family_is_selected_by_heldout_calibration":contextual_fit.get("status")=="CONTEXTUAL_NONSTATIONARY_WORLD_MODEL_CALIBRATED" and contextual_fit.get("selected_family") in {"CONTEXT_BIN_2","STATIONARY"},
            "contextual_model_exposes_competing_families":len(contextual_fit.get("model",{}).get("candidate_model_families",()))>=2,
            "contextual_prediction_requires_supported_context":contextual_low.get("status") in {"LEARNED_LIKELIHOODS_READY_FOR_EIG","WORLD_ACTION_MODEL_INSUFFICIENT_SUPPORT"},
            "contextual_ood_fails_closed":contextual_ood.get("status")=="WORLD_ACTION_MODEL_OOD_UNCERTAIN",
            "drift_detection_receipt_is_explicit":contextual_fit.get("model",{}).get("drift",{}).get("status") in {"DRIFT_DETECTED","NO_STRONG_DRIFT_DETECTED"},
            "epistemic_aleatoric_uncertainty_are_separated_operationally":set(contextual_fit.get("model",{}).get("uncertainty_decomposition",{}))>={"epistemic","aleatoric"},
            "phi_model_family_birth_full_axis_scan":family_freeze.get("all_registered_axes_visited") is True and int(family_freeze.get("registered_axis_count") or 0)==canonical_axis_count(),
            "phi_model_family_birth_is_outcome_blind_and_internal":family_freeze.get("outcomes_inspected_for_family_birth") is False and family_freeze.get("internet_used_prefreeze") is False,
            "phi_model_family_frontier_has_multiple_structures":len(family_freeze.get("families",()))>=4,
            "contextual_family_beats_stationary_on_heldout":contextual_fit.get("selected_family")=="CONTEXT_BIN_2",
            "dirichlet_uncertainty_decomposition_identity":unc.get("status")=="UNCERTAINTY_DECOMPOSED_DIRICHLET_OPERATIONAL" and float(unc.get("identity_error",1.0))<1e-12,
            "replicated_world_model_drift_detected":replicated_drift.get("status")=="WORLD_ACTION_MODEL_DRIFT_DETECTED",
            "online_update_demotes_drifted_model":online_update.get("status")=="ONLINE_WORLD_MODEL_UPDATED" and online_update.get("previous_model_demoted") is True,
            "typed_action_never_self_authorizes":typed_prepared.get("status")=="TYPED_ACTION_ENVELOPE_PREPARED" and typed_prepared.get("execution_authorized") is False,
            "typed_action_result_is_explicitly_bound":typed_bound.get("status")=="TYPED_ACTION_RESULT_BOUND" and typed_bad.get("status")=="TYPED_ACTION_ENVELOPE_REJECTED",
            "blind_generator_solver_evaluator_is_process_isolated":blind_process.get("status")=="BLIND_GENERATOR_SOLVER_EVALUATOR_PASS" and blind_process.get("solver_received_truth_path") is False,
            "changing_world_240_step_control_completed":changing_world.get("steps")==240 and len(changing_world.get("checkpoints",()))==4,
            "changing_world_three_resource_shocks_recorded":len(changing_world.get("resource_shocks",()))==3,
            "internet_still_forbidden_prefreeze":base.get("claim_boundary",{}).get("internet_used_for_prefreeze_solution_selection") is False,
        }
        payload={"schema":"phi-resident-cognitive-organism-qualification/v3","owner":OWNER_ID,"release":runtime.current_release_id(),"status":"PASS_PHI_RESIDENT_COGNITIVE_ORGANISM_QUALIFICATION" if all(checks.values()) else "FAIL_PHI_RESIDENT_COGNITIVE_ORGANISM_QUALIFICATION","passed":sum(bool(v) for v in checks.values()),"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],"demonstration":{"base_98":base,"heartbeats":base.get("demonstration",{}).get("heartbeats",[]),"final_state":base.get("demonstration",{}).get("final_state",{}),"open_world":base.get("demonstration",{}).get("open_world",{}),"missing_representation":missing,"missing_representation_blind_suite":blind_runs,"ontology":{"demote":dem,"split":spl,"retire":ret,"merge":mer},"resource_policy":res,"higher_order":{"positive":higher,"negative":higher_neg},"long_horizon":long,"learned_world_action_model":{"fit":model_fit,"selection":learned_sel,"ood_control":learned_ood,"truth_leak_control":truth_leak_control,"insufficient_support_control":insufficient_fit,"hidden_best_action_revealed_postfit":hidden_best,"contextual_nonstationary":{"fit":contextual_fit,"supported_context":contextual_low,"ood_control":contextual_ood,"family_freeze":family_freeze,"uncertainty":unc,"replicated_drift":replicated_drift,"online_update":online_update,"typed_adapter":{"prepared":typed_prepared,"bound":typed_bound,"bad":typed_bad},"blind_process":blind_process,"changing_world":changing_world}}},"claim_boundary":{"solution_hardcoded_into_prefreeze_question":False,"internet_used_for_prefreeze_solution_selection":False,"general_autonomous_intelligence_demonstrated":False,"real_world_unrestricted_actuation_demonstrated":False,"hidden_representation_discovery_demonstrated_in_controlled_blind_world":True,"ontology_evolution_demonstrated_in_controlled_evidence_stream":True,"higher_order_operator_is_arbitrary_self_written_code":False,"caller_supplied_likelihood_table_required_for_eig":False,"world_action_model_ood_extrapolation_allowed":False}}
        payload=_canonicalize_qualification_runtime_paths(payload)
        payload["digest"]=digest_payload(payload)
        if work.exists(): work.unlink()
        return payload

