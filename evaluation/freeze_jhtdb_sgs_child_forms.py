from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

EXPECTED_FAMILY_FREEZE_DIGEST = "66adb9d2e3e70499e5926f4fe25d98e614a6aa3d1214b63463c510ca4dc69397"
EXPECTED_OBSERVATIONAL_PROTOCOL_DIGEST = "c41038ac515826c3d6acf722488e788b13ad337e5beb40f9d903d7a401fda4bf"


def canonical_digest(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_content_digest(value: Mapping[str, Any], key: str = "digest") -> None:
    if value.get(key) != canonical_digest({k: v for k, v in value.items() if k != key}):
        raise ValueError(f"{key} content mismatch")


def component_form(row: Mapping[str, Any]) -> dict[str, Any]:
    summary = row.get("summary", {}) if isinstance(row.get("summary"), Mapping) else {}
    component = str(summary.get("component", row.get("component", ""))).strip().lower()
    if component not in {"x", "y", "z"}:
        raise ValueError(f"unexpected component: {component!r}")
    selected_axes = summary.get("selected_axes")
    parameters = summary.get("parameters")
    if not isinstance(selected_axes, list) or not selected_axes:
        raise ValueError(f"component {component}: selected_axes missing")
    if not isinstance(parameters, list) or len(parameters) < 2:
        raise ValueError(f"component {component}: parameters missing")
    form_core = {
        "component": component,
        "source_status": summary.get("status"),
        "selected_axes": selected_axes,
        "parameters": parameters,
        "discovery_holdout_nrmse": summary.get("discovery_holdout_nrmse"),
        "sealed_nrmse": summary.get("sealed_nrmse"),
        "causal_status": summary.get("causal_status"),
        "scientific_law_established": False,
        "source_receipt_digest": summary.get("receipt_digest"),
    }
    return {**form_core, "digest": canonical_digest(form_core)}


def build_freeze(report: Mapping[str, Any], family: Mapping[str, Any], obs: Mapping[str, Any]) -> dict[str, Any]:
    verify_content_digest(family, "freeze_digest")
    verify_content_digest(report)
    if family.get("freeze_digest") != EXPECTED_FAMILY_FREEZE_DIGEST:
        raise ValueError("family freeze digest mismatch")
    if family.get("fresh_measurement_status") != "NOT_ACQUIRED":
        raise ValueError("family freeze is no longer premeasurement")

    proto = obs.get("protocol", {}) if isinstance(obs.get("protocol"), Mapping) else {}
    verify_content_digest(proto)
    if proto.get("digest") != EXPECTED_OBSERVATIONAL_PROTOCOL_DIGEST:
        raise ValueError("observational protocol digest mismatch")
    if proto.get("fresh_measurement_status") != "NOT_ACQUIRED":
        raise ValueError("observational protocol is no longer premeasurement")
    if proto.get("outcomes_inspected_prefreeze") is not False:
        raise ValueError("observational outcomes were not cleanly frozen")

    if report.get("status") != "EXPERIMENT_COMPLETED_WITHOUT_TRANSFER_LAW_PROMOTION":
        raise ValueError("development DNS report has unexpected status")
    if report.get("protocol_status") != "PASS_PROTOCOL_INTEGRITY":
        raise ValueError("development DNS report protocol failed")

    rows = report.get("components")
    if not isinstance(rows, list):
        raise ValueError("development report components missing")
    forms = [component_form(row) for row in rows]
    by_component = {row["component"]: row for row in forms}
    if set(by_component) != {"x", "y", "z"}:
        raise ValueError(f"expected x/y/z child forms, got {sorted(by_component)}")

    retired = family.get("retired_parent_form", {}) if isinstance(family.get("retired_parent_form"), Mapping) else {}
    retired_digest = str(retired.get("digest", ""))
    if retired_digest and retired_digest in {row["digest"] for row in forms}:
        raise ValueError("child form digest equals retired parent form digest")

    core = {
        "schema": "atlas-jhtdb-sgs-child-forms-freeze/v1",
        "status": "CHILD_FORMS_FROZEN_BEFORE_FRESH_OBSERVATIONAL_EVIDENCE",
        "family_id": family.get("hypothesis_family_lineage", {}).get("family_id"),
        "family_freeze_digest": family.get("freeze_digest"),
        "observational_protocol_digest": proto.get("digest"),
        "development_report_digest": report.get("digest"),
        "development_report_status": report.get("status"),
        "forms": [by_component[k] for k in ("x", "y", "z")],
        "fresh_data_accessed_for_this_freeze": False,
        "fresh_outcomes_inspected_for_this_freeze": False,
        "coefficient_refit_on_fresh_data_allowed": False,
        "term_selection_on_fresh_data_allowed": False,
        "scientific_law_established": False,
        "world_novelty_established": False,
        "next_action": "ACQUIRE_FROZEN_NATURAL_SAMPLES_WITH_ATTESTED_MEASUREMENT_ADAPTER",
    }
    return {**core, "digest": canonical_digest(core)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze Atlas-generated JHTDB SGS child forms before fresh 8192 evidence.")
    ap.add_argument("--report", default="reports/TURBULENCE_DNS_CLOSURE_CURRENT.json")
    ap.add_argument("--family", default="reports/turbulence/ATLAS_RANDOM20_SGS_HYPOTHESIS_FAMILY_FREEZE.json")
    ap.add_argument("--protocol", default="reports/turbulence/JHTDB_SGS_OBSERVATIONAL_PROTOCOL_FROZEN.json")
    ap.add_argument("--output", default="reports/turbulence/ATLAS_RANDOM20_SGS_CHILD_FORMS_FREEZE.json")
    args = ap.parse_args()

    report_p, family_p, protocol_p, output_p = map(Path, (args.report, args.family, args.protocol, args.output))
    for p in (report_p, family_p, protocol_p):
        if not p.is_file():
            raise SystemExit(f"required file not found: {p}")

    freeze = build_freeze(load_json(report_p), load_json(family_p), load_json(protocol_p))
    output_p.parent.mkdir(parents=True, exist_ok=True)
    if output_p.exists():
        existing = load_json(output_p)
        if existing.get("digest") != freeze.get("digest"):
            raise SystemExit(f"refusing to overwrite different child freeze: {output_p}")
        print("CHILD FREEZE ALREADY EXISTS AND MATCHES")
    else:
        output_p.write_text(json.dumps(freeze, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("STATUS:", freeze["status"])
    print("FORMS:", ",".join(row["component"] for row in freeze["forms"]))
    print("FRESH DATA ACCESSED:", freeze["fresh_data_accessed_for_this_freeze"])
    print("DIGEST:", freeze["digest"])
    print("OUTPUT:", output_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
