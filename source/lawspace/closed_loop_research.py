"""Measurement-driven orchestration of the existing axis-modeling owner.

The adapter is an explicitly supplied measurement capability, not a truth oracle
available to the search owner. A digest binds an answer to its frozen request;
it is integrity evidence, not independent world attestation. Validation used by
axis selection is development data. Final evaluation is revealed once after fit.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping, Protocol

from .axis_modeling import AxisModelingDataset, AxisModelingOwner
from .schema import digest_payload


def seal(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(payload))
    row.pop("digest", None)
    row["digest"] = digest_payload(row)
    return row


class MeasurementAdapter(Protocol):
    def measure(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def reveal_holdout(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ClosedLoopResearchOwner:
    """Residual -> generated coordinate -> intervention -> refit -> heldout test."""

    owner_id = "CLOSED-LOOP-AXIS-RESEARCH/1.0.0"

    def __init__(self) -> None:
        self.modeling = AxisModelingOwner()

    @staticmethod
    def _response(response: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        row = deepcopy(dict(response))
        if row.get("digest") != seal(row)["digest"]:
            raise ValueError("measurement response digest mismatch")
        if row.get("request_digest") != request["digest"]:
            raise ValueError("measurement response is not bound to frozen request")
        if not row.get("provenance"):
            raise ValueError("measurement provenance required")
        return row

    def run(self, request: Mapping[str, Any], adapter: MeasurementAdapter) -> Mapping[str, Any]:
        req = deepcopy(dict(request))
        dataset = deepcopy(req["dataset"])
        ds = AxisModelingDataset.from_mapping(dataset)
        ds.validate()
        budget = req.get("measurement_budget", 3)
        tolerance = float(req.get("final_nrmse_tolerance", 0.25))
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
            raise ValueError("measurement_budget must be a positive integer")
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("final_nrmse_tolerance must be finite and positive")
        validation = tuple(req.get("validation_regime_ids", ()))
        if not validation or not set(validation).issubset(set(ds.regime_ids)):
            raise ValueError("explicit development validation regimes required")
        holdout_commitment = str(req.get("holdout_dataset_digest", ""))
        if len(holdout_commitment) != 64 or any(c not in '0123456789abcdef' for c in holdout_commitment):
            raise ValueError("pre-search final holdout digest commitment required")
        policy = seal({
            "initial_dataset_digest": digest_payload(dataset),
            "measurement_budget": budget, "final_nrmse_tolerance": tolerance,
            "validation_regime_ids": list(validation),
            "holdout_dataset_digest": holdout_commitment,
            "representation_class": "EXISTING_AXIS_MODELING_RESIDUAL_LOCALIZATION",
            "scientific_promotion_allowed": False,
        })
        def fit() -> Mapping[str, Any]:
            return self.modeling.run({"dataset": dataset, "seed": int(req.get("seed", 0)),
                                      "ood_regime_ids": list(validation),
                                      "combination_materialization_budget": 0})

        model = fit()
        initial_digest = model["digest"]
        journal: list[dict[str, Any]] = []
        stop = "MEASUREMENT_BUDGET_EXHAUSTED"
        for index in range(budget):
            candidate = model.get("best_axis_birth")
            if not candidate or candidate.get("ood_rmse_fractional_improvement", 0) <= 0:
                stop = "NO_USEFUL_RESIDUAL_AXIS_CANDIDATE"
                break
            observed = [dict(zip((a["axis_id"] for a in dataset["axes"]), vals))
                        for vals in zip(*(a["values"] for a in dataset["axes"]))]
            design = self.modeling.design_discriminating_experiment(model, observed_points=observed)
            selected = design.get("selected_experiment")
            if not selected or selected["prediction_span"] <= 1e-12:
                stop = "NO_DISCRIMINATING_MEASUREMENT_AVAILABLE"
                break
            point = dict(selected["axis_values"])
            # Evaluate the actual selected best model, which can differ from other
            # candidates used to rank the experiment frontier.
            predictions = self.modeling.predict_frozen_axis_candidate(model, point)
            experiment = seal({
                "round": index, "policy_digest": policy["digest"],
                "model_digest": model["digest"], "design_digest": design["digest"],
                "previous_round_digest": journal[-1]["digest"] if journal else None,
                "axis_values": point,
                "predictions": {k: predictions[k] for k in ("baseline_prediction", "augmented_prediction")},
            })
            response = self._response(adapter.measure(deepcopy(experiment)), experiment)
            if response.get("axis_values") != point:
                raise ValueError("response measured a different point")
            value = float(response["observed"])
            sigma = response.get("sigma")
            if not math.isfinite(value):
                raise ValueError("nonfinite measured target")
            if dataset.get("sigma") is not None:
                if sigma is None or not math.isfinite(float(sigma)) or float(sigma) <= 0:
                    raise ValueError("measured uncertainty required")
                dataset["sigma"].append(float(sigma))
            dataset["y"].append(value)
            dataset["regime_ids"].append("ACQUIRED_TRAIN_" + experiment["digest"][:12])
            for axis in dataset["axes"]:
                axis["values"].append(point[axis["axis_id"]])
            updated = fit()
            journal.append(seal({
                "experiment": experiment, "response": response,
                "axis_before": {k: candidate.get(k) for k in
                                ("axis_id", "source_axis_id", "generated_coordinate", "frozen_model")},
                "baseline_absolute_error": abs(value - predictions["baseline_prediction"]),
                "candidate_absolute_error": abs(value - predictions["augmented_prediction"]),
                "revised_model_digest": updated["digest"],
                "fit_data_digest": digest_payload(dataset),
                "axis_semantic_admission": model.get("semantic_axis_admission"),
            }))
            model = updated

        # Nothing may be fitted or selected after this request.
        final_freeze = seal({"policy_digest": policy["digest"], "model_digest": model["digest"],
                             "journal_digest": digest_payload(journal),
                             "fit_data_digest": digest_payload(dataset)})
        response = self._response(adapter.reveal_holdout(deepcopy(final_freeze)), final_freeze)
        holdout = response["dataset"]
        if digest_payload(holdout) != holdout_commitment:
            raise ValueError("final holdout differs from pre-search commitment")
        hds = AxisModelingDataset.from_mapping(holdout)
        hds.validate()
        if set(hds.regime_ids) & set(dataset["regime_ids"]):
            raise ValueError("final holdout regimes overlap development data")
        if (hds.observable_id, hds.observable_units) != (ds.observable_id, ds.observable_units):
            raise ValueError("final observable semantics changed")
        if [(a.axis_id, a.domain, a.units) for a in hds.axes] != [(a.axis_id, a.domain, a.units) for a in ds.axes]:
            raise ValueError("final axis semantics changed")
        before_points = {tuple(p.values()) for p in
                         [dict(zip((a["axis_id"] for a in dataset["axes"]), vals))
                          for vals in zip(*(a["values"] for a in dataset["axes"]))]}
        if before_points & set(zip(*(a.values for a in hds.axes))):
            raise ValueError("final holdout repeats development input points")
        evaluation = self.modeling.evaluate_frozen_axis_candidate(model, holdout)
        supported = (bool(journal) and evaluation.get("augmented_nrmse", math.inf) <= tolerance
                     and evaluation.get("fractional_rmse_improvement", 0) > 0)
        return seal({
            "owner": self.owner_id, "schema": "phi-closed-loop-axis-research/v1",
            "status": "CLOSED_LOOP_HELDOUT_SUPPORTED_NOT_LAW" if supported else "CLOSED_LOOP_REPRESENTATION_GAP",
            "policy": policy, "initial_model_digest": initial_digest,
            "rounds": journal, "stop_reason": stop, "final_freeze": final_freeze,
            "holdout_response_digest": response["digest"], "final_evaluation": evaluation,
            "final_axis": model.get("best_axis_birth"),
            "final_axis_semantic_admission": model.get("semantic_axis_admission"),
            "claim_boundary": {"law_established": False, "causality_established": False,
                               "canonical_registry_mutated": False,
                               "final_holdout_used_for_refit": False,
                               "digest_is_world_attestation": False,
                               "whole_pipeline_null_calibrated": False,
                               "new_physical_observable_discovered": False},
        })
