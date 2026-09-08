"""Authoritative P0/P1 formal-analysis contracts for Φ-Compiler CURRENT-STATE.

The objects built here are active semantic contracts. Reports and JSON files are
projections of these objects and never own the algorithm.
"""
from __future__ import annotations

import dataclasses
import re
from datetime import date
from typing import Any, Mapping, Sequence

from .schema import (
    DistributionWavefrontIR, ExpressionIR,
    LawPassport,
    LimitPath,
    LimitProtocol,
    OperatorScopeIR,
    PrimarySourceEntry,
    PrimarySourceLedger,
    ProofObligationGraph,
    ProofObligationNode,
    SharedBinding,
    SharedBindingGraph,
    digest_payload,
)

CURRENT_SNAPSHOT_DATE = "2026-08-01"
CURRENT_QG_SNAPSHOT_DATE = "2026-08-02"


def _source_identifier(provenance: Mapping[str, Any]) -> tuple[str, str, str, str]:
    url = str(provenance.get("source_url", "")).strip()
    reference = str(provenance.get("source_reference", "")).strip()
    source_id = str(provenance.get("source_id", "UNRECORDED_SOURCE")).strip() or "UNRECORDED_SOURCE"
    version = str(provenance.get("edition", provenance.get("accessed_date", "UNRECORDED_VERSION"))).strip() or "UNRECORDED_VERSION"
    snapshot = str(provenance.get("accessed_date", CURRENT_SNAPSHOT_DATE)).strip() or CURRENT_SNAPSHOT_DATE
    if "arxiv.org/abs/" in url:
        return "ARXIV", url.rsplit("/", 1)[-1], version, snapshot
    if "doi.org/" in url:
        return "DOI", url.split("doi.org/", 1)[-1], version, snapshot
    if url:
        return "URL", url, version, snapshot
    if reference:
        return "SOURCE_REFERENCE", reference, version, snapshot
    return "INTERNAL_SOURCE_ID", source_id, version, snapshot


def source_ledger_from_passports(passports: Sequence[LawPassport], *, ledger_id: str) -> PrimarySourceLedger:
    entries: list[PrimarySourceEntry] = []
    seen: set[str] = set()
    complete = True
    for passport in passports:
        provenance = passport.provenance
        identifier_type, identifier, version, snapshot = _source_identifier(provenance)
        source_id = f"{passport.owner_id}:{provenance.get('source_id', 'UNRECORDED_SOURCE')}"
        if source_id in seen:
            continue
        seen.add(source_id)
        if identifier_type == "INTERNAL_SOURCE_ID" or "UNRECORDED" in version:
            complete = False
        entries.append(PrimarySourceEntry(
            source_id=source_id,
            identifier_type=identifier_type,
            identifier=identifier,
            version=version,
            snapshot_date=snapshot,
            formula_signature=passport.formula.digest,
            claim_scope="source formula and declared validity domain only",
        ))
    return PrimarySourceLedger(
        ledger_id=ledger_id,
        entries=tuple(entries),
        external_novelty_status="NOT_SEARCHED",
        status="COMPLETE_IDENTIFIERS" if complete and entries else "PARTIAL_SOURCE_NORMALIZATION",
    ).finalized()


def source_ledger_from_methods(methods: Sequence[Mapping[str, Any]], *, ledger_id: str) -> PrimarySourceLedger:
    entries: list[PrimarySourceEntry] = []
    complete = True
    for method in methods:
        provenance = method.get("provenance", {})
        if not isinstance(provenance, Mapping):
            provenance = {}
        identifier_type, identifier, version, snapshot = _source_identifier(provenance)
        if identifier_type == "INTERNAL_SOURCE_ID" or "UNRECORDED" in version:
            complete = False
        entries.append(PrimarySourceEntry(
            source_id=str(method["method_id"]),
            identifier_type=identifier_type,
            identifier=identifier,
            version=version,
            snapshot_date=snapshot,
            formula_signature=str(method.get("digest", digest_payload(method))),
            claim_scope="established computational method and stated limitations only",
        ))
    return PrimarySourceLedger(
        ledger_id=ledger_id,
        entries=tuple(entries),
        external_novelty_status="NOT_APPLICABLE_TO_METHOD_COMPOSITION",
        status="COMPLETE_IDENTIFIERS" if complete and entries else "PARTIAL_SOURCE_NORMALIZATION",
    ).finalized()




_STRUCTURAL_SYMBOLS = {
    "R_base", "Psi", "Integral", "Sum", "exp", "log", "ln", "sin", "cos",
    "partial_t", "grad", "div", "curl", "Tr", "Birth", "Death", "Growth",
    "moments", "det", "diag", "commutator", "anticommutator",
}

def candidate_inheritance_contract(
    candidate_id: str,
    passports: Sequence[LawPassport],
    expression: ExpressionIR,
    *,
    dimension_contract: Mapping[str, Any],
    controlled_limits: Sequence[str],
    transformation_id: str,
) -> Mapping[str, Any]:
    """Exact boundary between inherited source results and new coupled content.

    The composition inherits only properties preserved by the registered
    transformation on the intersection of source validity domains.  Empirical
    adequacy, coupling closure and numerical parameter values are not copied
    from the sources.
    """
    source_symbols = sorted({symbol for passport in passports for symbol in passport.formula.symbols})
    candidate_symbols = sorted(set(expression.symbols))
    introduced = sorted(set(candidate_symbols) - set(source_symbols))
    call_like = set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*[\[(]", expression.source))
    operator_symbols = sorted(set(introduced) & (call_like | _STRUCTURAL_SYMBOLS))
    introduced_quantities = sorted(set(introduced) - set(operator_symbols) - {"Psi"})
    coefficient_pattern = re.compile(
        r"^(?:lambda|kappa|gamma|alpha|beta|eta|theta|tau|ell|chi|xi|zeta|mu|nu|D|K|G|C|c|g|k)(?:_|[0-9A-Za-z].*)?$",
        re.IGNORECASE,
    )
    coefficient_candidates = sorted(symbol for symbol in introduced_quantities if coefficient_pattern.match(symbol))
    inherited_constant_ids = sorted({constant_id for passport in passports for constant_id in passport.constants})
    validity_domains = [passport.validity_domain or "UNRECORDED_VALIDITY_DOMAIN" for passport in passports]
    source_states = {passport.owner_id: passport.epistemic_state for passport in passports}
    verified_source_states = {"ESTABLISHED_LAW", "EXPERIMENTALLY_CONFIRMED"}
    source_basis_class = (
        "VERIFIED_SOURCE_BASIS"
        if set(source_states.values()).issubset(verified_source_states)
        else "MODEL_DEPENDENT_SOURCE_BASIS"
    )
    dimension_status = str(dimension_contract.get("status", "UNRESOLVED"))
    contract = {
        "schema": "phi-property-inheritance/v1",
        "contract_id": candidate_id + ":INHERITANCE",
        "transformation_id": transformation_id,
        "source_owner_ids": [passport.owner_id for passport in passports],
        "source_epistemic_states": source_states,
        "source_basis_class": source_basis_class,
        "validity_domain_rule": {
            "operation": "INTERSECTION",
            "source_domains": validity_domains,
            "status": "INHERITED_ONLY_ON_SOURCE_VALIDITY_INTERSECTION",
        },
        "inherited_properties": {
            "source_sector_equations": "PRESERVED_BY_OWNER_REFERENCE",
            "source_sector_evidence": "PRESERVED_ONLY_FOR_UNCOUPLED_SOURCE_SECTORS",
            "dimensional_homogeneity": dimension_status,
            "controlled_source_recovery": "DECLARED_NOT_EXECUTED" if controlled_limits else "MISSING",
        },
        "properties_requiring_new_proof": {
            "coupling_operator": "OPEN",
            "symmetry_preservation": "OPEN_UNLESS_TRANSFORMATION_EQUIVARIANCE_PROVED",
            "conservation_closure": "OPEN_UNLESS_BALANCE_OR_NOETHER_PROOF_EXISTS",
            "causality_and_locality": "OPEN",
            "positivity_or_CPTP": "OPEN_WHEN_APPLICABLE",
            "well_posedness_and_stability": "OPEN",
            "empirical_transfer_to_coupled_regime": "OPEN",
        },
        "symbol_partition": {
            "inherited_source_symbols": source_symbols,
            "candidate_symbols": candidate_symbols,
            "introduced_operator_symbols": operator_symbols,
            "introduced_quantity_symbols": introduced_quantities,
            "introduced_coefficient_candidates": coefficient_candidates,
            "inherited_constant_ids": inherited_constant_ids,
            "classification_scope": "SYNTACTIC_INDEX_REQUIRES_DOMAIN_LOWERING",
        },
        "quantity_resolution_protocol": [
            "resolve exact and measured constants from the registered constant owner",
            "derive coefficients fixed by symmetry, conservation, constitutive or variational closure",
            "test structural identifiability before numerical fitting",
            "estimate remaining parameters with uncertainty from independent data",
        ],
        "promotion_criteria": {
            "mathematically_derived_composite_law": [
                "source owners are admissible for the claimed domain",
                "the coupling operator follows from a proved closure, variational principle, symmetry or conservation argument",
                "all introduced quantities are resolved or eliminated",
                "well-posedness, stability and mandatory invariants are proved",
                "controlled source limits are executed and recovered",
            ],
            "empirically_validated_composite_law": [
                "all mathematically derived criteria pass",
                "structural and practical identifiability pass",
                "blind coupled-regime predictions pass on independent data",
                "uncertainty and validity range are reported",
            ],
            "current_status": "NOT_YET_EVALUATED_AS_A_PROMOTED_LAW",
        },
        "scientific_status": "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED",
        "digest": "",
    }
    contract["digest"] = digest_payload({**contract, "digest": ""})
    return contract


def candidate_proof_graph(candidate_id: str) -> ProofObligationGraph:
    nodes = (
        ProofObligationNode("formal_ir", "Формула разобрана и снабжена operator/binding/distribution IR", status="PASS"),
        ProofObligationNode("source_inheritance", "Исходные owners и область пересечения применимости зафиксированы", ("formal_ir",), "PASS"),
        ProofObligationNode("coupling_closure", "Новый оператор связи выведен, а не только объявлен шаблоном", ("source_inheritance",), "OPEN"),
        ProofObligationNode("quantity_resolution", "Новые переменные и коэффициенты классифицированы и разрешены", ("coupling_closure",), "OPEN"),
        ProofObligationNode("limit", "Контролируемый предел и независимость кофинальных путей", ("coupling_closure",), "OPEN"),
        ProofObligationNode("stability", "Корректность задачи Коши, устойчивость и сохранение обязательных инвариантов", ("limit",), "OPEN"),
        ProofObligationNode("scheme", "Численная схема с явным бюджетом ошибки", ("stability",), "OPEN"),
        ProofObligationNode("numerical_certificate", "Воспроизводимый численный сертификат", ("scheme",), "OPEN"),
        ProofObligationNode("primary_sources", "Проверка первичных источников и эквивалентных форм", ("formal_ir",), "OPEN"),
        ProofObligationNode("identifiability", "Структурная и практическая идентифицируемость", ("quantity_resolution", "numerical_certificate"), "OPEN"),
        ProofObligationNode("experiment", "Слепой эксперимент и независимое повторение coupled-regime предсказаний", ("identifiability", "primary_sources"), "OPEN"),
    )
    return ProofObligationGraph(candidate_id + ":PROOF", nodes, status="SOURCE_INHERITANCE_PASS_COUPLING_OPEN").finalized()


def method_route_proof_graph(route_id: str) -> ProofObligationGraph:
    nodes = (
        ProofObligationNode("method_passports", "Все методы имеют типизированные паспорта", status="PASS"),
        ProofObligationNode("limit", "Сходимость по bond/time/memory/precision cutoffs", ("method_passports",), "OPEN"),
        ProofObligationNode("stability", "Стабильность маршрута и deterministic replay", ("limit",), "OPEN"),
        ProofObligationNode("scheme", "Единый составной алгоритм и error budget", ("stability",), "OPEN"),
        ProofObligationNode("numerical_certificate", "Сравнение с exact small-instance reference", ("scheme",), "OPEN"),
        ProofObligationNode("hardware", "CPU equality и реальная multi-GPU/MPI квалификация", ("numerical_certificate",), "OPEN"),
        ProofObligationNode("workload_claim", "Ограниченный claim по кубитам для конкретной нагрузки", ("hardware",), "OPEN"),
    )
    return ProofObligationGraph(route_id + ":PROOF", nodes, status="OPEN_COMPUTATIONAL_QUALIFICATION").finalized()


def candidate_limit_protocol(candidate_id: str, controlled_limits: Sequence[str]) -> LimitProtocol:
    regulators = tuple(f"limit_{i}:{text}" for i, text in enumerate(controlled_limits, 1)) or ("formal_limit_not_instantiated",)
    if len(regulators) > 1:
        paths = (
            LimitPath("forward", regulators, "sequential forward removal", "declared limiting model"),
            LimitPath("reverse", tuple(reversed(regulators)), "sequential reverse removal", "declared limiting model"),
            LimitPath("diagonal", regulators, "cofinal diagonal schedule", "declared limiting model"),
        )
    else:
        paths = (LimitPath("single", regulators, "single declared limit path", "declared limiting model"),)
    return LimitProtocol(
        protocol_id=candidate_id + ":LIMIT",
        regulators=regulators,
        cofinal_paths=paths,
        tail_estimate_status="NOT_RUN",
        path_independence_status="NOT_RUN" if len(paths) > 1 else "NOT_APPLICABLE_SINGLE_LIMIT",
        precision_switch_policy="switch to >=80-bit arithmetic when cancellation estimate, condition number or residual exceeds the registered threshold",
        claim_scope="CANDIDATE_LIMIT_NOT_PROVED",
        status="OPEN",
    ).finalized()


def method_route_limit_protocol(route_id: str, methods: Sequence[Mapping[str, Any]]) -> LimitProtocol:
    regulators = ("bond_dimension", "time_step", "memory_cutoff", "svd_cutoff", "floating_precision")
    paths = (
        LimitPath("accuracy_first", regulators, "chi↑, dt↓, memory↑, cutoff↓, precision↑", "registered observable tolerance"),
        LimitPath("memory_first", ("memory_cutoff", "svd_cutoff", "bond_dimension", "time_step", "floating_precision"), "memory convergence before state compression", "registered observable tolerance"),
        LimitPath("diagonal", regulators, "joint cofinal schedule under fixed resource envelope", "registered observable tolerance"),
    )
    return LimitProtocol(
        protocol_id=route_id + ":LIMIT",
        regulators=regulators,
        cofinal_paths=paths,
        tail_estimate_status="NOT_RUN",
        path_independence_status="NOT_RUN",
        precision_switch_policy="promote float64->longdouble/mpmath when roundoff bound exceeds 10% of remaining error budget",
        claim_scope="REGULATOR_INDEPENDENT_LIMIT",
        status="OPEN_COMPUTATIONAL_CONVERGENCE",
    ).finalized()


def toller_distributional_vertex_contract() -> Mapping[str, Any]:
    """Current-state causal Toller contract.

    `COUPLED-WEDGE-KERNEL-011` is a local kernel inside this contract, not a
    second vertex owner.  The executable evidence covers a finite shared-channel
    wedge, the test-function Feynman boundary-value identity, and the nested
    K3/K4/K5 forest combinatorics.  The complete bisimplex collision atlas is
    enumerated on K5 union_S K5 before any joint R-operation.
    CAUSAL-ORIENTATION-FOURIER-014 supplies the
    exact 16-character Fourier algebra of causal edge orientations and a
    cluster-resolved radial selector of exact rank 25.  Its forest-renormalized
    right-hand side, the full tensorial basis and the non-compact EPRL vertex
    remain open.
    """

    scope = OperatorScopeIR(
        domain_definition=(
            "principal-series boundary data; one shared spectral variable rho_tilde; "
            "complete intermediate SU(2) channel (q,p); Schwartz test functions for "
            "the epsilon->0 boundary-value qualification"
        ),
        codomain_definition=(
            "regulated coupled-wedge amplitude, test-function distribution pairing, "
            "and reduced homogeneous j=1/2 K5 forest certificate"
        ),
        measure=(
            "d rho_tilde times the exact Feynman Toller weight; finite quadrature for "
            "the wedge and adaptive real-axis integration for Schwartz pairings"
        ),
        adjoint_structure=(
            "left half-edge is complex-conjugated; K_z is Hermitian in the finite "
            "canonical-spin sector; opposite Toller branches are adjoint on the real axis"
        ),
        limit_topology=(
            "weak distribution topology on the registered test-function family; the 193-stratum "
            "conormal atlas and a conditional gluing-pullback test are available, while exact "
            "full-vertex wavefront containment and noncompact pushforward remain open"
        ),
        status="REDUCED_DISTRIBUTIONAL_SCOPE_EXPLICIT_FULL_VERTEX_OPEN",
        assumptions=(
            "one spectral projector owns the whole wedge",
            "complete intermediate channel retained at the declared cutoff",
            "test functions are Schwartz and the equal-spin projection kernel is the exact finite polynomial",
            "K3/K4/K5 scaling certificate uses the compact three-dimensional coincidence model",
            "the reduced compact scaling order is not promoted to the exact SL(2,C) vertex scaling degree",
        ),
    ).finalized()

    nodes = (
        "rho_left", "rho_right", "q_left", "q_right", "p_left", "p_right",
        "wedge_projector", "test_function", "forest_cluster",
    )
    bindings = SharedBindingGraph(
        nodes=nodes,
        bindings=(
            SharedBinding("rho_shared", ("rho_left", "rho_right", "wedge_projector")),
            SharedBinding("q_shared", ("q_left", "q_right")),
            SharedBinding("p_shared", ("p_left", "p_right")),
        ),
        bound_indices=("q_left", "q_right", "p_left", "p_right"),
        status="SHARED_WEDGE_BINDINGS_ENFORCED",
    ).finalized()

    wavefront = DistributionWavefrontIR(
        distribution_space=(
            "finite epsilon>0 kernels are Lorentz-group functions; reduced spectral boundary values "
            "act on Schwartz tests; the glued two-vertex target is a distribution whose candidate "
            "contact singularities lie on the 193 collision diagonals"
        ),
        wavefront_description=(
            "For every reduced collision stratum Delta_H the conormal incidence bundle N*Delta_H is "
            "constructed exactly.  The external-product conormal envelope is transverse to the "
            "shared-tetrahedron gluing normal, but exact EPRL-vertex wavefront containment is open. "
            "Toller pole cancellation forbids identifying primitive pole cones with the full vertex wavefront."
        ),
        operations=(
            "external_tensor_product", "pullback_to_shared_tetrahedron_diagonal",
            "glued_joint_forest_extension", "pushforward_over_noncompact_internal_variables",
            "distribution_product",
        ),
        pullback_map=(
            "iota identifies the independent shared tetrahedra S_L=S_R before the cross-vertex "
            "joint forest is applied on the glued configuration"
        ),
        pushforward_map="integration/summation over internal SL(2,C), spectral, canonical and gluing variables",
        tensor_product_status="PASS_REDUCED_BOUNDARY_VALUES_AND_CONORMAL_ENVELOPE",
        product_condition=(
            "WF(A_L boxtimes conjugate(A_R)) intersect N*iota must be empty; the exact incidence "
            "calculation proves this for the collision-conormal envelope, conditionally on exact WF containment"
        ),
        product_status="PASS_CONORMAL_ENVELOPE_PULLBACK_CONDITIONAL_EXACT_VERTEX_WF_OPEN",
        status="CONORMAL_ATLAS_RECORDED_PULLBACK_CONDITIONAL_PUSHFORWARD_OPEN_FULL_DISTRIBUTIONAL_LIMIT_OPEN",
    ).finalized()

    proof = ProofObligationGraph(
        "K-TOLLER-DIST-003:PROOF",
        (
            ProofObligationNode("scope", "OperatorScopeIR complete", status="PASS"),
            ProofObligationNode("bindings", "Shared spectral and canonical bindings enforced", ("scope",), "PASS"),
            ProofObligationNode("finite_equivalence", "Direct and coupled finite-regulator wedge representations agree", ("bindings",), "PASS"),
            ProofObligationNode("branch_sum", "T+ + T- recovers the Wigner distribution on Schwartz tests", ("finite_equivalence",), "PASS_REDUCED_TEST_FUNCTIONS"),
            ProofObligationNode("forest", "Nested K3/K4/K5 divergent-cluster forest is enumerated", ("branch_sum",), "PASS_COMBINATORIAL_JHALF"),
            ProofObligationNode("bisimplex_forest", "Complete connected collision atlas of K5 union_S K5", ("forest",), "PASS_EXACT_193_CLUSTERS"),
            ProofObligationNode("joint_forest_recursion", "Exact Bogoliubov preparation/counterterm recursion and complete Zimmermann forest catalog", ("bisimplex_forest",), "PASS_EXACT_112848_FORESTS"),
            ProofObligationNode("tensor_wavefront_atlas", "Compact symmetric-tensor Taylor descriptors and exact conormal incidence bundles for all 193 reduced collision strata; gluing pullback is transverse in the conormal envelope", ("joint_forest_recursion",), "PASS_193_CONORMALS_PULLBACK_CONDITIONAL"),
            ProofObligationNode("orientation_fourier", "The 16 causal classes modulo global reversal form an exact Hadamard character basis generated by wedge signs", ("joint_forest_recursion",), "PASS_EXACT_RANK_16"),
            ProofObligationNode("cluster_character_lift", "Ten K3, five K4 and one K5 compact clusters map bijectively to the 16 even orientation characters", ("orientation_fourier",), "PASS_EXACT_BIJECTION"),
            ProofObligationNode("orientation_structural_selector", "Orientation Fourier projectors and radial contact probes form an exact rank-25 selector on the cluster-resolved radial-scalar basis", ("cluster_character_lift",), "PASS_EXACT_RANK_25"),
            ProofObligationNode("qpdtr_bisimplex_pre_rhs", "Typed QPDTR v2.5.0 bisimplex, j=1/2 boundary and regularized measure feed a 25-component finite-regulator pre-RHS extraction", ("orientation_structural_selector",), "PASS_FINITE_PRE_RHS_PATH_DEPENDENT"),
            ProofObligationNode("wavefront", "Exact full EPRL vertex wavefront containment in the computed conormal atlas", ("tensor_wavefront_atlas",), "OPEN_EXACT_VERTEX_WF_CONTAINMENT"),
            ProofObligationNode("pushforward", "Noncompact internal SL(2,C) pushforward is proper on support or has a uniform tail estimate", ("wavefront",), "OPEN_NONPROPER_NO_TAIL_BOUND"),
            ProofObligationNode("renormalized_contact_rhs", "Forest-renormalized two-vertex amplitudes supply the physical right-hand side of the rank-25 selector", ("qpdtr_bisimplex_pre_rhs", "wavefront", "pushforward"), "OPEN_ANALYTIC_EXTENSION_NOT_COMPUTED"),
            ProofObligationNode("limit", "Cofinal cutoff removal and path independence in distribution topology", ("renormalized_contact_rhs",), "OPEN"),
            ProofObligationNode("scheme", "Full SL(2,C)^4 numerical scheme and shell sums", ("limit",), "OPEN"),
            ProofObligationNode("numerical_certificate", "Independent full-vertex numerical certificate", ("scheme",), "OPEN"),
            ProofObligationNode("experiment", "Frozen physical prediction and independent experiment", ("numerical_certificate",), "OPEN"),
        ),
        status="TENSOR_CONORMAL_ATLAS_COMPLETE_EXACT_VERTEX_WF_AND_PUSHFORWARD_OPEN",
    ).finalized()

    limit = LimitProtocol(
        "K-TOLLER-DIST-003:LIMIT",
        ("test_epsilon", "test_support_cutoff", "spectral_cutoff", "canonical_spin_cutoff", "noncompact_group_cutoff"),
        (
            LimitPath(
                "test_function_first",
                ("test_support_cutoff", "test_epsilon", "spectral_cutoff", "canonical_spin_cutoff", "noncompact_group_cutoff"),
                "prove weak boundary-value convergence on Schwartz tests before attempting physical cutoff removal",
                "reduced Toller distribution",
            ),
            LimitPath(
                "spectral_first",
                ("spectral_cutoff", "canonical_spin_cutoff", "test_epsilon", "noncompact_group_cutoff"),
                "Lambda_rho up, then j_cut up, then epsilon down, then group cutoff up",
                "candidate causal wedge distribution",
            ),
            LimitPath(
                "spin_first",
                ("canonical_spin_cutoff", "spectral_cutoff", "test_epsilon", "noncompact_group_cutoff"),
                "j_cut up, then Lambda_rho up, then epsilon down, then group cutoff up",
                "candidate causal wedge distribution",
            ),
            LimitPath(
                "diagonal",
                ("spectral_cutoff", "canonical_spin_cutoff", "test_epsilon", "noncompact_group_cutoff"),
                "joint cofinal schedule with explicit path comparison",
                "candidate causal wedge distribution",
            ),
        ),
        tail_estimate_status="PASS_REDUCED_SCHWARTZ_TESTS_PHYSICAL_WEDGE_OPEN",
        path_independence_status="ORDINARY_WEDGE_QUADRATURE_NONCONVERGENT_DISTRIBUTIONAL_EXTENSION_REQUIRED",
        precision_switch_policy=(
            "switch complex128 to mpmath >=80 digits when pole cancellation loses more than 8 decimal digits, "
            "condition estimate exceeds 1e10, or the quadrature envelope stops contracting"
        ),
        claim_scope="REDUCED_WEAK_DISTRIBUTIONAL_LIMIT_ONLY",
        status="PARTIAL_EXECUTED_FULL_COFINAL_LIMIT_OPEN",
    ).finalized()

    ledger = PrimarySourceLedger(
        "K-TOLLER-DIST-003:SOURCES",
        (
            PrimarySourceEntry("TOLLER-CAUSAL-2026", "ARXIV", "2601.23162", "v1", CURRENT_QG_SNAPSHOT_DATE, digest_payload("T(+)+T(-)=D; causal EPRL vertex"), "causal Toller vertex and constrained causal structures"),
            PrimarySourceEntry("TOLLER-ANALYTIC-2026", "ARXIV", "2604.24945", "v1", CURRENT_QG_SNAPSHOT_DATE, digest_payload("P_jl(rho_tilde;rho); Feynman i-epsilon boundary values; residue and Wick representations"), "exact analytic representations of Toller matrices"),
            PrimarySourceEntry("CAUSAL-GENERALIZED-2026", "ARXIV", "2603.22661", "v1", CURRENT_QG_SNAPSHOT_DATE, digest_payload("causal edge orientations on arbitrary 2-complexes and consistency of induced wedge orientations"), "causal orientation classes and compatibility on generalized EPRL complexes"),
            PrimarySourceEntry("SPINFOAM-CONTINUUM-2026", "ARXIV", "2603.16999", "v1", CURRENT_QG_SNAPSHOT_DATE, digest_payload("distributional spin-foam continuum limit; cylinder rigging map; strong-limit no-go"), "distributional continuum and physical cylinder requirements"),
            PrimarySourceEntry("SL2CFOAM-NEXT", "ARXIV", "2107.13952", "published version", CURRENT_QG_SNAPSHOT_DATE, digest_payload("Lorentzian EPRL numerical library and parallelization"), "ordinary Lorentzian EPRL numerical backend"),
            PrimarySourceEntry("EPRL-NUMERICS", "ARXIV", "1807.03066", "published version", CURRENT_QG_SNAPSHOT_DATE, digest_payload("intertwiner basis; booster functions; SL(2,C) Clebsch-Gordan"), "ordinary EPRL representation decomposition"),
            PrimarySourceEntry("EPRL-MAP", "ARXIV", "0912.0540", "published version", CURRENT_QG_SNAPSHOT_DATE, digest_payload("EPRL map injectivity and corrected partition function"), "EPRL intertwiner-map semantics"),
            PrimarySourceEntry("CONFIGURATION-BPHZ", "ARXIV", "1706.06762", "v3", CURRENT_QG_SNAPSHOT_DATE, digest_payload("configuration-space Taylor subtractions; Zimmermann convergence theorem; decay condition"), "configuration-space forest extension and tail hypotheses"),
            PrimarySourceEntry("WF-OPERATIONS", "ARXIV", "1409.7662", "published version", CURRENT_QG_SNAPSHOT_DATE, digest_payload("wavefront conditions for multiplication pullback and pushforward"), "continuity and admissibility of fundamental distribution operations"),
        ),
        external_novelty_status="LOCAL_IMPLEMENTATION_NOVELTY_NOT_WORLD_NOVELTY_CLAIM",
        status="PRIMARY_IDENTIFIERS_RECORDED",
    ).finalized()

    contract = {
        "schema": "phi-toller-distributional-vertex-contract/v4.1",
        "contract_id": "K-TOLLER-DIST-003",
        "local_kernel_id": "COUPLED-WEDGE-KERNEL-011",
        "operator_scope": dataclasses.asdict(scope),
        "shared_binding_graph": dataclasses.asdict(bindings),
        "distribution_wavefront": dataclasses.asdict(wavefront),
        "proof_obligation_graph": dataclasses.asdict(proof),
        "limit_protocol": dataclasses.asdict(limit),
        "primary_source_ledger": dataclasses.asdict(ledger),
        "claim_boundary": (
            "reduced Schwartz-test branch recovery, one-vertex forest combinatorics, complete 193-cluster bisimplex collision atlas, exact 112848-forest Bogoliubov recursion, exact 16-sector causal Fourier algebra, an exact rank-25 cluster-resolved radial measurement operator, a typed QPDTR finite-regulator 25-component pre-RHS diagnostic, and the multidimensional law/candidate/joint-method closure scan; "
            "compact tensor-projector descriptors and the 193-stratum conormal atlas are current; exact full-vertex scaling degrees and wavefront containment, noncompact pushforward, forest-renormalized physical right-hand side, physical cylinder and continuum remain open"
        ),
        "digest": "",
    }
    contract["digest"] = digest_payload({**contract, "digest": ""})
    return contract

