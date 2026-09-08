"""Authoritative algebraic experimental owner for the neutrino sector.

The owner separates exact algebraic admissibility from statistical fit quality.
It constructs polynomial ideals, runs exact and library-search injections, and
passes every materialized component through a symbolic verifier.  Components
that are inconsistent, positive-dimensional, or otherwise non-identifiable
remain diagnostic and cannot be promoted by a small numerical residual.

The current qualification covers three exact obligations relevant to the
neutrino programme:

* PMNS unitarity modulo the trigonometric normalization ideal;
* exact cancellation of Majorana phases from oscillation propagation;
* exact recovery of a hidden oscillatory residual basis from a finite library,
  including a deliberately degenerate negative control.

This owner does not replace an experiment likelihood.  It proves algebraic
properties of a declared model and its parameterization; real-data evidence is
owned by ``NEUTRINO-REAL-DATA-LIKELIHOOD``.
"""
from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

import sympy as sp

OWNER_ID = "NEUTRINO-ALGEBRAIC-EXPERIMENT"
OWNER_VERSION = "5.6.0"
SCHEMA = "phi-neutrino-algebraic-experiment/v5.6"
QUALIFICATION_SCHEMA = "phi-neutrino-algebraic-qualification/v5.6"
_PMNS_CACHE: Mapping[str, Any] | None = None
_MAJORANA_CACHE: Mapping[str, Any] | None = None
_MASS_SHIFT_CACHE: Mapping[str, Any] | None = None
_MINIMUM_MASS_CACHE: Mapping[str, Any] | None = None
_TAKAGI_BLOCK_CACHE: Mapping[str, Any] | None = None
_DIRAC_LNV_CACHE: Mapping[str, Any] | None = None
_SEESAW_CACHE: Mapping[str, Any] | None = None
_QUALIFICATION_CACHE: Mapping[str, Any] | None = None


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _rational(value: int | Fraction | sp.Rational) -> sp.Rational:
    if isinstance(value, sp.Rational):
        return value
    if isinstance(value, Fraction):
        return sp.Rational(value.numerator, value.denominator)
    return sp.Rational(value)


@dataclass(frozen=True)
class AlgebraicComponent:
    component_id: str
    status: str
    variables: tuple[str, ...]
    generators: tuple[str, ...]
    groebner_basis: tuple[str, ...]
    solution_count: int | None
    exact_solution: Mapping[str, str] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SearchCandidate:
    candidate_id: str
    basis_ids: tuple[str, ...]
    parameter_symbols: tuple[str, ...]


class NeutrinoAlgebraicExperimentalOwner:
    """Single owner of exact algebraic qualification for neutrino candidates."""

    @staticmethod
    def _reduce_polynomial(expr: sp.Expr, groebner: sp.GroebnerBasis) -> sp.Expr:
        expanded = sp.together(sp.expand(expr))
        numerator, denominator = sp.fraction(expanded)
        if denominator != 1:
            numerator = sp.expand(numerator)
        _, remainder = groebner.reduce(numerator)
        return sp.expand(remainder)

    def pmns_unitarity_certificate(self) -> Mapping[str, Any]:
        global _PMNS_CACHE
        if _PMNS_CACHE is not None:
            return _PMNS_CACHE
        s12, c12, s13, c13, s23, c23, sd, cd = sp.symbols(
            "s12 c12 s13 c13 s23 c23 sd cd", real=True
        )
        z = cd + sp.I * sd
        zc = cd - sp.I * sd
        u = sp.Matrix(
            [
                [c12 * c13, s12 * c13, s13 * zc],
                [-s12 * c23 - c12 * s23 * s13 * z, c12 * c23 - s12 * s23 * s13 * z, s23 * c13],
                [s12 * s23 - c12 * c23 * s13 * z, -c12 * s23 - s12 * c23 * s13 * z, c23 * c13],
            ]
        )
        generators = (
            c12**2 + s12**2 - 1,
            c13**2 + s13**2 - 1,
            c23**2 + s23**2 - 1,
            cd**2 + sd**2 - 1,
        )
        variables = (c12, s12, c13, s13, c23, s23, cd, sd)
        ideal = sp.groebner(generators, *variables, order="lex", domain=sp.QQ)
        residual = sp.simplify(sp.conjugate(u.T) * u - sp.eye(3))
        remainders: list[str] = []
        for entry in residual:
            real = self._reduce_polynomial(sp.re(entry).expand(complex=True), ideal)
            imag = self._reduce_polynomial(sp.im(entry).expand(complex=True), ideal)
            remainders.extend((str(real), str(imag)))
        passed = all(value == "0" for value in remainders)
        payload = {
            "obligation_id": "PMNS-UNITARITY-IDEAL",
            "status": "PROVED_EXACT_MODULO_IDEAL" if passed else "BLOCKED_NONZERO_REMAINDER",
            "variables": tuple(str(v) for v in variables),
            "ideal_generators": tuple(str(g) for g in generators),
            "groebner_basis": tuple(str(g) for g in ideal.polys),
            "entry_real_imag_remainders": tuple(remainders),
            "all_remainders_zero": passed,
        }
        _PMNS_CACHE = {**payload, "digest": _digest(payload)}
        return _PMNS_CACHE

    def majorana_phase_cancellation_certificate(self) -> Mapping[str, Any]:
        global _MAJORANA_CACHE
        if _MAJORANA_CACHE is not None:
            return _MAJORANA_CACHE
        p1, p2, p3, q1, q2, q3, d1, d2, d3 = sp.symbols("p1 p2 p3 q1 q2 q3 d1 d2 d3")
        p = sp.diag(p1, p2, p3)
        pinv = sp.diag(q1, q2, q3)
        d = sp.diag(d1, d2, d3)
        generators = (p1 * q1 - 1, p2 * q2 - 1, p3 * q3 - 1)
        variables = (p1, q1, p2, q2, p3, q3, d1, d2, d3)
        ideal = sp.groebner(generators, *variables, order="lex", domain=sp.QQ)
        residual = p * d * pinv - d
        remainders = tuple(str(self._reduce_polynomial(entry, ideal)) for entry in residual)
        passed = all(value == "0" for value in remainders)
        payload = {
            "obligation_id": "MAJORANA-PHASE-OSCILLATION-CANCELLATION",
            "status": "PROVED_EXACT_MODULO_UNIT_PHASE_IDEAL" if passed else "BLOCKED_NONZERO_REMAINDER",
            "ideal_generators": tuple(str(g) for g in generators),
            "remainders": remainders,
            "interpretation": "RIGHT_DIAGONAL_PHASES_COMMUTE_WITH_MASS_PROPAGATION_AND_CANCEL_WITH_THEIR_INVERSES",
            "dirac_majorana_decision_from_oscillations": False,
        }
        _MAJORANA_CACHE = {**payload, "digest": _digest(payload)}
        return _MAJORANA_CACHE


    def mass_squared_shift_invariance_certificate(self) -> Mapping[str, Any]:
        """Prove that oscillations are blind to a common mass-squared shift.

        A common shift multiplies every propagation amplitude by the same unit
        complex phase.  The real two-dimensional rotation below is the exact
        polynomial form of that statement; its squared norm is reduced modulo
        the unit-circle ideal rather than checked at sampled parameter values.
        """
        global _MASS_SHIFT_CACHE
        if _MASS_SHIFT_CACHE is not None:
            return _MASS_SHIFT_CACHE
        a, b, c, s = sp.symbols("a b c s", real=True)
        generators = (c**2 + s**2 - 1,)
        ideal = sp.groebner(generators, c, s, a, b, order="lex", domain=sp.QQ)
        shifted_real = c * a - s * b
        shifted_imag = s * a + c * b
        residual = sp.expand(shifted_real**2 + shifted_imag**2 - (a**2 + b**2))
        remainder = self._reduce_polynomial(residual, ideal)
        passed = remainder == 0
        payload = {
            "obligation_id": "COMMON-MASS-SQUARED-SHIFT-INVARIANCE",
            "status": "PROVED_EXACT_MODULO_UNIT_PHASE_IDEAL" if passed else "BLOCKED_NONZERO_REMAINDER",
            "ideal_generators": tuple(str(g) for g in generators),
            "probability_residual": str(residual),
            "groebner_remainder": str(remainder),
            "all_remainders_zero": passed,
            "interpretation": "MASS_SQUARED_SHIFT_MULTIPLIES_THE_FULL_PROPAGATOR_BY_ONE_GLOBAL_UNIT_PHASE",
            "absolute_mass_scale_identifiable_from_oscillations": False,
        }
        _MASS_SHIFT_CACHE = {**payload, "digest": _digest(payload)}
        return _MASS_SHIFT_CACHE

    def minimum_two_massive_states_certificate(self) -> Mapping[str, Any]:
        """Exclude an at-most-one-massive spectrum from two independent gaps.

        ``x1,x2,x3`` denote squared masses.  Nonzero invertible ``d21`` and
        ``d31``, together with an invertible difference ``d31-d21``, encode two
        independent nonzero unequal splittings.  The three pairwise products
        encode the counter-hypothesis that at most one squared mass is nonzero.
        The unit ideal proves that these assumptions are algebraically
        inconsistent.
        """
        global _MINIMUM_MASS_CACHE
        if _MINIMUM_MASS_CACHE is not None:
            return _MINIMUM_MASS_CACHE
        x1, x2, x3, d21, d31, q21, q31, qdiff = sp.symbols(
            "x1 x2 x3 d21 d31 q21 q31 qdiff"
        )
        generators = (
            d21 - (x2 - x1),
            d31 - (x3 - x1),
            d21 * q21 - 1,
            d31 * q31 - 1,
            (d31 - d21) * qdiff - 1,
            x1 * x2,
            x1 * x3,
            x2 * x3,
        )
        variables = (qdiff, q31, q21, d31, d21, x3, x2, x1)
        ideal = sp.groebner(generators, *variables, order="lex", domain=sp.QQ)
        basis = tuple(str(poly.as_expr()) for poly in ideal.polys)
        inconsistent = any(poly.as_expr() == 1 for poly in ideal.polys)
        payload = {
            "obligation_id": "TWO-INDEPENDENT-MASS-GAPS-REQUIRE-AT-LEAST-TWO-MASSIVE-STATES",
            "status": "PROVED_COUNTERHYPOTHESIS_UNIT_IDEAL" if inconsistent else "BLOCKED_COUNTERHYPOTHESIS_NOT_EXCLUDED",
            "counterhypothesis": "AT_MOST_ONE_OF_X1_X2_X3_IS_NONZERO",
            "assumptions": (
                "D21_EQUALS_X2_MINUS_X1",
                "D31_EQUALS_X3_MINUS_X1",
                "D21_NONZERO",
                "D31_NONZERO",
                "D31_MINUS_D21_NONZERO",
            ),
            "ideal_generators": tuple(str(g) for g in generators),
            "groebner_basis": basis,
            "unit_ideal": inconsistent,
            "interpretation": "TWO_INDEPENDENT_NONZERO_UNEQUAL_SPLITTINGS_EXCLUDE_ZERO_OR_ONE_MASSIVE_EIGENSTATE",
        }
        _MINIMUM_MASS_CACHE = {**payload, "digest": _digest(payload)}
        return _MINIMUM_MASS_CACHE

    @staticmethod
    def _basis_library(points: Sequence[int]) -> Mapping[str, tuple[sp.Rational, ...]]:
        x = tuple(sp.Rational(v) for v in points)
        return {
            "STANDARD_LINEAR": x,
            "STERILE_QUADRATIC": tuple(v**2 for v in x),
            "LED_CUBIC": tuple(v**3 for v in x),
            "DECOHERENCE_CONSTANT": tuple(sp.Integer(1) for _ in x),
            "DEGENERATE_STANDARD_COPY": x,
        }

    def verify_linearized_component(
        self,
        *,
        component_id: str,
        observations: Sequence[sp.Rational],
        basis_vectors: Sequence[Sequence[sp.Rational]],
        parameter_names: Sequence[str],
    ) -> AlgebraicComponent:
        if len(basis_vectors) != len(parameter_names):
            raise ValueError("one parameter name is required per basis vector")
        if not observations:
            raise ValueError("at least one observation is required")
        if any(len(vector) != len(observations) for vector in basis_vectors):
            raise ValueError("basis vectors and observations must have the same length")
        symbols = sp.symbols(" ".join(parameter_names))
        if isinstance(symbols, sp.Symbol):
            symbols = (symbols,)
        equations = []
        for row, observed in enumerate(observations):
            prediction = sum(symbols[col] * basis_vectors[col][row] for col in range(len(symbols)))
            equations.append(sp.expand(prediction - observed))
        ideal = sp.groebner(equations, *symbols, order="lex", domain=sp.QQ)
        basis = tuple(str(poly.as_expr()) for poly in ideal.polys)
        if any(poly.as_expr() == 1 for poly in ideal.polys):
            return AlgebraicComponent(
                component_id=component_id,
                status="REJECTED_INCONSISTENT_IDEAL",
                variables=tuple(str(s) for s in symbols),
                generators=tuple(str(e) for e in equations),
                groebner_basis=basis,
                solution_count=0,
                diagnostics={"fail_closed": True, "promotion_allowed": False},
            )
        solution_set = sp.linsolve(equations, symbols)
        solutions = list(solution_set)
        if not solutions:
            return AlgebraicComponent(
                component_id=component_id,
                status="REJECTED_NO_SYMBOLIC_SOLUTION",
                variables=tuple(str(s) for s in symbols),
                generators=tuple(str(e) for e in equations),
                groebner_basis=basis,
                solution_count=0,
                diagnostics={"fail_closed": True, "promotion_allowed": False},
            )
        solution = tuple(solutions[0])
        free = sorted({str(atom) for expr in solution for atom in expr.free_symbols if atom not in set(symbols)})
        unresolved_model_symbols = sorted(
            {str(symbols[idx]) for idx, expr in enumerate(solution) if symbols[idx] in expr.free_symbols}
        )
        if free or unresolved_model_symbols:
            return AlgebraicComponent(
                component_id=component_id,
                status="DIAGNOSTIC_NON_IDENTIFIABLE_COMPONENT",
                variables=tuple(str(s) for s in symbols),
                generators=tuple(str(e) for e in equations),
                groebner_basis=basis,
                solution_count=None,
                diagnostics={
                    "fail_closed": True,
                    "promotion_allowed": False,
                    "free_parameters": tuple(free),
                    "unresolved_model_symbols": tuple(unresolved_model_symbols),
                    "solution_family": tuple(str(expr) for expr in solution),
                },
            )
        exact = {str(symbols[index]): str(sp.simplify(value)) for index, value in enumerate(solution)}
        return AlgebraicComponent(
            component_id=component_id,
            status="CONFIRMED_EXACT_COMPONENT",
            variables=tuple(str(s) for s in symbols),
            generators=tuple(str(e) for e in equations),
            groebner_basis=basis,
            solution_count=1,
            exact_solution=exact,
            diagnostics={"fail_closed": True, "promotion_allowed": True, "zero_dimensional": True},
        )

    def complex_symmetric_majorana_block_certificate(self) -> Mapping[str, Any]:
        """Prove symmetry of the unified Dirac/Majorana block exactly."""
        global _TAKAGI_BLOCK_CACHE
        if _TAKAGI_BLOCK_CACHE is not None:
            return _TAKAGI_BLOCK_CACHE
        ml11, ml12, ml22, mr11, mr12, mr22, d11, d12, d21, d22 = sp.symbols(
            "ml11 ml12 ml22 mr11 mr12 mr22 d11 d12 d21 d22"
        )
        ml = sp.Matrix([[ml11, ml12], [ml12, ml22]])
        mr = sp.Matrix([[mr11, mr12], [mr12, mr22]])
        md = sp.Matrix([[d11, d12], [d21, d22]])
        matrix = ml.row_join(md).col_join(md.T.row_join(mr))
        residuals = tuple(str(sp.expand(value)) for value in matrix - matrix.T)
        passed = all(value == "0" for value in residuals)
        payload = {
            "obligation_id": "UNIFIED-DIRAC-MAJORANA-BLOCK-COMPLEX-SYMMETRY",
            "status": "PROVED_EXACT_COMPLEX_SYMMETRY" if passed else "BLOCKED_NONZERO_REMAINDER",
            "matrix": str(matrix),
            "transpose_residuals": residuals,
            "all_remainders_zero": passed,
            "interpretation": "M_L_AND_M_R_SYMMETRIC_WITH_OFF_DIAGONAL_M_D_AND_M_D_TRANSPOSE",
        }
        _TAKAGI_BLOCK_CACHE = {**payload, "digest": _digest(payload)}
        return _TAKAGI_BLOCK_CACHE

    def dirac_limit_lnv_cancellation_certificate(self) -> Mapping[str, Any]:
        """Prove m_beta_beta cancellation for one exact Dirac pair.

        The two equal Takagi masses have electron-row coefficients 1/sqrt(2)
        and i/sqrt(2). Their lepton-number-violating coherent sum cancels,
        whereas the beta-endpoint incoherent sum remains m^2.
        """
        global _DIRAC_LNV_CACHE
        if _DIRAC_LNV_CACHE is not None:
            return _DIRAC_LNV_CACHE
        m = sp.symbols("m", nonnegative=True, real=True)
        u1 = sp.sqrt(2) / 2
        u2 = sp.I * sp.sqrt(2) / 2
        lnv = sp.simplify(u1**2 * m + u2**2 * m)
        beta_sq = sp.simplify(sp.conjugate(u1) * u1 * m**2 + sp.conjugate(u2) * u2 * m**2)
        payload = {
            "obligation_id": "PURE-DIRAC-PAIR-LNV-CANCELLATION",
            "status": "PROVED_EXACT_DIRAC_LNV_CANCELLATION" if lnv == 0 and beta_sq == m**2 else "BLOCKED_NONZERO_REMAINDER",
            "takagi_pair_coefficients": (str(u1), str(u2)),
            "majorana_effective_mass_amplitude": str(lnv),
            "beta_effective_mass_squared": str(beta_sq),
            "interpretation": "DEGENERATE_MAJORANA_COMPONENTS_FORM_ONE_DIRAC_FERMION_AND_CANCEL_ONLY_IN_LNV_OBSERVABLES",
        }
        _DIRAC_LNV_CACHE = {**payload, "digest": _digest(payload)}
        return _DIRAC_LNV_CACHE

    def seesaw_schur_complement_certificate(self) -> Mapping[str, Any]:
        """Prove the exact Schur-complement identity behind the seesaw limit."""
        global _SEESAW_CACHE
        if _SEESAW_CACHE is not None:
            return _SEESAW_CACHE
        ml, md, mr, lam = sp.symbols("mL mD mR lambda")
        matrix = sp.Matrix([[ml, md], [md, mr]])
        characteristic = sp.expand((matrix - lam * sp.eye(2)).det())
        schur_numerator = sp.expand((mr - lam) * (ml - lam) - md**2)
        residual = sp.expand(characteristic - schur_numerator)
        low_energy_effective = sp.simplify(ml - md**2 / mr)
        payload = {
            "obligation_id": "MAJORANA-SEESAW-SCHUR-COMPLEMENT",
            "status": "PROVED_EXACT_SCHUR_COMPLEMENT_IDENTITY" if residual == 0 else "BLOCKED_NONZERO_REMAINDER",
            "complex_symmetric_mass_matrix": str(matrix),
            "characteristic_polynomial": str(characteristic),
            "schur_complement_numerator": str(schur_numerator),
            "identity_residual": str(residual),
            "controlled_large_mR_leading_effective_mass": str(low_energy_effective),
            "exact_effective_denominator": "mR-lambda",
            "interpretation": "M_L_MINUS_M_D_SQUARED_OVER_M_R_IS_A_CONTROLLED_LARGE_M_R_LOW_ENERGY_LIMIT_NOT_AN_EXACT_FINITE_M_R_EIGENVALUE",
        }
        _SEESAW_CACHE = {**payload, "digest": _digest(payload)}
        return _SEESAW_CACHE

    def exact_injection_qualification(self) -> Mapping[str, Any]:
        points = (1, 2, 3, 4, 5)
        library = self._basis_library(points)
        standard_truth = tuple(sp.Rational(2, 5) * value for value in library["STANDARD_LINEAR"])
        extra_truth = tuple(
            sp.Rational(2, 5) * library["STANDARD_LINEAR"][index]
            + sp.Rational(1, 7) * library["STERILE_QUADRATIC"][index]
            for index in range(len(points))
        )
        components = (
            self.verify_linearized_component(
                component_id="EXACT-STANDARD-AS-STANDARD",
                observations=standard_truth,
                basis_vectors=(library["STANDARD_LINEAR"],),
                parameter_names=("a",),
            ),
            self.verify_linearized_component(
                component_id="EXACT-EXTRA-AS-STANDARD",
                observations=extra_truth,
                basis_vectors=(library["STANDARD_LINEAR"],),
                parameter_names=("a",),
            ),
            self.verify_linearized_component(
                component_id="EXACT-EXTRA-AS-STANDARD-PLUS-STERILE",
                observations=extra_truth,
                basis_vectors=(library["STANDARD_LINEAR"], library["STERILE_QUADRATIC"]),
                parameter_names=("a", "b"),
            ),
            self.verify_linearized_component(
                component_id="EXACT-DEGENERATE-COPY",
                observations=standard_truth,
                basis_vectors=(library["STANDARD_LINEAR"], library["DEGENERATE_STANDARD_COPY"]),
                parameter_names=("a", "b"),
            ),
        )
        expected = {
            "EXACT-STANDARD-AS-STANDARD": "CONFIRMED_EXACT_COMPONENT",
            "EXACT-EXTRA-AS-STANDARD": "REJECTED_INCONSISTENT_IDEAL",
            "EXACT-EXTRA-AS-STANDARD-PLUS-STERILE": "CONFIRMED_EXACT_COMPONENT",
            "EXACT-DEGENERATE-COPY": "DIAGNOSTIC_NON_IDENTIFIABLE_COMPONENT",
        }
        status_match = all(component.status == expected[component.component_id] for component in components)
        payload = {
            "status": "PASS_EXACT_ALGEBRAIC_INJECTIONS" if status_match else "FAIL_EXACT_ALGEBRAIC_INJECTIONS",
            "points": points,
            "components": tuple(component.to_dict() for component in components),
            "expected_statuses": expected,
            "all_expected_statuses_observed": status_match,
        }
        return {**payload, "digest": _digest(payload)}

    def search_injection_qualification(self) -> Mapping[str, Any]:
        points = (1, 2, 3, 4, 5, 6)
        library = self._basis_library(points)
        # The selector receives only exact observations and the registered basis
        # library.  The hidden family is disclosed only after selection.
        observations = tuple(
            sp.Rational(1, 3) * library["STANDARD_LINEAR"][index]
            + sp.Rational(1, 11) * library["LED_CUBIC"][index]
            for index in range(len(points))
        )
        candidate_basis_ids = tuple(key for key in library if key != "DEGENERATE_STANDARD_COPY")
        candidates: list[AlgebraicComponent] = []
        for order in (1, 2):
            for basis_ids in itertools.combinations(candidate_basis_ids, order):
                parameters = tuple(f"p{index}" for index in range(order))
                candidates.append(
                    self.verify_linearized_component(
                        component_id="SEARCH-" + "+".join(basis_ids),
                        observations=observations,
                        basis_vectors=tuple(library[basis_id] for basis_id in basis_ids),
                        parameter_names=parameters,
                    )
                )
        eligible = [component for component in candidates if component.status == "CONFIRMED_EXACT_COMPONENT"]
        selected = min(eligible, key=lambda component: (len(component.variables), component.component_id)) if eligible else None
        hidden_truth = ("STANDARD_LINEAR", "LED_CUBIC")
        selected_basis = tuple(selected.component_id.removeprefix("SEARCH-").split("+")) if selected else ()
        payload = {
            "status": "PASS_SEARCH_INJECTION" if selected_basis == hidden_truth else "FAIL_SEARCH_INJECTION",
            "truth_accessed_during_search": False,
            "candidate_count": len(candidates),
            "confirmed_component_count": len(eligible),
            "diagnostic_component_count": sum(c.status.startswith("DIAGNOSTIC_") for c in candidates),
            "rejected_component_count": sum(c.status.startswith("REJECTED_") for c in candidates),
            "selected_component_id": selected.component_id if selected else None,
            "selected_basis_ids": selected_basis,
            "hidden_truth_after_unblinding": hidden_truth,
            "selected_matches_truth": selected_basis == hidden_truth,
            "components": tuple(component.to_dict() for component in candidates),
        }
        return {**payload, "digest": _digest(payload)}

    def run_qualification(self) -> Mapping[str, Any]:
        global _QUALIFICATION_CACHE
        if _QUALIFICATION_CACHE is not None:
            return _QUALIFICATION_CACHE
        unitarity = self.pmns_unitarity_certificate()
        majorana = self.majorana_phase_cancellation_certificate()
        mass_shift = self.mass_squared_shift_invariance_certificate()
        minimum_mass = self.minimum_two_massive_states_certificate()
        takagi_block = self.complex_symmetric_majorana_block_certificate()
        dirac_lnv = self.dirac_limit_lnv_cancellation_certificate()
        seesaw = self.seesaw_schur_complement_certificate()
        exact = self.exact_injection_qualification()
        search = self.search_injection_qualification()
        checks = {
            "pmns_unitarity_exact": unitarity["all_remainders_zero"] is True,
            "majorana_phase_cancellation_exact": majorana["status"] == "PROVED_EXACT_MODULO_UNIT_PHASE_IDEAL",
            "common_mass_squared_shift_invariance_exact": mass_shift["status"] == "PROVED_EXACT_MODULO_UNIT_PHASE_IDEAL",
            "at_least_two_massive_states_from_independent_gaps": minimum_mass["status"] == "PROVED_COUNTERHYPOTHESIS_UNIT_IDEAL",
            "unified_majorana_block_is_complex_symmetric": takagi_block["status"] == "PROVED_EXACT_COMPLEX_SYMMETRY",
            "pure_dirac_limit_cancels_lnv_exactly": dirac_lnv["status"] == "PROVED_EXACT_DIRAC_LNV_CANCELLATION",
            "seesaw_schur_complement_exact": seesaw["status"] == "PROVED_EXACT_SCHUR_COMPLEMENT_IDENTITY",
            "exact_injections_pass": exact["status"] == "PASS_EXACT_ALGEBRAIC_INJECTIONS",
            "search_injection_pass": search["status"] == "PASS_SEARCH_INJECTION",
            "search_truth_isolated": search["truth_accessed_during_search"] is False,
            "non_identifiable_component_not_promoted": any(
                component["status"] == "DIAGNOSTIC_NON_IDENTIFIABLE_COMPONENT"
                and component["diagnostics"].get("promotion_allowed") is False
                for component in exact["components"]
            ),
        }
        report: dict[str, Any] = {
            "schema": QUALIFICATION_SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_FAIL_CLOSED_ALGEBRAIC_EXPERIMENT" if all(checks.values()) else "BLOCKED_ALGEBRAIC_EXPERIMENT",
            "checks": checks,
            "pmns_unitarity": unitarity,
            "majorana_phase_cancellation": majorana,
            "mass_squared_shift_invariance": mass_shift,
            "minimum_two_massive_states": minimum_mass,
            "complex_symmetric_majorana_block": takagi_block,
            "dirac_limit_lnv_cancellation": dirac_lnv,
            "seesaw_schur_complement": seesaw,
            "exact_injections": exact,
            "search_injection": search,
            "claim_boundary": {
                "algebraic_admissibility_proved_for_declared_constraints": True,
                "absolute_mass_scale_from_oscillations": "PROVED_STRUCTURALLY_NON_IDENTIFIABLE",
                "minimum_massive_eigenstate_count_from_two_independent_gaps": 2,
                "real_data_used": False,
                "new_neutrino_state_discovered": False,
                "complex_symmetric_majorana_block": "PROVED_EXACT",
                "pure_dirac_lnv_cancellation": "PROVED_EXACT",
                "seesaw_schur_complement": "PROVED_EXACT_WITH_CONTROLLED_LIMIT_BOUNDARY",
                "extra_dimension_proved": False,
                "symbolic_confirmation_replaces_experiment": False,
                "unconfirmed_components": "DIAGNOSTIC_ONLY",
            },
            "sha256": "",
        }
        report["sha256"] = _digest({**report, "sha256": ""})
        _QUALIFICATION_CACHE = report
        return _QUALIFICATION_CACHE

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "responsibilities": (
                "CONSTRUCT_POLYNOMIAL_IDEALS",
                "RUN_EXACT_INJECTIONS",
                "RUN_LIBRARY_SEARCH_INJECTIONS",
                "SYMBOLICALLY_VERIFY_COMPONENTS",
                "PROVE_COMMON_MASS_SQUARED_SHIFT_INVARIANCE",
                "PROVE_MINIMUM_TWO_MASSIVE_STATES_FROM_INDEPENDENT_GAPS",
                "PROVE_COMPLEX_SYMMETRY_OF_UNIFIED_MAJORANA_BLOCK",
                "PROVE_PURE_DIRAC_LNV_CANCELLATION",
                "PROVE_SEESAW_SCHUR_COMPLEMENT_IDENTITY",
                "KEEP_NON_IDENTIFIABLE_COMPONENTS_DIAGNOSTIC",
                "FAIL_CLOSED_BEFORE_STATISTICAL_PROMOTION",
            ),
            "non_responsibilities": (
                "NO_EXPERIMENT_SPECTRUM_LIKELIHOOD",
                "NO_NUMERICAL_FIT_AS_PROOF",
                "NO_PHYSICAL_DISCOVERY_CLAIM",
            ),
            "downstream_owner": "NEUTRINO-REAL-DATA-LIKELIHOOD",
        }
        return {**payload, "digest": _digest(payload)}
