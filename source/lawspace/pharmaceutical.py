"""Fail-closed pharmaceutical research domain for Φ-LawSpace.

The authoritative owner separates evidence-field completeness from scientific
hypothesis compatibility.  Missing/placeholder values are semantic nulls, not
positive evidence.  Candidate hypotheses are screened through causal,
modality, delivery, PK and PD gates with explicit PASS/OPEN/FAIL semantics.
No model output establishes clinical efficacy or safety.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import math

from .domains import DOMAIN_REGISTRIES
from .schema import digest_payload
from .scientific_verification import (
    ScientificVerificationCore, semantic_state, is_usable as _usable,
    normalize_status as _norm_status, gate as _gate,
)
from .scientific_rules import CommonScientificRulesCore, OWNER_ID as COMMON_RULES_OWNER

OWNER_ID = "PHARMACEUTICAL-RESEARCH-DOMAIN/8.3.0"
SCHEMA = "phi-pharmaceutical-research-domain/v8.3"

SELECTIVITY_BRIDGE_ID = "PHARMACEUTICAL-SELECTIVITY-PROFILE-TO-SCALAR/8.3.0"
SELECTIVITY_BRIDGE_SCHEMA = "phi-pharmaceutical-selectivity-bridge/v8.3"

GATE_SEQUENCE = ("IDENTITY", "MOA", "PK", "PD", "SAFETY", "DDI", "CLINICAL", "EVIDENCE")
HYPOTHESIS_GATE_SEQUENCE = ("SCIENTIFIC_VERIFICATION", "SEMANTIC", "CAUSAL", "MODALITY", "DELIVERY", "PK", "PD")
CRITICAL_HYPOTHESIS_GATES = ("SCIENTIFIC_VERIFICATION", "SEMANTIC", "CAUSAL", "MODALITY", "DELIVERY")

ICH_REFERENCES = {
    "M3_R2": "ICH M3(R2) Nonclinical Safety Studies for the Conduct of Human Clinical Trials and Marketing Authorization",
    "M12": "ICH M12 Drug Interaction Studies",
    "M15": "ICH M15 General Principles for Model-Informed Drug Development",
    "E6_R3": "ICH E6(R3) Good Clinical Practice",
    "SAFETY_SERIES": "ICH S-series safety guidelines",
}

_REQUIRED_BY_GATE = {
    "IDENTITY": ("drug_entity_type", "active_moiety", "therapeutic_modality", "formulation", "route_of_administration"),
    "MOA": ("molecular_target", "mechanism_of_action", "target_engagement", "potency_metric", "selectivity_profile"),
    "PK": ("absorption_model", "bioavailability", "distribution_volume", "clearance", "metabolism_pathway", "elimination_half_life"),
    "PD": ("exposure_metric", "pharmacodynamic_biomarker", "concentration_effect_model", "dose_response_model"),
    "SAFETY": ("off_target_liability", "safety_pharmacology", "genotoxicity", "organ_toxicity"),
    "DDI": ("drug_drug_interaction", "metabolism_pathway", "transporter_profile"),
    "CLINICAL": ("indication", "target_population", "clinical_endpoint", "trial_design"),
    "EVIDENCE": ("evidence_phase", "evidence_provenance", "benefit_risk_status", "pharmacovigilance_signal"),
}

_MODALITY_ALIASES = {
    "PROTAC": "PROTAC degrader",
    "ASO": "antisense oligonucleotide",
}
_MODALITY_EFFECT = {
    "small-molecule inhibitor": "DOWN",
    "inverse agonist": "DOWN",
    "PROTAC degrader": "DOWN",
    "siRNA": "DOWN",
    "antisense oligonucleotide": "DOWN",
    "peptide agonist": "UP",
    "agonist": "UP",
    "monoclonal antibody": "UNSPECIFIED",
}

_MODALITY_COMPARTMENTS = {
    "monoclonal antibody": {"EXTRACELLULAR", "CELL_SURFACE"},
    "small-molecule inhibitor": {"CELL_SURFACE", "INTRACELLULAR", "CYTOSOLIC", "NUCLEAR", "MITOCHONDRIAL", "ENDOSOMAL"},
    "PROTAC degrader": {"INTRACELLULAR", "CYTOSOLIC", "NUCLEAR", "MITOCHONDRIAL"},
    "siRNA": {"CELL_SURFACE", "EXTRACELLULAR", "INTRACELLULAR", "CYTOSOLIC", "NUCLEAR", "MITOCHONDRIAL", "ENDOSOMAL"},
    "peptide agonist": {"EXTRACELLULAR", "CELL_SURFACE"},
    "agonist": {"EXTRACELLULAR", "CELL_SURFACE", "INTRACELLULAR", "CYTOSOLIC"},
    "inverse agonist": {"CELL_SURFACE", "INTRACELLULAR", "CYTOSOLIC"},
    "antisense oligonucleotide": {"INTRACELLULAR", "CYTOSOLIC", "NUCLEAR"},
}

_REQUIRED_TISSUE = {
    "asthma": "LUNG",
    "MASH": "LIVER",
    "Alzheimer disease": "CNS",
    "Parkinson disease": "CNS",
    "atopic dermatitis": "SKIN",
    "solid tumors": "TUMOR_SYSTEMIC",
    "familial hypercholesterolemia": "LIVER_SYSTEMIC",
    "type 2 diabetes": "METABOLIC_SYSTEMIC",
}

SOURCE_LOCKED_HYPOTHESIS_FIELDS = (
    "causal_support", "supported_effect", "formulation_route_status",
    "target_compartment", "tissue_access_support", "pk_support", "pd_support",
    "special_modality_support",
)


class PharmaceuticalDomainOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        registry = DOMAIN_REGISTRIES["pharmaceutical"]
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "domain_id": "pharmaceutical",
            "registered_axis_count": registry.axis_count,
            "axis_ids": sorted(registry.axes),
            "gate_sequence": list(GATE_SEQUENCE),
            "hypothesis_gate_sequence": list(HYPOTHESIS_GATE_SEQUENCE),
            "critical_hypothesis_gates": list(CRITICAL_HYPOTHESIS_GATES),
            "common_scientific_rules": {
                "owner_id": COMMON_RULES_OWNER,
                "contract_digest": CommonScientificRulesCore().contract()["digest"],
                "role": "REFERENCE_ONLY_GENERIC_RULES_ARE_NOT_REIMPLEMENTED_HERE",
            },
            "generic_scientific_rules_implemented_locally": False,
            "evidence_framework": dict(ICH_REFERENCES),
            "typed_coordinate_bridges": {
                SELECTIVITY_BRIDGE_ID: {
                    "source_axis": "selectivity_profile",
                    "target_axis": "selectivity",
                    "relation": "PARTIAL_TYPED_DERIVATION",
                    "raw_text_profile_is_numerically_derivable": False,
                    "supported_metric": "FOLD_SELECTIVITY_TO_NEAREST_COMPARATOR",
                    "requires_explicit_target_and_comparator_values": True,
                    "requires_common_units": True,
                    "requires_declared_potency_direction": True,
                }
            },
            "hard_boundaries": {
                "missing_data_is_efficacy": False,
                "missing_data_is_safety": False,
                "model_prediction_is_clinical_validation": False,
                "literature_association_is_causal_moa": False,
                "preclinical_signal_is_human_benefit": False,
                "patient_specific_dosing_recommendation": False,
                "clinical_claim_requires_independent_human_evidence": True,
                "benefit_risk_requires_declared_population_and_endpoint": True,
                "pk_pd_parameter_uncertainty_must_be_explicit": True,
                "drug_interaction_obligation_must_be_explicit": True,
                "hypothesis_survival_is_not_clinical_promotion": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def derive_selectivity_from_profile(self, profile: Any) -> Mapping[str, Any]:
        """Partial typed morphism ``selectivity_profile -> selectivity``.

        The legacy profile axis remains authoritative for qualitative/panel context.
        A scalar is derived only from explicit numeric target/comparator measurements;
        free text, missing comparators, mixed units, zeros and semantic-null values fail
        closed.  For concentration-like potency lower values are more potent and the
        fold selectivity is ``min(comparator_i / target)``.  For higher-is-better
        metrics it is ``target / max(comparator_i)``.
        """
        base = {
            "schema": SELECTIVITY_BRIDGE_SCHEMA,
            "owner_id": OWNER_ID,
            "bridge_id": SELECTIVITY_BRIDGE_ID,
            "source_axis": "selectivity_profile",
            "target_axis": "selectivity",
            "metric": "FOLD_SELECTIVITY_TO_NEAREST_COMPARATOR",
            "scientific_status_modified": False,
        }
        if not isinstance(profile, Mapping):
            payload = {**base, "status": "NOT_DERIVABLE_PROFILE_NOT_TYPED", "derived": False}
            return {**payload, "digest": digest_payload(payload)}
        direction = str(profile.get("potency_direction", "")).upper()
        unit = str(profile.get("unit", "")).strip()
        target = profile.get("target_value")
        comps = list(profile.get("comparators", ()) or ())
        try:
            target_f = float(target)
        except (TypeError, ValueError):
            target_f = math.nan
        reasons: list[str] = []
        if direction not in {"LOWER_IS_MORE_POTENT", "HIGHER_IS_MORE_POTENT"}:
            reasons.append("POTENCY_DIRECTION_REQUIRED")
        if not unit:
            reasons.append("COMMON_UNIT_REQUIRED")
        if not math.isfinite(target_f) or target_f <= 0:
            reasons.append("POSITIVE_FINITE_TARGET_VALUE_REQUIRED")
        comp_vals: list[float] = []
        comp_names: list[str] = []
        for i, row in enumerate(comps):
            if not isinstance(row, Mapping):
                reasons.append(f"COMPARATOR_{i}_NOT_TYPED")
                continue
            if str(row.get("unit", "")).strip() != unit:
                reasons.append(f"COMPARATOR_{i}_UNIT_MISMATCH")
            try:
                val = float(row.get("value"))
            except (TypeError, ValueError):
                val = math.nan
            if not math.isfinite(val) or val <= 0:
                reasons.append(f"COMPARATOR_{i}_POSITIVE_FINITE_VALUE_REQUIRED")
            else:
                comp_vals.append(val)
                comp_names.append(str(row.get("name", f"comparator_{i}")))
        if not comps:
            reasons.append("AT_LEAST_ONE_COMPARATOR_REQUIRED")
        if reasons:
            payload = {**base, "status": "NOT_DERIVABLE_FAIL_CLOSED", "derived": False, "blocking_reasons": reasons}
            return {**payload, "digest": digest_payload(payload)}
        if direction == "LOWER_IS_MORE_POTENT":
            values = [v / target_f for v in comp_vals]
            formula = "min(comparator_potency / target_potency)"
        else:
            values = [target_f / v for v in comp_vals]
            formula = "min(target_potency / comparator_potency)"
        fold = min(values)
        payload = {
            **base, "status": "DERIVED_TYPED_BRIDGE", "derived": True,
            "value": fold, "unit": "fold", "formula": formula,
            "source_unit": unit, "target_value": target_f,
            "comparator_names": comp_names, "comparator_values": comp_vals,
            "potency_direction": direction,
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_research_record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        registry = DOMAIN_REGISTRIES["pharmaceutical"]
        unknown = sorted(set(record) - set(registry.axes))
        selectivity_bridge = self.derive_selectivity_from_profile(record.get("selectivity_profile"))
        derived_coordinates = {}
        if selectivity_bridge.get("derived") is True:
            derived_coordinates["selectivity"] = {"value": selectivity_bridge["value"], "unit": selectivity_bridge["unit"], "bridge_id": SELECTIVITY_BRIDGE_ID}
        gates: dict[str, Any] = {}
        for gate in GATE_SEQUENCE:
            required = _REQUIRED_BY_GATE[gate]
            missing = [axis for axis in required if semantic_state(record.get(axis)) == "MISSING"]
            semantic_null = [axis for axis in required if semantic_state(record.get(axis)) == "SEMANTIC_NULL"]
            gates[gate] = {
                "status": "PASS_USABLE_EVIDENCE_FIELDS_PRESENT" if not missing and not semantic_null else "OPEN_MISSING_OR_SEMANTIC_NULL_EVIDENCE_FIELDS",
                "required_axes": list(required),
                "missing_axes": missing,
                "semantic_null_axes": semantic_null,
            }
        complete = all(g["status"].startswith("PASS_") for g in gates.values()) and not unknown
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "domain_id": "pharmaceutical",
            "record": dict(record),
            "unknown_axes": unknown,
            "derived_coordinates": derived_coordinates,
            "selectivity_bridge": selectivity_bridge,
            "gates": gates,
            "structurally_complete": complete,
            "overall_status": (
                "STRUCTURALLY_COMPLETE_USABLE_EVIDENCE_RECORD_NOT_CLINICAL_VALIDATION"
                if complete else "RESEARCH_RECORD_OPEN_OR_INCOMPLETE_FAIL_CLOSED"
            ),
            "clinical_efficacy_established": False,
            "clinical_safety_established": False,
            "patient_specific_recommendation_allowed": False,
            "promotion_allowed": False,
        }
        return {**payload, "assessment_digest": digest_payload(payload)}

    def assess_hypothesis(
        self, coordinate: Mapping[str, Any], evidence: Mapping[str, Any] | None = None,
        verification_bundle: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Screen a frozen coordinate using only centrally verified evidence.

        Raw evidence is a proposal. The domain owner itself recomputes the generic
        verification receipt from signed source/claim/artifact attestations; a
        serialized ScientificVerificationReceipt is never accepted as authorization.
        """
        raw_evidence = dict(evidence or {})
        embedded_bundle = raw_evidence.pop("_scientific_verification_bundle", None)
        bundle = dict(verification_bundle or embedded_bundle or {})
        coord = {k: coordinate.get(k) for k in ("target", "modality", "route", "localization", "indication")}
        missing_coord = [k for k, v in coord.items() if not _usable(v)]
        gates: dict[str, Mapping[str, Any]] = {}

        verification = ScientificVerificationCore().verify_bundle(
            bundle, required_entity_slots=("target",),
            allowed_entity_states={"target": ("ESTABLISHED_EXTERNAL",)},
        )
        declared_claims = dict(bundle.get("claim_values", {}))
        bundle_mismatches = [
            field for field in SOURCE_LOCKED_HYPOTHESIS_FIELDS
            if digest_payload(declared_claims.get(field, "INSUFFICIENT"))
               != digest_payload(raw_evidence.get(field, "INSUFFICIENT"))
        ]
        verification_engine_ok = (
            verification.get("evidence_ready_for_domain") is True
            and not bundle_mismatches
            and str(bundle.get("proposer_owner", "")) == OWNER_ID
        )
        verification_world_ok = bool(verification_engine_ok and verification.get("scientific_candidate_allowed") is True)
        gates["SCIENTIFIC_VERIFICATION"] = _gate(
            "PASS" if verification_engine_ok else "FAIL",
            ("CENTRAL_SOURCE_AUTHENTICITY_AND_SOURCE_LOCK_WORLD_VERIFIED" if verification_world_ok
             else "CENTRAL_VERIFICATION_ENGINE_PASS_WORLD_ATTESTATION_BLOCKED")
            if verification_engine_ok else "CENTRAL_SCIENTIFIC_VERIFICATION_FAILED",
            verification_status=verification.get("overall_status"),
            world_scientific_candidate_allowed=verification_world_ok,
            bundle_mismatch_fields=bundle_mismatches,
            verification_digest=verification.get("verification_digest"),
        )
        sanitized = dict(verification.get("sanitized_claim_values", {})) if verification_engine_ok else {}
        evidence = dict(raw_evidence)
        for field in SOURCE_LOCKED_HYPOTHESIS_FIELDS:
            evidence[field] = sanitized.get(field, "INSUFFICIENT")

        # SEMANTIC: coordinate vocabulary and route/formulation coherence.
        modality_raw = str(coord.get("modality") or "")
        modality = _MODALITY_ALIASES.get(modality_raw, modality_raw)
        route = str(coord.get("route") or "")
        localization = str(coord.get("localization") or "")
        indication = str(coord.get("indication") or "")
        formulation_route = _norm_status(evidence.get("formulation_route_status"))
        if missing_coord:
            gates["SEMANTIC"] = _gate("FAIL", "MISSING_OR_SEMANTIC_NULL_COORDINATE", missing_fields=missing_coord)
        elif modality not in _MODALITY_EFFECT:
            gates["SEMANTIC"] = _gate("OPEN", "MODALITY_NOT_IN_CURRENT_TYPED_COMPATIBILITY_TABLE", modality=modality)
        elif formulation_route == "CONTRADICTED":
            gates["SEMANTIC"] = _gate("FAIL", "FORMULATION_ROUTE_CONTRADICTION", route=route, localization=localization)
        elif formulation_route == "SUPPORTED":
            gates["SEMANTIC"] = _gate("PASS", "FORMULATION_ROUTE_COMPATIBILITY_SUPPORTED")
        else:
            gates["SEMANTIC"] = _gate("OPEN", "FORMULATION_ROUTE_COMPATIBILITY_NOT_ESTABLISHED")

        # CAUSAL: target-disease evidence plus therapeutic direction.
        causal = _norm_status(evidence.get("causal_support"))
        supported_effect = _norm_status(evidence.get("supported_effect"))
        candidate_effect = _norm_status(evidence.get("candidate_effect"))
        if candidate_effect == "INSUFFICIENT":
            candidate_effect = _MODALITY_EFFECT.get(modality, "UNSPECIFIED")
        if causal == "CONTRADICTED":
            gates["CAUSAL"] = _gate("FAIL", "TARGET_DISEASE_CAUSAL_EVIDENCE_CONTRADICTS_HYPOTHESIS")
        elif causal == "SUPPORTED" and supported_effect in {"UP", "DOWN"} and candidate_effect in {"UP", "DOWN"}:
            if supported_effect == candidate_effect:
                gates["CAUSAL"] = _gate("PASS", "TARGET_DISEASE_DIRECTION_SUPPORTED", supported_effect=supported_effect, candidate_effect=candidate_effect)
            else:
                gates["CAUSAL"] = _gate("FAIL", "THERAPEUTIC_DIRECTION_MISMATCH", supported_effect=supported_effect, candidate_effect=candidate_effect)
        elif causal == "SUPPORTED" and supported_effect == "CONTEXT_DEPENDENT":
            gates["CAUSAL"] = _gate("OPEN", "TARGET_EFFECT_IS_STAGE_OR_CONTEXT_DEPENDENT")
        elif causal == "SUPPORTED" and candidate_effect == "UNSPECIFIED":
            gates["CAUSAL"] = _gate("OPEN", "TARGET_SUPPORTED_BUT_CANDIDATE_DIRECTION_UNSPECIFIED", supported_effect=supported_effect)
        elif causal == "SUPPORTED":
            gates["CAUSAL"] = _gate("OPEN", "TARGET_SUPPORTED_BUT_DIRECTION_NOT_ESTABLISHED")
        elif causal == "AMBIGUOUS":
            gates["CAUSAL"] = _gate("OPEN", "TARGET_DISEASE_EVIDENCE_AMBIGUOUS_OR_CONTEXT_DEPENDENT")
        else:
            gates["CAUSAL"] = _gate("OPEN", "TARGET_DISEASE_CAUSAL_SUPPORT_INSUFFICIENT")

        # MODALITY: generic topology compatibility, independent of named target.
        compartment = _norm_status(evidence.get("target_compartment"))
        special_modality_support = _norm_status(evidence.get("special_modality_support"))
        allowed = _MODALITY_COMPARTMENTS.get(modality)
        if special_modality_support == "CONTRADICTED":
            gates["MODALITY"] = _gate("FAIL", "EXPLICIT_MODALITY_TARGET_CONTRADICTION")
        elif allowed is None:
            gates["MODALITY"] = _gate("OPEN", "MODALITY_COMPATIBILITY_UNREGISTERED")
        elif compartment == "INSUFFICIENT":
            gates["MODALITY"] = _gate("OPEN", "TARGET_COMPARTMENT_NOT_ESTABLISHED")
        elif compartment in allowed:
            gates["MODALITY"] = _gate("PASS", "MODALITY_COMPATIBLE_WITH_TARGET_COMPARTMENT", target_compartment=compartment)
        elif special_modality_support == "SUPPORTED":
            gates["MODALITY"] = _gate("PASS", "NONSTANDARD_MODALITY_COMPATIBILITY_SUPPORTED_BY_EXPLICIT_EVIDENCE")
        else:
            gates["MODALITY"] = _gate("FAIL", "MODALITY_TARGET_COMPARTMENT_MISMATCH", target_compartment=compartment)

        # DELIVERY: indication implies a required tissue; explicit access evidence can override only with support.
        required_tissue = _REQUIRED_TISSUE.get(indication, _norm_status(evidence.get("required_tissue")))
        tissue_access = _norm_status(evidence.get("tissue_access_support"))
        if tissue_access == "CONTRADICTED":
            gates["DELIVERY"] = _gate("FAIL", "ROUTE_LOCALIZATION_DOES_NOT_SUPPORT_REQUIRED_TISSUE_ACCESS", required_tissue=required_tissue)
        elif tissue_access == "SUPPORTED":
            gates["DELIVERY"] = _gate("PASS", "REQUIRED_TISSUE_ACCESS_SUPPORTED", required_tissue=required_tissue)
        else:
            # Conservative generic incompatibilities; all other cases stay OPEN rather than guessed PASS.
            if required_tissue == "CNS" and "brain" not in localization.lower():
                gates["DELIVERY"] = _gate("FAIL", "CNS_INDICATION_WITHOUT_BRAIN_ACCESS_STRATEGY", required_tissue=required_tissue)
            elif required_tissue == "LIVER" and route.lower() == "inhaled":
                gates["DELIVERY"] = _gate("FAIL", "INHALED_ROUTE_WITHOUT_SYSTEMIC_LIVER_EXPOSURE_EVIDENCE", required_tissue=required_tissue)
            elif required_tissue == "SKIN" and route.lower() == "inhaled":
                gates["DELIVERY"] = _gate("FAIL", "INHALED_ROUTE_MISMATCH_FOR_SKIN_INDICATION", required_tissue=required_tissue)
            elif required_tissue == "LUNG" and route.lower() == "inhaled":
                gates["DELIVERY"] = _gate("OPEN", "DIRECT_LUNG_ROUTE_PLAUSIBLE_BUT_TISSUE_EXPOSURE_NOT_VERIFIED", required_tissue=required_tissue)
            else:
                gates["DELIVERY"] = _gate("OPEN", "TISSUE_EXPOSURE_NOT_ESTABLISHED", required_tissue=required_tissue)

        # PK/PD: absence of measurements is OPEN, never evidence of feasibility.
        pk = _norm_status(evidence.get("pk_support"))
        if pk == "CONTRADICTED":
            gates["PK"] = _gate("FAIL", "PK_EXPOSURE_CONTRADICTS_REQUIRED_TARGET_TISSUE_EXPOSURE")
        elif pk == "SUPPORTED":
            gates["PK"] = _gate("PASS", "PK_EXPOSURE_FEASIBILITY_SUPPORTED")
        else:
            gates["PK"] = _gate("OPEN", "PK_PARAMETERS_OR_EXPOSURE_UNMEASURED")

        pd = _norm_status(evidence.get("pd_support"))
        if pd == "CONTRADICTED":
            gates["PD"] = _gate("FAIL", "PD_TARGET_ENGAGEMENT_OR_PHENOTYPE_CONTRADICTED")
        elif pd == "SUPPORTED":
            gates["PD"] = _gate("PASS", "PD_TARGET_ENGAGEMENT_TO_PHENOTYPE_SUPPORTED")
        else:
            gates["PD"] = _gate("OPEN", "PD_TARGET_ENGAGEMENT_OR_DOSE_RESPONSE_UNMEASURED")

        failed = [g for g in HYPOTHESIS_GATE_SEQUENCE if gates[g]["status"] == "FAIL"]
        open_gates = [g for g in HYPOTHESIS_GATE_SEQUENCE if gates[g]["status"] == "OPEN"]
        critical_failed = [g for g in CRITICAL_HYPOTHESIS_GATES if gates[g]["status"] == "FAIL"]
        critical_open = [g for g in CRITICAL_HYPOTHESIS_GATES if gates[g]["status"] == "OPEN"]
        if critical_failed:
            overall = "REJECT_HYPOTHESIS_COMPATIBILITY_OR_CAUSAL_CONTRADICTION"
            retained = False
        elif not verification_world_ok:
            overall = "ENGINE_SCREEN_ONLY_WORLD_VERIFICATION_REQUIRED_FOR_RESEARCH_RETENTION"
            retained = False
        elif critical_open:
            overall = "RETAIN_OPEN_HYPOTHESIS_REQUIRES_CRITICAL_EVIDENCE"
            retained = True
        else:
            overall = "SURVIVES_HYPOTHESIS_COMPATIBILITY_GATES_PK_PD_STILL_FAIL_CLOSED"
            retained = True

        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "domain_id": "pharmaceutical",
            "coordinate": coord,
            "evidence": evidence,
            "raw_evidence_proposal": raw_evidence,
            "scientific_verification": verification,
            "gates": gates,
            "failed_gates": failed,
            "open_gates": open_gates,
            "critical_failed_gates": critical_failed,
            "critical_open_gates": critical_open,
            "retained_for_research": retained,
            "engine_screen_completed": verification_engine_ok,
            "world_verification_ready": verification_world_ok,
            "overall_status": overall,
            "clinical_efficacy_established": False,
            "clinical_safety_established": False,
            "patient_specific_recommendation_allowed": False,
            "promotion_allowed": False,
            "world_novelty_established": False,
        }
        return {**payload, "assessment_digest": digest_payload(payload)}

    def axis_subset(self, axis_ids: Sequence[str]) -> Mapping[str, Any]:
        registry = DOMAIN_REGISTRIES["pharmaceutical"]
        selected = tuple(dict.fromkeys(str(x) for x in axis_ids))
        missing = [x for x in selected if x not in registry.axes]
        if missing:
            raise ValueError(f"unknown pharmaceutical axes: {missing}")
        payload = {
            "domain_id": "pharmaceutical",
            "axis_ids": list(selected),
            "axis_count": len(selected),
            "full_domain_axis_count": registry.axis_count,
            "full_space_exhaustion_claimed": False,
        }
        return {**payload, "digest": digest_payload(payload)}


__all__ = [
    "PharmaceuticalDomainOwner", "OWNER_ID", "SCHEMA", "GATE_SEQUENCE",
    "HYPOTHESIS_GATE_SEQUENCE", "CRITICAL_HYPOTHESIS_GATES", "ICH_REFERENCES",
    "SOURCE_LOCKED_HYPOTHESIS_FIELDS", "semantic_state",
    "SELECTIVITY_BRIDGE_ID", "SELECTIVITY_BRIDGE_SCHEMA",
]
