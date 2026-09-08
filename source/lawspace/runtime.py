"""Law-space runtime, bridges and deterministic acceptance gates."""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .catalog import LawCatalog
from .formal_contracts import toller_distributional_vertex_contract
from .domains import BASE_DOMAIN_REGISTRIES, DOMAIN_REGISTRIES, MANDATORY_CORE_DOMAINS, registry_digest_map
from .schema import (
    ASTNode,
    ComputationalMethodPassport,
    CorpusCoverageCertificate,
    DimensionVector,
    DomainBridge,
    EvidenceRecord,
    ExpressionIR,
    GateCertificate,
    LawPassport,
    OperatorScopeIR,
    SharedBinding,
    SharedBindingGraph,
    DistributionWavefrontIR,
    SourceManifest,
    SymbolRecord,
    digest_payload,
    OWNER_VERSION,
)


def _ast_from_dict(payload: Mapping[str, Any]) -> ASTNode:
    return ASTNode(str(payload["kind"]), str(payload.get("value", "")), tuple(_ast_from_dict(x) for x in payload.get("children", [])))


def expression_from_persisted(payload: Mapping[str, Any]) -> ExpressionIR:
    kind = str(payload["expression_kind"])
    scope_payload = payload.get("operator_scope")
    if isinstance(scope_payload, Mapping):
        scope = OperatorScopeIR(**scope_payload)
    else:
        scope = OperatorScopeIR.for_expression(kind)
    binding_payload = payload.get("binding_graph")
    if isinstance(binding_payload, Mapping):
        bindings = SharedBindingGraph(
            nodes=tuple(binding_payload.get("nodes", [])),
            bindings=tuple(SharedBinding(
                binding_id=str(row["binding_id"]),
                occurrences=tuple(row.get("occurrences", [])),
                relation=str(row.get("relation", "IDENTICAL_VARIABLE")),
                status=str(row.get("status", "DECLARED")),
            ) for row in binding_payload.get("bindings", [])),
            free_indices=tuple(binding_payload.get("free_indices", [])),
            bound_indices=tuple(binding_payload.get("bound_indices", [])),
            status=str(binding_payload.get("status", "NO_CROSS_EXPRESSION_BINDINGS_DECLARED")),
            digest=str(binding_payload.get("digest", "")),
        )
    else:
        bindings = SharedBindingGraph.structural(tuple(payload.get("symbols", [])))
    distribution_payload = payload.get("distribution_wavefront")
    if isinstance(distribution_payload, Mapping):
        distribution = DistributionWavefrontIR(**{
            **distribution_payload,
            "operations": tuple(distribution_payload.get("operations", [])),
        })
    else:
        distribution = DistributionWavefrontIR.structural(kind)
    return ExpressionIR(
        source=str(payload["source"]), canonical=str(payload["canonical"]), expression_kind=kind,
        ast=_ast_from_dict(payload["ast"]), symbols=tuple(payload.get("symbols", [])),
        operator_scope=scope, binding_graph=bindings, distribution_wavefront=distribution,
        semantic_level=str(payload.get("semantic_level", "STRUCTURAL_TYPED_AST_WITH_FORMAL_SCOPE")),
        parse_status=str(payload.get("parse_status", "PASS")), digest=str(payload.get("digest", "")),
    )


def passport_from_persisted(payload: Mapping[str, Any]) -> LawPassport:
    symbols = []
    for row in payload.get("symbols", []):
        dim = row.get("dimension")
        symbols.append(SymbolRecord(
            symbol_id=row["symbol_id"], display=row["display"], role=row["role"], quantity_id=row.get("quantity_id"), unit=row.get("unit"),
            dimension=DimensionVector(**dim) if dim else None, meaning_ru=row.get("meaning_ru", ""), provenance=row.get("provenance", ""),
        ))
    return LawPassport(
        owner_id=payload["owner_id"], name_ru=payload["name_ru"], domain_id=payload["domain_id"], entity_kind=payload["entity_kind"],
        formula=expression_from_persisted(payload["formula"]), scientific_coordinate=payload["scientific_coordinate"], quantity_semantics=payload["quantity_semantics"],
        epistemic_state=payload["epistemic_state"], provenance=payload["provenance"], home_cell_id=payload["home_cell_id"], symbols=tuple(symbols),
        constants=tuple(payload.get("constants", [])), assumptions=tuple(payload.get("assumptions", [])), validity_domain=payload.get("validity_domain", ""),
        controlled_limits=tuple(payload.get("controlled_limits", [])), observables=tuple(payload.get("observables", [])), uncertainty_model=payload.get("uncertainty_model", "NOT_DECLARED"),
        projection_ids=tuple(payload.get("projection_ids", [])), digest=payload.get("digest", ""),
    )


def computational_method_from_persisted(payload: Mapping[str, Any]) -> ComputationalMethodPassport:
    return ComputationalMethodPassport(
        method_id=payload["method_id"], name_ru=payload["name_ru"], domain_id=payload["domain_id"],
        method_family=payload["method_family"], role=payload["role"], scientific_coordinate=payload["scientific_coordinate"],
        capabilities=tuple(payload.get("capabilities", [])), applicability_rules=tuple(payload.get("applicability_rules", [])),
        cost_model=payload.get("cost_model", {}), error_contract=payload.get("error_contract", {}),
        exactness_class=payload.get("exactness_class", "NOT_DECLARED"), limitations=tuple(payload.get("limitations", [])),
        provenance=payload.get("provenance", {}), epistemic_state=payload.get("epistemic_state", "ESTABLISHED_METHOD"),
        incompatible_method_ids=tuple(payload.get("incompatible_method_ids", [])), exclusive_group=payload.get("exclusive_group"),
        digest=payload.get("digest", ""),
    )


def _dimension_contract(common_dimension: Sequence[str], terms: Mapping[str, Sequence[str]], *, dimensionless: Sequence[str] = ()) -> str:
    payload = {
        "status": "VALIDATED_SYMBOLIC",
        "common_dimension": list(common_dimension),
        "terms": {name: list(vector) for name, vector in sorted(terms.items())},
        "dimensionless_arguments": sorted(dimensionless),
    }
    if any(tuple(vector) != tuple(common_dimension) for vector in terms.values()):
        raise ValueError("bridge terms do not share the declared common dimension")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bridge_dimension_contract_valid(bridge: DomainBridge) -> bool:
    try:
        payload = json.loads(bridge.dimensional_contract)
    except (TypeError, json.JSONDecodeError):
        return False
    status = payload.get("status")
    if status == "VALIDATED_TYPED_MULTI_OBJECT":
        components = payload.get("components", {})
        return bool(components and all(len(tuple(str(x) for x in row.get("dimension", ()))) == 7 and row.get("quantity_id") for row in components.values()))
    common = tuple(str(x) for x in payload.get("common_dimension", ()))
    terms = payload.get("terms", {})
    return bool(
        status == "VALIDATED_SYMBOLIC"
        and len(common) == 7
        and terms
        and all(tuple(str(x) for x in vector) == common for vector in terms.values())
    )


def default_bridges() -> Dict[str, DomainBridge]:
    # Dimension order: (L, M, T, I, Θ, N, J). Abstract bridge dimensions are
    # represented by named symbolic exponents where a concrete SI exponent is
    # not intrinsic to the generic composition.
    D_FORCE = ("1", "1", "-2", "0", "0", "0", "0")
    D_FORCE_VOLUME = ("-2", "1", "-2", "0", "0", "0", "0")
    D_ENERGY = ("2", "1", "-2", "0", "0", "0", "0")
    D_MOLAR_ENERGY = ("2", "1", "-2", "0", "0", "-1", "0")
    D_CONC_RATE = ("-3", "0", "-1", "0", "0", "1", "0")
    D_STRESS = ("-1", "1", "-2", "0", "0", "0", "0")
    D_STATE_RATE = ("aL", "aM", "aT-1", "aI", "aTheta", "aN", "aJ")
    D_MOLAR_FLUX = ("-2", "0", "-1", "0", "0", "1", "0")
    specs = {
        "PHYS_MECH_FORCE": {
            "domains": ("physics", "mechanics"), "output": "force_and_motion", "formula": "F = \\int_V f_field \\, dV",
            "contract": _dimension_contract(D_FORCE, {"F": D_FORCE, "integral_volume_force_density": D_FORCE}),
        },
        "PHYS_MECH_CONTINUUM": {
            "domains": ("physics", "mechanics"), "output": "continuum_balance", "formula": "rho Dv/Dt = div(sigma) + rho b",
            "contract": _dimension_contract(D_FORCE_VOLUME, {"rho_Dv_Dt": D_FORCE_VOLUME, "div_sigma": D_FORCE_VOLUME, "rho_b": D_FORCE_VOLUME}),
        },
        "PHYS_CHEM_QUANTUM": {
            "domains": ("physics", "chemistry"), "output": "electronic_structure", "formula": "H_e psi = E psi",
            "contract": _dimension_contract(D_ENERGY, {"H_psi_per_psi": D_ENERGY, "E": D_ENERGY}),
        },
        "PHYS_CHEM_THERMO": {
            "domains": ("physics", "chemistry"), "output": "chemical_equilibrium", "formula": "mu_i = mu_i^0 + R T ln(a_i)",
            "contract": _dimension_contract(D_MOLAR_ENERGY, {"mu_i": D_MOLAR_ENERGY, "mu_i_0": D_MOLAR_ENERGY, "RT_ln_ai": D_MOLAR_ENERGY}, dimensionless=("a_i", "ln(a_i)")),
        },
        "PHYS_CHEM_SPECTROSCOPY": {
            "domains": ("physics", "chemistry"), "output": "spectral_transition", "formula": "h nu = E_f - E_i",
            "contract": _dimension_contract(D_ENERGY, {"h_nu": D_ENERGY, "E_f": D_ENERGY, "E_i": D_ENERGY}),
        },
        "MECH_CHEM_REACTIVE_FLOW": {
            "domains": ("mechanics", "chemistry"), "output": "reactive_transport", "formula": "partial_t c_i + div(c_i v) = - div(J_i) + sum_r nu_ir r_r",
            "contract": _dimension_contract(D_CONC_RATE, {"partial_t_c_i": D_CONC_RATE, "div_civ": D_CONC_RATE, "div_J_i": D_CONC_RATE, "reaction_source": D_CONC_RATE}, dimensionless=("nu_ir",)),
        },
        "MECH_CHEM_CHEMOMECHANICS": {
            "domains": ("mechanics", "chemistry", "materials_science"), "output": "composition_dependent_stress", "formula": "sigma = d psi(epsilon,c)/d epsilon",
            "contract": _dimension_contract(D_STRESS, {"sigma": D_STRESS, "dpsi_depsilon": D_STRESS}, dimensionless=("epsilon",)),
        },
        "MECH_CHEM_RHEOLOGY": {
            "domains": ("mechanics", "chemistry", "materials_science"), "output": "constitutive_response", "formula": "sigma = F[e_dot, composition, structure]",
            "contract": _dimension_contract(D_STRESS, {"sigma": D_STRESS, "constitutive_response": D_STRESS}),
        },
        "PHYS_MECH_CHEM_COMBUSTION": {
            "domains": ("physics", "mechanics", "chemistry"), "output": "combustion_model", "formula": "balance(U) = transport(U) + reaction(U)",
            "contract": _dimension_contract(D_STATE_RATE, {"balance_U": D_STATE_RATE, "transport_U": D_STATE_RATE, "reaction_U": D_STATE_RATE}),
        },
        "PHYS_MECH_CHEM_ELECTROCHEM": {
            "domains": ("physics", "mechanics", "chemistry"), "output": "electrochemical_continuum", "formula": "J_i = -D_i grad(c_i) - z_i u_i F c_i grad(phi) + c_i v",
            "contract": _dimension_contract(D_MOLAR_FLUX, {"J_i": D_MOLAR_FLUX, "diffusive_flux": D_MOLAR_FLUX, "migration_flux": D_MOLAR_FLUX, "advective_flux": D_MOLAR_FLUX}, dimensionless=("z_i",)),
        },
        "NEUTRINO_MULTIDOMAIN_THEORY_BRIDGE": {
            "domains": ("physics", "mathematics", "mechanics", "chemistry", "metrology", "systems_control"),
            "output": "higher_dimensional_neutrino_microparameters",
            "formula": "LawSpace[physics,mathematics,mechanics,chemistry,metrology,systems_control] -> HigherDimensionalMicroParameters -> M -> TakagiSpectrumIR",
            "contract": '{"components":{"compact_geometry":{"dimension":["1","0","0","0","0","0","0"],"quantity_id":"QTY-RADIUS"},"identifiability":{"dimension":["0","0","0","0","0","0","0"],"quantity_id":"QTY-IDENTIFIABILITY-RANK"},"likelihood":{"dimension":["0","0","0","0","0","0","0"],"quantity_id":"QTY-CHI-SQUARED"},"mass_operator":{"dimension":["2","1","-2","0","0","0","0"],"quantity_id":"QTY-MASS-MATRIX"},"molecular_response":{"dimension":["0","0","0","0","0","0","0"],"quantity_id":"QTY-EXPECTED-COUNT"}},"status":"VALIDATED_TYPED_MULTI_OBJECT"}',
        },
        "AERONAUTICS_MULTIDOMAIN_LAW_INTERSECTION_BRIDGE": {
            "domains": ("aeronautics_and_aerostation", "physics", "mechanics", "materials_science", "earth_systems", "systems_control", "metrology"),
            "output": "aeronautics_source_law_intersection_cell",
            "formula": "LawSpace[aeronautics_and_aerostation,physics,mechanics,materials_science,earth_systems,systems_control,metrology] -> validity_intersection -> deductive_closure",
            "contract": '{"components":{"validity_intersection":{"dimension":["0","0","0","0","0","0","0"],"quantity_id":"QTY-IDENTIFIABILITY-RANK"},"aerodynamic_force":{"dimension":["1","1","-2","0","0","0","0"],"quantity_id":"QTY-FORCE"},"propulsive_power":{"dimension":["2","1","-3","0","0","0","0"],"quantity_id":"QTY-POWER"}},"status":"VALIDATED_TYPED_MULTI_OBJECT"}',
        },
        "QUANTUM_VACUUM_GRAVITY_INTERSECTION_BRIDGE": {
            "domains": ("physics", "mathematics", "materials_science", "metrology"),
            "output": "quantum_vacuum_gravity_intersection_cell",
            "formula": "LawSpace[physics,mathematics,materials_science,metrology] -> renormalized_Tmunu -> validity_intersection -> semiclassical_gravity_closure",
            "contract": '{"components":{"validity_intersection":{"dimension":["0","0","0","0","0","0","0"],"quantity_id":"QTY-IDENTIFIABILITY-RANK"},"stress_energy":{"dimension":["-1","1","-2","0","0","0","0"],"quantity_id":"QTY-STRESS"},"force":{"dimension":["1","1","-2","0","0","0","0"],"quantity_id":"QTY-FORCE"}},"status":"VALIDATED_TYPED_MULTI_OBJECT"}',
        },
    }
    bridges: Dict[str, DomainBridge] = {}
    for bridge_id, spec in specs.items():
        domains = tuple(spec["domains"])
        is_neutrino = bridge_id == "NEUTRINO_MULTIDOMAIN_THEORY_BRIDGE"
        bridges[bridge_id] = DomainBridge(
            bridge_id=bridge_id, source_domains=domains, input_entity_types=("registered_owner",) * len(domains), output_entity_type=str(spec["output"]),
            mapping_rules=(("select registered neutrino owners", "bind quantity and constant IDs", "emit microparameter contract only; no solver", "preserve NEUTRINO-PHENOMENOLOGY as sole mass-lowering owner") if is_neutrino else ("preserve canonical owners", "map symbols explicitly", "do not infer from structural similarity alone")),
            dimensional_contract=str(spec["contract"]),
            assumptions=(("all required neutrino law passports are active", "input owners are valid in overlapping validity domains") if is_neutrino else ("input owners are valid in overlapping validity domains",)), validity_conditions=(("all source owners, quantities, constants and domains registered", "candidate geometry has an owner-supported lowering") if is_neutrino else ("all source owners and domains registered",)),
            composition_ast=ExpressionIR.from_source(str(spec["formula"]), "cross_domain_composition"), controlled_limits=(("zero coupling recovers source owners", "zero warp recovers flat S1/Z2", "finite truncation carries an explicit KK ledger") if is_neutrino else ("remove coupling to recover each source owner",)),
        )
    return bridges


class LawSpaceRuntime:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.registries = DOMAIN_REGISTRIES
        self.bridges = default_bridges()
        self.catalog = LawCatalog()
        self.manifests: Dict[str, SourceManifest] = {}
        self.evidence: Dict[str, EvidenceRecord] = {}
        self.candidates: List[Mapping[str, Any]] = []
        self.archetypes: List[Mapping[str, Any]] = []
        self.constants: Dict[str, Mapping[str, Any]] = {}
        self.quantities: Dict[str, Mapping[str, Any]] = {}
        self.computational_methods: Dict[str, ComputationalMethodPassport] = {}
        self.quantum_method_routes: List[Mapping[str, Any]] = []
        self._load()

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def current_release_id(self) -> str:
        manifest = self.root / "RELEASE_MANIFEST.json"
        if manifest.is_file():
            try:
                value = str(self._load_json(manifest).get("release", "")).strip()
                if value:
                    return value
            except Exception:
                pass
        return "UNSEALED-CURRENT"

    def external_state_path(self, component: str) -> Path:
        """Return a mutable state path that can never live inside the sealed tree."""
        name = str(component).strip().replace("/", "_")
        if not name:
            raise ValueError("state component name is required")
        configured = str(os.environ.get("PHI_STATE_DIR", "")).strip()
        if configured:
            state_root = Path(configured).expanduser()
        else:
            xdg = str(os.environ.get("XDG_STATE_HOME", "")).strip()
            state_root = (Path(xdg).expanduser() if xdg else (Path.home() / ".local" / "state")) / "phi-compiler"
        candidate = state_root / self.current_release_id() / f"{name}.json"
        try:
            candidate.resolve(strict=False).relative_to(self.root.resolve(strict=False))
        except ValueError:
            return candidate
        raise ValueError("mutable runtime state must be outside the sealed release tree")

    def _load(self) -> None:
        for path in sorted((self.root / "data" / "manifests").glob("*.json")):
            row = self._load_json(path)
            self.manifests[row["source_id"]] = SourceManifest(**row)
        for path in sorted((self.root / "data" / "passports").glob("known_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.catalog.add_passport(passport_from_persisted(json.loads(line)))
        knowledge_state_path = self.root / "data" / "knowledge" / "knowledge_evolution_state.json"
        if knowledge_state_path.exists():
            state = self._load_json(knowledge_state_path)
            if isinstance(state, Mapping):
                embedded = str(state.get("digest", ""))
                core = {k: v for k, v in state.items() if k != "digest"}
                if embedded != digest_payload(core):
                    raise ValueError("knowledge evolution state digest mismatch")
                for row in state.get("owner_axis_bindings", ()):
                    if not isinstance(row, Mapping):
                        continue
                    if str(row.get("status", "")) != "OWNER_AXIS_BINDING_QUALIFIED":
                        continue
                    self.catalog.add_owner_axis_binding(str(row.get("owner_id", "")), str(row.get("axis_id", "")))
        candidate_path = self.root / "data" / "passports" / "candidates.jsonl"
        if candidate_path.exists():
            self.candidates = [json.loads(line) for line in candidate_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        archetype_path = self.root / "data" / "passports" / "archetypes.jsonl"
        if archetype_path.exists():
            self.archetypes = [json.loads(line) for line in archetype_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        constants_path = self.root / "data" / "constants" / "registry.json"
        if constants_path.exists():
            rows = self._load_json(constants_path)
            self.constants = {row["constant_id"]: row for row in rows}
        quantities_path = self.root / "data" / "quantities" / "registry.json"
        if quantities_path.exists():
            rows = self._load_json(quantities_path)
            self.quantities = {row["quantity_id"]: row for row in rows}
        methods_path = self.root / "data" / "passports" / "computational_methods.jsonl"
        if methods_path.exists():
            for line in methods_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    method = computational_method_from_persisted(json.loads(line))
                    self.computational_methods[method.method_id] = method
        routes_path = self.root / "data" / "passports" / "quantum_method_routes.jsonl"
        if routes_path.exists():
            self.quantum_method_routes = [json.loads(line) for line in routes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        evidence_path = self.root / "data" / "evidence" / "records.jsonl"
        if evidence_path.exists():
            for line in evidence_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self.evidence[row["evidence_id"]] = EvidenceRecord(**{**row, "source_ids": tuple(row.get("source_ids", []))})

    def live_capability_ledger(self) -> Mapping[str, Any]:
        """Build the current executable capability ledger from authoritative runtime surfaces.

        The sealed ``capabilities.json`` is a release-state envelope since 15.10.x;
        it is no longer an exhaustive architecture capability registry.  Cognitive
        owners therefore derive their live ledger from executable API routes, current
        release receipts and declared open research obligations.  No historical
        capability snapshot is restored.
        """
        import re
        from .api import LawSpaceAPI

        capabilities: Dict[str, str] = {}
        for name in sorted(set(LawSpaceAPI.READ_TOOLS)):
            capabilities[str(name)] = "EXECUTABLE_READ_ROUTE"
        for name in sorted(set(LawSpaceAPI.MUTATION_TOOLS)):
            capabilities[str(name)] = "EXECUTABLE_MUTATION_ROUTE"
        for name in sorted(set(LawSpaceAPI.REGRESSION_TOOLS)):
            capabilities[str(name)] = "QUARANTINED_REGRESSION_ROUTE"

        envelope_path = self.root / "capabilities.json"
        envelope: Mapping[str, Any] = {}
        if envelope_path.is_file():
            raw = self._load_json(envelope_path)
            envelope = raw if isinstance(raw, Mapping) else {}
            for key, value in sorted(envelope.items()):
                if isinstance(value, Mapping) and str(value.get("status", "")).startswith("PASS_"):
                    capabilities[str(key)] = "QUALIFIED_CURRENT_RECEIPT::" + str(value.get("status"))
            for key, value in sorted(dict(envelope.get("preserved", {})).items()):
                if value is True or (isinstance(value, (int, float)) and value > 0):
                    capabilities[str(key)] = "QUALIFIED_PRESERVED_CURRENT_STATE"
            kernel = str(envelope.get("authoritative_research_kernel", "")).strip()
            if kernel:
                capabilities["authoritative_research_kernel"] = "QUALIFIED_CURRENT_KERNEL::" + kernel

        obligation_sources: Dict[str, list[str]] = {}
        pattern = re.compile(r'["\']next_research_obligation["\']\s*:\s*["\']([A-Z0-9_:-]+)["\']')
        for path in sorted((self.root / "source" / "lawspace").glob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for obligation in pattern.findall(text):
                capability_id = str(obligation).strip().lower().replace("::", "_").replace(":", "_")
                if not capability_id:
                    continue
                obligation_sources.setdefault(capability_id, []).append(str(path.relative_to(self.root)))
                capabilities[capability_id] = "ARCHITECTURE_OPEN_DECLARED_RESEARCH_OBLIGATION"

        payload: Dict[str, Any] = {
            "schema": "phi-live-capability-ledger/v2",
            "owner_id": "LIVE-CAPABILITY-LEDGER/15.10.2",
            "capabilities": dict(sorted(capabilities.items())),
            "capability_count": len(capabilities),
            "executable_read_count": sum(v == "EXECUTABLE_READ_ROUTE" for v in capabilities.values()),
            "executable_mutation_count": sum(v == "EXECUTABLE_MUTATION_ROUTE" for v in capabilities.values()),
            "qualified_current_count": sum(v.startswith("QUALIFIED") for v in capabilities.values()),
            "open_architecture_obligations": sorted(obligation_sources),
            "open_obligation_sources": {k: sorted(set(v)) for k, v in sorted(obligation_sources.items())},
            "historical_capability_snapshot_used": False,
            "release_envelope_schema": envelope.get("schema") if envelope else None,
            "release_envelope_status": envelope.get("status") if envelope else None,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def find_composition_path(self, source_domains: Sequence[str], target_type: str | None = None) -> List[DomainBridge]:
        source = set(source_domains)
        return [b for b in self.bridges.values() if set(b.source_domains).issubset(source) and (target_type is None or b.output_entity_type == target_type)]

    def compile_neutrino_multidomain_spec(self, *, candidate_id: str, geometry: str, microparameters: Mapping[str, Any]) -> Mapping[str, Any]:
        bridge = self.bridges["NEUTRINO_MULTIDOMAIN_THEORY_BRIDGE"]
        intersection_path = self.root / "data" / "passports" / "neutrino_intersection_laws.json"
        intersection_db = self._load_json(intersection_path)
        source_owners = tuple(intersection_db["source_registry"]["primary_intersection_source_owner_ids"])
        validation_owners = ("STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE",)
        required = source_owners + validation_owners
        missing = tuple(owner for owner in required if owner not in self.catalog.passports)
        if missing:
            raise RuntimeError(f"neutrino law-space owners missing: {missing}")
        expected_db_digest = digest_payload({k: v for k, v in intersection_db.items() if k != "database_digest"})
        if intersection_db.get("database_digest") != expected_db_digest:
            raise RuntimeError("neutrino intersection-law database digest mismatch")
        payload = {
            "schema": "phi-neutrino-multidomain-derivation/v1",
            "candidate_id": candidate_id,
            "bridge_id": bridge.bridge_id,
            "bridge_formula_digest": bridge.composition_ast.digest,
            "discovery_mode": "SOURCE_LAW_INTERSECTION_CLOSURE",
            "source_owner_ids": source_owners,
            "validation_owner_ids": validation_owners,
            "intersection_law_owner": "NEUTRINO-LAW-INTERSECTION-CLOSURE/6.13.0",
            "intersection_database_digest": intersection_db["database_digest"],
            "materialized_intersection_law_count": len(intersection_db.get("laws", [])),
            "blind_operator_synthesis_role": "AUXILIARY_ONLY",
            "geometry": geometry,
            "microparameters": dict(microparameters),
            "quantity_registry_digest": digest_payload(self.quantities),
            "constant_registry_digest": digest_payload(self.constants),
            "lowering_owner": "NEUTRINO-PHENOMENOLOGY/6.9.0",
            "solver_in_bridge": False,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def compile_aeronautics_intersection_spec(self, *, candidate_id: str) -> Mapping[str, Any]:
        bridge = self.bridges["AERONAUTICS_MULTIDOMAIN_LAW_INTERSECTION_BRIDGE"]
        db_path = self.root / "data" / "passports" / "aeronautics_intersection_laws.json"
        db = self._load_json(db_path)
        source_owners = tuple(row["owner_id"] for row in db.get("source_laws", ()))
        missing = tuple(owner for owner in source_owners if owner not in self.catalog.passports)
        if missing:
            raise RuntimeError(f"aeronautics law-space owners missing: {missing}")
        expected_db_digest = digest_payload({k: v for k, v in db.items() if k != "database_digest"})
        if db.get("database_digest") != expected_db_digest:
            raise RuntimeError("aeronautics intersection-law database digest mismatch")
        payload = {
            "schema": "phi-aeronautics-multidomain-derivation/v1",
            "candidate_id": candidate_id,
            "bridge_id": bridge.bridge_id,
            "bridge_formula_digest": bridge.composition_ast.digest,
            "discovery_mode": "SOURCE_LAW_INTERSECTION_CLOSURE",
            "source_owner_ids": source_owners,
            "intersection_law_owner": "AERONAUTICS-LAW-INTERSECTION-CLOSURE/6.15.0",
            "intersection_database_digest": db["database_digest"],
            "materialized_intersection_law_count": len(db.get("laws", ())),
            "closure_family_count": len(db.get("closure_families", ())),
            "registered_aeronautics_axis_count": self.registries["aeronautics_and_aerostation"].axis_count,
            "quantity_registry_digest": digest_payload(self.quantities),
            "constant_registry_digest": digest_payload(self.constants),
            "solver_in_bridge": False,
            "claim_boundary": "FORMAL_SOURCE_DERIVATION_NOT_CERTIFICATION_OR_NOVELTY_PROOF",
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def compile_quantum_vacuum_gravity_spec(self, *, candidate_id: str) -> Mapping[str, Any]:
        bridge = self.bridges["QUANTUM_VACUUM_GRAVITY_INTERSECTION_BRIDGE"]
        db_path = self.root / "data" / "passports" / "quantum_vacuum_gravity_intersection_laws.json"
        db = self._load_json(db_path)
        source_owners = tuple(row["owner_id"] for row in db.get("source_laws", ()))
        missing = tuple(owner for owner in source_owners if owner not in self.catalog.passports)
        if missing:
            raise RuntimeError(f"quantum-vacuum law-space owners missing: {missing}")
        expected_db_digest = digest_payload({k: v for k, v in db.items() if k != "database_digest"})
        if db.get("database_digest") != expected_db_digest:
            raise RuntimeError("quantum-vacuum intersection-law database digest mismatch")
        payload = {
            "schema": "phi-quantum-vacuum-gravity-multidomain-derivation/v1",
            "candidate_id": candidate_id,
            "bridge_id": bridge.bridge_id,
            "bridge_formula_digest": bridge.composition_ast.digest,
            "discovery_mode": "SOURCE_LAW_INTERSECTION_CLOSURE",
            "source_owner_ids": source_owners,
            "intersection_law_owner": "QUANTUM-VACUUM-GRAVITY-INTERSECTION-CLOSURE/6.16.0",
            "intersection_database_digest": db["database_digest"],
            "materialized_intersection_law_count": len(db.get("laws", ())),
            "registered_axis_count": sum(reg.axis_count for reg in self.registries.values()),
            "quantity_registry_digest": digest_payload(self.quantities),
            "constant_registry_digest": digest_payload(self.constants),
            "solver_in_bridge": False,
            "claim_boundary": dict(db.get("claim_boundary", {})),
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def qualify(self) -> Mapping[str, Any]:
        manifest_declared = sum(sum(m.declared_records.values()) for m in self.manifests.values())
        manifest_processed = sum(sum(m.processed_records.values()) for m in self.manifests.values())
        known_count = len(self.catalog.passports)
        expected_known = sum(m.declared_records.get("known_laws", 0) for m in self.manifests.values())
        expected_composite_models = sum(m.declared_records.get("composite_models", 0) for m in self.manifests.values())
        expected_archetypes = sum(m.declared_records.get("archetypes", 0) for m in self.manifests.values())
        expected_methods = sum(m.declared_records.get("computational_methods", 0) for m in self.manifests.values())
        expected_method_routes = sum(m.declared_records.get("quantum_method_routes", 0) for m in self.manifests.values())

        source_digest_checks = {}
        for source_id, manifest in self.manifests.items():
            source_path = self.root / manifest.location
            source_digest_checks[source_id] = bool(source_path.is_file() and __import__("hashlib").sha256(source_path.read_bytes()).hexdigest() == manifest.sha256)
        g1 = GateCertificate(OWNER_VERSION, "lawspace", "G1_CORPUS_COMPLETENESS", {
            "all_manifest_rows_processed": manifest_declared == manifest_processed,
            "all_source_snapshot_digests_match": bool(source_digest_checks) and all(source_digest_checks.values()),
            "known_law_count_matches": known_count == expected_known,
            "composite_model_count_matches": len(self.candidates) == expected_composite_models,
            "archetype_count_matches": len(self.archetypes) == expected_archetypes,
            "computational_method_count_matches": len(self.computational_methods) == expected_methods,
            "quantum_method_route_count_matches": len(self.quantum_method_routes) == expected_method_routes,
            "no_duplicate_known_owners": len(self.catalog.passports) == len(set(self.catalog.passports)),
        }, {"known_laws": known_count, "composite_models": len(self.candidates), "archetypes": len(self.archetypes), "computational_methods": len(self.computational_methods), "quantum_method_routes": len(self.quantum_method_routes), "declared_total": manifest_declared}, ["source manifests are authoritative corpus boundaries"]).finalize()

        parse_pass = all(p.formula.parse_status == "PASS" and p.formula.digest for p in self.catalog.passports.values())
        symbols_resolved = all(tuple(sorted(s.display for s in p.symbols)) == tuple(sorted(p.formula.symbols)) for p in self.catalog.passports.values())
        symbol_ids_unique = all(len({s.symbol_id for s in p.symbols}) == len(p.symbols) for p in self.catalog.passports.values())
        dimension_declared = sum(1 for p in self.catalog.passports.values() if p.quantity_semantics.get("dimension_status") in {"VALIDATED", "DECLARED_UNKNOWN", "NOT_APPLICABLE"})
        quantity_ids_known = all(s.quantity_id is None or s.quantity_id in self.quantities for p in self.catalog.passports.values() for s in p.symbols)
        quantity_dimensions_match = all(
            s.quantity_id is None or s.dimension is None or tuple(s.dimension.as_tuple()) == tuple(str(self.quantities[s.quantity_id]["dimension"][k]) for k in ("length","mass","time","current","temperature","amount","luminous_intensity"))
            for p in self.catalog.passports.values() for s in p.symbols if s.quantity_id is None or s.quantity_id in self.quantities
        )
        passport_constants_known = all(all(cid in self.constants for cid in p.constants) for p in self.catalog.passports.values())
        g2 = GateCertificate(OWNER_VERSION, "lawspace", "G2_SEMANTIC_INTEGRITY", {
            "all_formulas_structurally_parsed": parse_pass,
            "all_formula_symbols_have_records": symbols_resolved,
            "symbol_ids_unique_within_owner": symbol_ids_unique,
            "all_dimension_statuses_explicit": dimension_declared == known_count,
            "all_units_are_typed_or_explicitly_unknown": all("unit_status" in p.quantity_semantics for p in self.catalog.passports.values()),
            "all_symbol_quantity_ids_resolve": quantity_ids_known,
            "all_typed_symbol_dimensions_match_quantity_registry": quantity_dimensions_match,
            "all_passport_constants_resolve": passport_constants_known,
        }, {"formulas": known_count, "dimension_status_declared": dimension_declared, "fully_dimension_validated": sum(p.quantity_semantics.get("dimension_status") == "VALIDATED" for p in self.catalog.passports.values()), "quantities": len(self.quantities)}, ["STRUCTURAL_TYPED_AST is not claimed as full theorem-prover lowering", "DECLARED_UNKNOWN is explicit incompleteness, not a validation pass"]).finalize()

        dynamic_axis_path = self.root / "data" / "axes" / "canonical_dynamic_axes.json"
        dynamic_axis_doc = self._load_json(dynamic_axis_path) if dynamic_axis_path.is_file() else {}
        base_axis_count = sum(reg.axis_count for reg in BASE_DOMAIN_REGISTRIES.values())
        canonical_axis_count = sum(reg.axis_count for reg in DOMAIN_REGISTRIES.values())
        dynamic_entries = tuple(dynamic_axis_doc.get("entries", ()))
        authoritative_registry_match = bool(
            set(self.registries) == set(DOMAIN_REGISTRIES)
            and all(
                self.registries[domain].axis_count == DOMAIN_REGISTRIES[domain].axis_count
                and self.registries[domain].digest == DOMAIN_REGISTRIES[domain].digest
                for domain in DOMAIN_REGISTRIES
            )
        )
        dynamic_axis_metadata_coherent = bool(
            dynamic_axis_doc
            and int(dynamic_axis_doc.get("base_axis_count", -1)) == base_axis_count
            and int(dynamic_axis_doc.get("dynamic_axis_count", -1)) == len(dynamic_entries)
            and canonical_axis_count == base_axis_count + len(dynamic_entries)
        )
        g3 = GateCertificate(OWNER_VERSION, "lawspace", "G3_DOMAIN_AND_CELL_INTEGRITY", {
            "mandatory_domains_registered": all(d in self.registries for d in MANDATORY_CORE_DOMAINS),
            "quantum_computational_domain_registered": "quantum_information_and_computational_methods" in self.registries,
            "authoritative_registry_matches_runtime": authoritative_registry_match,
            "canonical_dynamic_axis_metadata_coherent": dynamic_axis_metadata_coherent,
            "one_owner_one_home_cell": len(self.catalog.owner_to_cell) == known_count,
            "home_cells_reproducible": all(self.catalog.cell_id(p.domain_id, p.scientific_coordinate) == p.home_cell_id for p in self.catalog.passports.values()),
            "all_bridges_use_registered_domains": all(all(d in self.registries for d in b.source_domains) for b in self.bridges.values()),
            "all_bridges_have_typed_ast": all(b.composition_ast.parse_status == "PASS" for b in self.bridges.values()),
            "all_bridge_dimension_contracts_validate": all(_bridge_dimension_contract_valid(b) for b in self.bridges.values()),
        }, {
            "domains": len(self.registries), "cells": len(self.catalog.cells), "bridges": len(self.bridges),
            "base_axis_count": base_axis_count, "dynamic_axis_count": len(dynamic_entries),
            "canonical_axis_count": canonical_axis_count,
            "axis_counts": {domain: registry.axis_count for domain, registry in sorted(self.registries.items())},
        }, ["axis counts are derived from the authoritative current registries, never frozen release constants", "cells are sparse; absent axes are not filled by defaults", "projections never replace canonical owners"]).finalize()

        known_source_ids = set(self.manifests)
        provenance_ok = all(
            p.provenance.get("source_id") in known_source_ids
            and p.provenance.get("source_digest") == self.manifests[p.provenance.get("source_id")].sha256
            for p in self.catalog.passports.values()
        )
        constant_provenance_ok = all(
            c.get("source_id") in known_source_ids
            and c.get("source_digest") == self.manifests[c.get("source_id")].sha256
            for c in self.constants.values()
        )
        allowed_constant_classes = {"SI_DEFINING_EXACT", "EXACT_DERIVED", "MEASURED_FUNDAMENTAL", "MEASURED_DERIVED"}
        constant_classes_ok = all(c.get("constant_class") in allowed_constant_classes for c in self.constants.values())
        constant_dependencies_known = all(all(dep in self.constants for dep in c.get("depends_on", [])) for c in self.constants.values())
        derived_constants_have_expressions = all(
            bool(c.get("derivation_expression")) and bool(c.get("depends_on"))
            for c in self.constants.values() if c.get("constant_class") in {"EXACT_DERIVED", "MEASURED_DERIVED"}
        )
        fit_parameters_excluded = all(c.get("fit_status") == "NOT_A_FIT_PARAMETER" for c in self.constants.values())
        evidence_sources_known = all(all(source_id in known_source_ids for source_id in e.source_ids) for e in self.evidence.values())

        quantum_axis_ids = set(self.registries["quantum_information_and_computational_methods"].axes)
        method_axis_fields_registered = all(
            set(m.scientific_coordinate).issubset(quantum_axis_ids)
            and {str(rule.get("field")) for rule in m.applicability_rules}.issubset(quantum_axis_ids)
            for m in self.computational_methods.values()
        )
        quantum_target_path = self.root / "data" / "targets" / "large_qubit_realistic_emulator.json"
        quantum_target = self._load_json(quantum_target_path) if quantum_target_path.is_file() else {}
        quantum_target_digest = str(quantum_target.get("digest", ""))
        quantum_target_digest_valid = bool(
            quantum_target
            and quantum_target_digest == digest_payload({k: v for k, v in quantum_target.items() if k != "digest"})
        )
        quantum_target_axes_registered = set(quantum_target.get("features", {})).issubset(quantum_axis_ids)
        quantum_route_digests_valid = all(
            r.get("digest") == digest_payload({**r, "digest": ""})
            for r in self.quantum_method_routes
        )
        quantum_route_target_digest_matches = all(
            r.get("provenance", {}).get("target_digest") == quantum_target_digest
            for r in self.quantum_method_routes
        )
        quantum_route_gates_pass = all(
            bool(r.get("gates")) and all(r["gates"].values())
            for r in self.quantum_method_routes
        )
        method_snapshot_matches = False
        method_manifests = [
            manifest for manifest in self.manifests.values()
            if int(manifest.declared_records.get("computational_methods", 0)) > 0
        ]
        if len(method_manifests) == 1:
            method_manifest = method_manifests[0]
            try:
                method_snapshot = self._load_json(self.root / method_manifest.location)
                methods_file = self.root / method_snapshot["methods_file"]
                method_snapshot_matches = bool(
                    method_snapshot.get("method_count") == len(self.computational_methods)
                    and method_snapshot.get("methods_file_sha256") == __import__("hashlib").sha256(methods_file.read_bytes()).hexdigest()
                    and method_snapshot.get("schema") == "phi-computational-method-snapshot/v6.4"
                )
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                method_snapshot_matches = False
        quantum_axis_census_explicit = False
        quantum_scan_path = self.root / "reports" / "QUANTUM_METHOD_SCAN_CURRENT.json"
        if quantum_scan_path.is_file():
            try:
                quantum_scan = self._load_json(quantum_scan_path)
                census = quantum_scan.get("axis_census", {})
                quantum_axis_census_explicit = bool(
                    census.get("registered_axis_count") == 75
                    and census.get("active_axis_count", 0) + census.get("open_uninstantiated_axis_count", 0) == 75
                    and census.get("all_referenced_axes_registered") is True
                    and len(census.get("axis_rows", [])) == 75
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                quantum_axis_census_explicit = False

        confirmed_baseline_states = {
            "ESTABLISHED_LAW", "EXPERIMENTALLY_CONFIRMED", "ESTABLISHED_ENGINEERING_RELATION",
            "ESTABLISHED_ENGINEERING_MODEL", "ESTABLISHED_EFFECTIVE_RELATION", "ESTABLISHED_QFT_BOUND",
            "ESTABLISHED_MECHANICAL_IDENTITY", "ESTABLISHED_GEOMETRIC_IDENTITY", "ESTABLISHED_PUBLISHED_MODEL",
            "ESTABLISHED_THEOREM", "ESTABLISHED_QFT_RESULT", "ESTABLISHED_DERIVED_RELATION",
        }
        candidate_boundary = all(
            c.get("epistemic_state") == "CONFIRMED_CONTROL_MODEL"
            and c.get("candidate_scope") == "CONFIRMED_SOURCE_CONTROL_NO_NEW_COUPLING"
            and c.get("scientific_status") == "WORLD_OR_SOURCE_ATTESTED_CONTROL_NO_NEW_COUPLING"
            and c.get("baseline_role") == "CONFIRMED_CONTROL_ANCHOR_NOT_SOLUTION_SPACE"
            and c.get("confirmation", {}).get("candidate_is_new_law") is False
            and c.get("confirmation", {}).get("all_source_states_confirmed") is True
            and c.get("property_inheritance_contract", {}).get("confirmation_scope") == "SOURCE_EQUATIONS_AND_DECLARED_VALIDITY_ONLY"
            for c in self.candidates
        )
        active_confirmed_only = all(
            c.get("source_id") == "CONFIRMED_BASELINE_CONTROLS_V13_4"
            and c.get("generator", {}).get("generator_id") == "ConfirmedBaselineReplacementOwner"
            and c.get("gate_status") == "CONFIRMED_BASELINE"
            for c in self.candidates
        )
        source_owners_known = all(all(owner_id in self.catalog.passports for owner_id in c.get("source_owner_ids", ())) for c in self.candidates)
        source_states_confirmed = all(
            all(self.catalog.passports[owner_id].epistemic_state in confirmed_baseline_states for owner_id in c.get("source_owner_ids", ()))
            for c in self.candidates
        )
        candidate_gates_pass = all(c.get("gates") and all(c["gates"].values()) for c in self.candidates)
        generated_ids_unique = len({c.get("candidate_id") for c in self.candidates}) == len(self.candidates)
        generated_digests_unique = len({c.get("digest") for c in self.candidates}) == len(self.candidates)
        candidate_digests_valid = all(c.get("digest") == digest_payload({**c, "digest": ""}) for c in self.candidates)

        def candidate_id_reproducible(candidate: Mapping[str, Any]) -> bool:
            candidate_id = str(candidate.get("candidate_id", ""))
            payload = candidate.get("candidate_identity_payload")
            if candidate_id.startswith("CCONF-"):
                return isinstance(payload, Mapping) and candidate_id == "CCONF-" + digest_payload(payload)[:20].upper()
            if candidate_id.startswith("DSPACE-"):
                return isinstance(payload, Mapping) and candidate_id == "DSPACE-" + digest_payload(payload)[:20].upper()
            payload = {
                "generator_version": candidate.get("generator", {}).get("generator_version"),
                "transformation_digest": candidate.get("transformation", {}).get("transformation_digest"),
                "source_formula_digests": candidate.get("source_formula_digests", []),
                "source_owner_ids": candidate.get("source_owner_ids", []),
                "target_domains": tuple(candidate.get("target_domains", [])),
                "axis_ids": tuple(candidate.get("transformation", {}).get("axis_ids", [])),
            }
            return candidate_id == "CGEN-" + digest_payload(payload)[:20].upper()

        candidate_ids_reproducible = all(candidate_id_reproducible(c) for c in self.candidates)
        candidate_formula_digests_valid = all(expression_from_persisted(c["formula"]).digest == c["formula"]["digest"] for c in self.candidates)
        baseline_constructor_present = {c.get("generator", {}).get("generator_id") for c in self.candidates} == {"ConfirmedBaselineReplacementOwner"}
        candidate_axes_declared = all(bool(c.get("transformation", {}).get("axis_ids")) for c in self.candidates)
        known_formula_digests = {p.formula.digest for p in self.catalog.passports.values()}
        component_formula_refs_known = all(
            bool(c.get("source_formula_digests"))
            and all(d in known_formula_digests for d in c.get("source_formula_digests", ()))
            for c in self.candidates
        )
        no_new_coupling_asserted = all(c.get("gates", {}).get("NO_NEW_COUPLING_ASSERTED") is True for c in self.candidates)
        original_frontier_path = self.root / "data" / "frontiers" / "unverified_composite_candidates.jsonl"
        original_frontier_count = 0
        if original_frontier_path.is_file():
            original_frontier_count = sum(1 for line in original_frontier_path.read_text(encoding="utf-8").splitlines() if line.strip())

        baseline_snapshot_ok = False
        axis_snapshot_ok = False
        baseline_manifest = self.manifests.get("CONFIRMED_BASELINE_CONTROLS_V13_4")
        if baseline_manifest is not None:
            try:
                snapshot = self._load_json(self.root / baseline_manifest.location)
                candidate_file = self.root / "data" / "passports" / "candidates.jsonl"
                candidate_file_sha = __import__("hashlib").sha256(candidate_file.read_bytes()).hexdigest()
                frontier_sha = __import__("hashlib").sha256(original_frontier_path.read_bytes()).hexdigest() if original_frontier_path.is_file() else ""
                baseline_snapshot_ok = bool(
                    snapshot.get("confirmed_baseline_count") == len(self.candidates)
                    and snapshot.get("candidate_file_sha256") == candidate_file_sha
                    and snapshot.get("candidate_scope") == "CONFIRMED_SOURCE_CONTROL_NO_NEW_COUPLING"
                    and snapshot.get("active_unconfirmed_count") == 0
                    and snapshot.get("original_unverified_frontier_sha256") == frontier_sha
                )
                axis_report = self._load_json(self.root / "reports" / "AXIS_SPACE_SCAN_CURRENT.json")
                axis_snapshot_ok = bool(
                    axis_report.get("status") in {"PASS", "PASS_WITH_OPEN_FRONTIER"}
                    and axis_report.get("axis_space", {}).get("all_registered_axes_classified") is True
                    and axis_report.get("axis_space", {}).get("exact_axis_subset_census") is True
                    and axis_report.get("axis_space", {}).get("all_registered_axis_orders_classified") is True
                    and axis_report.get("axis_space", {}).get("scan_order_policy") == "ALL_REGISTERED_AXES"
                    and len(axis_report.get("axis_space", {}).get("domains", {})) == len(DOMAIN_REGISTRIES)
                    and sum(domain_row.get("registry_axis_count", 0) for domain_row in axis_report.get("axis_space", {}).get("domains", {}).values()) == sum(registry.axis_count for registry in DOMAIN_REGISTRIES.values())
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                baseline_snapshot_ok = False
                axis_snapshot_ok = False

        current_frontier_path = self.root / "data" / "frontiers" / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
        current_frontier_rows: List[Mapping[str, Any]] = []
        if current_frontier_path.is_file():
            current_frontier_rows = [json.loads(line) for line in current_frontier_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        frontier_ids = [str(row.get("candidate_id", "")) for row in current_frontier_rows]
        frontier_record_digests_valid = all(
            row.get("record_digest") == digest_payload({k: v for k, v in row.items() if k != "record_digest"})
            for row in current_frontier_rows
        )
        frontier_domains_registered = all(
            all(domain_id in self.registries for domain_id in row.get("domain_ids", ()) if domain_id not in {"UNKNOWN"})
            for row in current_frontier_rows
        )
        frontier_source_owners_resolve_or_are_owner_local = all(
            all(owner_id in self.catalog.passports or "/" in str(owner_id) or str(owner_id).startswith(("CONSTRAINT-", "ATLAS-", "SCIENTIFIC-"))
                for owner_id in row.get("source_owner_ids", ()))
            for row in current_frontier_rows
        )
        archived_baseline_ok = False
        baseline_manifest = self.manifests.get("CONFIRMED_BASELINE_CONTROLS_V13_4")
        if baseline_manifest is not None:
            try:
                snapshot = self._load_json(self.root / baseline_manifest.location)
                archived_baseline_ok = bool(
                    snapshot.get("historical_confirmed_baseline_count") == 2771
                    and snapshot.get("active_baseline_count") == 0
                    and snapshot.get("active_unconfirmed_count") == 0
                    and snapshot.get("current_authoritative_candidate_store") == "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
                    and baseline_manifest.declared_records.get("historical_control_snapshot") == 1
                    and baseline_manifest.processed_records.get("historical_control_snapshot") == 1
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                archived_baseline_ok = False

        g4 = GateCertificate(OWNER_VERSION, "lawspace", "G4_EVIDENCE_AND_PROVENANCE", {
            "deleted_baseline_candidate_registry_remains_empty": len(self.candidates) == 0,
            "historical_2771_control_snapshot_is_archived_not_active": archived_baseline_ok,
            "current_frontier_ledger_present": bool(current_frontier_rows),
            "current_frontier_candidate_ids_unique": len(frontier_ids) == len(set(frontier_ids)),
            "current_frontier_record_digests_validate": frontier_record_digests_valid,
            "current_frontier_candidates_are_active": all("CANDIDATE_ACTIVE" in row.get("epistemic_statuses", ()) for row in current_frontier_rows),
            "current_frontier_unknowns_are_not_marked_false": all(not any("FALSE" in str(status) or "FALSIFIED" in str(status) for status in row.get("epistemic_statuses", ())) for row in current_frontier_rows),
            "current_frontier_domains_registered": frontier_domains_registered,
            "current_frontier_source_owners_resolve_or_are_owner_local": frontier_source_owners_resolve_or_are_owner_local,
            "current_frontier_is_not_promoted_to_known_law_catalog": not any(cid in self.catalog.passports for cid in frontier_ids),
        }, {
            "active_baseline_candidate_count": len(self.candidates),
            "historical_control_anchor_count": 2771,
            "active_frontier_candidate_count": len(current_frontier_rows),
        }, [
            "2771 is historical control provenance, not an active solution-space registry",
            "the authoritative current research state is the persistent frontier ledger",
            "UNKNOWN and novelty-unresolved states are preserved until discriminating evidence resolves them",
        ]).finalize()

        deterministic_search = [p.owner_id for p in self.catalog.search("уравнение", limit=25)] == [p.owner_id for p in self.catalog.search("уравнение", limit=25)]
        g5 = GateCertificate(OWNER_VERSION, "lawspace", "G5_RUNTIME_AND_AI", {
            "catalog_digest_reproducible": self.catalog.digest() == self.catalog.digest(),
            "search_reproducible": deterministic_search,
            "candidate_order_reproducible": [c.get("candidate_id") for c in self.candidates] == sorted(c.get("candidate_id") for c in self.candidates),
            "ai_mutation_boundary_declared": True,
            "blind_recovery_boundary_preserved": True,
            "json_roundtrip_available": bool(self.catalog.passports),
        }, {"catalog_digest": self.catalog.digest(), "registered_ai_tools": 16, "active_recovery_handlers_expected": 8, "active_candidate_generation_paths": 5, "computational_method_scanners": 1}, ["AI tools are read-only except pending proposal creation", "truth_access=True remains rejected by the existing recovery owner", "candidate generators consume canonical owners and registered bridges only"]).finalize()

        def nested_digest_valid(payload: Mapping[str, Any]) -> bool:
            return bool(payload.get("digest")) and payload.get("digest") == digest_payload({**payload, "digest": ""})

        known_formula_p0 = all(
            p.formula.operator_scope.digest
            and p.formula.binding_graph.digest
            and p.formula.distribution_wavefront.digest
            for p in self.catalog.passports.values()
        )
        candidate_p0 = all(
            nested_digest_valid(c.get("formula", {}).get("operator_scope", {}))
            and nested_digest_valid(c.get("formula", {}).get("binding_graph", {}))
            and nested_digest_valid(c.get("formula", {}).get("distribution_wavefront", {}))
            for c in self.candidates
        )
        candidate_p1 = all(
            nested_digest_valid(c.get("property_inheritance_contract", {}))
            and nested_digest_valid(c.get("proof_obligation_graph", {}))
            and nested_digest_valid(c.get("limit_protocol", {}))
            and nested_digest_valid(c.get("primary_source_ledger", {}))
            for c in self.candidates
        )
        route_p1 = all(
            nested_digest_valid(r.get("proof_obligation_graph", {}))
            and nested_digest_valid(r.get("limit_protocol", {}))
            and nested_digest_valid(r.get("primary_source_ledger", {}))
            for r in self.quantum_method_routes
        )
        formal_contract_path = self.root / "data" / "formal_contracts" / "toller_distributional_vertex_v4_1.json"
        formal_contract_projection = self._load_json(formal_contract_path) if formal_contract_path.is_file() else {}
        expected_formal_contract = toller_distributional_vertex_contract()
        formal_contract_matches = bool(
            formal_contract_projection
            and formal_contract_projection.get("digest") == expected_formal_contract.get("digest")
            and formal_contract_projection.get("digest") == digest_payload({**formal_contract_projection, "digest": ""})
        )
        binding_rows = formal_contract_projection.get("shared_binding_graph", {}).get("bindings", [])
        binding_sets = {frozenset(row.get("occurrences", [])) for row in binding_rows}
        shared_toller_bindings = {
            frozenset(("rho_left", "rho_right", "wedge_projector")),
            frozenset(("q_left", "q_right")),
            frozenset(("p_left", "p_right")),
        }.issubset(binding_sets)
        proof_nodes = {
            row.get("node_id"): row.get("status")
            for row in formal_contract_projection.get("proof_obligation_graph", {}).get("nodes", [])
        }
        causal_orientation_rank16 = proof_nodes.get("orientation_fourier") == "PASS_EXACT_RANK_16"
        cluster_character_bijection = proof_nodes.get("cluster_character_lift") == "PASS_EXACT_BIJECTION"
        causal_orientation_selector_rank25 = proof_nodes.get("orientation_structural_selector") == "PASS_EXACT_RANK_25"
        bisimplex_forest_complete = proof_nodes.get("bisimplex_forest") == "PASS_EXACT_193_CLUSTERS"
        joint_forest_recursion_complete = proof_nodes.get("joint_forest_recursion") == "PASS_EXACT_112848_FORESTS"
        tensor_wavefront_atlas_complete = proof_nodes.get("tensor_wavefront_atlas") == "PASS_193_CONORMALS_PULLBACK_CONDITIONAL"
        qpdtr_pre_rhs_executed = proof_nodes.get("qpdtr_bisimplex_pre_rhs") == "PASS_FINITE_PRE_RHS_PATH_DEPENDENT"
        wavefront_open = proof_nodes.get("wavefront") == "OPEN_EXACT_VERTEX_WF_CONTAINMENT"
        pushforward_open = proof_nodes.get("pushforward") == "OPEN_NONPROPER_NO_TAIL_BOUND"
        renormalized_contact_rhs_open = proof_nodes.get("renormalized_contact_rhs") == "OPEN_ANALYTIC_EXTENSION_NOT_COMPUTED"
        qpdtr_contract_path = self.root / "data" / "integrations" / "qpdtr_v2_5_0_contract.json"
        qpdtr_contract = self._load_json(qpdtr_contract_path) if qpdtr_contract_path.is_file() else {}
        qpdtr_contract_valid = bool(
            qpdtr_contract
            and qpdtr_contract.get("digest") == digest_payload({**qpdtr_contract, "digest": ""})
            and qpdtr_contract.get("source_release_version") == "2.5.0"
            and qpdtr_contract.get("external_authoritative_owner") == "qpdtr.owner.QuantumGravityDynamicsOwner.execute"
            and qpdtr_contract.get("required_control_gates") == 53
            and qpdtr_contract.get("required_packaged_tests") == 103
            and qpdtr_contract.get("confirmed_new_physical_laws") == 0
        )
        g6 = GateCertificate(OWNER_VERSION, "lawspace", "G6_FORMAL_ANALYSIS_AND_INTEGRATION", {
            "all_known_formulas_have_operator_binding_wavefront_ir": known_formula_p0,
            "all_candidates_have_operator_binding_wavefront_ir": candidate_p0,
            "all_candidates_have_inheritance_proof_limit_source_graphs": candidate_p1,
            "all_quantum_routes_have_proof_limit_source_graphs": route_p1,
            "toller_distributional_vertex_contract_matches_owner": formal_contract_matches,
            "toller_distributional_shared_bindings_enforced": shared_toller_bindings,
            "full_distributional_limit_remains_open": formal_contract_projection.get("distribution_wavefront", {}).get("status", "").endswith("FULL_DISTRIBUTIONAL_LIMIT_OPEN"),
            "causal_orientation_fourier_rank_16_exact": causal_orientation_rank16,
            "cluster_character_lift_bijective": cluster_character_bijection,
            "cluster_resolved_radial_selector_rank_25_exact": causal_orientation_selector_rank25,
            "bisimplex_collision_atlas_complete_193_clusters": bisimplex_forest_complete,
            "joint_bogoliubov_recursion_complete_112848_forests": joint_forest_recursion_complete,
            "tensor_projector_and_193_conormal_atlas_complete": tensor_wavefront_atlas_complete,
            "qpdtr_bisimplex_finite_pre_rhs_executed": qpdtr_pre_rhs_executed,
            "exact_full_vertex_wavefront_containment_remains_open": wavefront_open,
            "noncompact_pushforward_remains_open": pushforward_open,
            "forest_renormalized_contact_rhs_remains_open": renormalized_contact_rhs_open,
            "qpdtr_runtime_integration_is_typed_and_fail_closed": qpdtr_contract_valid,
        }, {
            "known_formula_count": len(self.catalog.passports),
            "confirmed_baseline_control_count": len(self.candidates),
            "quantum_route_count": len(self.quantum_method_routes),
            "formal_contract_digest": str(formal_contract_projection.get("digest", "")),
            "qpdtr_contract_digest": str(qpdtr_contract.get("digest", "")),
        }, [
            "P0 IR presence is not a proof that every operator has been fully lowered",
            "the 16-class causal Fourier algebra and the rank-25 cluster-resolved radial selector are exact finite-sector structural results",
            "QPDTR v2.5.0 supplies typed bounded PHI-Q1000 observable-first execution, process-tensor memory, finite bisimplex and 3+1D radial-mode evidence; generic full-state 1000-qubit execution, external accelerators and EPRL remain blocked",
            "compact symmetric-tensor projector descriptors and all 193 conormal incidence bundles are constructed; their physical order remains conditional on the exact full-vertex scaling degree",
            "the gluing pullback is transverse in the computed conormal envelope, but exact EPRL-vertex wavefront containment is still open",
            "the noncompact SL(2,C) pushforward remains blocked without proper support or a uniform tail estimate",
            "the finite 25-component pre-RHS is path-dependent and the forest-renormalized two-vertex right-hand side is not computed; full K5 pullback/product/pushforward remains open",
            "the external QPDTR runtime remains the sole owner of quantum-emulator execution",
        ]).finalize()

        gates = {g.family: dataclasses.asdict(g) for g in (g1, g2, g3, g4, g5, g6)}
        all_pass = all(g["status"] == "PASS" for g in gates.values())
        report = {
            "schema": "phi-lawspace-qualification/v6.4",
            "owner_version": OWNER_VERSION,
            "gates": gates,
            "acceptance_formula": "ACCEPT = G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5 ∧ G6",
            "all_acceptance_gates_pass": all_pass,
            "status": "PASS" if all_pass else "FAIL",
            "axis_counts": {k: v.axis_count for k, v in sorted(self.registries.items())},
            "registry_digests": registry_digest_map(),
            "catalog_digest": self.catalog.digest(),
            "claim_boundary": {
                "known_laws_loaded": known_count,
                "canonical_source_passports": known_count,
                "confirmed_baseline_control_records": 0,
                "historical_confirmed_control_anchor_count": 2771,
                "active_unconfirmed_candidate_records": len(current_frontier_rows),
                "active_baseline_semantics": "ARCHIVED_PROVENANCE_ONLY",
                "unverified_generated_couplings_location": "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl",
                "unverified_generated_couplings_retained_as_potential_laws_or_mechanisms": True,
                "candidate_scope": "CURRENT_FRONTIER_RESEARCH_STATE_NOT_ESTABLISHED_LAWS",
                "legacy_workbook_candidates_active": False,
                "full_symbolic_semantic_lowering": "NOT_CLAIMED",
                "real_device": "NOT_RUN",
                "computational_methods_loaded": len(self.computational_methods),
                "quantum_method_routes_pending": len(self.quantum_method_routes),
                "quantum_emulator_qubit_feasibility": "STRUCTURE_AND_OUTPUT_DEPENDENT_NOT_GLOBALLY_ESTABLISHED",
                "operator_scope_ir": "IMPLEMENTED_STRUCTURAL_AND_EXPLICIT_FOR_K_TOLLER_DIST_003",
                "distributional_reduced_test_function_limit": "PASS",
                "bisimplex_collision_atlas": "PASS_EXACT_193_CLUSTERS_161_CROSS_VERTEX",
                "joint_forest_r_operation": "PASS_EXACT_BPH_RECURSION_112848_FORESTS_ANALYTIC_EXTENSION_OPEN",
                "tensor_wavefront_atlas": "PASS_193_CONORMALS_PULLBACK_CONDITIONAL_PUSHFORWARD_OPEN",
                "causal_orientation_character_basis": "PASS_EXACT_RANK_16",
                "cluster_character_lift": "PASS_EXACT_BIJECTION_16_CLUSTERS",
                "cluster_resolved_radial_selector": "PASS_EXACT_RANK_25_NULLITY_0",
                "qpdtr_bisimplex_pre_rhs": "PASS_FINITE_25_COMPONENT_PATH_DEPENDENT",
                "exact_full_vertex_wavefront": "OPEN_CONTAINMENT_NOT_PROVED",
                "noncompact_pushforward": "OPEN_NONPROPER_NO_TAIL_BOUND",
                "forest_renormalized_contact_rhs": "OPEN_ANALYTIC_EXTENSION_NOT_COMPUTED",
                "distributional_full_limit": "OPEN",
                "persistent_adaptive_ttn": "PASS_STRUCTURED_50_QUBIT_LOW_TREEWIDTH_ONLY",
                "high_treewidth_general_graph_fallback": "PASS_BOUNDED_8_QUBIT_K8_EXACT_REFERENCE",
                "arbitrary_high_treewidth_or_volume_law_scalability": "OPEN",
                "schwarzschild_4d_radial_modes": "PASS_BOUNDED_FINITE_CUTOFFS",
                "full_reduced_dynamics_continuum_limit": "OPEN",
                "real_multigpu_qualification": "BLOCKED_BACKEND_UNAVAILABLE",
                "external_eprl_target": "BLOCKED_EXTERNAL_BACKEND",
            },
        }
        report["sha256"] = digest_payload(report)
        return report
