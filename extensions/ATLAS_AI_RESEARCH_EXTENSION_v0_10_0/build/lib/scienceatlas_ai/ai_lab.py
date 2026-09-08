"""Executable AI laboratory contracts for ScienceAtlas AI 0.10.0.

The laboratory closes the measurement gap identified by the frozen AI scaling-law
Frontier 003 without fabricating measurements.  One ModelExecutionOwner owns the
actual orchestration.  Exact frontier capabilities are exposed by thin contract
owners that delegate to that single laboratory authority.

A backend is an external executor, not scientific truth.  It must attest the same
architecture family at three scales, supported budget controls, task regimes, and
whether its outputs are real measurements or test fixtures.  Scientific execution
fails closed unless ``real_measurement=True``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import json
import subprocess
from typing import Any, Mapping, Protocol, Sequence

from .owners import OwnerSpec
from .provenance import digest_json


MODEL_FAMILY_CAPABILITY = "ai.model_family.same_architecture_three_scales"
BUDGET_CAPABILITIES = {
    "R": "ai.inference.reasoning_budget",
    "V": "ai.inference.verifier_budget",
    "M": "ai.memory.retrieval_budget",
    "W": "ai.world_model.rollout_budget",
    "E": "ai.active_information.probe_budget",
}
REGIME_CAPABILITIES = {
    "reasoning_verification": "ai.evaluation.regime.reasoning_verification",
    "memory_long_horizon": "ai.evaluation.regime.memory_long_horizon",
    "agentic_world_information": "ai.evaluation.regime.agentic_world_information",
    "mixed_open_ended": "ai.evaluation.regime.mixed_open_ended",
}
LABORATORY_CAPABILITY = "ai.laboratory.factorial_execution"
REQUIRED_FRONTIER_CAPABILITIES = (
    MODEL_FAMILY_CAPABILITY,
    *BUDGET_CAPABILITIES.values(),
    *REGIME_CAPABILITIES.values(),
)


def _fraction_json(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_json(value: Mapping[str, Any] | int | str | Fraction) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("boolean is not a scientific score")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        raise TypeError("external float score is forbidden; return rational object or decimal string")
    if isinstance(value, Mapping):
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    if isinstance(value, (int, str)):
        return Fraction(value)
    raise TypeError(f"unsupported external score type: {type(value)!r}")


@dataclass(frozen=True, slots=True)
class ModelScale:
    scale_id: str
    active_parameters: int

    def __post_init__(self) -> None:
        if not self.scale_id:
            raise ValueError("scale_id is required")
        if isinstance(self.active_parameters, bool) or self.active_parameters <= 0:
            raise ValueError("active_parameters must be positive")

    def to_json(self) -> dict[str, Any]:
        return {"scale_id": self.scale_id, "active_parameters": self.active_parameters}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ModelScale":
        return cls(scale_id=str(payload["scale_id"]), active_parameters=int(payload["active_parameters"]))


@dataclass(frozen=True, slots=True)
class ModelBackendSpec:
    backend_id: str
    model_family_id: str
    architecture_id: str
    scales: tuple[ModelScale, ...]
    supported_budget_capabilities: tuple[str, ...]
    supported_regimes: tuple[str, ...]
    real_measurement: bool
    backend_version: str = "1"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.backend_id or not self.model_family_id or not self.architecture_id:
            raise ValueError("backend/model family/architecture identifiers are required")
        scale_order = {"SMALL": 0, "REFERENCE": 1, "LARGE": 2}
        object.__setattr__(self, "scales", tuple(sorted(self.scales, key=lambda row: scale_order.get(row.scale_id, 99))))
        object.__setattr__(self, "supported_budget_capabilities", tuple(sorted(set(self.supported_budget_capabilities))))
        object.__setattr__(self, "supported_regimes", tuple(sorted(set(self.supported_regimes))))
        ids = [row.scale_id for row in self.scales]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate model scale identifiers")
        if set(ids) != {"SMALL", "REFERENCE", "LARGE"}:
            raise ValueError("backend must attest exactly SMALL, REFERENCE and LARGE scales")
        unknown_budget = set(self.supported_budget_capabilities) - set(BUDGET_CAPABILITIES.values())
        if unknown_budget:
            raise ValueError(f"unknown budget capabilities: {sorted(unknown_budget)}")
        unknown_regimes = set(self.supported_regimes) - set(REGIME_CAPABILITIES)
        if unknown_regimes:
            raise ValueError(f"unknown task regimes: {sorted(unknown_regimes)}")

    def scale_map(self) -> dict[str, ModelScale]:
        return {row.scale_id: row for row in self.scales}

    def to_json(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "model_family_id": self.model_family_id,
            "architecture_id": self.architecture_id,
            "scales": [row.to_json() for row in sorted(self.scales, key=lambda x: x.scale_id)],
            "supported_budget_capabilities": sorted(self.supported_budget_capabilities),
            "supported_regimes": sorted(self.supported_regimes),
            "real_measurement": self.real_measurement,
            "notes": self.notes,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ModelBackendSpec":
        return cls(
            backend_id=str(payload["backend_id"]),
            backend_version=str(payload.get("backend_version", "1")),
            model_family_id=str(payload["model_family_id"]),
            architecture_id=str(payload["architecture_id"]),
            scales=tuple(ModelScale.from_json(row) for row in payload.get("scales", [])),
            supported_budget_capabilities=tuple(str(x) for x in payload.get("supported_budget_capabilities", [])),
            supported_regimes=tuple(str(x) for x in payload.get("supported_regimes", [])),
            real_measurement=bool(payload.get("real_measurement", False)),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class AIBudgetVector:
    reasoning_traces: int = 0
    verifier_evaluations: int = 0
    retrievable_memory_tokens: int = 0
    world_model_rollouts: int = 0
    active_information_probes: int = 0

    def __post_init__(self) -> None:
        for name, value in self.to_mapping().items():
            if isinstance(value, bool) or value < 0:
                raise ValueError(f"budget {name} must be a non-negative integer")

    def to_mapping(self) -> dict[str, int]:
        return {
            "R": self.reasoning_traces,
            "V": self.verifier_evaluations,
            "M": self.retrievable_memory_tokens,
            "W": self.world_model_rollouts,
            "E": self.active_information_probes,
        }

    @classmethod
    def from_manifest_row(cls, row: Mapping[str, Any]) -> "AIBudgetVector":
        def parse(key: str) -> int:
            value = row.get(key, 0)
            if value in (None, ""):
                return 0
            return int(value)
        return cls(
            reasoning_traces=parse("budget_R"),
            verifier_evaluations=parse("budget_V"),
            retrievable_memory_tokens=parse("budget_M"),
            world_model_rollouts=parse("budget_W"),
            active_information_probes=parse("budget_E"),
        )

    def to_json(self) -> dict[str, int]:
        return self.to_mapping()


@dataclass(frozen=True, slots=True)
class ModelRunRequest:
    run_id: str
    model_scale_id: str
    condition_id: str
    task_regime: str
    budgets: AIBudgetVector
    seed: int

    def __post_init__(self) -> None:
        if not self.run_id or not self.condition_id:
            raise ValueError("run_id and condition_id are required")
        if self.model_scale_id not in {"SMALL", "REFERENCE", "LARGE"}:
            raise ValueError("invalid model_scale_id")
        if self.task_regime not in REGIME_CAPABILITIES:
            raise ValueError("unknown task regime")

    def to_json(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_scale_id": self.model_scale_id,
            "condition_id": self.condition_id,
            "task_regime": self.task_regime,
            "budgets": self.budgets.to_json(),
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class ModelRunResult:
    score: Fraction
    artifact_digest: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.score < 0 or self.score > 1:
            raise ValueError("score must lie in [0,1]")
        if not self.artifact_digest:
            raise ValueError("artifact_digest is required")

    def to_json(self) -> dict[str, Any]:
        return {
            "score": _fraction_json(self.score),
            "artifact_digest": self.artifact_digest,
            "metadata": dict(self.metadata),
        }


class ModelExecutionBackend(Protocol):
    spec: ModelBackendSpec

    def execute(self, request: ModelRunRequest) -> ModelRunResult: ...


class JsonCommandBackend:
    """Backend adapter for a real external runner using JSON over stdin/stdout.

    ``argv`` is executed without a shell.  The command receives one request JSON
    object on stdin and must return one JSON object containing ``score`` and
    ``artifact_digest``.  This adapter does not grant scientific status: that is
    controlled by ``spec.real_measurement`` and the laboratory preflight.
    """

    def __init__(self, spec: ModelBackendSpec, argv: Sequence[str], *, timeout_seconds: int = 3600) -> None:
        if not argv:
            raise ValueError("backend command argv is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.spec = spec
        self.argv = tuple(str(x) for x in argv)
        self.timeout_seconds = int(timeout_seconds)

    def execute(self, request: ModelRunRequest) -> ModelRunResult:
        payload = json.dumps(request.to_json(), sort_keys=True, separators=(",", ":"))
        proc = subprocess.run(
            self.argv,
            input=payload,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"AI backend failed rc={proc.returncode}; stderr={proc.stderr[-1000:]}"
            )
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("AI backend returned invalid JSON") from exc
        score = _fraction_from_json(result["score"])
        return ModelRunResult(
            score=score,
            artifact_digest=str(result["artifact_digest"]),
            metadata=dict(result.get("metadata", {})),
        )


class ModelExecutionOwner:
    """Single authoritative orchestrator for real AI factorial measurements."""

    spec = OwnerSpec(
        owner_id="ai-model-execution-owner/1.0.0",
        capability=LABORATORY_CAPABILITY,
        input_types=("frozen_factorial_manifest", "model_execution_backend", "task_regime"),
        output_types=("ai_measurement_rows", "execution_receipt"),
        validity_domain="same architecture family; three attested scales; explicit R/V/M/W/E budgets; bounded task metrics",
        uncertainty_contract="missing backend/capability/regime/measurement fails closed; fixture backend cannot produce scientific measurements",
        cost_model="sum of backend inference/evaluation costs over requested conditions; no hidden scientific ceiling",
        deterministic=False,
        replayable=True,
        falsification_contract="all run requests, backend identity, artifacts, scores and baseline linkage are receipt-bound and replayable",
        owner_kind="laboratory",
    )

    def __init__(self) -> None:
        self._backend: ModelExecutionBackend | None = None

    @property
    def backend(self) -> ModelExecutionBackend | None:
        return self._backend

    def attach_backend(self, backend: ModelExecutionBackend) -> None:
        if not hasattr(backend, "spec") or not isinstance(backend.spec, ModelBackendSpec):
            raise TypeError("backend must expose ModelBackendSpec as .spec")
        self._backend = backend

    def detach_backend(self) -> None:
        self._backend = None

    def status(self) -> dict[str, Any]:
        if self._backend is None:
            return {
                "status": "MEASUREMENT_BACKEND_GAP",
                "backend_attached": False,
                "required_frontier_capabilities": list(REQUIRED_FRONTIER_CAPABILITIES),
            }
        return {
            "status": "READY_REAL" if self._backend.spec.real_measurement else "READY_FIXTURE_ONLY",
            "backend_attached": True,
            "backend": self._backend.spec.to_json(),
            "required_frontier_capabilities": list(REQUIRED_FRONTIER_CAPABILITIES),
        }

    @staticmethod
    def _validate_three_scales(spec: ModelBackendSpec) -> dict[str, Any]:
        scales = spec.scale_map()
        small = scales["SMALL"].active_parameters
        ref = scales["REFERENCE"].active_parameters
        large = scales["LARGE"].active_parameters
        # Frontier 003 asks for approximately quarter/reference/fourfold.  Allow
        # a factor-of-two design tolerance because real model families are discrete.
        small_ratio = Fraction(small, ref)
        large_ratio = Fraction(large, ref)
        if not (Fraction(1, 8) <= small_ratio <= Fraction(1, 2)):
            raise ValueError("SMALL active-parameter scale is outside approximate P_ref/4 design band")
        if not (Fraction(2, 1) <= large_ratio <= Fraction(8, 1)):
            raise ValueError("LARGE active-parameter scale is outside approximate 4*P_ref design band")
        return {
            "status": "PASS",
            "architecture_id": spec.architecture_id,
            "model_family_id": spec.model_family_id,
            "small_to_reference": _fraction_json(small_ratio),
            "large_to_reference": _fraction_json(large_ratio),
        }

    def preflight(
        self,
        *,
        manifest_rows: Sequence[Mapping[str, Any]],
        task_regimes: Sequence[str],
        require_real: bool,
    ) -> dict[str, Any]:
        backend = self._backend
        if backend is None:
            raise RuntimeError("MEASUREMENT_BACKEND_GAP: attach a ModelExecutionBackend before execution")
        spec = backend.spec
        if require_real and not spec.real_measurement:
            raise RuntimeError("FIXTURE_BACKEND_FORBIDDEN_FOR_SCIENTIFIC_MEASUREMENT")
        scale_audit = self._validate_three_scales(spec)
        missing_budget = sorted(set(BUDGET_CAPABILITIES.values()) - set(spec.supported_budget_capabilities))
        if missing_budget:
            raise RuntimeError(f"BUDGET_CAPABILITY_GAP: {missing_budget}")
        unknown_regimes = sorted(set(task_regimes) - set(REGIME_CAPABILITIES))
        if unknown_regimes:
            raise ValueError(f"unknown requested regimes: {unknown_regimes}")
        missing_regimes = sorted(set(task_regimes) - set(spec.supported_regimes))
        if missing_regimes:
            raise RuntimeError(f"REGIME_EVALUATOR_GAP: {missing_regimes}")
        if not manifest_rows:
            raise ValueError("manifest_rows must not be empty")
        seen_runs: set[str] = set()
        baseline_by_scale: dict[str, list[str]] = {}
        for row in manifest_rows:
            run_id = str(row.get("run_id", ""))
            scale_id = str(row.get("model_scale_id", ""))
            condition_id = str(row.get("condition_id", ""))
            if not run_id or not condition_id or scale_id not in spec.scale_map():
                raise ValueError(f"invalid manifest row: {row}")
            if run_id in seen_runs:
                raise ValueError(f"duplicate run_id: {run_id}")
            seen_runs.add(run_id)
            budgets = AIBudgetVector.from_manifest_row(row)
            if all(value == 0 for value in budgets.to_mapping().values()):
                baseline_by_scale.setdefault(scale_id, []).append(run_id)
        missing_baselines = sorted(set(spec.scale_map()) - set(baseline_by_scale))
        if missing_baselines:
            raise ValueError(f"missing all-zero baseline condition for scales: {missing_baselines}")
        return {
            "status": "PASS",
            "backend": spec.to_json(),
            "scale_audit": scale_audit,
            "manifest_run_count": len(manifest_rows),
            "task_regimes": list(task_regimes),
            "baseline_run_ids": {k: list(v) for k, v in sorted(baseline_by_scale.items())},
            "require_real": require_real,
        }

    def execute_factorial(
        self,
        *,
        manifest_rows: Sequence[Mapping[str, Any]],
        task_regimes: Sequence[str],
        seed: int = 0,
        require_real: bool = True,
    ) -> dict[str, Any]:
        preflight = self.preflight(
            manifest_rows=manifest_rows,
            task_regimes=task_regimes,
            require_real=require_real,
        )
        backend = self._backend
        assert backend is not None
        raw: dict[tuple[str, str], tuple[ModelRunRequest, ModelRunResult]] = {}
        request_rows: list[dict[str, Any]] = []
        for row_index, row in enumerate(manifest_rows):
            budgets = AIBudgetVector.from_manifest_row(row)
            for regime_index, regime in enumerate(task_regimes):
                request = ModelRunRequest(
                    run_id=str(row["run_id"]),
                    model_scale_id=str(row["model_scale_id"]),
                    condition_id=str(row["condition_id"]),
                    task_regime=str(regime),
                    budgets=budgets,
                    seed=int(seed) + row_index * len(task_regimes) + regime_index,
                )
                result = backend.execute(request)
                key = (request.run_id, request.task_regime)
                if key in raw:
                    raise RuntimeError(f"duplicate backend measurement key: {key}")
                raw[key] = (request, result)
                request_rows.append({"request": request.to_json(), "result": result.to_json()})

        baseline_ids: Mapping[str, Sequence[str]] = preflight["baseline_run_ids"]
        scale_map = backend.spec.scale_map()
        baseline_means: dict[tuple[str, str], Fraction] = {}
        for scale_id, baseline_run_ids in baseline_ids.items():
            for regime in task_regimes:
                results = []
                for baseline_run_id in baseline_run_ids:
                    baseline_key = (baseline_run_id, regime)
                    if baseline_key not in raw:
                        raise RuntimeError(f"baseline measurement missing after execution: {baseline_key}")
                    results.append(raw[baseline_key][1].score)
                baseline_means[(scale_id, regime)] = sum(results, Fraction(0)) / len(results)

        measurements: list[dict[str, Any]] = []
        for (run_id, regime), (request, result) in sorted(raw.items()):
            baseline_score = baseline_means[(request.model_scale_id, regime)]
            measurements.append({
                "run_id": run_id,
                "model_scale_id": request.model_scale_id,
                "condition_id": request.condition_id,
                "task_regime": regime,
                "P_active": scale_map[request.model_scale_id].active_parameters,
                "baseline_score": _fraction_json(baseline_score),
                "baseline_run_ids": list(baseline_ids[request.model_scale_id]),
                "intervention_score": _fraction_json(result.score),
                "metric": "bounded_higher_is_better",
                "seed": request.seed,
                "status": "MEASURED_REAL" if backend.spec.real_measurement else "MEASURED_FIXTURE",
                "artifact_digest": result.artifact_digest,
            })

        body = {
            "schema": "scienceatlas-ai-laboratory-run/v1",
            "owner": self.spec.to_json(),
            "preflight": preflight,
            "measurement_count": len(measurements),
            "measurements": measurements,
            "request_results": request_rows,
            "scientific_measurement": bool(backend.spec.real_measurement and require_real),
        }
        body["run_digest"] = digest_json(body, namespace=b"SCIENCEATLAS_AI_LAB_RUN_V1")
        return body

    def invoke(self, *, action: str, **kwargs: Any) -> Mapping[str, Any]:
        if action == "status":
            return self.status()
        if action == "preflight":
            return self.preflight(**kwargs)
        if action == "execute_factorial":
            return self.execute_factorial(**kwargs)
        raise ValueError(f"unknown laboratory action: {action}")


class LaboratoryCapabilityOwner:
    """Algorithm-free exact capability contract delegating to ModelExecutionOwner."""

    def __init__(self, *, owner_id: str, capability: str, laboratory: ModelExecutionOwner, role: str) -> None:
        self._laboratory = laboratory
        self._role = role
        self.spec = OwnerSpec(
            owner_id=owner_id,
            capability=capability,
            input_types=("ai_laboratory_backend_contract",),
            output_types=("capability_attestation",),
            validity_domain=f"AI laboratory delegated capability: {role}",
            uncertainty_contract="reports GAP unless attached backend explicitly attests the exact capability",
            cost_model="contract check only; execution remains in ai-model-execution-owner/1.0.0",
            deterministic=True,
            replayable=True,
            falsification_contract="backend attestation and real execution receipt must agree",
            owner_kind="laboratory_contract",
        )

    def invoke(self, *, action: str = "status", **_: Any) -> Mapping[str, Any]:
        if action != "status":
            raise ValueError("laboratory capability owners expose status only")
        backend = self._laboratory.backend
        supported = False
        if backend is not None:
            if self.spec.capability == MODEL_FAMILY_CAPABILITY:
                supported = True
            elif self.spec.capability in BUDGET_CAPABILITIES.values():
                supported = self.spec.capability in backend.spec.supported_budget_capabilities
            elif self.spec.capability in REGIME_CAPABILITIES.values():
                regime = next(k for k, v in REGIME_CAPABILITIES.items() if v == self.spec.capability)
                supported = regime in backend.spec.supported_regimes
        return {
            "status": "PASS" if supported else "GAP",
            "capability": self.spec.capability,
            "delegates_execution_to": ModelExecutionOwner.spec.owner_id,
            "backend_attached": backend is not None,
            "real_measurement_backend": bool(backend and backend.spec.real_measurement),
        }


def build_laboratory_owners() -> tuple[ModelExecutionOwner, tuple[LaboratoryCapabilityOwner, ...]]:
    lab = ModelExecutionOwner()
    delegates: list[LaboratoryCapabilityOwner] = [
        LaboratoryCapabilityOwner(
            owner_id="ai-model-family-contract-owner/1.0.0",
            capability=MODEL_FAMILY_CAPABILITY,
            laboratory=lab,
            role="same architecture family at SMALL/REFERENCE/LARGE active-parameter scales",
        )
    ]
    for axis, capability in BUDGET_CAPABILITIES.items():
        delegates.append(LaboratoryCapabilityOwner(
            owner_id=f"ai-budget-{axis.lower()}-contract-owner/1.0.0",
            capability=capability,
            laboratory=lab,
            role=f"explicit {axis} budget control",
        ))
    for regime, capability in REGIME_CAPABILITIES.items():
        delegates.append(LaboratoryCapabilityOwner(
            owner_id=f"ai-regime-{regime.replace('_','-')}-contract-owner/1.0.0",
            capability=capability,
            laboratory=lab,
            role=f"task-regime evaluator {regime}",
        ))
    return lab, tuple(delegates)
