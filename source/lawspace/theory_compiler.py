"""Φ-Theory Compiler — typed executable theory synthesis.

The compiler is domain-neutral.  It never evaluates generated source code and it
never selects a named scientific solver.  Frozen mathematical evidence may lower
to one of two executable forms:

* an exact finite transition algebra;
* a typed continuous operator program built from a small safe operator grammar.

The continuous path is learned from black-box operator-response probes.  The
synthesis owner searches sparse combinations of identity, first/second spatial
derivatives, coordinate powers and cross-component blocks, freezes the selected
program, and exposes it to the same compiler/runtime/falsification boundary as any
other Atlas candidate.  Compilation proves executability only; it does not prove
that the candidate is a law of the world.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence
from itertools import combinations
import math

import numpy as np
from scipy import linalg
from scipy.special import eval_genlaguerre

from .schema import digest_payload

KERNEL_OWNER_ID = "PHI-THEORY-COMPILER/2.1.0"
SYNTHESIS_OWNER_ID = "EXECUTABLE-REPRESENTATION-SYNTHESIS/2.0.0"
LOWERING_OWNER_ID = "THEORY-TO-EXECUTABLE-COMPILER/2.0.0"
EXECUTOR_OWNER_ID = "EXECUTABLE-THEORY-RUNTIME/2.0.0"
ERROR_OWNER_ID = "THEORY-ERROR-ESTIMATOR/2.0.0"
PROBE_DESIGN_OWNER_ID = "OPERATOR-PROBE-DESIGN/2.1.0"
PRIMITIVE_FIELD_OPERATOR_BIRTH_OWNER_ID = "PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH/1.1.0"
ATOMIC_WORLD_INTERACTION_OWNER_ID = "ATOMIC-REFERENCE-WORLD-INTERACTION/1.0.0"
VARIABLE_PARTICLE_PROBE_DESIGN_OWNER_ID = "VARIABLE-PARTICLE-PROBE-DESIGN/1.0.0"
VARIABLE_PARTICLE_WORLD_INTERACTION_OWNER_ID = "ATOMIC-VARIABLE-PARTICLE-REFERENCE-WORLD/1.0.0"
SELF_CONSISTENT_SYNTHESIS_OWNER_ID = "SELF-CONSISTENT-REPRESENTATION-SYNTHESIS/1.0.0"
MANY_BODY_PROBE_DESIGN_OWNER_ID = "MANY-BODY-OPERATOR-PROBE-DESIGN/1.0.0"
ATOMIC_MANY_BODY_WORLD_OWNER_ID = "ATOMIC-MANY-BODY-REFERENCE-WORLD/1.0.0"
MANY_BODY_SYNTHESIS_OWNER_ID = "MANY-BODY-OPERATOR-COORDINATE-SYNTHESIS/1.0.0"
SCHEMA = "phi-theory-executable-ir/v2"


def _digest(payload: Mapping[str, Any]) -> str:
    return digest_payload(dict(payload))


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = _digest(payload)
    return payload


def _uniform_grid_matrices(grid: Sequence[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(grid, dtype=float)
    if x.ndim != 1 or len(x) < 5 or not np.all(np.isfinite(x)):
        raise ValueError("operator grid must contain at least five finite points")
    dx = np.diff(x)
    h = float(np.mean(dx))
    if h <= 0 or not np.allclose(dx, h, rtol=1e-8, atol=max(1e-12, abs(h) * 1e-10)):
        raise ValueError("current executable operator grammar requires a strictly increasing uniform 1D grid")
    n = len(x)
    d1 = np.zeros((n, n), dtype=float)
    d2 = np.zeros((n, n), dtype=float)
    for i in range(n):
        if i > 0:
            d1[i, i - 1] = -0.5 / h
            d2[i, i - 1] = 1.0 / (h * h)
        if i + 1 < n:
            d1[i, i + 1] = 0.5 / h
            d2[i, i + 1] = 1.0 / (h * h)
        d2[i, i] = -2.0 / (h * h)
    return x, d1, d2


def _basis_matrix(kind: str, x: np.ndarray, d1: np.ndarray, d2: np.ndarray, power: int = 0) -> np.ndarray:
    if kind == "IDENTITY":
        return np.eye(len(x), dtype=float)
    if kind == "FIRST_DERIVATIVE":
        return d1
    if kind == "SECOND_DERIVATIVE":
        return d2
    if kind == "COORDINATE_POWER":
        if power < 0 and np.any(np.abs(x) < 1e-14):
            raise ValueError("negative coordinate powers are undefined on a grid containing zero")
        return np.diag(np.power(x, int(power), dtype=float))
    raise ValueError(f"unsupported typed operator basis {kind!r}")


def _flatten_components(state: Sequence[Sequence[float]], components: int, points: int) -> np.ndarray:
    arr = np.asarray(state, dtype=float)
    if arr.shape != (components, points) or not np.all(np.isfinite(arr)):
        raise ValueError(f"state/response must have shape ({components}, {points}) with finite values")
    return arr


class OperatorProbeDesignOwner:
    """Birth a frozen, law-agnostic continuous operator-probe protocol.

    This owner generates only input states.  It never generates or guesses the
    corresponding operator responses.  The design is optimized against the safe
    executable operator grammar so that an eventual attested response provider
    can discriminate basis terms without exposing a named scientific law.
    """

    owner_id = PROBE_DESIGN_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "REPRESENTATION_GAP_PLUS_OPTIONAL_TYPED_CARRIER_CONSTRAINTS",
            "output": "FROZEN_OPERATOR_PROBE_INPUT_PROTOCOL_WITHOUT_RESPONSES",
            "design_objective": "MAXIMIZE_GENERIC_OPERATOR_GRAMMAR_IDENTIFIABILITY_BEFORE_RESPONSE_ACQUISITION",
            "known_law_name_required": False,
            "named_solver_selection": False,
            "response_generation_allowed": False,
            "assistant_is_response_provider": False,
            "internet_prefreeze": "FORBIDDEN",
            "fixed_global_probe_count_ceiling": None,
            "next_design_shell_exists": True,
        }

    @staticmethod
    def _score_matrix(matrix: np.ndarray) -> tuple[int, float]:
        if matrix.size == 0:
            return 0, 0.0
        norms = np.linalg.norm(matrix, axis=0)
        usable = norms > 1e-12
        if not np.any(usable):
            return 0, 0.0
        z = matrix[:, usable] / norms[usable]
        rank = int(np.linalg.matrix_rank(z, tol=1e-10))
        sv = np.linalg.svd(z, compute_uv=False)
        positive = sv[sv > 1e-12]
        min_sv = float(positive[-1]) if len(positive) else 0.0
        return rank, min_sv

    @staticmethod
    def _state_candidate(*, grid: np.ndarray, components: int, candidate_index: int, seed: int) -> np.ndarray:
        # Smooth boundary-compatible carrier probes.  Coefficients are seeded by
        # the frozen gap/design digest, not by any domain or named-law parameter.
        rng = np.random.default_rng((int(seed) + 104729 * (candidate_index + 1)) % (2**63 - 1))
        t = (grid - grid[0]) / max(float(grid[-1] - grid[0]), 1e-12)
        state = np.zeros((components, len(grid)), dtype=float)
        harmonic_count = max(4, min(12, len(grid) // 4))
        for c in range(components):
            coeff = rng.normal(size=harmonic_count)
            for m, a in enumerate(coeff, start=1):
                state[c] += float(a) * np.sin(m * np.pi * (t + 1.0 / (len(grid) + 1.0)))
            norm = float(np.linalg.norm(state[c]))
            if norm > 0:
                state[c] /= norm
        return state

    def design(
        self,
        *,
        freeze_digest: str,
        components: int = 1,
        grid: Sequence[float] | None = None,
        design_shell: int = 1,
    ) -> Mapping[str, Any]:
        if not freeze_digest:
            raise ValueError("operator probe design requires a frozen gap digest")
        components = max(1, int(components))
        design_shell = max(1, int(design_shell))
        specs = ExecutableRepresentationSynthesisOwner._term_specs(components)
        feature_count = len(specs)
        if grid is None:
            # Scale-free research-local coordinate chart.  This is not a physical
            # radial calibration; a measurement owner must bind it to a physical
            # coordinate before returning world responses.
            points = max(33, 4 * feature_count + 1)
            x = np.linspace(1.0 / (points + 1.0), points / (points + 1.0), points)
            chart_origin = "ATLAS_RESEARCH_LOCAL_NORMALIZED_COORDINATE"
        else:
            x, _, _ = _uniform_grid_matrices([float(v) for v in grid])
            points = len(x)
            chart_origin = "CALLER_OR_ATTESTED_TYPED_CARRIER_GRID"
        x, d1, d2 = _uniform_grid_matrices(x)
        seed = int(digest_payload({"freeze_digest": freeze_digest, "components": components, "design_shell": design_shell})[:16], 16)
        pool_size = max(24, (4 + 2 * design_shell) * feature_count)
        candidates: list[tuple[int, np.ndarray, np.ndarray]] = []
        for idx in range(pool_size):
            state = self._state_candidate(grid=x, components=components, candidate_index=idx, seed=seed)
            cols = [ExecutableRepresentationSynthesisOwner._feature_for_probe(spec, state, x, d1, d2) for spec in specs]
            candidates.append((idx, state, np.column_stack(cols)))

        selected: list[tuple[int, np.ndarray, np.ndarray]] = []
        stacked = np.empty((0, feature_count), dtype=float)
        target_rank = feature_count
        # Discovery count grows with the current grammar shell rather than being
        # a universal fixed truth gate.  Beyond that, selection stops as soon as
        # the current grammar is generically full-rank.
        min_discovery = max(3, int(math.ceil(feature_count / 3.0)))
        while candidates and (len(selected) < min_discovery or self._score_matrix(stacked)[0] < target_rank):
            ranked = []
            for row in candidates:
                trial = np.vstack([stacked, row[2]])
                rank, min_sv = self._score_matrix(trial)
                ranked.append((rank, min_sv, -row[0], row, trial))
            _, _, _, best, trial = max(ranked, key=lambda z: (z[0], z[1], z[2]))
            selected.append(best)
            stacked = trial
            candidates = [row for row in candidates if row[0] != best[0]]
        achieved_rank, min_sv = self._score_matrix(stacked)

        # Holdout probe inputs are frozen now, before any response exists.
        holdout_count = max(1, design_shell, int(math.ceil(min_discovery / 3.0)))
        holdouts = candidates[:holdout_count]
        blueprints = []
        for role, rows in (("DISCOVERY", selected), ("SEALED_HOLDOUT", holdouts)):
            for idx, state, _ in rows:
                core = {
                    "grid": x.tolist(),
                    "state": state.tolist(),
                    "role": role,
                    "coordinate_chart_origin": chart_origin,
                    "response": None,
                }
                blueprints.append({"probe_id": "P-" + digest_payload(core)[:16].upper(), **core})
        blueprint_digest = digest_payload(blueprints)
        qualified = achieved_rank >= target_rank and len(selected) >= min_discovery and bool(holdouts)
        payload = {
            "schema": "phi-operator-probe-design/v1",
            "owner_id": self.owner_id,
            "status": "OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES" if qualified else "OPERATOR_PROBE_DESIGN_CURRENT_SHELL_UNDERIDENTIFIED",
            "freeze_digest": freeze_digest,
            "design_shell": design_shell,
            "components": components,
            "grid_points": points,
            "candidate_grammar_term_count": feature_count,
            "design_certificate": {
                "target_feature_rank": target_rank,
                "achieved_feature_rank": achieved_rank,
                "normalized_min_singular_value": min_sv,
                "discovery_probe_count": len(selected),
                "sealed_holdout_probe_count": len(holdouts),
                "full_rank_for_current_grammar": achieved_rank >= target_rank,
                "holdout_inputs_frozen_before_responses": True,
            },
            "probe_blueprints": blueprints,
            "probe_blueprint_digest": blueprint_digest,
            "response_contract": {
                "required": "components x grid_points operator action for each frozen probe_id",
                "response_provider_must_be_attested": True,
                "response_provider_may_be_assistant": False,
                "response_values_present": False,
                "physical_coordinate_binding_required_if_chart_is_normalized": chart_origin == "ATLAS_RESEARCH_LOCAL_NORMALIZED_COORDINATE",
            },
            "next_design_shell_exists": True,
            "fixed_global_probe_count_ceiling": None,
            "claim_boundary": {
                "atlas_generated_probe_inputs": True,
                "atlas_generated_operator_responses": False,
                "probe_design_is_world_measurement": False,
                "known_law_used_for_probe_design": False,
                "named_solver_used_for_probe_design": False,
                "scientific_law_established": False,
            },
        }
        return _with_digest(payload)


class AtomicReferenceWorldInteractionOwner:
    """Execute frozen Atlas probes against an independent typed atomic reference world.

    This owner is intentionally separated from representation synthesis.  It may
    disclose carrier requirements and return numeric operator responses, but the
    synthesis owner receives only the frozen input/output rows and never receives
    the hidden reference-model coefficients or a named solver choice.

    The current reference world is a deterministic, established-physics
    *simulation benchmark*, not an empirical measurement and not evidence of a
    novel law.  It exists to close the world-interaction leg of the Atlas loop
    without reusing the answer-bearing ``atomic_frontier`` regression path.
    """

    owner_id = ATOMIC_WORLD_INTERACTION_OWNER_ID

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_RESPONSE_FREE_ATLAS_OPERATOR_PROBE_PROTOCOL",
            "output": "DIGEST_BOUND_TYPED_OPERATOR_RESPONSE_ROWS",
            "evidence_class": "TYPED_REFERENCE_SIMULATION_NOT_EMPIRICAL_WORLD",
            "carrier_feedback_allowed": True,
            "response_fabrication_by_assistant": False,
            "answer_bearing_regression_import": False,
            "named_solver_exposed_to_synthesis": False,
            "internet_required": False,
            "reference_world_is_scientific_novelty": False,
        }

    def _alpha_inverse(self) -> tuple[float, Mapping[str, Any]]:
        registry_path = self.root / "data" / "constants" / "registry.json"
        rows = __import__("json").loads(registry_path.read_text(encoding="utf-8"))
        for row in rows:
            if str(row.get("constant_id")) == "CONST-alpha-inv":
                value = float(row["value"])
                if not math.isfinite(value) or value <= 1.0:
                    raise ValueError("invalid alpha inverse in constants registry")
                return value, {
                    "constant_id": row.get("constant_id"),
                    "symbol": row.get("symbol"),
                    "value": row.get("value"),
                    "unit": row.get("unit"),
                    "source_id": row.get("source_id"),
                    "source_digest": row.get("source_digest"),
                    "row_digest": row.get("digest"),
                }
        raise ValueError("CONST-alpha-inv missing from constants registry")

    @staticmethod
    def _validate_protocol(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
        if protocol.get("status") != "OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            raise ValueError("world interaction requires a qualified frozen probe protocol")
        blueprints = [dict(x) for x in protocol.get("probe_blueprints", ())]
        if not blueprints:
            raise ValueError("frozen protocol contains no probe blueprints")
        if digest_payload(blueprints) != str(protocol.get("probe_blueprint_digest", "")):
            raise ValueError("probe blueprint digest mismatch")
        if protocol.get("design_certificate", {}).get("holdout_inputs_frozen_before_responses") is not True:
            raise ValueError("sealed holdout inputs were not frozen before world interaction")
        for row in blueprints:
            if row.get("response") is not None:
                raise ValueError("reference world refuses protocols containing prefilled responses")
        return blueprints

    def execute_frozen_protocol(
        self,
        *,
        protocol: Mapping[str, Any],
        allow_reference_simulation: bool = False,
        environment: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if not allow_reference_simulation:
            return _with_digest({
                "schema": "phi-atomic-reference-world-interaction/v1",
                "owner_id": self.owner_id,
                "status": "REFERENCE_SIMULATION_NOT_AUTHORIZED",
                "claim_boundary": {"responses_generated": False, "empirical_world_measurement": False},
            })
        blueprints = self._validate_protocol(protocol)
        env = dict(environment or {})
        components = int(protocol.get("components", 0))
        if components != 2:
            grid = list(blueprints[0]["grid"])
            core = {
                "schema": "phi-atomic-reference-world-interaction/v1",
                "owner_id": self.owner_id,
                "status": "TYPED_CARRIER_REDESIGN_REQUIRED",
                "probe_blueprint_digest": protocol.get("probe_blueprint_digest"),
                "required_carrier": {
                    "components": 2,
                    "grid": grid,
                    "coordinate_binding": "NUMERIC_GRID_IDENTIFIED_WITH_RADIAL_COORDINATE_IN_BOHR",
                    "reason": "REFERENCE_WORLD_STATE_RESPONSE_HAS_TWO_COUPLED_REAL_COMPONENTS",
                },
                "claim_boundary": {
                    "responses_generated": False,
                    "carrier_feedback_is_named_solver_selection": False,
                    "empirical_world_measurement": False,
                    "scientific_law_established": False,
                },
            }
            return _with_digest(core)

        alpha_inv, alpha_receipt = self._alpha_inverse()
        c_au = float(alpha_inv)
        positive_center_charge_units = float(env.get("positive_center_charge_units", 1.0))
        probe_charge_units = float(env.get("probe_charge_units", -1.0))
        signed_channel = float(env.get("signed_channel", -1.0))
        if not all(math.isfinite(v) for v in (positive_center_charge_units, probe_charge_units, signed_channel)):
            raise ValueError("non-finite reference-world environment parameter")
        if positive_center_charge_units <= 0 or probe_charge_units >= 0 or abs(signed_channel) < 1e-12:
            raise ValueError("reference-world environment must contain opposite unit-charge sectors and a nonzero signed channel")
        coupling = positive_center_charge_units * probe_charge_units

        rows: list[dict[str, Any]] = []
        for bp in blueprints:
            x = np.asarray(bp["grid"], dtype=float)
            state = np.asarray(bp["state"], dtype=float)
            if state.shape != (2, len(x)):
                raise ValueError("reference world requires two-component frozen state rows")
            x, d1, _ = _uniform_grid_matrices(x)
            p_state, q_state = state
            inverse_r = 1.0 / x
            central = coupling * inverse_r
            response0 = central * p_state + c_au * (-(d1 @ q_state) + signed_channel * inverse_r * q_state)
            response1 = c_au * ((d1 @ p_state) + signed_channel * inverse_r * p_state) + (central - 2.0 * c_au * c_au) * q_state
            rows.append({
                "probe_id": bp["probe_id"],
                "grid": bp["grid"],
                "state": bp["state"],
                "response": np.vstack([response0, response1]).tolist(),
                "role": bp["role"],
            })

        probe_digest = digest_payload(rows)
        model_core = {
            "carrier": "TWO_COMPONENT_RADIAL_REAL_FIELD",
            "coordinate_binding": "r/a0 = frozen numeric grid",
            "positive_center_charge_units": positive_center_charge_units,
            "probe_charge_units": probe_charge_units,
            "signed_channel": signed_channel,
            "inverse_speed_scale_constant": alpha_receipt,
            "discretization": "SAME_TYPED_FROZEN_GRID_CENTRAL_DIFFERENCE_CONTRACT_AS_EXECUTABLE_IR",
            "operator_action_postfreeze_audit": {
                "component_0": "V*f0 + c*(-d1(f1) + kappa*f1/r)",
                "component_1": "c*(d1(f0) + kappa*f0/r) + (V - 2*c^2)*f1",
                "V": "q_center*q_probe/r in atomic units",
            },
        }
        model_digest = digest_payload(model_core)
        attestation = {
            "schema": "phi-operator-probe-attestation/v2",
            "attestation_class": "TYPED_ATOMIC_REFERENCE_SIMULATION_AFTER_ATLAS_FREEZE",
            "provider_owner_id": self.owner_id,
            "probe_digest": probe_digest,
            "probe_blueprint_digest": protocol.get("probe_blueprint_digest"),
            "reference_model_digest": model_digest,
            "world_measurement": False,
            "reference_simulation": True,
            "oracle_visible_before_probe_freeze": False,
            "answer_bearing_regression_used": False,
            "atomic_frontier_module_used": False,
        }
        attestation["digest"] = digest_payload(attestation)
        core = {
            "schema": "phi-atomic-reference-world-interaction/v1",
            "owner_id": self.owner_id,
            "status": "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION",
            "probe_blueprint_digest": protocol.get("probe_blueprint_digest"),
            "probe_rows": rows,
            "probe_digest": probe_digest,
            "attestation": attestation,
            "postfreeze_audit_model": model_core,
            "postfreeze_audit_model_digest": model_digest,
            "claim_boundary": {
                "responses_generated_by_atlas": False,
                "responses_generated_by_independent_typed_owner": True,
                "empirical_world_measurement": False,
                "reference_simulation_is_new_atomic_law": False,
                "hidden_model_coefficients_exposed_to_synthesis": False,
                "named_solver_selected_by_synthesis": False,
                "answer_bearing_regression_used": False,
                "scientific_novelty_established": False,
            },
        }
        return _with_digest(core)



class VariableParticleProbeDesignOwner:
    """Birth an occupancy protocol without assuming a physical upper particle count.

    The owner selects integer occupancies only to identify generic affine/quadratic
    occupancy dependence.  Counts are experimental coordinates, not claims that a
    corresponding atom or element exists in nature.
    """

    owner_id = VARIABLE_PARTICLE_PROBE_DESIGN_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_ATLAS_OPERATOR_PROBE_PROTOCOL_PLUS_REPRESENTATION_GAP",
            "output": "FROZEN_VARIABLE_PARTICLE_EXPERIMENT_PROTOCOL_WITHOUT_RESPONSES",
            "particle_count_is_physical_object_existence_claim": False,
            "fixed_upper_particle_count": None,
            "response_generation_allowed": False,
            "design_basis": ("1", "N-1", "(N-1)^2"),
            "sealed_holdout_frozen_before_responses": True,
        }

    @staticmethod
    def _score(counts: Sequence[int]) -> tuple[int, float]:
        if not counts:
            return 0, 0.0
        x = np.asarray([[1.0, float(n-1), float((n-1)**2)] for n in counts], dtype=float)
        norms = np.linalg.norm(x, axis=0)
        z = x[:, norms > 1e-12] / norms[norms > 1e-12]
        rank = int(np.linalg.matrix_rank(z, tol=1e-12)) if z.size else 0
        sv = np.linalg.svd(z, compute_uv=False) if z.size else np.asarray([])
        return rank, float(sv[-1]) if len(sv) else 0.0

    def design(self, *, freeze_digest: str, base_protocol: Mapping[str, Any], design_shell: int = 1) -> Mapping[str, Any]:
        if not freeze_digest:
            raise ValueError("variable-particle probe design requires freeze_digest")
        if base_protocol.get("status") != "OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            raise ValueError("variable-particle design requires frozen Atlas base probe protocol")
        blueprints = [dict(x) for x in base_protocol.get("probe_blueprints", ())]
        if not blueprints or digest_payload(blueprints) != str(base_protocol.get("probe_blueprint_digest", "")):
            raise ValueError("invalid frozen base probe protocol")
        shell = max(1, int(design_shell))
        pool = list(range(1, max(7, 4 + 3*shell)))
        selected: list[int] = []
        target_rank = 3
        while pool and (len(selected) < 3 or self._score(selected)[0] < target_rank):
            ranked = []
            for n in pool:
                trial = selected + [n]
                rank, min_sv = self._score(trial)
                ranked.append((rank, min_sv, -n, n))
            best = max(ranked)[3]
            selected.append(best)
            pool.remove(best)
        holdout_count = max(1, shell)
        holdouts = pool[:holdout_count]
        rank, min_sv = self._score(selected)
        count_rows = ([{"particle_count": n, "role": "DISCOVERY"} for n in selected] +
                      [{"particle_count": n, "role": "SEALED_HOLDOUT"} for n in holdouts])
        core = {
            "schema": "phi-variable-particle-probe-design/v1",
            "owner_id": self.owner_id,
            "freeze_digest": freeze_digest,
            "base_probe_blueprint_digest": base_protocol.get("probe_blueprint_digest"),
            "particle_count_rows": count_rows,
            "design_certificate": {
                "target_feature_rank": target_rank,
                "achieved_feature_rank": rank,
                "normalized_min_singular_value": min_sv,
                "full_rank": rank >= target_rank,
                "sealed_holdout_frozen_before_responses": bool(holdouts),
                "fixed_upper_particle_count_used": False,
            },
            "claim_boundary": {
                "particle_counts_born_by_atlas": True,
                "particle_count_values_are_experimental_coordinates_not_existential_claims": True,
                "physical_upper_index_established": False,
                "responses_generated": False,
            },
        }
        payload = {**core, "protocol_digest": digest_payload(core)}
        payload["status"] = "VARIABLE_PARTICLE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES" if rank >= target_rank and holdouts else "VARIABLE_PARTICLE_PROTOCOL_NOT_IDENTIFYING"
        return _with_digest(payload)


class AtomicVariableParticleReferenceWorldInteractionOwner:
    """Independent nonlinear reference-world response provider.

    It receives only already-frozen Atlas state/occupancy protocols.  For each
    state it returns a typed density, a self-consistent field response and the
    resulting operator action.  The hidden reference model is not exposed until
    post-freeze audit and is explicitly a simulation benchmark, not empirical
    evidence of a new atom or periodic-table continuation.
    """

    owner_id = VARIABLE_PARTICLE_WORLD_INTERACTION_OWNER_ID

    def __init__(self, root: str | Path, one_particle_world: AtomicReferenceWorldInteractionOwner) -> None:
        self.root = Path(root)
        self.one_particle_world = one_particle_world

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_ATLAS_STATE_PROTOCOL_PLUS_FROZEN_VARIABLE_PARTICLE_PROTOCOL",
            "output": "DIGEST_BOUND_DENSITY_FIELD_AND_OPERATOR_RESPONSE_ROWS",
            "evidence_class": "NONLINEAR_REFERENCE_SIMULATION_NOT_EMPIRICAL_WORLD",
            "named_many_electron_solver_exposed_to_synthesis": False,
            "fixed_upper_particle_count": None,
            "nuclear_stability_claim": False,
        }

    def execute_frozen_protocol(self, *, base_protocol: Mapping[str, Any], particle_protocol: Mapping[str, Any], allow_reference_simulation: bool = False, environment: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        if not allow_reference_simulation:
            return _with_digest({
                "schema":"phi-variable-particle-reference-world/v1", "owner_id":self.owner_id,
                "status":"REFERENCE_SIMULATION_NOT_AUTHORIZED",
                "claim_boundary":{"responses_generated":False,"empirical_world_measurement":False},
            })
        blueprints = self.one_particle_world._validate_protocol(base_protocol)
        if int(base_protocol.get("components", 0)) != 2:
            raise ValueError("variable-particle world requires the previously identified two-component carrier")
        if particle_protocol.get("status") != "VARIABLE_PARTICLE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            raise ValueError("variable-particle world requires a qualified frozen occupancy protocol")
        count_rows = [dict(x) for x in particle_protocol.get("particle_count_rows", ())]
        if not count_rows:
            raise ValueError("empty variable-particle protocol")
        env = dict(environment or {})
        regularization = float(env.get("field_regularization", 0.5))
        field_scale = float(env.get("field_scale", 1.0))
        if not math.isfinite(regularization) or regularization < 0 or not math.isfinite(field_scale):
            raise ValueError("invalid variable-particle reference-world field parameters")

        # Get the hidden one-particle action entirely on the world side.  Synthesis
        # receives numeric rows, not these coefficients or the named model.
        one = self.one_particle_world.execute_frozen_protocol(
            protocol=base_protocol, allow_reference_simulation=True, environment=env
        )
        if one.get("status") != "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION":
            raise ValueError("one-particle reference world did not produce base responses")
        base_by_id = {str(r["probe_id"]): np.asarray(r["response"], dtype=float) for r in one.get("probe_rows", ())}

        rows: list[dict[str, Any]] = []
        for count_row in count_rows:
            n = int(count_row["particle_count"])
            if n < 1:
                raise ValueError("particle_count must be positive")
            count_role = str(count_row.get("role", "DISCOVERY")).upper()
            for bp in blueprints:
                x = np.asarray(bp["grid"], dtype=float)
                state = np.asarray(bp["state"], dtype=float)
                x, _, d2 = _uniform_grid_matrices(x)
                density = np.sum(np.square(state), axis=0)
                norm = float(np.trapezoid(density, x))
                if norm > 0:
                    density = density / norm
                source_scale = field_scale * float(n - 1)
                matrix = -d2 + regularization * np.eye(len(x))
                field = linalg.solve(matrix, source_scale * density, assume_a="sym")
                base_response = base_by_id[str(bp["probe_id"])]
                total_response = base_response + field[None, :] * state
                role = "SEALED_HOLDOUT" if count_role == "SEALED_HOLDOUT" or str(bp.get("role","")).upper() == "SEALED_HOLDOUT" else "DISCOVERY"
                rows.append({
                    "probe_id": str(bp["probe_id"]),
                    "particle_count": n,
                    "grid": bp["grid"],
                    "state": bp["state"],
                    "density": density.tolist(),
                    "field_id": "SCF_FIELD_0",
                    "field": field.tolist(),
                    "response": total_response.tolist(),
                    "role": role,
                })
        probe_digest = digest_payload(rows)
        hidden_model = {
            "field_equation_postfreeze_audit": "(-d2 + regularization*I) field = field_scale*(N-1)*normalized_density",
            "operator_extension_postfreeze_audit": "response = one_particle_response + field*state",
            "field_regularization": regularization,
            "field_scale": field_scale,
            "one_particle_reference_model_digest": one.get("postfreeze_audit_model_digest"),
        }
        attestation = {
            "schema":"phi-variable-particle-operator-attestation/v1",
            "attestation_class":"TYPED_VARIABLE_PARTICLE_SELF_CONSISTENT_REFERENCE_SIMULATION_AFTER_ATLAS_FREEZE",
            "provider_owner_id":self.owner_id,
            "probe_digest":probe_digest,
            "base_probe_blueprint_digest":base_protocol.get("probe_blueprint_digest"),
            "particle_protocol_digest":particle_protocol.get("protocol_digest"),
            "reference_model_digest":digest_payload(hidden_model),
            "world_measurement":False,
            "reference_simulation":True,
            "oracle_visible_before_probe_freeze":False,
            "answer_bearing_periodic_table_used":False,
        }
        attestation["digest"] = digest_payload(attestation)
        return _with_digest({
            "schema":"phi-variable-particle-reference-world/v1", "owner_id":self.owner_id,
            "status":"ATTESTED_VARIABLE_PARTICLE_SELF_CONSISTENT_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION",
            "probe_rows":rows, "probe_digest":probe_digest, "attestation":attestation,
            "postfreeze_audit_model":hidden_model,
            "claim_boundary":{
                "responses_generated_by_atlas":False,
                "responses_generated_by_independent_typed_owner":True,
                "empirical_world_measurement":False,
                "physical_atom_existence_established_for_particle_counts":False,
                "periodic_table_continuation_established":False,
                "nuclear_stability_established":False,
            },
        })


class SelfConsistentRepresentationSynthesisOwner:
    """Infer a density/field-dependent fixed-point extension from black-box rows."""

    owner_id = SELF_CONSISTENT_SYNTHESIS_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id":self.owner_id,
            "input":"ATTESTED_VARIABLE_PARTICLE_DENSITY_FIELD_OPERATOR_RESPONSE_ROWS_PLUS_BASE_ATLAS_OPERATOR",
            "output":"TYPED_SELF_CONSISTENT_EIGENPROBLEM_CANDIDATE",
            "field_coupling_grammar":"FIELD_MULTIPLICATION_CROSS_COMPONENT_BLOCKS",
            "field_update_grammar":"ELLIPTIC_RESPONSE_WITH_AFFINE_OCCUPANCY_SOURCE",
            "named_solver_selection":False,
            "fixed_particle_count_ceiling":None,
        }

    @staticmethod
    def _apply_linear_program(program: Mapping[str, Any], state: np.ndarray) -> np.ndarray:
        grid = [float(v) for v in program["state"]["grid"]]
        x,d1,d2 = _uniform_grid_matrices(grid)
        components = int(program["state"]["components"])
        out = np.zeros_like(state, dtype=float)
        for block in program.get("operator_blocks", ()):
            r=int(block["row_component"]); c=int(block["column_component"])
            for term in block.get("terms", ()):
                kind=str(term["kind"]); coeff=float(term["coefficient"])
                if kind == "FIELD_MULTIPLICATION":
                    continue
                out[r] += coeff * (_basis_matrix(kind,x,d1,d2,int(term.get("power",0))) @ state[c])
        return out

    @staticmethod
    def _nrmse(y: np.ndarray, pred: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(y-pred)))) / max(float(np.sqrt(np.mean(np.square(y)))),1e-12)

    def synthesize(self, *, base_candidate: Mapping[str, Any], probe_rows: Sequence[Mapping[str, Any]], freeze_digest: str, fit_tolerance_nrmse: float = 1e-7) -> Mapping[str, Any]:
        if base_candidate.get("qualified_for_compilation") is not True:
            return _with_digest({"schema":SCHEMA,"owner_id":self.owner_id,"status":"SELF_CONSISTENT_SYNTHESIS_REQUIRES_QUALIFIED_BASE_OPERATOR","qualified_for_compilation":False})
        rows=[dict(r) for r in probe_rows]
        if len(rows)<6:
            return _with_digest({"schema":SCHEMA,"owner_id":self.owner_id,"status":"SELF_CONSISTENT_SYNTHESIS_REQUIRES_MORE_PROBES","qualified_for_compilation":False})
        program0=dict(base_candidate.get("program",{}))
        grid=[float(v) for v in program0.get("state",{}).get("grid",())]
        components=int(program0.get("state",{}).get("components",0))
        x,_,d2=_uniform_grid_matrices(grid)
        norm=[]
        for r in rows:
            state=_flatten_components(r["state"],components,len(x))
            response=_flatten_components(r["response"],components,len(x))
            field=np.asarray(r["field"],dtype=float); density=np.asarray(r["density"],dtype=float)
            if field.shape!=(len(x),) or density.shape!=(len(x),):
                raise ValueError("self-consistent field/density shape mismatch")
            base=self._apply_linear_program(program0,state)
            norm.append({"state":state,"response":response,"base":base,"field":field,"density":density,"particle_count":int(r["particle_count"]),"role":str(r.get("role","")).upper()})
        discovery=[r for r in norm if r["role"]=="DISCOVERY"]; holdout=[r for r in norm if r["role"]=="SEALED_HOLDOUT"]
        if len(discovery)<3 or not holdout:
            return _with_digest({"schema":SCHEMA,"owner_id":self.owner_id,"status":"SELF_CONSISTENT_SYNTHESIS_REQUIRES_DISCOVERY_AND_HOLDOUT","qualified_for_compilation":False})

        coupling_blocks=[]; coupling_cert=[]; all_pass=True
        for outc in range(components):
            Xd=np.column_stack([np.concatenate([r["field"]*r["state"][src] for r in discovery]) for src in range(components)])
            yd=np.concatenate([(r["response"]-r["base"])[outc] for r in discovery])
            coef,*_=np.linalg.lstsq(Xd,yd,rcond=None)
            Xh=np.column_stack([np.concatenate([r["field"]*r["state"][src] for r in holdout]) for src in range(components)])
            yh=np.concatenate([(r["response"]-r["base"])[outc] for r in holdout])
            derr=self._nrmse(yd,Xd@coef); herr=self._nrmse(yh,Xh@coef)
            passed=derr<=fit_tolerance_nrmse and herr<=fit_tolerance_nrmse
            all_pass=all_pass and passed
            terms=[]
            for src,c in enumerate(coef):
                if abs(float(c))>1e-10:
                    coupling_blocks.append({"row_component":outc,"column_component":src,"terms":[{"kind":"FIELD_MULTIPLICATION","power":0,"coefficient":float(c),"field_id":"SCF_FIELD_0"}]})
            coupling_cert.append({"output_component":outc,"coefficients":[float(v) for v in coef],"discovery_nrmse":derr,"sealed_holdout_nrmse":herr,"pass":passed})

        # Infer (-d2 + r I) field = (a*N + b) density by linear least squares,
        # using discovery only.  This identifies regularization and occupancy law
        # without naming a domain solver.
        A=[]; y=[]
        for r in discovery:
            lhs=-(d2 @ r["field"])
            A.append(np.column_stack([float(r["particle_count"])*r["density"], r["density"], -r["field"]]))
            y.append(lhs)
        A=np.vstack(A); y=np.concatenate(y)
        theta,*_=np.linalg.lstsq(A,y,rcond=None)
        occ_scale, occ_intercept, regularization=[float(v) for v in theta]
        pred_d=A@theta
        field_d_err=self._nrmse(y,pred_d)
        Ah=[]; yh=[]
        for r in holdout:
            lhs=-(d2 @ r["field"])
            Ah.append(np.column_stack([float(r["particle_count"])*r["density"], r["density"], -r["field"]]))
            yh.append(lhs)
        Ah=np.vstack(Ah); yh=np.concatenate(yh)
        field_h_err=self._nrmse(yh,Ah@theta)
        field_pass=field_d_err<=fit_tolerance_nrmse and field_h_err<=fit_tolerance_nrmse and regularization>=-1e-8
        all_pass=all_pass and field_pass

        blocks=[{"row_component":int(b["row_component"]),"column_component":int(b["column_component"]),"terms":[dict(t) for t in b.get("terms",())]} for b in program0.get("operator_blocks",())]
        for cb in coupling_blocks:
            target=next((b for b in blocks if b["row_component"]==cb["row_component"] and b["column_component"]==cb["column_component"]),None)
            if target is None: blocks.append(cb)
            else: target["terms"].extend(cb["terms"])
        program={
            "program_type":"TYPED_LINEAR_OPERATOR_EIGENPROBLEM",
            "state":dict(program0["state"]),
            "operator_blocks":blocks,
            "metric":dict(program0.get("metric",{"kind":"IDENTITY"})),
            "problem":{
                "kind":"SELF_CONSISTENT_EIGENPROBLEM",
                "default_eigenpair_count":max(4,components*2),
                "fixed_point":{
                    "max_iterations":96,"tolerance":1e-9,"mixing":0.35,"occupied_eigenpair_count":2,
                    "field_updates":[{
                        "field_id":"SCF_FIELD_0","kind":"POISSON_RESPONSE","regularization":max(0.0,regularization),
                        "scale":occ_scale,"occupied_count_intercept":occ_intercept,"occupancy_affine":True,"offset":0.0,
                    }],
                },
            },
        }
        fit={
            "field_coupling_outputs":coupling_cert,
            "field_update":{"occupancy_scale":occ_scale,"occupancy_intercept":occ_intercept,"regularization":regularization,"discovery_nrmse":field_d_err,"sealed_holdout_nrmse":field_h_err,"pass":field_pass},
            "all_outputs_pass":all_pass,"tolerance_nrmse":fit_tolerance_nrmse,"sealed_holdout_not_used_for_selection":True,
        }
        core={"program":program,"probe_digest":digest_payload(rows),"freeze_digest":freeze_digest,"fit_certificate":fit}
        payload={
            "schema":SCHEMA,"owner_id":self.owner_id,
            "status":"GENERATED_SELF_CONSISTENT_EXECUTABLE_OPERATOR_CANDIDATE" if all_pass else "SELF_CONSISTENT_CANDIDATE_FAILS_SEALED_PROBE_GATE",
            "primitive_type":"GENERATED_TYPED_OPERATOR_PROGRAM","candidate_id":"SCF-"+digest_payload(core)[:16].upper(),
            "program":program,"probe_digest":core["probe_digest"],"freeze_digest":freeze_digest,"fit_certificate":fit,
            "qualified_for_compilation":all_pass,
            "claim_boundary":{"world_law_established":False,"physical_atom_existence_established":False,"known_many_electron_solver_selected":False,"periodic_table_continuation_established":False},
        }
        return _with_digest(payload)




def _fermion_annihilate(det: int, orbital: int) -> tuple[int, float] | None:
    bit = 1 << int(orbital)
    if not (int(det) & bit):
        return None
    parity = (int(det) & (bit - 1)).bit_count()
    return int(det) ^ bit, -1.0 if parity % 2 else 1.0


def _fermion_create(det: int, orbital: int) -> tuple[int, float] | None:
    bit = 1 << int(orbital)
    if int(det) & bit:
        return None
    parity = (int(det) & (bit - 1)).bit_count()
    return int(det) | bit, -1.0 if parity % 2 else 1.0


def _apply_normal_ordered_monomial(
    det: int, creators: Sequence[int], annihilators: Sequence[int]
) -> tuple[int, float] | None:
    """Apply a number-conserving fermionic monomial with a fixed canonical order.

    For sorted sets A=(a1<...<ak), B=(b1<...<bk) the represented operator is
    a†_a1 ... a†_ak a_bk ... a_b1.  It is a mathematical carrier convention;
    no atomic configuration ordering is encoded here.
    """
    state = int(det)
    sign = 1.0
    for q in sorted((int(x) for x in annihilators)):
        step = _fermion_annihilate(state, q)
        if step is None:
            return None
        state, sgn = step
        sign *= sgn
    for p in reversed(sorted(int(x) for x in creators)):
        step = _fermion_create(state, p)
        if step is None:
            return None
        state, sgn = step
        sign *= sgn
    return state, sign


def _fermionic_transition_matrix(
    determinants: Sequence[int], creators: Sequence[int], annihilators: Sequence[int]
) -> np.ndarray:
    index = {int(det): i for i, det in enumerate(determinants)}
    matrix = np.zeros((len(determinants), len(determinants)), dtype=float)
    for j, det in enumerate(determinants):
        result = _apply_normal_ordered_monomial(int(det), creators, annihilators)
        if result is None:
            continue
        out, sign = result
        i = index.get(int(out))
        if i is not None:
            matrix[i, j] += float(sign)
    return matrix


def _many_body_hermitian_grammar(
    determinants: Sequence[int], spin_orbital_count: int, interaction_rank: int
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    """Real Hermitian number-conserving operator grammar through body-rank k.

    The grammar is domain-neutral: rank-k coordinates are symmetrized normal-
    ordered monomials over k creation and k annihilation indices.  No Coulomb
    kernel, orbital order, element exception, CI/MCDHF vocabulary, or known
    atomic configuration is present in this synthesis grammar.
    """
    dets = [int(x) for x in determinants]
    m = int(spin_orbital_count)
    kmax = max(1, int(interaction_rank))
    matrices: list[np.ndarray] = []
    specs: list[dict[str, Any]] = []
    for rank in range(1, kmax + 1):
        subsets = list(combinations(range(m), rank))
        for ia, A in enumerate(subsets):
            for ib in range(ia, len(subsets)):
                B = subsets[ib]
                mab = _fermionic_transition_matrix(dets, A, B)
                if A == B:
                    mat = mab
                    symmetry = "HERMITIAN_DIAGONAL_MONOMIAL"
                else:
                    mba = _fermionic_transition_matrix(dets, B, A)
                    mat = mab + mba
                    symmetry = "HERMITIAN_SYMMETRIC_MONOMIAL"
                if float(np.linalg.norm(mat)) <= 1e-13:
                    continue
                matrices.append(mat)
                specs.append({
                    "interaction_rank": rank,
                    "creation_orbitals": list(A),
                    "annihilation_orbitals": list(B),
                    "symmetry": symmetry,
                })
    return matrices, specs


class ManyBodyOperatorProbeDesignOwner:
    """Freeze response-free probes on a finite fermionic occupation carrier.

    The carrier is generated from particle count and spin-orbital count only.
    Probe selection maximizes rank of the *generic normal-ordered grammar* for
    the requested interaction shell.  It never queries an atomic solver or a
    known ground-state configuration.
    """

    owner_id = MANY_BODY_PROBE_DESIGN_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_GAP_PLUS_PARTICLE_COUNT_AND_FINITE_RESEARCH_CARRIER",
            "output": "RESPONSE_FREE_FERMIONIC_OPERATOR_PROBE_PROTOCOL",
            "known_ground_state_required": False,
            "known_many_body_method_required": False,
            "fixed_global_interaction_rank_ceiling": None,
            "interaction_shell_expands_after_sealed_residual": True,
            "response_generation_allowed": False,
        }

    @staticmethod
    def _carrier(electron_count: int, spin_orbital_count: int) -> list[int]:
        n = int(electron_count); m = int(spin_orbital_count)
        if n < 1 or m < n:
            raise ValueError("fermionic carrier requires 1 <= electron_count <= spin_orbital_count")
        return [sum(1 << q for q in occ) for occ in combinations(range(m), n)]

    def design(
        self,
        *,
        freeze_digest: str,
        atom_z: int,
        electron_count: int,
        spatial_orbital_count: int = 3,
        interaction_rank: int = 1,
        design_shell: int = 1,
    ) -> Mapping[str, Any]:
        if not str(freeze_digest):
            raise ValueError("many-body probe design requires freeze_digest")
        z = int(atom_z); n = int(electron_count); spatial = max(1, int(spatial_orbital_count))
        m = 2 * spatial
        if n > m:
            # This is a research-basis insufficiency, not a physical atom limit.
            return _with_digest({
                "schema": "phi-many-body-probe-design/v1", "owner_id": self.owner_id,
                "status": "RESEARCH_CARRIER_REQUIRES_ORBITAL_BASIS_EXPANSION",
                "atom_z": z, "electron_count": n, "spin_orbital_count": m,
                "required_minimum_spatial_orbital_count": int(math.ceil(n / 2)),
                "claim_boundary": {"physical_atom_nonexistent": False, "fixed_global_orbital_ceiling": False},
            })
        dets = self._carrier(n, m)
        rank = max(1, min(int(interaction_rank), n))
        matrices, specs = _many_body_hermitian_grammar(dets, m, rank)
        if not matrices:
            raise RuntimeError("empty many-body grammar for finite carrier")
        vec_basis = np.column_stack([B.reshape(-1) for B in matrices])
        target_rank = int(np.linalg.matrix_rank(vec_basis, tol=1e-10))
        dim = len(dets)
        seed = int(digest_payload({
            "freeze": freeze_digest, "Z": z, "N": n, "m": m,
            "interaction_rank": rank, "design_shell": int(design_shell),
        })[:16], 16)
        rng = np.random.default_rng(seed)
        pool_size = max(24, 4 * int(math.ceil(target_rank / max(dim, 1))) + 12 * max(1, int(design_shell)))
        pool: list[tuple[int, np.ndarray, np.ndarray]] = []
        for idx in range(pool_size):
            x = rng.normal(size=dim)
            norm = float(np.linalg.norm(x))
            if norm <= 0:
                continue
            x = x / norm
            feat = np.column_stack([B @ x for B in matrices])
            pool.append((idx, x, feat))
        selected: list[tuple[int, np.ndarray, np.ndarray]] = []
        stacked = np.empty((0, len(matrices)), dtype=float)
        min_discovery = max(3, int(math.ceil(target_rank / max(dim, 1))))
        while pool and (len(selected) < min_discovery or int(np.linalg.matrix_rank(stacked, tol=1e-10)) < target_rank):
            ranked = []
            for row in pool:
                trial = np.vstack([stacked, row[2]])
                rnk = int(np.linalg.matrix_rank(trial, tol=1e-10))
                svals = np.linalg.svd(trial, compute_uv=False)
                pos = svals[svals > 1e-12]
                min_sv = float(pos[-1]) if len(pos) else 0.0
                ranked.append((rnk, min_sv, -row[0], row, trial))
            _, _, _, best, trial = max(ranked, key=lambda x: (x[0], x[1], x[2]))
            selected.append(best); stacked = trial
            pool = [x for x in pool if x[0] != best[0]]
        achieved = int(np.linalg.matrix_rank(stacked, tol=1e-10))
        holdout_count = max(2, int(design_shell))
        holdouts = pool[:holdout_count]
        blueprints: list[dict[str, Any]] = []
        for role, rows in (("DISCOVERY", selected), ("SEALED_HOLDOUT", holdouts)):
            for idx, state, _ in rows:
                core = {"role": role, "state": state.tolist(), "response": None, "candidate_index": idx}
                blueprints.append({"probe_id": "MBP-" + digest_payload(core)[:16].upper(), **core})
        carrier = {
            "atom_z": z,
            "electron_count": n,
            "spatial_orbital_count": spatial,
            "spin_orbital_count": m,
            "determinants": dets,
            "determinant_dimension": dim,
            "determinant_generation": "ALL_FIXED_PARTICLE_NUMBER_BIT_OCCUPATIONS",
        }
        payload = {
            "schema": "phi-many-body-probe-design/v1", "owner_id": self.owner_id,
            "status": "MANY_BODY_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES" if achieved >= target_rank and holdouts else "MANY_BODY_OPERATOR_PROBE_SHELL_UNDERIDENTIFIED",
            "freeze_digest": str(freeze_digest), "design_shell": int(design_shell),
            "interaction_rank_shell": rank, "carrier": carrier,
            "grammar_certificate": {
                "raw_term_count": len(specs), "independent_operator_rank": target_rank,
                "achieved_probe_feature_rank": achieved,
                "discovery_probe_count": len(selected), "sealed_holdout_probe_count": len(holdouts),
                "holdout_inputs_frozen_before_responses": True,
            },
            "probe_blueprints": blueprints, "probe_blueprint_digest": digest_payload(blueprints),
            "claim_boundary": {
                "atlas_generated_probe_inputs": True, "atlas_generated_operator_responses": False,
                "known_ground_state_used": False, "named_many_body_solver_used": False,
                "interaction_rank_is_research_shell_not_physical_truth": True,
                "fixed_global_interaction_rank_ceiling": False,
            },
        }
        return _with_digest(payload)


class AtomicManyBodyReferenceWorldInteractionOwner:
    """Independent small-basis atomic many-electron reference simulation.

    It evaluates frozen determinant-space probes with the nonrelativistic
    electronic Hamiltonian in a hydrogenic s-orbital research basis.  The
    synthesis owner receives only state->response rows plus carrier metadata;
    one- and two-electron integrals and the Hamiltonian matrix remain hidden.
    This is a deterministic reference simulation, never an empirical result.
    """

    owner_id = ATOMIC_MANY_BODY_WORLD_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_RESPONSE_FREE_FERMIONIC_PROBES",
            "output": "DIGEST_BOUND_BLACK_BOX_MANY_BODY_OPERATOR_RESPONSES",
            "reference_model": "NONRELATIVISTIC_COULOMB_HAMILTONIAN_SMALL_HYDROGENIC_S_BASIS",
            "named_many_body_solver_exposed_to_synthesis": False,
            "ground_state_configuration_exposed_to_synthesis": False,
            "empirical_world_measurement": False,
            "fixed_global_orbital_basis_ceiling": None,
        }

    @staticmethod
    def _radial_basis(z: int, spatial_count: int, points: int) -> tuple[np.ndarray, list[np.ndarray]]:
        zf = float(z)
        rmin = 1.0e-6 / max(zf, 1.0)
        rmax = max(20.0, 35.0 / max(zf, 1.0))
        r = np.geomspace(rmin, rmax, max(400, int(points)))
        basis: list[np.ndarray] = []
        for n in range(1, int(spatial_count) + 1):
            rho = 2.0 * zf * r / float(n)
            pref = math.sqrt((2.0 * zf / n) ** 3 * math.factorial(n - 1) / (2.0 * n * math.factorial(n)))
            radial_R = pref * np.exp(-rho / 2.0) * eval_genlaguerre(n - 1, 1, rho)
            P = r * radial_R
            norm = float(np.trapezoid(P * P, r))
            if norm <= 0 or not math.isfinite(norm):
                raise RuntimeError("invalid hydrogenic radial basis norm")
            basis.append(P / math.sqrt(norm))
        return r, basis

    @staticmethod
    def _spatial_integrals(z: int, r: np.ndarray, basis: Sequence[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        s = len(basis)
        h = np.zeros((s, s), dtype=float)
        for a in range(s):
            dpa = np.gradient(basis[a], r, edge_order=2)
            for c in range(s):
                dpc = np.gradient(basis[c], r, edge_order=2)
                h[a, c] = float(np.trapezoid(0.5 * dpa * dpc - float(z) * basis[a] * basis[c] / r, r))
        g = np.zeros((s, s, s, s), dtype=float)
        # For s orbitals the angularly integrated Coulomb kernel is 1/max(r1,r2).
        products = {(b, d): basis[b] * basis[d] for b in range(s) for d in range(s)}
        potentials: dict[tuple[int, int], np.ndarray] = {}
        for key, f in products.items():
            inner = np.zeros_like(r)
            inner[1:] = np.cumsum(0.5 * (f[1:] + f[:-1]) * np.diff(r))
            fr = f / r
            rev = np.zeros_like(r)
            vals = 0.5 * (fr[1:] + fr[:-1]) * np.diff(r)
            rev[:-1] = np.cumsum(vals[::-1])[::-1]
            potentials[key] = inner / r + rev
        for a in range(s):
            for b in range(s):
                for c in range(s):
                    fac = basis[a] * basis[c]
                    for d in range(s):
                        g[a, b, c, d] = float(np.trapezoid(fac * potentials[(b, d)], r))
        return h, g

    @staticmethod
    def _hamiltonian(carrier: Mapping[str, Any], *, radial_points: int) -> tuple[np.ndarray, Mapping[str, Any]]:
        z = int(carrier["atom_z"]); n = int(carrier["electron_count"])
        spatial = int(carrier["spatial_orbital_count"]); m = int(carrier["spin_orbital_count"])
        dets = [int(x) for x in carrier["determinants"]]
        r, basis = AtomicManyBodyReferenceWorldInteractionOwner._radial_basis(z, spatial, radial_points)
        h_sp, g_sp = AtomicManyBodyReferenceWorldInteractionOwner._spatial_integrals(z, r, basis)
        H = np.zeros((len(dets), len(dets)), dtype=float)
        # one-body sector
        for p in range(m):
            ap, spn_p = divmod(p, 2)
            for q in range(m):
                aq, spn_q = divmod(q, 2)
                if spn_p != spn_q:
                    continue
                coeff = float(h_sp[ap, aq])
                if abs(coeff) < 1e-14:
                    continue
                H += coeff * _fermionic_transition_matrix(dets, (p,), (q,))
        # two-body sector in an ordered-pair basis: <pq||rs> P†_pq P_rs.
        pairs = list(combinations(range(m), 2))
        for A in pairs:
            p, q = A; ap, spn_p = divmod(p, 2); aq, spn_q = divmod(q, 2)
            for B in pairs:
                rr, ss = B; ar, spn_r = divmod(rr, 2); a_s, spn_s = divmod(ss, 2)
                direct = float(g_sp[ap, aq, ar, a_s]) if (spn_p == spn_r and spn_q == spn_s) else 0.0
                exchange = float(g_sp[ap, aq, a_s, ar]) if (spn_p == spn_s and spn_q == spn_r) else 0.0
                coeff = direct - exchange
                if abs(coeff) < 1e-13:
                    continue
                H += coeff * _fermionic_transition_matrix(dets, A, B)
        H = 0.5 * (H + H.T)
        vals = np.linalg.eigvalsh(H)
        audit = {
            "atom_z": z, "electron_count": n, "spatial_orbital_count": spatial,
            "spin_orbital_count": m, "determinant_dimension": len(dets),
            "radial_grid_points": len(r), "radial_r_min_bohr": float(r[0]), "radial_r_max_bohr": float(r[-1]),
            "lowest_reference_energy_hartree": float(vals[0]),
            "highest_reference_energy_hartree": float(vals[-1]),
            "hamiltonian_hermiticity_relative_defect": float(np.linalg.norm(H-H.T)/max(np.linalg.norm(H),1e-15)),
            "hidden_one_body_integral_digest": digest_payload(h_sp.tolist()),
            "hidden_two_body_integral_digest": digest_payload(g_sp.tolist()),
            "hidden_hamiltonian_digest": digest_payload(H.tolist()),
        }
        return H, audit

    @staticmethod
    def _validate(protocol: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if protocol.get("status") != "MANY_BODY_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            raise ValueError("many-body world requires a qualified frozen probe protocol")
        blueprints = [dict(x) for x in protocol.get("probe_blueprints", ())]
        if digest_payload(blueprints) != str(protocol.get("probe_blueprint_digest", "")):
            raise ValueError("many-body probe blueprint digest mismatch")
        if protocol.get("grammar_certificate", {}).get("holdout_inputs_frozen_before_responses") is not True:
            raise ValueError("many-body holdout was not frozen before world interaction")
        if any(row.get("response") is not None for row in blueprints):
            raise ValueError("many-body reference world refuses prefilled responses")
        return blueprints, dict(protocol["carrier"])

    def execute_frozen_protocol(
        self, *, protocol: Mapping[str, Any], allow_reference_simulation: bool = False, radial_points: int = 700
    ) -> Mapping[str, Any]:
        if not allow_reference_simulation:
            return _with_digest({
                "schema": "phi-atomic-many-body-world/v1", "owner_id": self.owner_id,
                "status": "REFERENCE_SIMULATION_NOT_AUTHORIZED",
                "claim_boundary": {"responses_generated": False, "empirical_world_measurement": False},
            })
        blueprints, carrier = self._validate(protocol)
        H, audit = self._hamiltonian(carrier, radial_points=max(400, int(radial_points)))
        rows = []
        dim = int(carrier["determinant_dimension"])
        for bp in blueprints:
            state = np.asarray(bp["state"], dtype=float)
            if state.shape != (dim,):
                raise ValueError("many-body state dimension mismatch")
            response = H @ state
            rows.append({
                "probe_id": bp["probe_id"], "role": bp["role"],
                "state": state.tolist(), "response": response.tolist(),
            })
        probe_digest = digest_payload(rows)
        attestation = {
            "schema": "phi-many-body-operator-attestation/v1",
            "attestation_class": "ATOMIC_MANY_BODY_REFERENCE_SIMULATION_AFTER_FREEZE",
            "provider_owner_id": self.owner_id,
            "probe_digest": probe_digest,
            "probe_blueprint_digest": protocol.get("probe_blueprint_digest"),
            "carrier_digest": digest_payload(carrier),
            "world_measurement": False, "reference_simulation": True,
            "oracle_visible_before_probe_freeze": False,
        }
        attestation["digest"] = digest_payload(attestation)
        return _with_digest({
            "schema": "phi-atomic-many-body-world/v1", "owner_id": self.owner_id,
            "status": "ATTESTED_MANY_BODY_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION",
            "carrier": carrier, "probe_rows": rows, "probe_digest": probe_digest,
            "attestation": attestation,
            "postfreeze_reference_audit": audit,
            "claim_boundary": {
                "responses_generated_by_independent_typed_owner": True,
                "hidden_hamiltonian_exposed_to_synthesis": False,
                "known_ground_state_exposed_to_synthesis": False,
                "named_many_body_solver_exposed_to_synthesis": False,
                "empirical_world_measurement": False,
                "reference_simulation_establishes_atomic_truth": False,
            },
        })


class ManyBodyOperatorCoordinateSynthesisOwner:
    """Identify the minimal normal-ordered interaction rank from black-box action.

    The search starts at rank one and may expand until the finite carrier itself
    cannot support a higher nonzero body rank.  That carrier-local boundary is a
    mathematical consequence of particle count, not a global physics ceiling.
    """

    owner_id = MANY_BODY_SYNTHESIS_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "FROZEN_FERMIONIC_STATE_TO_OPERATOR_RESPONSE_ROWS",
            "candidate_grammar": "NORMAL_ORDERED_NUMBER_CONSERVING_FERMION_MONOMIALS_BY_INTERACTION_RANK",
            "search_starts_at_rank": 1,
            "fixed_global_interaction_rank_ceiling": None,
            "selection_gate": "SEALED_HOLDOUT_OPERATOR_ACTION_NRMSE",
            "known_many_body_method_required": False,
            "named_solver_selection": False,
        }

    @staticmethod
    def _nrmse(y: np.ndarray, p: np.ndarray) -> float:
        return float(np.sqrt(np.mean((y-p)**2)) / max(np.sqrt(np.mean(y*y)), 1e-15))

    def synthesize(
        self,
        *,
        carrier: Mapping[str, Any],
        probe_rows: Sequence[Mapping[str, Any]],
        freeze_digest: str,
        fit_tolerance_nrmse: float = 1e-9,
        max_interaction_rank: int | None = None,
        require_precommitted_rank: int | None = None,
    ) -> Mapping[str, Any]:
        dets = [int(x) for x in carrier.get("determinants", ())]
        m = int(carrier.get("spin_orbital_count", 0)); n = int(carrier.get("electron_count", 0))
        dim = len(dets)
        if not dets or m <= 0 or n <= 0 or not str(freeze_digest):
            raise ValueError("invalid many-body synthesis carrier/freeze")
        rows = [dict(x) for x in probe_rows]
        discovery = [r for r in rows if str(r.get("role", "")).upper() == "DISCOVERY"]
        holdout = [r for r in rows if str(r.get("role", "")).upper() == "SEALED_HOLDOUT"]
        if len(discovery) < 2 or not holdout:
            return _with_digest({
                "schema": "phi-many-body-coordinate-synthesis/v1", "owner_id": self.owner_id,
                "status": "MANY_BODY_SYNTHESIS_REQUIRES_DISCOVERY_AND_SEALED_HOLDOUT_PROBES",
                "qualified": False,
            })
        local_max = max(1, n)
        stop_rank = min(local_max, int(max_interaction_rank) if max_interaction_rank is not None else local_max)
        ranks = [int(require_precommitted_rank)] if require_precommitted_rank is not None else list(range(1, stop_rank+1))
        history = []
        selected = None
        for rank in ranks:
            if rank < 1 or rank > local_max:
                continue
            matrices, specs = _many_body_hermitian_grammar(dets, m, rank)
            def assemble(which: list[Mapping[str, Any]]):
                Xblocks=[]; yblocks=[]
                for row in which:
                    state=np.asarray(row["state"],dtype=float); response=np.asarray(row["response"],dtype=float)
                    if state.shape!=(dim,) or response.shape!=(dim,):
                        raise ValueError("many-body probe row dimension mismatch")
                    Xblocks.append(np.column_stack([B@state for B in matrices])); yblocks.append(response)
                return np.vstack(Xblocks), np.concatenate(yblocks)
            Xd, yd = assemble(discovery); Xh, yh = assemble(holdout)
            coef, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
            pd = Xd @ coef; ph = Xh @ coef
            d_err = self._nrmse(yd, pd); h_err = self._nrmse(yh, ph)
            design_rank = int(np.linalg.matrix_rank(Xd, tol=1e-10))
            active = []
            scale = max(float(np.max(np.abs(coef))) if len(coef) else 0.0, 1e-15)
            for c, spec in zip(coef, specs):
                if abs(float(c)) >= 1e-8 * scale:
                    active.append({**spec, "coefficient": float(c)})
            row = {
                "interaction_rank_shell": rank,
                "grammar_term_count": len(specs), "discovery_design_rank": design_rank,
                "discovery_nrmse": d_err, "sealed_holdout_nrmse": h_err,
                "active_term_count": len(active),
                "active_highest_rank": max([int(x["interaction_rank"]) for x in active] or [0]),
                "pass": h_err <= float(fit_tolerance_nrmse),
            }
            history.append(row)
            if row["pass"]:
                selected = {**row, "active_terms": active}
                break
        if selected is None:
            next_rank = None if stop_rank >= local_max else stop_rank + 1
            status = "MANY_BODY_OPERATOR_GRAMMAR_CURRENT_SHELL_FAILS_SEALED_HOLDOUT"
        else:
            next_rank = None
            status = "MANY_BODY_OPERATOR_COORDINATES_IDENTIFIED_ON_SEALED_HOLDOUT"
        inferred_shell = int(selected["interaction_rank_shell"]) if selected else None
        minimal = inferred_shell if require_precommitted_rank is None else None
        validated_precommitted = inferred_shell if (selected is not None and require_precommitted_rank is not None) else None
        born = []
        if minimal is not None and minimal > 1:
            born.append({
                "axis_id": "operator_interaction_rank",
                "origin": "SEALED_BLACK_BOX_OPERATOR_RESIDUAL",
                "canonical": False,
                "activation_state": "RESEARCH_LOCAL_ACTIVE",
                "value": minimal,
                "semantics": "minimum normal-ordered joint-coordinate arity required by frozen holdout",
            })
        payload = {
            "schema": "phi-many-body-coordinate-synthesis/v1", "owner_id": self.owner_id,
            "status": status, "freeze_digest": str(freeze_digest),
            "carrier_digest": digest_payload(dict(carrier)), "probe_digest": digest_payload(rows),
            "fit_tolerance_nrmse": float(fit_tolerance_nrmse),
            "interaction_rank_history": history,
            "minimal_interaction_rank": minimal,
            "validated_precommitted_interaction_rank": validated_precommitted,
            "precommitted_interaction_rank": require_precommitted_rank,
            "selected_shell": selected,
            "research_local_operator_coordinates": born,
            "next_interaction_rank_shell": next_rank,
            "qualified": selected is not None,
            "claim_boundary": {
                "named_many_body_method_selected": False,
                "coulomb_kernel_present_in_synthesis_grammar": False,
                "known_atomic_configuration_used": False,
                "minimal_rank_is_scientific_world_law": False,
                "precommitted_rank_validation_relabels_rank_as_minimum": False,
                "carrier_local_max_rank_is_global_physical_ceiling": False,
            },
        }
        return _with_digest(payload)


class ExecutableRepresentationSynthesisOwner:
    """Infer a sparse typed linear operator from black-box response probes.

    The owner sees only input state -> operator response pairs.  It is not told a
    named equation or solver family.  A deterministic sparse forward-selection
    search is performed over a domain-neutral operator grammar and is validated
    on probes excluded from fitting.
    """

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": SYNTHESIS_OWNER_ID,
            "input": "BLACK_BOX_TYPED_OPERATOR_RESPONSE_PROBES",
            "candidate_grammar": {
                "state_carrier": "MULTICOMPONENT_REAL_FIELD_ON_UNIFORM_1D_GRID",
                "basis_operators": (
                    "IDENTITY", "FIRST_DERIVATIVE", "SECOND_DERIVATIVE",
                    "COORDINATE_POWER[-2]", "COORDINATE_POWER[-1]",
                    "COORDINATE_POWER[1]", "COORDINATE_POWER[2]",
                    "FIELD_MULTIPLICATION (compiled nonlinear/fixed-point programs)",
                ),
                "cross_component_blocks": True,
                "fixed_operator_term_ceiling": None,
                "search": "DETERMINISTIC_SPARSE_FORWARD_SELECTION_BY_HELDOUT_OPERATOR_ERROR",
            },
            "known_law_name_required": False,
            "named_solver_selection": False,
            "arbitrary_code_generation": False,
            "internet_prefreeze": "FORBIDDEN",
            "insufficient_evidence_status": "EXECUTABLE_SYNTHESIS_REQUIRES_OPERATOR_PROBES",
        }

    @staticmethod
    def _fail(reason: str, *, probe_digest: str = "") -> Mapping[str, Any]:
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": SYNTHESIS_OWNER_ID,
            "status": "EXECUTABLE_SYNTHESIS_REQUIRES_OPERATOR_PROBES",
            "reason": reason,
            "probe_digest": probe_digest,
            "required_probe_schema": {
                "grid": "uniform finite 1D coordinate array",
                "state": "components x grid_points input field",
                "response": "components x grid_points measured/attested operator action",
                "role": "DISCOVERY or SEALED_HOLDOUT (optional; deterministic split otherwise)",
            },
            "claim_boundary": {
                "executable_representation_established": False,
                "world_law_established": False,
                "assistant_may_fill_missing_probe_values": False,
            },
        })

    @staticmethod
    def _term_specs(components: int) -> list[dict[str, Any]]:
        ops: list[tuple[str, int]] = [
            ("IDENTITY", 0), ("FIRST_DERIVATIVE", 0), ("SECOND_DERIVATIVE", 0),
            ("COORDINATE_POWER", -2), ("COORDINATE_POWER", -1),
            ("COORDINATE_POWER", 1), ("COORDINATE_POWER", 2),
        ]
        rows: list[dict[str, Any]] = []
        for source in range(components):
            for kind, power in ops:
                rows.append({"source_component": source, "kind": kind, "power": power})
        return rows

    @staticmethod
    def _feature_for_probe(spec: Mapping[str, Any], state: np.ndarray, x: np.ndarray, d1: np.ndarray, d2: np.ndarray) -> np.ndarray:
        mat = _basis_matrix(str(spec["kind"]), x, d1, d2, int(spec.get("power", 0)))
        return mat @ state[int(spec["source_component"])]

    @staticmethod
    def _nrmse(y: np.ndarray, pred: np.ndarray) -> float:
        rmse = float(np.sqrt(np.mean(np.square(y - pred))))
        scale = float(np.sqrt(np.mean(np.square(y))))
        return rmse / max(scale, 1e-12)

    @staticmethod
    def _fit_selected(matrix: np.ndarray, target: np.ndarray, selected: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
        if not selected:
            return np.empty(0, dtype=float), np.zeros_like(target)
        design = matrix[:, list(selected)]
        coef, *_ = np.linalg.lstsq(design, target, rcond=None)
        return coef, design @ coef

    def synthesize(
        self,
        *,
        probe_rows: Sequence[Mapping[str, Any]],
        freeze_digest: str,
        fit_tolerance_nrmse: float = 1e-5,
        max_terms_per_output: int | None = None,
    ) -> Mapping[str, Any]:
        if not freeze_digest:
            return self._fail("MISSING_FREEZE_DIGEST")
        rows = [dict(r) for r in probe_rows]
        probe_digest = digest_payload(rows)
        if len(rows) < 4:
            return self._fail("AT_LEAST_FOUR_OPERATOR_PROBES_REQUIRED", probe_digest=probe_digest)
        try:
            grid = [float(v) for v in rows[0]["grid"]]
            x, d1, d2 = _uniform_grid_matrices(grid)
            first_state = np.asarray(rows[0]["state"], dtype=float)
            if first_state.ndim != 2 or first_state.shape[1] != len(x):
                raise ValueError("probe state must be components x grid_points")
            components = int(first_state.shape[0])
            normalized = []
            for idx, row in enumerate(rows):
                if not np.allclose(np.asarray(row["grid"], dtype=float), x, rtol=0, atol=1e-12):
                    raise ValueError("all operator probes must use the same frozen grid")
                state = _flatten_components(row["state"], components, len(x))
                response = _flatten_components(row["response"], components, len(x))
                normalized.append({"state": state, "response": response, "role": str(row.get("role", "")).upper(), "row": idx})
        except Exception as exc:
            return self._fail(f"INVALID_OPERATOR_PROBE:{exc}", probe_digest=probe_digest)

        explicit_discovery = [r for r in normalized if r["role"] == "DISCOVERY"]
        explicit_holdout = [r for r in normalized if r["role"] == "SEALED_HOLDOUT"]
        if explicit_discovery and explicit_holdout:
            discovery, holdout = explicit_discovery, explicit_holdout
        else:
            hold_count = max(1, len(normalized) // 4)
            discovery, holdout = normalized[:-hold_count], normalized[-hold_count:]
        if len(discovery) < 3 or not holdout:
            return self._fail("INSUFFICIENT_DISCOVERY_HOLDOUT_SPLIT", probe_digest=probe_digest)

        specs = self._term_specs(components)
        if max_terms_per_output is None:
            max_terms = len(specs)
        else:
            max_terms = max(1, min(int(max_terms_per_output), len(specs)))

        fitted_blocks: list[dict[str, Any]] = []
        output_certificates: list[dict[str, Any]] = []
        all_pass = True
        for out_component in range(components):
            discovery_features = []
            holdout_features = []
            for spec in specs:
                discovery_features.append(np.concatenate([
                    self._feature_for_probe(spec, r["state"], x, d1, d2) for r in discovery
                ]))
                holdout_features.append(np.concatenate([
                    self._feature_for_probe(spec, r["state"], x, d1, d2) for r in holdout
                ]))
            Xd = np.column_stack(discovery_features)
            Xh = np.column_stack(holdout_features)
            yd = np.concatenate([r["response"][out_component] for r in discovery])
            yh = np.concatenate([r["response"][out_component] for r in holdout])
            norms = np.linalg.norm(Xd, axis=0)
            usable = [i for i, n in enumerate(norms) if math.isfinite(float(n)) and float(n) > 1e-12]
            selected: list[int] = []
            history: list[dict[str, Any]] = []
            previous_discovery = float("inf")
            for shell in range(1, max_terms + 1):
                coef0, pred0 = self._fit_selected(Xd, yd, selected)
                residual = yd - pred0
                remaining = [i for i in usable if i not in selected]
                if not remaining:
                    break
                ranked = sorted(
                    remaining,
                    key=lambda i: (-abs(float(np.dot(Xd[:, i], residual))) / max(float(norms[i]), 1e-12), i),
                )
                chosen = ranked[0]
                trial = selected + [chosen]
                coef, pred_d = self._fit_selected(Xd, yd, trial)
                d_err = self._nrmse(yd, pred_d)
                history.append({
                    "complexity_shell": shell,
                    "selected_term_index": chosen,
                    "selected_term": specs[chosen],
                    "discovery_nrmse": d_err,
                })
                if d_err > previous_discovery * (1.0 - 1e-10):
                    break
                selected = trial
                previous_discovery = d_err
                if d_err <= float(fit_tolerance_nrmse):
                    break
            # Discovery-only backward pruning. Forward selection is intentionally
            # generous because correlated basis terms can enter before the true sparse
            # support.  Once a discovery fit reaches tolerance, remove any term whose
            # deletion still satisfies the same frozen discovery gate.  The sealed
            # holdout is never inspected during pruning or tie-breaking.
            pruning_history: list[dict[str, Any]] = []
            while len(selected) > 1:
                removable: list[tuple[float, int, list[int]]] = []
                for term_idx in selected:
                    trial = [i for i in selected if i != term_idx]
                    _, pred_trial = self._fit_selected(Xd, yd, trial)
                    trial_error = self._nrmse(yd, pred_trial)
                    if trial_error <= float(fit_tolerance_nrmse):
                        removable.append((trial_error, term_idx, trial))
                if not removable:
                    break
                # Prefer the deletion with the lowest discovery error; use the term
                # index only as a deterministic tie-breaker.
                trial_error, removed_idx, trial = min(removable, key=lambda row: (row[0], row[1]))
                pruning_history.append({
                    "removed_term_index": removed_idx,
                    "removed_term": specs[removed_idx],
                    "discovery_nrmse_after_removal": trial_error,
                })
                selected = trial

            coef, pred_d = self._fit_selected(Xd, yd, selected)
            pred_h = Xh[:, selected] @ coef if selected else np.zeros_like(yh)
            discovery_error = self._nrmse(yd, pred_d)
            holdout_error = self._nrmse(yh, pred_h)
            passed = bool(selected) and discovery_error <= float(fit_tolerance_nrmse) and holdout_error <= float(fit_tolerance_nrmse)
            all_pass = all_pass and passed
            by_source: dict[int, list[dict[str, Any]]] = {}
            for term_idx, c in zip(selected, coef):
                if abs(float(c)) <= 1e-12:
                    continue
                spec = dict(specs[term_idx])
                src = int(spec.pop("source_component"))
                by_source.setdefault(src, []).append({**spec, "coefficient": float(c)})
            for src, terms in sorted(by_source.items()):
                fitted_blocks.append({"row_component": out_component, "column_component": src, "terms": terms})
            output_certificates.append({
                "output_component": out_component,
                "selected_term_count": len(selected),
                "selected_term_indices": selected,
                "discovery_nrmse": discovery_error,
                "sealed_holdout_nrmse": holdout_error,
                "pass": passed,
                "search_history": history,
                "backward_pruning_history": pruning_history,
                "sealed_holdout_used_for_pruning": False,
            })

        program = {
            "program_type": "TYPED_LINEAR_OPERATOR_EIGENPROBLEM",
            "state": {
                "carrier": "MULTICOMPONENT_REAL_FIELD",
                "components": components,
                "grid": grid,
                "boundary": "DIRICHLET_ZERO_OUTSIDE_FROZEN_GRID",
            },
            "operator_blocks": fitted_blocks,
            "metric": {"kind": "IDENTITY"},
            "problem": {"kind": "STANDARD_EIGENPROBLEM", "default_eigenpair_count": min(6, max(1, components * 2))},
        }
        artifact_core = {
            "program": program,
            "probe_digest": probe_digest,
            "freeze_digest": freeze_digest,
            "fit_tolerance_nrmse": float(fit_tolerance_nrmse),
            "discovery_probe_count": len(discovery),
            "sealed_holdout_probe_count": len(holdout),
            "output_certificates": output_certificates,
            "grammar": self.contract()["candidate_grammar"],
        }
        artifact_digest = digest_payload(artifact_core)
        payload = {
            "schema": SCHEMA,
            "owner_id": SYNTHESIS_OWNER_ID,
            "status": "GENERATED_EXECUTABLE_OPERATOR_CANDIDATE" if all_pass else "OPERATOR_CANDIDATE_FAILS_SEALED_PROBE_GATE",
            "primitive_type": "GENERATED_TYPED_OPERATOR_PROGRAM",
            "candidate_id": "OP-" + artifact_digest[:16].upper(),
            "program": program,
            "probe_digest": probe_digest,
            "freeze_digest": freeze_digest,
            "fit_certificate": {
                "output_certificates": output_certificates,
                "all_outputs_pass": all_pass,
                "tolerance_nrmse": float(fit_tolerance_nrmse),
                "sealed_holdout_not_used_for_term_selection": True,
            },
            "qualified_for_compilation": all_pass,
            "claim_boundary": {
                "operator_identified_only_on_probe_evidence": True,
                "known_equation_name_selected": False,
                "known_solver_selected": False,
                "arbitrary_code_generated": False,
                "world_law_established": False,
                "scientific_novelty_established": False,
            },
        }
        return _with_digest(payload)


class TheoryToExecutableCompilerOwner:
    """Fail-closed lowering from frozen generated theory artifacts to executable IR."""

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": LOWERING_OWNER_ID,
            "accepted_input_kinds": (
                "GENERATED_FINITE_ALGEBRAIC_SIGNATURE",
                "GENERATED_TYPED_OPERATOR_PROGRAM",
            ),
            "required_outputs": (
                "state_schema", "boundary_contract", "numerical_algorithm",
                "error_estimator", "validity_contract",
            ),
            "arbitrary_code_generation": False,
            "known_solver_selection": False,
            "internet_prefreeze": "FORBIDDEN",
            "failure_status": "THEORY_NOT_EXECUTABLE",
        }

    @staticmethod
    def _fail(reason: str, *, source_digest: str = "") -> Mapping[str, Any]:
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": LOWERING_OWNER_ID,
            "status": "THEORY_NOT_EXECUTABLE",
            "reason": reason,
            "source_theory_digest": source_digest,
            "claim_boundary": {
                "executable_object_established": False,
                "world_theory_validity_established": False,
                "world_novelty_established": False,
            },
        })

    def _compile_finite(
        self,
        *,
        theory_artifact: Mapping[str, Any],
        theory_freeze_digest: str,
        controlled_limit_receipt: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        artifact_digest = str(theory_artifact.get("digest", ""))
        primitive = theory_artifact.get("primitive")
        if theory_artifact.get("status") != "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE" or not isinstance(primitive, Mapping):
            return self._fail("UNSUPPORTED_OR_UNQUALIFIED_FINITE_ARTIFACT", source_digest=artifact_digest)
        carrier = tuple(str(x) for x in primitive.get("carrier", ()))
        actions = tuple(str(x) for x in primitive.get("action_alphabet", ()))
        operations = primitive.get("operations", {})
        observe = operations.get("observe", {}) if isinstance(operations, Mapping) else {}
        update = operations.get("update", {}) if isinstance(operations, Mapping) else {}
        if not carrier or not actions or set(observe) != set(carrier) or set(update) != set(actions):
            return self._fail("INCOMPLETE_FINITE_SEMANTICS", source_digest=artifact_digest)
        for action in actions:
            table = update.get(action)
            if not isinstance(table, Mapping) or set(table) != set(carrier) or any(str(v) not in set(carrier) for v in table.values()):
                return self._fail("INCOMPLETE_OR_ESCAPING_FINITE_UPDATE", source_digest=artifact_digest)
        if controlled_limit_receipt is None:
            limit_binding: Mapping[str, Any] = {"status": "NOT_REQUIRED_FOR_EXACT_FINITE_LOWERING", "digest": ""}
        else:
            if controlled_limit_receipt.get("status") != "CONTROLLED_LIMIT_ESTABLISHED":
                return self._fail("SUPPLIED_CONTROLLED_LIMIT_NOT_ESTABLISHED", source_digest=artifact_digest)
            limit_binding = {
                "status": "BOUND_CONTROLLED_LIMIT",
                "selected_limit_direction": controlled_limit_receipt.get("selected_limit_direction"),
                "digest": controlled_limit_receipt.get("digest", ""),
            }
        return {
            "source_theory_digest": artifact_digest,
            "theory_freeze_digest": theory_freeze_digest,
            "lowering_class": "EXACT_FINITE_TRANSITION_ALGEBRA",
            "state_schema": {"kind": "FINITE_ENUMERATED_CARRIER", "states": list(carrier), "state_count": len(carrier)},
            "initialize": {"kind": "VALIDATED_STATE_IDENTITY_INITIALIZER", "requires_state_in_schema": True},
            "update": {"kind": "TOTAL_TYPED_TRANSITION_TABLE", "actions": list(actions), "table": {a: {s: str(update[a][s]) for s in carrier} for a in actions}},
            "observe": {"kind": "TOTAL_TYPED_OBSERVATION_TABLE", "table": {s: str(observe[s]) for s in carrier}},
            "boundary_contract": {"invalid_initial_state": "REJECT", "unknown_action": "REJECT", "partial_operator": "FORBIDDEN"},
            "numerical_algorithm": {"kind": "DETERMINISTIC_FINITE_TABLE_LOOKUP", "dynamic_code_generation": False},
            "error_estimator": {"owner_id": ERROR_OWNER_ID, "kind": "EXACT_FINITE_LOWERING_CERTIFICATE", "local_update_error_upper_bound": 0.0, "observation_error_upper_bound": 0.0, "roundoff_error_upper_bound": 0.0},
            "validity_contract": {"exact_for": "FROZEN_GENERATED_FINITE_PRIMITIVE_SEMANTICS_ONLY", "world_predictive_validity_inherited": False, "controlled_limit_binding": dict(limit_binding)},
        }

    def _compile_operator(self, *, theory_artifact: Mapping[str, Any], theory_freeze_digest: str) -> Mapping[str, Any]:
        artifact_digest = str(theory_artifact.get("digest", ""))
        if theory_artifact.get("status") not in {"GENERATED_EXECUTABLE_OPERATOR_CANDIDATE", "GENERATED_SELF_CONSISTENT_EXECUTABLE_OPERATOR_CANDIDATE"} or theory_artifact.get("qualified_for_compilation") is not True:
            return self._fail("OPERATOR_CANDIDATE_NOT_QUALIFIED", source_digest=artifact_digest)
        program = theory_artifact.get("program")
        if not isinstance(program, Mapping) or program.get("program_type") != "TYPED_LINEAR_OPERATOR_EIGENPROBLEM":
            return self._fail("UNSUPPORTED_OPERATOR_PROGRAM_TYPE", source_digest=artifact_digest)
        state = program.get("state", {})
        try:
            components = int(state["components"])
            grid = [float(v) for v in state["grid"]]
            _uniform_grid_matrices(grid)
        except Exception as exc:
            return self._fail(f"INVALID_OPERATOR_STATE_SCHEMA:{exc}", source_digest=artifact_digest)
        if components < 1:
            return self._fail("EMPTY_OPERATOR_COMPONENT_SCHEMA", source_digest=artifact_digest)
        blocks = []
        for block in program.get("operator_blocks", ()):  # validate every executable term
            row = int(block["row_component"]); col = int(block["column_component"])
            if not (0 <= row < components and 0 <= col < components):
                return self._fail("OPERATOR_BLOCK_OUTSIDE_COMPONENT_SCHEMA", source_digest=artifact_digest)
            terms = []
            for term in block.get("terms", ()):
                kind = str(term.get("kind", "")); power = int(term.get("power", 0)); coefficient = float(term.get("coefficient", float("nan")))
                if kind not in {"IDENTITY", "FIRST_DERIVATIVE", "SECOND_DERIVATIVE", "COORDINATE_POWER", "FIELD_MULTIPLICATION"} or not math.isfinite(coefficient):
                    return self._fail("UNSUPPORTED_OR_NONFINITE_OPERATOR_TERM", source_digest=artifact_digest)
                if kind == "FIELD_MULTIPLICATION":
                    field_id = str(term.get("field_id", "")).strip()
                    if not field_id:
                        return self._fail("FIELD_MULTIPLICATION_REQUIRES_FIELD_ID", source_digest=artifact_digest)
                    terms.append({"kind": kind, "power": 0, "coefficient": coefficient, "field_id": field_id})
                else:
                    try:
                        x, d1, d2 = _uniform_grid_matrices(grid); _basis_matrix(kind, x, d1, d2, power)
                    except Exception as exc:
                        return self._fail(f"INVALID_OPERATOR_TERM:{exc}", source_digest=artifact_digest)
                    terms.append({"kind": kind, "power": power, "coefficient": coefficient})
            blocks.append({"row_component": row, "column_component": col, "terms": terms})
        problem = dict(program.get("problem", {}))
        if problem.get("kind") not in {"STANDARD_EIGENPROBLEM", "GENERALIZED_EIGENPROBLEM", "SELF_CONSISTENT_EIGENPROBLEM"}:
            return self._fail("UNSUPPORTED_OPERATOR_PROBLEM_CLASS", source_digest=artifact_digest)
        metric = dict(program.get("metric", {"kind": "IDENTITY"}))
        if metric.get("kind") != "IDENTITY" and not isinstance(metric.get("operator_blocks"), Sequence):
            return self._fail("INVALID_GENERALIZED_METRIC", source_digest=artifact_digest)
        fit = dict(theory_artifact.get("fit_certificate", {}))
        return {
            "source_theory_digest": artifact_digest,
            "theory_freeze_digest": theory_freeze_digest,
            "lowering_class": "TYPED_CONTINUOUS_OPERATOR_PROGRAM",
            "state_schema": {"kind": "MULTICOMPONENT_REAL_FIELD_ON_UNIFORM_1D_GRID", "components": components, "grid": grid, "points": len(grid)},
            "operator": {"blocks": blocks},
            "metric": metric,
            "problem": problem,
            "boundary_contract": {"kind": str(state.get("boundary", "DIRICHLET_ZERO_OUTSIDE_FROZEN_GRID")), "outside_grid": "ZERO", "grid_change_requires_recompile": True},
            "numerical_algorithm": {"kind": "DETERMINISTIC_TYPED_MATRIX_ASSEMBLY_AND_EIGENSOLVE", "dynamic_code_generation": False, "named_solver_selected_from_domain": False},
            "error_estimator": {"owner_id": ERROR_OWNER_ID, "kind": "EIGEN_RESIDUAL_PLUS_SEALED_OPERATOR_PROBE_ERROR", "sealed_operator_fit": fit},
            "validity_contract": {"exact_for": "FROZEN_TYPED_OPERATOR_PROGRAM_ON_FROZEN_GRID", "world_predictive_validity_inherited": False, "world_novelty_inherited": False, "probe_digest": theory_artifact.get("probe_digest")},
        }

    def compile(
        self,
        *,
        theory_artifact: Mapping[str, Any],
        theory_freeze_digest: str,
        controlled_limit_receipt: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if not theory_freeze_digest:
            return self._fail("MISSING_THEORY_FREEZE_DIGEST")
        artifact_digest = str(theory_artifact.get("digest", ""))
        if not artifact_digest:
            return self._fail("MISSING_SOURCE_THEORY_DIGEST")
        primitive_type = str(theory_artifact.get("primitive_type", ""))
        if primitive_type == "GENERATED_FINITE_ALGEBRAIC_SIGNATURE":
            ir_core = self._compile_finite(theory_artifact=theory_artifact, theory_freeze_digest=theory_freeze_digest, controlled_limit_receipt=controlled_limit_receipt)
        elif primitive_type == "GENERATED_TYPED_OPERATOR_PROGRAM":
            if controlled_limit_receipt is not None and controlled_limit_receipt.get("status") != "CONTROLLED_LIMIT_ESTABLISHED":
                return self._fail("SUPPLIED_CONTROLLED_LIMIT_NOT_ESTABLISHED", source_digest=artifact_digest)
            ir_core = self._compile_operator(theory_artifact=theory_artifact, theory_freeze_digest=theory_freeze_digest)
        else:
            return self._fail("UNSUPPORTED_OR_UNQUALIFIED_THEORY_ARTIFACT", source_digest=artifact_digest)
        if ir_core.get("status") == "THEORY_NOT_EXECUTABLE":
            return ir_core
        executable_id = "E-" + digest_payload(ir_core)[:16].upper()
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": LOWERING_OWNER_ID,
            "status": "THEORY_EXECUTABLE_COMPILED",
            "executable_id": executable_id,
            "executable_ir": ir_core,
            "claim_boundary": {
                "executable_object_established": True,
                "arbitrary_code_generated": False,
                "known_solver_selected": False,
                "internet_used_prefreeze": False,
                "world_theory_validity_established": False,
                "world_novelty_established": False,
            },
        })


class ExecutableTheoryRuntimeOwner:
    """Interpret only compiler-produced typed IR; no eval/exec or generated source."""

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": EXECUTOR_OWNER_ID,
            "accepted_schema": SCHEMA,
            "dynamic_eval": False,
            "dynamic_exec": False,
            "execution_modes": ("DETERMINISTIC_FINITE_INTERPRETATION", "DETERMINISTIC_TYPED_OPERATOR_EIGENSOLVE"),
        }

    @staticmethod
    def _validate(compiled: Mapping[str, Any]) -> Mapping[str, Any]:
        if compiled.get("status") != "THEORY_EXECUTABLE_COMPILED" or compiled.get("schema") != SCHEMA:
            raise ValueError("runtime accepts only qualified compiled executable IR")
        expected_digest = _digest({k: v for k, v in compiled.items() if k != "digest"})
        if expected_digest != compiled.get("digest"):
            raise ValueError("compiled executable digest mismatch")
        return compiled["executable_ir"]

    @staticmethod
    def _assemble_blocks(
        *, grid: Sequence[float], components: int, blocks: Sequence[Mapping[str, Any]], fields: Mapping[str, np.ndarray] | None = None,
    ) -> np.ndarray:
        x, d1, d2 = _uniform_grid_matrices(grid)
        n = len(x); matrix = np.zeros((components * n, components * n), dtype=float)
        for block in blocks:
            row = int(block["row_component"]); col = int(block["column_component"])
            local = np.zeros((n, n), dtype=float)
            for term in block.get("terms", ()):
                if str(term["kind"]) == "FIELD_MULTIPLICATION":
                    if fields is None or str(term.get("field_id")) not in fields:
                        raise ValueError(f"missing runtime field {term.get('field_id')!r}")
                    field = np.asarray(fields[str(term.get("field_id"))], dtype=float)
                    if field.shape != (n,) or not np.all(np.isfinite(field)):
                        raise ValueError("runtime field shape/value mismatch")
                    basis = np.diag(field)
                else:
                    basis = _basis_matrix(str(term["kind"]), x, d1, d2, int(term.get("power", 0)))
                local += float(term["coefficient"]) * basis
            matrix[row*n:(row+1)*n, col*n:(col+1)*n] += local
        return matrix

    @staticmethod
    def _eigensolve(ir: Mapping[str, Any], *, eigenpair_count: int, fields: Mapping[str, np.ndarray] | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        state = ir["state_schema"]; components = int(state["components"]); grid = state["grid"]
        A = ExecutableTheoryRuntimeOwner._assemble_blocks(grid=grid, components=components, blocks=ir["operator"]["blocks"], fields=fields)
        metric = ir.get("metric", {"kind": "IDENTITY"})
        if metric.get("kind") == "IDENTITY":
            B = np.eye(A.shape[0], dtype=float)
        else:
            B = ExecutableTheoryRuntimeOwner._assemble_blocks(grid=grid, components=components, blocks=metric.get("operator_blocks", ()), fields=fields)
        sym_a = float(np.linalg.norm(A - A.T) / max(np.linalg.norm(A), 1e-12))
        sym_b = float(np.linalg.norm(B - B.T) / max(np.linalg.norm(B), 1e-12))
        count = max(1, min(int(eigenpair_count), A.shape[0]))
        if sym_a <= 1e-10 and sym_b <= 1e-10:
            try:
                values, vectors = linalg.eigh(A, B, check_finite=False)
            except Exception:
                values, vectors = linalg.eig(A, B, check_finite=False)
        else:
            values, vectors = linalg.eig(A, B, check_finite=False)
        order = sorted(range(len(values)), key=lambda i: (abs(float(np.imag(values[i]))), float(np.real(values[i])), i))[:count]
        vals = np.asarray([values[i] for i in order], dtype=complex)
        vecs = np.column_stack([vectors[:, i] for i in order]).astype(complex)
        residuals = []
        for val, vec in zip(vals, vecs.T):
            num = np.linalg.norm(A @ vec - val * (B @ vec))
            den = max(np.linalg.norm(A @ vec) + abs(val) * np.linalg.norm(B @ vec), 1e-12)
            residuals.append(float(num / den))
        return vals, vecs, np.asarray(residuals, dtype=float)

    def execute(
        self,
        *,
        compiled: Mapping[str, Any],
        initial_state: str | None = None,
        actions: Sequence[str] = (),
        runtime_request: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ir = self._validate(compiled)
        if ir.get("lowering_class") == "EXACT_FINITE_TRANSITION_ALGEBRA":
            states = set(str(x) for x in ir["state_schema"]["states"])
            if initial_state is None or str(initial_state) not in states:
                raise ValueError("initial state outside compiled state schema")
            transition = ir["update"]["table"]; observe = ir["observe"]["table"]
            state = str(initial_state)
            trace = [{"step": 0, "state": state, "observation": str(observe[state]), "action": None}]
            for idx, raw_action in enumerate(actions, 1):
                action = str(raw_action)
                if action not in transition:
                    raise ValueError(f"unknown compiled action: {action}")
                state = str(transition[action][state])
                trace.append({"step": idx, "state": state, "observation": str(observe[state]), "action": action})
            return _with_digest({
                "schema": "phi-theory-execution-receipt/v2", "owner_id": EXECUTOR_OWNER_ID,
                "status": "EXECUTION_PASS", "execution_class": "FINITE_TRANSITION_ALGEBRA",
                "executable_id": compiled["executable_id"], "compiled_digest": compiled["digest"],
                "initial_state": str(initial_state), "actions": [str(x) for x in actions],
                "final_state": state, "trace": trace, "error_estimate": dict(ir["error_estimator"]),
                "claim_boundary": {"world_prediction_validated": False, "execution_matches_compiled_semantics": True},
            })

        if ir.get("lowering_class") != "TYPED_CONTINUOUS_OPERATOR_PROGRAM":
            raise ValueError("unknown compiled lowering class")
        request = dict(runtime_request or {})
        count = int(request.get("eigenpair_count", ir.get("problem", {}).get("default_eigenpair_count", 4)))
        problem = dict(ir.get("problem", {}))
        fixed_point_receipt = None
        if problem.get("kind") == "SELF_CONSISTENT_EIGENPROBLEM":
            fp = dict(problem.get("fixed_point", {}))
            max_iterations = max(1, int(fp.get("max_iterations", 64)))
            tolerance = max(0.0, float(fp.get("tolerance", 1e-8)))
            mixing = min(1.0, max(1e-6, float(fp.get("mixing", 0.35))))
            occupied = max(1, int(request.get("occupied_eigenpair_count", fp.get("occupied_eigenpair_count", 1))))
            grid = np.asarray(ir["state_schema"]["grid"], dtype=float)
            _, _, d2 = _uniform_grid_matrices(grid)
            fields: dict[str, np.ndarray] = {}
            for spec in fp.get("field_updates", ()):
                fid = str(spec.get("field_id", "")).strip()
                if not fid:
                    raise ValueError("fixed-point field update requires field_id")
                initial = spec.get("initial", 0.0)
                if isinstance(initial, Sequence) and not isinstance(initial, (str, bytes)):
                    arr = np.asarray(initial, dtype=float)
                    if arr.shape != (len(grid),):
                        raise ValueError("fixed-point initial field shape mismatch")
                    fields[fid] = arr.copy()
                else:
                    fields[fid] = np.full(len(grid), float(initial), dtype=float)
            history = []
            converged = False
            values = vectors = residuals = None
            for iteration in range(1, max_iterations + 1):
                values, vectors, residuals = self._eigensolve(ir, eigenpair_count=max(count, occupied), fields=fields)
                density = np.zeros(len(grid), dtype=float)
                components = int(ir["state_schema"]["components"]); points = int(ir["state_schema"]["points"])
                for vec in vectors[:, :min(occupied, vectors.shape[1])].T:
                    for comp in range(components):
                        section = vec[comp*points:(comp+1)*points]
                        density += np.square(section.real) + np.square(section.imag)
                if np.max(density) > 0:
                    density = density / max(float(np.trapezoid(density, grid)), 1e-12)
                next_fields: dict[str, np.ndarray] = {}
                for spec in fp.get("field_updates", ()):
                    fid = str(spec["field_id"]); kind = str(spec.get("kind", "DENSITY_POWER"))
                    scale = float(spec.get("scale", 1.0)); offset = float(spec.get("offset", 0.0))
                    if kind == "DENSITY_POWER":
                        power = float(spec.get("power", 1.0))
                        target = offset + scale * np.power(np.maximum(density, 0.0), power)
                    elif kind == "POISSON_RESPONSE":
                        regularization = max(0.0, float(spec.get("regularization", 1e-8)))
                        matrix = -d2 + regularization * np.eye(len(grid))
                        if bool(spec.get("occupancy_affine", False)):
                            effective_scale = scale * float(occupied) + float(spec.get("occupied_count_intercept", 0.0))
                        else:
                            effective_scale = scale
                        target = linalg.solve(matrix, effective_scale * density, assume_a="sym") + offset
                    else:
                        raise ValueError(f"unsupported fixed-point field update {kind!r}")
                    next_fields[fid] = (1.0 - mixing) * fields[fid] + mixing * np.asarray(target, dtype=float)
                field_residual = max([
                    float(np.linalg.norm(next_fields[fid] - fields[fid]) / max(np.linalg.norm(next_fields[fid]), 1e-12))
                    for fid in next_fields
                ] or [0.0])
                history.append({"iteration": iteration, "field_residual": field_residual, "max_eigen_residual": float(np.max(residuals)) if len(residuals) else None})
                fields = next_fields
                if field_residual <= tolerance:
                    converged = True
                    break
            assert values is not None and vectors is not None and residuals is not None
            fixed_point_receipt = {
                "status": "FIXED_POINT_CONVERGED" if converged else "FIXED_POINT_RESIDUAL_NOT_CONVERGED",
                "iterations": len(history), "tolerance": tolerance, "history": history,
                "field_digests": {k: digest_payload([float(v) for v in arr]) for k, arr in sorted(fields.items())},
            }
        else:
            values, vectors, residuals = self._eigensolve(ir, eigenpair_count=count)
        state = ir["state_schema"]; components = int(state["components"]); points = int(state["points"])
        eigenpairs = []
        for idx, (value, vector, residual) in enumerate(zip(values, vectors.T, residuals)):
            parts = []
            for comp in range(components):
                section = vector[comp*points:(comp+1)*points]
                parts.append({"real": [float(v.real) for v in section], "imag": [float(v.imag) for v in section]})
            eigenpairs.append({
                "rank": idx, "eigenvalue_real": float(value.real), "eigenvalue_imag": float(value.imag),
                "relative_eigen_residual": float(residual), "components": parts,
            })
        return _with_digest({
            "schema": "phi-theory-execution-receipt/v2", "owner_id": EXECUTOR_OWNER_ID,
            "status": "EXECUTION_PASS", "execution_class": "TYPED_CONTINUOUS_OPERATOR_PROGRAM",
            "executable_id": compiled["executable_id"], "compiled_digest": compiled["digest"],
            "eigenpairs": eigenpairs,
            "max_relative_eigen_residual": float(np.max(residuals)) if len(residuals) else None,
            "fixed_point": fixed_point_receipt,
            "error_estimate": dict(ir["error_estimator"]),
            "claim_boundary": {
                "world_prediction_validated": False,
                "execution_matches_compiled_semantics": True,
                "eigenproblem_solution_is_world_law": False,
            },
        })


class PrimitiveFieldOperatorCoordinateBirthOwner:
    """Birth typed local operator coordinates directly from primitive sampled fields.

    The owner is deliberately equation-agnostic.  It receives coordinate charts,
    sampled fields and dimensions; it is not given named PDE terms or a target
    formula.  In current research mode it executes a frozen operator language
    generated upstream by Mathematical Invention from translation/algebra
    meta-primitives.  The older differential grammar remains compatibility-only
    for replaying Level-2 receipts.  The resulting coordinates are research-local
    candidates, not world laws.
    """

    owner_id = PRIMITIVE_FIELD_OPERATOR_BIRTH_OWNER_ID
    stencil_radius = 3

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "PRIMITIVE_COORDINATE_CHARTS_PLUS_SAMPLED_FIELDS_PLUS_DIMENSIONS",
            "output": "ATLAS_BORN_TYPED_LOCAL_OPERATOR_COORDINATES",
            "known_equation_name_required": False,
            "named_pde_term_catalog_used": False,
            "derivative_values_may_be_supplied_by_caller": False,
            "derivatives_born_from_sampled_fields": True,
            "fixed_operator_axis_count": None,
            "primary_research_mode": "MATHEMATICAL_INVENTION_GENERATED_OPERATOR_LANGUAGE",
            "generated_operator_language_input_supported": True,
            "predeclared_differential_grammar_required_in_primary_mode": False,
            "legacy_level2_grammar_compatibility_only": (
                "FIRST_DERIVATIVE",
                "SECOND_SPATIAL_DERIVATIVE",
                "FIELD_TIMES_TARGET_DERIVATIVE",
                "RECIPROCAL_FIELD_TIMES_OTHER_FIELD_GRADIENT",
            ),
            "claim_boundary": {
                "born_coordinate_is_scientific_law": False,
                "numerical_derivative_is_independent_measurement": False,
                "world_novelty_established": False,
            },
        }

    @staticmethod
    def _dim(v: Sequence[float]) -> tuple[float, ...]:
        row = tuple(float(x) for x in v)
        if len(row) != 7:
            raise ValueError("primitive-field dimensions must have seven base exponents")
        return row

    @staticmethod
    def _dadd(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
        return tuple(float(x) + float(y) for x, y in zip(a, b))

    @staticmethod
    def _dsub(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
        return tuple(float(x) - float(y) for x, y in zip(a, b))

    @staticmethod
    def _dscale(a: Sequence[float], k: float) -> tuple[float, ...]:
        return tuple(float(k) * float(x) for x in a)

    @staticmethod
    def _deq(a: Sequence[float], b: Sequence[float], tol: float = 1e-12) -> bool:
        return all(abs(float(x)-float(y)) <= tol for x, y in zip(a, b))

    @staticmethod
    def _fd_weights(order: int, radius: int = 3) -> np.ndarray:
        offsets = np.arange(-radius, radius + 1, dtype=float)
        powers = np.arange(len(offsets), dtype=int)
        matrix = np.vstack([np.power(offsets, int(k)) for k in powers])
        rhs = np.zeros(len(offsets), dtype=float)
        rhs[int(order)] = float(math.factorial(int(order)))
        return np.linalg.solve(matrix, rhs)

    @classmethod
    def _differentiate(cls, values: np.ndarray, coordinate: Sequence[float], axis: int, order: int) -> np.ndarray:
        x = np.asarray(coordinate, dtype=float)
        if x.ndim != 1 or len(x) < 2 * cls.stencil_radius + 1 or not np.all(np.isfinite(x)):
            raise ValueError("each primitive coordinate needs at least seven finite samples")
        dx = np.diff(x)
        h = float(np.mean(dx))
        if h <= 0 or not np.allclose(dx, h, rtol=1e-8, atol=max(1e-12, abs(h)*1e-10)):
            raise ValueError("primitive-field birth currently requires strictly increasing uniform coordinates")
        w = cls._fd_weights(order, cls.stencil_radius) / (h ** int(order))
        out = np.full_like(values, np.nan, dtype=float)
        dst = [slice(None)] * values.ndim
        dst[axis] = slice(cls.stencil_radius, values.shape[axis]-cls.stencil_radius)
        acc = np.zeros(tuple(values[tuple(dst)].shape), dtype=float)
        for off, coef in zip(range(-cls.stencil_radius, cls.stencil_radius + 1), w):
            src = [slice(None)] * values.ndim
            start = cls.stencil_radius + off
            stop = values.shape[axis] - cls.stencil_radius + off
            src[axis] = slice(start, stop)
            acc += float(coef) * values[tuple(src)]
        out[tuple(dst)] = acc
        return out

    @staticmethod
    def _axis_id(spec: Mapping[str, Any]) -> str:
        return "pf_" + digest_payload(dict(spec))[:16]

    def discover(
        self,
        *,
        studies: Sequence[Mapping[str, Any]],
        coordinate_dimensions: Mapping[str, Sequence[float]],
        field_dimensions: Mapping[str, Sequence[float]],
        target_field: str,
        operator_language: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        rows = [dict(x) for x in studies]
        if not rows:
            raise ValueError("primitive-field discovery requires studies")
        cdim = {str(k): self._dim(v) for k, v in coordinate_dimensions.items()}
        fdim = {str(k): self._dim(v) for k, v in field_dimensions.items()}
        target_field = str(target_field)
        if target_field not in fdim:
            raise ValueError("target_field is missing from field_dimensions")
        time_dim = (0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        length_dim = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        time_coords = [name for name, dim in cdim.items() if self._deq(dim, time_dim)]
        spatial_coords = [name for name, dim in cdim.items() if self._deq(dim, length_dim)]
        if len(time_coords) != 1 or not spatial_coords:
            raise ValueError("primitive-field birth requires exactly one time-like and at least one length-like coordinate")
        time_coord = time_coords[0]
        target_dim = self._dsub(fdim[target_field], cdim[time_coord])

        language = dict(operator_language or {})
        generated_language_mode = language.get("status") == "GENERATED_OPERATOR_LANGUAGE"
        if generated_language_mode:
            # Mathematical Invention supplies frozen signatures generated from
            # translation/algebra meta-primitives. This owner executes them only.
            specs = [dict(x) for x in language.get("generated_signatures", ())]
            target_spec = dict(language.get("target_action") or {})
            if not specs or not target_spec:
                raise ValueError("generated operator language did not provide executable signatures")
            if str(target_spec.get("response_field")) != target_field or str(target_spec.get("coordinate")) != time_coord:
                raise ValueError("generated target action is incompatible with primitive-field request")
        else:
            # Level-2 compatibility path. New Level-3 research must use the
            # generated-language route above rather than this typed grammar.
            specs: list[dict[str, Any]] = []
            for coord in spatial_coords:
                d1_dim = self._dsub(fdim[target_field], cdim[coord])
                d2_dim = self._dsub(fdim[target_field], self._dscale(cdim[coord], 2.0))
                for carrier, carrier_dim in fdim.items():
                    prod1_dim = self._dadd(carrier_dim, d1_dim)
                    if self._deq(prod1_dim, target_dim):
                        specs.append({"kind":"FIELD_TIMES_TARGET_D1","carrier_field":carrier,"target_field":target_field,"coordinate":coord,"dimension":list(target_dim)})
                    prod2_dim = self._dadd(carrier_dim, d2_dim)
                    if self._deq(prod2_dim, target_dim):
                        specs.append({"kind":"FIELD_TIMES_TARGET_D2","carrier_field":carrier,"target_field":target_field,"coordinate":coord,"dimension":list(target_dim)})
                for other, other_dim in fdim.items():
                    grad_dim = self._dsub(other_dim, cdim[coord])
                    for carrier, carrier_dim in fdim.items():
                        inv_prod_dim = self._dadd(self._dscale(carrier_dim, -1.0), grad_dim)
                        if self._deq(inv_prod_dim, target_dim):
                            specs.append({"kind":"RECIPROCAL_FIELD_TIMES_OTHER_D1","carrier_field":carrier,"other_field":other,"coordinate":coord,"dimension":list(target_dim)})
            target_spec = {"kind":"TARGET_TIME_D1","field":target_field,"coordinate":time_coord,"dimension":list(target_dim)}
        unique = {digest_payload(spec): spec for spec in specs}
        specs = [unique[k] for k in sorted(unique)]
        spec_by_axis = {self._axis_id(spec): spec for spec in specs}
        target_axis = "pf_target_" + digest_payload(target_spec)[:16]

        discovery_obs: list[dict[str, Any]] = []
        sealed_obs: list[dict[str, Any]] = []
        study_receipts: list[dict[str, Any]] = []
        for study_index, study in enumerate(rows):
            sid = str(study.get("study_id", f"PF-STUDY-{study_index:03d}"))
            role = str(study.get("role", "DISCOVERY")).upper()
            order = [str(x) for x in study.get("coordinate_order", ())]
            coords = {str(k): [float(v) for v in vals] for k, vals in dict(study.get("coordinates", {})).items()}
            fields = {str(k): np.asarray(v, dtype=float) for k, v in dict(study.get("fields", {})).items()}
            if set(order) != set(cdim) or not order:
                raise ValueError(f"study {sid}: coordinate_order must contain every declared coordinate exactly once")
            expected_shape = tuple(len(coords[name]) for name in order)
            if any(name not in coords for name in order):
                raise ValueError(f"study {sid}: coordinate values missing")
            for field_name in fdim:
                if field_name not in fields or fields[field_name].shape != expected_shape or not np.all(np.isfinite(fields[field_name])):
                    raise ValueError(f"study {sid}: field {field_name!r} must have finite shape {expected_shape}")
            coord_axis = {name: order.index(name) for name in order}
            interior = tuple(slice(self.stencil_radius, n-self.stencil_radius) for n in expected_shape)
            feature_arrays: dict[str,np.ndarray] = {}
            if generated_language_mode:
                actions: dict[tuple[str,str,int],np.ndarray] = {}
                needed={(str(target_spec["response_field"]),str(target_spec["coordinate"]),int(target_spec["moment_rank"]))}
                for spec in specs:
                    needed.add((str(spec["response_field"]),str(spec["coordinate"]),int(spec["moment_rank"])))
                for field_name,coord,rank in sorted(needed):
                    if rank > 2*self.stencil_radius:
                        raise ValueError("generated translation-moment rank exceeds current executable stencil resource")
                    actions[(field_name,coord,rank)] = self._differentiate(fields[field_name],coords[coord],coord_axis[coord],rank)
                target_values=actions[(str(target_spec["response_field"]),str(target_spec["coordinate"]),int(target_spec["moment_rank"]))][interior]
                for axis_id,spec in spec_by_axis.items():
                    response=actions[(str(spec["response_field"]),str(spec["coordinate"]),int(spec["moment_rank"]))]
                    factors=spec.get("carrier_factors")
                    if isinstance(factors,(list,tuple)) and factors:
                        arr=np.asarray(response,dtype=float).copy()
                        invalid=False
                        for factor in factors:
                            field_name=str(dict(factor).get("field",""))
                            power=int(dict(factor).get("power",0))
                            if field_name not in fields or power==0:
                                invalid=True; break
                            base=fields[field_name]
                            if power < 0 and np.any(np.abs(base[interior])<=1e-14):
                                invalid=True; break
                            arr=arr*np.power(base,power)
                        if invalid:
                            arr=np.full_like(response,np.nan,dtype=float)
                    else:
                        carrier=spec.get("carrier_field"); power=int(spec.get("carrier_power",0))
                        if carrier is None or power==0:
                            arr=response
                        elif power==1:
                            arr=fields[str(carrier)]*response
                        elif power==-1:
                            base=fields[str(carrier)]
                            if np.any(np.abs(base[interior])<=1e-14):
                                arr=np.full_like(base,np.nan,dtype=float)
                            else:
                                arr=response/base
                        else:
                            # Repeated pointwise multiplication/reciprocal is a
                            # composition of seed algebra operations, not a new
                            # scientific primitive.
                            base=fields[str(carrier)]
                            if power < 0 and np.any(np.abs(base[interior])<=1e-14):
                                arr=np.full_like(base,np.nan,dtype=float)
                            else:
                                arr=response*np.power(base,power)
                    feature_arrays[axis_id]=arr[interior]
            else:
                d1: dict[tuple[str,str], np.ndarray] = {}
                d2: dict[tuple[str,str], np.ndarray] = {}
                needed_d1 = {(target_field,time_coord)}
                needed_d2 = set()
                for spec in specs:
                    coord = str(spec["coordinate"]); kind = str(spec["kind"])
                    if kind == "FIELD_TIMES_TARGET_D1": needed_d1.add((target_field,coord))
                    elif kind == "FIELD_TIMES_TARGET_D2": needed_d2.add((target_field,coord))
                    elif kind == "RECIPROCAL_FIELD_TIMES_OTHER_D1": needed_d1.add((str(spec["other_field"]),coord))
                for field_name, coord in sorted(needed_d1):
                    d1[(field_name,coord)] = self._differentiate(fields[field_name], coords[coord], coord_axis[coord], 1)
                for field_name, coord in sorted(needed_d2):
                    d2[(field_name,coord)] = self._differentiate(fields[field_name], coords[coord], coord_axis[coord], 2)
                target_values = d1[(target_field,time_coord)][interior]
                for axis_id, spec in spec_by_axis.items():
                    kind = str(spec["kind"]); coord = str(spec["coordinate"]); carrier = str(spec["carrier_field"])
                    if kind == "FIELD_TIMES_TARGET_D1":
                        arr = fields[carrier] * d1[(target_field,coord)]
                    elif kind == "FIELD_TIMES_TARGET_D2":
                        arr = fields[carrier] * d2[(target_field,coord)]
                    elif kind == "RECIPROCAL_FIELD_TIMES_OTHER_D1":
                        base = fields[carrier]
                        if np.any(np.abs(base[interior]) <= 1e-14):
                            arr = np.full_like(base, np.nan, dtype=float)
                        else:
                            arr = d1[(str(spec["other_field"]),coord)] / base
                    else:
                        raise ValueError(f"unsupported primitive operation {kind!r}")
                    feature_arrays[axis_id] = arr[interior]
            flat_target = target_values.reshape(-1)
            flat_features = {k:v.reshape(-1) for k,v in feature_arrays.items()}
            valid = np.isfinite(flat_target)
            for arr in flat_features.values(): valid &= np.isfinite(arr)
            kept = np.flatnonzero(valid)
            bucket = sealed_obs if role == "SEALED_HOLDOUT" else discovery_obs
            for local_index in kept:
                values = {target_axis: float(flat_target[local_index])}
                values.update({axis_id: float(arr[local_index]) for axis_id, arr in flat_features.items()})
                bucket.append({"record_id":f"{sid}-{int(local_index):06d}","study_id":sid,"values":values})
            study_receipts.append({
                "study_id":sid,"role":role,"shape":list(expected_shape),"interior_record_count":int(len(kept)),
                "primitive_field_digest":digest_payload({k:np.asarray(v,dtype=float).tolist() for k,v in sorted(fields.items())}),
            })

        variable_dimensions = {target_axis:list(target_dim), **{axis_id:list(target_dim) for axis_id in spec_by_axis}}
        core = {
            "schema":"phi-primitive-field-operator-birth/v1",
            "owner_id":self.owner_id,
            "status":"PRIMITIVE_FIELD_OPERATOR_COORDINATES_BORN",
            "target_field":target_field,
            "inferred_time_coordinate":time_coord,
            "inferred_spatial_coordinates":spatial_coords,
            "target_axis":target_axis,
            "target_operation":target_spec,
            "operator_language_mode":"INVENTED_FROM_META_PRIMITIVES" if generated_language_mode else "LEGACY_TYPED_DIFFERENTIAL_GRAMMAR",
            "operator_language_birth":language if generated_language_mode else None,
            "candidate_axis_count":len(spec_by_axis),
            "candidate_axes":{axis_id:spec for axis_id,spec in sorted(spec_by_axis.items())},
            "variable_dimensions":variable_dimensions,
            "discovery_observation_count":len(discovery_obs),
            "sealed_observation_count":len(sealed_obs),
            "discovery_observations":discovery_obs,
            "sealed_holdout_observations":sealed_obs,
            "study_receipts":study_receipts,
            "claim_boundary":{
                "caller_supplied_derived_derivative_values":False,
                "caller_supplied_named_pde_terms":False,
                "operator_coordinates_generated_inside_atlas_owner":True,
                "operator_coordinate_is_scientific_law":False,
                "sealed_holdout_used_to_generate_candidate_grammar":False,
                "named_differential_operator_catalog_used":False if generated_language_mode else None,
                "fixed_derivative_order_catalog_used":False if generated_language_mode else None,
                "operator_language_generated_by_mathematical_invention":bool(generated_language_mode),
            },
        }
        return _with_digest(core)


class TheoryCompilerKernel:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.probe_design = OperatorProbeDesignOwner()
        self.primitive_field_birth = PrimitiveFieldOperatorCoordinateBirthOwner()
        self.atomic_world_interaction = AtomicReferenceWorldInteractionOwner(self.root)
        self.variable_particle_probe_design = VariableParticleProbeDesignOwner()
        self.variable_particle_world_interaction = AtomicVariableParticleReferenceWorldInteractionOwner(self.root, self.atomic_world_interaction)
        self.synthesis = ExecutableRepresentationSynthesisOwner()
        self.self_consistent_synthesis = SelfConsistentRepresentationSynthesisOwner()
        self.many_body_probe_design = ManyBodyOperatorProbeDesignOwner()
        self.atomic_many_body_world_interaction = AtomicManyBodyReferenceWorldInteractionOwner()
        self.many_body_coordinate_synthesis = ManyBodyOperatorCoordinateSynthesisOwner()
        self.compiler = TheoryToExecutableCompilerOwner()
        self.runtime = ExecutableTheoryRuntimeOwner()

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": KERNEL_OWNER_ID,
            "probe_design_owner": self.probe_design.contract(),
            "primitive_field_operator_birth_owner": self.primitive_field_birth.contract(),
            "atomic_world_interaction_owner": self.atomic_world_interaction.contract(),
            "variable_particle_probe_design_owner": self.variable_particle_probe_design.contract(),
            "variable_particle_world_interaction_owner": self.variable_particle_world_interaction.contract(),
            "synthesis_owner": self.synthesis.contract(),
            "self_consistent_synthesis_owner": self.self_consistent_synthesis.contract(),
            "many_body_probe_design_owner": self.many_body_probe_design.contract(),
            "atomic_many_body_world_interaction_owner": self.atomic_many_body_world_interaction.contract(),
            "many_body_coordinate_synthesis_owner": self.many_body_coordinate_synthesis.contract(),
            "lowering_owner": self.compiler.contract(),
            "runtime_owner": self.runtime.contract(),
            "input_source": "FROZEN_INTERNAL_PHI_THEORY_OR_TYPED_OPERATOR_PROBES",
            "internet_prefreeze": "FORBIDDEN",
            "representation_policy": {
                "finite_state_only": False,
                "continuous_operator_programs_supported": True,
                "generalized_eigenproblem_supported": True,
                "self_consistent_problem_schema_supported": True,
                "fermionic_many_body_operator_coordinate_discovery_supported": True,
                "known_law_name_required": False,
                "generated_source_code_allowed": False,
            },
            "claim_boundary": {
                "compilation_implies_world_truth": False,
                "compilation_implies_world_novelty": False,
                "operator_probe_fit_implies_scientific_law": False,
                "arbitrary_code_generation": False,
            },
        }


__all__ = [
    "TheoryCompilerKernel", "OperatorProbeDesignOwner", "PrimitiveFieldOperatorCoordinateBirthOwner", "AtomicReferenceWorldInteractionOwner",
    "VariableParticleProbeDesignOwner", "AtomicVariableParticleReferenceWorldInteractionOwner",
    "ExecutableRepresentationSynthesisOwner", "SelfConsistentRepresentationSynthesisOwner",
    "ManyBodyOperatorProbeDesignOwner", "AtomicManyBodyReferenceWorldInteractionOwner",
    "ManyBodyOperatorCoordinateSynthesisOwner",
    "TheoryToExecutableCompilerOwner", "ExecutableTheoryRuntimeOwner",
    "KERNEL_OWNER_ID", "PROBE_DESIGN_OWNER_ID", "ATOMIC_WORLD_INTERACTION_OWNER_ID",
    "VARIABLE_PARTICLE_PROBE_DESIGN_OWNER_ID", "VARIABLE_PARTICLE_WORLD_INTERACTION_OWNER_ID",
    "SELF_CONSISTENT_SYNTHESIS_OWNER_ID", "MANY_BODY_PROBE_DESIGN_OWNER_ID",
    "ATOMIC_MANY_BODY_WORLD_OWNER_ID", "MANY_BODY_SYNTHESIS_OWNER_ID",
    "SYNTHESIS_OWNER_ID", "LOWERING_OWNER_ID", "EXECUTOR_OWNER_ID", "SCHEMA",
]
