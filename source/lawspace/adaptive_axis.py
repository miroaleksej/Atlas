"""Adaptive latent/context axis discovery for Φ-LawSpace.

This owner does not declare truth and does not mutate the canonical registry.
It scans structured contradictory or heterogeneous evidence for context fields
that partition outcomes, checks whether the coordinate already exists in the
active domain registry, and emits research-local axis candidates.  Qualified
proposals are delegated to the existing DynamicAxisAdmissionOwner; canonical
mutation remains solely owned by DynamicAxisPromotionOwner.
"""
from __future__ import annotations

import itertools
import math
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .domains import DOMAIN_REGISTRIES
from .research_cycle import DynamicAxisAdmissionOwner, DynamicAxisProposal
from .schema import digest_payload

OWNER_ID = "ADAPTIVE-AXIS-DISCOVERY/1.1.0"
SCHEMA = "phi-adaptive-axis-discovery/v2"


def _tokens(*values: Any) -> set[str]:
    text = " ".join(str(v) for v in values if v is not None).casefold()
    return set(re.findall(r"[0-9a-zа-я_]+", text))


def _entropy(labels: Sequence[str]) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def _conditional_entropy(labels: Sequence[str], values: Sequence[str]) -> float:
    n = len(labels)
    groups: dict[str, list[str]] = defaultdict(list)
    for y, x in zip(labels, values):
        groups[x].append(y)
    return sum((len(rows) / n) * _entropy(rows) for rows in groups.values()) if n else 0.0


def _axis_similarity(axis_key: str, axis_id: str, description: str) -> float:
    a = _tokens(axis_key.replace("_", " "))
    b = _tokens(axis_id.replace("_", " "), description)
    union = a | b
    return (len(a & b) / len(union)) if union else 0.0


def _study_id(row: Mapping[str, Any], index: int) -> str:
    """Return an explicit independent-study identifier when available.

    The fallback order is intentionally conservative. A PMID/DOI identifies a
    publication/study better than a record id. If no study identity is supplied,
    each record is treated as its own study; this prevents accidental aggregation
    but cannot create evidence of replication.
    """
    for key in ("study_id", "pmid", "doi", "source_id"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    source = dict(row.get("source", {}) or {})
    for key in ("pmid", "doi", "study_id"):
        value = source.get(key)
        if value not in (None, ""):
            return str(value)
    value = row.get("record_id")
    return str(value) if value not in (None, "") else f"ROW-{index}"


def _partition_signature(values: Sequence[str]) -> str:
    """Digest an equality partition, not the literal category labels.

    Renaming A/B to X/Y must not make two confounded partitions look distinct.
    """
    ids: dict[str, int] = {}
    pattern = []
    for value in values:
        if value not in ids:
            ids[value] = len(ids)
        pattern.append(ids[value])
    return digest_payload(pattern)


def _majority_label(labels: Sequence[str]) -> str:
    counts = Counter(labels)
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _loso_axis_gain(labels: Sequence[str], values: Sequence[str], studies: Sequence[str]) -> Mapping[str, Any]:
    """Leave-one-study-out accuracy gain over a training-majority baseline.

    Unseen axis values fall back to the training majority. This is deliberately
    harsh for high-cardinality/singleton categorical axes: memorization is not
    rewarded as generalization.
    """
    unique_studies = sorted(set(studies))
    if len(unique_studies) < 3:
        return {"status": "INSUFFICIENT_INDEPENDENT_STUDIES", "study_count": len(unique_studies), "axis_accuracy": 0.0, "baseline_accuracy": 0.0, "gain": 0.0}
    axis_correct = baseline_correct = total = 0
    for held in unique_studies:
        train_idx = [i for i, s in enumerate(studies) if s != held]
        test_idx = [i for i, s in enumerate(studies) if s == held]
        train_y = [labels[i] for i in train_idx]
        global_majority = _majority_label(train_y)
        by_value: dict[str, list[str]] = defaultdict(list)
        for i in train_idx:
            by_value[values[i]].append(labels[i])
        value_majority = {x: _majority_label(ys) for x, ys in by_value.items()}
        for i in test_idx:
            pred = value_majority.get(values[i], global_majority)
            axis_correct += int(pred == labels[i])
            baseline_correct += int(global_majority == labels[i])
            total += 1
    axis_acc = axis_correct / total if total else 0.0
    base_acc = baseline_correct / total if total else 0.0
    return {"status": "COMPUTED", "study_count": len(unique_studies), "axis_accuracy": axis_acc, "baseline_accuracy": base_acc, "gain": axis_acc - base_acc}


def _unique_multiset_permutations(labels: Sequence[str], max_count: int = 100000):
    """Yield exact unique permutations for small label multisets, else none."""
    counts = Counter(labels)
    n = len(labels)
    denom = 1
    for c in counts.values():
        denom *= math.factorial(c)
    total = math.factorial(n) // denom if n else 1
    if total > max_count:
        return total, None

    keys = sorted(counts)
    work = []
    def rec():
        if len(work) == n:
            yield tuple(work)
            return
        for k in keys:
            if counts[k] <= 0:
                continue
            counts[k] -= 1
            work.append(k)
            yield from rec()
            work.pop()
            counts[k] += 1
    return total, rec()


def _exact_permutation_p(labels: Sequence[str], values: Sequence[str], observed_ig: float) -> Mapping[str, Any]:
    total, perms = _unique_multiset_permutations(labels)
    if perms is None:
        return {"status": "EXACT_ENUMERATION_TOO_LARGE_FAIL_CLOSED", "permutation_count": total, "p_value": 1.0}
    extreme = 0
    seen = 0
    for perm in perms:
        seen += 1
        h = _entropy(perm)
        ig = max(0.0, h - _conditional_entropy(perm, values)) if len(set(perm)) > 1 else 0.0
        if ig >= observed_ig - 1e-15:
            extreme += 1
    return {"status": "COMPUTED_EXACT", "permutation_count": seen, "p_value": extreme / seen if seen else 1.0}


def _grouped_permutation_p(labels: Sequence[str], values: Sequence[str], studies: Sequence[str]) -> Mapping[str, Any]:
    """Exact study-level permutation when each study has one outcome and value.

    Mixed outcomes or mixed axis values inside a study are not silently split into
    independent evidence. They make the grouped null test inapplicable and causal
    readiness remains fail-closed.
    """
    grouped: dict[str, list[int]] = defaultdict(list)
    for i, study in enumerate(studies):
        grouped[study].append(i)
    study_labels = []
    study_values = []
    for study in sorted(grouped):
        idx = grouped[study]
        ys = {labels[i] for i in idx}
        xs = {values[i] for i in idx}
        if len(ys) != 1:
            return {"status": "MIXED_OUTCOMES_WITHIN_STUDY_FAIL_CLOSED", "study_count": len(grouped), "permutation_count": 0, "p_value": 1.0}
        if len(xs) != 1:
            return {"status": "MIXED_AXIS_VALUES_WITHIN_STUDY_FAIL_CLOSED", "study_count": len(grouped), "permutation_count": 0, "p_value": 1.0}
        study_labels.append(next(iter(ys)))
        study_values.append(next(iter(xs)))
    h = _entropy(study_labels)
    observed = max(0.0, h - _conditional_entropy(study_labels, study_values)) if len(set(study_labels)) > 1 else 0.0
    result = dict(_exact_permutation_p(study_labels, study_values, observed))
    result["study_count"] = len(grouped)
    result["observed_information_gain_bits"] = observed
    return result


class AdaptiveAxisDiscoveryOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "purpose": "detect missing context coordinates from structured residual/contradiction evidence",
            "mutation_policy": "NO_CANONICAL_MUTATION",
            "delegates_provisional_admission_to": DynamicAxisAdmissionOwner.owner_id,
            "hard_boundaries": {
                "absence_of_prior_art_can_reject_candidate": False,
                "external_contradiction_can_auto_reject_candidate": False,
                "unexplained_conflict_may_trigger_axis_search": True,
                "axis_count_has_fixed_ceiling": False,
                "research_local_axis_is_canonical_truth": False,
                "canonical_mutation_requires_dynamic_axis_promotion_owner": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def scan(
        self,
        *,
        domain_id: str,
        evidence_records: Sequence[Mapping[str, Any]],
        outcome_key: str = "outcome_class",
        context_key: str = "context",
        minimum_coverage: float = 0.60,
        minimum_information_gain_bits: float = 0.05,
        minimum_independent_study_support: int = 2,
        maximum_grouped_permutation_p: float = 0.05,
        minimum_loso_gain: float = 0.0,
    ) -> Mapping[str, Any]:
        if domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain {domain_id!r}")
        if len(evidence_records) < 2:
            raise ValueError("at least two evidence records are required")
        outcomes = [str(row.get(outcome_key, "")).strip().upper() for row in evidence_records]
        if any(not y for y in outcomes):
            raise ValueError("every evidence record must declare outcome_class")
        base_h = _entropy(outcomes)
        dimensions = sorted({str(k) for row in evidence_records for k in dict(row.get(context_key, {}) or {})})
        active = DOMAIN_REGISTRIES[domain_id]
        rows = []
        for dim in dimensions:
            usable = []
            ys = []
            for row, y in zip(evidence_records, outcomes):
                value = dict(row.get(context_key, {}) or {}).get(dim)
                if value not in (None, "", "UNKNOWN", "UNRESOLVED"):
                    usable.append(str(value))
                    ys.append(y)
            coverage = len(usable) / len(evidence_records)
            values = sorted(set(usable))
            cond_h = _conditional_entropy(ys, usable) if usable else base_h
            ig = max(0.0, _entropy(ys) - cond_h) if len(set(ys)) > 1 else 0.0
            norm_ig = (ig / _entropy(ys)) if ys and _entropy(ys) > 0 else 0.0
            within = []
            for axis_id, axis in active.axes.items():
                sim = _axis_similarity(dim, axis_id, axis.description_ru)
                if axis_id == dim or sim >= 0.25:
                    within.append({"axis_id": axis_id, "similarity": sim, "exact": axis_id == dim})
            cross = []
            for other_domain, registry in DOMAIN_REGISTRIES.items():
                if other_domain == domain_id:
                    continue
                for axis_id, axis in registry.axes.items():
                    sim = _axis_similarity(dim, axis_id, axis.description_ru)
                    if sim >= 0.40:
                        cross.append({"domain_id": other_domain, "axis_id": axis_id, "similarity": sim})
            exact = any(r["exact"] for r in within)
            near = max([float(r["similarity"]) for r in within] + [0.0])
            min_support = min(Counter(usable).values()) if usable else 0
            partition_signature = _partition_signature(usable) if usable else ""
            if exact:
                status = "EXISTING_DOMAIN_AXIS"
            elif near >= 0.70:
                status = "LIKELY_REDUNDANT_WITH_DOMAIN_AXIS"
            elif coverage >= minimum_coverage and len(values) >= 2 and ig >= minimum_information_gain_bits:
                status = "RESEARCH_LOCAL_AXIS_CANDIDATE"
            else:
                status = "INSUFFICIENT_AXIS_SIGNAL"
            usable_studies = []
            for index, row in enumerate(evidence_records):
                value = dict(row.get(context_key, {}) or {}).get(dim)
                if value not in (None, "", "UNKNOWN", "UNRESOLVED"):
                    usable_studies.append(_study_id(row, index))
            study_support_by_value: dict[str, set[str]] = defaultdict(set)
            for value, study in zip(usable, usable_studies):
                study_support_by_value[value].add(study)
            min_independent_study_support = min((len(v) for v in study_support_by_value.values()), default=0)
            record_permutation = _exact_permutation_p(ys, usable, ig) if usable and len(set(ys)) > 1 else {"status":"NOT_APPLICABLE", "permutation_count":0, "p_value":1.0}
            grouped_permutation = _grouped_permutation_p(ys, usable, usable_studies) if usable and len(set(ys)) > 1 else {"status":"NOT_APPLICABLE", "study_count":len(set(usable_studies)), "permutation_count":0, "p_value":1.0}
            loso = _loso_axis_gain(ys, usable, usable_studies) if usable and len(set(ys)) > 1 else {"status":"NOT_APPLICABLE", "study_count":len(set(usable_studies)), "axis_accuracy":0.0, "baseline_accuracy":0.0, "gain":0.0}
            rows.append({
                "context_dimension": dim,
                "coverage": coverage,
                "distinct_value_count": len(values),
                "values": values,
                "minimum_value_support": min_support,
                "minimum_independent_study_support": min_independent_study_support,
                "record_level_exact_permutation": record_permutation,
                "grouped_study_exact_permutation": grouped_permutation,
                "leave_one_study_out": loso,
                "outcome_entropy_bits": _entropy(ys),
                "conditional_entropy_bits": cond_h,
                "information_gain_bits": ig,
                "normalized_information_gain": norm_ig,
                "partition_signature": partition_signature,
                "within_domain_matches": sorted(within, key=lambda r: (-float(r["similarity"]), str(r["axis_id"])))[:8],
                "cross_domain_matches": sorted(cross, key=lambda r: (-float(r["similarity"]), str(r["domain_id"]), str(r["axis_id"])))[:8],
                "status": status,
            })
        by_partition: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            if row.get("partition_signature") and row.get("status") == "RESEARCH_LOCAL_AXIS_CANDIDATE":
                by_partition[str(row["partition_signature"])].append(str(row["context_dimension"]))
        for row in rows:
            peers = sorted(x for x in by_partition.get(str(row.get("partition_signature", "")), []) if x != row["context_dimension"])
            row["confounded_with"] = peers
            row["identifiability_status"] = (
                "CONFOUNDED_PARTITION_NOT_CAUSALLY_IDENTIFIED" if peers else
                "PARTITION_DISTINCT_BUT_NOT_CAUSALLY_PROVEN" if row.get("status") == "RESEARCH_LOCAL_AXIS_CANDIDATE" else
                "NOT_APPLICABLE"
            )
            row["support_status"] = "LOW_INDEPENDENT_STUDY_REPLICATION" if 0 < int(row.get("minimum_independent_study_support", 0)) < minimum_independent_study_support else "INDEPENDENT_STUDY_SUPPORT_OK_OR_NOT_APPLICABLE"
            grouped = dict(row.get("grouped_study_exact_permutation", {}) or {})
            loso = dict(row.get("leave_one_study_out", {}) or {})
            row["causal_readiness_gates"] = {
                "candidate_signal": row.get("status") == "RESEARCH_LOCAL_AXIS_CANDIDATE",
                "independent_study_support": int(row.get("minimum_independent_study_support", 0)) >= int(minimum_independent_study_support),
                "grouped_permutation_null_rejected": grouped.get("status") == "COMPUTED_EXACT" and float(grouped.get("p_value", 1.0)) <= float(maximum_grouped_permutation_p),
                "leave_one_study_out_generalization": loso.get("status") == "COMPUTED" and float(loso.get("gain", 0.0)) > float(minimum_loso_gain),
                "partition_not_confounded": not peers,
            }
            row["causal_readiness_pass"] = all(row["causal_readiness_gates"].values())
            if row["causal_readiness_pass"]:
                row["identifiability_status"] = "CAUSAL_READINESS_GATES_PASSED_RESEARCH_LEVEL_NOT_WORLD_TRUTH"
        rows.sort(key=lambda r: (-float(r["normalized_information_gain"]), -float(r["coverage"]), str(r["context_dimension"])))
        candidate_rows = [r for r in rows if r.get("status") == "RESEARCH_LOCAL_AXIS_CANDIDATE"]
        causal_ready = [r for r in candidate_rows if r.get("causal_readiness_pass") is True]
        if len(causal_ready) == 1:
            identifiability_status = "ONE_AXIS_PASSED_POSITIVE_CAUSAL_READINESS_CONTRACT"
            automatic_allowed = True
        elif len(causal_ready) > 1:
            identifiability_status = "MULTIPLE_CAUSAL_READY_AXES_REQUIRE_DISCRIMINATING_EXPERIMENT"
            automatic_allowed = False
        elif candidate_rows:
            identifiability_status = "NO_AXIS_PASSED_POSITIVE_CAUSAL_READINESS_CONTRACT"
            automatic_allowed = False
        else:
            identifiability_status = "NO_RESEARCH_LOCAL_AXIS_CANDIDATE"
            automatic_allowed = False
        scan_summary = {
            "research_local_candidate_count": len(candidate_rows),
            "existing_axis_count_in_context": sum(r.get("status") == "EXISTING_DOMAIN_AXIS" for r in rows),
            "high_information_candidate_dimensions": [r["context_dimension"] for r in candidate_rows],
            "causal_ready_candidate_dimensions": [r["context_dimension"] for r in causal_ready],
            "causal_readiness_contract": {
                "default": "FAIL_CLOSED",
                "minimum_independent_study_support": int(minimum_independent_study_support),
                "maximum_grouped_permutation_p": float(maximum_grouped_permutation_p),
                "minimum_leave_one_study_out_gain_strictly_greater_than": float(minimum_loso_gain),
                "requires_unconfounded_partition": True,
                "normalized_ig_shortcut_threshold_used": False,
            },
            "identifiability_status": identifiability_status,
            "automatic_causal_axis_selection_allowed": automatic_allowed,
        }
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "domain_id": domain_id,
            "evidence_record_count": len(evidence_records),
            "outcome_classes": sorted(set(outcomes)),
            "baseline_outcome_entropy_bits": base_h,
            "minimum_coverage": float(minimum_coverage),
            "minimum_information_gain_bits": float(minimum_information_gain_bits),
            "minimum_independent_study_support": int(minimum_independent_study_support),
            "maximum_grouped_permutation_p": float(maximum_grouped_permutation_p),
            "minimum_loso_gain": float(minimum_loso_gain),
            "active_domain_axis_count": active.axis_count,
            "candidate_axes": rows,
            "scan_summary": scan_summary,
            "claim_boundary": {
                "axis_candidate_is_scientific_truth": False,
                "axis_candidate_may_be_mounted_research_locally": True,
                "canonical_registry_mutated": False,
                "contradictory_evidence_forces_rejection": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def build_proposal_from_scan(
        self,
        *,
        scan_result: Mapping[str, Any],
        source_dimension: str,
        evidence_records: Sequence[Mapping[str, Any]] = (),
    ) -> DynamicAxisProposal:
        """Build a typed research-local proposal from an observed scan dimension.

        This is intentionally conservative: it derives only what is present in
        the scan/evidence contract and never invents a domain mechanism. Numeric
        source units remain unresolved at research level until a domain owner
        supplies them; categorical coordinates carry only their observed levels.
        """
        rows = {str(r["context_dimension"]): dict(r) for r in scan_result.get("candidate_axes", ())}
        if source_dimension not in rows:
            raise ValueError(f"source dimension {source_dimension!r} not present in scan")
        source = rows[source_dimension]
        if source.get("status") != "RESEARCH_LOCAL_AXIS_CANDIDATE":
            raise ValueError(f"source dimension {source_dimension!r} is not a research-local candidate")
        values = [str(x) for x in source.get("values", ())]

        def as_int(v: str):
            try:
                x = int(v)
                return x if str(x) == v.strip() or v.strip().lstrip("+-").isdigit() else None
            except Exception:
                return None

        def as_float(v: str):
            try:
                return float(v)
            except Exception:
                return None

        ints = [as_int(v) for v in values]
        floats = [as_float(v) for v in values]
        lower = {v.casefold() for v in values}
        if values and lower <= {"true", "false", "yes", "no", "0", "1"}:
            value_kind = "BOOLEAN"
            allowed_values = tuple(values)
            expected_range = {"values": values}
            units = "boolean/categorical observed context level"
        elif values and all(x is not None for x in ints):
            value_kind = "INTEGER"
            allowed_values = ()
            nums = [int(x) for x in ints if x is not None]
            expected_range = {"minimum": min(nums), "maximum": max(nums)}
            units = "source units unresolved; research-local observed integer coordinate"
        elif values and all(x is not None for x in floats):
            value_kind = "CONTINUOUS_RANGE"
            allowed_values = ()
            nums = [float(x) for x in floats if x is not None]
            expected_range = {"minimum": min(nums), "maximum": max(nums)}
            units = "source units unresolved; research-local observed continuous coordinate"
        else:
            value_kind = "ENUM"
            allowed_values = tuple(values[:128])
            expected_range = {"values": list(allowed_values)}
            units = "categorical observed context level"

        evidence_ids = []
        for i, row in enumerate(evidence_records):
            evidence_ids.append(_study_id(row, i))
        proposal_seed = {
            "scan_digest": scan_result.get("digest"),
            "domain_id": scan_result.get("domain_id"),
            "source_dimension": source_dimension,
            "partition_signature": source.get("partition_signature"),
        }
        proposal_id = "ADAPTIVE-" + digest_payload(proposal_seed)[:24].upper()
        return DynamicAxisProposal(
            proposal_id=proposal_id,
            domain_id=str(scan_result.get("domain_id")),
            axis_id=source_dimension,
            description_ru=(
                f"Исследовательская координата «{source_dimension}», обнаруженная по устойчивому "
                "разделению outcomes в измеренном контексте."
            ),
            value_kind=value_kind,
            physical_or_information_meaning=(
                "Observed context coordinate whose partition reduces outcome uncertainty and is "
                "subject to independent-study/identifiability gates; mechanism is not inferred."
            ),
            measurement_protocol=(
                f"Read context[{source_dimension!r}] before outcome from each evidence record; "
                "missing/UNKNOWN values remain unresolved and are never imputed by this owner."
            ),
            units_or_normalization=units,
            expected_range=expected_range,
            falsifiable_advantage=(
                "The coordinate must preserve its outcome-discriminating advantage under grouped-study "
                "null testing and leave-one-study-out generalization; otherwise it is retired."
            ),
            redundancy_test=(
                "Compare against active canonical axes and against equality-partition confounding; "
                "a redundant/confounded coordinate cannot be causally selected automatically."
            ),
            allowed_values=allowed_values,
            provenance_evidence=tuple([str(scan_result.get("digest", "")), *sorted(set(evidence_ids))]),
        )

    def admit_provisional_axis(
        self,
        *,
        scan_result: Mapping[str, Any],
        source_dimension: str,
        proposal: DynamicAxisProposal,
    ) -> Mapping[str, Any]:
        rows = {str(r["context_dimension"]): dict(r) for r in scan_result.get("candidate_axes", ())}
        if source_dimension not in rows:
            raise ValueError(f"source dimension {source_dimension!r} not present in scan")
        source = rows[source_dimension]
        if source.get("status") != "RESEARCH_LOCAL_AXIS_CANDIDATE":
            raise ValueError(f"source dimension {source_dimension!r} is not an admitted research-local candidate")
        admission = DynamicAxisAdmissionOwner().assess(proposal)
        payload = {
            "schema": "phi-adaptive-axis-provisional-admission/v1",
            "owner_id": OWNER_ID,
            "source_scan_digest": scan_result.get("digest"),
            "source_dimension": source_dimension,
            "source_axis_signal": source,
            "delegated_admission": admission,
            "research_region_mount_allowed": admission.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS",
            "canonical_registry_mutated": False,
            "canonical_promotion_required_for_global_registration": True,
        }
        return {**payload, "digest": digest_payload(payload)}

    def mount_research_region(
        self,
        *,
        domain_id: str,
        provisional_admissions: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        base = DOMAIN_REGISTRIES[domain_id]
        mounted = []
        for row in provisional_admissions:
            if row.get("research_region_mount_allowed") is not True:
                continue
            axis = dict(row.get("delegated_admission", {}).get("provisional_axis_definition", {}) or {})
            if axis and axis.get("domain") == domain_id:
                mounted.append(axis)
        ids = sorted({str(x["axis_id"]) for x in mounted})
        payload = {
            "schema": "phi-adaptive-research-region/v1",
            "owner_id": OWNER_ID,
            "domain_id": domain_id,
            "canonical_axis_count": base.axis_count,
            "research_local_axis_ids": ids,
            "research_region_axis_count": base.axis_count + len(ids),
            "canonical_registry_mutated": False,
            "research_region_axes": mounted,
        }
        return {**payload, "digest": digest_payload(payload)}
