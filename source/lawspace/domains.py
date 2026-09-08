"""Discipline-specific sparse axis registries.

Axis counts are always computed from the registries. No runtime claim stores a
manually maintained count.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from .schema import AxisConstraint, AxisDefinition, AxisProfile, AxisValueKind, DomainAxisRegistry


def _axis(domain: str, axis_id: str, description: str | None = None, *, kind: AxisValueKind = AxisValueKind.TEXT, values: Sequence[str] = ()) -> AxisDefinition:
    return AxisDefinition(axis_id, domain, description or f"Предметная ось «{axis_id}» в пространстве «{domain}»", kind, tuple(values))


def _registry(domain: str, description: str, groups: Sequence[Sequence[str]], *, role: str = "natural_science", profiles: Mapping[str, AxisProfile] | None = None, constraints: Sequence[AxisConstraint] = (), axis_overrides: Mapping[str, AxisDefinition] | None = None) -> DomainAxisRegistry:
    ids = [axis_id for group in groups for axis_id in group]
    if len(ids) != len(set(ids)):
        duplicates = sorted({x for x in ids if ids.count(x) > 1})
        raise ValueError(f"{domain}: duplicate axes {duplicates}")
    overrides = dict(axis_overrides or {})
    unknown_overrides = sorted(set(overrides) - set(ids))
    if unknown_overrides:
        raise ValueError(f"{domain}: axis overrides for unregistered ids {unknown_overrides}")
    axes = {axis_id: overrides.get(axis_id, _axis(domain, axis_id)) for axis_id in ids}
    return DomainAxisRegistry(domain, "2.8.0", description, axes, profiles or {}, tuple(constraints), role)


DOMAIN_PLUGIN_MANIFEST_SCHEMA = "phi-domain-plugin-manifest/v1"


def _domain_plugin_manifest_dir() -> Path:
    override = os.environ.get("PHI_DOMAIN_PLUGIN_MANIFEST_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data" / "domains"


def load_domain_plugin_manifests(path: str | Path | None = None) -> Dict[str, Mapping[str, Any]]:
    """Load declarative domain registries.

    A new science can be connected by adding one manifest under ``data/domains``
    plus, when domain-specific semantics are needed, an owner module named by the
    manifest. Generic evidence, research-cycle and promotion rules are not copied
    into the domain manifest.
    """
    root = Path(path) if path is not None else _domain_plugin_manifest_dir()
    if not root.exists():
        return {}
    manifests: Dict[str, Mapping[str, Any]] = {}
    for file in sorted(root.glob("*.json")):
        doc = json.loads(file.read_text(encoding="utf-8"))
        if doc.get("schema") != DOMAIN_PLUGIN_MANIFEST_SCHEMA:
            raise ValueError(f"unsupported domain plugin manifest schema in {file.name}: {doc.get('schema')!r}")
        domain_id = str(doc.get("domain_id", "")).strip()
        if not domain_id:
            raise ValueError(f"domain plugin manifest without domain_id: {file}")
        if domain_id in manifests:
            raise ValueError(f"duplicate domain plugin manifest for {domain_id!r}")
        if str(doc.get("common_rules_owner", "")) != "COMMON-SCIENTIFIC-RULES/1.0.0":
            raise ValueError(f"{domain_id}: plugin must delegate generic rules to COMMON-SCIENTIFIC-RULES/1.0.0")
        forbidden_generic_keys = {
            "generic_rules", "scientific_verification_rules", "scientific_promotion_rules",
            "novelty_rules", "eig_rules", "evidence_rules",
        }
        shadowed = sorted(forbidden_generic_keys & set(doc))
        if shadowed:
            raise ValueError(f"{domain_id}: generic scientific rules must not be copied into a domain manifest: {shadowed}")
        axes = doc.get("axes", ())
        if not isinstance(axes, list):
            raise ValueError(f"{domain_id}: axes must be a list")
        axis_ids = [str(dict(row).get("axis_id", "")).strip() for row in axes]
        if any(not x for x in axis_ids):
            raise ValueError(f"{domain_id}: every plugin axis requires a non-empty axis_id")
        if len(axis_ids) != len(set(axis_ids)):
            duplicates = sorted({x for x in axis_ids if axis_ids.count(x) > 1})
            raise ValueError(f"{domain_id}: duplicate plugin axes {duplicates}")
        owner = doc.get("owner", {}) or {}
        if not isinstance(owner, dict):
            raise ValueError(f"{domain_id}: owner must be an object")
        module_name = str(owner.get("module", "")).strip()
        class_name = str(owner.get("class", "")).strip()
        if bool(module_name) != bool(class_name):
            raise ValueError(f"{domain_id}: owner.module and owner.class must be declared together")
        manifests[domain_id] = doc
    return manifests


def _registry_from_plugin_manifest(doc: Mapping[str, Any]) -> DomainAxisRegistry:
    domain = str(doc["domain_id"])
    axes: Dict[str, AxisDefinition] = {}
    for row0 in doc.get("axes", ()):
        row = dict(row0)
        axis = AxisDefinition(
            axis_id=str(row["axis_id"]),
            domain=domain,
            description_ru=str(row.get("description_ru") or f"Предметная ось «{row['axis_id']}» в пространстве «{domain}»"),
            value_kind=AxisValueKind(str(row.get("value_kind", "TEXT"))),
            allowed_values=tuple(str(x) for x in row.get("allowed_values", ())),
            required_for=tuple(str(x) for x in row.get("required_for", ())),
            forbidden_for=tuple(str(x) for x in row.get("forbidden_for", ())),
            provenance=str(row.get("provenance", f"DOMAIN_PLUGIN:{domain}")),
        )
        if axis.axis_id in axes:
            raise ValueError(f"{domain}: duplicate plugin axis {axis.axis_id!r}")
        axes[axis.axis_id] = axis
    profiles: Dict[str, AxisProfile] = {}
    for row0 in doc.get("entity_profiles", ()):
        row = dict(row0)
        profile = AxisProfile(
            str(row["profile_id"]),
            tuple(str(x) for x in row.get("allowed_axes", ())),
            required_axes=tuple(str(x) for x in row.get("required_axes", ())),
            forbidden_axes=tuple(str(x) for x in row.get("forbidden_axes", ())),
        )
        if profile.profile_id in profiles:
            raise ValueError(f"{domain}: duplicate plugin profile {profile.profile_id!r}")
        referenced = set(profile.allowed_axes) | set(profile.required_axes) | set(profile.forbidden_axes)
        unknown = sorted(referenced - set(axes))
        if unknown:
            raise ValueError(f"{domain}: profile {profile.profile_id!r} references unknown axes {unknown}")
        profiles[profile.profile_id] = profile
    if doc.get("constraints"):
        raise ValueError(f"{domain}: declarative constraint decoding is not enabled; use the domain owner for domain-specific constraints")
    return DomainAxisRegistry(
        domain,
        str(doc.get("axis_schema_version", "2.8.0")),
        str(doc.get("description_ru", domain)),
        axes, profiles, (), str(doc.get("domain_role", "natural_science")),
    )


PHYSICS_GROUPS = (
    ("physical_entity", "state_carrier", "state_space", "algebra", "equation_family", "expression_role", "time_order", "space_order", "tensor_rank", "form_degree", "linearity_state", "linearity_parameters"),
    ("spatial_dimension", "temporal_dimension", "signature", "coordinate_frame", "geometry_dynamics", "curvature_regime", "connection_type", "torsion", "metric_structure", "topology", "boundary_geometry", "singularity_class", "regularity_class"),
    ("determinism", "probability_model", "stochastic_calculus", "locality", "interaction_range", "memory", "openness", "causal_structure", "causal_order", "reversibility", "time_symmetry", "dissipation", "generator_type", "conservation_structure"),
    ("spacetime_symmetry", "internal_symmetry", "gauge_group", "symmetry_realization", "symmetry_breaking", "interaction_sector", "charge_structure", "constraint_algebra", "variational_structure", "hamiltonian_structure"),
    ("scale_regime", "multiscale_structure", "renormalization_status", "RG_regime", "effective_order", "semiclassical_order", "perturbation_order", "continuum_discrete_status", "thermodynamic_limit", "classical_quantum_regime", "relativistic_regime"),
    ("observable_type", "measurement_model", "detector_coupling", "experimental_control", "identifiability_class", "data_regime", "noise_model"),
    ("scientific_coordinate_role", "state_relation_structure", "geometric_relation_structure", "scale_invariance_structure", "dimensionless_group_structure", "periodic_phase_structure", "thermal_coupling_structure", "relativistic_coupling_structure", "resonance_structure", "coherence_structure", "response_coordinate_structure", "metrology_consistency"),
    # 15.6.0: reusable coordinate archetypes migrated from research-local procedural
    # knowledge into the canonical Atlas.  These are coordinate classes, not laws.
    ("state_difference_coordinate", "typed_additive_coordinate", "dimensionless_ratio_coordinate", "euclidean_distance_coordinate",
     "euclidean_norm_coordinate", "dot_product_coordinate", "weighted_state_mean_coordinate",
     "thermal_energy_coordinate", "phase_action_coordinate", "detuning_phase_coordinate",
     "quantum_action_phase_coordinate", "thermal_quantum_ratio_coordinate",
     "coherent_cross_magnitude_coordinate", "coherent_phase_projection_coordinate",
     "coherent_superposition_intensity_coordinate", "relativistic_beta_coordinate",
     "relativistic_pair_coupling_coordinate", "relativistic_spacetime_coordinate",
     "resonance_coordinate", "direction_cosine_coordinate", "orientational_thermal_coordinate",
     "periodic_response_coordinate", "cosine_law_coordinate", "evidence_born_response_coordinate"),
)
MECHANICS_GROUPS = (
    ("mechanical_object", "body_dimension", "material_description", "configuration_space", "degrees_of_freedom", "mass_distribution", "inertia_structure"),
    ("kinematic_mode", "reference_configuration", "reference_frame", "coordinate_description", "motion_map", "strain_measure", "rotation_representation", "velocity_field_type"),
    ("mechanical_generator", "force_type", "load_type", "inertia_regime", "excitation", "control_mode", "potential_structure", "energy_structure", "momentum_balance", "angular_momentum_balance"),
    ("constraint_type", "constraint_integrability", "contact_type", "friction_model", "impact_model", "joint_type", "boundary_support"),
    ("deformation_regime", "constitutive_class", "material_symmetry", "elasticity_class", "plasticity_class", "viscoelasticity_class", "damage_model", "fracture_model", "rheology", "compressibility"),
    ("flow_regime", "turbulence_regime", "dimensionless_regime", "stability_type", "bifurcation_type", "wave_type", "dispersion_type", "failure_mode"),
)
CHEMISTRY_GROUPS = (
    ("chemical_entity_type", "elemental_composition", "isotopic_composition", "formal_charge", "oxidation_state", "spin_state", "electronic_state", "molecularity", "molecular_structure", "bonding_pattern", "functional_groups", "stereochemistry", "conformation", "tautomeric_state", "protonation_state"),
    ("phase", "phase_count", "mixture_type", "solvent", "solvation_model", "temperature_regime", "pressure_regime", "pH_regime", "ionic_strength", "composition_measure", "standard_state", "activity_model", "fugacity_model"),
    ("reaction_class", "reaction_directionality", "stoichiometry", "element_balance", "charge_balance", "electron_balance", "reaction_center", "mechanism_class", "elementary_step_count", "molecularity_of_step", "intermediate_structure", "transition_state_model"),
    ("kinetic_law", "reaction_order", "rate_coefficient_model", "temperature_dependence", "pressure_dependence", "catalysis", "inhibition", "activation_model", "timescale_separation", "steady_state_approximation", "pre_equilibrium"),
    ("thermodynamic_ensemble", "reaction_enthalpy", "reaction_entropy", "reaction_gibbs_energy", "chemical_potential_model", "equilibrium_type", "equilibrium_constant_type", "phase_equilibrium", "stability_condition"),
    ("photochemical_regime", "electrochemical_regime", "surface_reaction", "heterogeneous_catalysis", "plasma_chemistry", "combustion_regime", "polymerization_regime", "transport_limitation", "reaction_diffusion_regime"),
    ("analytical_method", "instrument_type", "spectroscopy_type", "separation_method", "sample_preparation", "quantum_chemical_method", "basis_set", "electronic_correlation_level", "property_source"),
)

MATHEMATICS_GROUPS = (("mathematical_entity", "formal_language", "axiom_system", "logic", "algebraic_structure", "order_structure", "topological_structure", "geometric_structure", "measure_structure", "category_structure", "equivalence_relation", "proof_status", "proof_method", "regularity", "existence", "uniqueness", "stability", "computability", "complexity_class", "controlled_limit"),)
METROLOGY_GROUPS = (("quantity_kind", "dimension_vector", "unit_system", "canonical_unit", "scale_type", "traceability_chain", "calibration_model", "measurement_model", "instrument_class", "sampling_regime", "resolution", "repeatability", "reproducibility", "uncertainty_model", "covariance_model", "reference_condition", "standard_edition", "data_quality"),)
MATERIALS_GROUPS = (("material_entity", "composition", "microstructure", "phase_structure", "defect_structure", "grain_structure", "interface_structure", "processing_history", "thermodynamic_state", "kinetic_state", "transport_property", "mechanical_property", "electrical_property", "magnetic_property", "optical_property", "thermal_property", "constitutive_model", "multiphysics_coupling", "damage_state", "fracture_state", "fatigue_state", "aging_state", "environmental_interaction", "length_scale", "time_scale", "characterization_method", "manufacturing_route", "property_provenance"),)
BIOLOGY_GROUPS = (("organization_level", "cellular_component", "molecular_function", "biological_process", "regulatory_network", "genotype", "phenotype", "evolutionary_regime", "population_structure", "homeostasis", "developmental_space", "developmental_time"),)
EARTH_GROUPS = (("earth_compartment", "geological_medium", "stratigraphy", "atmospheric_ocean_layer", "geographic_coordinate_system", "spatial_resolution", "temporal_averaging", "forcing", "boundary_exchange", "biogeochemical_cycle", "climate_ensemble", "assimilation_regime"),)
ASTRONOMY_GROUPS = (("celestial_coordinate_system", "redshift", "epoch", "time_system", "spectral_band", "angular_resolution", "luminosity_distance", "observational_selection", "survey_geometry", "source_morphology", "gravitational_regime", "cosmological_background", "instrumental_response"),)
QUANTUM_INFORMATION_COMPUTATIONAL_METHODS_GROUPS = (
    ("problem_class", "simulation_object", "state_type", "local_dimension", "qubit_count", "circuit_depth", "gate_locality", "circuit_geometry", "interaction_graph", "hardware_topology"),
    ("representation_family", "tensor_network_geometry", "bond_dimension", "operator_bond_dimension", "treewidth", "linear_rank_width", "decision_diagram_size", "path_sum_form", "contraction_width", "contraction_order_policy", "network_restructuring_policy", "slicing_strategy", "checkpoint_policy"),
    ("entanglement_entropy", "operator_entanglement", "entanglement_growth_rate", "correlation_length", "symmetry_sector", "conservation_sector", "low_rank_structure", "sparsity_structure", "fermionic_gaussianity", "bosonic_gaussianity"),
    ("stabilizer_rank", "stabilizer_extent", "t_gate_count", "magic_monotone", "non_clifford_structure", "code_compilation_status", "permutation_tracking", "measurement_pattern", "reset_pattern", "feedforward_structure"),
    ("open_system_regime", "noise_model_class", "noise_correlation_length", "noise_memory_time", "noise_compression_strength", "unravelling_method", "trajectory_count", "process_tensor_bond_dimension", "temporal_memory_length", "operator_space_dimension"),
    ("truncation_strategy", "truncation_budget", "truncation_norm", "observable_error_budget", "fidelity_error_budget", "time_step_error", "sampling_error", "roundoff_error", "validation_reference", "exactness_class"),
    ("backend_type", "precision_mode", "cpu_memory_budget", "gpu_memory_budget", "gpu_count", "interconnect_type", "parallel_decomposition", "communication_collective", "communication_cost_model", "load_balance_policy", "fault_tolerance", "reproducibility_level"),
)


AERONAUTICS_AEROSTATION_GROUPS = (
    ("vehicle_class", "lift_principle", "configuration", "mission_type", "mission_phase", "flight_regime", "altitude_regime", "speed_regime", "endurance_regime", "payload_fraction", "energy_source", "certification_class"),
    ("atmosphere_model", "atmospheric_layer", "air_density", "static_pressure", "static_temperature", "dynamic_viscosity", "kinematic_viscosity", "speed_of_sound", "mach_number", "reynolds_number", "knudsen_number", "compressibility_regime", "rarefaction_regime", "wind_field", "turbulence_intensity", "gust_spectrum", "weather_time_series", "cubic_wind_moment", "solar_irradiance"),
    ("lifting_surface_type", "wing_planform", "wing_area", "span", "aspect_ratio", "span_efficiency", "sweep", "taper_ratio", "thickness_ratio", "camber", "angle_of_attack", "lift_coefficient", "drag_coefficient", "zero_lift_drag", "induced_drag", "lift_curve_slope", "stall_model", "maximum_lift_coefficient", "high_lift_system", "wave_drag_regime"),
    ("boundary_layer_state", "transition_model", "transition_reynolds", "surface_roughness", "wall_temperature_ratio", "heat_transfer_regime", "stagnation_temperature", "skin_friction_model", "separation_state", "laminar_flow_control", "pressure_gradient", "shock_boundary_layer_interaction", "wall_heat_flux", "areal_heat_capacity", "transition_heat_flux_ratio"),
    ("structural_model", "wing_loading", "load_factor", "gust_model", "gust_velocity", "mass_ratio", "bending_stiffness", "torsional_stiffness", "aeroelastic_divergence", "flutter_boundary", "modal_damping", "fatigue_state", "buckling_state", "damage_tolerance", "structural_temperature", "aeroservoelastic_state", "flexible_mode_frequency", "thermoelastic_stress", "thermal_dwell_time", "thermal_expansion_coefficient"),
    ("propulsion_type", "thrust_model", "propulsive_efficiency", "specific_fuel_consumption", "shaft_power", "disk_loading", "rotor_solidity", "tip_mach", "propeller_advance_ratio", "distributed_propulsion", "energy_storage", "thermal_efficiency", "engine_operating_point", "inlet_regime", "nozzle_regime", "auxiliary_power", "storage_state_of_charge", "storage_usable_capacity", "storage_loss_power"),
    ("lifting_gas", "buoyancy_fraction", "gas_density", "envelope_volume", "envelope_area", "envelope_areal_density", "fineness_ratio", "ballonet_state", "superpressure", "mooring_state", "static_heaviness", "gas_temperature_ratio", "envelope_permeability"),
    ("rotor_count", "rotor_disk_area", "hover_regime", "induced_velocity", "figure_of_merit", "transition_mode", "tilt_angle", "wake_interaction", "ground_effect", "rotor_hull_interaction"),
    ("longitudinal_static_margin", "lateral_stability", "directional_stability", "control_authority", "trim_state", "control_surface", "flight_control_law", "gust_alleviation", "actuator_bandwidth", "sensor_suite", "state_estimator", "fault_tolerance_mode", "closed_loop_transfer", "load_response_spectrum", "control_effort_spectrum"),
    ("range_model", "endurance_model", "climb_rate", "service_ceiling", "stall_speed", "cruise_speed", "station_keeping", "wind_speed", "takeoff_distance", "landing_distance", "turn_rate", "turn_radius", "flight_envelope"),
    ("airframe_material", "envelope_material", "composite_layup", "temperature_limit", "stress_limit", "manufacturing_route", "surface_finish", "joining_method", "corrosion_state"),
    ("wind_tunnel_model", "flight_test_condition", "cfd_fidelity", "turbulence_model", "uncertainty_model", "observable", "validation_source", "data_regime", "falsification_metric", "model_discrepancy"),
)

SYSTEMS_CONTROL_GROUPS = (("system_model", "state_estimation", "identifiability", "observability", "controllability", "causal_inference", "inverse_problem", "data_assimilation", "experiment_design", "next_measurement_policy", "model_failure_class", "truth_access_boundary"),)


def build_domain_registries() -> Dict[str, DomainAxisRegistry]:
    physics = _registry("physics", "Поля, взаимодействия, пространство-время, квантовая и статистическая физика", PHYSICS_GROUPS)
    mechanics = _registry(
        "mechanics", "Движение, силы, связи, деформации, континуумы, контакт и устойчивость", MECHANICS_GROUPS,
        profiles={
            "material_point": AxisProfile("material_point", tuple(x for g in MECHANICS_GROUPS for x in g if x not in {"strain_measure", "deformation_regime", "plasticity_class", "fracture_model"}), forbidden_axes=("strain_measure", "deformation_regime", "plasticity_class", "fracture_model")),
            "deformable_body": AxisProfile("deformable_body", tuple(x for g in MECHANICS_GROUPS for x in g), required_axes=("mechanical_object", "configuration_space", "strain_measure", "constitutive_class")),
        },
    )
    chemistry = _registry(
        "chemistry", "Вещества, реакции, кинетика, равновесие, механизмы и среды", CHEMISTRY_GROUPS,
        profiles={
            "chemical_species": AxisProfile("chemical_species", tuple(x for g in CHEMISTRY_GROUPS[:2] for x in g), forbidden_axes=("reaction_order", "kinetic_law")),
            "rate_law": AxisProfile("rate_law", tuple(x for g in CHEMISTRY_GROUPS for x in g), required_axes=("kinetic_law", "reaction_order")),
        },
    )
    registries = {
        "mathematics": _registry("mathematics", "Формальные структуры, определения, теоремы и доказательства", MATHEMATICS_GROUPS, role="formal_science"),
        "metrology": _registry("metrology", "Величины, единицы, измерения, калибровка и неопределённость", METROLOGY_GROUPS, role="semantic_infrastructure"),
        "physics": physics,
        "mechanics": mechanics,
        "chemistry": chemistry,
        "materials_science": _registry("materials_science", "Микроструктура, фазы, свойства, конститутивные модели и повреждение", MATERIALS_GROUPS),
        "biology": _registry("biology", "Биологические уровни, функции, процессы, регуляция и эволюция", BIOLOGY_GROUPS),
        "earth_systems": _registry("earth_systems", "Геосферы, атмосфера, океан, климат и биогеохимические циклы", EARTH_GROUPS),
        "astronomy": _registry("astronomy", "Наблюдательная астрономия и космология", ASTRONOMY_GROUPS),
        "aeronautics_and_aerostation": _registry(
            "aeronautics_and_aerostation",
            "Авиастроение и воздухоплавание: аэродинамика, газодинамика, атмосфера, конструкции, аэроупругость, силовые установки, аэростаты, вертикальный взлёт, управление, эксплуатация и валидация",
            AERONAUTICS_AEROSTATION_GROUPS,
            role="engineering_science",
            profiles={
                "fixed_wing": AxisProfile("fixed_wing", tuple(x for g in AERONAUTICS_AEROSTATION_GROUPS for x in g), required_axes=("vehicle_class", "wing_loading", "lift_coefficient", "drag_coefficient", "flight_envelope")),
                "airship": AxisProfile("airship", tuple(x for g in AERONAUTICS_AEROSTATION_GROUPS for x in g), required_axes=("vehicle_class", "lifting_gas", "envelope_volume", "buoyancy_fraction", "station_keeping")),
                "rotorcraft_or_hybrid": AxisProfile("rotorcraft_or_hybrid", tuple(x for g in AERONAUTICS_AEROSTATION_GROUPS for x in g), required_axes=("vehicle_class", "rotor_disk_area", "disk_loading", "hover_regime")),
            },
        ),
        "systems_control": _registry("systems_control", "Идентификация, обратные задачи, управление и выбор измерений", SYSTEMS_CONTROL_GROUPS, role="methodological"),
        "quantum_information_and_computational_methods": _registry(
            "quantum_information_and_computational_methods",
            "Квантовая информация, классические представления квантовых состояний, алгоритмы сжатия, оценка ошибки и аппаратная стоимость",
            QUANTUM_INFORMATION_COMPUTATIONAL_METHODS_GROUPS,
            role="computational_science",
            profiles={
                "tensor_network_method": AxisProfile("tensor_network_method", tuple(x for g in QUANTUM_INFORMATION_COMPUTATIONAL_METHODS_GROUPS for x in g), required_axes=("representation_family", "bond_dimension", "truncation_budget", "observable_error_budget")),
                "stabilizer_method": AxisProfile("stabilizer_method", tuple(x for g in QUANTUM_INFORMATION_COMPUTATIONAL_METHODS_GROUPS for x in g), required_axes=("representation_family", "t_gate_count", "magic_monotone")),
                "open_system_method": AxisProfile("open_system_method", tuple(x for g in QUANTUM_INFORMATION_COMPUTATIONAL_METHODS_GROUPS for x in g), required_axes=("open_system_regime", "noise_model_class", "observable_error_budget")),
            },
        ),
    }
    for domain_id, manifest in sorted(load_domain_plugin_manifests().items()):
        if domain_id in registries:
            raise ValueError(f"domain plugin conflicts with built-in registry {domain_id!r}")
        registries[domain_id] = _registry_from_plugin_manifest(manifest)

    # Structural validation only.  Canonical axis counts are a runtime snapshot,
    # never a truth gate or an architectural ceiling.
    for domain_id, registry in registries.items():
        if registry.axis_count <= 0:
            raise AssertionError(f"{domain_id}: empty canonical axis registry")
        if len(registry.axes) != len(set(registry.axes)):
            raise AssertionError(f"{domain_id}: duplicate canonical axis id")
    return registries


DYNAMIC_AXIS_REGISTRY_SCHEMA = "phi-canonical-dynamic-axis-registry/v8.0"
DYNAMIC_AXIS_REGISTRY_OWNER = "DYNAMIC-AXIS-PROMOTION/8.0.0"


def _default_dynamic_axis_registry_path() -> Path:
    override = os.environ.get("PHI_DYNAMIC_AXIS_REGISTRY_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data" / "axes" / "canonical_dynamic_axes.json"


def _read_dynamic_axis_registry(path: Path | None = None) -> Mapping[str, Any]:
    path = Path(path or _default_dynamic_axis_registry_path())
    if not path.exists():
        return {"schema": DYNAMIC_AXIS_REGISTRY_SCHEMA, "owner": DYNAMIC_AXIS_REGISTRY_OWNER, "entries": []}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != DYNAMIC_AXIS_REGISTRY_SCHEMA:
        raise ValueError(f"unsupported dynamic axis registry schema: {doc.get('schema')!r}")
    if not isinstance(doc.get("entries"), list):
        raise ValueError("dynamic axis registry entries must be a list")
    return doc


def _axis_from_dynamic_entry(entry: Mapping[str, Any]) -> AxisDefinition:
    row = dict(entry.get("axis_definition", {}))
    return AxisDefinition(
        axis_id=str(row["axis_id"]),
        domain=str(row["domain"]),
        description_ru=str(row["description_ru"]),
        value_kind=AxisValueKind(str(row.get("value_kind", "TEXT"))),
        allowed_values=tuple(str(x) for x in row.get("allowed_values", ())),
        required_for=tuple(str(x) for x in row.get("required_for", ())),
        forbidden_for=tuple(str(x) for x in row.get("forbidden_for", ())),
        provenance=str(row.get("provenance", "CANONICAL_DYNAMIC")),
    )


def _apply_dynamic_axis_entries(registries: Dict[str, DomainAxisRegistry], entries: Sequence[Mapping[str, Any]]) -> Dict[str, DomainAxisRegistry]:
    out = dict(registries)
    for entry in sorted(entries, key=lambda row: (str(row.get("axis_definition", {}).get("domain", "")), str(row.get("axis_definition", {}).get("axis_id", "")))):
        axis = _axis_from_dynamic_entry(entry)
        if axis.domain not in out:
            raise ValueError(f"dynamic axis references unknown domain {axis.domain!r}")
        registry = out[axis.domain]
        if axis.axis_id in registry.axes:
            existing = registry.axes[axis.axis_id]
            if existing != axis:
                raise ValueError(f"dynamic axis conflicts with registered axis {axis.domain}:{axis.axis_id}")
            continue
        axes = dict(registry.axes)
        axes[axis.axis_id] = axis
        out[axis.domain] = DomainAxisRegistry(
            registry.domain_id, registry.schema_version, registry.description_ru, axes,
            registry.entity_profiles, registry.constraints, registry.domain_role,
        )
    return out


BASE_DOMAIN_REGISTRIES = build_domain_registries()
DOMAIN_REGISTRIES = _apply_dynamic_axis_entries(dict(BASE_DOMAIN_REGISTRIES), _read_dynamic_axis_registry().get("entries", ()))
MANDATORY_CORE_DOMAINS = ("mathematics", "metrology", "physics", "mechanics", "chemistry", "materials_science")
PLUGGABLE_DOMAINS = tuple(sorted(set(("biology", "earth_systems", "astronomy", "aeronautics_and_aerostation")) | set(load_domain_plugin_manifests())))
METHODOLOGICAL_DOMAINS = ("systems_control",)
COMPUTATIONAL_DOMAINS = ("quantum_information_and_computational_methods",)


def canonical_axis_count(*, include_dynamic: bool = True) -> int:
    source = DOMAIN_REGISTRIES if include_dynamic else BASE_DOMAIN_REGISTRIES
    return sum(reg.axis_count for reg in source.values())


def dynamic_axis_registry_state(path: Path | None = None) -> Mapping[str, Any]:
    doc = dict(_read_dynamic_axis_registry(path))
    entries = list(doc.get("entries", ()))
    payload = {
        "schema": DYNAMIC_AXIS_REGISTRY_SCHEMA,
        "owner": DYNAMIC_AXIS_REGISTRY_OWNER,
        "path": str(Path(path or _default_dynamic_axis_registry_path())),
        "base_axis_count": canonical_axis_count(include_dynamic=False),
        "dynamic_axis_count": len(entries),
        "canonical_axis_count": canonical_axis_count(include_dynamic=True),
        "entries": entries,
    }
    return payload


def install_canonical_dynamic_axis(entry: Mapping[str, Any], path: Path | None = None) -> Mapping[str, Any]:
    """Low-level persistence primitive. Only DynamicAxisPromotionOwner may call this."""
    path = Path(path or _default_dynamic_axis_registry_path())
    doc = dict(_read_dynamic_axis_registry(path))
    entries = list(doc.get("entries", ()))
    axis = _axis_from_dynamic_entry(entry)
    if axis.domain not in BASE_DOMAIN_REGISTRIES:
        raise ValueError(f"unknown domain {axis.domain!r}")
    if axis.axis_id in BASE_DOMAIN_REGISTRIES[axis.domain].axes:
        raise ValueError(f"cannot dynamically replace base canonical axis {axis.domain}:{axis.axis_id}")
    for existing_entry in entries:
        existing = _axis_from_dynamic_entry(existing_entry)
        if existing.domain == axis.domain and existing.axis_id == axis.axis_id:
            if dict(existing_entry) == dict(entry):
                return {"status": "IDEMPOTENT_ALREADY_REGISTERED", "axis_id": axis.axis_id, "domain_id": axis.domain, "path": str(path)}
            raise ValueError(f"conflicting dynamic axis registration {axis.domain}:{axis.axis_id}")
    entries.append(dict(entry))
    entries.sort(key=lambda row: (str(row.get("axis_definition", {}).get("domain", "")), str(row.get("axis_definition", {}).get("axis_id", ""))))
    out = {
        "schema": DYNAMIC_AXIS_REGISTRY_SCHEMA,
        "owner": DYNAMIC_AXIS_REGISTRY_OWNER,
        "base_axis_count": sum(reg.axis_count for reg in BASE_DOMAIN_REGISTRIES.values()),
        "dynamic_axis_count": len(entries),
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    refreshed = _apply_dynamic_axis_entries(dict(BASE_DOMAIN_REGISTRIES), entries)
    DOMAIN_REGISTRIES.clear(); DOMAIN_REGISTRIES.update(refreshed)
    return {
        "status": "REGISTERED_CANONICAL_DYNAMIC_AXIS",
        "axis_id": axis.axis_id,
        "domain_id": axis.domain,
        "dynamic_axis_count": len(entries),
        "canonical_axis_count": sum(reg.axis_count for reg in DOMAIN_REGISTRIES.values()),
        "path": str(path),
    }


def reload_dynamic_axis_registry(path: Path | None = None) -> Mapping[str, Any]:
    doc = _read_dynamic_axis_registry(path)
    refreshed = _apply_dynamic_axis_entries(dict(BASE_DOMAIN_REGISTRIES), doc.get("entries", ()))
    DOMAIN_REGISTRIES.clear(); DOMAIN_REGISTRIES.update(refreshed)
    return dynamic_axis_registry_state(path)


def registry_digest_map() -> Dict[str, str]:
    return {domain: registry.digest for domain, registry in sorted(DOMAIN_REGISTRIES.items())}
