"""Thin I/O adapter between Frontier 003 CSV artifacts and AI Laboratory receipts.

No hypothesis fitting lives here.  The module only loads a frozen manifest and
materializes receipt-bound measurements into the pre-existing results-template
schema consumed by Frontier 003 analyzers.
"""
from __future__ import annotations

import csv
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Mapping, Sequence

from .runtime import ScienceAtlasAI

DEFAULT_REGIMES = (
    "reasoning_verification",
    "memory_long_horizon",
    "agentic_world_information",
    "mixed_open_ended",
)


def load_manifest(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError("Frontier 003 manifest is empty")
    required = {"run_id", "model_scale_id", "condition_id", "budget_R", "budget_V", "budget_M", "budget_W", "budget_E"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Frontier 003 manifest missing columns: {sorted(missing)}")
    return rows


def execute_frontier003(
    ai: ScienceAtlasAI,
    *,
    manifest_path: str | Path,
    task_regimes: Sequence[str] = DEFAULT_REGIMES,
    seed: int = 0,
    require_real: bool = True,
) -> dict[str, Any]:
    return ai.run_ai_factorial_experiment(
        manifest_rows=load_manifest(manifest_path),
        task_regimes=tuple(task_regimes),
        seed=seed,
        require_real=require_real,
    )


def _ratio_decimal(payload: Mapping[str, Any]) -> str:
    numerator = int(payload["numerator"])
    denominator = int(payload["denominator"])
    with localcontext() as ctx:
        ctx.prec = 40
        value = Decimal(numerator) / Decimal(denominator)
        text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def materialize_results_template(
    *,
    receipt: Mapping[str, Any],
    template_path: str | Path,
    output_path: str | Path,
) -> Path:
    if not bool(receipt.get("scientific_measurement", False)):
        raise RuntimeError("NON_SCIENTIFIC_RECEIPT_CANNOT_FILL_REAL_RESULTS_TEMPLATE")
    measurements = {
        (str(row["run_id"]), str(row["task_regime"])): row
        for row in receipt.get("measurements", [])
    }
    source = Path(template_path)
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    required = {"run_id", "task_regime", "P_active", "baseline_score", "intervention_score", "metric", "seed", "status", "notes"}
    missing = required - set(fieldnames)
    if missing:
        raise ValueError(f"results template missing columns: {sorted(missing)}")
    for row in rows:
        key = (str(row["run_id"]), str(row["task_regime"]))
        measurement = measurements.get(key)
        if measurement is None:
            raise RuntimeError(f"receipt missing template measurement: {key}")
        row["P_active"] = str(measurement["P_active"])
        row["baseline_score"] = _ratio_decimal(measurement["baseline_score"])
        row["intervention_score"] = _ratio_decimal(measurement["intervention_score"])
        row["metric"] = str(measurement["metric"])
        row["seed"] = str(measurement["seed"])
        row["status"] = "COMPLETE"
        row["notes"] = f"scienceatlas_ai_lab_run={receipt['run_digest']}; artifact={measurement['artifact_digest']}"
    if len(measurements) != len(rows):
        extra = sorted(set(measurements) - {(r["run_id"], r["task_regime"]) for r in rows})
        if extra:
            raise RuntimeError(f"receipt contains measurements outside frozen template: {extra[:5]}")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return target
