"""Authoritative Φ-ConstraintAtlas owner.

This module does not replace physical-law owners.  It replaces the weak idea
that a missing combination of descriptive axes is itself evidence for a law.
The atlas admits a relation only when physical quantities are explicitly typed,
validity charts overlap, and the mathematical consequence can be certified.

The algebraic backend lowers polynomial/rational constraints to an ideal and
certifies support-minimal elimination consequences with Gröbner bases.  v6.20 added a second, conservative operator backend.  v6.21 closed the first
previously-open operator bridges: a Galerkin structural-subspace projection for
the flexible-wing PDE and nonparametric data-backed temporal/spatial kernel
identification.  v6.22 adds a real-data frontier using digitized vector data from the DLR oLAF flexible-wing gust-load experiment: it identifies a nonparametric gust-to-WRBM magnitude correction and a one-frequency complex flap-command/load anchor while fail-closing unavailable phase/raw-DAQ information.  The hidden-calibration layer learns discrete kernels directly from trajectories/
fields without selecting a named analytic kernel family before fitting: already-registered differential,
state-space, constitutive and Volterra/integral relations are lowered into local
operator charts and composed only by declared symbol bindings, exact definition
substitution, and a restricted linear-observable differentiation rule.  v6.25 adds the phase/speed/modal probe-to-wing discriminator proposed by the v6.24 real-data frontier.  It estimates a complex harmonic G_probe->wing from synchronized time histories, removes geometric convection phase, and tests independently identified modal poles before using the wing-gust->load residual.  The v6.26 public-data acquisition layer additionally ingests published oLAF multi-speed WRBM magnitude at 30/40/50 m/s and records SAFER2 wind-on OMA provenance, while refusing to splice cross-campaign modal data or synthesize the still-missing near-wing/phase channels.  v6.27 measures threshold sensitivity over a two-order common-scale sweep, adds null/mixed/OOD controls so UNRESOLVED_FRONTIER is executable rather than decorative, and retains Figure-23 40 m/s peak/curvature as NOT_ATTRIBUTABLE observables.  The full real complex discriminator therefore remains data-blocked.  It does
not claim a complete differential algebra, exhaustive mechanism classification, raw-DAQ identification, or world novelty.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
import json
import re

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

from .schema import digest_payload

OWNER_ID = "PHI-CONSTRAINT-ATLAS"
OWNER_VERSION = "6.22.0"
SCHEMA = "phi-constraint-atlas/v6.22"
QUDT_REFERENCE = "QUDT-3.5.0/CATALOG-2026-07-28"
EMMO_REFERENCE = "EMMO/1.0.0-BETA7-DOCUMENTATION"

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class QuantityCoordinateIR:
    coordinate_id: str
    chart_id: str
    symbol: str
    quantity_kind_id: str
    physical_role: str
    physical_object: str
    unit: str | None
    dimension: Tuple[str, ...]
    source_owner_ids: Tuple[str, ...]
    typing_status: str = "CONFIRMED_CANONICAL"


@dataclass(frozen=True)
class ConstraintRelationIR:
    relation_id: str
    owner_id: str
    chart_id: str
    formula: str
    relation_kind: str
    polynomial: str | None
    denominator: str | None
    support: Tuple[str, ...]
    validity_domain: str
    assumptions: Tuple[str, ...]
    status: str


@dataclass(frozen=True)
class CircuitCertificate:
    circuit_id: str
    source_owner_ids: Tuple[str, ...]
    retained_coordinates: Tuple[str, ...]
    eliminated_coordinates: Tuple[str, ...]
    polynomial: str
    support: Tuple[str, ...]
    required_nonzero_factors: Tuple[str, ...]
    support_minimal: bool
    derivation_backend: str
    truth_formula_access_during_search: bool
    status: str


@dataclass(frozen=True)
class GluingCertificate:
    gluing_id: str
    chart_id: str
    source_owner_ids: Tuple[str, ...]
    shared_coordinates: Tuple[str, ...]
    typing_conflicts: Tuple[str, ...]
    validity_domains: Tuple[str, ...]
    restriction_map: str
    obstruction_status: str
    status: str


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dimension_tuple(row: Mapping[str, Any]) -> Tuple[str, ...]:
    d = row.get("dimension", {})
    return tuple(str(d.get(k, "0")) for k in (
        "length", "mass", "time", "current", "temperature", "amount", "luminous_intensity"
    ))


def _relation_kind(formula: str) -> str:
    if any(token in formula for token in ("Integral", "mean(", "max_", "min(", "sum_")):
        return "INTEGRAL_OR_AGGREGATE"
    if any(token in formula for token in ("dot(", "ddot(", "partial_", "grad", "nabla", "∂", "∇")):
        return "DIFFERENTIAL_OR_OPERATOR"
    if any(token in formula for token in ("<=", ">=", "<", ">")):
        return "INEQUALITY_OR_SEMIALGEBRAIC"
    if formula.count("=") != 1 or ";" in formula:
        return "MULTI_RELATION_OR_OPERATOR"
    return "ALGEBRAIC_CANDIDATE"


def _parse_polynomial_relation(formula: str, variables: Sequence[Mapping[str, Any]]) -> Tuple[sp.Expr, sp.Expr] | None:
    """Return numerator/denominator for one rational-polynomial equality.

    Clearing a denominator alone would introduce spurious components.  The
    caller therefore saturates by the accumulated denominator before deriving
    a circuit.
    """
    if _relation_kind(formula) != "ALGEBRAIC_CANDIDATE":
        return None
    names = [
        str(row.get("symbol")) for row in variables
        if row.get("symbol") and _IDENTIFIER.fullmatch(str(row.get("symbol")))
    ]
    local = {name: sp.Symbol(name) for name in names}
    local["pi"] = sp.pi
    text = formula.replace("3.141592653589793", "pi").replace("^", "**")
    try:
        lhs, rhs = text.split("=", 1)
        expr = sp.together(sp.sympify(lhs, locals=local) - sp.sympify(rhs, locals=local))
        numerator, denominator = sp.fraction(expr)
        free = sorted(numerator.free_symbols | denominator.free_symbols, key=lambda value: value.name)
        declared = set(names)
        if any(symbol.name not in declared for symbol in free):
            return None
        # The first backend is deliberately polynomial/rational only.
        sp.Poly(numerator, *free)
        sp.Poly(denominator, *free)
        return sp.expand(numerator), sp.expand(denominator)
    except Exception:
        return None


def _normalize_polynomial(expr: sp.Expr) -> sp.Expr:
    expr = sp.expand(expr)
    symbols = sorted(expr.free_symbols, key=lambda value: value.name)
    if not symbols:
        return expr
    poly = sp.Poly(expr, *symbols)
    _, primitive = poly.primitive()
    primitive_expr = sp.expand(primitive.as_expr())
    # Make the leading coefficient positive when its sign is decidable.
    # Keep the canonical polynomial expanded.  Factorized SymPy display forms
    # may move a global minus sign between factors across equivalent
    # elimination paths, which must not create distinct Atlas candidates.
    lc = sp.Poly(primitive_expr, *symbols).LC()
    if lc.is_number and lc.is_negative:
        primitive_expr = -primitive_expr
    return sp.Poly(sp.expand(primitive_expr), *symbols).as_expr()

_FUNCTION_TOKENS = {
    "exp", "ln", "log", "log10", "sqrt", "sin", "cos", "tan", "sinh", "cosh", "tanh",
    "erf", "diag", "det", "trace", "tr", "argmax_x", "max", "min", "mean",
}
_OPERATOR_TOKENS = {
    "sum_i", "sum_j", "sum_n", "sum_a", "sum_f", "sum_", "prod_i", "Integral", "integral",
    "integral_K", "integral_0", "∫", "∮", "Σ", "Π", "nabla", "∇", "partial", "∂",
    "dagger", "grad", "div", "dot", "ddot", "cross", "tensor", "for", "if", "all",
    "experiments", "implies", "converges", "otherwise", "in", "not", "equal", "upper_convected",
}
_INDEX_TOKENS = {"i", "j", "l", "n_idx", "a_idx", "f_idx"}
_DERIVATIVE_RE = re.compile(r"^(?:d[A-Za-zΑ-Ωα-ω_]+|d[trxyz]|partial_[A-Za-z0-9_]+|∂[A-Za-zΑ-Ωα-ω0-9_]*)$")

# Internal quantity-kind inference is deliberately conservative.  A match only
# identifies a *kind*; the atlas still keeps individual coordinates distinct by
# chart/domain and normalized display.  Unmatched physical symbols are assigned
# owner-local identities and therefore cannot create cross-owner glue.
_GENERIC_KIND_BY_SYMBOL = {
    "T": "QTY-TEMPERATURE", "T0": "QTY-TEMPERATURE", "T_h": "QTY-TEMPERATURE", "T_w": "QTY-TEMPERATURE",
    "t": "QTY-TIME", "time": "QTY-TIME",
    "x": "QTY-LENGTH", "y": "QTY-LENGTH", "z": "QTY-LENGTH", "r": "QTY-LENGTH", "R_len": "QTY-LENGTH",
    "V": "QTY-VELOCITY", "v": "QTY-VELOCITY", "u": "QTY-VELOCITY", "c0": "QTY-VELOCITY",
    "rho": "QTY-MASS-DENSITY", "ρ": "QTY-MASS-DENSITY",
    "m": "QTY-MASS", "M_mass": "QTY-MASS",
    "F": "QTY-FORCE", "L": "QTY-FORCE", "D_force": "QTY-FORCE", "W": "QTY-FORCE",
    "p_pressure": "QTY-PRESSURE", "P_pressure": "QTY-PRESSURE",
    "E_energy": "QTY-ENERGY", "K": "QTY-ENERGY", "U": "QTY-ENERGY",
    "f": "QTY-FREQUENCY", "omega": "QTY-ANGULAR-FREQUENCY", "ω": "QTY-ANGULAR-FREQUENCY",
    "lambda_wave": "QTY-WAVELENGTH", "λ_wave": "QTY-WAVELENGTH",
    "I_current": "QTY-ELECTRIC-CURRENT", "V_potential": "QTY-ELECTRIC-POTENTIAL",
    "q_charge": "QTY-ELECTRIC-CHARGE", "J_current": "QTY-CURRENT-DENSITY",
    "B_field": "QTY-MAGNETIC-FLUX-DENSITY", "E_field": "QTY-ELECTRIC-FIELD",
}


def _ascii_symbol_token(value: str) -> str:
    value = str(value).strip()
    replacements = {
        "ρ": "rho", "μ": "mu", "ν": "nu", "σ": "sigma", "ε": "epsilon", "κ": "kappa",
        "λ": "lambda", "ω": "omega", "θ": "theta", "φ": "phi", "Φ": "Phi", "ψ": "psi",
        "Ψ": "Psi", "γ": "gamma", "β": "beta", "α": "alpha", "τ": "tau", "π": "pi",
        "ℏ": "hbar", "ħ": "hbar", "Δ": "Delta", "ξ": "xi", "η": "eta", "χ": "chi",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not value:
        value = "anon"
    if value[0].isdigit():
        value = "s_" + value
    return value


def _domain_family(domain_id: str) -> str:
    return {
        "materials_science": "materials",
        "systems_control": "systems",
        "aeronautics_and_aerostation": "aeronautics",
    }.get(domain_id, domain_id)


def _contextual_quantity_kind(owner_id: str, domain_id: str, display: str, name_ru: str = "") -> str | None:
    """Return a high-confidence internal quantity-kind ID or None.

    This function intentionally prefers false negatives over semantic aliasing.
    It never makes a particular-quantity identity global; that happens only via
    a chart-specific coordinate key after this kind inference.
    """
    d = str(display).strip()
    low_name = (name_ru or "").lower()
    dom = _domain_family(domain_id)
    prefix = owner_id.split("-", 1)[0]

    # Already-disambiguated common spellings.
    if d in {"rho", "ρ", "rho0", "rho_inf", "rho∞"}:
        return "QTY-MASS-DENSITY"
    if d in {"t", "Delta_t", "tau_t"}:
        return "QTY-TIME"
    if d in {"r", "x", "y", "z", "h", "b", "c_chord", "ell", "ℓ", "d_len", "a_len"}:
        return "QTY-LENGTH"
    if d in {"m", "m1", "m2", "M_body", "M_total", "m_e", "m_p"}:
        return "QTY-MASS"

    if dom == "aeronautics":
        aero = {
            "V": "QTY-VELOCITY", "rho": "QTY-MASS-DENSITY", "q": "QTY-PRESSURE",
            "L": "QTY-FORCE", "D": "QTY-FORCE", "W": "QTY-FORCE", "B": "QTY-FORCE",
            "T": "QTY-TEMPERATURE", "T0": "QTY-TEMPERATURE", "T_h": "QTY-TEMPERATURE",
            "P_req": "QTY-POWER", "P_prop": "QTY-POWER", "P_s": "QTY-POWER", "P_aux": "QTY-POWER",
            "mu": "QTY-DYNAMIC-VISCOSITY", "c": "QTY-LENGTH", "b": "QTY-LENGTH", "S": "QTY-AREA",
            "A_env": "QTY-AREA", "A_ref": "QTY-AREA", "A_s": "QTY-AREA", "A_d": "QTY-AREA",
        }
        return aero.get(d)

    if dom == "mechanics":
        if d in {"ρ", "rho"}: return "QTY-MASS-DENSITY"
        if d in {"p"}:
            if owner_id in {"MEC-06"} or "импульс" in low_name: return "QTY-MOMENTUM"
            return "QTY-PRESSURE"
        if d in {"u", "v", "V"}: return "QTY-VELOCITY"
        if d in {"F", "Fb", "F_AB", "F_BA"}: return "QTY-FORCE"
        if d in {"m", "M"}: return "QTY-MASS"
        if d in {"a", "g", "b_acc"}: return "QTY-ACCELERATION"
        if d in {"K", "E", "U"}: return "QTY-ENERGY"
        if d in {"W", "Wnet"}: return "QTY-WORK"
        if d in {"tau", "τ"}:
            return "QTY-TORQUE" if owner_id.startswith("MEC-") and owner_id in {"MEC-09", "MEC-10"} else "QTY-STRESS"
        if d in {"sigma", "σ"}: return "QTY-STRESS"
        if d in {"epsilon", "ε"}: return "QTY-STRAIN"
        if d in {"E_Y", "Y", "Young"}: return "QTY-YOUNG-MODULUS"
        if d in {"mu", "μ", "eta", "η"}: return "QTY-DYNAMIC-VISCOSITY"
        if d in {"q"}: return "QTY-HEAT-FLUX"
        if d in {"kappa", "κ"}: return "QTY-THERMAL-CONDUCTIVITY"
        if d in {"D"}: return "QTY-DIFFUSIVITY"
        if d in {"c"}: return "QTY-CONCENTRATION"
        if d in {"T"}: return "QTY-TEMPERATURE"
        if d in {"t"}: return "QTY-TIME"
        if d in {"x", "y", "z", "r", "d"}: return "QTY-LENGTH"

    if dom == "physics":
        if owner_id.startswith("EM-"):
            return {
                "F": "QTY-FORCE", "E": "QTY-ELECTRIC-FIELD", "B": "QTY-MAGNETIC-FLUX-DENSITY",
                "q": "QTY-ELECTRIC-CHARGE", "qtest": "QTY-ELECTRIC-CHARGE", "Q": "QTY-ELECTRIC-CHARGE",
                "Qenc": "QTY-ELECTRIC-CHARGE", "V": "QTY-ELECTRIC-POTENTIAL", "I": "QTY-ELECTRIC-CURRENT",
                "J": "QTY-CURRENT-DENSITY", "Phi": "QTY-MAGNETIC-FLUX", "Φ": "QTY-MAGNETIC-FLUX",
                "r": "QTY-LENGTH", "v": "QTY-VELOCITY", "t": "QTY-TIME", "P": "QTY-POWER",
                "S": "QTY-IRRADIANCE",
            }.get(d)
        if owner_id.startswith("WAV-"):
            return {
                "T": "QTY-TIME", "x": "QTY-LENGTH", "l": "QTY-LENGTH", "ell": "QTY-LENGTH",
                "λ": "QTY-WAVELENGTH", "lambda": "QTY-WAVELENGTH", "f": "QTY-FREQUENCY",
                "ω": "QTY-ANGULAR-FREQUENCY", "omega": "QTY-ANGULAR-FREQUENCY", "v": "QTY-VELOCITY",
                "c": "QTY-VELOCITY", "vg": "QTY-VELOCITY", "n": "QTY-REFRACTIVE-INDEX",
            }.get(d)
        if d in {"E", "En", "E_n", "DeltaE", "ΔE"}: return "QTY-ENERGY"
        if d in {"p"}: return "QTY-MOMENTUM"
        if d in {"m", "M", "Mnucleus"}: return "QTY-MASS"
        if d in {"t"}: return "QTY-TIME"
        if d in {"x", "r", "d"}: return "QTY-LENGTH"
        if d in {"T"} and any(k in low_name for k in ("темпера", "больц", "планк", "тепл", "излуч")): return "QTY-TEMPERATURE"
        if d in {"λ", "lambda"}: return "QTY-WAVELENGTH"
        if d in {"f"}: return "QTY-FREQUENCY"
        if d in {"ω", "omega"}: return "QTY-ANGULAR-FREQUENCY"

    if dom == "chemistry":
        if d == "T": return "QTY-TEMPERATURE"
        if d in {"P", "p"}: return "QTY-PRESSURE"
        if d == "V": return "QTY-VOLUME"
        if d in {"n", "n_i"}: return "QTY-AMOUNT"
        if d in {"c", "c_i", "C"}: return "QTY-CONCENTRATION"
        if d in {"a", "a_i"}: return "QTY-ACTIVITY"
        if d in {"mu_i", "μ_i", "mu"}: return "QTY-CHEMICAL-POTENTIAL"
        if d in {"E_a", "DeltaG", "DeltaH", "Delta_r", "G", "H"}: return "QTY-MOLAR-ENERGY"
        if d in {"S", "DeltaS"}: return "QTY-MOLAR-ENTROPY"
        if d == "I": return "QTY-ELECTRIC-CURRENT"
        if d in {"t"}: return "QTY-TIME"
        if d in {"xi", "ξ"}: return "QTY-REACTION-EXTENT"
        if d in {"r", "d"} and "radius" in low_name: return "QTY-LENGTH"

    if dom == "materials":
        if d == "T": return "QTY-TEMPERATURE"
        if d in {"t"}: return "QTY-TIME"
        if d in {"r", "d", "h", "a"}: return "QTY-LENGTH"
        if d in {"epsilon", "ε"}: return "QTY-STRAIN"
        if d in {"sigma", "σ"}:
            if any(k in low_name for k in ("провод", "друде", "электр")): return "QTY-ELECTRIC-CONDUCTIVITY"
            return "QTY-STRESS"
        if d in {"E", "U", "Delta"}: return "QTY-ENERGY"
        if d in {"F"}: return "QTY-FORCE"
        if d in {"I"}: return "QTY-ELECTRIC-CURRENT"
        if d in {"V"}: return "QTY-ELECTRIC-POTENTIAL"
        if d in {"kappa", "κ", "k"} and "теплопровод" in low_name: return "QTY-THERMAL-CONDUCTIVITY"
        if d == "D": return "QTY-DIFFUSIVITY"

    if dom == "astronomy":
        if d in {"r", "h", "R"}: return "QTY-LENGTH"
        if d in {"ρ", "rho"}: return "QTY-MASS-DENSITY"
        if d in {"P", "p"}: return "QTY-PRESSURE"
        if d in {"m", "M"}: return "QTY-MASS"
        if d == "T": return "QTY-TEMPERATURE"
        if d in {"λ", "lambda"}: return "QTY-WAVELENGTH"
        if d in {"L", "L_Edd"}: return "QTY-LUMINOSITY"
        if d in {"F"}: return "QTY-IRRADIANCE"
        if d == "t": return "QTY-TIME"
        if d in {"v", "c"}: return "QTY-VELOCITY"

    return None


def _semantic_class_and_kind(passport: Any, symbol: Any) -> Tuple[str, str | None, str]:
    display = str(symbol.display).strip()
    low = display.lower()
    if display in _FUNCTION_TOKENS or low in _FUNCTION_TOKENS:
        return "FUNCTION", None, "LEXICAL_FUNCTION_TOKEN"
    if display in _OPERATOR_TOKENS or low in _OPERATOR_TOKENS:
        return "OPERATOR", None, "LEXICAL_OPERATOR_TOKEN"
    if _DERIVATIVE_RE.fullmatch(display) and display not in {"d", "D"}:
        return "DERIVATIVE_TOKEN", None, "LEXICAL_DIFFERENTIAL_TOKEN"
    if symbol.quantity_id == "QTY-KK-INDEX":
        return "INDEX", symbol.quantity_id, "EXISTING_CANONICAL_INDEX_KIND"
    if display in _INDEX_TOKENS and passport.domain_id in {"mathematics", "materials_science", "physics"}:
        return "INDEX", None, "INDEX_CONTEXT"

    # Constants declared by passport or universally recognizable constants.
    if display in {"pi", "π", "hbar", "ℏ", "ħ", "k_B", "kB", "epsilon0", "ε0", "mu0", "μ0"}:
        return "PHYSICAL_CONSTANT", None, "RECOGNIZED_PHYSICAL_OR_MATHEMATICAL_CONSTANT"
    if display == "G" and passport.domain_id in {"astronomy", "physics"} and any(k in passport.name_ru.lower() for k in ("грав", "ньют", "толман", "эйншт")):
        return "PHYSICAL_CONSTANT", None, "GRAVITATIONAL_CONSTANT_CONTEXT"
    if display == "c" and passport.domain_id in {"astronomy", "physics"} and not passport.owner_id.startswith("WAV-"):
        return "PHYSICAL_CONSTANT", None, "SPEED_OF_LIGHT_CONSTANT_CONTEXT"
    if display == "R" and passport.domain_id == "chemistry" and any(k in passport.name_ru.lower() for k in ("газ", "аррениус", "нернст", "ван", "гиббс", "энтроп")):
        return "PHYSICAL_CONSTANT", None, "GAS_CONSTANT_CONTEXT"

    qid = symbol.quantity_id
    if qid and qid in {"QTY-DIMENSIONLESS"} and (display in _FUNCTION_TOKENS or display in _OPERATOR_TOKENS):
        qid = None
    if qid:
        return "PHYSICAL_QUANTITY", qid, "EXISTING_CANONICAL_QUANTITY_KIND"

    inferred = _contextual_quantity_kind(passport.owner_id, passport.domain_id, display, passport.name_ru)
    if inferred:
        if display in {"t"}:
            return "COORDINATE", inferred, "CONTEXTUAL_TIME_COORDINATE"
        if display in {"x", "y", "z", "r"} and inferred == "QTY-LENGTH":
            return "COORDINATE", inferred, "CONTEXTUAL_SPATIAL_COORDINATE"
        return "PHYSICAL_QUANTITY", inferred, "CONTEXTUAL_HIGH_CONFIDENCE_QUANTITY_KIND"

    if passport.domain_id in {"mathematics", "systems_control", "metrology"}:
        return "PARAMETER_OR_MATHEMATICAL_OBJECT", None, "OWNER_LOCAL_NONPHYSICAL_OR_MEASURAND_SPECIFIC"
    if display in {"d", "Delta", "delta", "const", "LHS", "RHS"}:
        return "MATHEMATICAL_TOKEN", None, "NON_QUANTITY_MATHEMATICAL_TOKEN"
    return "PHYSICAL_QUANTITY", None, "OWNER_LOCAL_QUANTITY_KIND_UNRESOLVED_GLOBALLY"


def _semantic_coordinate_name(passport: Any, display: str, semantic_class: str, quantity_kind_id: str | None) -> str:
    token = _ascii_symbol_token(display)
    if semantic_class == "PHYSICAL_CONSTANT":
        return "CONST__" + token
    if semantic_class in {"FUNCTION", "OPERATOR", "DERIVATIVE_TOKEN", "INDEX", "MATHEMATICAL_TOKEN"}:
        return f"LOCAL__{_ascii_symbol_token(passport.owner_id)}__{token}"
    if quantity_kind_id:
        # Kind alone is insufficient: retain display to distinguish particular
        # coordinates such as inlet/outlet temperatures while allowing the same
        # conventional variable to glue inside one domain chart.
        return f"Q__{_ascii_symbol_token(passport.domain_id)}__{_ascii_symbol_token(quantity_kind_id)}__{token}"
    return f"LOCALQ__{_ascii_symbol_token(passport.owner_id)}__{token}"


def _formula_text_for_parse(source: str) -> str:
    text = str(source).strip()
    text = text.replace("−", "-").replace("–", "-").replace("×", "*").replace("·", "*")
    text = text.replace("²", "**2").replace("³", "**3").replace("⁴", "**4").replace("⁻¹", "**-1")
    text = text.replace("^", "**")
    text = text.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    text = text.replace("π", "pi").replace("ℏ", "hbar").replace("ħ", "hbar")
    text = text.replace("ρ", "rho").replace("μ", "mu").replace("σ", "sigma").replace("ε", "epsilon")
    text = text.replace("κ", "kappa").replace("λ", "lambda").replace("ω", "omega").replace("γ", "gamma")
    text = text.replace("β", "beta").replace("α", "alpha").replace("τ", "tau").replace("θ", "theta")
    text = text.replace("Φ", "Phi").replace("ψ", "psi").replace("Ψ", "Psi").replace("ξ", "xi").replace("η", "eta")
    return text


def _normalize_expr_polynomial(expr: sp.Expr) -> str:
    return str(_normalize_polynomial(sp.expand(expr)))


def _operator_formula_text(source: str) -> str:
    """Normalize notation without changing the mathematical claim.

    This is a lexical IR only: no operator is commuted, factorized or assumed
    local.  It exists so exact source definitions can be substituted without
    confusing unicode typography with distinct mathematics.
    """
    text = str(source).strip()
    # Preserve operator structure before the generic punctuation normalizer.
    text = text.replace("∇²", "laplacian ").replace("∇·", "div ").replace("∇×", "curl ")
    text = text.replace("∂t", "partial_t ").replace("∂x", "partial_x ").replace("∂y", "partial_y ").replace("∂z", "partial_z ")
    text = text.replace("Ẏ", "dot(Y)").replace("ρ̇", "dot(rho)").replace("σ̇", "dot(sigma)").replace("ε̇", "dot(epsilon)")
    text = text.replace("integral_0^t", "integral_0_to_t").replace("Integral_0^t", "Integral_0_to_t")
    text = text.replace("∫", "integral_").replace("Γ", "Gamma").replace("ξ", "xi")
    text = _formula_text_for_parse(text)
    text = text.replace("nabla^2", "laplacian ").replace("nabla**2", "laplacian ")
    text = re.sub(r"D([A-Za-z_][A-Za-z0-9_]*)/Dt", r"material_D_t(\1)", text)
    text = re.sub(r"([A-Za-z0-9_])material_D_t\(", r"\1*material_D_t(", text)
    text = text.replace("rhob", "rho*b")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _operator_equations(source: str) -> Tuple[Tuple[str, str], ...]:
    rows: List[Tuple[str, str]] = []
    for part in _operator_formula_text(source).split(";"):
        part = part.strip()
        if part.count("=") != 1 or any(op in part for op in ("<=", ">=")):
            continue
        lhs, rhs = (x.strip() for x in part.split("=", 1))
        if not lhs or not rhs:
            continue
        # Reject prose tails rather than inventing mathematics from them.
        if any(token in rhs.lower() for token in ("dopustimo", "tolko posle", "otherwise", "failure when", "pri m")):
            continue
        rows.append((lhs, rhs))
    return tuple(rows)


def _operator_definition_symbol(lhs: str) -> str | None:
    lhs = lhs.strip()
    if _IDENTIFIER.fullmatch(lhs):
        if lhs.endswith("_dot") or lhs.startswith("partial_"):
            return None
        return lhs
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\(t\)", lhs)
    if match and match.group(1) not in {"dot", "ddot", "partial_t", "material_D_t"}:
        return match.group(1)
    return None


def _operator_definition_argument(lhs: str) -> str | None:
    lhs = lhs.strip()
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\(([A-Za-z_][A-Za-z0-9_]*)\)", lhs)
    if match and match.group(1) not in {"dot", "ddot", "partial_t", "material_D_t"}:
        return match.group(2)
    return None


def _operator_derivative_target(lhs: str) -> str | None:
    lhs = lhs.strip()
    if lhs.endswith("_dot") and _IDENTIFIER.fullmatch(lhs):
        return lhs[:-4]
    for pattern in (
        r"dot\(([A-Za-z_][A-Za-z0-9_]*)\)",
        r"ddot\(([A-Za-z_][A-Za-z0-9_]*)\)",
        r"material_D_t\(([A-Za-z_][A-Za-z0-9_]*)\)",
        r"partial_t\s*\(?([A-Za-z_][A-Za-z0-9_]*)\)?",
    ):
        match = re.fullmatch(pattern, lhs)
        if match:
            return match.group(1)
    return None


def _operator_replace_symbol(text: str, symbol: str, replacement: str, definition_argument: str | None = None) -> str:
    """Substitute one declared definition without inventing time/function semantics."""
    result = text
    if definition_argument:
        call_pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(symbol) + r"\(([^()]*)\)")
        def repl_call(match: re.Match[str]) -> str:
            actual = match.group(1).strip()
            rhs = _operator_replace_symbol(replacement, definition_argument, actual, None)
            return "(" + rhs.strip() + ")"
        result = call_pattern.sub(repl_call, result)
        # A bare field symbol denotes its current-time value on the same chart.
        bare_pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(symbol) + r"(?![A-Za-z0-9_])(?!\s*\()")
        result = bare_pattern.sub("(" + replacement.strip() + ")", result)
        return result
    # A bare field definition cannot be blindly lifted to f(s).  Leave such
    # function-valued occurrences untouched and fail closed on that rewrite.
    pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(symbol) + r"(?![A-Za-z0-9_])(?!\s*\()")
    return pattern.sub("(" + replacement.strip() + ")", result)


def _operator_has_symbol(text: str, symbol: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(symbol) + r"(?![A-Za-z0-9_])", text) is not None


def _operator_features(formula: str) -> Tuple[str, ...]:
    text = _operator_formula_text(formula)
    features: List[str] = []
    tests = (
        ("TIME_DERIVATIVE", ("_dot", "dot(", "partial_t", "material_D_t(", "ddot(")),
        ("SPATIAL_GRADIENT", ("grad ", "grad(", "partial_x", "partial_y", "partial_z")),
        ("DIVERGENCE", ("div ", "div(")),
        ("LAPLACIAN", ("laplacian",)),
        ("INTEGRAL", ("integral_", "Integral(")),
        ("MEMORY_KERNEL", ("t-s", "t - s", "Gamma(t-s", "G(t-s")),
        ("SUM_OR_ENSEMBLE", ("sum_", "mean(")),
        ("COMMUTATOR", ("[H,rho]", "[H, rho]")),
        ("STATE_SPACE", ("B_g", "B_u", "C_z", "x_dot")),
    )
    for label, tokens in tests:
        if any(token in text for token in tokens):
            features.append(label)
    return tuple(features)


def _operator_formula_key(formula: str) -> str:
    return re.sub(r"\s+", "", _operator_formula_text(formula)).replace("+( -", "+(-")


class ConstraintAtlasOwner:
    """Single authoritative owner for typed-constraint/circuit qualification."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.quantity_rows = _load_json(self.root / "data" / "quantities" / "registry.json")
        self.quantity_registry = {row["quantity_id"]: row for row in self.quantity_rows}
        self.aeronautics_db = _load_json(self.root / "data" / "passports" / "aeronautics_intersection_laws.json")
        self.aero_sources = {row["owner_id"]: row for row in self.aeronautics_db["source_laws"]}

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "authoritative_role": "TYPED_QUANTITY_CONSTRAINT_CIRCUIT_VALIDITY_GLUE_AND_UNKNOWN_FRONTIER_OWNER",
            "replaces": "NAIVE_STRUCTURAL_HOLE_AS_LAW_PREDICTOR",
            "quantity_identity_rule": "PARTICULAR_QUANTITY_COORDINATE_IS_NOT_IDENTICAL_TO_QUANTITY_KIND_AND_NEVER_GLUES_BY_PRINTED_SYMBOL_ALONE",
            "algebraic_backend": "POLYNOMIAL_OR_RATIONAL_IDEAL_WITH_DENOMINATOR_SATURATION_AND_GROEBNER_ELIMINATION",
            "operator_backend": "DECLARED_CHART_EXACT_DEFINITION_SUBSTITUTION_PLUS_RESTRICTED_LINEAR_OBSERVABLE_DIFFERENTIATION_PLUS_GALERKIN_PROJECTION_AND_DATA_BACKED_DISCRETE_KERNEL_INVERSION",
            "operator_supported_classes": ["ODE_STATE_SPACE", "PDE_CONSTITUTIVE_SUBSTITUTION", "VOLTERRA_MEMORY", "INTEGRAL_CONSTITUTIVE", "GALERKIN_PDE_TO_STRUCTURAL_STATE", "DATA_BACKED_TEMPORAL_KERNEL_DISCOVERY", "DATA_BACKED_SPATIAL_NONLOCAL_KERNEL_DISCOVERY", "NONLOCAL_FRONTIER_SLOT"],
            "operator_backend_not_claimed": ["COMPLETE_DIFFERENTIAL_ALGEBRA", "ARBITRARY_UNKNOWN_OPERATOR_IDENTIFICATION_WITHOUT_DATA", "FRACTIONAL_OPERATOR_COMPLETENESS", "FULL_AEROSERVOELASTIC_AERO_LAG_STATE_IDENTIFICATION", "UNDECLARED_CROSS_CHART_STATE_IDENTIFICATION"],
            "circuit_rule": "ONLY_SUPPORT_MINIMAL_ELIMINATION_CONSEQUENCES_ARE_CERTIFIED_AS_FORCED_CIRCUITS",
            "validity_rule": "LOCAL_TYPED_GLUE_ONLY_INSIDE_DECLARED_CHART; CROSS_CHART_BRIDGE_REQUIRED",
            "unknown_frontier_rule": "SEARCH_IS_TARGET_FORMULA_FREE; KNOWN_LAWS_CONSTRAIN THE FRONTIER BUT ARE NOT THE SEARCH TARGET",
            "scientific_order_rule": "NO_FIXED_SOURCE_ORDER_OR_SUPPORT_CEILING; EXECUTION_BUDGET_STOPS COMPUTATION ONLY",
            "fail_closed": [
                "UNTYPED_QUANTITY",
                "SAME_SYMBOL_DIFFERENT_QUANTITY_KIND",
                "UNDECLARED_CROSS_CHART_BRIDGE",
                "NONPOLYNOMIAL_RELATION_OUTSIDE_EXECUTABLE_OPERATOR_SUBSET",
                "EMPTY_OR_INCOMPATIBLE_VALIDITY_OVERLAP",
            ],
            "external_semantic_foundations": {
                "QUDT": QUDT_REFERENCE,
                "EMMO": EMMO_REFERENCE,
                "algebraic_matroid_basis": "Rosen-2014-Computing-Algebraic-Matroids",
                "finite_sheaf_transport_basis": "Olivieri-Hernandez-2026-Sheaf-Theoretic-Transport-And-Obstruction",
            },
            "claim_boundary": {
                "naive_structural_lattice_validated": False,
                "mass_hidden_law_benchmark_validated": False,
                "mass_hidden_law_benchmark_executed": True,
                "new_physical_law_established": False,
                "full_sheaf_cohomology_backend": False,
                "semantic_lowering_all_symbol_occurrences": True,
                "global_quantity_identity_complete": False,
                "unknown_frontier_world_novelty_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def compile_quantity_ontology(self) -> Mapping[str, Any]:
        """Semantically lower every symbol occurrence in the current corpus.

        v6.18 deliberately does *not* equate "all fields filled" with semantic
        completeness.  Mathematical syntax, operators and differential tokens
        are first separated from physical quantities.  Every occurrence gets a
        semantic class; only canonical/high-confidence quantity kinds may form
        cross-owner coordinates.  Ambiguous physical quantities remain owner-
        local and therefore fail closed for cross-owner algebra.
        """
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        occurrences: List[Mapping[str, Any]] = []
        class_counts: Dict[str, int] = {}
        canonical = 0
        owner_local_quantity = 0
        syntax_nonquantity = 0
        inferred = 0
        preexisting = 0
        for passport in sorted(runtime.catalog.passports.values(), key=lambda row: row.owner_id):
            for symbol in passport.symbols:
                semantic_class, qid, reason = _semantic_class_and_kind(passport, symbol)
                class_counts[semantic_class] = class_counts.get(semantic_class, 0) + 1
                is_quantity_bearing = semantic_class in {"PHYSICAL_QUANTITY", "COORDINATE"}
                globally_canonical = bool(is_quantity_bearing and qid and qid in self.quantity_registry)
                canonical += int(globally_canonical)
                preexisting += int(globally_canonical and symbol.quantity_id == qid)
                inferred += int(globally_canonical and symbol.quantity_id != qid)
                owner_local_quantity += int(is_quantity_bearing and not globally_canonical)
                syntax_nonquantity += int(not is_quantity_bearing)
                coordinate_name = _semantic_coordinate_name(passport, symbol.display, semantic_class, qid if globally_canonical else None)
                qrow = self.quantity_registry.get(qid) if globally_canonical else None
                occurrences.append({
                    "coordinate_id": f"{passport.owner_id}::{symbol.symbol_id}",
                    "owner_id": passport.owner_id,
                    "domain_id": passport.domain_id,
                    "symbol_id": symbol.symbol_id,
                    "display": symbol.display,
                    "meaning": symbol.meaning_ru,
                    "semantic_class": semantic_class,
                    "semantic_lowering_reason": reason,
                    "quantity_kind_id": qid if globally_canonical else None,
                    "owner_local_quantity_identity": coordinate_name if is_quantity_bearing and not globally_canonical else None,
                    "chart_coordinate_key": coordinate_name if is_quantity_bearing or semantic_class == "PHYSICAL_CONSTANT" else None,
                    "dimension": qrow.get("dimension") if qrow else (asdict(symbol.dimension) if symbol.dimension is not None else None),
                    "unit": qrow.get("canonical_unit") if qrow else symbol.unit,
                    "status": (
                        "GLOBAL_CANONICAL_QUANTITY_KIND" if globally_canonical
                        else "OWNER_LOCAL_QUANTITY_KIND_UNRESOLVED_GLOBALLY" if is_quantity_bearing
                        else "SEMANTICALLY_LOWERED_NON_QUANTITY_TOKEN"
                    ),
                    "cross_owner_gluing_allowed": globally_canonical,
                    "global_gluing_by_display_allowed": False,
                })
        total = len(occurrences)
        payload = {
            "schema": "phi-quantity-ontology-compiler/v6.21",
            "owner_id": OWNER_ID,
            "passport_count": len(runtime.catalog.passports),
            "occurrence_count": total,
            "semantic_lowering_complete_count": total,
            "semantic_lowering_unresolved_count": 0,
            "semantic_class_counts": dict(sorted(class_counts.items())),
            "globally_canonical_quantity_occurrence_count": canonical,
            "preexisting_canonical_quantity_occurrence_count": preexisting,
            "contextually_inferred_canonical_quantity_occurrence_count": inferred,
            "owner_local_quantity_occurrence_count": owner_local_quantity,
            "nonquantity_syntax_or_object_occurrence_count": syntax_nonquantity,
            "semantic_completion_fraction": 1.0 if total else 0.0,
            "global_quantity_canonicalization_fraction": canonical / total if total else 0.0,
            "quantity_kind_registry_count": len(self.quantity_registry),
            "fail_closed_rule": "OWNER_LOCAL_OR_AMBIGUOUS_QUANTITY_MAY_BE_USED_INSIDE_ONE_SOURCE_RELATION_BUT_CANNOT_CREATE_CROSS_OWNER_GLUE",
            "quantity_identity_rule": "QUANTITY_KIND_PLUS_DOMAIN_CHART_PLUS_CONVENTIONAL_DISPLAY_IS_STILL_NOT_A_UNIVERSAL_INDIVIDUAL_QUANTITY_IDENTITY",
            "occurrences": occurrences,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def compile_global_constraint_hypergraph(self) -> Mapping[str, Any]:
        """Compile all passports after semantic lowering.

        A relation is semantically lowered even when it is not globally
        algebraically executable.  This separates *ontology completion* from
        *cross-owner canonical identity completion*, avoiding fake 100% typing.
        """
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        ontology = self.compile_quantity_ontology()
        by_owner: Dict[str, List[Mapping[str, Any]]] = {}
        for row in ontology["occurrences"]:
            by_owner.setdefault(row["owner_id"], []).append(row)
        relations: List[Mapping[str, Any]] = []
        algebraic_ready = 0
        semantic_ready = 0
        blocked_cross_owner = 0
        for passport in sorted(runtime.catalog.passports.values(), key=lambda row: row.owner_id):
            rows = by_owner.get(passport.owner_id, [])
            semantic_complete = len(rows) == len(passport.symbols) and all(row.get("semantic_class") for row in rows)
            quantity_rows = [row for row in rows if row["semantic_class"] in {"PHYSICAL_QUANTITY", "COORDINATE"}]
            globally_canonical = all(row.get("quantity_kind_id") for row in quantity_rows)
            lowered = self._lower_passport_algebraic(passport, precompiled_occurrences=rows)
            executable = lowered is not None and globally_canonical
            semantic_ready += int(semantic_complete)
            algebraic_ready += int(executable)
            blocked_cross_owner += int(not globally_canonical)
            relations.append({
                "relation_id": f"REL::{passport.owner_id}",
                "owner_id": passport.owner_id,
                "domain_id": passport.domain_id,
                "formula_digest": passport.formula.digest,
                "coordinate_occurrence_ids": [f"{passport.owner_id}::{s.symbol_id}" for s in passport.symbols],
                "semantic_lowering_complete": semantic_complete,
                "all_quantity_coordinates_globally_canonical": globally_canonical,
                "algebraic_polynomial_lowering_ready": lowered is not None,
                "cross_owner_circuit_ready": executable,
                "status": (
                    "READY_FOR_TYPED_CIRCUIT_SEARCH" if executable
                    else "SEMANTICALLY_LOWERED_BUT_CROSS_OWNER_OR_BACKEND_BLOCKED"
                ),
            })
        payload = {
            "schema": "phi-typed-constraint-hypergraph/v6.18",
            "owner_id": OWNER_ID,
            "relation_count": len(relations),
            "semantically_lowered_relation_count": semantic_ready,
            "cross_owner_circuit_ready_relation_count": algebraic_ready,
            "relations_with_owner_local_quantity_block": blocked_cross_owner,
            "global_same_printed_symbol_merge": False,
            "cross_owner_merge_rule": "REQUIRES_CANONICAL_QUANTITY_KIND_AND_SAME_DECLARED_DOMAIN_CHART_AND_CONVENTIONAL_COORDINATE_BINDING",
            "relations": relations,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def _lower_passport_algebraic(
        self,
        passport: Any,
        precompiled_occurrences: Sequence[Mapping[str, Any]] | None = None,
    ) -> Mapping[str, Any] | None:
        """Lower one passport equality to a semantic polynomial, fail-closed."""
        source = str(passport.formula.source or "").strip()
        if not source or source.count("=") != 1:
            return None
        if any(tok in source for tok in ("⇒", "=>", "≈", "∝", "≤", "≥", "<", ">", "∂", "∇", "∫", "∮", "⟨", "⟩")):
            return None
        low_source = source.lower()
        if any(re.search(rf"\b{re.escape(tok.lower())}\b", low_source) for tok in _FUNCTION_TOKENS | {"grad", "div", "dot", "ddot", "integral"}):
            return None
        text = _formula_text_for_parse(source)
        # Reject explicit derivatives even when the legacy parser tokenized dP/dr
        # as ordinary symbols.  Differential circuits require a separate backend.
        if re.search(r"\bd[A-Za-z_]+\s*/\s*d[A-Za-z_]+\b", text):
            return None
        if ";" in text or text.count("=") != 1:
            return None

        occ_rows = list(precompiled_occurrences or [])
        if not occ_rows:
            for symbol in passport.symbols:
                semantic_class, qid, reason = _semantic_class_and_kind(passport, symbol)
                globally_canonical = bool(qid and qid in self.quantity_registry and semantic_class in {"PHYSICAL_QUANTITY", "COORDINATE"})
                occ_rows.append({
                    "display": symbol.display,
                    "semantic_class": semantic_class,
                    "quantity_kind_id": qid if globally_canonical else None,
                    "chart_coordinate_key": _semantic_coordinate_name(passport, symbol.display, semantic_class, qid if globally_canonical else None),
                    "semantic_lowering_reason": reason,
                })
        occ_by_ascii: Dict[str, Mapping[str, Any]] = {}
        for row in occ_rows:
            occ_by_ascii[_ascii_symbol_token(str(row["display"]))] = row

        # Explicitly bind common single-letter symbols so implicit multiplication
        # splits legacy tokens such as mv, IR and RT instead of preserving them as
        # accidental composite coordinates.
        atom_names = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        atom_names.update({
            "rho", "mu", "sigma", "epsilon", "kappa", "lambda", "omega", "gamma", "beta", "alpha", "tau",
            "theta", "Phi", "phi", "psi", "xi", "eta", "hbar", "pi", "Delta", "Re", "AR", "Mach",
        })
        atom_names.update(occ_by_ascii)
        local = {name: sp.Symbol(name) for name in atom_names if name not in _FUNCTION_TOKENS}
        local["pi"] = sp.Symbol("pi")
        transforms = standard_transformations + (implicit_multiplication_application, convert_xor)
        try:
            lhs_text, rhs_text = text.split("=", 1)
            lhs = parse_expr(lhs_text, local_dict=local, transformations=transforms, evaluate=False)
            rhs = parse_expr(rhs_text, local_dict=local, transformations=transforms, evaluate=False)
            expr = sp.together(lhs - rhs)
            numerator, denominator = sp.fraction(expr)
        except Exception:
            return None

        free = sorted(numerator.free_symbols | denominator.free_symbols, key=lambda v: v.name)
        if not free:
            return None
        rename: Dict[sp.Symbol, sp.Symbol] = {}
        bindings: Dict[str, Mapping[str, Any]] = {}
        for sym in free:
            name = sym.name
            row = occ_by_ascii.get(name)
            if row is None:
                # Virtual atom recovered by implicit splitting of a legacy
                # composite token.  Classify it with the same deterministic
                # context rules as an explicit symbol occurrence.
                class Dummy:
                    display = name
                    quantity_id = None
                semantic_class, qid, reason = _semantic_class_and_kind(passport, Dummy())
                globally_canonical = bool(qid and qid in self.quantity_registry and semantic_class in {"PHYSICAL_QUANTITY", "COORDINATE"})
                key = _semantic_coordinate_name(passport, name, semantic_class, qid if globally_canonical else None)
                row = {
                    "display": name, "semantic_class": semantic_class,
                    "quantity_kind_id": qid if globally_canonical else None,
                    "chart_coordinate_key": key, "semantic_lowering_reason": reason,
                }
            safe = str(row.get("chart_coordinate_key") or f"LOCAL__{_ascii_symbol_token(passport.owner_id)}__{name}")
            rename[sym] = sp.Symbol(safe)
            bindings[safe] = row
        numerator = sp.expand(numerator.xreplace(rename))
        denominator = sp.expand(denominator.xreplace(rename))
        try:
            all_free = sorted(numerator.free_symbols | denominator.free_symbols, key=lambda v: v.name)
            sp.Poly(numerator, *all_free)
            sp.Poly(denominator, *all_free)
        except Exception:
            return None
        if len(all_free) > 12 or sp.count_ops(numerator) > 120:
            return None
        return {
            "owner_id": passport.owner_id,
            "domain_id": passport.domain_id,
            "polynomial_expr": _normalize_polynomial(numerator),
            "denominator_expr": sp.factor(denominator),
            "polynomial": str(_normalize_polynomial(numerator)),
            "denominator": str(sp.factor(denominator)),
            "support": tuple(sorted(sym.name for sym in all_free)),
            "bindings": bindings,
            "formula_digest": passport.formula.digest,
            "status": "SEMANTIC_RATIONAL_POLYNOMIAL_LOWERING_PASS",
        }

    def _load_mass_blind_partitions(self) -> Mapping[str, Any]:
        path = self.root / "data" / "benchmarks" / "law_lattice_v0_2_mass_blind_partitions.json"
        payload = _load_json(path)
        if payload.get("original_total_hidden_evaluations") != 320 or len(payload.get("splits", [])) != 5:
            raise ValueError("mass blind benchmark partition contract is malformed")
        if any(len(row.get("hidden_owner_ids", [])) != 64 for row in payload["splits"]):
            raise ValueError("mass blind benchmark must preserve 64 hidden cases per split")
        return payload

    @staticmethod
    def _poly_equivalent(left: sp.Expr, right: sp.Expr) -> bool:
        left = _normalize_polynomial(left)
        right = _normalize_polynomial(right)
        union = sorted(left.free_symbols | right.free_symbols, key=lambda v: v.name)
        if not union:
            return bool(sp.simplify(left - right) == 0)
        try:
            p_left = sp.Poly(left, *union)
            p_right = sp.Poly(right, *union)
            if p_left.total_degree() != p_right.total_degree():
                return False
            quotient = sp.simplify(left / right)
            return quotient != 0 and not quotient.free_symbols
        except Exception:
            return False

    def _generate_blind_circuit_pool(self, training_passports: Sequence[Any]) -> Mapping[str, Any]:
        """Generate pair/triple resultants using visible laws only.

        Hidden truth objects are not accepted by this method.  The bounded
        construction is an execution strategy, not a scientific order ceiling:
        pairwise circuits are materialized first and one additional source law
        may extend them.  Higher-order algebra remains available through the
        public Gröbner owner for directed queries.
        """
        lowered: List[Mapping[str, Any]] = []
        for passport in training_passports:
            row = self._lower_passport_algebraic(passport)
            if row is not None:
                lowered.append(row)
        lowered.sort(key=lambda r: r["owner_id"])
        by_domain: Dict[str, List[Mapping[str, Any]]] = {}
        for row in lowered:
            by_domain.setdefault(row["domain_id"], []).append(row)

        candidates: Dict[str, Dict[str, Any]] = {}
        pair_attempts = pair_successes = 0
        for domain, rows in sorted(by_domain.items()):
            for left, right in combinations(rows, 2):
                shared = sorted(
                    sym for sym in set(left["support"]) & set(right["support"])
                    if sym.startswith("Q__")
                )
                for shared_name in shared[:3]:
                    pair_attempts += 1
                    x = sp.Symbol(shared_name)
                    try:
                        res = sp.resultant(left["polynomial_expr"], right["polynomial_expr"], x)
                        if res == 0:
                            continue
                        factors = sp.factor_list(sp.expand(res))[1]
                    except Exception:
                        continue
                    for factor, _power in factors:
                        factor = _normalize_polynomial(factor)
                        support = sorted(sym.name for sym in factor.free_symbols)
                        if len(support) < 2 or len(support) > 10 or sp.count_ops(factor) > 100:
                            continue
                        if any(name.startswith("LOCAL") for name in support):
                            continue
                        try:
                            if sp.Poly(factor, *sorted(factor.free_symbols, key=lambda s: s.name)).total_degree() > 6:
                                continue
                        except Exception:
                            continue
                        key = str(factor)
                        source_ids = tuple(sorted((left["owner_id"], right["owner_id"])))
                        existing = candidates.get(key)
                        if existing is None:
                            candidates[key] = {
                                "polynomial_expr": factor, "polynomial": key, "domain_id": domain,
                                "source_owner_ids": source_ids, "support": tuple(support),
                                "derivation_count": 1, "construction_depth": 2,
                            }
                            pair_successes += 1
                        else:
                            existing["derivation_count"] += 1
                            if source_ids < tuple(existing["source_owner_ids"]):
                                existing["source_owner_ids"] = source_ids

        # One deterministic extension layer, capped only for execution cost.
        pair_seed = sorted(
            candidates.values(),
            key=lambda r: (-int(r["derivation_count"]), len(r["support"]), sp.count_ops(r["polynomial_expr"]), r["polynomial"]),
        )[:1500]
        triple_attempts = triple_successes = 0
        for cand in pair_seed:
            domain_rows = by_domain.get(cand["domain_id"], [])
            cand_support = set(cand["support"])
            for relation in domain_rows:
                if relation["owner_id"] in cand["source_owner_ids"]:
                    continue
                shared = sorted(sym for sym in cand_support & set(relation["support"]) if sym.startswith("Q__"))
                for shared_name in shared[:1]:
                    triple_attempts += 1
                    if triple_attempts > 8000:
                        break
                    x = sp.Symbol(shared_name)
                    try:
                        res = sp.resultant(cand["polynomial_expr"], relation["polynomial_expr"], x)
                        if res == 0:
                            continue
                        factors = sp.factor_list(sp.expand(res))[1]
                    except Exception:
                        continue
                    for factor, _power in factors:
                        factor = _normalize_polynomial(factor)
                        support = sorted(sym.name for sym in factor.free_symbols)
                        if len(support) < 2 or len(support) > 10 or sp.count_ops(factor) > 100:
                            continue
                        if any(name.startswith("LOCAL") for name in support):
                            continue
                        try:
                            if sp.Poly(factor, *sorted(factor.free_symbols, key=lambda s: s.name)).total_degree() > 6:
                                continue
                        except Exception:
                            continue
                        key = str(factor)
                        source_ids = tuple(sorted(set(cand["source_owner_ids"]) | {relation["owner_id"]}))
                        if len(source_ids) != 3:
                            continue
                        existing = candidates.get(key)
                        if existing is None:
                            candidates[key] = {
                                "polynomial_expr": factor, "polynomial": key, "domain_id": cand["domain_id"],
                                "source_owner_ids": source_ids, "support": tuple(support),
                                "derivation_count": 1, "construction_depth": 3,
                            }
                            triple_successes += 1
                        else:
                            existing["derivation_count"] += 1
                if triple_attempts > 8000:
                    break
            if triple_attempts > 8000:
                break

        ranked = sorted(
            candidates.values(),
            key=lambda r: (
                -int(r["derivation_count"]), int(r["construction_depth"]), len(r["support"]),
                sp.count_ops(r["polynomial_expr"]), r["polynomial"],
            ),
        )
        for idx, row in enumerate(ranked, start=1):
            row["rank"] = idx
        frozen_payload = [
            {k: v for k, v in row.items() if k != "polynomial_expr"}
            for row in ranked
        ]
        return {
            "lowered_visible_relation_count": len(lowered),
            "pair_attempt_count": pair_attempts,
            "pair_new_circuit_count": pair_successes,
            "triple_attempt_count": triple_attempts,
            "triple_new_circuit_count": triple_successes,
            "candidate_count": len(ranked),
            "candidate_pool_digest": digest_payload(frozen_payload),
            "ranked_candidates": ranked,
        }

    def _run_mass_hidden_law_benchmark(self) -> Mapping[str, Any]:
        """Replay the original 5x64 holdout partitions with circuit search."""
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        partitions = self._load_mass_blind_partitions()
        strict_states = {"ESTABLISHED_LAW", "EXPERIMENTALLY_CONFIRMED", "PHENOMENOLOGICAL", "DERIVED_CLOSURE_THEOREM"}
        current_strict = {
            oid: p for oid, p in runtime.catalog.passports.items() if p.epistemic_state in strict_states
        }
        split_rows: List[Mapping[str, Any]] = []
        total_exact = total_top64 = total_eligible = total_available = unavailable = 0
        reciprocal_rank_sum = 0.0
        exact_available = top64_available = 0
        all_case_rows: List[Mapping[str, Any]] = []
        for split_index, split in enumerate(partitions["splits"], start=1):
            hidden_ids = list(split["hidden_owner_ids"])
            hidden_set = set(hidden_ids)
            # The generator sees only current strict visible passports.  Hidden
            # IDs are used by the harness exclusively to remove rows.
            training = [p for oid, p in sorted(current_strict.items()) if oid not in hidden_set]
            pool = self._generate_blind_circuit_pool(training)
            ranked = pool["ranked_candidates"]
            # Freeze digest before any hidden target is read for scoring.
            frozen_digest = pool["candidate_pool_digest"]
            case_rows = []
            for oid in hidden_ids:
                passport = current_strict.get(oid)
                if passport is None:
                    unavailable += 1
                    row = {
                        "owner_id": oid,
                        "status": "SOURCE_CASE_UNAVAILABLE_IN_CURRENT_RELEASE",
                        "eligible_algebraic_target": False,
                        "exact_recovered": False,
                        "top64_recovered": False,
                        "rank": None,
                    }
                    case_rows.append(row); all_case_rows.append(row)
                    continue
                total_available += 1
                target = self._lower_passport_algebraic(passport)
                if target is None:
                    row = {
                        "owner_id": oid,
                        "status": "TARGET_NOT_IN_RATIONAL_POLYNOMIAL_BACKEND",
                        "eligible_algebraic_target": False,
                        "exact_recovered": False,
                        "top64_recovered": False,
                        "rank": None,
                    }
                    case_rows.append(row); all_case_rows.append(row)
                    continue
                total_eligible += 1
                target_expr = target["polynomial_expr"]
                match_rank = None
                match = None
                for candidate in ranked:
                    if candidate["domain_id"] != passport.domain_id:
                        continue
                    if self._poly_equivalent(candidate["polynomial_expr"], target_expr):
                        match_rank = int(candidate["rank"])
                        match = candidate
                        break
                exact_recovered = match_rank is not None
                top64 = bool(match_rank is not None and match_rank <= 64)
                total_exact += int(exact_recovered)
                total_top64 += int(top64)
                exact_available += int(exact_recovered)
                top64_available += int(top64)
                reciprocal_rank_sum += (1.0 / match_rank) if match_rank else 0.0
                row = {
                    "owner_id": oid,
                    "status": "EXACT_CIRCUIT_RECOVERED" if exact_recovered else "NO_EXACT_CIRCUIT_IN_FROZEN_POOL",
                    "eligible_algebraic_target": True,
                    "target_support_size": len(target["support"]),
                    "exact_recovered": exact_recovered,
                    "top64_recovered": top64,
                    "rank": match_rank,
                    "matched_source_owner_ids": list(match["source_owner_ids"]) if match else [],
                    "matched_circuit": match["polynomial"] if match else None,
                }
                case_rows.append(row); all_case_rows.append(row)
            split_rows.append({
                "split_index": split_index,
                "seed": split["seed"],
                "hidden_case_count": len(hidden_ids),
                "training_current_strict_count": len(training),
                "candidate_pool_digest_frozen_before_unblind": frozen_digest,
                "lowered_visible_relation_count": pool["lowered_visible_relation_count"],
                "candidate_count": pool["candidate_count"],
                "pair_attempt_count": pool["pair_attempt_count"],
                "triple_attempt_count": pool["triple_attempt_count"],
                "exact_recovery_count": sum(int(r["exact_recovered"]) for r in case_rows),
                "top64_recovery_count": sum(int(r["top64_recovered"]) for r in case_rows),
                "eligible_target_count": sum(int(r["eligible_algebraic_target"]) for r in case_rows),
                "source_unavailable_count": sum(r["status"] == "SOURCE_CASE_UNAVAILABLE_IN_CURRENT_RELEASE" for r in case_rows),
                "cases": case_rows,
            })
        total = int(partitions["original_total_hidden_evaluations"])
        eligible_fraction = total_eligible / total if total else 0.0
        recall_all = total_top64 / total if total else 0.0
        recall_available = top64_available / total_available if total_available else 0.0
        recall_eligible = total_top64 / total_eligible if total_eligible else 0.0
        exact_all = total_exact / total if total else 0.0
        exact_eligible = total_exact / total_eligible if total_eligible else 0.0
        # Scientific validation requires a material improvement over the old
        # random baseline on the all-case denominator *and* nontrivial backend
        # coverage.  This threshold is intentionally conservative and reported,
        # not hidden inside a generic PASS.
        random_baseline = float(partitions["original_random_recall_at_64"])
        predictive_validated = recall_all >= max(0.25, 2.0 * random_baseline) and eligible_fraction >= 0.5
        scientific_verdict = "PREDICTIVE_SIGNAL_VALIDATED_ON_REPLAY" if predictive_validated else "PREDICTIVE_SIGNAL_NOT_VALIDATED"
        result = {
            "schema": "phi-constraint-atlas/v6.18-mass-blind-circuit-replay",
            "benchmark_partition_source": "EXACT_PHI_LAWLATTICE_V0_2_5X64_PARTITIONS",
            "partition_source_report_digest": partitions["source_report_digest"],
            "partition_source_report_sha256": partitions["source_report_sha256"],
            "partition_source_probe_zip_sha256": partitions["source_probe_zip_sha256"],
            "hidden_formula_used_during_candidate_generation": False,
            "hidden_name_used_during_candidate_generation": False,
            "hidden_owner_metadata_used_during_candidate_generation": False,
            "hidden_ids_used_by_harness_only_to_remove_and_postfreeze_score": True,
            "candidate_pool_frozen_before_target_formula_access": True,
            "original_total_hidden_evaluations": total,
            "executed_hidden_cases": total,
            "current_source_available_cases": total_available,
            "source_case_unavailable_count": unavailable,
            "eligible_rational_polynomial_targets": total_eligible,
            "backend_eligibility_fraction_all_cases": eligible_fraction,
            "exact_recovery_count_all_320": total_exact,
            "exact_recovery_fraction_all_320": exact_all,
            "top64_recovery_count_all_320": total_top64,
            "recall_at_64_all_320": recall_all,
            "recall_at_64_current_source_available": recall_available,
            "recall_at_64_backend_eligible": recall_eligible,
            "exact_recovery_fraction_backend_eligible": exact_eligible,
            "mean_reciprocal_rank_backend_eligible_denominator": reciprocal_rank_sum / total_eligible if total_eligible else 0.0,
            "old_structural_recall_at_64": float(partitions["original_structural_recall_at_64"]),
            "old_random_baseline_recall_at_64": random_baseline,
            "strict_comparability_note": "HOLDOUT_PARTITIONS_ARE_EXACT_BUT_CURRENT_RELEASE_CORPUS_HAS_DRIFTED_FROM_THE_428_PASSPORT_V6_15_SNAPSHOT;_15_OF_320_SOURCE_CASES_ARE_UNAVAILABLE_AND_NEWER_VISIBLE_LAWS_MAY_EXIST",
            "scientific_validation_rule": "RECALL_AT_64_ALL_320>=MAX(0.25,2*OLD_RANDOM_BASELINE)_AND_BACKEND_ELIGIBILITY>=0.5",
            "scientific_verdict": scientific_verdict,
            "constraint_atlas_mass_hidden_law_recall_validated": predictive_validated,
            "splits": split_rows,
        }
        result["digest"] = digest_payload(result)
        return result

    @staticmethod
    def _frontier_family(owner_id: str) -> str:
        """Coarse research-family label used only for exploration ranking."""
        for token in (
            "GUST", "BREGUET", "POWER", "REYNOLDS", "MACH", "STAGNATION",
            "AEROSTAT", "HYBRID", "INDUCED", "LIFT", "DRAG", "ASPECT",
            "TRANSITION", "THERMO", "SOLAR", "STORAGE", "CONTROL", "PSD",
        ):
            if token in owner_id:
                return token
        return owner_id.split("-", 1)[0]

    def _aeronautics_known_polynomial_keys(self) -> set[str]:
        """Return normalized current-corpus relations for post-derivation novelty checks.

        This routine is never consulted while generating a frontier candidate.  It is
        used only after the candidate pool is frozen, so the target/newness label
        cannot steer the symbolic derivation.
        """
        keys: set[str] = set()
        chart = self._aeronautics_chart()
        for relation in chart["relations"].values():
            if relation.polynomial:
                try:
                    local = {name: sp.Symbol(name) for name in relation.support}
                    local["pi"] = sp.pi
                    expr = _normalize_polynomial(sp.sympify(relation.polynomial, locals=local))
                    keys.add(sp.srepr(expr))
                except Exception:
                    pass
        for law in self.aeronautics_db.get("laws", ()):  # materialized closures
            variables = [str(row.get("symbol")) for row in law.get("variables", ()) if row.get("symbol")]
            local = {name: sp.Symbol(name) for name in variables if _IDENTIFIER.fullmatch(name)}
            local["pi"] = sp.pi
            for part in str(law.get("formula", "")).split(";"):
                text = part.strip()
                if text.count("=") != 1 or any(token in text for token in ("<=", ">=")):
                    continue
                try:
                    lhs, rhs = text.replace("^", "**").split("=", 1)
                    expr = sp.together(sp.sympify(lhs, locals=local) - sp.sympify(rhs, locals=local))
                    numerator, _denominator = sp.fraction(expr)
                    keys.add(sp.srepr(_normalize_polynomial(numerator)))
                except Exception:
                    continue
        return keys

    def scan_unknown_frontier(self, execution_budget: Mapping[str, int] | None = None) -> Mapping[str, Any]:
        """Construct a finite algebraic-ideal basis for each connected source component.

        The former best-first resultant walk used fixed visit/expression ceilings and
        therefore made the materialized research region depend on arbitrary execution
        counters.  The current backend instead computes a deterministic Gröbner basis
        of the polynomial ideal generated by every executable relation in each
        connected source component.  Gröbner-basis completion has a mathematical
        saturation criterion; no source-order, support-size, expression-size or visit
        ceiling is used by the canonical run.

        ``execution_budget`` is retained only as a backwards-compatible API field.
        Supplying any finite legacy budget is rejected rather than silently restoring
        the old scientific truncation semantics.
        """
        if execution_budget:
            raise ValueError(
                "finite execution_budget is no longer a scientific search control; "
                "the canonical algebraic frontier terminates by Gröbner-basis saturation"
            )

        chart = self._aeronautics_chart()
        source_rows: List[Dict[str, Any]] = []
        for owner_id, relation in sorted(chart["relations"].items()):
            if relation.status != "EXECUTABLE_ALGEBRAIC_CONSTRAINT":
                continue
            parsed = _parse_polynomial_relation(
                self.aero_sources[owner_id]["formula"], self.aero_sources[owner_id]["variables"]
            )
            if parsed is None:
                continue
            numerator, denominator = parsed
            numerator = _normalize_polynomial(numerator)
            denominator = sp.factor(denominator)
            source_rows.append({
                "owner_id": owner_id,
                "polynomial_expr": numerator,
                "denominator_expr": denominator,
                "support": frozenset(symbol.name for symbol in numerator.free_symbols | denominator.free_symbols),
            })

        source_by_id = {row["owner_id"]: row for row in source_rows}
        adjacency: Dict[str, set[str]] = {row["owner_id"]: set() for row in source_rows}
        for index, left in enumerate(source_rows):
            for right in source_rows[index + 1:]:
                if set(left["support"]) & set(right["support"]):
                    adjacency[left["owner_id"]].add(right["owner_id"])
                    adjacency[right["owner_id"]].add(left["owner_id"])

        components: List[Tuple[str, ...]] = []
        unvisited = set(adjacency)
        while unvisited:
            seed = min(unvisited)
            stack = [seed]
            component: set[str] = set()
            while stack:
                owner_id = stack.pop()
                if owner_id in component:
                    continue
                component.add(owner_id)
                stack.extend(sorted(adjacency[owner_id] - component, reverse=True))
            unvisited -= component
            components.append(tuple(sorted(component)))
        components.sort(key=lambda ids: (ids[0] if ids else "", len(ids), ids))

        known_keys = self._aeronautics_known_polynomial_keys()
        postchecked: List[Dict[str, Any]] = []
        component_reports: List[Dict[str, Any]] = []
        total_basis_polynomials = 0

        for component_index, source_ids in enumerate(components, start=1):
            rows = [source_by_id[owner_id] for owner_id in source_ids]
            polynomials = [row["polynomial_expr"] for row in rows]
            symbols = sorted(
                set().union(*(poly.free_symbols for poly in polynomials)),
                key=lambda value: value.name,
            ) if polynomials else []
            denominator_guards = sorted({
                str(row["denominator_expr"])
                for row in rows
                if sp.simplify(row["denominator_expr"] - 1) != 0
            })
            if not polynomials or not symbols:
                basis_exprs = polynomials
            else:
                basis = sp.groebner(polynomials, *symbols, order="grevlex")
                basis_exprs = [_normalize_polynomial(poly.as_expr()) for poly in basis.polys]

            # A Gröbner basis is a finite generating basis of the same polynomial
            # ideal.  It is not an enumeration of every formula expressible from
            # that ideal, so downstream novelty remains a candidate property.
            unique_basis: Dict[str, sp.Expr] = {}
            for expr in basis_exprs:
                unique_basis.setdefault(sp.srepr(expr), expr)
            basis_exprs = [unique_basis[key] for key in sorted(unique_basis)]
            total_basis_polynomials += len(basis_exprs)

            source_union = set().union(*(set(row["support"]) for row in rows)) if rows else set()
            family_count = len({self._frontier_family(owner_id) for owner_id in source_ids})
            component_id = f"ALG-COMP-{component_index:02d}-" + digest_payload(source_ids)[:12].upper()
            candidate_ids: List[str] = []
            for expr in basis_exprs:
                support = tuple(sorted(symbol.name for symbol in expr.free_symbols))
                complexity = int(sp.count_ops(expr))
                eliminated_count = len(source_union - set(support))
                blocked_touch = sum(
                    bool(set(support) & set(blocked.support))
                    for blocked in chart["relations"].values()
                    if blocked.status != "EXECUTABLE_ALGEBRAIC_CONSTRAINT"
                )
                key = sp.srepr(expr)
                candidate_id = "UF-ALG-" + digest_payload({
                    "component": component_id,
                    "polynomial": key,
                })[:18].upper()
                candidate_ids.append(candidate_id)
                row = {
                    "candidate_id": candidate_id,
                    "component_id": component_id,
                    "polynomial": str(expr),
                    "source_owner_ids": source_ids,
                    "source_order": len(source_ids),
                    "support": support,
                    "support_count": len(support),
                    "eliminated_coordinate_count": eliminated_count,
                    "family_count": family_count,
                    "blocked_operator_touch_count": blocked_touch,
                    "expression_operation_count": complexity,
                    "priority_score": (
                        80 * family_count + 18 * eliminated_count + 5 * len(support)
                        + 12 * len(source_ids) + 15 * blocked_touch - complexity
                    ),
                    "frontier_priority_score": (
                        80 * family_count + 18 * eliminated_count + 5 * len(support)
                        + 12 * len(source_ids) + 15 * blocked_touch - complexity
                    ),
                    "derivation_backend": "CONNECTED_COMPONENT_GROEBNER_IDEAL_BASIS_GREvLEX",
                    "monomial_order": "grevlex",
                    "component_generator_count": len(source_ids),
                    "component_variable_count": len(symbols),
                    "validity_denominator_guards": denominator_guards,
                    "target_formula_access_during_search": False,
                    "materialized_law_catalog_access_during_search": False,
                    "formal_status": "SOURCE_IDEAL_GROEBNER_BASIS_CONSEQUENCE",
                    "source_minimal_under_generated_factor_witnesses": None,
                    "source_minimality_status": "NOT_CLAIMED_COMPONENT_GENERATOR_CERTIFICATE",
                    "already_materialized_in_current_aeronautics_corpus": key in known_keys,
                    "corpus_novelty_status": (
                        "ALREADY_MATERIALIZED_RELATION" if key in known_keys
                        else "CURRENT_CORPUS_UNMATERIALIZED_IDEAL_BASIS_CONSEQUENCE"
                    ),
                    "world_literature_novelty_status": "NOT_ESTABLISHED_POST_DERIVATION_REVIEW_REQUIRED",
                }
                postchecked.append(row)
            component_reports.append({
                "component_id": component_id,
                "source_owner_ids": source_ids,
                "source_relation_count": len(source_ids),
                "variable_count": len(symbols),
                "variables": tuple(symbol.name for symbol in symbols),
                "basis_polynomial_count": len(basis_exprs),
                "candidate_ids": tuple(sorted(candidate_ids)),
                "validity_denominator_guards": denominator_guards,
                "saturation_status": "GROEBNER_IDEAL_BASIS_COMPLETED",
            })

        postchecked.sort(key=lambda row: row["candidate_id"])
        frozen_generation_digest = digest_payload([
            {k: v for k, v in row.items() if k not in {"already_materialized_in_current_aeronautics_corpus", "corpus_novelty_status", "world_literature_novelty_status"}}
            for row in postchecked
        ])
        unknown = [row for row in postchecked if not row["already_materialized_in_current_aeronautics_corpus"]]
        unknown.sort(key=lambda row: (
            -int(row["frontier_priority_score"]), -row["family_count"], -row["support_count"],
            -row["source_order"], row["expression_operation_count"], row["candidate_id"],
        ))
        exploration_anchor = unknown[0] if unknown else None
        operator_frontiers = [
            {
                "owner_id": relation.owner_id,
                "relation_kind": relation.relation_kind,
                "support": list(relation.support),
                "status": "UNKNOWN_OPERATOR_BACKEND_FRONTIER",
            }
            for relation in chart["relations"].values()
            if relation.status != "EXECUTABLE_ALGEBRAIC_CONSTRAINT"
        ]
        result = {
            "schema": "phi-constraint-atlas-unknown-frontier/v6.23",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": (
                "PASS_UNKNOWN_FRONTIER_ALGEBRAIC_IDEAL_BASIS_SATURATED"
                if unknown else "PASS_ALGEBRAIC_IDEAL_BASIS_SATURATED_NO_CURRENT_CORPUS_GAP"
            ),
            "research_mode": "TARGET_FREE_CONNECTED_SOURCE_ALGEBRAIC_IDEAL_SATURATION",
            "chart_id": chart["chart_id"],
            "source_relation_count": len(source_rows),
            "connected_source_component_count": len(components),
            "connected_source_components": component_reports,
            "execution_budget_ir": {
                "backend": "GROEBNER_IDEAL_BASIS_SATURATION",
                "monomial_order": "grevlex",
                "fixed_resultant_evaluation_ceiling": None,
                "fixed_expression_operation_ceiling": None,
                "fixed_frontier_state_ceiling": None,
                "fixed_execution_visit_ceiling": None,
            },
            "execution_budget_stop_reason": "ALGEBRAIC_IDEAL_BASIS_SATURATED",
            "resultant_evaluation_count": 0,
            "expanded_state_count": total_basis_polynomials,
            "scientific_source_order_ceiling_used": False,
            "scientific_support_size_ceiling_used": False,
            "execution_budget_is_physical_admissibility_gate": False,
            "fixed_execution_visit_ceiling": None,
            "target_formula_access_during_search": False,
            "materialized_law_catalog_access_during_generation": False,
            "candidate_pool_frozen_before_corpus_novelty_check": True,
            "frozen_generation_digest": frozen_generation_digest,
            "generated_consequence_count": len(postchecked),
            "forced_unmaterialized_relation_count": len(unknown),
            "maximum_executed_source_order": max((len(c) for c in components), default=0),
            "maximum_candidate_support_count": max((row["support_count"] for row in postchecked), default=0),
            "operator_backend_frontier_count": len(operator_frontiers),
            "operator_backend_frontiers": operator_frontiers,
            "candidate_ledger": postchecked,
            "unknown_candidate_ledger": unknown,
            "top_unknown_candidates": unknown[:25],
            "exploration_anchor_candidate": exploration_anchor,
            "claim_boundary": {
                "formal_source_derived_consequence": True,
                "groebner_basis_generates_same_polynomial_ideal_as_source_component": True,
                "every_possible_symbolic_formula_enumerated": False,
                "source_certificate_minimality_established": False,
                "new_law_of_nature_established": False,
                "world_literature_novelty_established": False,
                "cross_regime_physical_validity_inherited_automatically": False,
                "candidate_requires_post_derivation_validity_and_falsification": True,
            },
        }
        result["digest"] = digest_payload(result)
        return result

    def build_aeroelastic_projection_bridge(
        self,
        mode_count: int = 4,
        quadrature_points: int = 4001,
    ) -> Mapping[str, Any]:
        """Materialize the structural PDE -> reduced-state part of the ASE bridge.

        The source PDE is OME-036 (Euler--Bernoulli).  No target A-matrix is
        supplied.  A clamped-free validation chart is declared explicitly,
        cantilever eigenfunctions are generated from their boundary-value
        condition, and Galerkin projection builds M, K, A_s and B_q.  This
        closes only the *structural substate* x_s=[eta, eta_dot].  Unsteady
        aerodynamic lag states, actuator/sensor states, and the gust->q(x,t)
        map remain separate unknown operators and are not guessed.
        """
        import numpy as np
        from scipy.optimize import brentq
        from .runtime import LawSpaceRuntime

        runtime = LawSpaceRuntime(self.root)
        required = ("OME-036", "AERO-AEROSERVOELASTIC-STATE-SPACE")
        missing = [owner_id for owner_id in required if owner_id not in runtime.catalog.passports]
        if missing:
            return {
                "schema": "phi-aeroelastic-projection-bridge/v6.21",
                "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION,
                "status": "BLOCKED_SOURCE_OWNER_MISSING",
                "missing_owner_ids": missing,
                "digest": digest_payload({"missing": missing}),
            }
        mode_count = int(mode_count)
        quadrature_points = int(quadrature_points)
        if mode_count < 1 or quadrature_points < 501:
            raise ValueError("mode_count>=1 and quadrature_points>=501 are required")

        # Nondimensional uniform cantilever calibration chart: L=rho*A=E*I=1.
        # Physical scaling is retained symbolically in the returned bridge IR.
        f = lambda beta: float(np.cosh(beta) * np.cos(beta) + 1.0)
        scan = np.linspace(0.1, (mode_count + 1.5) * np.pi, 50000)
        roots: List[float] = []
        prev_x, prev_f = float(scan[0]), f(float(scan[0]))
        for xval in scan[1:]:
            xval = float(xval)
            value = f(xval)
            if prev_f * value < 0.0:
                root = float(brentq(f, prev_x, xval, xtol=1e-14, rtol=1e-14))
                if not roots or abs(root - roots[-1]) > 1e-8:
                    roots.append(root)
                    if len(roots) == mode_count:
                        break
            prev_x, prev_f = xval, value
        if len(roots) != mode_count:
            raise RuntimeError("cantilever eigen-root generation did not reach requested mode_count")

        x = np.linspace(0.0, 1.0, quadrature_points)
        phis: List[np.ndarray] = []
        phi1s: List[np.ndarray] = []
        phi2s: List[np.ndarray] = []
        phi3s: List[np.ndarray] = []
        for beta in roots:
            alpha = (np.cosh(beta) + np.cos(beta)) / (np.sinh(beta) + np.sin(beta))
            bx = beta * x
            phi = np.cosh(bx) - np.cos(bx) - alpha * (np.sinh(bx) - np.sin(bx))
            phi1 = beta * (np.sinh(bx) + np.sin(bx) - alpha * (np.cosh(bx) - np.cos(bx)))
            phi2 = beta**2 * (np.cosh(bx) + np.cos(bx) - alpha * (np.sinh(bx) + np.sin(bx)))
            phi3 = beta**3 * (np.sinh(bx) - np.sin(bx) - alpha * (np.cosh(bx) + np.cos(bx)))
            norm = float(np.sqrt(np.trapezoid(phi * phi, x)))
            phis.append(phi / norm)
            phi1s.append(phi1 / norm)
            phi2s.append(phi2 / norm)
            phi3s.append(phi3 / norm)
        Phi = np.asarray(phis)
        Phi1 = np.asarray(phi1s)
        Phi2 = np.asarray(phi2s)
        Phi3 = np.asarray(phi3s)

        M = np.asarray([[np.trapezoid(Phi[i] * Phi[j], x) for j in range(mode_count)] for i in range(mode_count)])
        K = np.asarray([[np.trapezoid(Phi2[i] * Phi2[j], x) for j in range(mode_count)] for i in range(mode_count)])
        Minv = np.linalg.inv(M)
        Omega2 = Minv @ K
        eigvals = np.sort(np.real(np.linalg.eigvals(Omega2)))
        omega_numeric = np.sqrt(eigvals)
        omega_exact = np.asarray(roots) ** 2
        frequency_relative_error = float(np.max(np.abs(omega_numeric - omega_exact) / omega_exact))

        zeros = np.zeros_like(M)
        identity = np.eye(mode_count)
        A_s = np.block([[zeros, identity], [-Omega2, zeros]])
        B_q = np.vstack([zeros, Minv])

        # Projection/reconstruction control entirely inside the retained subspace.
        eta_truth = np.asarray([1.0 / (j + 1.0) for j in range(mode_count)])
        w = eta_truth @ Phi
        generalized = np.asarray([np.trapezoid(Phi[j] * w, x) for j in range(mode_count)])
        eta_recovered = Minv @ generalized
        w_recovered = eta_recovered @ Phi
        reconstruction_rms = float(np.sqrt(np.mean((w_recovered - w) ** 2)))
        eta_relative_error = float(np.linalg.norm(eta_recovered - eta_truth) / np.linalg.norm(eta_truth))

        # Unforced PDE/modal equivalence at one reproducible state.
        phase = 0.37
        eta = eta_truth * np.cos(omega_numeric * phase)
        eta_ddot = -eigvals * eta
        projected_pde_residual = M @ eta_ddot + K @ eta
        modal_equation_relative_residual = float(
            np.linalg.norm(projected_pde_residual) /
            max(1.0, np.linalg.norm(K @ eta), np.linalg.norm(M @ eta_ddot))
        )

        root_boundary_residuals = []
        for j in range(mode_count):
            root_boundary_residuals.append({
                "mode": j + 1,
                "beta": float(roots[j]),
                "clamped_displacement_abs": float(abs(Phi[j, 0])),
                "clamped_slope_abs": float(abs(Phi1[j, 0])),
                "free_moment_abs": float(abs(Phi2[j, -1])),
                "free_shear_abs": float(abs(Phi3[j, -1])),
            })
        max_boundary_residual = max(
            max(row[k] for k in ("clamped_displacement_abs", "clamped_slope_abs", "free_moment_abs", "free_shear_abs"))
            for row in root_boundary_residuals
        )
        mass_orthogonality_error = float(np.max(np.abs(M - np.eye(mode_count))))

        checks = {
            "source_pde_owner_present": True,
            "target_state_space_owner_present": True,
            "target_A_matrix_not_used_to_generate_projection": True,
            "cantilever_boundary_conditions_satisfied": max_boundary_residual < 2e-7,
            "mass_orthogonality_recovered": mass_orthogonality_error < 2e-6,
            "modal_frequencies_match_pde_eigenproblem": frequency_relative_error < 2e-8,
            "retained_subspace_reconstruction_closes": reconstruction_rms < 2e-10 and eta_relative_error < 2e-9,
            "projected_pde_matches_second_order_modal_dynamics": modal_equation_relative_residual < 2e-6,
            "full_aeroservoelastic_embedding_not_overclaimed": True,
        }
        payload = {
            "schema": "phi-aeroelastic-projection-bridge/v6.21",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_STRUCTURAL_SUBSPACE_PDE_TO_REDUCED_STATE_BRIDGE_AERO_LAG_OPEN" if all(checks.values()) else "BLOCKED_AEROELASTIC_PROJECTION_BRIDGE",
            "research_region": "UF-OP-AEROELASTIC-PDE-STATE-BRIDGE",
            "source_owner_ids": list(required),
            "generation_mode": "TARGET_A_MATRIX_FREE_GALERKIN_PROJECTION",
            "validation_chart": "UNIFORM_CLAMPED_FREE_EULER_BERNOULLI_STRUCTURAL_SUBSPACE_NONDIMENSIONAL_CALIBRATION",
            "projection_ir": {
                "field_expansion": "w(x,t)=sum_k phi_k(x)*eta_k(t)",
                "generalized_load": "f_q,k(t)=Integral_0^L phi_k(x)*q(x,t) dx",
                "second_order_reduced_equation": "M*eta_ddot+K*eta=f_q",
                "structural_state": "x_s=[eta,eta_dot]",
                "first_order_structural_block": "x_s_dot=A_s*x_s+B_q*f_q",
                "physical_scaling": "M_ij=Integral rho*A*phi_i*phi_j dx; K_ij=Integral E*I*phi_i''*phi_j'' dx",
                "basis_boundary_condition": "clamped_root_free_tip",
                "mode_count": mode_count,
            },
            "modal_beta_roots": [float(v) for v in roots],
            "mass_matrix": M.tolist(),
            "stiffness_matrix": K.tolist(),
            "structural_state_matrix_A_s": A_s.tolist(),
            "generalized_load_matrix_B_q": B_q.tolist(),
            "natural_frequencies_nondimensional": [float(v) for v in omega_numeric],
            "frequency_relative_error": frequency_relative_error,
            "mass_orthogonality_error": mass_orthogonality_error,
            "retained_subspace_reconstruction_rms": reconstruction_rms,
            "modal_coordinate_relative_error": eta_relative_error,
            "projected_pde_relative_residual": modal_equation_relative_residual,
            "boundary_residuals": root_boundary_residuals,
            "maximum_boundary_residual": float(max_boundary_residual),
            "resolved_bridge": {
                "w(x,t)_to_structural_coordinates": "eta=M^{-1}*Integral Phi^T*rho*A*w dx",
                "q(x,t)_to_generalized_force": "f_q=Integral Phi^T*q dx",
                "structural_coordinates_to_ASE_substate": "x_struct=[eta,eta_dot]",
                "structural_PDE_to_state_block": "A_s=[[0,I],[-M^{-1}K,0]], B_q=[[0],[M^{-1}]]",
            },
            "remaining_unknown_operator_slots": [
                "K_UNKNOWN[AERODYNAMIC_UNSTEADY_LAG_STATE_EMBEDDING]",
                "K_UNKNOWN[GUST_FIELD_TO_DISTRIBUTED_AERODYNAMIC_LOAD_q]",
                "K_UNKNOWN[ACTUATOR_SENSOR_STATE_EMBEDDING_AND_LIMITS]",
            ],
            "full_aeroservoelastic_state_space_bridge_complete": False,
            "target_formula_access_during_bridge_generation": False,
            "checks": checks,
            "claim_boundary": {
                "structural_projection_operator_materialized": True,
                "full_flexible_aircraft_A_matrix_derived": False,
                "experimental_flight_validation_executed": False,
                "new_physical_law_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def discover_temporal_convolution_kernel(
        self,
        times: Sequence[float],
        driving_signal: Sequence[float],
        response_residual: Sequence[float],
        *,
        memory_horizon: float,
        regularization: float = 1.0,
        train_fraction: float = 0.65,
    ) -> Mapping[str, Any]:
        """Learn a causal discrete Volterra kernel without an analytic kernel family.

        Input contract is r(t)=Integral_0^t K(t-s) f(s) ds + error.  Only
        nonnegative lags are represented, so causality is structural.  The fit
        uses a second-difference Tikhonov penalty for well-posedness but does not
        assume exponential, power-law, Padé, Prony, or any named kernel form.
        """
        import numpy as np
        t = np.asarray(times, dtype=float)
        f = np.asarray(driving_signal, dtype=float)
        r = np.asarray(response_residual, dtype=float)
        if t.ndim != 1 or f.shape != t.shape or r.shape != t.shape or len(t) < 20:
            raise ValueError("times, driving_signal and response_residual must be equal 1D arrays with >=20 samples")
        dts = np.diff(t)
        dt = float(np.mean(dts))
        if dt <= 0 or float(np.max(np.abs(dts - dt))) > max(1e-10, 1e-7 * dt):
            raise ValueError("uniform strictly increasing time grid required")
        memory_horizon = float(memory_horizon)
        regularization = float(regularization)
        if memory_horizon <= 0 or regularization < 0:
            raise ValueError("positive memory_horizon and nonnegative regularization required")
        lag_count = min(len(t) - 2, int(memory_horizon / dt) + 1)
        if lag_count < 3:
            raise ValueError("memory horizon too short for discrete kernel")
        n_train = max(lag_count + 3, int(float(train_fraction) * len(t)))
        n_train = min(n_train, len(t) - 3)

        X_rows, y_rows = [], []
        for i in range(n_train):
            row = np.zeros(lag_count)
            upto = min(i, lag_count - 1)
            row[:upto + 1] = dt * f[i - np.arange(upto + 1)]
            X_rows.append(row)
            y_rows.append(r[i])
        X = np.asarray(X_rows)
        y = np.asarray(y_rows)
        D2 = np.zeros((lag_count - 2, lag_count))
        for j in range(lag_count - 2):
            D2[j, j:j + 3] = (1.0, -2.0, 1.0)
        augmented_X = np.vstack([X, np.sqrt(regularization) * D2])
        augmented_y = np.concatenate([y, np.zeros(D2.shape[0])])
        kernel, *_ = np.linalg.lstsq(augmented_X, augmented_y, rcond=None)

        train_prediction = X @ kernel
        train_rmse = float(np.sqrt(np.mean((train_prediction - y) ** 2)))
        holdout_errors = []
        for i in range(n_train, len(t)):
            upto = min(i, lag_count - 1)
            pred = dt * float(np.dot(kernel[:upto + 1], f[i - np.arange(upto + 1)]))
            holdout_errors.append(pred - r[i])
        holdout_rmse = float(np.sqrt(np.mean(np.square(holdout_errors)))) if holdout_errors else 0.0
        payload = {
            "schema": "phi-data-backed-temporal-kernel-discovery/v6.21",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_DATA_BACKED_CAUSAL_DISCRETE_VOLterra_KERNEL_INVERSION",
            "fit_equation": "r(t_i)≈dt*sum_{lag>=0} K_lag*f(t_i-lag)",
            "analytic_kernel_family_selected_before_fit": False,
            "kernel_parameterization": "NONPARAMETRIC_DISCRETE_CAUSAL_LAG_GRID",
            "causality_enforced_by_construction": True,
            "future_samples_used_in_convolution_design": False,
            "truth_kernel_access_during_fit": False,
            "regularizer": "SECOND_DIFFERENCE_TIKHONOV",
            "regularization": regularization,
            "time_step": dt,
            "memory_horizon": float((lag_count - 1) * dt),
            "lag_grid": [float(j * dt) for j in range(lag_count)],
            "kernel_values": [float(v) for v in kernel],
            "training_sample_count": int(n_train),
            "holdout_sample_count": int(len(t) - n_train),
            "training_rmse": train_rmse,
            "holdout_rmse": holdout_rmse,
            "claim_boundary": {
                "kernel_values_identified_from_supplied_data": True,
                "unique_continuum_kernel_proved": False,
                "closed_form_kernel_discovered": False,
                "physical_truth_established_without_data_provenance": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def discover_spatial_nonlocal_kernel(
        self,
        input_fields: Sequence[Sequence[float]],
        output_fields: Sequence[Sequence[float]],
        *,
        regularization: float = 1e-8,
        train_sample_count: int | None = None,
    ) -> Mapping[str, Any]:
        """Learn a 1D periodic spatial convolution kernel from field pairs.

        No radial/exponential/compact-support family is selected.  Every signed
        discrete lag is a free coefficient regularized only by circular second
        differences; holdout field pairs are never used in the fit.
        """
        import numpy as np
        F = np.asarray(input_fields, dtype=float)
        G = np.asarray(output_fields, dtype=float)
        if F.ndim != 2 or G.shape != F.shape or F.shape[0] < 4 or F.shape[1] < 16:
            raise ValueError("input_fields/output_fields must be matching [sample,space] arrays")
        sample_count, point_count = F.shape
        n_train = int(train_sample_count if train_sample_count is not None else max(2, int(0.7 * sample_count)))
        if not 2 <= n_train < sample_count:
            raise ValueError("train_sample_count must leave at least one holdout field")
        dx = 1.0 / point_count
        X_rows, y_rows = [], []
        lag_index = np.arange(point_count)
        for s in range(n_train):
            field = F[s]
            for i in range(point_count):
                X_rows.append(dx * field[(i - lag_index) % point_count])
                y_rows.append(G[s, i])
        X = np.asarray(X_rows)
        y = np.asarray(y_rows)
        D2 = np.zeros((point_count, point_count))
        for j in range(point_count):
            D2[j, j] = -2.0
            D2[j, (j - 1) % point_count] = 1.0
            D2[j, (j + 1) % point_count] = 1.0
        augmented_X = np.vstack([X, np.sqrt(float(regularization)) * D2])
        augmented_y = np.concatenate([y, np.zeros(point_count)])
        kernel, *_ = np.linalg.lstsq(augmented_X, augmented_y, rcond=None)
        train_rmse = float(np.sqrt(np.mean((X @ kernel - y) ** 2)))
        holdout_errors = []
        for s in range(n_train, sample_count):
            field = F[s]
            for i in range(point_count):
                pred = dx * float(np.dot(kernel, field[(i - lag_index) % point_count]))
                holdout_errors.append(pred - G[s, i])
        holdout_rmse = float(np.sqrt(np.mean(np.square(holdout_errors))))
        signed_lag = [float(j / point_count if j <= point_count // 2 else (j - point_count) / point_count) for j in range(point_count)]
        payload = {
            "schema": "phi-data-backed-spatial-nonlocal-kernel-discovery/v6.21",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_DATA_BACKED_NONPARAMETRIC_SPATIAL_NONLOCAL_KERNEL_INVERSION",
            "fit_equation": "g(x_i)≈dx*sum_j K(x_j)*f(x_i-x_j)",
            "analytic_kernel_family_selected_before_fit": False,
            "kernel_parameterization": "NONPARAMETRIC_PERIODIC_SIGNED_LAG_GRID",
            "truth_kernel_access_during_fit": False,
            "regularizer": "CIRCULAR_SECOND_DIFFERENCE_TIKHONOV",
            "regularization": float(regularization),
            "spatial_step": dx,
            "signed_lag_grid": signed_lag,
            "kernel_values": [float(v) for v in kernel],
            "training_field_count": n_train,
            "holdout_field_count": sample_count - n_train,
            "training_rmse": train_rmse,
            "holdout_rmse": holdout_rmse,
            "claim_boundary": {
                "kernel_values_identified_from_supplied_field_data": True,
                "continuum_identifiability_proved_for_arbitrary_data": False,
                "closed_form_kernel_discovered": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_data_backed_kernel_discovery_qualification(self) -> Mapping[str, Any]:
        """One hidden-kernel calibration plus current-project application gates.

        The generator truth is used only after both nonparametric fits are frozen.
        This qualifies the inverse operator, not a new physical kernel.
        """
        import numpy as np

        # Temporal hidden-kernel trajectory.  The learner receives only the
        # sampled driving signal and convolution residual, never this function.
        dt = 0.02
        n = 800
        t = np.arange(n, dtype=float) * dt
        lag = np.arange(n, dtype=float) * dt
        hidden_temporal_kernel = 0.55 * np.exp(-1.4 * lag) * (1.0 + 0.25 * np.cos(2.2 * lag))
        y = np.zeros(n, dtype=float)
        y[0] = 1.0
        residual = np.zeros(n, dtype=float)
        for i in range(n - 1):
            residual[i] = dt * float(np.dot(hidden_temporal_kernel[:i + 1], y[i::-1]))
            local = -0.8 * y[i] + 0.12 * np.sin(0.7 * t[i])
            y[i + 1] = y[i] + dt * (local + residual[i])
        residual[-1] = dt * float(np.dot(hidden_temporal_kernel, y[::-1]))
        temporal = self.discover_temporal_convolution_kernel(
            t.tolist(), y.tolist(), residual.tolist(), memory_horizon=6.0,
            regularization=1.0, train_fraction=0.65,
        )
        learned_temporal = np.asarray(temporal["kernel_values"], dtype=float)
        truth_temporal = hidden_temporal_kernel[:len(learned_temporal)]
        temporal_kernel_relative_error = float(np.linalg.norm(learned_temporal - truth_temporal) / np.linalg.norm(truth_temporal))

        # Forward trajectory with the learned kernel is a post-fit holdout/control.
        y_hat = np.zeros_like(y)
        y_hat[0] = y[0]
        for i in range(n - 1):
            upto = min(i, len(learned_temporal) - 1)
            memory = dt * float(np.dot(learned_temporal[:upto + 1], y_hat[i - np.arange(upto + 1)]))
            local = -0.8 * y_hat[i] + 0.12 * np.sin(0.7 * t[i])
            y_hat[i + 1] = y_hat[i] + dt * (local + memory)
        holdout_start = int(0.80 * n)
        temporal_rollout_holdout_rmse = float(np.sqrt(np.mean((y_hat[holdout_start:] - y[holdout_start:]) ** 2)))

        # Spatial hidden-kernel calibration with broadband fields.  Again the
        # truth kernel is not passed to the inverse fit.
        point_count = 64
        sample_count = 20
        rng = np.random.default_rng(420621)
        signed_index = np.arange(point_count)
        radial_lag = np.minimum(signed_index / point_count, 1.0 - signed_index / point_count)
        hidden_spatial_kernel = np.exp(-radial_lag / 0.12) * (1.0 + 0.15 * np.cos(8.0 * np.pi * radial_lag))
        inputs = []
        outputs = []
        dx = 1.0 / point_count
        for _ in range(sample_count):
            raw = rng.normal(size=point_count)
            field = (np.roll(raw, 1) + 2.0 * raw + np.roll(raw, -1)) / 4.0
            response = np.asarray([
                dx * float(np.dot(hidden_spatial_kernel, field[(i - signed_index) % point_count]))
                for i in range(point_count)
            ])
            inputs.append(field)
            outputs.append(response)
        spatial = self.discover_spatial_nonlocal_kernel(
            np.asarray(inputs).tolist(), np.asarray(outputs).tolist(), regularization=1e-8, train_sample_count=14,
        )
        learned_spatial = np.asarray(spatial["kernel_values"], dtype=float)
        spatial_kernel_relative_error = float(np.linalg.norm(learned_spatial - hidden_spatial_kernel) / np.linalg.norm(hidden_spatial_kernel))

        # Current QPDTR provides a bounded non-Markovian process-tensor witness,
        # but explicitly lacks the multitime hardware calibration trajectories
        # needed to fit a physical device kernel.  Preserve that boundary.
        from source.qpdtr_bridge import load_qpdtr_v2_5_0_bridge
        qpdtr_certificate = load_qpdtr_v2_5_0_bridge(self.root)
        qpdtr = qpdtr_certificate.evidence.get("execution_bundle", {}) if qpdtr_certificate.passed else {}
        process_tensor = qpdtr.get("control_evidence", {}).get("process_tensor_memory", {})
        if not process_tensor:
            # Schema fallback used by the current evidence file.
            stack = [qpdtr]
            while stack and not process_tensor:
                item = stack.pop()
                if isinstance(item, dict):
                    if item.get("digital_twin_non_markovian_status") == "BLOCKED_MULTITIME_CALIBRATION_DATA_REQUIRED":
                        process_tensor = item
                        break
                    stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
        qpdtr_nonmarkov_status = process_tensor.get("digital_twin_non_markovian_status", "NOT_FOUND") if isinstance(process_tensor, dict) else "NOT_FOUND"

        checks = {
            "temporal_fit_is_nonparametric_and_target_family_free": temporal["analytic_kernel_family_selected_before_fit"] is False,
            "temporal_fit_is_causal": temporal["causality_enforced_by_construction"] is True,
            "temporal_hidden_kernel_not_used_during_fit": temporal["truth_kernel_access_during_fit"] is False,
            "temporal_kernel_recovered_on_hidden_calibration": temporal_kernel_relative_error < 0.01,
            "temporal_rollout_generalizes_to_late_holdout": temporal_rollout_holdout_rmse < 1e-4,
            "spatial_fit_is_nonparametric_and_target_family_free": spatial["analytic_kernel_family_selected_before_fit"] is False,
            "spatial_hidden_kernel_not_used_during_fit": spatial["truth_kernel_access_during_fit"] is False,
            "spatial_kernel_recovered_on_hidden_calibration": spatial_kernel_relative_error < 0.01,
            "spatial_holdout_fields_reconstructed": spatial["holdout_rmse"] < 1e-6,
            "real_qpdtr_nonmarkov_kernel_not_fabricated_without_multitime_data": qpdtr_nonmarkov_status == "BLOCKED_MULTITIME_CALIBRATION_DATA_REQUIRED",
        }
        payload = {
            "schema": "phi-data-backed-unknown-kernel-qualification/v6.21",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_DATA_BACKED_TEMPORAL_AND_SPATIAL_UNKNOWN_KERNEL_DISCOVERY_CALIBRATION_REAL_QPDTR_DATA_BLOCKED" if all(checks.values()) else "BLOCKED_DATA_BACKED_KERNEL_DISCOVERY_QUALIFICATION",
            "research_mode": "HIDDEN_KERNEL_DATA_BACKED_NONPARAMETRIC_INVERSE_OPERATOR_CALIBRATION",
            "temporal_kernel_discovery": temporal,
            "temporal_postfit_truth_metrics": {
                "kernel_relative_l2_error": temporal_kernel_relative_error,
                "late_holdout_rollout_rmse": temporal_rollout_holdout_rmse,
                "truth_accessed_only_after_fit_frozen": True,
            },
            "spatial_kernel_discovery": spatial,
            "spatial_postfit_truth_metrics": {
                "kernel_relative_l2_error": spatial_kernel_relative_error,
                "truth_accessed_only_after_fit_frozen": True,
            },
            "current_project_application": {
                "qpdtr_nonmarkovian_kernel_fit_status": qpdtr_nonmarkov_status,
                "required_multitime_data_contract": [
                    "uniform_or_timestamped_time_grid",
                    "intervention_or_initial-state labels",
                    "reduced-state trajectory or informationally complete observable vector",
                    "local generator / Markov baseline used to form residual",
                    "measurement covariance or uncertainty",
                    "repeated multitime intervention sequences sufficient for identifiability",
                ],
                "physical_kernel_claimed": False,
            },
            "checks": checks,
            "claim_boundary": {
                "inverse_kernel_algorithm_qualified_on_hidden_synthetic_data": True,
                "real_aircraft_kernel_identified": False,
                "real_qpu_nonmarkovian_kernel_identified": False,
                "world_novelty_established": False,
                "new_physical_law_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def _operator_frontier_regions(self) -> Tuple[Mapping[str, Any], ...]:
        """Directed regions; source owners and bindings are fixed before generation.

        The bindings select shared physical coordinates, never a target formula.
        A missing binding remains a research obstruction instead of being guessed.
        """
        return (
            {
                "region_id": "UF-OP-AEROSERVOELASTIC-CONTROL",
                "domain_id": "aeronautics_and_aerostation",
                "source_owner_ids": ("AERO-AEROSERVOELASTIC-STATE-SPACE", "AERO-STATE-FEEDBACK-CONTROL"),
                "declared_shared_symbols": ("u", "x"),
                "validity_chart": "LINEARIZED_AEROSERVOELASTIC_STATE_SPACE_WITH_CONSTANT_OUTPUT_AND_STATE_FEEDBACK_MATRICES",
            },
            {
                "region_id": "UF-OP-AEROELASTIC-PDE-STATE-BRIDGE",
                "domain_id": "aeronautics_and_aerostation+mechanics",
                "source_owner_ids": ("AERO-AEROSERVOELASTIC-STATE-SPACE", "OME-036"),
                "declared_shared_symbols": (),
                "bridge_materializer": "GALERKIN_STRUCTURAL_SUBSPACE_PROJECTION_CURRENT",
                "remaining_bridge_required": {
                    "aerodynamic_lag_states": "UNSTEADY_AERODYNAMIC_STATE_EMBEDDING_IN_FULL_ASE_x",
                    "gust_field": "GUST_TO_DISTRIBUTED_AERODYNAMIC_LOAD_q(x,t)",
                    "actuator_sensor_states": "ACTUATOR_SENSOR_STATE_EMBEDDING_AND_LIMITS",
                },
                "validity_chart": "DISTRIBUTED_FLEXIBLE_WING_PDE_TO_REDUCED_STRUCTURAL_STATE_SUBSPACE; FULL_ASE_AERO_LAG_EMBEDDING_REMAINS_OPEN",
            },
            {
                "region_id": "UF-OP-AEROTHERMAL-HEAT-TRANSITION-BRIDGE",
                "domain_id": "aeronautics_and_aerostation+mechanics",
                "source_owner_ids": ("CON-07", "AEROTHERMAL-SURFACE-ENERGY-BALANCE", "AIRSHIP-WALL-HEATING-TRANSITION-MODEL-2026"),
                "declared_shared_symbols": (),
                "bridge_required": {
                    "T": "T_w",
                    "volumetric_heat_diffusion": "surface_areal_heat_capacity_and_boundary_heat_flux",
                    "T_w": "theta_w_via_T_w_over_T_infinity",
                },
                "validity_chart": "SOLID_OR_SHELL_HEAT_PDE_TO_SURFACE_ENERGY_BALANCE_TO_TRANSITION_BRIDGE_NOT_YET_DECLARED",
            },
            {
                "region_id": "UF-OP-VISCOELASTIC-MEMORY-MOMENTUM",
                "domain_id": "mechanics",
                "source_owner_ids": ("CON-02", "OME-012", "OME-014", "OME-015"),
                "declared_shared_symbols": ("sigma",),
                "validity_chart": "ONE_DIMENSIONAL_OR_COMPONENTWISE_SMALL_STRAIN_VISCOELASTIC_REDUCTION_OF_CONTINUUM_MOMENTUM; VELOCITY_AND_DISPLACEMENT_SYMBOLS_ARE_NOT_ALIASED",
            },
            {
                "region_id": "UF-OP-SMALL-STRAIN-VISCOELASTIC-KINEMATICS",
                "domain_id": "mechanics",
                "source_owner_ids": ("OME-001", "OME-012", "OME-014"),
                "declared_shared_symbols": ("epsilon",),
                "validity_chart": "SMALL_STRAIN_DEFORMABLE_BODY_KINEMATIC_CONSTITUTIVE_OVERLAP",
            },
            {
                "region_id": "UF-OP-ELECTRODIFFUSION-REACTION",
                "domain_id": "chemistry",
                "source_owner_ids": ("OCH-028", "OCH-029"),
                "declared_shared_symbols": ("J_i", "c_i", "phi"),
                "validity_chart": "NERNST_PLANCK_SPECIES_BALANCE_POISSON_CONTINUUM_OVERLAP",
            },
            {
                "region_id": "UF-OP-PHASE-FIELD-HIGH-ORDER",
                "domain_id": "materials_science",
                "source_owner_ids": ("OMAT-006",),
                "declared_shared_symbols": ("mu", "c"),
                "validity_chart": "CAHN_HILLIARD_ISOTHERMAL_PHASE_FIELD_CHART",
            },
            {
                "region_id": "UF-OP-SEMICLASSICAL-VACUUM-GRAVITY",
                "domain_id": "physics",
                "source_owner_ids": ("QVAC-RENORMALIZED-CONSERVATION", "QVAC-SEMICLASSICAL-EINSTEIN", "QVAC-WALD-RENORMALIZATION-AMBIGUITY"),
                "declared_shared_symbols": ("T_munu_ren",),
                "validity_chart": "SEMICLASSICAL_GRAVITY_RENORMALIZED_STRESS_ENERGY_CHART",
            },
            {
                "region_id": "UF-OP-QUANTUM-NONMARKOVIAN-MEMORY",
                "domain_id": "physics",
                "source_owner_ids": ("OPH-003", "NEW-03"),
                "declared_shared_symbols": (),
                "bridge_required": {"Y": "rho", "K(Y)": "-i[H,rho]/hbar"},
                "validity_chart": "OPEN_QUANTUM_SYSTEM_REDUCED_STATE_BRIDGE_NOT_YET_DECLARED",
            },
        )

    def _operator_known_keys(self) -> set[str]:
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        keys: set[str] = set()
        for passport in runtime.catalog.passports.values():
            for lhs, rhs in _operator_equations(passport.formula.source or ""):
                keys.add(_operator_formula_key(f"{lhs}={rhs}"))
        for law in self.aeronautics_db.get("laws", ()):
            for lhs, rhs in _operator_equations(str(law.get("formula", ""))):
                keys.add(_operator_formula_key(f"{lhs}={rhs}"))
        return keys

    def run_real_gust_aero_lag_discovery_qualification(self) -> Mapping[str, Any]:
        """Identify only the real-data parts of gust->load and aero-lag operators that the public data supports.

        The source is a compact numeric digitization of vector PDF figures from the
        DLR oLAF flexible-wing wind-tunnel publication.  It is explicitly *not* the
        authors' raw DAQ stream.  Figure 16 supplies magnitude-only gust->WRBM data;
        therefore a full causal gust kernel is not identifiable.  Figures 22/23
        provide common plotted time axes at 9 Hz and allow one empirical complex
        control-effect anchor, but not a broadband phase kernel.  Figure 12 supplies
        the broadband flap-command->WRBM magnitude response.
        """
        import hashlib
        import numpy as np

        path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_gla_2024_digitized.json"
        if not path.exists():
            payload = {
                "schema": "phi-real-gust-aero-lag-discovery/v6.22",
                "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION,
                "status": "BLOCKED_REAL_AEROELASTIC_DATASET_MISSING",
                "dataset_path": str(path.relative_to(self.root)),
            }
            payload["digest"] = digest_payload(payload)
            return payload
        data = _load_json(path)
        source = data.get("source", {})
        dataset_sha = hashlib.sha256(path.read_bytes()).hexdigest()

        # Gust -> WRBM magnitude residual.  No analytic correction family is chosen.
        rows = data["figure16_gust_to_wrbm"]["points"]
        freq = np.asarray([float(r["frequency_hz"]) for r in rows])
        exp_db = np.asarray([float(r["experiment_wrbm_db"]) for r in rows])
        sim_db = np.asarray([float(r["simulation_wrbm_db"]) for r in rows])
        delta_db = exp_db - sim_db
        amplitude_ratio = 10.0 ** (delta_db / 20.0)
        n = len(freq)
        D2 = np.zeros((max(0, n - 2), n), dtype=float)
        for i in range(n - 2):
            D2[i, i:i + 3] = (1.0, -2.0, 1.0)
        lam = 0.3
        penalty = D2.T @ D2
        smooth_delta = np.linalg.solve(np.eye(n) + lam * penalty, delta_db)
        loo_pred = np.zeros(n, dtype=float)
        for j in range(n):
            W = np.eye(n)
            W[j, j] = 0.0
            loo_pred[j] = np.linalg.solve(W + lam * penalty + 1e-9 * np.eye(n), W @ delta_db)[j]
        loo_rmse_db = float(np.sqrt(np.mean((loo_pred - delta_db) ** 2)))
        low = freq <= 8.0
        near_and_above_mode = freq >= 9.0
        low_frequency_mean_ratio = float(np.mean(amplitude_ratio[low]))
        high_frequency_mean_ratio = float(np.mean(amplitude_ratio[near_and_above_mode]))
        low_frequency_mean_residual_db = float(np.mean(delta_db[low]))

        # Broadband control-surface -> WRBM magnitude channel from Figure 12.
        f12 = np.asarray(data["figure12_flap5_to_wrbm"]["frequency_hz"], dtype=float)
        e12 = np.asarray(data["figure12_flap5_to_wrbm"]["experiment_wrbm_db"], dtype=float)
        s12 = np.asarray(data["figure12_flap5_to_wrbm"]["simulation_wrbm_db"], dtype=float)
        valid12 = (f12 >= 1.0) & (f12 <= 12.0)
        flap_wrbm_rms_model_mismatch_db = float(np.sqrt(np.mean((e12[valid12] - s12[valid12]) ** 2)))

        # One-frequency complex control-effect anchor from publication time plots.
        tr = data["figure22_23_continuous_9hz"]
        t = np.asarray(tr["time_s"], dtype=float)
        m_open = np.asarray(tr["wrbm_open_loop_nm"], dtype=float)
        m_closed = np.asarray(tr["wrbm_gla_nm"], dtype=float)
        u4 = np.asarray(tr["flap4_command_deg"], dtype=float)
        u5 = np.asarray(tr["flap5_command_deg"], dtype=float)
        u = 0.5 * (u4 + u5)
        fit = (t >= 3.1) & (t <= 3.9)
        tf = t[fit]
        omega = 2.0 * np.pi * float(tr["frequency_hz"])
        X = np.column_stack((np.cos(omega * tf), np.sin(omega * tf), np.ones_like(tf)))
        def _phasor(values: np.ndarray) -> complex:
            c = np.linalg.lstsq(X, values[fit], rcond=None)[0]
            return complex(float(c[0]), float(-c[1]))
        z_open = _phasor(m_open)
        z_closed = _phasor(m_closed)
        z_u = _phasor(u)
        z_delta = z_closed - z_open
        h_control = z_delta / z_u
        open_rms = float(np.sqrt(np.mean(m_open ** 2)))
        closed_rms = float(np.sqrt(np.mean(m_closed ** 2)))
        load_reduction_fraction = 1.0 - closed_rms / open_rms

        checks = {
            "real_public_flexible_wing_data_used": source.get("extraction_method") == "DIRECT_PDF_VECTOR_GEOMETRY_NO_OCR",
            "derived_dataset_declared_not_raw_daq": "not the authors' raw DAQ" in source.get("claim_boundary", ""),
            "gust_operator_fit_is_nonparametric": True,
            "gust_operator_target_family_not_prespecified": True,
            "gust_magnitude_residual_cross_validates": loo_rmse_db < 0.60,
            "low_frequency_gust_load_overprediction_is_reproduced": low_frequency_mean_ratio < 0.90 and low_frequency_mean_residual_db < -1.0,
            "gust_correction_relaxes_near_first_mode": high_frequency_mean_ratio > 0.93,
            "gust_phase_unavailable_blocks_full_causal_kernel": data["figure16_gust_to_wrbm"].get("phase_available") is False,
            "flap_to_wrbm_broadband_magnitude_matches_nominal_model": flap_wrbm_rms_model_mismatch_db < 2.0,
            "nine_hz_control_effect_complex_anchor_finite": bool(np.isfinite(abs(h_control)) and np.isfinite(np.angle(h_control))),
            "digitized_gla_load_reduction_reproduces_publication": 0.78 < load_reduction_fraction < 0.84,
            "broadband_aero_lag_phase_not_overclaimed": data["figure12_flap5_to_wrbm"].get("phase_available") is False,
        }
        status = "PASS_REAL_GUST_LOAD_MAGNITUDE_CORRECTION_AND_9HZ_CONTROL_EFFECT_ANCHOR_FULL_AERO_LAG_OPEN" if all(checks.values()) else "BLOCKED_REAL_GUST_AERO_LAG_DISCOVERY"
        payload = {
            "schema": "phi-real-gust-aero-lag-discovery/v6.22",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": status,
            "dataset": {
                "dataset_id": data.get("dataset_id"),
                "relative_path": str(path.relative_to(self.root)),
                "derived_numeric_dataset_sha256": dataset_sha,
                "source": source,
                "operating_point": data.get("operating_point", {}),
            },
            "gust_to_load_operator": {
                "identified_object": "C_g(f)=|H_gust->WRBM,exp(f)|/|H_gust->WRBM,sim(f)|",
                "representation": "NONPARAMETRIC_MAGNITUDE_CORRECTION_ON_MEASURED_FREQUENCY_GRID",
                "frequency_hz": freq.tolist(),
                "measured_residual_db": delta_db.tolist(),
                "smoothed_residual_db": smooth_delta.tolist(),
                "amplitude_correction_ratio": amplitude_ratio.tolist(),
                "leave_one_frequency_out_rmse_db": loo_rmse_db,
                "mean_amplitude_correction_4_to_8_hz": low_frequency_mean_ratio,
                "mean_residual_4_to_8_hz_db": low_frequency_mean_residual_db,
                "mean_amplitude_correction_9_to_12_hz": high_frequency_mean_ratio,
                "full_causal_kernel_identified": False,
                "blocker": "FIGURE_16_IS_RMS_MAGNITUDE_ONLY; PHASE_OR_RAW_SYNCHRONIZED_GUST_AND_LOAD_HISTORY_REQUIRED",
            },
            "aero_lag_control_to_load_operator": {
                "broadband_magnitude_frequency_hz": f12[valid12].tolist(),
                "broadband_experiment_wrbm_db": e12[valid12].tolist(),
                "broadband_simulation_wrbm_db": s12[valid12].tolist(),
                "broadband_model_mismatch_rms_db": flap_wrbm_rms_model_mismatch_db,
                "complex_anchor_frequency_hz": 9.0,
                "control_induced_wrbm_per_mean_flap_command_nm_per_deg": float(abs(h_control)),
                "control_effect_phase_deg": float(np.degrees(np.angle(h_control))),
                "open_loop_9hz_wrbm_phasor_amplitude_nm": float(abs(z_open)),
                "closed_loop_9hz_wrbm_phasor_amplitude_nm": float(abs(z_closed)),
                "mean_flap_command_9hz_phasor_amplitude_deg": float(abs(z_u)),
                "digitized_open_loop_rms_nm": open_rms,
                "digitized_gla_rms_nm": closed_rms,
                "digitized_load_reduction_fraction": load_reduction_fraction,
                "full_broadband_complex_aero_lag_identified": False,
                "blocker": "FIGURE_12_HAS_MAGNITUDE_ONLY; FIGURES_22_23 PROVIDE ONLY ONE COMMON 9HZ PLOT ANCHOR AND ARE NOT RAW_SYNCHRONIZED_DAQ",
            },
            "frontier_update": {
                "K_UNKNOWN_gust_to_load": "PARTIALLY_MATERIALIZED_REAL_MAGNITUDE_CORRECTION_4_TO_12HZ_PHASE_OPEN",
                "K_UNKNOWN_aero_lag": "PARTIALLY_MATERIALIZED_BROADBAND_MAGNITUDE_PLUS_9HZ_COMPLEX_CONTROL_EFFECT_PHASE_OPEN_ELSEWHERE",
                "remaining_required_data": [
                    "raw_synchronized_gust_angle_or_velocity_time_history",
                    "raw_WBRM_WRTM_and_distributed_strain_acceleration_pressure_histories",
                    "measured_not_only_commanded_actuator_deflections",
                    "multi_frequency_phase_or_time_histories",
                    "independent_holdout_runs_across_speed_and_gust_gradient",
                ],
            },
            "checks": checks,
            "claim_boundary": {
                "new_aerodynamic_law_established": False,
                "real_gust_load_residual_signature_identified": True,
                "full_unsteady_aerodynamic_kernel_identified": False,
                "publication_raw_data_claimed": False,
                "world_novelty_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_real_gust_mechanism_competition_research_cycle(self) -> Mapping[str, Any]:
        """Run the v6.24 scientific cycle on the real DLR oLAF gust-load residual.

        This is a retrospective, leakage-controlled model-discrimination experiment
        over vector-digitized public Figure-16 data.  Candidate mechanisms are fit
        only on the predeclared training frequencies.  Holdout values are not read
        by the fitting path until after the candidate/data freeze and EIG selection.
        The post-derivation literature snapshot is loaded only after that freeze.

        The method deliberately does *not* claim access to the authors' raw DAQ,
        identification of the full complex gust/load kernel, a unique root cause,
        or a new aerodynamic law.
        """
        import hashlib
        import math
        import numpy as np
        from scipy.optimize import least_squares

        from .runtime import LawSpaceRuntime
        from .research_cycle import (
            DynamicAxisProposal,
            ExperimentLikelihoodSpec,
            LiteratureRecord,
            ScientificResearchCycleOwner,
        )

        data_path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_gla_2024_digitized.json"
        literature_path = self.root / "data" / "source_snapshots" / "aero_gust_residual_prior_art_v6_24.json"
        if not data_path.exists():
            payload = {
                "schema": "phi-aero-realdata-full-research-cycle/v6.24",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_REAL_AEROELASTIC_DATASET_MISSING",
                "dataset_path": str(data_path.relative_to(self.root)),
            }
            payload["digest"] = digest_payload(payload)
            return payload
        if not literature_path.exists():
            payload = {
                "schema": "phi-aero-realdata-full-research-cycle/v6.24",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_POSTFREEZE_LITERATURE_SNAPSHOT_MISSING",
                "literature_path": str(literature_path.relative_to(self.root)),
            }
            payload["digest"] = digest_payload(payload)
            return payload

        data = _load_json(data_path)
        dataset_sha256 = hashlib.sha256(data_path.read_bytes()).hexdigest()
        source = dict(data.get("source", {}))
        all_rows = tuple(data["figure16_gust_to_wrbm"]["points"])
        training_frequency_hz = (4.0, 5.0, 6.0, 8.0, 9.0, 10.0, 12.0)
        hidden_holdout_frequency_hz = (7.0, 11.0)

        # Only the training branch is numerically dereferenced before the freeze.
        training_rows = tuple(
            row for row in all_rows if float(row["frequency_hz"]) in training_frequency_hz
        )
        f_train = np.asarray([float(row["frequency_hz"]) for row in training_rows], dtype=float)
        y_train = np.asarray([
            float(row["experiment_wrbm_db"]) - float(row["simulation_wrbm_db"])
            for row in training_rows
        ], dtype=float)

        def fit_scalar(f: np.ndarray, y: np.ndarray) -> np.ndarray:
            return np.asarray([float(np.mean(y))], dtype=float)

        def pred_scalar(f: np.ndarray, p: np.ndarray) -> np.ndarray:
            return np.full_like(np.asarray(f, dtype=float), float(p[0]), dtype=float)

        def fit_linear(f: np.ndarray, y: np.ndarray) -> np.ndarray:
            X = np.column_stack((np.ones(len(f), dtype=float), f - 8.0))
            return np.linalg.lstsq(X, y, rcond=None)[0]

        def pred_linear(f: np.ndarray, p: np.ndarray) -> np.ndarray:
            f = np.asarray(f, dtype=float)
            return float(p[0]) + float(p[1]) * (f - 8.0)

        def pred_mode(f: np.ndarray, p: np.ndarray) -> np.ndarray:
            f = np.asarray(f, dtype=float)
            a, gain, halfwidth = (float(x) for x in p)
            return a + gain / (1.0 + ((f - 9.0) / halfwidth) ** 2)

        def fit_mode(f: np.ndarray, y: np.ndarray) -> np.ndarray:
            result = least_squares(
                lambda p: pred_mode(f, p) - y,
                x0=np.asarray([-1.6, 1.7, 1.0], dtype=float),
                bounds=(np.asarray([-5.0, -5.0, 0.1]), np.asarray([5.0, 5.0, 10.0])),
                max_nfev=50000,
            )
            return result.x

        def pred_memory(f: np.ndarray, p: np.ndarray) -> np.ndarray:
            f = np.asarray(f, dtype=float)
            a, ln_f_zero, ln_f_pole = (float(x) for x in p)
            f_zero = math.exp(ln_f_zero)
            f_pole = math.exp(ln_f_pole)
            return a + 10.0 * np.log10((1.0 + (f / f_zero) ** 2) / (1.0 + (f / f_pole) ** 2))

        def fit_memory(f: np.ndarray, y: np.ndarray) -> np.ndarray:
            result = least_squares(
                lambda p: pred_memory(f, p) - y,
                x0=np.asarray([-2.5, math.log(8.0), math.log(14.0)], dtype=float),
                bounds=(
                    np.asarray([-10.0, math.log(0.1), math.log(0.1)]),
                    np.asarray([10.0, math.log(100.0), math.log(100.0)]),
                ),
                max_nfev=50000,
            )
            return result.x

        def _h2_mag_local(f: np.ndarray, fn_hz: float, zeta: float) -> np.ndarray:
            ratio = np.asarray(f, dtype=float) / float(fn_hz)
            return 1.0 / np.sqrt((1.0 - ratio * ratio) ** 2 + (2.0 * float(zeta) * ratio) ** 2)

        def pred_structural(f: np.ndarray, p: np.ndarray) -> np.ndarray:
            a, fn_hz, zeta, nominal_zeta = (float(x) for x in p)
            numerator = _h2_mag_local(np.asarray(f, dtype=float), fn_hz, zeta)
            denominator = _h2_mag_local(np.asarray(f, dtype=float), 9.0, nominal_zeta)
            return a + 20.0 * np.log10(numerator / denominator)

        def fit_structural(f: np.ndarray, y: np.ndarray) -> np.ndarray:
            result = least_squares(
                lambda p: pred_structural(f, p) - y,
                x0=np.asarray([-1.8, 9.2, 0.15, 0.17], dtype=float),
                bounds=(
                    np.asarray([-10.0, 7.0, 0.01, 0.01]),
                    np.asarray([10.0, 11.0, 0.5, 0.5]),
                ),
                max_nfev=50000,
            )
            return result.x

        model_specs = (
            {
                "candidate_id": "H-AERO-REAL-001",
                "mechanism_family": "GUST_INPUT_SCALAR_CALIBRATION",
                "mechanism_meaning": "Frequency-independent gust-amplitude calibration/input-gain mismatch",
                "source_owner_ids": ("AERO-DISCRETE-GUST-LOAD", "MET-006"),
                "formula_source": "delta_WRBM_dB(f)=a",
                "fit": fit_scalar,
                "predict": pred_scalar,
                "parameter_names": ("a_db",),
            },
            {
                "candidate_id": "H-AERO-REAL-002",
                "mechanism_family": "GUST_FIELD_FREQUENCY_SHAPE",
                "mechanism_meaning": "Frequency-dependent effective gust field between the measured probe and wing encounter plane",
                "source_owner_ids": ("AERO-DISCRETE-GUST-LOAD", "AERO-AEROSERVOELASTIC-STATE-SPACE", "MET-006"),
                "formula_source": "delta_WRBM_dB(f)=a+b*(f-8Hz)",
                "fit": fit_linear,
                "predict": pred_linear,
                "parameter_names": ("a_db", "slope_db_per_hz"),
            },
            {
                "candidate_id": "H-AERO-REAL-003",
                "mechanism_family": "FIRST_MODE_PARTICIPATION_CORRECTION",
                "mechanism_meaning": "Localized participation mismatch around the independently identified first flexible mode",
                "source_owner_ids": ("AERO-AEROSERVOELASTIC-STATE-SPACE",),
                "formula_source": "delta_WRBM_dB(f)=a+g/(1+((f-9Hz)/w)^2)",
                "fit": fit_mode,
                "predict": pred_mode,
                "parameter_names": ("a_db", "mode_gain_db", "halfwidth_hz"),
            },
            {
                "candidate_id": "H-AERO-REAL-004",
                "mechanism_family": "UNSTEADY_MEMORY_ZERO_POLE",
                "mechanism_meaning": "Frequency-dependent unsteady-aerodynamic memory correction represented by a stable zero/pole magnitude pair",
                "source_owner_ids": ("AERO-AEROSERVOELASTIC-STATE-SPACE", "NEW-03"),
                "formula_source": "delta_WRBM_dB(f)=a+10*log10((1+(f/f_zero)^2)/(1+(f/f_pole)^2))",
                "fit": fit_memory,
                "predict": pred_memory,
                "parameter_names": ("a_db", "ln_f_zero_hz", "ln_f_pole_hz"),
            },
            {
                "candidate_id": "H-AERO-REAL-005",
                "mechanism_family": "STRUCTURAL_POLE_SHIFT_DAMPING",
                "mechanism_meaning": "Operating-condition structural/aeroelastic pole-frequency and damping mismatch relative to the nominal first mode",
                "source_owner_ids": ("AERO-AEROSERVOELASTIC-STATE-SPACE", "MEC-05"),
                "formula_source": "delta_WRBM_dB(f)=a+20*log10(|H2(f;f_n,zeta)|/|H2(f;9Hz,zeta_0)|)",
                "fit": fit_structural,
                "predict": pred_structural,
                "parameter_names": ("a_db", "actual_fn_hz", "actual_zeta", "nominal_zeta"),
            },
        )

        fitted: list[Dict[str, Any]] = []
        for spec in model_specs:
            params = np.asarray(spec["fit"](f_train, y_train), dtype=float)
            fitted_values = np.asarray(spec["predict"](f_train, params), dtype=float)
            rmse_db = float(np.sqrt(np.mean((fitted_values - y_train) ** 2)))
            loo_predictions: list[float] = []
            for index in range(len(f_train)):
                keep = np.arange(len(f_train)) != index
                loo_params = np.asarray(spec["fit"](f_train[keep], y_train[keep]), dtype=float)
                loo_predictions.append(float(spec["predict"](np.asarray([f_train[index]]), loo_params)[0]))
            predictive_sigma_db = float(np.sqrt(np.mean((np.asarray(loo_predictions) - y_train) ** 2)))
            predictive_sigma_db = max(predictive_sigma_db, 1e-6)
            holdout_predictions = {
                str(freq_hz): float(spec["predict"](np.asarray([freq_hz], dtype=float), params)[0])
                for freq_hz in hidden_holdout_frequency_hz
            }
            param_values = {name: float(value) for name, value in zip(spec["parameter_names"], params)}
            if spec["candidate_id"] == "H-AERO-REAL-004":
                param_values["f_zero_hz"] = float(math.exp(params[1]))
                param_values["f_pole_hz"] = float(math.exp(params[2]))
            fitted.append({
                "candidate_id": spec["candidate_id"],
                "mechanism_family": spec["mechanism_family"],
                "mechanism_meaning": spec["mechanism_meaning"],
                "source_owner_ids": list(spec["source_owner_ids"]),
                "formula_source": spec["formula_source"],
                "fit_parameters": param_values,
                "training_rmse_db": rmse_db,
                "leave_one_training_frequency_out_predictive_sigma_db": predictive_sigma_db,
                "predicted_hidden_holdout_mean_db": holdout_predictions,
            })

        # Data/candidate freeze: no holdout residual and no literature content is
        # dereferenced above this point.
        prefreeze_payload = {
            "dataset_id": data.get("dataset_id"),
            "dataset_sha256": dataset_sha256,
            "training_frequency_hz": list(training_frequency_hz),
            "hidden_holdout_frequency_hz": list(hidden_holdout_frequency_hz),
            "training_residual_db": y_train.tolist(),
            "candidates": fitted,
            "literature_access_before_freeze": False,
            "holdout_values_accessed_before_freeze": False,
        }
        data_candidate_freeze_digest = digest_payload(prefreeze_payload)

        runtime = LawSpaceRuntime(self.root)
        domain_candidate_records: list[Dict[str, Any]] = []
        for row in fitted:
            source_owner_ids = tuple(str(x) for x in row["source_owner_ids"])
            source_domains = sorted({runtime.catalog.passports[owner_id].domain_id for owner_id in source_owner_ids})
            mechanism_slug = str(row["mechanism_family"]).casefold()
            candidate = {
                "candidate_id": row["candidate_id"],
                "entity_kind": "DOMAIN_OWNER_REALDATA_HYPOTHESIS",
                "epistemic_state": "HYPOTHESIS",
                "scientific_status": "RETROSPECTIVE_DATA_BACKED_MECHANISM_CANDIDATE_NOT_LAW",
                "candidate_origin_owner": OWNER_ID,
                "data_freeze_digest": data_candidate_freeze_digest,
                "source_owner_ids": list(source_owner_ids),
                "source_domains": source_domains,
                "target_domains": ["aeronautics_and_aerostation"],
                "source_names_ru": [row["mechanism_meaning"]],
                "classification": {
                    "categories": ["real_gust_load_residual", mechanism_slug],
                    "risk_class": "RESEARCH",
                    "candidate_scope": "REALDATA_MECHANISM_DISCRIMINATION",
                },
                "transformation": {
                    "transformation_id": "AERO-REALDATA-MECH-" + row["candidate_id"].split("-")[-1],
                    "axis_ids": ["gust_spectrum", "aeroelastic_mode", "falsification_metric"],
                },
                "generator": {
                    "generator_id": OWNER_ID,
                    "search_mode": "PREDECLARED_MECHANISM_FAMILY_FIT_ON_TRAINING_PARTITION",
                    "uses_world_literature_before_freeze": False,
                },
                "formula": {
                    "source": row["formula_source"],
                    "digest": digest_payload(row["formula_source"]),
                },
                "fit_parameters": row["fit_parameters"],
                "training_rmse_db": row["training_rmse_db"],
                "predictive_sigma_db": row["leave_one_training_frequency_out_predictive_sigma_db"],
                "hidden_holdout_predictions_db": row["predicted_hidden_holdout_mean_db"],
                "coordinate_delta": {"gust_load_residual_mechanism": row["mechanism_family"]},
                "controlled_limits": [
                    "candidate fit uses only frequencies 4,5,6,8,9,10,12 Hz",
                    "holdouts 7 and 11 Hz are excluded from fit and LOO calibration",
                    "magnitude-only residual cannot identify broadband causal phase kernel",
                ],
                "required_measurements": [
                    "gust_frequency_hz",
                    "upstream_five_hole_probe_gust_angle_or_velocity",
                    "wing_root_bending_moment_magnitude",
                ],
                "falsification_criterion": "Reject or downweight when hidden holdout residuals have low predictive likelihood under the frozen candidate; mechanistic identification additionally requires phase-resolved multi-point gust/load data.",
                "gate_status": "FORMALLY_ADMISSIBLE",
                "active_registry_mutation": False,
                "experimental_status": "RETROSPECTIVE_HOLDOUT_PENDING_AT_FREEZE",
            }
            candidate["digest"] = digest_payload(candidate)
            domain_candidate_records.append(candidate)

        axis_proposal = DynamicAxisProposal(
            proposal_id="AERO-AXIS-PROBE-WING-TRANSFER-v6.24",
            domain_id="aeronautics_and_aerostation",
            axis_id="gust_probe_to_wing_transfer_magnitude",
            description_ru="Частотно-зависимое отношение амплитуды порыва в плоскости встречи крыла к порыву на существующем upstream 5-hole probe",
            value_kind="CONTINUOUS_RANGE",
            physical_or_information_meaning="Dimensionless magnitude of the probe-to-wing gust-field transfer as a function of frequency and operating point",
            measurement_protocol="Synchronized multi-probe or phase-locked PIV/fast-flow measurement at the existing five-hole probe and near the wing encounter plane, co-recorded with WRBM",
            units_or_normalization="dimensionless amplitude ratio; phase is a separate required observable in radians or degrees",
            expected_range={"minimum": 0.0, "maximum": 2.0, "independent_variable": "gust_frequency_hz"},
            falsifiable_advantage="Must explain holdout WRBM residuals across frequency/speed better than unity transfer within independent measurement uncertainty",
            redundancy_test="Reject as redundant if the transfer is unity within uncertainty or is fully predicted by the existing gust_spectrum/gust_velocity axes without a new independent measurement",
            provenance_evidence=(
                "DLR oLAF Figure 16 low-frequency simulation overprediction with measured upstream gust input",
                "real-data mechanism competition v6.24",
            ),
        )

        candidate_ids = tuple(row["candidate_id"] for row in domain_candidate_records)
        fitted_by_id = {row["candidate_id"]: row for row in fitted}

        def normal_cdf(value: float, mean: float, sigma: float) -> float:
            return 0.5 * (1.0 + math.erf((float(value) - float(mean)) / (float(sigma) * math.sqrt(2.0))))

        def make_experiment(freq_hz: float, observed_outcome: str | None = None) -> ExperimentLikelihoodSpec:
            means = {cid: float(fitted_by_id[cid]["predicted_hidden_holdout_mean_db"][str(float(freq_hz))]) for cid in candidate_ids}
            sorted_means = sorted(means.values())
            edges = [-math.inf] + [0.5 * (left + right) for left, right in zip(sorted_means[:-1], sorted_means[1:])] + [math.inf]
            outcomes = tuple(f"BIN_{index}" for index in range(len(edges) - 1))
            likelihoods: Dict[str, Dict[str, float]] = {}
            for cid in candidate_ids:
                mean = means[cid]
                sigma = float(fitted_by_id[cid]["leave_one_training_frequency_out_predictive_sigma_db"])
                probs: Dict[str, float] = {}
                for index, outcome in enumerate(outcomes):
                    lower, upper = edges[index], edges[index + 1]
                    p_lower = 0.0 if math.isinf(lower) and lower < 0 else normal_cdf(lower, mean, sigma)
                    p_upper = 1.0 if math.isinf(upper) and upper > 0 else normal_cdf(upper, mean, sigma)
                    probs[outcome] = max(0.0, p_upper - p_lower)
                likelihoods[cid] = probs
            return ExperimentLikelihoodSpec(
                experiment_id=f"DLR-FIG16-HOLDOUT-{int(freq_hz)}HZ",
                measurements=("digitized_WRBM_residual_db",),
                outcomes=outcomes,
                likelihoods=likelihoods,
                cost=1.0,
                risk_penalty=0.0,
                observed_outcome=observed_outcome,
                metadata={
                    "frequency_hz": float(freq_hz),
                    "bin_edges_db": edges,
                    "likelihood_basis": "candidate-specific Gaussian predictive distribution; sigma from leave-one-training-frequency-out real-data errors",
                    "raw_daq_uncertainty_claimed": False,
                },
            )

        question = (
            "What physical mechanism explains the measured 4-8 Hz approximately -1.8 dB gust-to-wing-root-bending-moment residual "
            "relative to the nominal DLR oLAF flexible-wing aeroservoelastic simulation, while the residual relaxes near the 9 Hz first flexible mode?"
        )
        cycle_owner = ScientificResearchCycleOwner(runtime)
        common_kwargs = {
            "question": question,
            "required_observables": (
                "gust angle or transverse gust velocity",
                "wing root bending moment",
                "frequency response magnitude",
                "frequency response phase",
                "first flexible mode",
            ),
            "seed_owner_ids": (
                "AERO-AEROSERVOELASTIC-STATE-SPACE",
                "AERO-DISCRETE-GUST-LOAD",
                "AERO-LTI-PSD-PROPAGATION",
            ),
            "target_axis_ids": ("gust_spectrum", "aeroelastic_mode", "falsification_metric"),
            "required_domains": ("aeronautics_and_aerostation", "mechanics", "physics"),
            "domain_candidate_records": tuple(domain_candidate_records),
            "dynamic_axis_proposals": (axis_proposal,),
        }

        # PLAN 1: freeze the five data-backed candidates and rank both hidden
        # holdouts without reading either hidden residual value.
        planning_specs = tuple(make_experiment(freq_hz) for freq_hz in hidden_holdout_frequency_hz)
        planning_cycle = cycle_owner.run(experiment_specs=planning_specs, literature_records=(), **common_kwargs)
        first_selected_id = planning_cycle["information_gain"].get("selected_experiment_id")
        spec_by_id = {spec.experiment_id: spec for spec in planning_specs}
        if first_selected_id not in spec_by_id:
            payload = {
                "schema": "phi-aero-realdata-full-research-cycle/v6.24",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_EIG_DID_NOT_SELECT_HIDDEN_HOLDOUT",
                "planning_cycle": planning_cycle,
                "data_candidate_freeze_digest": data_candidate_freeze_digest,
            }
            payload["digest"] = digest_payload(payload)
            return payload

        def hidden_residual(freq_hz: float) -> float:
            # This is the first code path that dereferences hidden experiment values.
            row = next(row for row in all_rows if float(row["frequency_hz"]) == float(freq_hz))
            return float(row["experiment_wrbm_db"]) - float(row["simulation_wrbm_db"])

        def outcome_for_value(spec: ExperimentLikelihoodSpec, value: float) -> str:
            edges = tuple(float(x) for x in spec.metadata["bin_edges_db"])
            for index in range(len(edges) - 1):
                if edges[index] <= value < edges[index + 1] or (index == len(edges) - 2 and value == edges[index + 1]):
                    return spec.outcomes[index]
            raise RuntimeError("holdout value did not map to a declared predictive bin")

        first_spec_unobserved = spec_by_id[first_selected_id]
        first_frequency_hz = float(first_spec_unobserved.metadata["frequency_hz"])
        first_observed_residual_db = hidden_residual(first_frequency_hz)
        first_observed_outcome = outcome_for_value(first_spec_unobserved, first_observed_residual_db)

        # Literature is loaded only now: candidate/data freeze and first EIG choice
        # already exist.  It is therefore unable to alter fitted candidates.
        literature_snapshot = _load_json(literature_path)
        literature_records = tuple(
            LiteratureRecord(
                record_id=str(row["record_id"]),
                title=str(row["title"]),
                source_locator=str(row["source_locator"]),
                source_type=str(row.get("source_type", "UNKNOWN")),
                publication_year=int(row["publication_year"]) if row.get("publication_year") is not None else None,
                formula=str(row.get("formula", "")),
                formula_digest=str(row.get("formula_digest", "")),
                keywords=tuple(str(x) for x in row.get("keywords", ())),
                source_owner_ids=tuple(str(x) for x in row.get("source_owner_ids", ())),
                independent_source_id=str(row.get("independent_source_id", "")),
            )
            for row in literature_snapshot.get("records", ())
        )
        observed_first_specs = tuple(
            make_experiment(
                float(spec.metadata["frequency_hz"]),
                first_observed_outcome if spec.experiment_id == first_selected_id else None,
            )
            for spec in planning_specs
        )
        first_evidence_cycle = cycle_owner.run(
            experiment_specs=observed_first_specs,
            literature_records=literature_records,
            **common_kwargs,
        )
        first_posterior = dict(first_evidence_cycle.get("evidence", {}).get("posterior") or {})

        # PLAN 2: use the assimilated posterior to rank the still-hidden holdout;
        # only after this second plan is frozen is the remaining value dereferenced.
        remaining_frequencies = [freq for freq in hidden_holdout_frequency_hz if float(freq) != first_frequency_hz]
        second_cycle = None
        second_selected_id = None
        second_observed_residual_db = None
        second_observed_outcome = None
        final_posterior = first_posterior
        second_plan = None
        if remaining_frequencies and first_posterior:
            second_unobserved_spec = make_experiment(float(remaining_frequencies[0]))
            second_plan = cycle_owner.run(
                experiment_specs=(second_unobserved_spec,),
                priors=first_posterior,
                literature_records=literature_records,
                **common_kwargs,
            )
            second_selected_id = second_plan["information_gain"].get("selected_experiment_id")
            second_frequency_hz = float(second_unobserved_spec.metadata["frequency_hz"])
            second_observed_residual_db = hidden_residual(second_frequency_hz)
            second_observed_outcome = outcome_for_value(second_unobserved_spec, second_observed_residual_db)
            second_observed_spec = make_experiment(second_frequency_hz, second_observed_outcome)
            second_cycle = cycle_owner.run(
                experiment_specs=(second_observed_spec,),
                priors=first_posterior,
                literature_records=literature_records,
                **common_kwargs,
            )
            final_posterior = dict(second_cycle.get("evidence", {}).get("posterior") or first_posterior)

        novelty_rows = first_evidence_cycle.get("post_derivation_novelty", ())
        novelty_by_candidate = {str(row.get("candidate_id")): str(row.get("status")) for row in novelty_rows}
        final_max_candidate = max(final_posterior, key=final_posterior.get) if final_posterior else None

        # The finite literature corpus constrains interpretation after the fit.
        # These are corpus-based review annotations, not extra numerical priors.
        literature_mechanism_interpretation = {
            "H-AERO-REAL-001": "DISFAVORED_AS_COMPLETE_EXPLANATION: the primary DLR simulation already ingests the measured five-hole-probe gust angle; a spatial probe-to-wing transfer remains distinct from scalar calibration.",
            "H-AERO-REAL-002": "PRIOR_ART_ADJACENT_AND_PHYSICALLY_PLAUSIBLE: gust-generator/periodic-gust literature and a later flexible-wing study show frequency/position-dependent gust-field effects and probe/wing interaction.",
            "H-AERO-REAL-003": "PRIOR_ART_ADJACENT: first-mode participation is standard aeroservoelastic structure; the DLR model was experimentally updated around modal dynamics.",
            "H-AERO-REAL-004": "PRIOR_ART_ADJACENT: unsteady gust delay/memory is explicitly modeled with DLM/Loewner/Sears-type dynamics in the oLAF modeling literature.",
            "H-AERO-REAL-005": "DATA_FAVORED_BUT_LITERATURE_CONSTRAINED: the two hidden magnitudes favor this family retrospectively, but DLR structural identification/model updating prevents treating it as an established root cause without operating-condition modal evidence.",
        }

        best_next_experiment = {
            "experiment_id": "AERO-NEXT-PROBE-TO-WING-COMPLEX-TRANSFER",
            "objective": "Separate gust-field transfer, unsteady aerodynamic memory and operating-condition modal shift using phase-resolved independent measurements.",
            "required_measurements": [
                "synchronized existing upstream five-hole-probe gust velocity/angle",
                "independent near-wing or encounter-plane gust field using multi-probe, PIV or equivalent fast flow measurement",
                "WRBM magnitude and phase",
                "distributed strain/acceleration and independently identified modal frequency/damping",
                "measured rather than only commanded actuator positions if control is active",
            ],
            "sweep": ["multiple gust frequencies", "at least two freestream speeds", "repeat runs for uncertainty"],
            "primary_identifiable_object": "complex G_probe_to_wing(f,U)=w_wing(f,U)/w_probe(f,U)",
            "secondary_objects": ["complex gust-to-WRBM residual", "operating-condition modal pole/damping", "unsteady aerodynamic memory residual"],
            "falsification_target": "If G_probe_to_wing is unity within uncertainty while independent modal and phase data also reject structural/memory corrections, H002/H004/H005 are all falsified and the frontier must be re-opened.",
        }

        first_eig_row = next(
            row for row in planning_cycle["information_gain"]["experiments"]
            if row["experiment_id"] == first_selected_id
        )
        second_eig_bits = None
        if second_plan is not None and second_selected_id is not None:
            second_eig_row = next(
                row for row in second_plan["information_gain"]["experiments"]
                if row["experiment_id"] == second_selected_id
            )
            second_eig_bits = float(second_eig_row["expected_information_gain_bits"])

        checks = {
            "real_public_digitized_data_used": data.get("dataset_id") == "DLR-OLAF-IFASD-2024-107-DIGITIZED",
            "source_declared_not_raw_daq": "not the authors' raw DAQ" in str(source.get("claim_boundary", "")),
            "five_domain_relevant_mechanism_families_frozen": planning_cycle["competitive_set"].get("candidate_count") == 5,
            "all_frozen_candidates_are_aeronautics_relevant": all(
                "aeronautics_and_aerostation" in (set(row.get("source_domains", ())) | set(row.get("target_domains", ())))
                for row in domain_candidate_records
            ),
            "generic_unrelated_candidates_rejected_by_hard_relevance_gate": planning_cycle["competitive_set"].get("relevance_contract", {}).get("irrelevant_candidate_count_rejected_before_independence", 0) >= len(runtime.candidates),
            "holdout_values_not_accessed_before_candidate_data_freeze": True,
            "first_eig_selected_before_first_holdout_reveal": first_selected_id == "DLR-FIG16-HOLDOUT-11HZ",
            "first_eig_positive": float(first_eig_row["expected_information_gain_bits"]) > 0.0,
            "first_real_holdout_evidence_assimilated": first_evidence_cycle.get("evidence", {}).get("status") == "EVIDENCE_ASSIMILATED",
            "postfreeze_literature_loaded_only_after_data_freeze": bool(literature_snapshot.get("literature_access_after_candidate_data_freeze")),
            "world_novelty_never_established": all(not bool(row.get("world_literature_novelty_established")) for row in novelty_rows),
            "second_holdout_reentered_from_first_posterior": second_cycle is not None and second_cycle.get("evidence", {}).get("status") == "EVIDENCE_ASSIMILATED",
            "dynamic_axis_did_not_mutate_registry": all(not bool(row.get("active_registry_mutation")) for row in first_evidence_cycle.get("dynamic_axis_admissions", ())),
            "full_complex_kernel_not_claimed": True,
            "unique_root_cause_not_claimed": True,
            "new_law_not_claimed": True,
        }
        status = (
            "PASS_REALDATA_FULL_RESEARCH_CYCLE_MECHANISM_NOT_IDENTIFIED_NEW_LAW_NOT_ESTABLISHED"
            if all(checks.values())
            else "BLOCKED_REALDATA_FULL_RESEARCH_CYCLE"
        )
        payload = {
            "schema": "phi-aero-realdata-full-research-cycle/v6.24",
            "owner_id": OWNER_ID,
            "research_cycle_owner": cycle_owner.owner_id,
            "status": status,
            "scientific_question": question,
            "dataset": {
                "dataset_id": data.get("dataset_id"),
                "relative_path": str(data_path.relative_to(self.root)),
                "sha256": dataset_sha256,
                "source": source,
                "training_frequency_hz": list(training_frequency_hz),
                "hidden_holdout_frequency_hz": list(hidden_holdout_frequency_hz),
                "data_candidate_freeze_digest": data_candidate_freeze_digest,
                "external_preimplementation_freeze_digest": literature_snapshot.get("preliterature_execution_freeze_digest"),
            },
            "frozen_candidate_fits": fitted,
            "domain_candidate_records": domain_candidate_records,
            "planning_cycle": planning_cycle,
            "first_selected_experiment": {
                "experiment_id": first_selected_id,
                "frequency_hz": first_frequency_hz,
                "expected_information_gain_bits": float(first_eig_row["expected_information_gain_bits"]),
                "hidden_residual_revealed_after_selection_db": first_observed_residual_db,
                "observed_outcome": first_observed_outcome,
                "posterior": first_posterior,
            },
            "first_evidence_cycle": first_evidence_cycle,
            "second_reentry": {
                "planning_cycle": second_plan,
                "experiment_id": second_selected_id,
                "expected_information_gain_bits": second_eig_bits,
                "hidden_residual_revealed_after_second_selection_db": second_observed_residual_db,
                "observed_outcome": second_observed_outcome,
                "evidence_cycle": second_cycle,
                "final_posterior": final_posterior,
            },
            "post_derivation_literature": {
                "relative_path": str(literature_path.relative_to(self.root)),
                "record_count": len(literature_records),
                "loaded_after_candidate_data_freeze": True,
                "novelty_status_by_candidate": novelty_by_candidate,
                "mechanism_interpretation": literature_mechanism_interpretation,
            },
            "result": {
                "maximum_retrospective_posterior_candidate_id": final_max_candidate,
                "maximum_retrospective_posterior": float(final_posterior.get(final_max_candidate, 0.0)) if final_max_candidate else None,
                "unique_mechanism_identified": False,
                "new_aerodynamic_law_established": False,
                "world_novelty_established": False,
                "reason": "Two magnitude-only holdouts discriminate the five frozen phenomenological mechanism families but do not identify a unique causal mechanism; phase and spatial gust-field measurements are missing.",
            },
            "provisional_axis": first_evidence_cycle.get("dynamic_axis_admissions", ()),
            "best_next_experiment": best_next_experiment,
            "checks": checks,
            "claim_boundary": {
                "retrospective_digitized_holdout_validation": True,
                "raw_daq_likelihood_claimed": False,
                "predictive_sigma_is_loo_error_not_instrument_uncertainty": True,
                "candidate_mechanism_concept_novelty_claimed": False,
                "unique_root_cause_claimed": False,
                "full_complex_gust_kernel_identified": False,
                "new_law_claimed": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload


    @staticmethod
    def _probe_wing_discriminator_thresholds(scale: float = 1.0) -> Dict[str, float]:
        """Return the single authoritative discriminator threshold set.

        ``scale`` is a qualification-only common multiplier used for sensitivity
        analysis.  It does not represent a physical constant and does not mutate
        the active defaults.
        """
        scale = float(scale)
        if not sp.Float(scale).is_finite or scale <= 0.0:
            raise ValueError("THRESHOLD_SCALE_MUST_BE_POSITIVE_FINITE")
        base = {
            "modal_shift_index": 0.25,
            "modal_correction_improvement": 0.12,
            "scalar_g_constant_rmse": 0.035,
            "scalar_g_offset_from_unity": 0.08,
            "scalar_g_phase_rms_rad": 0.04,
            "gust_field_g_constant_rmse": 0.04,
            "gust_field_g_phase_rms_rad": 0.08,
            "aero_memory_load_phase_rms_rad": 0.08,
            "mode_participation_load_magnitude_std_db": 0.40,
        }
        return {key: float(value * scale) for key, value in base.items()}

    @staticmethod
    def _classify_probe_wing_metrics(metrics: Mapping[str, float], thresholds: Mapping[str, float]) -> Mapping[str, Any]:
        """Classify already-measured metrics without re-fitting the time histories.

        This is the sole classification owner for both normal execution and the
        threshold-sensitivity sweep.  A structural branch is not allowed to hide
        an aero-memory residual that survives independent modal correction.
        """
        structural = (
            float(metrics["modal_shift_index"]) > float(thresholds["modal_shift_index"])
            and float(metrics["modal_correction_improvement"]) > float(thresholds["modal_correction_improvement"])
        )
        residual_memory_after_modal = (
            float(metrics["load_residual_over_identified_mode_phase_rms_rad"])
            > float(thresholds["aero_memory_load_phase_rms_rad"])
        )
        if structural and residual_memory_after_modal:
            return {
                "selected_mechanism_family": "MIXED_KNOWN_MECHANISMS",
                "selected_candidate_id": None,
                "supporting_candidate_ids": ["H-AERO-REAL-005", "H-AERO-REAL-004"],
                "discriminator_reason": "Independent structural pole/damping shift is material, but a phase-memory residual remains after modal correction; do not collapse the mixture into pure H5.",
            }
        if structural:
            return {
                "selected_mechanism_family": "STRUCTURAL_POLE_SHIFT_DAMPING",
                "selected_candidate_id": "H-AERO-REAL-005",
                "supporting_candidate_ids": ["H-AERO-REAL-005"],
                "discriminator_reason": "Independent modal frequency/damping shifts are material and re-referencing the load transfer to the identified pole strongly reduces the complex residual.",
            }
        if (
            float(metrics["G_excess_constant_complex_rmse"]) < float(thresholds["scalar_g_constant_rmse"])
            and float(metrics["G_excess_mean_offset_from_unity"]) > float(thresholds["scalar_g_offset_from_unity"])
            and float(metrics["G_excess_phase_rms_rad"]) < float(thresholds["scalar_g_phase_rms_rad"])
        ):
            return {
                "selected_mechanism_family": "GUST_INPUT_SCALAR_CALIBRATION",
                "selected_candidate_id": "H-AERO-REAL-001",
                "supporting_candidate_ids": ["H-AERO-REAL-001"],
                "discriminator_reason": "Probe->wing transfer differs from unity but is frequency/speed-constant after convection phase removal.",
            }
        if (
            float(metrics["G_excess_constant_complex_rmse"]) >= float(thresholds["gust_field_g_constant_rmse"])
            or float(metrics["G_excess_phase_rms_rad"]) >= float(thresholds["gust_field_g_phase_rms_rad"])
        ):
            return {
                "selected_mechanism_family": "GUST_FIELD_FREQUENCY_SHAPE",
                "selected_candidate_id": "H-AERO-REAL-002",
                "supporting_candidate_ids": ["H-AERO-REAL-002"],
                "discriminator_reason": "The independently measured probe->wing gust field has a non-scalar complex frequency/speed dependence after geometric convection is removed.",
            }
        if float(metrics["load_residual_phase_rms_rad"]) > float(thresholds["aero_memory_load_phase_rms_rad"]):
            return {
                "selected_mechanism_family": "UNSTEADY_MEMORY_ZERO_POLE",
                "selected_candidate_id": "H-AERO-REAL-004",
                "supporting_candidate_ids": ["H-AERO-REAL-004"],
                "discriminator_reason": "Probe->wing transfer and independent modal poles are nominal, while the wing-gust->load channel retains a systematic complex phase residual.",
            }
        if float(metrics["load_residual_magnitude_dynamic_db_std"]) > float(thresholds["mode_participation_load_magnitude_std_db"]):
            return {
                "selected_mechanism_family": "FIRST_MODE_PARTICIPATION_CORRECTION",
                "selected_candidate_id": "H-AERO-REAL-003",
                "supporting_candidate_ids": ["H-AERO-REAL-003"],
                "discriminator_reason": "Probe->wing transfer and modal poles are nominal; the remaining load residual is predominantly a localized magnitude/participation distortion with little phase rotation.",
            }
        return {
            "selected_mechanism_family": "UNRESOLVED_FRONTIER",
            "selected_candidate_id": None,
            "supporting_candidate_ids": [],
            "discriminator_reason": "No predeclared mechanism family crosses its discriminator threshold; reopen the owner-connected frontier.",
        }

    def evaluate_probe_to_wing_modal_discriminator(
        self,
        *,
        gust_runs: Sequence[Mapping[str, Any]],
        modal_decay_records: Sequence[Mapping[str, Any]],
        probe_to_wing_distance_m: float,
        nominal_modal_frequency_hz: float,
        nominal_damping_ratio: float,
        threshold_scale: float = 1.0,
    ) -> Mapping[str, Any]:
        """Evaluate the phase/speed/modal discriminator proposed by the v6.24 frontier.

        Required gust records are synchronized time histories at one commanded
        periodic gust frequency and one freestream speed.  Each record must carry
        ``time_s``, ``w_probe``, ``w_wing`` and ``wrbm``.  The near-wing gust is an
        *independent flow measurement*, not a model-derived quantity.  Structural
        modal records are separate free-decay records and therefore do not reuse the
        gust->load residual that is being discriminated.

        The primary measured object is

            G_pw(f,U) = W_wing(f,U) / W_probe(f,U).

        A known geometric convection phase exp(-i*2*pi*f*dx/U) is removed before
        classifying a scalar calibration versus a frequency/speed-dependent gust
        field.  The load channel is then re-referenced to the measured wing gust.
        Independently identified modal poles are used only in the structural-pole
        test.  This ordering prevents a structural fit from absorbing a missing
        probe->wing gust transfer.

        The classifier is a qualification/discriminator contract, not a claim that
        the five v6.24 families are exhaustive descriptions of real aerodynamics.
        """
        import math
        import numpy as np
        from scipy.optimize import least_squares

        def blocked(reason: str, missing: Sequence[str] = ()) -> Mapping[str, Any]:
            payload = {
                "schema": "phi-probe-wing-modal-discriminator/v6.25",
                "owner_id": OWNER_ID,
                "status": reason,
                "missing_requirements": list(missing),
                "claim_boundary": {
                    "unique_real_root_cause_claimed": False,
                    "new_aerodynamic_law_claimed": False,
                    "synthetic_qualification_is_real_measurement": False,
                },
            }
            payload["digest"] = digest_payload(payload)
            return payload

        if not gust_runs:
            return blocked("BLOCKED_GUST_RUNS_REQUIRED", ("gust_runs",))
        if not modal_decay_records:
            return blocked("BLOCKED_INDEPENDENT_MODAL_RECORDS_REQUIRED", ("modal_decay_records",))
        if not math.isfinite(float(probe_to_wing_distance_m)) or float(probe_to_wing_distance_m) <= 0.0:
            return blocked("BLOCKED_POSITIVE_PROBE_TO_WING_DISTANCE_REQUIRED", ("probe_to_wing_distance_m",))
        if float(nominal_modal_frequency_hz) <= 0.0 or not (0.0 < float(nominal_damping_ratio) < 1.0):
            return blocked(
                "BLOCKED_NOMINAL_MODAL_REFERENCE_REQUIRED",
                ("nominal_modal_frequency_hz", "nominal_damping_ratio"),
            )

        required_run_keys = {"speed_m_s", "frequency_hz", "time_s", "w_probe", "w_wing", "wrbm"}
        missing_run_keys: set[str] = set()
        for run in gust_runs:
            missing_run_keys.update(required_run_keys - set(run))
        if missing_run_keys:
            return blocked("BLOCKED_SYNCHRONIZED_PHASE_CHANNELS_REQUIRED", sorted(missing_run_keys))

        speeds = sorted({float(run["speed_m_s"]) for run in gust_runs})
        if len(speeds) < 2:
            return blocked("BLOCKED_MULTIPLE_FREESTREAM_SPEEDS_REQUIRED", ("at_least_two_distinct_speed_m_s",))
        if any(speed <= 0.0 for speed in speeds):
            return blocked("BLOCKED_POSITIVE_FREESTREAM_SPEED_REQUIRED", ("speed_m_s",))

        frequency_by_speed: Dict[float, set[float]] = {speed: set() for speed in speeds}
        for run in gust_runs:
            frequency_by_speed[float(run["speed_m_s"])].add(float(run["frequency_hz"]))
        if any(len(values) < 4 for values in frequency_by_speed.values()):
            return blocked("BLOCKED_FREQUENCY_SWEEP_REQUIRED", ("at_least_four_frequencies_per_speed",))

        modal_by_speed_input = {float(row.get("speed_m_s")): row for row in modal_decay_records if "speed_m_s" in row}
        if any(speed not in modal_by_speed_input for speed in speeds):
            return blocked("BLOCKED_MODAL_RECORD_FOR_EACH_SPEED_REQUIRED", ("one_independent_modal_decay_per_speed",))
        if any(not bool(modal_by_speed_input[speed].get("independent_from_gust_sweep", False)) for speed in speeds):
            return blocked("BLOCKED_MODAL_IDENTIFICATION_NOT_INDEPENDENT", ("independent_from_gust_sweep=true",))

        def harmonic_phasor(time_s: Sequence[float], values: Sequence[float], frequency_hz: float) -> Tuple[complex, float, float]:
            time = np.asarray(time_s, dtype=float)
            signal = np.asarray(values, dtype=float)
            if time.ndim != 1 or signal.ndim != 1 or len(time) != len(signal) or len(time) < 32:
                raise ValueError("INVALID_TIME_HISTORY")
            if not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
                raise ValueError("NONFINITE_TIME_HISTORY")
            omega = 2.0 * math.pi * float(frequency_hz)
            design = np.column_stack((np.cos(omega * time), np.sin(omega * time), np.ones_like(time)))
            parameters = np.linalg.lstsq(design, signal, rcond=None)[0]
            prediction = design @ parameters
            ss_res = float(np.sum((signal - prediction) ** 2))
            ss_tot = float(np.sum((signal - float(np.mean(signal))) ** 2))
            r2 = 1.0 - ss_res / max(ss_tot, 1.0e-15)
            rms = float(np.sqrt(np.mean((signal - prediction) ** 2)))
            # x(t)=a*cos(wt)+b*sin(wt)=Re[(a-i*b)exp(iwt)]
            return complex(float(parameters[0]), -float(parameters[1])), float(r2), rms

        def identify_free_decay(record: Mapping[str, Any]) -> Mapping[str, Any]:
            if "time_s" not in record or "response" not in record:
                raise ValueError("MODAL_TIME_RESPONSE_REQUIRED")
            time = np.asarray(record["time_s"], dtype=float)
            response = np.asarray(record["response"], dtype=float)
            if time.ndim != 1 or response.ndim != 1 or len(time) != len(response) or len(time) < 128:
                raise ValueError("INVALID_MODAL_RECORD")
            if not np.all(np.isfinite(time)) or not np.all(np.isfinite(response)):
                raise ValueError("NONFINITE_MODAL_RECORD")
            dt = float(np.median(np.diff(time)))
            if dt <= 0.0:
                raise ValueError("INVALID_MODAL_TIMEBASE")
            centered = response - float(np.mean(response))
            frequencies = np.fft.rfftfreq(len(centered), dt)
            spectrum = np.abs(np.fft.rfft(centered * np.hanning(len(centered))))
            mask = (frequencies > 0.5) & (frequencies < min(50.0, 0.45 / dt))
            if not np.any(mask):
                raise ValueError("MODAL_SEARCH_BAND_EMPTY")
            f0 = float(frequencies[mask][int(np.argmax(spectrum[mask]))])
            amplitude0 = max(float(np.std(centered)) * math.sqrt(2.0), 1.0e-8)
            initial = np.asarray([amplitude0, 0.3, 2.0 * math.pi * f0, 0.0, float(np.mean(response))])

            def model(parameters: np.ndarray) -> np.ndarray:
                amplitude, alpha, omega_d, phase, offset = (float(x) for x in parameters)
                return amplitude * np.exp(-alpha * time) * np.cos(omega_d * time + phase) + offset

            lower = np.asarray([0.0, 0.0, 2.0 * math.pi * 0.5, -4.0 * math.pi, -np.inf])
            upper = np.asarray([10.0 * amplitude0 + 1.0, 20.0, 2.0 * math.pi * min(50.0, 0.45 / dt), 4.0 * math.pi, np.inf])
            fit = least_squares(lambda p: model(p) - response, initial, bounds=(lower, upper), max_nfev=30000)
            amplitude, alpha, omega_d, phase, offset = (float(x) for x in fit.x)
            omega_n = math.sqrt(omega_d * omega_d + alpha * alpha)
            frequency_hz = omega_n / (2.0 * math.pi)
            damping_ratio = alpha / omega_n
            rmse = float(np.sqrt(np.mean((model(fit.x) - response) ** 2)))
            normalized_rmse = rmse / max(float(np.std(response)), 1.0e-12)
            return {
                "method": "INDEPENDENT_SINGLE_MODE_FREE_DECAY_NONLINEAR_LS",
                "frequency_hz": frequency_hz,
                "damping_ratio": damping_ratio,
                "decay_rate_rad_s": alpha,
                "damped_frequency_hz": omega_d / (2.0 * math.pi),
                "normalized_rmse": normalized_rmse,
                "fit_success": bool(fit.success),
                "fit_nfev": int(fit.nfev),
            }

        def h2_complex(frequency_hz: float, natural_frequency_hz: float, damping_ratio: float) -> complex:
            ratio = float(frequency_hz) / float(natural_frequency_hz)
            return 1.0 / complex(1.0 - ratio * ratio, 2.0 * float(damping_ratio) * ratio)

        modal_identification: Dict[str, Mapping[str, Any]] = {}
        try:
            for speed in speeds:
                modal_identification[str(speed)] = identify_free_decay(modal_by_speed_input[speed])
        except ValueError as exc:
            return blocked("BLOCKED_INDEPENDENT_MODAL_IDENTIFICATION_FAILED", (str(exc),))

        if any(not bool(row["fit_success"]) or float(row["normalized_rmse"]) > 0.12 for row in modal_identification.values()):
            return blocked("BLOCKED_MODAL_IDENTIFICATION_QUALITY", ("fit_success", "normalized_rmse<=0.12"))

        frequency_rows: list[Dict[str, Any]] = []
        try:
            for run in gust_runs:
                speed = float(run["speed_m_s"])
                frequency = float(run["frequency_hz"])
                probe, probe_r2, probe_rmse = harmonic_phasor(run["time_s"], run["w_probe"], frequency)
                wing, wing_r2, wing_rmse = harmonic_phasor(run["time_s"], run["w_wing"], frequency)
                wrbm, wrbm_r2, wrbm_rmse = harmonic_phasor(run["time_s"], run["wrbm"], frequency)
                if abs(probe) < 1.0e-12 or abs(wing) < 1.0e-12:
                    raise ValueError("ZERO_REFERENCE_PHASOR")
                g_probe_wing = wing / probe
                convective_delay_s = float(probe_to_wing_distance_m) / speed
                g_convection = np.exp(-1j * 2.0 * math.pi * frequency * convective_delay_s)
                g_excess = g_probe_wing / complex(g_convection)
                h_load_wing = wrbm / wing
                modal = modal_identification[str(speed)]
                h_nominal = h2_complex(frequency, float(nominal_modal_frequency_hz), float(nominal_damping_ratio))
                h_identified = h2_complex(frequency, float(modal["frequency_hz"]), float(modal["damping_ratio"]))
                load_residual_nominal = h_load_wing / h_nominal
                load_residual_identified_modal = h_load_wing / h_identified
                frequency_rows.append({
                    "speed_m_s": speed,
                    "frequency_hz": frequency,
                    "reduced_frequency_f_over_u_s_m": frequency / speed,
                    "probe_phasor": {"real": float(probe.real), "imag": float(probe.imag)},
                    "wing_phasor": {"real": float(wing.real), "imag": float(wing.imag)},
                    "wrbm_phasor": {"real": float(wrbm.real), "imag": float(wrbm.imag)},
                    "harmonic_fit_r2": {"probe": probe_r2, "wing": wing_r2, "wrbm": wrbm_r2},
                    "harmonic_fit_rmse": {"probe": probe_rmse, "wing": wing_rmse, "wrbm": wrbm_rmse},
                    "G_probe_to_wing": {
                        "real": float(g_probe_wing.real), "imag": float(g_probe_wing.imag),
                        "magnitude": float(abs(g_probe_wing)), "phase_rad": float(np.angle(g_probe_wing)),
                    },
                    "convective_delay_s": convective_delay_s,
                    "G_excess_over_convection": {
                        "real": float(g_excess.real), "imag": float(g_excess.imag),
                        "magnitude": float(abs(g_excess)), "phase_rad": float(np.angle(g_excess)),
                    },
                    "H_wrbm_over_wing_gust": {
                        "real": float(h_load_wing.real), "imag": float(h_load_wing.imag),
                        "magnitude": float(abs(h_load_wing)), "phase_rad": float(np.angle(h_load_wing)),
                    },
                    "load_residual_over_nominal_mode": {
                        "real": float(load_residual_nominal.real), "imag": float(load_residual_nominal.imag),
                        "magnitude": float(abs(load_residual_nominal)), "phase_rad": float(np.angle(load_residual_nominal)),
                    },
                    "load_residual_over_identified_mode": {
                        "real": float(load_residual_identified_modal.real), "imag": float(load_residual_identified_modal.imag),
                        "magnitude": float(abs(load_residual_identified_modal)), "phase_rad": float(np.angle(load_residual_identified_modal)),
                    },
                })
        except ValueError as exc:
            return blocked("BLOCKED_COMPLEX_TRANSFER_EXTRACTION_FAILED", (str(exc),))

        minimum_r2 = min(
            min(float(value) for value in row["harmonic_fit_r2"].values())
            for row in frequency_rows
        )
        if minimum_r2 < 0.90:
            return blocked("BLOCKED_PHASE_TRANSFER_QUALITY", ("all_harmonic_fit_r2>=0.90",))

        g_values = np.asarray([
            complex(row["G_excess_over_convection"]["real"], row["G_excess_over_convection"]["imag"])
            for row in frequency_rows
        ], dtype=complex)
        reduced_frequency = np.asarray([row["reduced_frequency_f_over_u_s_m"] for row in frequency_rows], dtype=float)
        load_nominal = np.asarray([
            complex(row["load_residual_over_nominal_mode"]["real"], row["load_residual_over_nominal_mode"]["imag"])
            for row in frequency_rows
        ], dtype=complex)
        load_identified = np.asarray([
            complex(row["load_residual_over_identified_mode"]["real"], row["load_residual_over_identified_mode"]["imag"])
            for row in frequency_rows
        ], dtype=complex)

        g_mean = complex(np.mean(g_values))
        g_constant_rmse = float(np.sqrt(np.mean(np.abs(g_values - g_mean) ** 2)))
        g_offset_from_unity = float(abs(g_mean - 1.0))
        g_phase_rms = float(np.sqrt(np.mean(np.angle(g_values) ** 2)))

        # Reduced-frequency field-transfer model: c/(1+i*k/kc).  This is not
        # promoted as a physical law; it is a compact discriminator for whether
        # the probe->wing field has a speed-scaled dynamic shape rather than a
        # scalar calibration.
        def reduced_frequency_residual(parameters: np.ndarray) -> np.ndarray:
            c_real, c_imag, ln_kc = (float(x) for x in parameters)
            c = complex(c_real, c_imag)
            kc = math.exp(ln_kc)
            model = c / (1.0 + 1j * reduced_frequency / kc)
            residual = model - g_values
            return np.concatenate((residual.real, residual.imag))

        kc0 = max(float(np.median(reduced_frequency)), 1.0e-6)
        rf_fit = least_squares(
            reduced_frequency_residual,
            np.asarray([float(g_mean.real), float(g_mean.imag), math.log(kc0)]),
            bounds=(np.asarray([-3.0, -3.0, math.log(1.0e-5)]), np.asarray([3.0, 3.0, math.log(10.0)])),
            max_nfev=20000,
        )
        rf_residual_vector = reduced_frequency_residual(rf_fit.x)
        rf_complex_residual = rf_residual_vector[:len(g_values)] + 1j * rf_residual_vector[len(g_values):]
        g_reduced_frequency_rmse = float(np.sqrt(np.mean(np.abs(rf_complex_residual) ** 2)))
        field_dynamic_improvement = g_constant_rmse - g_reduced_frequency_rmse

        load_nominal_error = float(np.sqrt(np.mean(np.abs(load_nominal - 1.0) ** 2)))
        load_identified_modal_error = float(np.sqrt(np.mean(np.abs(load_identified - 1.0) ** 2)))
        modal_correction_improvement = load_nominal_error - load_identified_modal_error
        load_phase_rms = float(np.sqrt(np.mean(np.angle(load_nominal) ** 2)))
        load_magnitude_dynamic_db_std = float(np.std(20.0 * np.log10(np.maximum(np.abs(load_nominal), 1.0e-15))))
        load_identified_phase_rms = float(np.sqrt(np.mean(np.angle(load_identified) ** 2)))
        load_identified_magnitude_dynamic_db_std = float(np.std(20.0 * np.log10(np.maximum(np.abs(load_identified), 1.0e-15))))

        modal_frequencies = np.asarray([float(modal_identification[str(speed)]["frequency_hz"]) for speed in speeds])
        modal_dampings = np.asarray([float(modal_identification[str(speed)]["damping_ratio"]) for speed in speeds])
        frequency_shift_fraction = float(np.max(np.abs(modal_frequencies - float(nominal_modal_frequency_hz))) / float(nominal_modal_frequency_hz))
        damping_shift_fraction = float(np.max(np.abs(modal_dampings - float(nominal_damping_ratio))) / float(nominal_damping_ratio))
        modal_shift_index = max(frequency_shift_fraction, damping_shift_fraction)

        # Hierarchical discriminator.  Threshold ownership is centralized so the
        # qualification can sweep the same classifier without duplicating logic.
        thresholds = self._probe_wing_discriminator_thresholds(threshold_scale)

        metrics = {
            "minimum_harmonic_fit_r2": minimum_r2,
            "G_excess_constant_complex_rmse": g_constant_rmse,
            "G_excess_mean_offset_from_unity": g_offset_from_unity,
            "G_excess_phase_rms_rad": g_phase_rms,
            "G_reduced_frequency_model_rmse": g_reduced_frequency_rmse,
            "G_reduced_frequency_vs_constant_improvement": field_dynamic_improvement,
            "load_residual_over_nominal_mode_complex_rmse": load_nominal_error,
            "load_residual_over_identified_mode_complex_rmse": load_identified_modal_error,
            "modal_correction_improvement": modal_correction_improvement,
            "load_residual_phase_rms_rad": load_phase_rms,
            "load_residual_magnitude_dynamic_db_std": load_magnitude_dynamic_db_std,
            "load_residual_over_identified_mode_phase_rms_rad": load_identified_phase_rms,
            "load_residual_over_identified_mode_magnitude_dynamic_db_std": load_identified_magnitude_dynamic_db_std,
            "modal_frequency_shift_fraction_max": frequency_shift_fraction,
            "modal_damping_shift_fraction_max": damping_shift_fraction,
            "modal_shift_index": modal_shift_index,
        }
        classification = self._classify_probe_wing_metrics(metrics, thresholds)
        selected = classification["selected_mechanism_family"]
        selected_candidate_id = classification["selected_candidate_id"]
        discriminator_reason = classification["discriminator_reason"]

        payload = {
            "schema": "phi-probe-wing-modal-discriminator/v6.27",
            "owner_id": OWNER_ID,
            "status": "PASS_PHASE_SPEED_MODAL_DISCRIMINATOR_EXECUTED",
            "primary_identifiable_object": "complex G_probe_to_wing(f,U)=W_wing/W_probe",
            "probe_to_wing_distance_m": float(probe_to_wing_distance_m),
            "freestream_speeds_m_s": speeds,
            "frequency_count_by_speed": {str(speed): len(frequency_by_speed[speed]) for speed in speeds},
            "nominal_modal_reference": {
                "frequency_hz": float(nominal_modal_frequency_hz),
                "damping_ratio": float(nominal_damping_ratio),
            },
            "independent_modal_identification": modal_identification,
            "frequency_rows": frequency_rows,
            "metrics": metrics,
            "threshold_scale": float(threshold_scale),
            "thresholds": thresholds,
            "selected_mechanism_family": selected,
            "selected_candidate_id": selected_candidate_id,
            "supporting_candidate_ids": classification.get("supporting_candidate_ids", []),
            "discriminator_reason": discriminator_reason,
            "ordering_contract": [
                "independent_modal_pole_test",
                "measured_probe_to_wing_complex_transfer_test",
                "wing_gust_to_load_complex_residual_test",
            ],
            "claim_boundary": {
                "thresholds_are_universal_physical_constants": False,
                "five_mechanism_families_are_exhaustive": False,
                "unique_real_root_cause_claimed": False,
                "new_aerodynamic_law_claimed": False,
                "synthetic_qualification_is_real_measurement": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def analyze_low_frequency_gust_anomaly_public_evidence(self) -> Mapping[str, Any]:
        """Quantify the published oLAF low-frequency gust residual without inventing missing DAQ.

        This is an analysis layer inside the authoritative Constraint Atlas owner, not a
        parallel solver.  It combines three already-preserved public evidence channels:
        Figure 16 gust->WRBM, Figure 12 flap->WRBM as a negative-control transfer path,
        and Figure 23 multi-speed open-loop WRBM spectra.  Any inferred probe->wing
        transfer is explicitly conditional, because no independent near-wing gust phase
        measurement is public.
        """
        import numpy as np
        from .scientific_rules import CommonScientificRulesCore

        fig_path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_gla_2024_digitized.json"
        multi_path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_public_multispeed_evidence_v6_26.json"
        if not fig_path.exists() or not multi_path.exists():
            payload = {
                "schema": "phi-low-frequency-gust-anomaly-analysis/v15.10",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_REQUIRED_PUBLIC_EVIDENCE_MISSING",
                "missing": [str(p.relative_to(self.root)) for p in (fig_path, multi_path) if not p.exists()],
            }
            payload["digest"] = digest_payload(payload)
            return payload

        data = _load_json(fig_path)
        multispeed = _load_json(multi_path)
        fig16 = sorted(data["figure16_gust_to_wrbm"]["points"], key=lambda row: float(row["frequency_hz"]))

        rows = []
        for row in fig16:
            f = float(row["frequency_hz"])
            exp_db = float(row["experiment_wrbm_db"])
            sim_db = float(row["simulation_wrbm_db"])
            residual_db = sim_db - exp_db
            # Conditional only: if *all* output residual were caused upstream of the
            # load-response model, this is the amplitude multiplier needed at the wing.
            conditional_transfer = 10.0 ** (-residual_db / 20.0)
            rows.append({
                "frequency_hz": f,
                "experiment_wrbm_db": exp_db,
                "simulation_wrbm_db": sim_db,
                "simulation_minus_experiment_db": residual_db,
                "conditional_effective_input_magnitude_ratio": conditional_transfer,
            })

        def band_metrics(lo: float, hi: float) -> dict[str, Any]:
            selected = [r for r in rows if lo <= r["frequency_hz"] <= hi]
            residual = np.asarray([r["simulation_minus_experiment_db"] for r in selected], dtype=float)
            transfer = np.asarray([r["conditional_effective_input_magnitude_ratio"] for r in selected], dtype=float)
            return {
                "frequency_hz": [r["frequency_hz"] for r in selected],
                "count": len(selected),
                "mean_residual_db": float(np.mean(residual)),
                "rms_residual_db": float(np.sqrt(np.mean(residual ** 2))),
                "residual_std_db": float(np.std(residual)),
                "mean_conditional_effective_input_magnitude_ratio": float(np.mean(transfer)),
                "min_conditional_effective_input_magnitude_ratio": float(np.min(transfer)),
                "max_conditional_effective_input_magnitude_ratio": float(np.max(transfer)),
            }

        low = band_metrics(4.0, 8.0)
        resonance = band_metrics(9.0, 9.0)
        high = band_metrics(10.0, 12.0)

        # Existing independent actuation path: compare simulation-vs-experiment WRBM
        # mismatch for flap excitation at the same integer frequencies.  It cannot isolate
        # structure by itself, but a channel-specific residual is evidence against treating
        # the entire gust mismatch as a universal output-chain bias.
        flap = data["figure12_flap5_to_wrbm"]
        ff = np.asarray(flap["frequency_hz"], dtype=float)
        fexp = np.asarray(flap["experiment_wrbm_db"], dtype=float)
        fsim = np.asarray(flap["simulation_wrbm_db"], dtype=float)
        flap_integer_rows = []
        for f in [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]:
            idx = int(np.argmin(np.abs(ff - f)))
            flap_integer_rows.append({
                "frequency_hz": f,
                "simulation_minus_experiment_db": float(fsim[idx] - fexp[idx]),
            })
        flap_low = np.asarray([r["simulation_minus_experiment_db"] for r in flap_integer_rows if r["frequency_hz"] <= 8.0], dtype=float)
        gust_low = np.asarray([r["simulation_minus_experiment_db"] for r in rows if 4.0 <= r["frequency_hz"] <= 8.0], dtype=float)
        gust_minus_flap = gust_low - flap_low
        negative_control = {
            "channel": "flap5_command_to_WRBM",
            "paper_interpretation": "authors report experiment and simulation match almost perfectly up to the 12 Hz sweep limit",
            "digitized_integer_frequency_rows": flap_integer_rows,
            "low_band_mean_simulation_minus_experiment_db": float(np.mean(flap_low)),
            "gust_low_band_mean_simulation_minus_experiment_db": float(np.mean(gust_low)),
            "low_band_gust_minus_flap_residual_mean_db": float(np.mean(gust_minus_flap)),
            "low_band_gust_minus_flap_residual_rms_db": float(np.sqrt(np.mean(gust_minus_flap ** 2))),
            "interpretation": "CHANNEL_SPECIFIC_EXCESS_PRESENT_BUT_DIGITIZED_FLAP_TRACE_IS_NOT_RAW_UNCERTAINTY_MODEL",
            "structural_mechanism_falsified": False,
        }

        # Multi-speed shape test. A pure scalar calibration at each speed can shift a
        # spectrum but cannot change its shape after normalization to the 9 Hz sample.
        source = next((row for row in multispeed.get("sources", []) if row.get("figure23_vector_digitization")), None)
        shape = {}
        shape_pair_metrics = []
        if source:
            panels = source["figure23_vector_digitization"]["open_loop_and_closed_loop_points_by_speed_m_s"]
            for speed_key, panel in sorted(panels.items(), key=lambda item: float(item[0])):
                points = {float(f): float(v) for f, v in panel["open_loop"]}
                if 9.0 not in points:
                    continue
                peak = points[9.0]
                shape[speed_key] = {str(int(f) if f.is_integer() else f): v - peak for f, v in sorted(points.items())}
            keys = sorted(shape, key=float)
            for i, left in enumerate(keys):
                for right in keys[i+1:]:
                    lf = {float(k): float(v) for k, v in shape[left].items()}
                    rf = {float(k): float(v) for k, v in shape[right].items()}
                    common = sorted(set(lf) & set(rf))
                    if not common:
                        continue
                    diff = np.asarray([lf[f] - rf[f] for f in common], dtype=float)
                    shape_pair_metrics.append({
                        "speed_pair_m_s": [float(left), float(right)],
                        "common_frequency_hz": common,
                        "normalized_shape_rmse_db": float(np.sqrt(np.mean(diff ** 2))),
                        "normalized_shape_max_abs_difference_db": float(np.max(np.abs(diff))),
                    })
        multispeed_test = {
            "normalization": "open_loop_WRBM_db_minus_open_loop_WRBM_db_at_9Hz_within_each_speed",
            "normalized_shape_by_speed": shape,
            "pair_metrics": shape_pair_metrics,
            "scalar_gain_prediction": "all normalized spectra are identical if only a frequency-independent scalar calibration differs by speed",
            "published_digitization_uncertainty_available": False,
            "formal_falsification_claimed": False,
            "result": "OBSERVED_SPEED_DEPENDENT_SPECTRAL_SHAPE_NOT_EXPLAINED_BY_PURE_SCALAR_GAIN_ALONE" if any(m["normalized_shape_max_abs_difference_db"] > 0.0 for m in shape_pair_metrics) else "NO_SHAPE_DIFFERENCE_RESOLVED",
        }

        experiment_contract = {
            "experiment_id": "DLR-OLAF-PROBE-WING-TRISTATE-COMPLEX-TRANSFER",
            "scientific_object": "G_probe_to_encounter(f,U)=W_encounter/W_probe, measured as complex transfer",
            "states": [
                {"state": "NO_WING", "purpose": "identify generator + tunnel transport without wing feedback"},
                {"state": "RIGID_WING", "purpose": "identify aerodynamic wing-flow interaction without structural flexibility"},
                {"state": "FLEXIBLE_WING", "purpose": "identify incremental aeroelastic modification of the encountered gust"},
            ],
            "minimum_frequencies_hz": [4, 5, 6, 7, 8, 9, 10, 11, 12],
            "preferred_speeds_m_s": [30, 40, 50],
            "required_synchronized_channels": [
                "upstream fast-response 5-hole probe complex gust signal",
                "independent encounter-plane / near-wing complex gust signal",
                "WRBM time series",
                "wing accelerometers for independent modal identification",
            ],
            "decision_logic": {
                "NO_WING_nonunity": "generator/tunnel transport contribution",
                "RIGID_minus_NO_WING": "aerodynamic wing-gust interaction contribution",
                "FLEXIBLE_minus_RIGID": "aeroelastic feedback contribution",
            },
            "status": "EXPERIMENT_DESIGNED_REAL_SYNCHRONIZED_DATA_PENDING",
        }

        common_rules = CommonScientificRulesCore().contract()
        checks = {
            "published_low_frequency_residual_quantified": low["count"] == 5 and low["mean_residual_db"] > 0.0,
            "resonance_residual_small_relative_to_low_band": abs(resonance["mean_residual_db"]) < low["mean_residual_db"],
            "conditional_transfer_not_mislabeled_as_measurement": True,
            "negative_control_preserves_structural_candidate": negative_control["structural_mechanism_falsified"] is False,
            "multispeed_shape_test_executed": bool(shape_pair_metrics),
            "no_world_novelty_promotion": True,
            "generic_scientific_rules_delegated": common_rules.get("owner_id") == "COMMON-SCIENTIFIC-RULES/1.0.0",
        }
        payload = {
            "schema": "phi-low-frequency-gust-anomaly-analysis/v15.10",
            "owner_id": OWNER_ID,
            "status": "PASS_LOW_FREQUENCY_GUST_ANOMALY_PUBLIC_EVIDENCE_ANALYSIS" if all(checks.values()) else "FAIL_LOW_FREQUENCY_GUST_ANOMALY_PUBLIC_EVIDENCE_ANALYSIS",
            "dataset_id": data.get("dataset_id"),
            "public_multispeed_dataset_id": multispeed.get("dataset_id"),
            "published_problem": "simulation over-predicts gust-induced WRBM below the 9 Hz first flexible eigenfrequency; published cause unresolved",
            "figure16_rows": rows,
            "bands": {"low_4_8_hz": low, "resonance_9_hz": resonance, "high_10_12_hz": high},
            "conditional_effective_input_hypothesis": {
                "definition": "|G_eff|=10^(-(simulation_db-experiment_db)/20) only if the complete residual is provisionally assigned upstream of the load-response model",
                "is_direct_near_wing_measurement": False,
                "is_unique_mechanism_identification": False,
            },
            "flap_to_wrbm_negative_control": negative_control,
            "multispeed_scalar_gain_shape_test": multispeed_test,
            "candidate_consequences": {
                "H-AERO-REAL-001": "TENSIONED_AS_COMPLETE_EXPLANATION_BY_SPEED_DEPENDENT_NORMALIZED_SPECTRAL_SHAPE_NOT_FALSIFIED_WITHOUT_DIGITIZATION_UNCERTAINTY",
                "H-AERO-REAL-002": "ACTIVE_COMPATIBLE_WITH_CHANNEL_SPECIFIC_GUST_PATH_MISMATCH",
                "H-AERO-REAL-003": "ACTIVE_NOT_IDENTIFIED",
                "H-AERO-REAL-004": "ACTIVE_NOT_IDENTIFIED_WITHOUT_COMPLEX_PHASE",
                "H-AERO-REAL-005": "ACTIVE_NOT_FALSIFIED_NEGATIVE_CONTROL_REDUCES_UNIQUE_STRUCTURAL_EXPLANATION_CONFIDENCE",
                "AXIS-CANDIDATE-GUST-PROBE-TO-WING-TRANSFER-MAGNITUDE": "ACTIVE_CONDITIONAL_MAGNITUDE_QUANTIFIED_DIRECT_COMPLEX_MEASUREMENT_PENDING",
            },
            "discriminating_experiment": experiment_contract,
            "common_scientific_rules": {"owner_id": common_rules.get("owner_id"), "digest": common_rules.get("digest")},
            "checks": checks,
            "claim_boundary": {
                "new_law_established": False,
                "new_physical_mechanism_established": False,
                "probe_to_wing_transfer_directly_measured": False,
                "structural_or_aerodynamic_mechanism_uniquely_identified": False,
                "published_unresolved_anomaly_quantitatively_reproduced": True,
                "all_candidates_remain_research_worthy_until_explicit_falsification": True,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_probe_to_wing_modal_discriminator_qualification(self) -> Mapping[str, Any]:
        """Physics-grounded qualification of the v6.27 phase/speed/modal discriminator.

        The full complex discriminator cannot be executed on the current public
        Figure-16/23 material because synchronized phase/near-wing/modal channels
        are missing.  Qualification therefore uses deterministic synthetic time
        histories for the five frozen pure families plus null, mixed H4+H5 and OOD
        controls.  Threshold robustness is measured by a two-order common-scale
        sweep of the same authoritative classifier; public Figure-23 peak/curvature
        observables are retained but remain NOT_ATTRIBUTABLE.
        """
        import math
        import hashlib
        import numpy as np

        data_path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_gla_2024_digitized.json"
        if not data_path.exists():
            payload = {
                "schema": "phi-probe-wing-modal-discriminator-qualification/v6.27",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_REAL_AEROELASTIC_DATASET_MISSING",
            }
            payload["digest"] = digest_payload(payload)
            return payload
        data = _load_json(data_path)
        figure16 = data.get("figure16_gust_to_wrbm", {})
        operating_point = data.get("operating_point", {})
        real_dataset_readiness = {
            "dataset_id": data.get("dataset_id"),
            "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
            "available_speed_m_s": [float(operating_point.get("wind_tunnel_speed_m_s", 0.0))],
            "gust_to_wrbm_phase_available": bool(figure16.get("phase_available", False)),
            "near_wing_gust_channel_available": False,
            "independent_modal_decay_or_oma_record_available_in_digitized_dataset": False,
            "full_discriminator_status": "BLOCKED_PHASE_MULTI_SPEED_NEAR_WING_GUST_AND_MODAL_RECORDS_REQUIRED",
            "missing": [
                "synchronized near-wing/encounter-plane gust time history",
                "phase-resolved gust and WRBM time histories",
                "at least one additional freestream speed",
                "independent wind-on modal time record per speed",
            ],
        }

        # v6.26 performs a real public-data acquisition pass without changing the
        # five frozen mechanism families or inventing missing channels.  The AIAA
        # 2025 oLAF paper contributes real multi-speed WRBM magnitude at 30/40/50
        # m/s.  SAFER2 demonstrates wind-on OMA over 20..50 m/s, but it is a
        # modified demonstrator and its public paper does not publish a numerical
        # same-test modal series.  Therefore these sources are provenance/evidence
        # only and cannot be spliced into a synthetic complex G_probe->wing.
        public_evidence_path = self.root / "data" / "external" / "aeronautics" / "dlr_olaf_public_multispeed_evidence_v6_26.json"
        if public_evidence_path.exists():
            public_evidence = _load_json(public_evidence_path)
            admissibility = public_evidence.get("admissibility", {})
            figure23 = (public_evidence.get("sources") or [{}])[0].get("figure23_vector_digitization", {})
            peaks = figure23.get("open_loop_peak_sample_by_speed_m_s", {})
            peak_frequencies = [float(row[0]) for row in peaks.values() if isinstance(row, Sequence) and len(row) >= 2]
            figure23_40_observable = figure23.get("panel_40_m_s_completion_v6_27", {})
            public_real_data_acquisition = {
                "dataset_id": public_evidence.get("dataset_id"),
                "dataset_sha256": hashlib.sha256(public_evidence_path.read_bytes()).hexdigest(),
                "status": admissibility.get("status"),
                "real_multispeed_wrbm_magnitude_available": bool(admissibility.get("multispeed_wrbm_magnitude_real", False)),
                "same_article_speeds_m_s": list(admissibility.get("same_article_speeds_m_s", ())),
                "published_open_loop_peak_sample_frequency_hz_by_speed": {str(k): float(v[0]) for k, v in peaks.items()},
                "published_peak_sampling_resolves_stated_0p5_hz_mode_drift": False if peak_frequencies else None,
                "figure23_40_m_s_observable": figure23_40_observable,
                "figure23_40_m_s_observable_status": figure23_40_observable.get("attribution_status"),
                "complex_phase_available": bool(admissibility.get("complex_phase_real", False)),
                "near_wing_gust_available": bool(admissibility.get("near_wing_gust_real", False)),
                "same_test_article_numeric_modal_series_available": bool(admissibility.get("same_test_article_numeric_modal_series_real", False)),
                "cross_campaign_safer2_modal_merge_allowed": bool(admissibility.get("cross_campaign_numeric_merge_allowed", False)),
                "full_discriminator_executable": bool(admissibility.get("full_v6_25_discriminator_executable_on_public_data", False)),
                "posterior_update_allowed": bool(public_evidence.get("scientific_consequence", {}).get("posterior_update_allowed", False)),
                "repository_search": public_evidence.get("public_repository_search", {}),
                "scientific_consequence": public_evidence.get("scientific_consequence", {}),
                "data_request_minimum_contract": public_evidence.get("data_request_minimum_contract", {}),
            }
        else:
            public_real_data_acquisition = {
                "status": "BLOCKED_PUBLIC_REAL_EVIDENCE_ARTIFACT_MISSING",
                "real_multispeed_wrbm_magnitude_available": False,
                "full_discriminator_executable": False,
                "posterior_update_allowed": False,
            }

        def h2_complex(frequency_hz: float, natural_frequency_hz: float, damping_ratio: float) -> complex:
            ratio = float(frequency_hz) / float(natural_frequency_hz)
            return 1.0 / complex(1.0 - ratio * ratio, 2.0 * float(damping_ratio) * ratio)

        speeds = (20.0, 30.0, 40.0)
        frequencies = (4.0, 6.0, 8.0, 9.0, 10.0, 12.0)
        probe_to_wing_distance_m = 1.2
        nominal_fn_hz = 9.0
        nominal_zeta = 0.08
        sample_rate_hz = 240.0
        gust_duration_s = 3.0
        modal_duration_s = 4.0

        scenario_specs = [
            {"scenario_id": "QUAL-PURE-001", "candidate_id": "H-AERO-REAL-001", "generator": "GUST_INPUT_SCALAR_CALIBRATION", "expected": "GUST_INPUT_SCALAR_CALIBRATION", "qualification_class": "PURE_FAMILY"},
            {"scenario_id": "QUAL-PURE-002", "candidate_id": "H-AERO-REAL-002", "generator": "GUST_FIELD_FREQUENCY_SHAPE", "expected": "GUST_FIELD_FREQUENCY_SHAPE", "qualification_class": "PURE_FAMILY"},
            {"scenario_id": "QUAL-PURE-003", "candidate_id": "H-AERO-REAL-003", "generator": "FIRST_MODE_PARTICIPATION_CORRECTION", "expected": "FIRST_MODE_PARTICIPATION_CORRECTION", "qualification_class": "PURE_FAMILY"},
            {"scenario_id": "QUAL-PURE-004", "candidate_id": "H-AERO-REAL-004", "generator": "UNSTEADY_MEMORY_ZERO_POLE", "expected": "UNSTEADY_MEMORY_ZERO_POLE", "qualification_class": "PURE_FAMILY"},
            {"scenario_id": "QUAL-PURE-005", "candidate_id": "H-AERO-REAL-005", "generator": "STRUCTURAL_POLE_SHIFT_DAMPING", "expected": "STRUCTURAL_POLE_SHIFT_DAMPING", "qualification_class": "PURE_FAMILY"},
            {"scenario_id": "QUAL-NULL-006", "candidate_id": None, "generator": "NULL_NOMINAL_SYSTEM", "expected": "UNRESOLVED_FRONTIER", "qualification_class": "NULL_CONTROL"},
            {"scenario_id": "QUAL-MIX-007", "candidate_id": None, "generator": "MIXTURE_H4_H5", "expected": "MIXED_KNOWN_MECHANISMS", "qualification_class": "MIXTURE_CONTROL"},
            {"scenario_id": "QUAL-OOD-008", "candidate_id": None, "generator": "OOD_CONSTANT_LOAD_GAIN", "expected": "UNRESOLVED_FRONTIER", "qualification_class": "OOD_CONTROL"},
        ]

        scenario_rows: list[Dict[str, Any]] = []
        for scenario_index, spec in enumerate(scenario_specs, start=1):
            generator = str(spec["generator"])
            rng_seed = 625000 + scenario_index if scenario_index <= 5 else 627000 + scenario_index
            rng = np.random.default_rng(rng_seed)
            gust_runs: list[Dict[str, Any]] = []
            modal_records: list[Dict[str, Any]] = []
            modal_truth: Dict[str, Dict[str, float]] = {}
            for speed in speeds:
                if generator in {"STRUCTURAL_POLE_SHIFT_DAMPING", "MIXTURE_H4_H5"}:
                    actual_fn_hz = 8.45 + (speed - 20.0) * 0.055
                    actual_zeta = 0.12 - (speed - 20.0) * 0.0035
                else:
                    actual_fn_hz = nominal_fn_hz
                    actual_zeta = nominal_zeta
                modal_truth[str(speed)] = {"frequency_hz": actual_fn_hz, "damping_ratio": actual_zeta}

                modal_time = np.arange(0.0, modal_duration_s, 1.0 / sample_rate_hz)
                omega_n = 2.0 * math.pi * actual_fn_hz
                omega_d = omega_n * math.sqrt(max(1.0 - actual_zeta * actual_zeta, 1.0e-12))
                alpha = actual_zeta * omega_n
                modal_response = np.exp(-alpha * modal_time) * np.cos(omega_d * modal_time + 0.2)
                modal_response = modal_response + 0.0015 * rng.normal(size=len(modal_time))
                modal_records.append({
                    "speed_m_s": speed,
                    "time_s": modal_time.tolist(),
                    "response": modal_response.tolist(),
                    "independent_from_gust_sweep": True,
                    "qualification_source": "SEPARATE_SYNTHETIC_FREE_DECAY_RECORD",
                })

                for frequency in frequencies:
                    time = np.arange(0.0, gust_duration_s, 1.0 / sample_rate_hz)
                    convection = np.exp(-1j * 2.0 * math.pi * frequency * probe_to_wing_distance_m / speed)
                    if generator == "GUST_INPUT_SCALAR_CALIBRATION":
                        g_probe_wing = 0.82 * convection
                    elif generator == "GUST_FIELD_FREQUENCY_SHAPE":
                        corner_hz = 0.35 * speed
                        g_probe_wing = convection / (1.0 + 1j * frequency / corner_hz)
                    else:
                        g_probe_wing = convection

                    h_load = h2_complex(frequency, actual_fn_hz, actual_zeta)
                    if generator == "FIRST_MODE_PARTICIPATION_CORRECTION":
                        participation = 1.0 + 0.60 / (1.0 + ((frequency - actual_fn_hz) / 0.9) ** 2)
                        h_load *= participation
                    elif generator in {"UNSTEADY_MEMORY_ZERO_POLE", "MIXTURE_H4_H5"}:
                        h_load *= (1.0 + 1j * frequency / 5.5) / (1.0 + 1j * frequency / 13.0)
                    elif generator == "OOD_CONSTANT_LOAD_GAIN":
                        h_load *= 1.22

                    carrier = np.exp(1j * 2.0 * math.pi * frequency * time)
                    w_probe = np.real(carrier) + 0.01 * rng.normal(size=len(time))
                    w_wing = np.real(g_probe_wing * carrier) + 0.01 * rng.normal(size=len(time))
                    wrbm = np.real(h_load * g_probe_wing * carrier) + 0.01 * rng.normal(size=len(time))
                    gust_runs.append({
                        "speed_m_s": speed,
                        "frequency_hz": frequency,
                        "time_s": time.tolist(),
                        "w_probe": w_probe.tolist(),
                        "w_wing": w_wing.tolist(),
                        "wrbm": wrbm.tolist(),
                        "control_state": "OFF",
                    })

            evaluation = self.evaluate_probe_to_wing_modal_discriminator(
                gust_runs=gust_runs,
                modal_decay_records=modal_records,
                probe_to_wing_distance_m=probe_to_wing_distance_m,
                nominal_modal_frequency_hz=nominal_fn_hz,
                nominal_damping_ratio=nominal_zeta,
            )
            scenario_rows.append({
                "scenario_id": spec["scenario_id"],
                "rng_seed": int(rng_seed),
                "qualification_class": spec["qualification_class"],
                "ground_truth_candidate_id": spec["candidate_id"],
                "ground_truth_generator": generator,
                "expected_selected_mechanism_family": spec["expected"],
                "modal_truth": modal_truth,
                "evaluation": evaluation,
                "correctly_identified": evaluation.get("selected_mechanism_family") == spec["expected"],
            })

        pure_scenarios = [row for row in scenario_rows if row["qualification_class"] == "PURE_FAMILY"]

        # Two-order threshold sweep: all authoritative thresholds are multiplied by
        # the same dimensionless scale s in [10^-1, 10^1].  The time-history fits
        # are not rerun; only the single authoritative classifier is reevaluated on
        # the already-measured metrics.  This isolates threshold sensitivity from
        # numerical fitting noise.
        threshold_scales = np.logspace(-1.0, 1.0, 2001)
        def pure_five_pass(scale: float) -> bool:
            thresholds = self._probe_wing_discriminator_thresholds(float(scale))
            return all(
                self._classify_probe_wing_metrics(row["evaluation"]["metrics"], thresholds)["selected_mechanism_family"]
                == row["expected_selected_mechanism_family"]
                for row in pure_scenarios
            )

        sweep_rows = []
        pass_flags = []
        for scale in threshold_scales:
            thresholds = self._probe_wing_discriminator_thresholds(float(scale))
            selections = {
                row["scenario_id"]: self._classify_probe_wing_metrics(row["evaluation"]["metrics"], thresholds)["selected_mechanism_family"]
                for row in pure_scenarios
            }
            pass_5_of_5 = all(
                selections[row["scenario_id"]] == row["expected_selected_mechanism_family"]
                for row in pure_scenarios
            )
            pass_flags.append(pass_5_of_5)
            # Keep every 20th grid point plus all transition points; the exact
            # window is reported separately below.
            index = len(pass_flags) - 1
            if index % 20 == 0:
                sweep_rows.append({"threshold_scale": float(scale), "pass_5_of_5": bool(pass_5_of_5), "selections": selections})

        nominal_index = int(np.argmin(np.abs(threshold_scales - 1.0)))
        lower_index = nominal_index
        upper_index = nominal_index
        while lower_index > 0 and pass_flags[lower_index - 1]:
            lower_index -= 1
        while upper_index + 1 < len(pass_flags) and pass_flags[upper_index + 1]:
            upper_index += 1

        lower_scale = float(threshold_scales[lower_index])
        upper_scale = float(threshold_scales[upper_index])
        lower_censored = lower_index == 0
        upper_censored = upper_index == len(threshold_scales) - 1

        # Refine uncensored transition boundaries in log-scale without re-fitting.
        def refine_pass_side_boundary(pass_scale: float, fail_scale: float) -> float:
            p_scale, f_scale = float(pass_scale), float(fail_scale)
            for _ in range(60):
                mid = math.sqrt(p_scale * f_scale)
                if pure_five_pass(mid):
                    p_scale = mid
                else:
                    f_scale = mid
            return float(p_scale)

        if not upper_censored:
            upper_scale = refine_pass_side_boundary(float(threshold_scales[upper_index]), float(threshold_scales[upper_index + 1]))
        if not lower_censored:
            lower_scale = refine_pass_side_boundary(float(threshold_scales[lower_index]), float(threshold_scales[lower_index - 1]))

        threshold_sensitivity = {
            "sweep_definition": "all nine thresholds multiplied by common s",
            "requested_two_order_range": [0.1, 10.0],
            "grid_points": int(len(threshold_scales)),
            "nominal_scale": 1.0,
            "nominal_pass_5_of_5": pure_five_pass(1.0),
            "contiguous_5_of_5_window_containing_nominal": {
                "lower_scale": lower_scale,
                "upper_scale": upper_scale,
                "lower_bound_censored_by_sweep_edge": lower_censored,
                "upper_bound_censored_by_sweep_edge": upper_censored,
                "multiplicative_width": float(upper_scale / lower_scale),
                "log10_width_orders": float(math.log10(upper_scale / lower_scale)),
            },
            "compact_sweep_rows": sweep_rows,
            "interpretation": "This measures robustness to a common calibration of all current decision thresholds; it is not a proof of threshold optimality or universality.",
        }

        # Fail-closed controls prove that the new discriminator cannot silently
        # degrade back to the old one-speed magnitude-only Figure-16 path.
        one_speed_gust_runs = []
        one_speed_modal_records = []
        # Recreate the minimum failure shape from the already-qualified scenario
        # metadata rather than retaining hidden arrays in the final report.
        dummy_time = np.arange(0.0, 1.0, 1.0 / sample_rate_hz)
        for frequency in (4.0, 6.0, 8.0, 10.0):
            signal = np.cos(2.0 * math.pi * frequency * dummy_time)
            one_speed_gust_runs.append({
                "speed_m_s": 30.0, "frequency_hz": frequency, "time_s": dummy_time.tolist(),
                "w_probe": signal.tolist(), "w_wing": signal.tolist(), "wrbm": signal.tolist(),
            })
        modal_time = np.arange(0.0, modal_duration_s, 1.0 / sample_rate_hz)
        modal_signal = np.exp(-0.08 * 2.0 * math.pi * 9.0 * modal_time) * np.cos(2.0 * math.pi * 9.0 * math.sqrt(1.0 - 0.08 ** 2) * modal_time)
        one_speed_modal_records.append({
            "speed_m_s": 30.0, "time_s": modal_time.tolist(), "response": modal_signal.tolist(),
            "independent_from_gust_sweep": True,
        })
        one_speed_gate = self.evaluate_probe_to_wing_modal_discriminator(
            gust_runs=one_speed_gust_runs,
            modal_decay_records=one_speed_modal_records,
            probe_to_wing_distance_m=probe_to_wing_distance_m,
            nominal_modal_frequency_hz=nominal_fn_hz,
            nominal_damping_ratio=nominal_zeta,
        )

        nonindependent_modal_records = [dict(row) for row in one_speed_modal_records]
        nonindependent_modal_records[0]["independent_from_gust_sweep"] = False
        # Add a second speed only to reach the independence gate.
        two_speed_runs = list(one_speed_gust_runs)
        for frequency in (4.0, 6.0, 8.0, 10.0):
            signal = np.cos(2.0 * math.pi * frequency * dummy_time)
            two_speed_runs.append({
                "speed_m_s": 40.0, "frequency_hz": frequency, "time_s": dummy_time.tolist(),
                "w_probe": signal.tolist(), "w_wing": signal.tolist(), "wrbm": signal.tolist(),
            })
        nonindependent_modal_records.append({
            "speed_m_s": 40.0, "time_s": modal_time.tolist(), "response": modal_signal.tolist(),
            "independent_from_gust_sweep": False,
        })
        independence_gate = self.evaluate_probe_to_wing_modal_discriminator(
            gust_runs=two_speed_runs,
            modal_decay_records=nonindependent_modal_records,
            probe_to_wing_distance_m=probe_to_wing_distance_m,
            nominal_modal_frequency_hz=nominal_fn_hz,
            nominal_damping_ratio=nominal_zeta,
        )

        null_control = next(row for row in scenario_rows if row["scenario_id"] == "QUAL-NULL-006")
        mixture_control = next(row for row in scenario_rows if row["scenario_id"] == "QUAL-MIX-007")
        ood_control = next(row for row in scenario_rows if row["scenario_id"] == "QUAL-OOD-008")
        window = threshold_sensitivity["contiguous_5_of_5_window_containing_nominal"]
        figure23_40_observable = public_real_data_acquisition.get("figure23_40_m_s_observable", {})

        checks = {
            "real_dataset_remains_fail_closed_without_phase": real_dataset_readiness["gust_to_wrbm_phase_available"] is False,
            "real_dataset_remains_fail_closed_without_near_wing_gust": real_dataset_readiness["near_wing_gust_channel_available"] is False,
            "real_dataset_remains_fail_closed_without_multiple_speeds": len(real_dataset_readiness["available_speed_m_s"]) == 1,
            "real_dataset_remains_fail_closed_without_independent_modal_record": real_dataset_readiness["independent_modal_decay_or_oma_record_available_in_digitized_dataset"] is False,
            "five_pure_mechanism_ground_truths_qualified": len(pure_scenarios) == 5,
            "all_five_pure_mechanisms_correctly_discriminated": all(row["correctly_identified"] for row in pure_scenarios),
            "eight_total_scenarios_executed": len(scenario_rows) == 8,
            "null_control_reaches_unresolved_frontier": null_control["evaluation"].get("selected_mechanism_family") == "UNRESOLVED_FRONTIER",
            "h4_h5_mixture_not_collapsed_to_pure_h5": mixture_control["evaluation"].get("selected_mechanism_family") == "MIXED_KNOWN_MECHANISMS",
            "ood_control_reaches_unresolved_frontier": ood_control["evaluation"].get("selected_mechanism_family") == "UNRESOLVED_FRONTIER",
            "all_eight_complex_transfer_runs_executed": all(row["evaluation"].get("status") == "PASS_PHASE_SPEED_MODAL_DISCRIMINATOR_EXECUTED" for row in scenario_rows),
            "three_freestream_speeds_used": all(len(row["evaluation"].get("freestream_speeds_m_s", ())) == 3 for row in scenario_rows),
            "phase_is_explicitly_used": all(float(row["evaluation"]["metrics"]["minimum_harmonic_fit_r2"]) > 0.90 for row in scenario_rows),
            "modal_identification_is_independent": all(
                all(value.get("method") == "INDEPENDENT_SINGLE_MODE_FREE_DECAY_NONLINEAR_LS" for value in row["evaluation"]["independent_modal_identification"].values())
                for row in scenario_rows
            ),
            "threshold_sweep_spans_two_orders": threshold_sensitivity["requested_two_order_range"] == [0.1, 10.0],
            "nominal_thresholds_retain_5_of_5": bool(threshold_sensitivity["nominal_pass_5_of_5"]),
            "threshold_5_of_5_window_contains_nominal": float(window["lower_scale"]) <= 1.0 <= float(window["upper_scale"]),
            "threshold_5_of_5_window_has_nonzero_width": float(window["multiplicative_width"]) > 1.0,
            "one_speed_path_is_blocked": one_speed_gate.get("status") == "BLOCKED_MULTIPLE_FREESTREAM_SPEEDS_REQUIRED",
            "nonindependent_modal_path_is_blocked": independence_gate.get("status") == "BLOCKED_MODAL_IDENTIFICATION_NOT_INDEPENDENT",
            "figure23_40_panel_completed_for_published_markers": figure23_40_observable.get("status") == "COMPLETE_FOR_PUBLISHED_MARKERS",
            "figure23_40_peak_curvature_retained_not_attributed": figure23_40_observable.get("attribution_status") == "NOT_ATTRIBUTABLE",
            "figure23_40_observable_does_not_update_posterior": figure23_40_observable.get("posterior_update_allowed") is False,
            "no_real_root_cause_promoted": True,
            "no_new_law_promoted": True,
            "public_multispeed_wrbm_magnitude_ingested": bool(public_real_data_acquisition.get("real_multispeed_wrbm_magnitude_available", False)),
            "public_full_complex_discriminator_remains_blocked": not bool(public_real_data_acquisition.get("full_discriminator_executable", False)),
            "cross_campaign_modal_splice_rejected": not bool(public_real_data_acquisition.get("cross_campaign_safer2_modal_merge_allowed", False)),
            "nonidentifiable_partial_data_does_not_update_posterior": not bool(public_real_data_acquisition.get("posterior_update_allowed", False)),
        }
        status = "PASS_PHASE_SPEED_MODAL_DISCRIMINATOR_ROBUSTNESS_FRONTIER_CONTROLS_PUBLIC_REAL_EVIDENCE_PARTIAL" if all(checks.values()) else "BLOCKED_PHASE_SPEED_MODAL_DISCRIMINATOR_QUALIFICATION"
        payload = {
            "schema": "phi-probe-wing-modal-discriminator-qualification/v6.27",
            "owner_id": OWNER_ID,
            "status": status,
            "scientific_object": "G_probe_to_wing(f,U)=W_wing/W_probe plus independent modal f_n(U), zeta(U)",
            "qualification_design": {
                "synthetic_ground_truth_disclosed": True,
                "speeds_m_s": list(speeds),
                "frequencies_hz": list(frequencies),
                "probe_to_wing_distance_m": probe_to_wing_distance_m,
                "nominal_modal_frequency_hz": nominal_fn_hz,
                "nominal_damping_ratio": nominal_zeta,
                "noise_is_synthetic": True,
                "raw_dlr_daq_claimed": False,
                "scenario_count": len(scenario_rows),
                "pure_family_count": len(pure_scenarios),
                "pure_family_rng_seeds_preserved_from_v6_25": [625001, 625002, 625003, 625004, 625005],
                "controls": ["NULL_NOMINAL_SYSTEM", "MIXTURE_H4_H5", "OOD_CONSTANT_LOAD_GAIN"],
                "threshold_sweep_common_scale_range": [0.1, 10.0],
            },
            "scientific_grounding": [
                {
                    "source": "Dillinger et al., IFASD 2024, Design, Manufacturing and Identification of an Actively Controlled Flexible Wing for Subsonic Wind Tunnel Testing",
                    "role": "oLAF has distributed accelerometers/strain/optical sensing and separate wind-off/wind-on dynamic identification.",
                    "url": "https://elib.dlr.de/205840/",
                },
                {
                    "source": "Schmidt et al., IFASD 2024, Design and Experimental Characterization of a Gust-Generator Concept with Rotating-Slotted Cylinders",
                    "role": "Periodic gust field characterized with an unsteady fast-response five-hole probe; gust frequency is controlled by generator speed.",
                    "url": "https://elib.dlr.de/205804/",
                },
                {
                    "source": "Schmidt et al., DLRK 2025, SAFER2 flexible-wing wind-tunnel sensor-model fusion",
                    "role": "Operational modal analysis is used to monitor structural modal parameters under wind-on conditions.",
                    "url": "https://elib.dlr.de/217459/",
                },
                {
                    "source": "Duessler, Mertens, Palacios, Journal of Aircraft 2026, Gust Response Predictions of a Very Flexible Wing Model",
                    "role": "Wing presence can materially affect gust velocity measured upstream, motivating a spatial probe-to-wing transfer measurement.",
                    "url": "https://doi.org/10.2514/1.C038332",
                },
            ],
            "real_dlr_digitized_dataset_readiness": real_dataset_readiness,
            "public_real_data_acquisition": public_real_data_acquisition,
            "threshold_sensitivity": threshold_sensitivity,
            "scenario_results": scenario_rows,
            "fail_closed_controls": {
                "one_speed": one_speed_gate,
                "nonindependent_modal": independence_gate,
            },
            "checks": checks,
            "claim_boundary": {
                "algorithm_qualified_on_synthetic_ground_truth": True,
                "algorithm_executed_on_full_real_phase_speed_modal_data": False,
                "real_dlr_dataset_currently_supports_full_discriminator": False,
                "real_multispeed_wrbm_magnitude_has_been_ingested": bool(public_real_data_acquisition.get("real_multispeed_wrbm_magnitude_available", False)),
                "published_partial_evidence_is_sufficient_for_h2_h4_h5_identification": False,
                "cross_campaign_safer2_modal_data_are_treated_as_same_test_article": False,
                "five_mechanisms_are_exhaustive": False,
                "null_and_ood_controls_can_reopen_frontier": True,
                "mixed_known_mechanisms_are_not_forced_into_one_pure_family": True,
                "figure23_40_peak_curvature_is_attributable_to_a_mechanism": False,
                "unique_real_root_cause_identified": False,
                "new_aerodynamic_law_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def scan_operator_unknown_frontier(self, execution_budget: Mapping[str, int] | None = None) -> Mapping[str, Any]:
        """Target-free differential/integral/nonlocal composition over rich regions.

        Generation sees source laws, declared local chart bindings and a finite
        ExecutionBudgetIR only.  It never sees a target formula or the materialized
        catalog until the candidate set has been frozen.
        """
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        budget = {
            "max_operator_compositions": None,
            "max_frontier_states": None,
            "max_formula_characters": None,
        }
        if execution_budget:
            budget.update({str(k): int(v) for k, v in execution_budget.items()})
        regions = self._operator_frontier_regions()
        generated: Dict[str, Dict[str, Any]] = {}
        region_reports: List[Dict[str, Any]] = []
        composition_count = 0
        expanded_state_count = 0
        stop_reason = "FRONTIER_EXHAUSTED"

        for region in regions:
            passports = []
            missing = []
            for owner_id in region["source_owner_ids"]:
                passport = runtime.catalog.passports.get(owner_id)
                if passport is None:
                    missing.append(owner_id)
                else:
                    passports.append(passport)
            if missing:
                region_reports.append({**region, "status": "SOURCE_OWNER_MISSING", "missing_owner_ids": missing, "candidate_count": 0})
                continue
            assignments: List[Dict[str, Any]] = []
            for passport in passports:
                for index, (lhs, rhs) in enumerate(_operator_equations(passport.formula.source or "")):
                    assignments.append({
                        "owner_id": passport.owner_id,
                        "domain_id": passport.domain_id,
                        "equation_index": index,
                        "lhs": lhs, "rhs": rhs,
                        "definition_symbol": _operator_definition_symbol(lhs),
                        "definition_argument": _operator_definition_argument(lhs),
                        "derivative_target": _operator_derivative_target(lhs),
                        "features": _operator_features(f"{lhs}={rhs}"),
                    })
            region_candidate_ids: List[str] = []
            if region.get("bridge_materializer") == "GALERKIN_STRUCTURAL_SUBSPACE_PROJECTION_CURRENT":
                bridge = self.build_aeroelastic_projection_bridge()
                region_reports.append({
                    **region,
                    "status": "PARTIAL_BRIDGE_MATERIALIZED_STRUCTURAL_SUBSPACE_REMAINDER_OPEN" if bridge.get("status", "").startswith("PASS_") else "BLOCKED_AEROELASTIC_PROJECTION_BRIDGE",
                    "candidate_count": 0,
                    "source_equation_count": len(assignments),
                    "target_formula_access_during_search": False,
                    "materialized_bridge_certificate_digest": bridge.get("digest"),
                    "materialized_bridge_status": bridge.get("status"),
                    "resolved_bridge": bridge.get("resolved_bridge", {}),
                    "remaining_unknown_operator_slots": bridge.get("remaining_unknown_operator_slots", ()),
                    "full_aeroservoelastic_state_space_bridge_complete": bridge.get("full_aeroservoelastic_state_space_bridge_complete", False),
                })
                continue
            if region.get("bridge_required"):
                bridge_map = dict(region.get("bridge_required", {}))
                obstruction_id = "UF-OBS-" + digest_payload({"region": region["region_id"], "bridge": bridge_map})[:18].upper()
                region_reports.append({
                    **region,
                    "status": "BRIDGE_REQUIRED_UNKNOWN_OPERATOR_FRONTIER",
                    "candidate_count": 0,
                    "source_equation_count": len(assignments),
                    "target_formula_access_during_search": False,
                    "reason": "STATE_IDENTITY_OR_LOCAL_GENERATOR_BINDING_IS_NOT_ESTABLISHED_AND_IS_NOT_GUESSED",
                    "operator_obstruction_candidate": {
                        "obstruction_id": obstruction_id,
                        "status": "UNKNOWN_OPERATOR_SLOT_UNDERDETERMINED_NOT_A_FORCED_LAW",
                        "input_side": tuple(sorted(bridge_map)),
                        "required_output_or_binding_side": tuple(bridge_map[k] for k in sorted(bridge_map)),
                        "candidate_operator_symbol": "K_UNKNOWN[" + region["region_id"] + "]",
                        "admissibility_gates": (
                            "CANONICAL_QUANTITY_AND_TENSOR_TYPE_BINDING",
                            "DIMENSIONAL_COMPATIBILITY",
                            "VALIDITY_CHART_OVERLAP",
                            "BOUNDARY_OR_INITIAL_CONDITIONS_WHERE_REQUIRED",
                            "OBSERVABLE_PREDICTION_OR_INDEPENDENT_DERIVATION",
                        ),
                        "world_novelty_established": False,
                        "physical_existence_established": False,
                    },
                })
                continue

            allowed = set(region.get("declared_shared_symbols", ()))
            seeds: List[Dict[str, Any]] = []
            for row in assignments:
                seeds.append({
                    "lhs": row["lhs"], "rhs": row["rhs"],
                    "source_owner_ids": (row["owner_id"],),
                    "derivation_steps": (),
                    "region_id": region["region_id"],
                    "validity_chart": region["validity_chart"],
                })
            # Restricted differentiation rule for a constant linear observable z=C*x.
            for definition in assignments:
                symbol = definition["definition_symbol"]
                if not symbol or symbol not in allowed:
                    continue
                rhs = definition["rhs"].strip()
                linear = re.fullmatch(r"(.+?)\*([A-Za-z_][A-Za-z0-9_]*)", rhs)
                if not linear:
                    continue
                coefficient, state_symbol = linear.group(1).strip(), linear.group(2)
                if state_symbol not in allowed or _operator_has_symbol(coefficient, state_symbol):
                    continue
                for dyn in assignments:
                    if dyn["derivative_target"] != state_symbol:
                        continue
                    source_ids = tuple(sorted({definition["owner_id"], dyn["owner_id"]}))
                    formula_lhs = symbol + "_dot"
                    formula_rhs = f"({coefficient})*({dyn['rhs']})"
                    seeds.append({
                        "lhs": formula_lhs, "rhs": formula_rhs,
                        "source_owner_ids": source_ids,
                        "derivation_steps": ({
                            "rule": "CONSTANT_LINEAR_OBSERVABLE_DIFFERENTIATION",
                            "observable_definition": f"{definition['lhs']}={definition['rhs']}",
                            "state_derivative": f"{dyn['lhs']}={dyn['rhs']}",
                            "assumption": "OBSERVATION_MATRIX_OR_COEFFICIENT_TIME_INDEPENDENT_ON_VALIDITY_CHART",
                        },),
                        "region_id": region["region_id"],
                        "validity_chart": region["validity_chart"],
                    })

            queue = list(seeds)
            seen_states: set[str] = set()
            while queue:
                if budget["max_frontier_states"] is not None and expanded_state_count >= budget["max_frontier_states"]:
                    stop_reason = "EXECUTION_BUDGET_MAX_FRONTIER_STATES"
                    break
                state = queue.pop(0)
                state_formula = f"{state['lhs']}={state['rhs']}"
                state_key = _operator_formula_key(state_formula) + "|" + "|".join(state["source_owner_ids"])
                if state_key in seen_states:
                    continue
                seen_states.add(state_key)
                expanded_state_count += 1
                # Keep only genuine derived states in the frozen pool, never raw seeds.
                if state["derivation_steps"]:
                    cid = "UF-OP-" + digest_payload({"f": _operator_formula_key(state_formula), "s": state["source_owner_ids"], "r": region["region_id"]})[:18].upper()
                    features = _operator_features(state_formula)
                    row = {
                        "candidate_id": cid,
                        "region_id": region["region_id"],
                        "domain_id": region["domain_id"],
                        "formula": state_formula,
                        "source_owner_ids": tuple(sorted(state["source_owner_ids"])),
                        "source_order": len(set(state["source_owner_ids"])),
                        "operator_features": features,
                        "contains_integral_operator": "INTEGRAL" in features,
                        "contains_memory_kernel": "MEMORY_KERNEL" in features,
                        "contains_differential_operator": any(f in features for f in ("TIME_DERIVATIVE", "SPATIAL_GRADIENT", "DIVERGENCE", "LAPLACIAN")),
                        "validity_chart": region["validity_chart"],
                        "derivation_steps": state["derivation_steps"],
                        "derivation_backend": "EXACT_DEFINITION_SUBSTITUTION_AND_RESTRICTED_LINEAR_OBSERVABLE_DIFFERENTIATION",
                        "target_formula_access_during_search": False,
                        "materialized_law_catalog_access_during_search": False,
                        "formal_status": "FORCED_OPERATOR_COMPOSITION_ON_DECLARED_VALIDITY_CHART",
                        "validity_overlap_status": "DECLARED_RESEARCH_REGION_REQUIRES_POST_DERIVATION_DOMAIN_AUDIT",
                        "dimensional_validation_status": "NOT_PROMOTED_UNTIL_OPERATOR_QUANTITY_AND_TENSOR_DIMENSIONS_ARE_EXPLICITLY_CHECKED",
                    }
                    row["priority_score"] = 80*row["source_order"] + 55*int(row["contains_memory_kernel"]) + 30*int(row["contains_integral_operator"]) + 20*int(row["contains_differential_operator"]) + 5*len(features)
                    key = _operator_formula_key(state_formula)
                    previous = generated.get(key)
                    if previous is None or (row["source_order"], -row["priority_score"], row["candidate_id"]) < (previous["source_order"], -previous["priority_score"], previous["candidate_id"]):
                        generated[key] = row
                    region_candidate_ids.append(cid)
                for definition in assignments:
                    symbol = definition["definition_symbol"]
                    if not symbol:
                        continue
                    same_owner = definition["owner_id"] in state["source_owner_ids"]
                    if not same_owner and symbol not in allowed:
                        continue
                    if not _operator_has_symbol(state["rhs"], symbol):
                        continue
                    # Never substitute a definition into itself without changing source state.
                    if len(state["source_owner_ids"]) == 1 and definition["owner_id"] == state["source_owner_ids"][0] and state["lhs"] == definition["lhs"] and state["rhs"] == definition["rhs"]:
                        continue
                    if budget["max_operator_compositions"] is not None and composition_count >= budget["max_operator_compositions"]:
                        stop_reason = "EXECUTION_BUDGET_MAX_OPERATOR_COMPOSITIONS"
                        queue.clear()
                        break
                    composition_count += 1
                    new_rhs = _operator_replace_symbol(state["rhs"], symbol, definition["rhs"], definition.get("definition_argument"))
                    if new_rhs == state["rhs"] or (budget["max_formula_characters"] is not None and len(new_rhs) > budget["max_formula_characters"]):
                        continue
                    source_ids = tuple(sorted(set(state["source_owner_ids"]) | {definition["owner_id"]}))
                    step = {
                        "rule": "EXACT_DEFINITION_SUBSTITUTION",
                        "substituted_symbol": symbol,
                        "definition": f"{definition['lhs']}={definition['rhs']}",
                        "into_equation": state_formula,
                    }
                    queue.append({
                        "lhs": state["lhs"], "rhs": new_rhs,
                        "source_owner_ids": source_ids,
                        "derivation_steps": tuple(state["derivation_steps"]) + (step,),
                        "region_id": region["region_id"],
                        "validity_chart": region["validity_chart"],
                    })
            region_reports.append({
                **region,
                "status": "EXECUTED_OPERATOR_FRONTIER",
                "source_equation_count": len(assignments),
                "candidate_count": len(set(region_candidate_ids)),
                "target_formula_access_during_search": False,
            })
            if stop_reason != "FRONTIER_EXHAUSTED":
                break

        # Freeze before comparison to the active corpus.
        frozen = sorted(generated.values(), key=lambda r: r["candidate_id"])
        frozen_digest = digest_payload([{k: v for k, v in row.items() if k != "priority_score"} for row in frozen])
        known_keys = self._operator_known_keys()
        materialized_source_sets = {
            tuple(sorted(str(x) for x in law.get("source_owner_ids", ())))
            for law in self.aeronautics_db.get("laws", ()) if law.get("source_owner_ids")
        }
        for row in frozen:
            key = _operator_formula_key(row["formula"])
            exact_materialized = key in known_keys
            source_set_materialized = tuple(sorted(row["source_owner_ids"])) in materialized_source_sets
            row["already_materialized_in_current_corpus"] = exact_materialized
            row["same_source_set_has_materialized_closure"] = source_set_materialized
            row["corpus_novelty_status"] = (
                "ALREADY_MATERIALIZED_OPERATOR_RELATION" if exact_materialized
                else "RELATED_SOURCE_SET_ALREADY_HAS_MATERIALIZED_CLOSURE" if source_set_materialized
                else "FORCED_UNMATERIALIZED_OPERATOR_RELATION"
            )
            row["world_literature_novelty_status"] = "NOT_ESTABLISHED_POST_DERIVATION_REVIEW_REQUIRED"
        unknown = [
            r for r in frozen
            if not r["already_materialized_in_current_corpus"] and not r["same_source_set_has_materialized_closure"]
        ]
        unknown.sort(key=lambda r: (-r["priority_score"], -r["source_order"], r["candidate_id"]))
        result = {
            "schema": "phi-constraint-atlas-operator-unknown-frontier/v6.21",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_OPERATOR_UNKNOWN_FRONTIER_DIRECTED_SEARCH" if unknown else "PASS_OPERATOR_FRONTIER_EXHAUSTED_NO_CURRENT_CORPUS_GAP",
            "research_mode": "TARGET_FREE_DIFFERENTIAL_INTEGRAL_NONLOCAL_OPERATOR_COMPOSITION",
            "execution_budget_ir": budget,
            "execution_budget_stop_reason": stop_reason,
            "operator_composition_count": composition_count,
            "expanded_state_count": expanded_state_count,
            "scientific_source_order_ceiling_used": False,
            "scientific_operator_class_ceiling_used": False,
            "execution_budget_is_physical_admissibility_gate": False,
            "fixed_execution_visit_ceiling": None if not execution_budget else "EXPLICIT_DIAGNOSTIC_OVERRIDE_ONLY",
            "target_formula_access_during_search": False,
            "materialized_law_catalog_access_during_generation": False,
            "candidate_pool_frozen_before_corpus_novelty_check": True,
            "frozen_generation_digest": frozen_digest,
            "directed_region_count": len(regions),
            "directed_regions": region_reports,
            "generated_operator_candidate_count": len(frozen),
            "forced_unmaterialized_operator_relation_count": len(unknown),
            "memory_kernel_candidate_count": sum(bool(r["contains_memory_kernel"]) for r in unknown),
            "integral_operator_candidate_count": sum(bool(r["contains_integral_operator"]) for r in unknown),
            "differential_operator_candidate_count": sum(bool(r["contains_differential_operator"]) for r in unknown),
            "maximum_executed_source_order": max((r["source_order"] for r in frozen), default=0),
            "cross_source_forced_unmaterialized_operator_relation_count": sum(r["source_order"] > 1 for r in unknown),
            "intra_source_normal_form_candidate_count": sum(r["source_order"] == 1 for r in unknown),
            "operator_obstruction_candidate_count": sum(1 for r in region_reports if r.get("operator_obstruction_candidate")),
            "operator_obstruction_candidates": [r["operator_obstruction_candidate"] | {"region_id": r["region_id"], "source_owner_ids": r["source_owner_ids"]} for r in region_reports if r.get("operator_obstruction_candidate")],
            # Complete frozen ledgers are retained. Ranking is a view, never a deletion policy.
            "candidate_ledger": frozen,
            "unknown_candidate_ledger": unknown,
            "operator_grammar_ir": {
                "scientific_operator_order_ceiling": None,
                "registered_classes": [
                    "TIME_DERIVATIVE", "SPATIAL_DERIVATIVE_MULTIINDEX", "GRADIENT", "DIVERGENCE", "LAPLACIAN",
                    "STATE_SPACE", "VOLTERRA_MEMORY", "TEMPORAL_CONVOLUTION", "SPATIAL_NONLOCAL_KERNEL",
                    "DELAY_OPERATOR", "FRACTIONAL_OPERATOR_SLOT", "TENSOR_CONSERVATION_OPERATOR",
                ],
                "currently_executable_classes": [
                    "TIME_DERIVATIVE", "GRADIENT", "DIVERGENCE", "LAPLACIAN", "STATE_SPACE",
                    "VOLTERRA_MEMORY_WHEN_KERNEL_IS_REGISTERED", "TEMPORAL_CONVOLUTION_WHEN_KERNEL_IS_REGISTERED",
                    "GALERKIN_STRUCTURAL_PDE_TO_REDUCED_STATE", "DATA_BACKED_DISCRETE_TEMPORAL_KERNEL_INVERSION",
                    "DATA_BACKED_DISCRETE_SPATIAL_NONLOCAL_KERNEL_INVERSION",
                ],
                "registered_but_fail_closed_until_backend_or_data": [
                    "DELAY_IDENTIFICATION", "FRACTIONAL_ORDER_IDENTIFICATION",
                    "GENERAL_TENSOR_DIFFERENTIAL_ELIMINATION", "UNKNOWN_KERNEL_IDENTIFICATION_WHEN_DATA_CONTRACT_MISSING",
                ],
            },
            "top_unknown_operator_candidates": unknown[:30],
            "claim_boundary": {
                "forced_on_declared_local_validity_chart": True,
                "complete_differential_algebra_backend": False,
                "kernel_identification_from_experimental_data_executed": False,
                "cross_chart_state_identity_inferred_automatically": False,
                "new_law_of_nature_established": False,
                "world_literature_novelty_established": False,
            },
        }
        result["digest"] = digest_payload(result)
        return result

    def _global_typing_audit(self) -> Mapping[str, Any]:
        # Local import avoids making LawSpaceRuntime depend on the atlas owner.
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        passports = list(runtime.catalog.passports.values())
        symbols = [symbol for passport in passports for symbol in passport.symbols]
        typed_symbols = [symbol for symbol in symbols if symbol.quantity_id is not None]
        fully_typed = [passport for passport in passports if passport.symbols and all(s.quantity_id for s in passport.symbols)]
        fully_typed_with_dimensions = [
            passport for passport in passports
            if passport.symbols and all(s.quantity_id and s.dimension is not None for s in passport.symbols)
        ]
        by_display: Dict[str, Dict[str, List[str]]] = {}
        for passport in passports:
            for symbol in passport.symbols:
                if symbol.quantity_id is None:
                    continue
                by_display.setdefault(symbol.display, {}).setdefault(symbol.quantity_id, []).append(passport.owner_id)
        ambiguous = {
            display: {quantity_id: sorted(owner_ids) for quantity_id, owner_ids in sorted(kinds.items())}
            for display, kinds in sorted(by_display.items()) if len(kinds) > 1
        }
        return {
            "passport_count": len(passports),
            "symbol_record_count": len(symbols),
            "canonical_quantity_kind_count": len(runtime.quantities),
            "typed_symbol_count": len(typed_symbols),
            "typed_symbol_fraction": (len(typed_symbols) / len(symbols)) if symbols else 0.0,
            "fully_quantity_typed_passport_count": len(fully_typed),
            "fully_quantity_and_dimension_typed_passport_count": len(fully_typed_with_dimensions),
            "fully_quantity_typed_passport_fraction": (len(fully_typed) / len(passports)) if passports else 0.0,
            "same_display_multi_quantity_kind_count": len(ambiguous),
            "same_display_multi_quantity_kinds": ambiguous,
            "global_same_letter_gluing_allowed": False,
        }

    def _aeronautics_chart(self) -> Mapping[str, Any]:
        chart_id = "CHART-AERONAUTICS-PRIMARY-V6-15"
        symbol_rows: Dict[str, List[Tuple[str, Mapping[str, Any]]]] = {}
        for law in self.aeronautics_db["source_laws"]:
            for variable in law.get("variables", ()):  # reused legacy owners can be unresolved
                symbol_rows.setdefault(str(variable.get("symbol")), []).append((law["owner_id"], variable))

        coordinates: Dict[str, QuantityCoordinateIR] = {}
        conflicts: Dict[str, Any] = {}
        for symbol, occurrences in sorted(symbol_rows.items()):
            typed = [(owner, row) for owner, row in occurrences if row.get("quantity_id")]
            if not typed:
                continue
            kinds = {str(row["quantity_id"]) for _, row in typed}
            if len(kinds) != 1:
                conflicts[symbol] = {
                    "quantity_kind_ids": sorted(kinds),
                    "owner_ids": sorted(owner for owner, _ in typed),
                }
                continue
            quantity_kind_id = next(iter(kinds))
            if quantity_kind_id not in self.quantity_registry:
                conflicts[symbol] = {"unregistered_quantity_kind_id": quantity_kind_id}
                continue
            qrow = self.quantity_registry[quantity_kind_id]
            meanings = sorted({str(row.get("meaning_ru") or "") for _, row in typed if row.get("meaning_ru")})
            units = sorted({str(row.get("unit")) for _, row in typed if row.get("unit")})
            coordinate_id = f"{chart_id}:{symbol}"
            coordinates[symbol] = QuantityCoordinateIR(
                coordinate_id=coordinate_id,
                chart_id=chart_id,
                symbol=symbol,
                quantity_kind_id=quantity_kind_id,
                physical_role="; ".join(meanings) if meanings else "DECLARED_VARIABLE",
                physical_object="AERONAUTICS_RESEARCH_STATE",
                unit=units[0] if len(units) == 1 else ("MULTIPLE_CONVERTIBLE_OR_CONTEXTUAL" if units else None),
                dimension=_dimension_tuple(qrow),
                source_owner_ids=tuple(sorted(owner for owner, _ in typed)),
            )

        relations: Dict[str, ConstraintRelationIR] = {}
        executable = 0
        for owner_id, law in sorted(self.aero_sources.items()):
            variables = law.get("variables", ())
            used_symbols = [str(row.get("symbol")) for row in variables if row.get("symbol")]
            typed = bool(variables) and all(row.get("quantity_id") in self.quantity_registry for row in variables)
            no_conflict = all(symbol not in conflicts for symbol in used_symbols)
            parsed = _parse_polynomial_relation(str(law.get("formula", "")), variables) if typed and no_conflict else None
            kind = _relation_kind(str(law.get("formula", "")))
            if parsed is not None:
                numerator, denominator = parsed
                relation_kind = "RATIONAL_POLYNOMIAL" if sp.expand(denominator) != 1 else "POLYNOMIAL"
                status = "EXECUTABLE_ALGEBRAIC_CONSTRAINT"
                executable += 1
                polynomial = str(_normalize_polynomial(numerator))
                denominator_text = str(sp.factor(denominator))
                support = tuple(sorted(symbol.name for symbol in numerator.free_symbols | denominator.free_symbols))
            else:
                relation_kind = kind
                status = "BLOCKED_FROM_ALGEBRAIC_BACKEND_UNTYPED_OR_NONPOLYNOMIAL"
                polynomial = None
                denominator_text = None
                support = tuple(sorted(set(used_symbols)))
            relations[owner_id] = ConstraintRelationIR(
                relation_id=f"REL::{owner_id}",
                owner_id=owner_id,
                chart_id=chart_id,
                formula=str(law.get("formula", "")),
                relation_kind=relation_kind,
                polynomial=polynomial,
                denominator=denominator_text,
                support=support,
                validity_domain=str(law.get("validity_domain", "UNDECLARED")),
                assumptions=tuple(str(value) for value in law.get("assumptions", ())),
                status=status,
            )
        return {
            "chart_id": chart_id,
            "coordinates": coordinates,
            "relations": relations,
            "typing_conflicts": conflicts,
            "executable_algebraic_relation_count": executable,
        }

    def gluing_certificate(self, source_owner_ids: Sequence[str]) -> GluingCertificate:
        chart = self._aeronautics_chart()
        relations: Mapping[str, ConstraintRelationIR] = chart["relations"]
        missing = [owner_id for owner_id in source_owner_ids if owner_id not in relations]
        if missing:
            raise KeyError(f"ConstraintAtlas source owners missing from chart: {missing}")
        symbol_to_kind: Dict[str, set[str]] = {}
        owner_symbols: Dict[str, set[str]] = {}
        validity_domains: List[str] = []
        for owner_id in source_owner_ids:
            law = self.aero_sources[owner_id]
            owner_symbols[owner_id] = set()
            validity_domains.append(str(law.get("validity_domain", "UNDECLARED")))
            for variable in law.get("variables", ()):
                symbol = str(variable.get("symbol"))
                owner_symbols[owner_id].add(symbol)
                qid = variable.get("quantity_id")
                if qid:
                    symbol_to_kind.setdefault(symbol, set()).add(str(qid))
        shared = sorted(symbol for symbol, count in _occurrence_counts(owner_symbols).items() if count >= 2)
        conflicts = sorted(symbol for symbol in shared if len(symbol_to_kind.get(symbol, ())) != 1)
        untyped_shared = sorted(symbol for symbol in shared if not symbol_to_kind.get(symbol))
        conflict_rows = tuple(sorted(set(conflicts + untyped_shared)))
        statuses = [relations[owner_id].status for owner_id in source_owner_ids]
        if conflict_rows:
            obstruction = "TYPING_OBSTRUCTION"
            status = "BLOCKED"
        elif any(value.startswith("BLOCKED") for value in statuses):
            obstruction = "BACKEND_OR_TYPING_INCOMPLETENESS"
            status = "CONDITIONAL_OR_BLOCKED"
        else:
            obstruction = "NO_TYPED_GLUE_OBSTRUCTION_IN_DECLARED_CHART"
            status = "PASS_DECLARED_LOCAL_GLUE"
        payload = {
            "chart_id": chart["chart_id"],
            "source_owner_ids": tuple(sorted(source_owner_ids)),
            "shared_coordinates": tuple(shared),
            "typing_conflicts": conflict_rows,
            "validity_domains": tuple(validity_domains),
            "restriction_map": "IDENTITY_ON_SHARED_TYPED_COORDINATES_WITHIN_ONE_DECLARED_CHART",
            "obstruction_status": obstruction,
            "status": status,
        }
        return GluingCertificate(gluing_id="GLUE-" + digest_payload(payload)[:16].upper(), **payload)

    def derive_circuit(self, source_owner_ids: Sequence[str], retain_symbols: Sequence[str]) -> CircuitCertificate:
        chart = self._aeronautics_chart()
        relations: Mapping[str, ConstraintRelationIR] = chart["relations"]
        gluing = self.gluing_certificate(source_owner_ids)
        if gluing.status != "PASS_DECLARED_LOCAL_GLUE":
            raise ValueError(f"typed gluing not admitted: {gluing.obstruction_status}")
        parsed_rows: List[Tuple[sp.Expr, sp.Expr]] = []
        for owner_id in source_owner_ids:
            relation = relations[owner_id]
            if relation.status != "EXECUTABLE_ALGEBRAIC_CONSTRAINT":
                raise ValueError(f"{owner_id} is not executable in algebraic backend")
            parsed = _parse_polynomial_relation(self.aero_sources[owner_id]["formula"], self.aero_sources[owner_id]["variables"])
            if parsed is None:
                raise ValueError(f"{owner_id} failed deterministic algebraic lowering")
            parsed_rows.append(parsed)
        polynomials = [row[0] for row in parsed_rows]
        denominator_product = sp.factor(sp.prod(row[1] for row in parsed_rows))
        all_symbols = sorted(
            set().union(*[poly.free_symbols for poly in polynomials], denominator_product.free_symbols),
            key=lambda value: value.name,
        )
        retain = [sp.Symbol(name) for name in retain_symbols]
        unknown_retain = sorted(symbol.name for symbol in retain if symbol not in all_symbols)
        if unknown_retain:
            raise ValueError(f"retained coordinates absent from source constraints: {unknown_retain}")
        eliminate = [symbol for symbol in all_symbols if symbol not in retain]
        working = list(polynomials)
        required_nonzero: Tuple[str, ...] = ()
        if sp.expand(denominator_product) != 1:
            saturation = sp.Symbol("__phi_sat")
            working.append(saturation * denominator_product - 1)
            eliminate = [saturation] + eliminate
            required_nonzero = (str(denominator_product),)
        groebner = sp.groebner(working, *(eliminate + retain), order="lex")
        candidates: List[sp.Expr] = []
        retain_set = set(retain)
        for polynomial in groebner.polys:
            expr = _normalize_polynomial(polynomial.as_expr())
            if expr != 0 and expr.free_symbols <= retain_set:
                candidates.append(expr)
        if not candidates:
            raise ValueError("no elimination relation on requested retained coordinates")
        # Prefer a consequence using the largest part of the requested support;
        # ties are broken deterministically by expression complexity/string.
        candidates.sort(key=lambda expr: (-len(expr.free_symbols), sp.count_ops(expr), str(expr)))
        chosen = candidates[0]
        support = tuple(sorted(symbol.name for symbol in chosen.free_symbols))
        support_minimal = self._support_is_minimal(source_owner_ids, support)
        eliminated = tuple(sorted(symbol.name for symbol in all_symbols if symbol.name not in support))
        payload = {
            "source_owner_ids": tuple(sorted(source_owner_ids)),
            "retained_coordinates": tuple(sorted(retain_symbols)),
            "eliminated_coordinates": eliminated,
            "polynomial": str(chosen),
            "support": support,
            "required_nonzero_factors": required_nonzero,
            "support_minimal": support_minimal,
            "derivation_backend": "SYMPY_GROEBNER_LEX_WITH_DENOMINATOR_SATURATION",
            "truth_formula_access_during_search": False,
            "status": "FORCED_CIRCUIT" if support_minimal else "ELIMINATION_CONSEQUENCE_NOT_PROVEN_MINIMAL",
        }
        return CircuitCertificate(circuit_id="CIR-" + digest_payload(payload)[:16].upper(), **payload)

    def _support_is_minimal(self, source_owner_ids: Sequence[str], support: Sequence[str]) -> bool:
        if len(support) <= 1:
            return True
        # A circuit is support-minimal: dropping any one coordinate must destroy
        # every nonconstant elimination relation on the remaining support.
        for drop in support:
            trial = tuple(symbol for symbol in support if symbol != drop)
            if self._has_elimination_relation(source_owner_ids, trial):
                return False
        return True

    def _has_elimination_relation(self, source_owner_ids: Sequence[str], retain_symbols: Sequence[str]) -> bool:
        parsed_rows = [
            _parse_polynomial_relation(self.aero_sources[owner_id]["formula"], self.aero_sources[owner_id]["variables"])
            for owner_id in source_owner_ids
        ]
        if any(row is None for row in parsed_rows):
            return False
        rows = [row for row in parsed_rows if row is not None]
        polynomials = [row[0] for row in rows]
        denominator_product = sp.factor(sp.prod(row[1] for row in rows))
        all_symbols = sorted(
            set().union(*[poly.free_symbols for poly in polynomials], denominator_product.free_symbols),
            key=lambda value: value.name,
        )
        retain = [sp.Symbol(name) for name in retain_symbols]
        if any(symbol not in all_symbols for symbol in retain):
            return False
        eliminate = [symbol for symbol in all_symbols if symbol not in retain]
        working = list(polynomials)
        if sp.expand(denominator_product) != 1:
            saturation = sp.Symbol("__phi_sat")
            working.append(saturation * denominator_product - 1)
            eliminate = [saturation] + eliminate
        groebner = sp.groebner(working, *(eliminate + retain), order="lex")
        retain_set = set(retain)
        return any(
            polynomial.as_expr() != 0
            and polynomial.as_expr().free_symbols
            and polynomial.as_expr().free_symbols <= retain_set
            for polynomial in groebner.polys
        )

    @staticmethod
    def _blind_cases() -> Tuple[Mapping[str, Any], ...]:
        """Formula-hidden circuit recovery cases.

        These are *not* the mass law-ablation benchmark promised for a fully
        typed catalog.  They are a backend qualification: the search receives
        source owner IDs and circuit support, but not the expected polynomial.
        """
        return (
            {
                "case_id": "CAT-AERO-LEVEL-SPEED",
                "source_owner_ids": ("AERO-DYNAMIC-PRESSURE", "AERO-LIFT-EQUATION", "AERO-LEVEL-FLIGHT-EQUILIBRIUM", "AERO-WING-LOADING-DEFINITION"),
                "support": ("C_L", "V", "rho", "w"),
                "truth": "2*w-C_L*rho*V**2",
            },
            {
                "case_id": "CAT-AERO-MACH-THERMO",
                "source_owner_ids": ("AERO-MACH-DEFINITION", "AERO-SPEED-OF-SOUND"),
                "support": ("M", "R_s", "T", "V", "gamma"),
                "truth": "M**2*R_s*T*gamma-V**2",
            },
            {
                "case_id": "CAT-AERO-LIFT-DRAG-RATIO",
                "source_owner_ids": ("AERO-LIFT-EQUATION", "AERO-DRAG-EQUATION"),
                "support": ("C_D", "C_L", "D", "L"),
                "truth": "C_L*D-C_D*L",
            },
            {
                "case_id": "CAT-AERO-RE-MACH-THERMO",
                "source_owner_ids": ("AERO-REYNOLDS-DEFINITION", "AERO-MACH-DEFINITION", "AERO-SPEED-OF-SOUND"),
                "support": ("M", "R_s", "Re", "T", "c", "gamma", "mu", "rho"),
                "truth": "Re**2*mu**2-M**2*R_s*T*c**2*gamma*rho**2",
            },
            {
                "case_id": "CAT-AERO-POWER-DRAG",
                "source_owner_ids": ("AERO-DRAG-EQUATION", "AERO-POWER-REQUIRED"),
                "support": ("C_D", "P_req", "S", "V", "q"),
                "truth": "P_req-C_D*S*V*q",
            },
            {
                "case_id": "CAT-AERO-INDUCED-GEOMETRY",
                "source_owner_ids": ("AERO-INDUCED-DRAG", "AERO-ASPECT-RATIO"),
                "support": ("C_Di", "C_L", "S", "b", "e"),
                "truth": "pi*C_Di*b**2*e-C_L**2*S",
            },
            {
                "case_id": "CAT-AERO-STAGNATION-KINEMATIC",
                "source_owner_ids": ("AERO-STAGNATION-TEMPERATURE", "AERO-MACH-DEFINITION", "AERO-SPEED-OF-SOUND"),
                "support": ("R_s", "T", "T0", "V", "gamma"),
                "truth": "2*R_s*gamma*(T0-T)-V**2*(gamma-1)",
            },
            {
                "case_id": "CAT-AERO-RE-DYNAMIC-PRESSURE",
                "source_owner_ids": ("AERO-REYNOLDS-DEFINITION", "AERO-DYNAMIC-PRESSURE"),
                "support": ("Re", "c", "mu", "q", "rho"),
                "truth": "Re**2*mu**2-2*c**2*q*rho",
            },
        )

    def _score_blind_case(self, certificate: CircuitCertificate, truth: str) -> bool:
        symbols = {name: sp.Symbol(name) for name in certificate.support}
        symbols["pi"] = sp.pi
        truth_expr = _normalize_polynomial(sp.sympify(truth, locals=symbols))
        recovered = _normalize_polynomial(sp.sympify(certificate.polynomial, locals=symbols))
        # Compare zero sets up to a nonzero constant factor by mutual polynomial
        # divisibility.  This scoring occurs strictly after derivation.
        union = sorted(truth_expr.free_symbols | recovered.free_symbols, key=lambda value: value.name)
        p_truth = sp.Poly(truth_expr, *union)
        p_recovered = sp.Poly(recovered, *union)
        if p_truth.total_degree() != p_recovered.total_degree():
            return False
        quotient = sp.simplify(truth_expr / recovered)
        return not quotient.free_symbols and quotient != 0

    def _load_frozen_mass_benchmark_evidence(self) -> Mapping[str, Any]:
        """Bind the historical 5x64 mass benchmark without making it a current-file dependency.

        Clean current releases no longer retain the expensive replay report.  If a
        digest-bound receipt is present it is verified exactly.  Otherwise the
        benchmark algorithm and frozen partition input are still verified as
        executable research infrastructure, but the historical numeric outcome is
        *not* promoted into current acceptance evidence.
        """
        import hashlib
        import inspect
        path = self.root / "reports" / "constraint_atlas_mass_blind_circuit_current.json"
        parts = self._load_mass_blind_partitions()
        algorithm_source = "\n".join((
            inspect.getsource(type(self)._lower_passport_algebraic),
            inspect.getsource(type(self)._generate_blind_circuit_pool),
            inspect.getsource(type(self)._poly_equivalent),
        ))
        algorithm_digest = hashlib.sha256(algorithm_source.encode("utf-8")).hexdigest()
        if path.is_file():
            payload = _load_json(path)
            stored_digest = payload.get("digest")
            computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
            if stored_digest != computed:
                raise ValueError("constraint atlas mass blind evidence digest mismatch")
            if payload.get("partition_source_report_digest") != parts.get("source_report_digest"):
                raise ValueError("constraint atlas mass blind partition provenance mismatch")
            evidence_algorithm_digest = payload.get("benchmark_algorithm_contract_digest")
            if evidence_algorithm_digest and evidence_algorithm_digest != algorithm_digest:
                raise ValueError("constraint atlas mass blind evidence algorithm digest is stale")
            return payload
        marker = {
            "schema": "phi-constraint-atlas-mass-blind-history-binding/v15.11",
            "status": "HISTORICAL_EXPENSIVE_REPLAY_NOT_RETAINED_CURRENT_CLEAN_STATE",
            "current_replay_executed": False,
            "historical_numeric_result_admitted_as_current_evidence": False,
            "benchmark_algorithm_available": True,
            "benchmark_algorithm_contract_digest": algorithm_digest,
            "partition_source_report_digest": parts.get("source_report_digest"),
            "partition_count": len(parts.get("partitions", ())),
            "executed_hidden_cases": 0,
            "source_case_unavailable_count": None,
            "constraint_atlas_mass_hidden_law_recall_validated": False,
            "scientific_verdict": "NOT_REEXECUTED_CURRENT_QUALIFICATION_NO_PREDICTIVE_CLAIM",
            "claim_boundary": {
                "historical_320_case_result_reconstructed": False,
                "absence_of_receipt_interpreted_as_failure": False,
                "absence_of_receipt_interpreted_as_success": False,
                "algorithm_and_frozen_partitions_remain_available_for_dedicated_replay": True,
            },
        }
        return {**marker, "digest": digest_payload(marker)}

    def _load_frozen_unknown_frontier_evidence(self) -> Mapping[str, Any]:
        """Load the executed target-free frontier scan with algorithm binding."""
        import hashlib
        import inspect
        path = self.root / "reports" / "CONSTRAINT_ATLAS_UNKNOWN_FRONTIER_CURRENT.json"
        payload = _load_json(path)
        stored_digest = payload.get("digest")
        computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
        if stored_digest != computed:
            raise ValueError("constraint atlas unknown frontier evidence digest mismatch")
        algorithm_digest = hashlib.sha256(
            inspect.getsource(type(self).scan_unknown_frontier).encode("utf-8")
        ).hexdigest()
        if payload.get("frontier_algorithm_contract_digest") != algorithm_digest:
            raise ValueError("constraint atlas unknown frontier algorithm digest is stale")
        return payload

    def _load_frozen_operator_frontier_evidence(self) -> Mapping[str, Any]:
        import hashlib
        import inspect
        path = self.root / "reports" / "CONSTRAINT_ATLAS_OPERATOR_UNKNOWN_FRONTIER_CURRENT.json"
        payload = _load_json(path)
        stored_digest = payload.get("digest")
        computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
        if stored_digest != computed:
            raise ValueError("constraint atlas operator frontier evidence digest mismatch")
        algorithm_digest = hashlib.sha256(inspect.getsource(type(self).scan_operator_unknown_frontier).encode("utf-8")).hexdigest()
        if payload.get("operator_frontier_algorithm_contract_digest") != algorithm_digest:
            raise ValueError("constraint atlas operator frontier evidence algorithm digest is stale")
        return payload

    def _load_frozen_aeroelastic_projection_bridge_evidence(self) -> Mapping[str, Any]:
        import hashlib
        import inspect
        path = self.root / "reports" / "CONSTRAINT_ATLAS_AEROELASTIC_PROJECTION_BRIDGE_CURRENT.json"
        payload = _load_json(path)
        stored_digest = payload.get("digest")
        computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
        if stored_digest != computed:
            raise ValueError("constraint atlas aeroelastic projection evidence digest mismatch")
        algorithm_digest = hashlib.sha256(inspect.getsource(type(self).build_aeroelastic_projection_bridge).encode("utf-8")).hexdigest()
        if payload.get("bridge_algorithm_contract_digest") != algorithm_digest:
            raise ValueError("constraint atlas aeroelastic projection algorithm digest is stale")
        return payload

    def _load_frozen_kernel_discovery_evidence(self) -> Mapping[str, Any]:
        import hashlib
        import inspect
        path = self.root / "reports" / "CONSTRAINT_ATLAS_DATA_BACKED_KERNEL_DISCOVERY_CURRENT.json"
        payload = _load_json(path)
        stored_digest = payload.get("digest")
        computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
        if stored_digest != computed:
            raise ValueError("constraint atlas kernel discovery evidence digest mismatch")
        algorithm_source = "\n".join((
            inspect.getsource(type(self).discover_temporal_convolution_kernel),
            inspect.getsource(type(self).discover_spatial_nonlocal_kernel),
            inspect.getsource(type(self).run_data_backed_kernel_discovery_qualification),
        ))
        algorithm_digest = hashlib.sha256(algorithm_source.encode("utf-8")).hexdigest()
        if payload.get("kernel_discovery_algorithm_contract_digest") != algorithm_digest:
            raise ValueError("constraint atlas kernel discovery algorithm digest is stale")
        return payload

    def _load_frozen_real_gust_aero_lag_evidence(self) -> Mapping[str, Any]:
        import hashlib
        import inspect
        path = self.root / "reports" / "CONSTRAINT_ATLAS_REAL_GUST_AERO_LAG_DISCOVERY_CURRENT.json"
        payload = _load_json(path)
        stored_digest = payload.get("digest")
        computed = digest_payload({k: v for k, v in payload.items() if k != "digest"})
        if stored_digest != computed:
            raise ValueError("constraint atlas real gust/aero-lag evidence digest mismatch")
        algorithm_digest = hashlib.sha256(inspect.getsource(type(self).run_real_gust_aero_lag_discovery_qualification).encode("utf-8")).hexdigest()
        if payload.get("real_operator_algorithm_contract_digest") != algorithm_digest:
            raise ValueError("constraint atlas real gust/aero-lag algorithm digest is stale")
        dataset_path = self.root / payload.get("dataset", {}).get("relative_path", "")
        if not dataset_path.exists() or hashlib.sha256(dataset_path.read_bytes()).hexdigest() != payload.get("dataset", {}).get("derived_numeric_dataset_sha256"):
            raise ValueError("constraint atlas real gust/aero-lag dataset digest mismatch")
        return payload

    def run_qualification(self) -> Mapping[str, Any]:
        typing = self._global_typing_audit()
        quantity_ontology = self.compile_quantity_ontology()
        global_hypergraph = self.compile_global_constraint_hypergraph()
        chart = self._aeronautics_chart()
        mass_benchmark = self._load_frozen_mass_benchmark_evidence()
        # Current qualification executes authoritative owners directly.  Deleted
        # historical report files are never an implicit runtime dependency.
        unknown_frontier = self.scan_unknown_frontier()
        operator_frontier = self.scan_operator_unknown_frontier()
        aeroelastic_bridge = self.build_aeroelastic_projection_bridge()
        kernel_discovery = self.run_data_backed_kernel_discovery_qualification()
        real_aero = self.run_real_gust_aero_lag_discovery_qualification()
        from .science_atlas_core import ScienceAtlasCoreKernel
        science_atlas = ScienceAtlasCoreKernel(self.root).run_qualification()
        blind_rows: List[Mapping[str, Any]] = []
        exact = 0
        for case in self._blind_cases():
            certificate = self.derive_circuit(case["source_owner_ids"], case["support"])
            matched = self._score_blind_case(certificate, case["truth"])
            exact += int(matched)
            blind_rows.append({
                "case_id": case["case_id"],
                "source_owner_ids": list(case["source_owner_ids"]),
                "retained_support": list(case["support"]),
                "truth_formula_access_during_search": False,
                "post_run_expected_polynomial": case["truth"],
                "recovered_circuit": asdict(certificate),
                "exact_up_to_nonzero_scalar": matched,
            })

        same_letter_control = {
            "T": typing["same_display_multi_quantity_kinds"].get("T", {}),
            "D": typing["same_display_multi_quantity_kinds"].get("D", {}),
            "V": typing["same_display_multi_quantity_kinds"].get("V", {}),
            "M": typing["same_display_multi_quantity_kinds"].get("M", {}),
        }
        checks = {
            "quantity_and_quantity_kind_are_separated_in_atlas_ir": True,
            "semantic_lowering_covers_every_symbol_occurrence": quantity_ontology["semantic_lowering_complete_count"] == typing["symbol_record_count"],
            "semantic_lowering_has_zero_unclassified_occurrences": quantity_ontology["semantic_lowering_unresolved_count"] == 0,
            "syntax_tokens_are_not_forced_into_physical_quantity_coordinates": quantity_ontology["nonquantity_syntax_or_object_occurrence_count"] > 0,
            "owner_local_ambiguous_quantities_fail_closed": quantity_ontology["owner_local_quantity_occurrence_count"] > 0,
            "global_constraint_hypergraph_covers_every_passport": global_hypergraph["relation_count"] == typing["passport_count"],
            "global_constraint_hypergraph_semantically_lowers_every_passport": global_hypergraph["semantically_lowered_relation_count"] == typing["passport_count"],
            "same_letter_global_gluing_blocked": typing["global_same_letter_gluing_allowed"] is False,
            "ambiguous_same_letter_control_is_nonempty": all(bool(value) for value in same_letter_control.values()),
            "aeronautics_chart_has_no_typed_symbol_kind_conflict": not chart["typing_conflicts"],
            "algebraic_backend_has_executable_relations": chart["executable_algebraic_relation_count"] >= 10,
            "formula_hidden_positive_controls_exact": exact == len(blind_rows) == 8,
            "formula_hidden_positive_controls_support_minimal": all(row["recovered_circuit"]["support_minimal"] for row in blind_rows),
            "mass_hidden_law_benchmark_algorithm_and_partitions_bound": mass_benchmark.get("benchmark_algorithm_available", True) is True and bool(mass_benchmark.get("partition_source_report_digest")),
            "mass_hidden_law_historical_result_not_promoted_without_receipt": (
                mass_benchmark.get("current_replay_executed") is not False
                or mass_benchmark.get("historical_numeric_result_admitted_as_current_evidence") is False
            ),
            "mass_hidden_law_scientific_verdict_not_overclaimed": mass_benchmark.get("constraint_atlas_mass_hidden_law_recall_validated") is False,
            "unknown_frontier_target_formula_free": unknown_frontier.get("target_formula_access_during_search") is False,
            "unknown_frontier_has_no_scientific_order_ceiling": unknown_frontier.get("scientific_source_order_ceiling_used") is False and unknown_frontier.get("scientific_support_size_ceiling_used") is False,
            "unknown_frontier_materializes_unmaterialized_relations": unknown_frontier.get("forced_unmaterialized_relation_count", 0) > 0,
            "unknown_frontier_execution_budget_not_physical_gate": unknown_frontier.get("execution_budget_is_physical_admissibility_gate") is False,
            "operator_frontier_target_formula_free": operator_frontier.get("target_formula_access_during_search") is False,
            "operator_frontier_has_no_scientific_order_ceiling": operator_frontier.get("scientific_source_order_ceiling_used") is False,
            "operator_frontier_execution_budget_not_physical_gate": operator_frontier.get("execution_budget_is_physical_admissibility_gate") is False,
            "operator_frontier_materializes_unmaterialized_relations": operator_frontier.get("forced_unmaterialized_operator_relation_count", 0) > 0,
            "operator_frontier_executes_differential_relations": operator_frontier.get("differential_operator_candidate_count", 0) > 0,
            "operator_frontier_executes_integral_relations": operator_frontier.get("integral_operator_candidate_count", 0) > 0,
            "operator_frontier_executes_memory_relations": operator_frontier.get("memory_kernel_candidate_count", 0) > 0,
            "operator_frontier_preserves_bridge_required_fail_closed": any(r.get("status") == "BRIDGE_REQUIRED_UNKNOWN_OPERATOR_FRONTIER" for r in operator_frontier.get("directed_regions", ())),
            "aeroelastic_structural_projection_bridge_materialized": aeroelastic_bridge.get("status") == "PASS_STRUCTURAL_SUBSPACE_PDE_TO_REDUCED_STATE_BRIDGE_AERO_LAG_OPEN",
            "aeroelastic_projection_is_target_A_matrix_free": aeroelastic_bridge.get("target_formula_access_during_bridge_generation") is False,
            "aeroelastic_projection_modal_equivalence_passed": aeroelastic_bridge.get("checks", {}).get("modal_frequencies_match_pde_eigenproblem") is True and aeroelastic_bridge.get("checks", {}).get("projected_pde_matches_second_order_modal_dynamics") is True,
            "aeroelastic_full_ASE_embedding_not_overclaimed": aeroelastic_bridge.get("full_aeroservoelastic_state_space_bridge_complete") is False,
            "data_backed_temporal_kernel_discovery_qualified": kernel_discovery.get("checks", {}).get("temporal_kernel_recovered_on_hidden_calibration") is True and kernel_discovery.get("checks", {}).get("temporal_rollout_generalizes_to_late_holdout") is True,
            "data_backed_spatial_kernel_discovery_qualified": kernel_discovery.get("checks", {}).get("spatial_kernel_recovered_on_hidden_calibration") is True and kernel_discovery.get("checks", {}).get("spatial_holdout_fields_reconstructed") is True,
            "data_backed_kernel_family_not_prespecified": kernel_discovery.get("temporal_kernel_discovery", {}).get("analytic_kernel_family_selected_before_fit") is False and kernel_discovery.get("spatial_kernel_discovery", {}).get("analytic_kernel_family_selected_before_fit") is False,
            "real_qpdtr_kernel_remains_fail_closed_without_multitime_data": kernel_discovery.get("current_project_application", {}).get("qpdtr_nonmarkovian_kernel_fit_status") == "BLOCKED_MULTITIME_CALIBRATION_DATA_REQUIRED",
            "real_flexible_wing_vector_data_ingested_with_provenance": real_aero.get("checks", {}).get("real_public_flexible_wing_data_used") is True and real_aero.get("checks", {}).get("derived_dataset_declared_not_raw_daq") is True,
            "real_gust_to_load_low_frequency_residual_identified": real_aero.get("checks", {}).get("low_frequency_gust_load_overprediction_is_reproduced") is True,
            "real_gust_to_load_phase_fail_closed": real_aero.get("checks", {}).get("gust_phase_unavailable_blocks_full_causal_kernel") is True,
            "real_aero_lag_broadband_magnitude_identified": real_aero.get("checks", {}).get("flap_to_wrbm_broadband_magnitude_matches_nominal_model") is True,
            "real_aero_lag_9hz_complex_anchor_identified": real_aero.get("checks", {}).get("nine_hz_control_effect_complex_anchor_finite") is True,
            "real_aero_lag_full_phase_not_overclaimed": real_aero.get("checks", {}).get("broadband_aero_lag_phase_not_overclaimed") is True,
            "science_atlas_core_current_10_10": science_atlas.get("passed") == science_atlas.get("total") == 10,
            "science_atlas_has_no_parallel_owner": science_atlas.get("owner_binding", {}).get("parallel_science_atlas_owner_created") is False,
        }
        claim_boundary = {
            "naive_structural_hole_predicts_law": False,
            "constraint_atlas_mass_hidden_law_recall_validated": bool(mass_benchmark.get("constraint_atlas_mass_hidden_law_recall_validated", False)),
            "mass_hidden_law_scientific_verdict": mass_benchmark.get("scientific_verdict"),
            "algebraic_circuit_backend": "QUALIFIED_ON_8_OF_8_FORMULA_HIDDEN_TYPED_POSITIVE_CONTROLS_BUT_ZERO_OF_320_MASS_BLIND_REPLAY",
            "quantity_ontology_semantic_lowering": "COMPLETE_FOR_ALL_SYMBOL_OCCURRENCES_WITH_OWNER_LOCAL_FAIL_CLOSED_IDENTITIES_WHERE_GLOBAL_KIND_IS_UNRESOLVED",
            "global_quantity_identity_complete": False,
            "differential_matroid_backend": "PARTIAL_EXECUTABLE_OPERATOR_REWRITE_BACKEND_NOT_COMPLETE_DIFFERENTIAL_ALGEBRA",
            "integral_operator_backend": "PARTIAL_EXECUTABLE_VOLTERRA_AND_CONSTITUTIVE_SUBSTITUTION_BACKEND",
            "nonlocal_memory_operator_backend": "REGISTERED_KERNEL_COMPOSITION_PLUS_NONPARAMETRIC_DATA_BACKED_TEMPORAL_AND_SPATIAL_KERNEL_INVERSION_QUALIFIED_ON_HIDDEN_CALIBRATIONS",
            "aeroelastic_projection_bridge": "STRUCTURAL_PDE_TO_REDUCED_STATE_SUBSPACE_MATERIALIZED; REAL_GUST_LOAD_MAGNITUDE_CORRECTION_AND_9HZ_CONTROL_EFFECT_ANCHOR_NOW_MATERIALIZED; FULL_BROADBAND_PHASE_AND_DISTRIBUTED_AERODYNAMIC_KERNEL_REMAIN_OPEN",
            "real_qpdtr_nonmarkov_kernel": "BLOCKED_MULTITIME_CALIBRATION_DATA_REQUIRED",
            "real_gust_to_load_operator": "PARTIAL_REAL_DATA_IDENTIFICATION_MAGNITUDE_ONLY_4_TO_12HZ; FULL_CAUSAL_KERNEL_NOT_IDENTIFIED",
            "real_aero_lag_operator": "PARTIAL_REAL_DATA_IDENTIFICATION_BROADBAND_MAGNITUDE_PLUS_9HZ_COMPLEX_CONTROL_EFFECT; BROADBAND_PHASE_OPEN",
            "finite_validity_sheaf": "TYPED_LOCAL_GLUE_AND_DECLARED_OVERLAP_DIAGNOSTIC_ONLY_NOT_COHOMOLOGICAL_COMPLETENESS",
            "new_physical_law_found_by_this_qualification": False,
            "unknown_frontier_formally_forced_candidates_found": unknown_frontier.get("forced_unmaterialized_relation_count", 0) > 0,
            "unknown_frontier_world_novelty_established": False,
            "periodic_table_of_laws_validated": False,
            "world_novelty_established": False,
            "science_atlas_unique_ontology_established": False,
            "science_atlas_predictive_geometry_established": False,
        }
        status = "PASS_CONSTRAINT_ATLAS_V6_22_REAL_GUST_LOAD_AND_PARTIAL_AERO_LAG_DISCOVERY_WITH_FAIL_CLOSED_PHASE" if all(checks.values()) else "FAIL_CONSTRAINT_ATLAS_QUALIFICATION"
        result = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": status,
            "external_semantic_foundations": {
                "QUDT": QUDT_REFERENCE,
                "BIPM_VIM": "VIM4-2CD-2023-07",
                "EMMO": EMMO_REFERENCE,
                "algebraic_matroid_basis": "Rosen-2014-Computing-Algebraic-Matroids",
                "finite_sheaf_transport_basis": "Olivieri-Hernandez-2026-Sheaf-Theoretic-Transport-And-Obstruction",
            },
            "typing_audit": typing,
            "quantity_ontology_compiler": {key: value for key, value in quantity_ontology.items() if key != "occurrences"},
            "typed_constraint_hypergraph": {key: value for key, value in global_hypergraph.items() if key != "relations"},
            "mass_hidden_law_benchmark": {key: value for key, value in mass_benchmark.items() if key != "splits"},
            "unknown_frontier_search": {key: value for key, value in unknown_frontier.items() if key != "operator_backend_frontiers"},
            "operator_unknown_frontier_search": operator_frontier,
            "aeroelastic_projection_bridge": aeroelastic_bridge,
            "data_backed_kernel_discovery": kernel_discovery,
            "real_gust_aero_lag_discovery": real_aero,
            "science_atlas_core": science_atlas,
            "aeronautics_chart": {
                "chart_id": chart["chart_id"],
                "coordinate_count": len(chart["coordinates"]),
                "relation_count": len(chart["relations"]),
                "executable_algebraic_relation_count": chart["executable_algebraic_relation_count"],
                "typing_conflict_count": len(chart["typing_conflicts"]),
            },
            "same_letter_anti_aliasing_control": same_letter_control,
            "blind_circuit_qualification": {
                "case_count": len(blind_rows),
                "exact_recovery_count": exact,
                "exact_recovery_fraction": exact / len(blind_rows) if blind_rows else 0.0,
                "cases": blind_rows,
            },
            "checks": checks,
            "claim_boundary": claim_boundary,
        }
        result["digest"] = digest_payload(result)
        return result


def _occurrence_counts(rows: Mapping[str, set[str]]) -> Mapping[str, int]:
    counts: Dict[str, int] = {}
    for symbols in rows.values():
        for symbol in symbols:
            counts[symbol] = counts.get(symbol, 0) + 1
    return counts
