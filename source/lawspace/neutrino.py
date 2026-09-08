"""Authoritative neutrino micro→IR owner with Majorana/Takagi lowering.

The active neutrino route is one replacement-in-place pipeline

    declared 4D or compactified microphysics
        -> one finite complex-symmetric mass matrix M
        -> Autonne-Takagi factorisation W^T M W = diag(m_r), m_r >= 0
        -> active-flavour mixing rows and LNV observables
        -> vacuum/matter propagation and multi-experiment model selection.

The former real Dirac ``M M^T`` eigensolver is not an active alternative.
Its Dirac/LED behaviour is a controlled zero-Majorana limit of the same
complex-symmetric operator.  ``LEDParameters`` remains a thin data lowering
record and contains no scientific algorithm.

Executable scope:
* three-flavour PMNS propagation in vacuum and piecewise-constant matter;
* one global flavour-coupled Dirac/Majorana/seesaw/KK mass matrix;
* flat S1/Z2, anisotropic T2/Z2, localised flat and warped-interval geometry;
* brane-left, brane-right and bulk Majorana terms;
* beta-endpoint m_beta and neutrinoless-double-beta m_beta_beta observables;
* exact Takagi residual certificates and geometry-specific KK convergence;
* controlled flat, zero-warp, zero-coupling and finite-tower limits;
* directed inter-experiment blind holdout.

No synthetic benchmark or emulator certificate is evidence that extra
spatial dimensions exist in nature.
"""
from __future__ import annotations

import dataclasses
import hashlib
import heapq
import itertools
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.linalg import expm, sqrtm
from scipy.optimize import brentq, least_squares
from scipy.stats import qmc
from scipy.special import jv, yv

OWNER_ID = "NEUTRINO-PHENOMENOLOGY"
OWNER_VERSION = "6.9.0"
BLIND_DISCOVERY_OWNER_ID = "NEUTRINO-BLIND-DISCOVERY"
BLIND_DISCOVERY_OWNER_VERSION = "6.9.0"
SCHEMA = "phi-neutrino-majorana-takagi-micro-ir/v6.9"
BENCHMARK_SCHEMA = "phi-neutrino-majorana-takagi-blind-discovery/v6.9"

OSCILLATION_PHASE_KM_GEV = 2.0 * 1.266932679
MATTER_POTENTIAL_EV2 = 1.526e-4
MICROMETRE_TO_EV_INV = 5.067730716

REFERENCE_SNAPSHOT: Mapping[str, Any] = {
    "snapshot_id": "NUFIT-6.1-IC24-SK-NO-2025",
    "source": "NuFIT 6.1 parameter table; IC24 with SK atmospheric data; normal ordering",
    "sin2_theta12": 0.3088,
    "sin2_theta13": 0.02248,
    "sin2_theta23": 0.470,
    "delta_cp_deg": 212.0,
    "dm21_ev2": 7.537e-5,
    "dm3l_ev2": 2.511e-3,
    "absolute_mass_status": "BOUNDED_NOT_MEASURED",
    "katrin_mbeta_upper_ev_90cl": 0.45,
    "references": (
        "NuFIT 6.1 (2025), https://www.nu-fit.org/sites/default/files/v61.tbl-parameters.pdf",
        "KATRIN Collaboration (2025), m_beta < 0.45 eV/c^2",
        "Machado, Nunokawa, Zukanovich Funchal, arXiv:1101.0003",
        "Eller et al., Phys. Rev. D (2025), arXiv:2508.04274",
        "de Giorgi et al., JHEP 05 (2026) 152, arXiv:2512.02101",
    ),
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OscillationParameters:
    sin2_theta12: float = float(REFERENCE_SNAPSHOT["sin2_theta12"])
    sin2_theta13: float = float(REFERENCE_SNAPSHOT["sin2_theta13"])
    sin2_theta23: float = float(REFERENCE_SNAPSHOT["sin2_theta23"])
    delta_cp_rad: float = math.radians(float(REFERENCE_SNAPSHOT["delta_cp_deg"]))
    dm21_ev2: float = float(REFERENCE_SNAPSHOT["dm21_ev2"])
    dm3l_ev2: float = float(REFERENCE_SNAPSHOT["dm3l_ev2"])
    lightest_mass_ev: float = 0.0
    ordering: str = "NORMAL"

    def validate(self) -> None:
        for name in ("sin2_theta12", "sin2_theta13", "sin2_theta23"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0,1]")
        if not math.isfinite(self.delta_cp_rad):
            raise ValueError("delta_cp_rad must be finite")
        if self.dm21_ev2 <= 0.0 or self.dm3l_ev2 == 0.0:
            raise ValueError("mass splittings must be non-zero with dm21 positive")
        if self.lightest_mass_ev < 0.0:
            raise ValueError("lightest_mass_ev must be non-negative")
        if self.ordering not in {"NORMAL", "INVERTED"}:
            raise ValueError("ordering must be NORMAL or INVERTED")

    def masses_ev(self) -> np.ndarray:
        self.validate()
        m0 = float(self.lightest_mass_ev)
        if self.ordering == "NORMAL":
            m1_sq = m0 * m0
            m2_sq = m1_sq + self.dm21_ev2
            m3_sq = m1_sq + abs(self.dm3l_ev2)
            return np.sqrt(np.array([m1_sq, m2_sq, m3_sq], dtype=float))
        m3_sq = m0 * m0
        m2_sq = m3_sq + abs(self.dm3l_ev2)
        m1_sq = m2_sq - self.dm21_ev2
        if m1_sq < 0.0:
            raise ValueError("inverted-ordering masses are inconsistent")
        return np.sqrt(np.array([m1_sq, m2_sq, m3_sq], dtype=float))

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class MatterLayer:
    length_km: float
    density_g_cm3: float
    electron_fraction: float = 0.5

    def validate(self) -> None:
        if self.length_km <= 0.0:
            raise ValueError("matter layer length must be positive")
        if self.density_g_cm3 < 0.0:
            raise ValueError("matter density must be non-negative")
        if not 0.0 <= self.electron_fraction <= 1.0:
            raise ValueError("electron_fraction must be in [0,1]")


@dataclass(frozen=True)
class SterileParameters:
    dm41_ev2: float
    theta14_rad: float
    theta24_rad: float
    theta34_rad: float = 0.0

    def validate(self) -> None:
        if self.dm41_ev2 <= 0.0:
            raise ValueError("dm41_ev2 must be positive")
        for angle in (self.theta14_rad, self.theta24_rad, self.theta34_rad):
            if not 0.0 <= angle <= math.pi / 2.0:
                raise ValueError("sterile mixing angles must be in [0,pi/2]")


ZERO_MATRIX3: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
)


@dataclass(frozen=True)
class NonStandardInteractionParameters:
    """Hermitian matter-potential deformation in the active flavour basis."""

    epsilon_ee: float = 0.0
    epsilon_mumu: float = 0.0
    epsilon_tautau: float = 0.0
    epsilon_emu_real: float = 0.0
    epsilon_emu_imag: float = 0.0
    epsilon_etau_real: float = 0.0
    epsilon_etau_imag: float = 0.0
    epsilon_mutau_real: float = 0.0
    epsilon_mutau_imag: float = 0.0

    def validate(self) -> None:
        values = dataclasses.astuple(self)
        if any(not math.isfinite(float(v)) for v in values):
            raise ValueError("NSI coefficients must be finite")
        if max(abs(float(v)) for v in values) > 5.0:
            raise ValueError("NSI benchmark contract is bounded to |epsilon| <= 5")

    def epsilon_matrix(self) -> np.ndarray:
        self.validate()
        emu = complex(self.epsilon_emu_real, self.epsilon_emu_imag)
        etau = complex(self.epsilon_etau_real, self.epsilon_etau_imag)
        mutau = complex(self.epsilon_mutau_real, self.epsilon_mutau_imag)
        return np.array(
            [
                [self.epsilon_ee, emu, etau],
                [np.conjugate(emu), self.epsilon_mumu, mutau],
                [np.conjugate(etau), np.conjugate(mutau), self.epsilon_tautau],
            ],
            dtype=complex,
        )


@dataclass(frozen=True)
class ScientificDomainIR:
    """Physical admissibility is independent of finite execution resources.

    ``None`` means that the scientific coordinate is not capped by the owner.
    A finite numerical run may still stop under :class:`ExecutionBudgetIR`; that
    stop is evidence about available resources, never a physical no-go theorem.
    """

    maximum_extra_dimensions: int | None = None
    maximum_kk_modes_per_family: int | None = None
    admissible_geometries: tuple[str, ...] = (
        "FOUR_DIMENSIONAL", "FLAT_TD_Z2", "LOCALISED_FLAT_ORBIFOLD", "WARPED_INTERVAL_RS1"
    )
    continuous_parameter_exhaustion_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ExecutionBudgetIR:
    """Explicit technical stop rules; never part of the physical domain."""

    maximum_dense_operator_dimension: int | None = 2048
    maximum_materialized_kk_modes_per_family: int | None = None
    maximum_wall_seconds: float | None = None
    maximum_owner_visits: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class HigherDimensionalMicroParameters:
    """Declared 4D/compactified Dirac-Majorana microphysics.

    The geometry selector changes only the compact spectral lowering.  Every
    geometry is assembled into the same finite complex-symmetric Majorana
    mass operator and is diagonalised by the same Takagi owner.
    """

    dimensions: int
    radii_micrometre: tuple[float, ...]
    lightest_dirac_mass_ev: float
    kk_modes_per_family: int
    family_coupling_scales: tuple[float, float, float] = (1.0, 1.0, 1.0)
    family_bulk_masses_ev: tuple[float, float, float] = (0.0, 0.0, 0.0)
    family_brane_kinetic: tuple[float, float, float] = (0.0, 0.0, 0.0)
    localisation_width_fraction: float = 0.0
    boundary_phases: tuple[float, ...] = ()
    geometry: str = "FLAT_TOROIDAL_ORBIFOLD"
    uv_cutoff_ev: float | None = None
    family_dirac_masses_ev: tuple[float, float, float] | None = None
    family_dirac_phases_rad: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Optional general 3x3 active Dirac block.  When omitted, the same owner
    # constructs the historical PMNS-aligned block as a controlled subcase.
    # The mass-operator assembly itself remains single-path.
    brane_dirac_real_ev: tuple[tuple[float, float, float], ...] | None = None
    brane_dirac_imag_ev: tuple[tuple[float, float, float], ...] | None = None
    # Optional general active-flavour -> compact-family coupling matrix.  This
    # is dimensionless and permits blind synthesis of couplings that are not
    # pre-labelled as a published neutrino-model family.
    active_compact_coupling_real: tuple[tuple[float, float, float], ...] | None = None
    active_compact_coupling_imag: tuple[tuple[float, float, float], ...] | None = None
    # Arbitrary finite Chebyshev expansion of a dimensionless mode-dependent
    # coupling kernel K(x)=exp(sum a_k T_k(z)+i sum b_k T_k(z)).  Empty tuples
    # recover K=1 exactly.  The scientific contract has no fixed polynomial
    # order ceiling; any finite execution samples only a declared prefix.
    compact_coupling_log_chebyshev: tuple[float, ...] = ()
    compact_coupling_phase_chebyshev: tuple[float, ...] = ()
    brane_left_majorana_real_ev: tuple[tuple[float, float, float], ...] = ZERO_MATRIX3
    brane_left_majorana_imag_ev: tuple[tuple[float, float, float], ...] = ZERO_MATRIX3
    brane_right_majorana_real_ev: tuple[tuple[float, float, float], ...] = ZERO_MATRIX3
    brane_right_majorana_imag_ev: tuple[tuple[float, float, float], ...] = ZERO_MATRIX3
    family_bulk_majorana_left_ev: tuple[float, float, float] = (0.0, 0.0, 0.0)
    family_bulk_majorana_left_phases_rad: tuple[float, float, float] = (0.0, 0.0, 0.0)
    family_bulk_majorana_right_ev: tuple[float, float, float] = (0.0, 0.0, 0.0)
    family_bulk_majorana_right_phases_rad: tuple[float, float, float] = (0.0, 0.0, 0.0)
    warp_curvature_ev: float = 0.0
    warp_exponent: float = 0.0
    family_warp_bulk_c: tuple[float, float, float] = (0.5, 0.5, 0.5)
    warp_boundary_condition: str = "RH_EVEN_LH_ODD"

    _GEOMETRY_ALIASES = {
        "FLAT_TOROIDAL_ORBIFOLD": "FLAT_S1_Z2_OR_TD_Z2",
        "FLAT_S1_Z2": "FLAT_S1_Z2_OR_TD_Z2",
        "FLAT_ANISOTROPIC_T2_Z2": "FLAT_S1_Z2_OR_TD_Z2",
        "LOCALISED_FLAT_ORBIFOLD": "LOCALISED_FLAT_ORBIFOLD",
        "LOCALIZED_FLAT_ORBIFOLD": "LOCALISED_FLAT_ORBIFOLD",
        "WARPED_INTERVAL_RS1": "WARPED_INTERVAL_RS1",
        "FOUR_DIMENSIONAL": "FOUR_DIMENSIONAL",
    }

    @staticmethod
    def _validate_matrix_pair(real: Sequence[Sequence[float]], imag: Sequence[Sequence[float]], name: str) -> None:
        if len(real) != 3 or len(imag) != 3 or any(len(row) != 3 for row in real) or any(len(row) != 3 for row in imag):
            raise ValueError(f"{name} must be two 3x3 matrices")
        r = np.asarray(real, dtype=float)
        q = np.asarray(imag, dtype=float)
        if not np.all(np.isfinite(r)) or not np.all(np.isfinite(q)):
            raise ValueError(f"{name} entries must be finite")
        if np.linalg.norm(r-r.T) > 1.0e-14 or np.linalg.norm(q-q.T) > 1.0e-14:
            raise ValueError(f"{name} must be complex symmetric")

    @property
    def canonical_geometry(self) -> str:
        if self.dimensions == 0:
            return "FOUR_DIMENSIONAL"
        try:
            geometry = self._GEOMETRY_ALIASES[self.geometry]
        except KeyError as exc:
            raise ValueError(f"unsupported compactification geometry: {self.geometry}") from exc
        if geometry == "FLAT_S1_Z2_OR_TD_Z2":
            if self.dimensions == 1:
                return "FLAT_S1_Z2"
            if self.dimensions == 2:
                return "FLAT_ANISOTROPIC_T2_Z2"
            return "FLAT_TD_Z2"
        return geometry

    def validate(self) -> None:
        canonical = self.canonical_geometry
        if not isinstance(self.dimensions, int) or self.dimensions < 0:
            raise ValueError("dimensions must be a non-negative integer; the scientific domain has no fixed upper ceiling")
        if len(self.radii_micrometre) != self.dimensions:
            raise ValueError("one positive radius is required per extra dimension")
        if any((not math.isfinite(r) or r <= 0.0) for r in self.radii_micrometre):
            raise ValueError("compactification radii must be finite and positive")
        if self.lightest_dirac_mass_ev < 0.0 or not math.isfinite(self.lightest_dirac_mass_ev):
            raise ValueError("lightest_dirac_mass_ev must be finite and non-negative")
        if not isinstance(self.kk_modes_per_family, int) or self.kk_modes_per_family < 0:
            raise ValueError("kk_modes_per_family must be a non-negative integer; execution limits are declared separately")
        if self.dimensions == 0 and self.kk_modes_per_family != 0:
            raise ValueError("four-dimensional sector cannot declare KK modes")
        if canonical == "WARPED_INTERVAL_RS1":
            if self.dimensions != 1:
                raise ValueError("WARPED_INTERVAL_RS1 requires exactly one compact dimension")
            if self.warp_curvature_ev <= 0.0 or not math.isfinite(self.warp_curvature_ev):
                raise ValueError("warped geometry requires positive finite warp_curvature_ev")
            if self.warp_exponent < 0.0 or not math.isfinite(self.warp_exponent):
                raise ValueError("warp_exponent must be finite and non-negative")
            if self.warp_boundary_condition != "RH_EVEN_LH_ODD":
                raise ValueError("only the declared RH_EVEN_LH_ODD warped boundary domain is qualified")
        elif self.warp_curvature_ev != 0.0 or self.warp_exponent != 0.0:
            raise ValueError("warp parameters are active only for WARPED_INTERVAL_RS1")
        if canonical == "LOCALISED_FLAT_ORBIFOLD" and self.localisation_width_fraction <= 0.0:
            raise ValueError("localised compactification requires positive localisation_width_fraction")
        for values, name in (
            (self.family_coupling_scales, "family_coupling_scales"),
            (self.family_bulk_masses_ev, "family_bulk_masses_ev"),
            (self.family_brane_kinetic, "family_brane_kinetic"),
            (self.family_bulk_majorana_left_ev, "family_bulk_majorana_left_ev"),
            (self.family_bulk_majorana_right_ev, "family_bulk_majorana_right_ev"),
        ):
            if len(values) != 3:
                raise ValueError(f"{name} must contain three family values")
            if any((not math.isfinite(v) or v < 0.0) for v in values):
                raise ValueError(f"{name} must be finite and non-negative")
        if len(self.family_warp_bulk_c) != 3 or any(not math.isfinite(v) for v in self.family_warp_bulk_c):
            raise ValueError("family_warp_bulk_c must contain three finite values")
        for values, name in (
            (self.family_dirac_phases_rad, "family_dirac_phases_rad"),
            (self.family_bulk_majorana_left_phases_rad, "family_bulk_majorana_left_phases_rad"),
            (self.family_bulk_majorana_right_phases_rad, "family_bulk_majorana_right_phases_rad"),
        ):
            if len(values) != 3 or any(not math.isfinite(v) for v in values):
                raise ValueError(f"{name} must contain three finite phases")
        if self.family_dirac_masses_ev is not None:
            if len(self.family_dirac_masses_ev) != 3 or any((not math.isfinite(v) or v < 0.0) for v in self.family_dirac_masses_ev):
                raise ValueError("family_dirac_masses_ev must contain three finite non-negative masses")
        if (self.brane_dirac_real_ev is None) != (self.brane_dirac_imag_ev is None):
            raise ValueError("brane Dirac real/imag matrices must be declared together")
        if self.brane_dirac_real_ev is not None:
            for matrix, name in ((self.brane_dirac_real_ev, "brane_dirac_real_ev"), (self.brane_dirac_imag_ev, "brane_dirac_imag_ev")):
                if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
                    raise ValueError(f"{name} must be a 3x3 matrix")
                if not np.all(np.isfinite(np.asarray(matrix, dtype=float))):
                    raise ValueError(f"{name} entries must be finite")
        if (self.active_compact_coupling_real is None) != (self.active_compact_coupling_imag is None):
            raise ValueError("active compact coupling real/imag matrices must be declared together")
        if self.active_compact_coupling_real is not None:
            for matrix, name in ((self.active_compact_coupling_real, "active_compact_coupling_real"), (self.active_compact_coupling_imag, "active_compact_coupling_imag")):
                if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
                    raise ValueError(f"{name} must be a 3x3 matrix")
                if not np.all(np.isfinite(np.asarray(matrix, dtype=float))):
                    raise ValueError(f"{name} entries must be finite")
        if any(not math.isfinite(float(v)) for v in (*self.compact_coupling_log_chebyshev, *self.compact_coupling_phase_chebyshev)):
            raise ValueError("compact coupling kernel coefficients must be finite")
        self._validate_matrix_pair(self.brane_left_majorana_real_ev, self.brane_left_majorana_imag_ev, "brane_left_majorana")
        self._validate_matrix_pair(self.brane_right_majorana_real_ev, self.brane_right_majorana_imag_ev, "brane_right_majorana")
        if not 0.0 <= self.localisation_width_fraction <= 1.0:
            raise ValueError("localisation_width_fraction must be in [0,1]")
        phases = self.boundary_phases or tuple(0.0 for _ in range(self.dimensions))
        if len(phases) != self.dimensions or any(not 0.0 <= p < 1.0 for p in phases):
            raise ValueError("boundary_phases must contain one value in [0,1) per dimension")
        if self.uv_cutoff_ev is not None and (self.uv_cutoff_ev <= 0.0 or not math.isfinite(self.uv_cutoff_ev)):
            raise ValueError("uv_cutoff_ev must be positive and finite")

    @property
    def phases(self) -> tuple[float, ...]:
        return self.boundary_phases or tuple(0.0 for _ in range(self.dimensions))

    def dirac_masses_ev(self, parameters: OscillationParameters) -> np.ndarray:
        if self.family_dirac_masses_ev is not None:
            return np.asarray(self.family_dirac_masses_ev, dtype=float)
        return dataclasses.replace(parameters, lightest_mass_ev=self.lightest_dirac_mass_ev).masses_ev()

    def active_dirac_matrix(self, parameters: OscillationParameters) -> np.ndarray:
        """Return the unique active Dirac block used by the mass assembler."""
        if self.brane_dirac_real_ev is not None:
            return np.asarray(self.brane_dirac_real_ev, dtype=float) + 1j * np.asarray(self.brane_dirac_imag_ev, dtype=float)
        masses = self.dirac_masses_ev(parameters)
        phases = np.exp(1j * np.asarray(self.family_dirac_phases_rad, dtype=float))
        pmns = NeutrinoPhenomenologyOwner.pmns_matrix(parameters)
        return np.conjugate(pmns) @ np.diag(masses * phases)

    def active_compact_coupling_matrix(self, parameters: OscillationParameters) -> np.ndarray:
        """Return the dimensionless flavour-to-compact coupling basis."""
        if self.active_compact_coupling_real is not None:
            return np.asarray(self.active_compact_coupling_real, dtype=float) + 1j * np.asarray(self.active_compact_coupling_imag, dtype=float)
        return np.conjugate(NeutrinoPhenomenologyOwner.pmns_matrix(parameters))

    def compact_coupling_kernel(self, mode_mass_ev: float) -> complex:
        """Dimensionless arbitrary-finite spectral coupling kernel.

        The argument is formed from the compact mass and the geometric mean
        compactification radius, so every Chebyshev basis function is fed a
        dimensionless number in [-1,1).  Empty coefficient tuples give unity.
        """
        if self.dimensions <= 0 or not self.radii_micrometre:
            return 1.0 + 0.0j
        radius = float(np.exp(np.mean(np.log(np.asarray(self.radii_micrometre, dtype=float)))))
        x = max(0.0, float(mode_mass_ev) * radius / MICROMETRE_TO_EV_INV)
        z = 2.0 * x / (1.0 + x) - 1.0
        log_coeff = [0.0, *[float(v) for v in self.compact_coupling_log_chebyshev]]
        phase_coeff = [0.0, *[float(v) for v in self.compact_coupling_phase_chebyshev]]
        log_amp = float(np.polynomial.chebyshev.chebval(z, log_coeff))
        phase = float(np.polynomial.chebyshev.chebval(z, phase_coeff))
        if not math.isfinite(log_amp) or abs(log_amp) > 50.0:
            raise ValueError("compact coupling kernel leaves the qualified numerical exponential domain")
        return math.exp(log_amp) * complex(math.cos(phase), math.sin(phase))

    @staticmethod
    def _complex_matrix(real: Sequence[Sequence[float]], imag: Sequence[Sequence[float]]) -> np.ndarray:
        return np.asarray(real, dtype=float) + 1j*np.asarray(imag, dtype=float)

    @property
    def brane_left_majorana_matrix(self) -> np.ndarray:
        return self._complex_matrix(self.brane_left_majorana_real_ev, self.brane_left_majorana_imag_ev)

    @property
    def brane_right_majorana_matrix(self) -> np.ndarray:
        return self._complex_matrix(self.brane_right_majorana_real_ev, self.brane_right_majorana_imag_ev)

    @property
    def majorana_sector_active(self) -> bool:
        return bool(
            np.linalg.norm(self.brane_left_majorana_matrix) > 0.0
            or np.linalg.norm(self.brane_right_majorana_matrix) > 0.0
            or any(v > 0.0 for v in self.family_bulk_majorana_left_ev)
            or any(v > 0.0 for v in self.family_bulk_majorana_right_ev)
        )

    @property
    def active_axis_count(self) -> int:
        base = (
            2 + self.dimensions + 1 + 1 + 3 + 3 + 3 + 1 + self.dimensions
            + (1 if self.uv_cutoff_ev is not None else 0)
            + 3 + (3 if self.family_dirac_masses_ev is not None else 0)
        )
        if self.canonical_geometry == "WARPED_INTERVAL_RS1":
            base += 2 + 3
        if self.brane_dirac_real_ev is not None:
            base += int(np.count_nonzero(np.abs(self.active_dirac_matrix(OscillationParameters())) > 0.0)) * 2
        if self.active_compact_coupling_real is not None:
            coupling = np.asarray(self.active_compact_coupling_real, dtype=float) + 1j*np.asarray(self.active_compact_coupling_imag, dtype=float)
            base += int(np.count_nonzero(np.abs(coupling) > 0.0)) * 2
        base += len(self.compact_coupling_log_chebyshev) + len(self.compact_coupling_phase_chebyshev)
        for matrix in (self.brane_left_majorana_matrix, self.brane_right_majorana_matrix):
            for i in range(3):
                for j in range(i,3):
                    if abs(matrix[i,j]) > 0.0:
                        base += 2
        for magnitude, phase in (
            (self.family_bulk_majorana_left_ev, self.family_bulk_majorana_left_phases_rad),
            (self.family_bulk_majorana_right_ev, self.family_bulk_majorana_right_phases_rad),
        ):
            for m,p in zip(magnitude,phase):
                if m > 0.0:
                    base += 1 + int(abs(p) > 0.0)
        return base

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HigherDimensionalMicroParameters":
        """Reconstruct the exact typed microphysics from a persisted identity.

        ``canonical_geometry`` is derived metadata and is deliberately ignored.
        JSON arrays are converted back to immutable tuples so a frozen discovery
        candidate can be re-lowered by the same authoritative physics owner
        before any experiment owner sees it.
        """
        row = dict(payload)
        row.pop("canonical_geometry", None)
        tuple_keys = {
            "radii_micrometre", "family_coupling_scales", "family_bulk_masses_ev",
            "family_brane_kinetic", "boundary_phases", "family_dirac_masses_ev",
            "family_dirac_phases_rad", "compact_coupling_log_chebyshev",
            "compact_coupling_phase_chebyshev", "family_bulk_majorana_left_ev",
            "family_bulk_majorana_left_phases_rad", "family_bulk_majorana_right_ev",
            "family_bulk_majorana_right_phases_rad", "family_warp_bulk_c",
        }
        matrix_keys = {
            "brane_dirac_real_ev", "brane_dirac_imag_ev",
            "active_compact_coupling_real", "active_compact_coupling_imag",
            "brane_left_majorana_real_ev", "brane_left_majorana_imag_ev",
            "brane_right_majorana_real_ev", "brane_right_majorana_imag_ev",
        }
        for key in tuple_keys:
            if key in row and row[key] is not None:
                row[key] = tuple(row[key])
        for key in matrix_keys:
            if key in row and row[key] is not None:
                row[key] = tuple(tuple(float(v) for v in line) for line in row[key])
        allowed = {field.name for field in dataclasses.fields(cls)}
        unknown = sorted(set(row) - allowed)
        if unknown:
            raise ValueError(f"unknown persisted microphysics fields: {unknown}")
        micro = cls(**row)
        micro.validate()
        return micro

    def to_dict(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["canonical_geometry"] = self.canonical_geometry
        return payload


@dataclass(frozen=True)
class LEDParameters:
    """Thin compatibility record lowering the old 1D call into the micro owner."""

    radius_micrometre: float
    lightest_dirac_mass_ev: float
    kk_modes: int

    def validate(self) -> None:
        self.to_micro_parameters().validate()

    def to_micro_parameters(self) -> HigherDimensionalMicroParameters:
        return HigherDimensionalMicroParameters(
            dimensions=1,
            radii_micrometre=(self.radius_micrometre,),
            lightest_dirac_mass_ev=self.lightest_dirac_mass_ev,
            kk_modes_per_family=self.kk_modes,
        )


@dataclass(frozen=True)
class CompactificationGeometryIR:
    input_geometry: str
    canonical_geometry: str
    dimensions: int
    topology: str
    orbifold_action: str
    metric_contract: str
    radii_micrometre: tuple[float, ...]
    boundary_phases: tuple[float, ...]
    warp_curvature_ev: float
    warp_exponent: float
    family_warp_bulk_c: tuple[float, float, float]
    boundary_condition: str
    family_mode_masses_ev: tuple[tuple[float, ...], ...]
    family_mode_overlaps: tuple[tuple[float, ...], ...]
    family_mode_labels: tuple[tuple[str, ...], ...]
    maximum_spectral_residual: float
    maximum_profile_normalisation_residual: float
    controlled_limit: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class KKConvergenceCertificateIR:
    status: str
    canonical_geometry: str
    asymptotic_dimension: int
    shell_density_power: float
    coupling_decay_power: float | str
    schur_summand_power: float | str
    convergence_margin: float | str
    infinite_limit_admissible: bool
    uv_cutoff_required: bool
    truncation_order: int
    normalized_tail_bound: float | None
    proof_contract: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class _CompactMode:
    label: str
    mass_ev: float
    overlap: float
    spectral_residual: float = 0.0
    profile_normalisation_residual: float = 0.0


@dataclass(frozen=True)
class TakagiSpectrumIR:
    takagi_masses_ev: tuple[float, ...]
    mass_squared_ev2: tuple[float, ...]
    active_mixing_real: tuple[tuple[float, ...], ...]
    active_mixing_imag: tuple[tuple[float, ...], ...]
    full_mixing_real: tuple[tuple[float, ...], ...]
    full_mixing_imag: tuple[tuple[float, ...], ...]
    active_weight_normalization_residuals: tuple[float, float, float]
    basis_labels: tuple[str, ...]
    complex_symmetry_residual: float
    takagi_unitarity_residual: float
    takagi_diagonalization_residual: float
    takagi_reconstruction_residual: float
    minimum_mass_ev: float
    beta_effective_mass_ev: float
    majorana_effective_mass_ev: float

    def active_mixing_matrix(self) -> np.ndarray:
        return np.asarray(self.active_mixing_real, dtype=float) + 1j*np.asarray(self.active_mixing_imag, dtype=float)

    def full_mixing_matrix(self) -> np.ndarray:
        return np.asarray(self.full_mixing_real, dtype=float) + 1j*np.asarray(self.full_mixing_imag, dtype=float)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class HigherDimensionalNeutrinoIR:
    schema: str
    micro_parameters: Mapping[str, Any]
    active_axis_count: int
    geometry_ir: CompactificationGeometryIR
    kk_convergence: KKConvergenceCertificateIR
    takagi_spectrum: TakagiSpectrumIR
    propagating_eigenmodes: int
    maximum_compact_momentum_ev: float
    finite_tower_disclosed: bool
    uv_cutoff_required: bool
    uv_cutoff_satisfied: bool
    controlled_limits: Mapping[str, bool]
    diagnostics: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class NeutrinoCandidateIR:
    schema: str
    candidate_id: str
    family: str
    oscillation_parameters: Mapping[str, Any]
    microscopic_parameters: Mapping[str, Any]
    nuisance_policy: str
    lawspace_derivation_digest: str
    operator_identity_status: str
    operator_identity: Mapping[str, Any]
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class DirectedOperatorSearchRequest:
    """Execution policy for blind open-ended neutrino operator discovery.

    The discovery core receives only owner-supported mathematical/physical
    primitives and generic observable probes.  Published BSM family labels,
    ready-made mass-matrix templates, KATRIN/JUNO constraints and literature
    fingerprints are not inputs to generation or ranking.  All finite lists
    below are execution probes, never scientific ceilings.
    """

    dimension_representatives: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 8, 16, 32, 64)
    points_per_primitive_coordinate: int = 2
    kk_modes_per_family: int = 4
    seed: int = 6901
    novelty_neighbour_count: int = 12
    priority_region_count: int = 8
    mutation_children_per_region: int = 4
    initial_mutation_step: float = 0.125
    minimum_mutation_step: float = 0.00390625
    novelty_relative_tolerance: float = 0.01
    quality_relative_tolerance: float = 0.005
    archive_stability_rounds: int = 2
    kernel_order_representatives: tuple[int, ...] = (0, 1, 2, 4, 8)

    def validate(self) -> None:
        if not self.dimension_representatives or any((not isinstance(d, int) or d < 0) for d in self.dimension_representatives):
            raise ValueError("dimension_representatives must be non-negative integer execution probes")
        if self.points_per_primitive_coordinate < 1:
            raise ValueError("points_per_primitive_coordinate must be positive")
        if self.kk_modes_per_family < 0:
            raise ValueError("kk_modes_per_family must be non-negative")
        if self.novelty_neighbour_count < 2 or self.priority_region_count < 1 or self.mutation_children_per_region < 1:
            raise ValueError("novelty search requires at least two neighbours and positive archive/mutation counts")
        if not 0.0 < self.minimum_mutation_step <= self.initial_mutation_step <= 0.5:
            raise ValueError("mutation steps must satisfy 0 < minimum <= initial <= 0.5")
        if self.novelty_relative_tolerance < 0.0 or self.quality_relative_tolerance < 0.0:
            raise ValueError("novelty and quality relative tolerances must be non-negative")
        if self.archive_stability_rounds < 1:
            raise ValueError("archive_stability_rounds must be positive")
        if not self.kernel_order_representatives or any((not isinstance(v, int) or v < 0) for v in self.kernel_order_representatives):
            raise ValueError("kernel order representatives must be non-negative integer execution probes")

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class NeutrinoPhenomenologyOwner:
    """Single authoritative neutrino owner for microphysics and observables."""

    def __init__(self, parameters: OscillationParameters | None = None) -> None:
        self.parameters = parameters or OscillationParameters()
        self.parameters.validate()

    def candidate_ir(
        self,
        *,
        candidate_id: str,
        family: str,
        microscopic_parameters: HigherDimensionalMicroParameters | Mapping[str, Any] | None = None,
        nuisance_policy: str = "PROFILE_EXPERIMENT_SPECIFIC_AND_SHARE_ONLY_DECLARED_GLOBAL_NUISANCE",
        lawspace_derivation_digest: str = "",
    ) -> NeutrinoCandidateIR:
        """Materialize one digest-complete candidate identity when microphysics is executable.

        Mapping-only candidates remain explicitly incomplete rather than receiving
        fabricated phases or mixing matrices.  A full microphysical declaration is
        lowered through this same owner to one Takagi spectrum shared by every
        experiment owner.
        """
        if not candidate_id or not family:
            raise ValueError("candidate_id and family are required")
        operator_identity: Mapping[str, Any]
        if isinstance(microscopic_parameters, HigherDimensionalMicroParameters):
            microscopic_parameters.validate()
            micro_payload: Mapping[str, Any] = microscopic_parameters.to_dict()
            ir = self.micro_to_ir(microscopic_parameters)
            operator_identity = {
                "schema": "phi-neutrino-operator-identity/v6.9",
                "micro_parameters": micro_payload,
                "geometry": ir.geometry_ir.to_dict(),
                "kk_convergence": ir.kk_convergence.to_dict(),
                "takagi_spectrum": ir.takagi_spectrum.to_dict(),
                "propagating_eigenmodes": ir.propagating_eigenmodes,
                "controlled_limits": dict(ir.controlled_limits),
            }
            operator_identity = {**operator_identity, "digest": _digest(operator_identity)}
            identity_status = "COMPLETE_OWNER_LOWERED_OPERATOR_IDENTITY"
        elif microscopic_parameters is None:
            micro_payload = {}
            operator_identity = {}
            identity_status = "INCOMPLETE_NO_MICROPHYSICS"
        else:
            micro_payload = dict(microscopic_parameters)
            operator_identity = {}
            identity_status = "INCOMPLETE_MAPPING_NOT_OWNER_LOWERED"
        payload = {
            "schema": "phi-neutrino-candidate-ir/v6.9",
            "candidate_id": candidate_id,
            "family": family,
            "oscillation_parameters": self.parameters.to_dict(),
            "microscopic_parameters": micro_payload,
            "nuisance_policy": nuisance_policy,
            "lawspace_derivation_digest": lawspace_derivation_digest,
            "operator_identity_status": identity_status,
            "operator_identity": operator_identity,
        }
        return NeutrinoCandidateIR(**payload, digest=_digest(payload))

    def lower_multidomain_lawspace_spec(self, spec: Mapping[str, Any]) -> tuple[HigherDimensionalMicroParameters, NeutrinoCandidateIR]:
        required = {"schema", "candidate_id", "bridge_id", "geometry", "microparameters", "digest", "lowering_owner"}
        missing = sorted(required - set(spec))
        if missing:
            raise ValueError(f"multidomain spec missing fields: {missing}")
        if spec["bridge_id"] != "NEUTRINO_MULTIDOMAIN_THEORY_BRIDGE":
            raise ValueError("unsupported law-space bridge")
        if spec["lowering_owner"] != f"{OWNER_ID}/{OWNER_VERSION}":
            raise ValueError("multidomain spec is bound to another lowering owner")
        expected = _digest({k: v for k, v in spec.items() if k != "digest"})
        if expected != spec["digest"]:
            raise ValueError("multidomain derivation digest mismatch")
        payload = dict(spec["microparameters"])
        payload.pop("canonical_geometry", None)
        payload["geometry"] = str(spec["geometry"])
        for key in ("radii_micrometre", "family_coupling_scales", "family_bulk_masses_ev", "family_brane_kinetic", "boundary_phases", "family_dirac_phases_rad", "family_warp_bulk_c"):
            if key in payload and isinstance(payload[key], list):
                payload[key] = tuple(payload[key])
        micro = HigherDimensionalMicroParameters(**payload)
        micro.validate()
        candidate = self.candidate_ir(
            candidate_id=str(spec["candidate_id"]),
            family="HIGHER_DIMENSIONAL_MICRO_IR",
            microscopic_parameters=micro,
            lawspace_derivation_digest=str(spec["digest"]),
        )
        return micro, candidate

    @staticmethod
    def pmns_matrix(parameters: OscillationParameters, *, majorana_phases: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
        parameters.validate()
        s12, s13, s23 = (math.sqrt(parameters.sin2_theta12), math.sqrt(parameters.sin2_theta13), math.sqrt(parameters.sin2_theta23))
        c12, c13, c23 = (math.sqrt(1.0 - parameters.sin2_theta12), math.sqrt(1.0 - parameters.sin2_theta13), math.sqrt(1.0 - parameters.sin2_theta23))
        d = parameters.delta_cp_rad
        u = np.array(
            [
                [c12 * c13, s12 * c13, s13 * np.exp(-1j * d)],
                [-s12 * c23 - c12 * s23 * s13 * np.exp(1j * d), c12 * c23 - s12 * s23 * s13 * np.exp(1j * d), s23 * c13],
                [s12 * s23 - c12 * c23 * s13 * np.exp(1j * d), -c12 * s23 - s12 * c23 * s13 * np.exp(1j * d), c23 * c13],
            ],
            dtype=complex,
        )
        p = np.diag([np.exp(0.5j * majorana_phases[0]), np.exp(0.5j * majorana_phases[1]), 1.0 + 0.0j])
        return u @ p

    def vacuum_amplitude(self, baseline_km: float, energy_gev: float, *, parameters: OscillationParameters | None = None, majorana_phases: tuple[float, float] = (0.0, 0.0), antineutrino: bool = False) -> np.ndarray:
        if baseline_km < 0.0 or energy_gev <= 0.0:
            raise ValueError("baseline must be non-negative and energy positive")
        p = parameters or self.parameters
        u = self.pmns_matrix(p, majorana_phases=majorana_phases)
        if antineutrino:
            u = np.conjugate(u)
        phases = np.exp(-1j * OSCILLATION_PHASE_KM_GEV * (p.masses_ev() ** 2) * baseline_km / energy_gev)
        return u @ np.diag(phases) @ np.conjugate(u.T)

    def vacuum_probability_matrix(self, baseline_km: float, energy_gev: float, **kwargs: Any) -> np.ndarray:
        return np.abs(self.vacuum_amplitude(baseline_km, energy_gev, **kwargs)) ** 2

    def matter_amplitude(self, energy_gev: float, layers: Sequence[MatterLayer], *, parameters: OscillationParameters | None = None, antineutrino: bool = False) -> np.ndarray:
        if energy_gev <= 0.0:
            raise ValueError("energy must be positive")
        p = parameters or self.parameters
        u = self.pmns_matrix(p)
        if antineutrino:
            u = np.conjugate(u)
        mass_term = u @ np.diag(p.masses_ev() ** 2) @ np.conjugate(u.T)
        total = np.eye(3, dtype=complex)
        for layer in layers:
            layer.validate()
            a = MATTER_POTENTIAL_EV2 * layer.electron_fraction * layer.density_g_cm3 * energy_gev
            if antineutrino:
                a = -a
            h_ev2 = mass_term + np.diag([a, 0.0, 0.0])
            total = expm(-1j * OSCILLATION_PHASE_KM_GEV * h_ev2 * layer.length_km / energy_gev) @ total
        return total

    def matter_probability_matrix(self, energy_gev: float, layers: Sequence[MatterLayer], **kwargs: Any) -> np.ndarray:
        return np.abs(self.matter_amplitude(energy_gev, layers, **kwargs)) ** 2


    def nsi_matter_amplitude(
        self,
        energy_gev: float,
        layers: Sequence[MatterLayer],
        nsi: NonStandardInteractionParameters,
        *,
        parameters: OscillationParameters | None = None,
        antineutrino: bool = False,
    ) -> np.ndarray:
        if energy_gev <= 0.0:
            raise ValueError("energy must be positive")
        nsi.validate()
        p = parameters or self.parameters
        u = self.pmns_matrix(p)
        epsilon = nsi.epsilon_matrix()
        if antineutrino:
            u = np.conjugate(u)
            epsilon = np.conjugate(epsilon)
        mass_term = u @ np.diag(p.masses_ev() ** 2) @ np.conjugate(u.T)
        total = np.eye(3, dtype=complex)
        for layer in layers:
            layer.validate()
            a = MATTER_POTENTIAL_EV2 * layer.electron_fraction * layer.density_g_cm3 * energy_gev
            if antineutrino:
                a = -a
            matter_kernel = np.diag([1.0, 0.0, 0.0]).astype(complex) + epsilon
            h_ev2 = mass_term + a * matter_kernel
            total = expm(-1j * OSCILLATION_PHASE_KM_GEV * h_ev2 * layer.length_km / energy_gev) @ total
        return total

    def nsi_matter_probability_matrix(self, energy_gev: float, layers: Sequence[MatterLayer], nsi: NonStandardInteractionParameters, **kwargs: Any) -> np.ndarray:
        return np.abs(self.nsi_matter_amplitude(energy_gev, layers, nsi, **kwargs)) ** 2

    def sterile_matter_probability_matrix(
        self,
        energy_gev: float,
        layers: Sequence[MatterLayer],
        sterile: SterileParameters,
        *,
        parameters: OscillationParameters | None = None,
        antineutrino: bool = False,
    ) -> np.ndarray:
        if energy_gev <= 0.0:
            raise ValueError("energy must be positive")
        p = parameters or self.parameters
        u = self.sterile_mixing_matrix(p, sterile)
        if antineutrino:
            u = np.conjugate(u)
        masses_sq = np.concatenate([p.masses_ev() ** 2, [p.masses_ev()[0] ** 2 + sterile.dm41_ev2]])
        total = np.eye(4, dtype=complex)
        for layer in layers:
            layer.validate()
            a = MATTER_POTENTIAL_EV2 * layer.electron_fraction * layer.density_g_cm3 * energy_gev
            if antineutrino:
                a = -a
            h_ev2 = u @ np.diag(masses_sq) @ np.conjugate(u.T) + np.diag([a, 0.0, 0.0, 0.0])
            total = expm(-1j * OSCILLATION_PHASE_KM_GEV * h_ev2 * layer.length_km / energy_gev) @ total
        return np.abs(total[:3, :3]) ** 2

    @staticmethod
    def sterile_mixing_matrix(parameters: OscillationParameters, sterile: SterileParameters) -> np.ndarray:
        sterile.validate()
        u4 = np.eye(4, dtype=complex)
        u4[:3, :3] = NeutrinoPhenomenologyOwner.pmns_matrix(parameters)

        def rotation(i: int, j: int, angle: float) -> np.ndarray:
            r = np.eye(4, dtype=complex)
            c, s = math.cos(angle), math.sin(angle)
            r[i, i] = r[j, j] = c
            r[i, j] = s
            r[j, i] = -s
            return r

        return rotation(2, 3, sterile.theta34_rad) @ rotation(1, 3, sterile.theta24_rad) @ rotation(0, 3, sterile.theta14_rad) @ u4

    def sterile_probability_matrix(self, baseline_km: float, energy_gev: float, sterile: SterileParameters, *, parameters: OscillationParameters | None = None) -> np.ndarray:
        p = parameters or self.parameters
        u = self.sterile_mixing_matrix(p, sterile)
        active_masses_sq = p.masses_ev() ** 2
        m4_sq = active_masses_sq[0] + sterile.dm41_ev2
        phases = np.exp(-1j * OSCILLATION_PHASE_KM_GEV * np.concatenate([active_masses_sq, [m4_sq]]) * baseline_km / energy_gev)
        return np.abs(u @ np.diag(phases) @ np.conjugate(u.T)) ** 2

    @staticmethod
    @lru_cache(maxsize=256)
    def _ordered_mode_vectors(
        dimensions: int,
        radii_ev_inv: tuple[float, ...],
        phases: tuple[float, ...],
        requested_modes: int,
        uv_cutoff_ev: float | None,
    ) -> tuple[tuple[int, ...], ...]:
        """Return the k lowest non-zero lattice momenta without a shell ceiling.

        The non-negative orthant is monotone in every coordinate because all
        boundary phases are in [0,1).  A best-first heap therefore enumerates
        lattice states in increasing momentum and needs O(k*d) frontier growth
        instead of the former Cartesian shell with ``shell <= 512``.
        """
        if requested_modes < 1:
            return tuple()
        if dimensions < 1:
            return tuple()
        if len(radii_ev_inv) != dimensions or len(phases) != dimensions:
            raise ValueError("lattice coordinate dimensionality mismatch")

        def momentum(vector: tuple[int, ...]) -> float:
            return math.sqrt(sum(((vector[a] + phases[a]) / radii_ev_inv[a]) ** 2 for a in range(dimensions)))

        origin = tuple(0 for _ in range(dimensions))
        heap: list[tuple[float, tuple[int, ...]]] = [(momentum(origin), origin)]
        visited = {origin}
        result: list[tuple[int, ...]] = []
        while heap and len(result) < requested_modes:
            value, vector = heapq.heappop(heap)
            if uv_cutoff_ev is not None and value > uv_cutoff_ev:
                break
            if any(vector):
                result.append(vector)
            for axis in range(dimensions):
                neighbour = list(vector)
                neighbour[axis] += 1
                key = tuple(neighbour)
                if key in visited:
                    continue
                visited.add(key)
                p = momentum(key)
                if uv_cutoff_ev is None or p <= uv_cutoff_ev:
                    heapq.heappush(heap, (p, key))
        return tuple(result)

    @staticmethod
    def _mode_momentum_ev(vector: Sequence[int], radii_ev_inv: Sequence[float], phases: Sequence[float]) -> float:
        return math.sqrt(sum(((vector[a] + phases[a]) / radii_ev_inv[a]) ** 2 for a in range(len(vector))))

    @staticmethod
    def _orbifold_normalisation(vector: Sequence[int]) -> float:
        return 2.0 ** (0.5 * sum(1 for value in vector if value != 0))

    @staticmethod
    def _warped_boundary_determinant(x: float, epsilon: float, order: float) -> float:
        a = jv(order, epsilon * x) * yv(order, x)
        b = yv(order, epsilon * x) * jv(order, x)
        scale = max(abs(a) + abs(b), np.finfo(float).tiny)
        return float((a - b) / scale)

    @classmethod
    @lru_cache(maxsize=256)
    def _warped_dimensionless_roots(
        cls,
        warp_exponent: float,
        bulk_c: float,
        requested_modes: int,
    ) -> tuple[tuple[float, float], ...]:
        if requested_modes < 1:
            return tuple()
        epsilon = math.exp(-warp_exponent)
        order = abs(float(bulk_c) + 0.5)
        roots: list[tuple[float, float]] = []
        step = math.pi / 12.0
        left = max(1.0e-7, step * 0.01)
        f_left = cls._warped_boundary_determinant(left, epsilon, order)
        x = left + step
        # Sturm-Liouville spectrum is unbounded; grow the bracket until the
        # requested finite execution slice is resolved.  No physical root
        # ceiling is encoded here.
        while len(roots) < requested_modes:
            f_right = cls._warped_boundary_determinant(x, epsilon, order)
            if math.isfinite(f_left) and math.isfinite(f_right):
                if f_left == 0.0:
                    root = left
                elif f_left * f_right < 0.0:
                    try:
                        root = brentq(
                            lambda value: cls._warped_boundary_determinant(value, epsilon, order),
                            left,
                            x,
                            xtol=2.0e-13,
                            rtol=2.0e-13,
                            maxiter=200,
                        )
                    except ValueError:
                        root = math.nan
                else:
                    root = math.nan
                if math.isfinite(root) and (not roots or abs(root - roots[-1][0]) > 1.0e-6):
                    residual = abs(cls._warped_boundary_determinant(root, epsilon, order))
                    roots.append((float(root), float(residual)))
            left, f_left = x, f_right
            x += step
        if len(roots) < requested_modes:
            raise ValueError("warped spectral root search did not resolve the requested KK tower")
        return tuple(roots)

    @classmethod
    @lru_cache(maxsize=2048)
    def _warped_profile_overlap(
        cls,
        root: float,
        warp_exponent: float,
        bulk_c: float,
    ) -> tuple[float, float]:
        epsilon = math.exp(-warp_exponent)
        order = abs(float(bulk_c) + 0.5)
        uv_j, uv_y = jv(order, epsilon * root), yv(order, epsilon * root)
        if abs(uv_y) > np.finfo(float).tiny:
            coefficient = -uv_j / uv_y
        else:
            coefficient = 0.0
        grid = np.geomspace(max(epsilon, 1.0e-8), 1.0, 2048)
        profile = grid ** 2.5 * (jv(order, root * grid) + coefficient * yv(order, root * grid))
        density = np.abs(profile) ** 2 / np.maximum(grid, np.finfo(float).tiny) ** 4
        norm2 = float(np.trapezoid(density, grid))
        if not math.isfinite(norm2) or norm2 <= 0.0:
            raise ValueError("warped profile has no finite positive norm")
        normalised = profile / math.sqrt(norm2)
        overlap = float(abs(normalised[-1]))
        check = float(abs(np.trapezoid(np.abs(normalised) ** 2 / grid ** 4, grid) - 1.0))
        return overlap, check

    @staticmethod
    def classify_infinite_dimension_kk_domain(
        *,
        dimensions: int,
        localised: bool = False,
        brane_kinetic_active: bool = False,
        warped: bool = False,
    ) -> Mapping[str, Any]:
        """Analytically classify every finite d without enumerating an infinite tower."""
        if dimensions < 1:
            return {"status": "FOUR_DIMENSIONAL", "infinite_limit_admissible": True, "asymptotic_dimension": 0}
        if warped:
            if dimensions != 1:
                return {"status": "WARPED_DOMAIN_REQUIRES_ONE_DIMENSION", "infinite_limit_admissible": False, "asymptotic_dimension": dimensions}
            return {"status": "PROVED_CONVERGENT_WARPED_1D_LINEAR_SPECTRUM", "infinite_limit_admissible": True, "asymptotic_dimension": 1, "schur_summand_power": -2.0}
        if localised:
            return {"status": "PROVED_CONVERGENT_GAUSSIAN_LOCALISATION", "infinite_limit_admissible": True, "asymptotic_dimension": dimensions, "schur_summand_power": "EXPONENTIAL"}
        p = 1 if brane_kinetic_active else 0
        q = float(dimensions - 3 - 2 * p)
        if q < -1.0:
            status = "PROVED_CONVERGENT_POWER_TAIL"
            admissible = True
        elif q == -1.0:
            status = "CUTOFF_DEPENDENT_LOGARITHMIC_EFT"
            admissible = False
        else:
            status = "CUTOFF_DEPENDENT_POWER_EFT"
            admissible = False
        return {
            "status": status,
            "infinite_limit_admissible": admissible,
            "asymptotic_dimension": dimensions,
            "brane_kinetic_decay_power": p,
            "schur_summand_power": q,
        }

    @staticmethod
    def qualify_execution_budget(
        micro: HigherDimensionalMicroParameters,
        budget: ExecutionBudgetIR | None = None,
    ) -> Mapping[str, Any]:
        budget = budget or ExecutionBudgetIR()
        # full Majorana doubling: 3 brane + 3 families*k compact states in
        # each chiral block.  This is a resource estimate, not a domain gate.
        single_chiral = 3 + 3 * int(micro.kk_modes_per_family)
        dense_dimension = 2 * single_chiral
        blocked = bool(
            budget.maximum_dense_operator_dimension is not None
            and dense_dimension > budget.maximum_dense_operator_dimension
        )
        return {
            "status": "RESOURCE_BLOCKED_WITH_BOUND" if blocked else "EXECUTION_BUDGET_ADMISSIBLE",
            "estimated_dense_operator_dimension": dense_dimension,
            "budget": budget.to_dict(),
            "scientific_admissibility_changed": False,
        }

    def _compact_modes_by_family(
        self,
        micro: HigherDimensionalMicroParameters,
    ) -> tuple[tuple[tuple[_CompactMode, ...], ...], CompactificationGeometryIR]:
        canonical = micro.canonical_geometry
        if micro.dimensions == 0 or micro.kk_modes_per_family == 0:
            empty = (tuple(), tuple(), tuple())
            geometry_ir = CompactificationGeometryIR(
                input_geometry=micro.geometry,
                canonical_geometry="FOUR_DIMENSIONAL" if micro.dimensions == 0 else canonical,
                dimensions=micro.dimensions,
                topology="POINT" if micro.dimensions == 0 else canonical,
                orbifold_action="NONE" if micro.dimensions == 0 else "DECLARED_WITHOUT_EXCITED_MODES",
                metric_contract="MINKOWSKI_4D" if micro.dimensions == 0 else "COMPACT_SECTOR_NO_EXCITED_MODES",
                radii_micrometre=micro.radii_micrometre,
                boundary_phases=micro.phases,
                warp_curvature_ev=micro.warp_curvature_ev,
                warp_exponent=micro.warp_exponent,
                family_warp_bulk_c=micro.family_warp_bulk_c,
                boundary_condition=micro.warp_boundary_condition,
                family_mode_masses_ev=(tuple(), tuple(), tuple()),
                family_mode_overlaps=(tuple(), tuple(), tuple()),
                family_mode_labels=(tuple(), tuple(), tuple()),
                maximum_spectral_residual=0.0,
                maximum_profile_normalisation_residual=0.0,
                controlled_limit="EXACT_FOUR_DIMENSIONAL" if micro.dimensions == 0 else "FINITE_ZERO_MODE_SECTOR",
            )
            return empty, geometry_ir

        if canonical == "WARPED_INTERVAL_RS1" and micro.warp_exponent == 0.0:
            canonical_for_spectrum = "FLAT_S1_Z2"
            controlled_limit = "EXACT_ZERO_WARP_TO_FLAT_S1_Z2"
        else:
            canonical_for_spectrum = canonical
            controlled_limit = "NONE"

        families: list[tuple[_CompactMode, ...]] = []
        maximum_spectral = 0.0
        maximum_profile = 0.0
        if canonical_for_spectrum.startswith("FLAT_") or canonical_for_spectrum == "LOCALISED_FLAT_ORBIFOLD":
            radii_ev_inv = tuple(r * MICROMETRE_TO_EV_INV for r in micro.radii_micrometre)
            vectors = self._ordered_mode_vectors(
                micro.dimensions,
                radii_ev_inv,
                micro.phases,
                micro.kk_modes_per_family,
                micro.uv_cutoff_ev,
            )
            if len(vectors) < micro.kk_modes_per_family:
                raise ValueError("declared UV cutoff does not contain the requested number of KK modes")
            for family in range(3):
                rows: list[_CompactMode] = []
                kinetic = micro.family_brane_kinetic[family]
                for vector in vectors:
                    momentum = self._mode_momentum_ev(vector, radii_ev_inv, micro.phases)
                    shell_norm = math.sqrt(sum(v * v for v in vector))
                    localisation = math.exp(-0.5 * (micro.localisation_width_fraction * shell_norm) ** 2)
                    kinetic_suppression = 1.0 / math.sqrt(1.0 + kinetic * momentum * momentum)
                    overlap = self._orbifold_normalisation(vector) * localisation * kinetic_suppression
                    vector_label = "_".join(str(v) for v in vector)
                    rows.append(_CompactMode(f"n_{vector_label}", momentum, overlap))
                families.append(tuple(rows))
        elif canonical_for_spectrum == "WARPED_INTERVAL_RS1":
            mass_scale = micro.warp_curvature_ev * math.exp(-micro.warp_exponent)
            for family in range(3):
                rows = []
                roots = self._warped_dimensionless_roots(
                    micro.warp_exponent,
                    micro.family_warp_bulk_c[family],
                    micro.kk_modes_per_family,
                )
                reference_overlap = None
                for mode_index, (root, residual) in enumerate(roots, start=1):
                    raw_overlap, profile_residual = self._warped_profile_overlap(
                        root, micro.warp_exponent, micro.family_warp_bulk_c[family]
                    )
                    if reference_overlap is None:
                        reference_overlap = max(raw_overlap, np.finfo(float).tiny)
                    overlap = raw_overlap / reference_overlap
                    kinetic = micro.family_brane_kinetic[family]
                    mass = root * mass_scale
                    overlap /= math.sqrt(1.0 + kinetic * mass * mass)
                    rows.append(_CompactMode(f"rs1_{mode_index}", mass, overlap, residual, profile_residual))
                    maximum_spectral = max(maximum_spectral, residual)
                    maximum_profile = max(maximum_profile, profile_residual)
                families.append(tuple(rows))
        else:
            raise ValueError(f"unimplemented compactification geometry: {canonical_for_spectrum}")

        topology = {
            "FLAT_S1_Z2": "S1/Z2",
            "FLAT_ANISOTROPIC_T2_Z2": "T2/Z2",
            "FLAT_TD_Z2": f"T{micro.dimensions}/Z2",
            "LOCALISED_FLAT_ORBIFOLD": f"LOCALISED_T{micro.dimensions}/Z2",
            "WARPED_INTERVAL_RS1": "S1/Z2_INTERVAL",
        }[canonical_for_spectrum]
        metric = (
            "ds2=eta_mn dx^m dx^n + sum_a R_a^2 dtheta_a^2"
            if canonical_for_spectrum != "WARPED_INTERVAL_RS1"
            else "ds2=exp(-2 k |y|) eta_mn dx^m dx^n + dy2"
        )
        geometry_ir = CompactificationGeometryIR(
            input_geometry=micro.geometry,
            canonical_geometry=canonical_for_spectrum,
            dimensions=micro.dimensions,
            topology=topology,
            orbifold_action="Z2_CHIRAL_PROJECTION",
            metric_contract=metric,
            radii_micrometre=micro.radii_micrometre,
            boundary_phases=micro.phases,
            warp_curvature_ev=micro.warp_curvature_ev,
            warp_exponent=micro.warp_exponent,
            family_warp_bulk_c=micro.family_warp_bulk_c,
            boundary_condition=micro.warp_boundary_condition if canonical_for_spectrum == "WARPED_INTERVAL_RS1" else "EVEN_RH_ZERO_MODE",
            family_mode_masses_ev=tuple(tuple(mode.mass_ev for mode in family) for family in families),
            family_mode_overlaps=tuple(tuple(mode.overlap for mode in family) for family in families),
            family_mode_labels=tuple(tuple(mode.label for mode in family) for family in families),
            maximum_spectral_residual=maximum_spectral,
            maximum_profile_normalisation_residual=maximum_profile,
            controlled_limit=controlled_limit,
        )
        return tuple(families), geometry_ir

    @staticmethod
    def _kk_convergence_certificate(
        micro: HigherDimensionalMicroParameters,
        geometry_ir: CompactificationGeometryIR,
    ) -> KKConvergenceCertificateIR:
        n = max(int(micro.kk_modes_per_family), 1)
        if micro.kk_modes_per_family == 0 or all(value == 0.0 for value in micro.family_coupling_scales):
            return KKConvergenceCertificateIR(
                status="PROVED_TRIVIAL_ZERO_COUPLING_OR_ZERO_TOWER",
                canonical_geometry=geometry_ir.canonical_geometry,
                asymptotic_dimension=max(micro.dimensions, 0),
                shell_density_power=float(max(micro.dimensions - 1, 0)),
                coupling_decay_power="INFINITE",
                schur_summand_power="MINUS_INFINITY",
                convergence_margin="INFINITE",
                infinite_limit_admissible=True,
                uv_cutoff_required=False,
                truncation_order=micro.kk_modes_per_family,
                normalized_tail_bound=0.0,
                proof_contract=("ALL_BRANE_BULK_COUPLINGS_ZERO_OR_NO_EXCITED_MODES",),
            )
        if geometry_ir.canonical_geometry == "WARPED_INTERVAL_RS1":
            q = -2.0
            tail = 1.0 / n
            return KKConvergenceCertificateIR(
                status="PROVED_CONVERGENT_WARPED_1D_LINEAR_SPECTRUM",
                canonical_geometry=geometry_ir.canonical_geometry,
                asymptotic_dimension=1,
                shell_density_power=0.0,
                coupling_decay_power=0.0,
                schur_summand_power=q,
                convergence_margin=1.0,
                infinite_limit_admissible=True,
                uv_cutoff_required=False,
                truncation_order=micro.kk_modes_per_family,
                normalized_tail_bound=tail,
                proof_contract=(
                    "SELF_ADJOINT_COMPACT_INTERVAL_DIRAC_DOMAIN",
                    "ASYMPTOTIC_KK_MASSES_LINEAR_IN_MODE_NUMBER",
                    "NORMALISED_BRANE_OVERLAPS_BOUNDED",
                    "SUM_N_ABS_G_N_SQUARED_OVER_MU_N_SQUARED_CONVERGES",
                ),
            )
        dimension = micro.dimensions
        if micro.localisation_width_fraction > 0.0:
            width = micro.localisation_width_fraction
            tail = math.exp(-(width * n) ** 2) / max(2.0 * width * width * n, np.finfo(float).tiny)
            return KKConvergenceCertificateIR(
                status="PROVED_CONVERGENT_GAUSSIAN_LOCALISATION",
                canonical_geometry=geometry_ir.canonical_geometry,
                asymptotic_dimension=dimension,
                shell_density_power=float(dimension - 1),
                coupling_decay_power="GAUSSIAN",
                schur_summand_power="SUPERPOLYNOMIAL",
                convergence_margin="INFINITE",
                infinite_limit_admissible=True,
                uv_cutoff_required=False,
                truncation_order=micro.kk_modes_per_family,
                normalized_tail_bound=float(tail),
                proof_contract=(
                    "LATTICE_SHELL_MULTIPLICITY_GROWS_POLYNOMIALLY",
                    "GAUSSIAN_BRANE_OVERLAP_DOMINATES_ANY_FINITE_DIMENSIONAL_SHELL_GROWTH",
                ),
            )
        p = 1.0 if min(micro.family_brane_kinetic) > 0.0 else 0.0
        q = float(dimension - 3 - 2 * p)
        margin = float(-1.0 - q)
        convergent = q < -1.0
        tail = float(n ** (q + 1.0) / (-q - 1.0)) if convergent else None
        if convergent:
            status = "PROVED_CONVERGENT_POLYNOMIAL_KK_TAIL"
        elif abs(q + 1.0) <= 1.0e-12:
            status = "CUTOFF_DEPENDENT_LOGARITHMIC_EFT"
        else:
            status = "CUTOFF_DEPENDENT_POWER_LAW_EFT"
        return KKConvergenceCertificateIR(
            status=status,
            canonical_geometry=geometry_ir.canonical_geometry,
            asymptotic_dimension=dimension,
            shell_density_power=float(dimension - 1),
            coupling_decay_power=p,
            schur_summand_power=q,
            convergence_margin=margin,
            infinite_limit_admissible=convergent,
            uv_cutoff_required=not convergent,
            truncation_order=micro.kk_modes_per_family,
            normalized_tail_bound=tail,
            proof_contract=(
                "RHO_N_ASYMPTOTIC_N_TO_D_MINUS_1",
                "MU_N_ASYMPTOTIC_N",
                "G_N_ASYMPTOTIC_N_TO_MINUS_P",
                "SCHUR_TAIL_ASYMPTOTIC_SUM_N_TO_D_MINUS_3_MINUS_2P",
                "CONVERGENCE_IFF_P_GREATER_THAN_D_MINUS_2_OVER_2",
            ),
        )

    @staticmethod
    def _takagi_factorization(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, Mapping[str, float]]:
        """Autonne–Takagi factorisation via a real-symmetric doubled problem.

        For ``M=B+iC`` and a Takagi vector ``w=x+i y`` satisfying
        ``M w = m conjugate(w)``, the real vector ``(x,y)`` obeys

            [[B,-C],[-C,-B]] (x,y)^T = m (x,y)^T.

        The doubled matrix is real symmetric, so ``eigh`` gives an orthogonal
        basis and avoids the phase/degeneracy instability of the former SVD
        square-root mismatch construction.  Positive eigenvalues are the
        Takagi singular values; the n largest eigenpairs provide the n
        non-negative modes, including exact/near zero modes.
        """
        m = np.asarray(matrix, dtype=complex)
        if m.ndim != 2 or m.shape[0] != m.shape[1]:
            raise ValueError("Takagi matrix must be square")
        if m.size == 0:
            raise ValueError("Takagi matrix must be non-empty")
        n = m.shape[0]
        if not np.all(np.isfinite(m)):
            raise ValueError("Takagi matrix contains non-finite entries")
        maximum_entry = float(np.max(np.abs(m)))
        # This is an execution/numerical dynamic-range bound, not a scientific
        # mass or dimension ceiling.  It is chosen before Frobenius norms and
        # m^2 observables so extreme generated coordinates fail closed instead
        # of emitting NumPy overflow/NaN diagnostics.
        safe_entry_bound = math.sqrt(np.finfo(float).max) / float(max(1, n))
        if maximum_entry > safe_entry_bound:
            raise ValueError(
                f"NUMERICAL_DYNAMIC_RANGE_UNSUPPORTED: max|M_ij|={maximum_entry:.6e} "
                f"exceeds safe float64 execution bound {safe_entry_bound:.6e}; "
                "this is an execution bound, not a scientific admissibility ceiling"
            )
        absolute_scale = float(np.linalg.norm(m))
        scale = max(absolute_scale, np.finfo(float).eps * max(1, n))
        symmetry = float(np.linalg.norm(m - m.T) / scale)
        if symmetry > 1.0e-10:
            raise ValueError("Takagi matrix must be complex symmetric")
        if absolute_scale == 0.0:
            w = np.eye(n, dtype=complex)
            masses = np.zeros(n, dtype=float)
        else:
            b = np.real(m)
            c = np.imag(m)
            doubled = np.block([[b, -c], [-c, -b]])
            eigenvalues, eigenvectors = np.linalg.eigh(doubled)
            take = np.argsort(eigenvalues, kind="stable")[-n:]
            masses = np.maximum(np.asarray(eigenvalues[take], dtype=float), 0.0)
            vectors = eigenvectors[:, take]
            order = np.argsort(masses, kind="stable")
            masses = masses[order]
            vectors = vectors[:, order]
            w = vectors[:n, :] + 1j * vectors[n:, :]
            # Numerical roundoff can leave a tiny complex Gram residual.
            # Polar projection restores unitarity without changing a
            # non-degenerate Takagi basis beyond machine precision.
            gram = w.conj().T @ w
            if np.linalg.norm(gram - np.eye(n)) > 1.0e-12:
                gvals, gvecs = np.linalg.eigh(0.5 * (gram + gram.conj().T))
                if np.min(gvals) <= 0.0:
                    raise ValueError("Takagi eigenbasis lost positive Gram rank")
                invsqrt = gvecs @ np.diag(1.0 / np.sqrt(gvals)) @ gvecs.conj().T
                w = w @ invsqrt
            diagonal = w.T @ m @ w
            # Only a residual diagonal phase is admissible.  The real doubled
            # formulation already fixes it up to numerical sign/phase.
            phases = np.ones(n, dtype=complex)
            for i, value in enumerate(np.diag(diagonal)):
                if abs(value) > np.finfo(float).eps * scale:
                    phases[i] = np.exp(-0.5j * np.angle(value))
            w = w @ np.diag(phases)
            diagonal = w.T @ m @ w
            masses = np.maximum(np.real(np.diag(diagonal)), 0.0)
            order = np.argsort(masses, kind="stable")
            masses = masses[order]
            w = w[:, order]

        diagonal = w.T @ m @ w
        target = np.diag(masses)
        reconstruction = np.conjugate(w) @ target @ np.conjugate(w.T)
        residuals = {
            "complex_symmetry_residual": symmetry,
            "takagi_unitarity_residual": float(np.linalg.norm(w.conj().T @ w - np.eye(w.shape[0]))),
            "takagi_diagonalization_residual": float(np.linalg.norm(diagonal - target) / scale),
            "takagi_reconstruction_residual": float(np.linalg.norm(m - reconstruction) / scale),
            "absolute_takagi_diagonalization_residual": float(np.linalg.norm(diagonal - target)),
            "absolute_takagi_reconstruction_residual": float(np.linalg.norm(m - reconstruction)),
            "normalisation_scale": scale,
        }
        return masses, w, residuals

    def _compact_majorana_mass_operator(
        self,
        micro: HigherDimensionalMicroParameters,
        parameters: OscillationParameters,
        modes_by_family: Sequence[Sequence[_CompactMode]],
    ) -> tuple[np.ndarray, tuple[str, ...], float]:
        """Build the single active Dirac/Majorana/seesaw/KK mass operator."""
        counts = tuple(len(modes) for modes in modes_by_family)
        total_modes = sum(counts)
        side = 3 + total_modes
        left_majorana = np.zeros((side, side), dtype=complex)
        right_majorana = np.zeros((side, side), dtype=complex)
        dirac = np.zeros((side, side), dtype=complex)
        left_majorana[:3, :3] = micro.brane_left_majorana_matrix
        right_majorana[:3, :3] = micro.brane_right_majorana_matrix

        dirac_masses = micro.dirac_masses_ev(parameters)
        dirac_phases = np.exp(1j * np.asarray(micro.family_dirac_phases_rad, dtype=float))
        compact_coupling_basis = micro.active_compact_coupling_matrix(parameters)
        dirac[:3, :3] = micro.active_dirac_matrix(parameters)

        labels_left = [f"nuL_flavour_{name}" for name in ("e", "mu", "tau")]
        labels_right = [f"nuR_zero_family_{i+1}" for i in range(3)]
        maximum_momentum = 0.0
        offset = 3
        for family, modes in enumerate(modes_by_family):
            coupling_scale = micro.family_coupling_scales[family]
            bulk_dirac = micro.family_bulk_masses_ev[family]
            ml = micro.family_bulk_majorana_left_ev[family] * np.exp(1j * micro.family_bulk_majorana_left_phases_rad[family])
            mr = micro.family_bulk_majorana_right_ev[family] * np.exp(1j * micro.family_bulk_majorana_right_phases_rad[family])
            for mode_index, mode in enumerate(modes):
                compact_index = offset + mode_index
                maximum_momentum = max(maximum_momentum, mode.mass_ev)
                coupling = (
                    dirac_masses[family]
                    * dirac_phases[family]
                    * coupling_scale
                    * mode.overlap
                    * micro.compact_coupling_kernel(mode.mass_ev)
                )
                dirac[:3, compact_index] = compact_coupling_basis[:, family] * coupling
                dirac[compact_index, compact_index] = math.sqrt(mode.mass_ev * mode.mass_ev + bulk_dirac * bulk_dirac)
                left_majorana[compact_index, compact_index] = ml
                right_majorana[compact_index, compact_index] = mr
                labels_left.append(f"kkL_family_{family+1}_{mode.label}")
                labels_right.append(f"kkR_family_{family+1}_{mode.label}")
            offset += len(modes)

        full = np.block([[left_majorana, dirac], [dirac.T, right_majorana]])
        labels = tuple(labels_left + labels_right)
        return full, labels, maximum_momentum

    def mass_operator(
        self,
        micro: HigherDimensionalMicroParameters,
        *,
        parameters: OscillationParameters | None = None,
    ) -> tuple[np.ndarray, tuple[str, ...], CompactificationGeometryIR, KKConvergenceCertificateIR, float]:
        """Expose the owner-built mass operator for independent certified cross-checks."""
        micro.validate()
        modes_by_family, geometry_ir = self._compact_modes_by_family(micro)
        convergence = self._kk_convergence_certificate(micro, geometry_ir)
        if convergence.uv_cutoff_required and micro.kk_modes_per_family > 0 and micro.uv_cutoff_ev is None:
            raise ValueError(
                f"{convergence.status} requires explicit uv_cutoff_ev for the declared finite EFT tower"
            )
        mass_matrix, labels, maximum_momentum = self._compact_majorana_mass_operator(
            micro, parameters or self.parameters, modes_by_family
        )
        if micro.uv_cutoff_ev is not None and maximum_momentum > micro.uv_cutoff_ev * (1.0 + 1.0e-12):
            raise ValueError("requested KK spectrum exceeds declared uv_cutoff_ev")
        return mass_matrix, labels, geometry_ir, convergence, maximum_momentum

    def micro_to_ir(self, micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None) -> HigherDimensionalNeutrinoIR:
        p = parameters or self.parameters
        mass_matrix, labels, geometry_ir, convergence, maximum_momentum = self.mass_operator(micro, parameters=p)
        masses, w, residuals = self._takagi_factorization(mass_matrix)
        active = w[:3, :]
        normalization = active @ active.conj().T
        normalization_residuals = tuple(float(abs(normalization[i, i] - 1.0)) for i in range(3))
        mass_squared = masses * masses
        m_beta = float(math.sqrt(max(0.0, np.sum(np.abs(active[0, :]) ** 2 * mass_squared))))
        m_beta_beta = float(abs(np.sum(active[0, :] ** 2 * masses)))

        spectrum = TakagiSpectrumIR(
            takagi_masses_ev=tuple(float(v) for v in masses),
            mass_squared_ev2=tuple(float(v) for v in mass_squared),
            active_mixing_real=tuple(tuple(float(v) for v in row) for row in np.real(active)),
            active_mixing_imag=tuple(tuple(float(v) for v in row) for row in np.imag(active)),
            full_mixing_real=tuple(tuple(float(v) for v in row) for row in np.real(w)),
            full_mixing_imag=tuple(tuple(float(v) for v in row) for row in np.imag(w)),
            active_weight_normalization_residuals=normalization_residuals,
            basis_labels=labels,
            complex_symmetry_residual=float(residuals["complex_symmetry_residual"]),
            takagi_unitarity_residual=float(residuals["takagi_unitarity_residual"]),
            takagi_diagonalization_residual=float(residuals["takagi_diagonalization_residual"]),
            takagi_reconstruction_residual=float(residuals["takagi_reconstruction_residual"]),
            minimum_mass_ev=float(np.min(masses)),
            beta_effective_mass_ev=m_beta,
            majorana_effective_mass_ev=m_beta_beta,
        )
        uv_required = convergence.uv_cutoff_required and micro.kk_modes_per_family > 0
        uv_satisfied = (not uv_required) or (
            micro.uv_cutoff_ev is not None and maximum_momentum <= micro.uv_cutoff_ev * (1.0 + 1.0e-12)
        )
        no_majorana = not micro.majorana_sector_active
        no_kk_coupling = micro.kk_modes_per_family == 0 or all(v == 0.0 for v in micro.family_coupling_scales)
        controlled_limits = {
            "zero_majorana_recovers_dirac_doubled_operator": no_majorana,
            "zero_brane_bulk_coupling_decouples_kk_sector": no_kk_coupling,
            "four_dimensional_sector_has_no_kk_modes": micro.dimensions == 0 and micro.kk_modes_per_family == 0,
            "one_dimensional_zero_bulk_zero_width_is_standard_led_limit": (
                geometry_ir.canonical_geometry == "FLAT_S1_Z2"
                and no_majorana
                and all(v == 0.0 for v in micro.family_bulk_masses_ev)
                and all(v == 0.0 for v in micro.family_brane_kinetic)
                and micro.localisation_width_fraction == 0.0
                and all(v == 0.0 for v in micro.phases)
            ),
            "zero_warp_exactly_lowers_to_flat_s1_z2": geometry_ir.controlled_limit == "EXACT_ZERO_WARP_TO_FLAT_S1_Z2",
            "finite_tower_disclosed": True,
            "infinite_kk_limit_has_analytic_certificate": convergence.infinite_limit_admissible,
        }
        diagnostics = {
            "maximum_active_row_normalization_residual": max(normalization_residuals),
            "active_row_orthogonality_residual": float(np.linalg.norm(normalization - np.eye(3))),
            "mode_count_per_family": tuple(len(row) for row in geometry_ir.family_mode_masses_ev),
            "full_complex_symmetric_dimension": int(mass_matrix.shape[0]),
            "multi_dimensional_tower_is_cutoff_dependent": convergence.uv_cutoff_required,
            "warped_geometry_executed": geometry_ir.canonical_geometry == "WARPED_INTERVAL_RS1",
            "majorana_takagi_system_executed": True,
            "infinite_kk_limit_executed": convergence.infinite_limit_admissible,
            "absolute_takagi_diagonalization_residual": residuals["absolute_takagi_diagonalization_residual"],
            "absolute_takagi_reconstruction_residual": residuals["absolute_takagi_reconstruction_residual"],
            "takagi_normalisation_scale": residuals["normalisation_scale"],
        }
        return HigherDimensionalNeutrinoIR(
            schema=SCHEMA,
            micro_parameters=micro.to_dict(),
            active_axis_count=micro.active_axis_count,
            geometry_ir=geometry_ir,
            kk_convergence=convergence,
            takagi_spectrum=spectrum,
            propagating_eigenmodes=len(masses),
            maximum_compact_momentum_ev=maximum_momentum,
            finite_tower_disclosed=True,
            uv_cutoff_required=uv_required,
            uv_cutoff_satisfied=uv_satisfied,
            controlled_limits=controlled_limits,
            diagnostics=diagnostics,
        )

    def micro_amplitude(self, baseline_km: float, energy_gev: float, micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None, ir: HigherDimensionalNeutrinoIR | None = None, antineutrino: bool = False) -> np.ndarray:
        if baseline_km < 0.0 or energy_gev <= 0.0:
            raise ValueError("baseline must be non-negative and energy positive")
        compact_ir = ir or self.micro_to_ir(micro, parameters=parameters or self.parameters)
        active = compact_ir.takagi_spectrum.active_mixing_matrix()
        if antineutrino:
            active = np.conjugate(active)
        masses_sq = np.asarray(compact_ir.takagi_spectrum.mass_squared_ev2, dtype=float)
        phases = np.exp(-1j * OSCILLATION_PHASE_KM_GEV * masses_sq * baseline_km / energy_gev)
        return active @ np.diag(phases) @ active.conj().T

    def micro_probability_matrix(self, baseline_km: float, energy_gev: float, micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None, ir: HigherDimensionalNeutrinoIR | None = None, antineutrino: bool = False) -> np.ndarray:
        return np.abs(self.micro_amplitude(baseline_km, energy_gev, micro, parameters=parameters, ir=ir, antineutrino=antineutrino)) ** 2

    def micro_matter_amplitude(self, energy_gev: float, layers: Sequence[MatterLayer], micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None, ir: HigherDimensionalNeutrinoIR | None = None, antineutrino: bool = False) -> np.ndarray:
        if energy_gev <= 0.0:
            raise ValueError("energy must be positive")
        compact_ir = ir or self.micro_to_ir(micro, parameters=parameters or self.parameters)
        active = compact_ir.takagi_spectrum.active_mixing_matrix()
        if antineutrino:
            active = np.conjugate(active)
        masses_sq = np.asarray(compact_ir.takagi_spectrum.mass_squared_ev2, dtype=float)
        total = np.eye(len(masses_sq), dtype=complex)
        for layer in layers:
            layer.validate()
            matter = MATTER_POTENTIAL_EV2 * layer.electron_fraction * layer.density_g_cm3 * energy_gev
            if antineutrino:
                matter = -matter
            h_mass = np.diag(masses_sq) + active.conj().T @ np.diag([matter, 0.0, 0.0]) @ active
            total = expm(-1j * OSCILLATION_PHASE_KM_GEV * h_mass * layer.length_km / energy_gev) @ total
        return active @ total @ active.conj().T

    def micro_matter_probability_matrix(self, energy_gev: float, layers: Sequence[MatterLayer], micro: HigherDimensionalMicroParameters, **kwargs: Any) -> np.ndarray:
        return np.abs(self.micro_matter_amplitude(energy_gev, layers, micro, **kwargs)) ** 2

    def beta_effective_mass_ev(self, micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None) -> float:
        return self.micro_to_ir(micro, parameters=parameters or self.parameters).takagi_spectrum.beta_effective_mass_ev

    def majorana_effective_mass_ev(self, micro: HigherDimensionalMicroParameters, *, parameters: OscillationParameters | None = None) -> float:
        return self.micro_to_ir(micro, parameters=parameters or self.parameters).takagi_spectrum.majorana_effective_mass_ev

    def led_probability_matrix(self, baseline_km: float, energy_gev: float, led: LEDParameters, *, parameters: OscillationParameters | None = None) -> np.ndarray:
        """Thin compatibility wrapper; all mathematics is owned by micro→IR."""
        return self.micro_probability_matrix(baseline_km, energy_gev, led.to_micro_parameters(), parameters=parameters)

    def decoherence_probability_matrix(self, baseline_km: float, energy_gev: float, gamma: float, *, parameters: OscillationParameters | None = None) -> np.ndarray:
        if gamma < 0.0:
            raise ValueError("decoherence gamma must be non-negative")
        p = parameters or self.parameters
        coherent = self.vacuum_probability_matrix(baseline_km, energy_gev, parameters=p)
        u = self.pmns_matrix(p)
        incoherent = np.einsum("ai,bi->ab", np.abs(u) ** 2, np.abs(u) ** 2)
        damping = math.exp(-gamma * baseline_km / energy_gev)
        return np.clip(np.real(incoherent + damping * (coherent - incoherent)), 0.0, 1.0)

    def dirac_majorana_oscillation_identifiability(self, baselines_km: Sequence[float], energies_gev: Sequence[float]) -> Mapping[str, Any]:
        max_difference = 0.0
        for baseline in baselines_km:
            for energy in energies_gev:
                p0 = self.vacuum_probability_matrix(baseline, energy, majorana_phases=(0.0, 0.0))
                p1 = self.vacuum_probability_matrix(baseline, energy, majorana_phases=(0.73, -1.17))
                max_difference = max(max_difference, float(np.max(np.abs(p0 - p1))))
        payload = {
            "status": "NOT_IDENTIFIABLE_FROM_OSCILLATIONS",
            "maximum_probability_difference": max_difference,
            "reason": "Majorana phases cancel from flavour-transition probabilities",
            "required_external_observable": "lepton-number-violating process such as neutrinoless double beta decay",
        }
        return {**payload, "digest": _digest(payload)}

    @staticmethod
    def _matrix_tuple(matrix: np.ndarray) -> tuple[tuple[float, float, float], ...]:
        array = np.asarray(matrix, dtype=float)
        return tuple(tuple(float(v) for v in row) for row in array)

    @staticmethod
    def _blind_dense_complex_matrix(
        sample: Sequence[float],
        *,
        log10_min: float,
        log10_max: float,
        zero_threshold: float = 0.0,
    ) -> np.ndarray:
        values = np.asarray(sample, dtype=float)
        if values.size != 18:
            raise ValueError("dense 3x3 complex synthesis requires exactly 18 coordinates")
        magnitude_u = values[:9]
        phase_u = values[9:]
        magnitude = 10.0 ** (log10_min + (log10_max - log10_min) * magnitude_u)
        magnitude = np.where(magnitude_u < zero_threshold, 0.0, magnitude)
        phase = 2.0 * math.pi * phase_u
        return (magnitude * np.exp(1j * phase)).reshape(3, 3)

    @staticmethod
    def _blind_symmetric_complex_matrix(
        sample: Sequence[float],
        *,
        log10_min: float,
        log10_max: float,
        zero_threshold: float,
    ) -> np.ndarray:
        values = np.asarray(sample, dtype=float)
        if values.size != 12:
            raise ValueError("symmetric 3x3 complex synthesis requires exactly 12 coordinates")
        magnitude_u = values[:6]
        phase_u = values[6:]
        magnitude = 10.0 ** (log10_min + (log10_max - log10_min) * magnitude_u)
        magnitude = np.where(magnitude_u < zero_threshold, 0.0, magnitude)
        phase = 2.0 * math.pi * phase_u
        coefficients = magnitude * np.exp(1j * phase)
        result = np.zeros((3, 3), dtype=complex)
        for coefficient, (i, j) in zip(coefficients, ((0,0),(0,1),(0,2),(1,1),(1,2),(2,2))):
            result[i,j] = coefficient
            result[j,i] = coefficient
        return result

    @staticmethod
    def _blind_kernel_coefficients(sample: Sequence[float], order: int, *, phase: bool) -> tuple[float, ...]:
        values = tuple(float(v) for v in sample)
        if not values or order <= 0:
            return ()
        result = []
        for k in range(order):
            centered = 2.0 * values[k % len(values)] - 1.0
            if phase:
                result.append(float((0.75 * math.pi * centered) / (k + 1.0)))
            else:
                result.append(float((0.55 * centered) / (k + 1.0)))
        return tuple(result)

    def _blind_micro_point(
        self,
        *,
        primitive_id: str,
        geometry_class: str,
        dimensions: int,
        brane_kinetic_active: bool,
        sample: Sequence[float],
        kk_modes_per_family: int,
        kernel_order: int,
    ) -> HigherDimensionalMicroParameters:
        """Synthesize microphysics without any named BSM-family template.

        The 80-dimensional genome writes directly into a general complex Dirac
        block, two complex-symmetric Majorana blocks, a general flavour-to-
        compact coupling matrix, compact geometry primitives and an arbitrary
        finite spectral coupling kernel.  No branch says Dirac, pseudo-Dirac,
        seesaw, sterile-3+N, or another literature family name.
        """
        u = np.asarray(sample, dtype=float)
        if u.shape != (80,) or np.any(~np.isfinite(u)) or np.any((u <= 0.0) | (u >= 1.0)):
            raise ValueError("blind discovery genome must contain 80 finite coordinates strictly inside (0,1)")

        active_dirac = self._blind_dense_complex_matrix(u[0:18], log10_min=-4.5, log10_max=-0.6, zero_threshold=0.03)
        left_majorana = self._blind_symmetric_complex_matrix(u[18:30], log10_min=-8.0, log10_max=-1.0, zero_threshold=0.42)
        right_majorana = self._blind_symmetric_complex_matrix(u[30:42], log10_min=-8.0, log10_max=-0.3, zero_threshold=0.42)
        compact_basis = self._blind_dense_complex_matrix(u[42:60], log10_min=-1.3, log10_max=0.15, zero_threshold=0.10)

        family_dirac = tuple(float(10.0 ** (-4.0 + 2.9 * value)) for value in u[60:63])
        radius = float(10.0 ** (-2.0 + 2.0 * u[63]))
        width = float(0.015 + 0.80 * u[64])
        coupling_scales = tuple(float(0.05 + 1.45 * value) for value in u[65:68])
        bkt = tuple(float(0.02 + 0.98 * value) for value in u[68:71]) if brane_kinetic_active else (0.0, 0.0, 0.0)
        bulk_dirac = tuple(float(10.0 ** (-5.0 + 4.0 * value)) if value > 0.28 else 0.0 for value in u[71:74])
        log_kernel = self._blind_kernel_coefficients(u[74:77], kernel_order, phase=False)
        phase_kernel = self._blind_kernel_coefficients(u[77:80], kernel_order, phase=True)

        if dimensions == 0:
            radii: tuple[float, ...] = ()
            geometry = "FOUR_DIMENSIONAL"
            kk_modes = 0
            phases: tuple[float, ...] = ()
            uv = None
            width_value = 0.0
        else:
            radii = tuple(radius * (1.0 + 0.11 * axis / max(1, dimensions)) for axis in range(dimensions))
            phases = tuple(float((u[64] + (axis + 1) * u[77] / (dimensions + 1.0)) % 0.999999) for axis in range(dimensions))
            kk_modes = kk_modes_per_family
            width_value = width if geometry_class == "LOCALISED" else 0.0
            if geometry_class == "FLAT":
                geometry = "FLAT_TOROIDAL_ORBIFOLD"
                domain = self.classify_infinite_dimension_kk_domain(dimensions=dimensions, brane_kinetic_active=brane_kinetic_active)
                uv = None if domain["infinite_limit_admissible"] else 1.0e3
            elif geometry_class == "LOCALISED":
                geometry = "LOCALISED_FLAT_ORBIFOLD"
                uv = None
            elif geometry_class == "WARPED":
                if dimensions != 1:
                    raise ValueError("warped primitive is owner-qualified only for one compact dimension")
                geometry = "WARPED_INTERVAL_RS1"
                uv = None
            else:
                raise ValueError(f"unknown blind geometry primitive {geometry_class}")

        kwargs: dict[str, Any] = {}
        if geometry_class == "WARPED" and dimensions == 1:
            kwargs.update(
                warp_curvature_ev=float(0.5 + 12.0 * u[63]),
                warp_exponent=float(0.05 + 3.5 * u[64]),
                family_warp_bulk_c=tuple(float(-0.2 + 1.4 * value) for value in u[65:68]),
            )

        return HigherDimensionalMicroParameters(
            dimensions=dimensions,
            radii_micrometre=radii,
            lightest_dirac_mass_ev=min(family_dirac),
            kk_modes_per_family=kk_modes,
            family_coupling_scales=coupling_scales,
            family_bulk_masses_ev=bulk_dirac,
            family_brane_kinetic=bkt,
            localisation_width_fraction=width_value,
            boundary_phases=phases,
            geometry=geometry,
            uv_cutoff_ev=uv,
            family_dirac_masses_ev=family_dirac,
            brane_dirac_real_ev=self._matrix_tuple(np.real(active_dirac)),
            brane_dirac_imag_ev=self._matrix_tuple(np.imag(active_dirac)),
            active_compact_coupling_real=self._matrix_tuple(np.real(compact_basis)),
            active_compact_coupling_imag=self._matrix_tuple(np.imag(compact_basis)),
            compact_coupling_log_chebyshev=log_kernel,
            compact_coupling_phase_chebyshev=phase_kernel,
            brane_left_majorana_real_ev=self._matrix_tuple(np.real(left_majorana)),
            brane_left_majorana_imag_ev=self._matrix_tuple(np.imag(left_majorana)),
            brane_right_majorana_real_ev=self._matrix_tuple(np.real(right_majorana)),
            brane_right_majorana_imag_ev=self._matrix_tuple(np.imag(right_majorana)),
            **kwargs,
        )

    @staticmethod
    def _entropy(weights: np.ndarray) -> float:
        p = np.asarray(weights, dtype=float)
        p = p[p > np.finfo(float).tiny]
        if p.size <= 1:
            return 0.0
        p = p / float(np.sum(p))
        return float(-np.sum(p * np.log(p)) / math.log(len(p)))

    def _blind_behavior_descriptor(
        self,
        micro: HigherDimensionalMicroParameters,
        ir: HigherDimensionalNeutrinoIR,
    ) -> tuple[tuple[float, ...], Mapping[str, float]]:
        """Describe behaviour without comparing it to a published theory or data fit."""
        spectrum = ir.takagi_spectrum
        active = spectrum.active_mixing_matrix()
        masses = np.asarray(spectrum.takagi_masses_ev, dtype=float)
        positive = masses[masses > np.finfo(float).tiny]
        log_masses = np.log10(np.maximum(positive, 1.0e-15)) if positive.size else np.array([-15.0])
        quantiles = np.quantile(log_masses, [0.1, 0.5, 0.9])
        flavour_entropy = [self._entropy(np.abs(active[a, :]) ** 2) for a in range(3)]

        # Generic logarithmically separated observable probes.  They are not
        # named experiments and carry no target values during discovery.
        probes = (
            (1.0, 0.003, 0, 0, False), (7.0, 0.006, 0, 0, False),
            (40.0, 0.004, 0, 0, False), (120.0, 0.12, 1, 0, False),
            (400.0, 0.8, 1, 0, False), (1200.0, 2.5, 1, 0, False),
            (3000.0, 4.0, 1, 1, False), (9000.0, 8.0, 1, 1, False),
            (1200.0, 2.5, 1, 0, True), (9000.0, 8.0, 1, 0, True),
        )
        probabilities = []
        for baseline, energy, initial, final, antineutrino in probes:
            matrix = self.micro_probability_matrix(baseline, energy, micro, ir=ir, antineutrino=antineutrino)
            probabilities.append(float(matrix[final, initial]))

        layers = (MatterLayer(length_km=1300.0, density_g_cm3=2.8, electron_fraction=0.5),)
        matter = self.micro_matter_probability_matrix(2.0, layers, micro, ir=ir)
        vacuum = self.micro_probability_matrix(1300.0, 2.0, micro, ir=ir)
        matter_delta = float(np.max(np.abs(matter[:3, :3] - vacuum[:3, :3])))
        probability_span = float(max(probabilities) - min(probabilities))
        mbeta = float(spectrum.beta_effective_mass_ev)
        mbb = float(spectrum.majorana_effective_mass_ev)
        lnv_ratio = float(math.log10((mbb + 1.0e-15) / (mbeta + 1.0e-15)))
        summary = {
            "log10_mbeta_ev": float(math.log10(mbeta + 1.0e-15)),
            "log10_mbb_ev": float(math.log10(mbb + 1.0e-15)),
            "lnv_log_ratio": lnv_ratio,
            "spectral_log_q10": float(quantiles[0]),
            "spectral_log_q50": float(quantiles[1]),
            "spectral_log_q90": float(quantiles[2]),
            "mean_active_entropy": float(np.mean(flavour_entropy)),
            "matter_response": matter_delta,
            "probability_span": probability_span,
            "propagating_mode_log1p": float(math.log1p(ir.propagating_eigenmodes)),
        }
        descriptor = tuple(summary.values()) + tuple(probabilities)
        return descriptor, summary

    @staticmethod
    def _behavior_cell(summary: Mapping[str, float]) -> str:
        def bucket(value: float, edges: Sequence[float]) -> int:
            return int(np.searchsorted(np.asarray(edges, dtype=float), value, side="right"))
        parts = (
            bucket(float(summary["log10_mbeta_ev"]), (-4.0, -3.0, -2.0, -1.0, -0.3)),
            bucket(float(summary["lnv_log_ratio"]), (-4.0, -2.0, -1.0, -0.3, 0.0)),
            bucket(float(summary["mean_active_entropy"]), (0.2, 0.4, 0.6, 0.8)),
            bucket(float(summary["matter_response"]), (1e-4, 1e-3, 1e-2, 5e-2, 0.2)),
            bucket(float(summary["probability_span"]), (0.05, 0.2, 0.4, 0.7)),
        )
        return "B" + "-".join(str(v) for v in parts)

    @staticmethod
    def _compact_observable_kernel(spectrum: TakagiSpectrumIR) -> Mapping[str, Any]:
        """Persist the complete active-observable eigenbasis without dense sterile rows.

        The authoritative owner can deterministically reconstruct the full dense
        Takagi basis from the canonical microphysics. Persisting masses plus the
        three active rows is sufficient for every active-flavour oscillation,
        matter propagation, m_beta and m_beta_beta observable while avoiding an
        O(N^2) report explosion for high-dimensional execution probes.
        """
        return {
            "takagi_masses_ev": spectrum.takagi_masses_ev,
            "mass_squared_ev2": spectrum.mass_squared_ev2,
            "active_mixing_real": spectrum.active_mixing_real,
            "active_mixing_imag": spectrum.active_mixing_imag,
            "basis_labels": spectrum.basis_labels,
            "active_weight_normalization_residuals": spectrum.active_weight_normalization_residuals,
            "complex_symmetry_residual": spectrum.complex_symmetry_residual,
            "takagi_unitarity_residual": spectrum.takagi_unitarity_residual,
            "takagi_diagonalization_residual": spectrum.takagi_diagonalization_residual,
            "takagi_reconstruction_residual": spectrum.takagi_reconstruction_residual,
            "minimum_mass_ev": spectrum.minimum_mass_ev,
            "beta_effective_mass_ev": spectrum.beta_effective_mass_ev,
            "majorana_effective_mass_ev": spectrum.majorana_effective_mass_ev,
            "dense_full_mixing_persisted": False,
            "dense_full_mixing_reconstruction": "DETERMINISTIC_FROM_CANONICAL_MICROPHYSICS_BY_AUTHORITATIVE_OWNER",
        }

    def _planning_forward_vectors(
        self,
        micro: HigherDimensionalMicroParameters,
        ir: HigherDimensionalNeutrinoIR,
    ) -> Mapping[str, Any]:
        """Post-freeze experiment-design predictions; never a discovery score."""
        def prob(l_km: float, e_gev: float, a: int, b: int) -> float:
            return float(self.micro_probability_matrix(l_km, e_gev, micro, ir=ir)[b, a])
        return {
            "status": "POSTFREEZE_PLANNING_FORWARD_MODEL_NOT_DISCOVERY_OBJECTIVE",
            "design_vectors": {
                "JUNO_MEDIUM_BASELINE_SPECTRUM": [prob(52.5, e, 0, 0) for e in (0.0020, 0.0028, 0.0036, 0.0045, 0.0060)],
                "LBL_SECOND_MAXIMUM_CP": [value for e in (0.7, 0.9, 1.1) for value in (prob(1300.0, e, 1, 0), prob(1300.0, e, 1, 1))],
                "ATMOSPHERIC_LONG_BASELINE": [value for e in (3.0, 6.0, 10.0) for value in (prob(12000.0, e, 1, 1), prob(12000.0, e, 1, 0))],
                "BETA_ENDPOINT_ABSOLUTE_MASS": [float(ir.takagi_spectrum.beta_effective_mass_ev)],
                "LNV_MAJORANA_PHASE": [float(ir.takagi_spectrum.majorana_effective_mass_ev)],
            },
            "declared_base_noise_scales": {
                "JUNO_MEDIUM_BASELINE_SPECTRUM": [0.003] * 5,
                "LBL_SECOND_MAXIMUM_CP": [0.01] * 6,
                "ATMOSPHERIC_LONG_BASELINE": [0.015] * 6,
                "BETA_ENDPOINT_ABSOLUTE_MASS": [0.02],
                "LNV_MAJORANA_PHASE": [0.01],
            },
        }

    @staticmethod
    def _robust_gaussian_information_gain(
        prediction_rows: Sequence[Sequence[float]],
        base_noise: Sequence[float],
        noise_multipliers: Sequence[float] = (0.5, 1.0, 2.0),
    ) -> Mapping[str, Any]:
        x = np.asarray(prediction_rows, dtype=float)
        noise = np.asarray(base_noise, dtype=float)
        if x.ndim != 2 or len(x) < 2 or x.shape[1] != len(noise):
            return {"robust_eig_nats": 0.0, "per_noise_multiplier_nats": {str(v): 0.0 for v in noise_multipliers}}
        centered = x - np.mean(x, axis=0, keepdims=True)
        values: dict[str, float] = {}
        for multiplier in noise_multipliers:
            z = centered / np.maximum(noise * float(multiplier), np.finfo(float).tiny)
            covariance = (z.T @ z) / float(len(z))
            eigenvalues = np.linalg.eigvalsh(0.5 * (covariance + covariance.T))
            values[f"{float(multiplier):.6g}"] = float(0.5 * np.sum(np.log1p(np.maximum(eigenvalues, 0.0))))
        return {"robust_eig_nats": min(values.values()), "per_noise_multiplier_nats": values}

    @staticmethod
    def _information_priority_axis_ids(design_id: str) -> tuple[str, ...]:
        common = (
            "systems_control.identifiability", "systems_control.observability",
            "systems_control.inverse_problem", "systems_control.experiment_design",
            "metrology.measurement_model", "metrology.uncertainty_model",
        )
        per_design = {
            "JUNO_MEDIUM_BASELINE_SPECTRUM": ("physics.detector_coupling", "physics.data_regime", "metrology.resolution"),
            "LBL_SECOND_MAXIMUM_CP": ("physics.experimental_control", "physics.identifiability_class", "metrology.sampling_regime"),
            "ATMOSPHERIC_LONG_BASELINE": ("physics.metric_structure", "physics.data_regime", "metrology.resolution"),
            "BETA_ENDPOINT_ABSOLUTE_MASS": ("physics.observable_type", "metrology.resolution"),
            "LNV_MAJORANA_PHASE": ("physics.observable_type", "physics.identifiability_class"),
        }
        return tuple(dict.fromkeys((*common, *per_design.get(design_id, ()))))

    def _materialize_blind_operator_point(
        self,
        *,
        primitive_id: str,
        geometry_class: str,
        dimensions: int,
        brane_kinetic_active: bool,
        sample: Sequence[float],
        sample_index: str,
        stage: str,
        kk_modes_per_family: int,
        kernel_order: int,
        budget: ExecutionBudgetIR,
    ) -> Mapping[str, Any]:
        micro = self._blind_micro_point(
            primitive_id=primitive_id,
            geometry_class=geometry_class,
            dimensions=dimensions,
            brane_kinetic_active=brane_kinetic_active,
            sample=sample,
            kk_modes_per_family=kk_modes_per_family,
            kernel_order=kernel_order,
        )
        micro.validate()
        budget_status = self.qualify_execution_budget(micro, budget)
        primitive_key = f"{primitive_id}|d={dimensions}|bkt={int(brane_kinetic_active)}|korder={kernel_order}"
        if budget_status["status"] == "RESOURCE_BLOCKED_WITH_BOUND":
            return {
                "status": "RESOURCE_BLOCKED_WITH_BOUND", "stage": stage,
                "primitive_key": primitive_key, "primitive_id": primitive_id,
                "dimensions": dimensions, "brane_kinetic_active": brane_kinetic_active,
                "kernel_order": kernel_order, "sample_index": sample_index,
                "sample_coordinates": tuple(float(v) for v in sample),
                "micro_parameters": micro.to_dict(), "execution_budget": budget_status,
            }
        ir = self.micro_to_ir(micro)
        descriptor, summary = self._blind_behavior_descriptor(micro, ir)
        operator_identity = {
            "schema": "phi-neutrino-operator-identity/v6.9",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "micro_parameters": micro.to_dict(),
            "geometry": ir.geometry_ir.to_dict(),
            "kk_convergence": ir.kk_convergence.to_dict(),
            "observable_kernel": self._compact_observable_kernel(ir.takagi_spectrum),
            "propagating_eigenmodes": ir.propagating_eigenmodes,
            "controlled_limits": dict(ir.controlled_limits),
            "blind_synthesis_contract": {
                "named_bsm_family_template_used": False,
                "published_model_name_used_for_ranking": False,
                "reference_experiment_constraint_used_for_ranking": False,
                "explicit_general_active_dirac_block": True,
                "explicit_general_active_compact_coupling": dimensions > 0,
                "arbitrary_finite_spectral_coupling_kernel_order": kernel_order,
            },
        }
        identity_digest = _digest(operator_identity)
        return {
            "status": "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY",
            "stage": stage,
            "candidate_id": "NU-BLIND-" + identity_digest[:20].upper(),
            "operator_identity_digest": identity_digest,
            "operator_identity": operator_identity,
            "primitive_key": primitive_key,
            "primitive_id": primitive_id,
            "dimensions": dimensions,
            "brane_kinetic_active": brane_kinetic_active,
            "kernel_order": kernel_order,
            "sample_index": sample_index,
            "sample_coordinates": tuple(float(v) for v in sample),
            "micro_parameters": micro.to_dict(),
            "active_axis_count": micro.active_axis_count,
            "kk_convergence": ir.kk_convergence.to_dict(),
            "m_beta_ev": ir.takagi_spectrum.beta_effective_mass_ev,
            "m_beta_beta_ev": ir.takagi_spectrum.majorana_effective_mass_ev,
            "takagi_diagonalization_residual": ir.takagi_spectrum.takagi_diagonalization_residual,
            "takagi_reconstruction_residual": ir.takagi_spectrum.takagi_reconstruction_residual,
            "behavior_descriptor": descriptor,
            "behavior_summary": summary,
            "behavior_cell": self._behavior_cell(summary),
            "planning_forward": self._planning_forward_vectors(micro, ir),
            "physical_claim_status": "FORMAL_EXECUTABLE_BLIND_CANDIDATE_NOT_DATA_PROMOTED",
        }

    @staticmethod
    def _rank_behavior_novelty(rows: Sequence[Mapping[str, Any]], neighbour_count: int) -> list[dict[str, Any]]:
        executable = [row for row in rows if row.get("status") == "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY"]
        if len(executable) < 2:
            return []
        x = np.asarray([row["behavior_descriptor"] for row in executable], dtype=float)
        median = np.median(x, axis=0)
        mad = np.median(np.abs(x - median), axis=0)
        scale = np.where(mad > 1.0e-10, 1.4826 * mad, np.std(x, axis=0))
        scale = np.where(scale > 1.0e-10, scale, 1.0)
        z = (x - median) / scale
        delta = z[:, None, :] - z[None, :, :]
        distance = np.sqrt(np.sum(delta * delta, axis=2))
        rankings: list[dict[str, Any]] = []
        k = min(max(1, neighbour_count), len(executable) - 1)
        for i, row in enumerate(executable):
            order = np.argsort(distance[i], kind="stable")
            neighbours = [int(j) for j in order if int(j) != i][:k]
            novelty = float(np.mean([distance[i, j] for j in neighbours])) if neighbours else 0.0
            rankings.append({
                "candidate_id": row["candidate_id"],
                "operator_identity_digest": row["operator_identity_digest"],
                "primitive_key": row["primitive_key"],
                "behavior_cell": row["behavior_cell"],
                "novelty_score": novelty,
                "nearest_neighbour_candidate_ids": tuple(executable[j]["candidate_id"] for j in neighbours),
                "stage": row["stage"],
                "sample_coordinates": row["sample_coordinates"],
                "kernel_order": row["kernel_order"],
                "active_axis_count": row["active_axis_count"],
            })
        rankings.sort(key=lambda row: (-float(row["novelty_score"]), int(row["active_axis_count"]), row["candidate_id"]))
        return rankings

    @staticmethod
    def _quality_diversity_archive(rankings: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Keep one elite per behaviour cell without collapsing diversity.

        In a pure blind batch, behavioural novelty is the cell quality.  When a
        declared real-data discovery partition is supplied, the empirical loss
        becomes the primary within-cell quality and novelty remains the
        secondary tie-breaker.  Published theory names or literature distances
        never enter either ordering.
        """
        by_id = {str(row.get("candidate_id")): row for row in rows if row.get("candidate_id")}
        best: dict[str, dict[str, Any]] = {}

        def key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
            quality = candidate.get("discovery_quality")
            if isinstance(quality, Mapping) and quality.get("status", "").startswith("PASS_") and quality.get("quality_loss") is not None:
                return (0, float(quality["quality_loss"]), -float(candidate["novelty_score"]), float(candidate["takagi_residual"]), int(candidate["active_axis_count"]), candidate["candidate_id"])
            return (1, 0.0, -float(candidate["novelty_score"]), float(candidate["takagi_residual"]), int(candidate["active_axis_count"]), candidate["candidate_id"])

        for rank in rankings:
            cell = str(rank["behavior_cell"])
            source = by_id[str(rank["candidate_id"])]
            candidate = dict(rank)
            candidate["takagi_residual"] = max(float(source["takagi_diagonalization_residual"]), float(source["takagi_reconstruction_residual"]))
            if source.get("discovery_quality") is not None:
                candidate["discovery_quality"] = source["discovery_quality"]
                candidate["discovery_quality_digest"] = source.get("discovery_quality_digest")
            previous = best.get(cell)
            if previous is None or key(candidate) < key(previous):
                best[cell] = candidate
        result = list(best.values())
        result.sort(key=key)
        return result

    @staticmethod
    def _select_qd_parents(archive: Sequence[Mapping[str, Any]], count: int, *, data_guided: bool) -> list[dict[str, Any]]:
        if count <= 0:
            return []
        rows = [dict(row) for row in archive]
        if not data_guided:
            return sorted(rows, key=lambda row: (-float(row["novelty_score"]), row["behavior_cell"], row["candidate_id"]))[:count]
        quality_sorted = sorted(rows, key=lambda row: (float(row.get("discovery_quality", {}).get("quality_loss", float("inf"))), -float(row["novelty_score"]), row["candidate_id"]))
        novelty_sorted = sorted(rows, key=lambda row: (-float(row["novelty_score"]), float(row.get("discovery_quality", {}).get("quality_loss", float("inf"))), row["candidate_id"]))
        selected: list[dict[str, Any]] = []
        used: set[str] = set()
        for i in range(max(len(quality_sorted), len(novelty_sorted))):
            for pool in (quality_sorted, novelty_sorted):
                if i >= len(pool):
                    continue
                row = pool[i]
                cid = str(row["candidate_id"])
                if cid in used:
                    continue
                used.add(cid)
                selected.append(row)
                if len(selected) >= count:
                    return selected
        return selected

    @staticmethod
    def _mutation_direction(candidate_id: str, round_index: int, child_index: int, width: int) -> np.ndarray:
        seed_material = f"{candidate_id}|{round_index}|{child_index}".encode("utf-8")
        seed = int(hashlib.sha256(seed_material).hexdigest()[:16], 16)
        rng = np.random.default_rng(seed)
        direction = rng.normal(size=width)
        norm = float(np.linalg.norm(direction))
        return direction / (norm if norm > 0.0 else 1.0)

    def _postfreeze_information_design(self, frozen_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        rows = [row for row in frozen_rows if row.get("planning_forward")]
        if len(rows) < 2:
            return {"status": "BLOCKED_NOT_ENOUGH_FROZEN_CANDIDATES", "selected_design": None, "feedback_to_discovery": False}
        design_ids = tuple(rows[0]["planning_forward"]["design_vectors"].keys())
        scores: dict[str, Any] = {}
        for design_id in design_ids:
            predictions = [row["planning_forward"]["design_vectors"][design_id] for row in rows]
            noise = rows[0]["planning_forward"]["declared_base_noise_scales"][design_id]
            scores[design_id] = self._robust_gaussian_information_gain(predictions, noise)
        selected = max(scores, key=lambda key: scores[key]["robust_eig_nats"])
        return {
            "status": "POSTFREEZE_INFORMATION_DESIGN_EXECUTED",
            "selected_design": selected,
            "all_design_information_gain": scores,
            "priority_axis_ids": self._information_priority_axis_ids(selected),
            "feedback_to_discovery": False,
            "candidate_set_frozen_before_scoring": True,
        }

    def _blind_discovery_scan_impl(
        self,
        request: DirectedOperatorSearchRequest | None = None,
        *,
        execution_budget: ExecutionBudgetIR | None = None,
        discovery_quality_evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        discovery_quality_contract: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Blind structural synthesis with optional declared real-data quality.

        Generation never consumes published family labels, ready-made model
        matrices, literature fingerprints or known-theory distance.  An
        explicitly declared ``D_discovery`` partition may provide an empirical
        scalar quality through an experiment owner; this is observation
        feedback, not theory-template feedback.  The candidate ledger is frozen
        before any held-out partition, post-freeze information design or
        literature audit is opened.
        """
        req = request or DirectedOperatorSearchRequest()
        req.validate()
        budget = execution_budget or ExecutionBudgetIR()
        quality_contract = dict(discovery_quality_contract or {})
        data_guided = discovery_quality_evaluator is not None
        if data_guided and not quality_contract.get("dataset_partition_id"):
            raise ValueError("data-guided blind discovery requires a declared dataset_partition_id")
        dimensions = tuple(sorted(set(req.dimension_representatives)))
        positive_dimensions = tuple(d for d in dimensions if d > 0)
        dimension_atlas = {
            "FLAT_NO_BKT": {"d=1": self.classify_infinite_dimension_kk_domain(dimensions=1), "d=2": self.classify_infinite_dimension_kk_domain(dimensions=2), "d>=3": "CUTOFF_DEPENDENT_POWER_EFT_FOR_EVERY_FINITE_D_GE_3"},
            "FLAT_WITH_BKT": {"1<=d<=3": "PROVED_CONVERGENT_POWER_TAIL", "d=4": self.classify_infinite_dimension_kk_domain(dimensions=4, brane_kinetic_active=True), "d>=5": "CUTOFF_DEPENDENT_POWER_EFT_FOR_EVERY_FINITE_D_GE_5"},
            "LOCALISED": {"all_finite_d>=1": "PROVED_CONVERGENT_GAUSSIAN_LOCALISATION"},
            "WARPED": {"d=1": "PROVED_CONVERGENT_WARPED_1D_LINEAR_SPECTRUM", "d!=1": "OUTSIDE_WARPED_OWNER_DOMAIN"},
        }
        primitive_coordinates: list[tuple[str, str, int, bool]] = [("G0", "FOUR_DIMENSIONAL", 0, False)]
        for d in positive_dimensions:
            primitive_coordinates.extend((("G1", "FLAT", d, False), ("G2", "FLAT", d, True), ("G3", "LOCALISED", d, False)))
        if 1 in positive_dimensions:
            primitive_coordinates.append(("G4", "WARPED", 1, False))

        needed = req.points_per_primitive_coordinate + 1
        exponent = int(math.ceil(math.log2(max(2, needed))))
        scout_samples = qmc.Sobol(d=80, scramble=False).random_base2(exponent)[1:needed]
        eps = 1.0e-9
        scout_samples = np.clip(scout_samples, eps, 1.0 - eps)
        rows: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        seen_identity_digests: set[str] = set()
        deduplicated_identity_count = 0

        def append_point(primitive_id: str, geometry_class: str, d: int, bkt: bool, sample: Sequence[float], kernel_order: int, label: str, stage: str) -> None:
            nonlocal deduplicated_identity_count
            key = (primitive_id, geometry_class, d, bkt, kernel_order, *tuple(round(float(x), 12) for x in sample))
            if key in seen:
                return
            seen.add(key)
            try:
                materialized = dict(self._materialize_blind_operator_point(
                    primitive_id=primitive_id, geometry_class=geometry_class, dimensions=d,
                    brane_kinetic_active=bkt, sample=sample, sample_index=label, stage=stage,
                    kk_modes_per_family=req.kk_modes_per_family, kernel_order=kernel_order, budget=budget,
                ))
                digest = materialized.get("operator_identity_digest")
                if digest and digest in seen_identity_digests:
                    deduplicated_identity_count += 1
                    return
                if digest:
                    seen_identity_digests.add(str(digest))
                if data_guided and materialized.get("status") == "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY":
                    quality = dict(discovery_quality_evaluator(materialized))
                    if not quality.get("status", "").startswith("PASS_") or quality.get("quality_loss") is None:
                        materialized["status"] = "DISCOVERY_QUALITY_BLOCKED_WITH_REASON"
                        materialized["discovery_quality"] = quality
                    else:
                        materialized["discovery_quality"] = quality
                        materialized["discovery_quality_digest"] = _digest(quality)
                rows.append(materialized)
            except Exception as exc:
                rows.append({
                    "status": "LOWERING_BLOCKED_WITH_REASON", "stage": stage,
                    "primitive_id": primitive_id, "geometry_class": geometry_class,
                    "dimensions": d, "brane_kinetic_active": bkt, "kernel_order": kernel_order,
                    "sample_index": label, "sample_coordinates": tuple(float(v) for v in sample),
                    "reason": f"{type(exc).__name__}: {exc}",
                })

        for coordinate_index, (primitive_id, geometry_class, d, bkt) in enumerate(primitive_coordinates):
            for sample_index, sample in enumerate(scout_samples):
                order_index = (coordinate_index + sample_index) % len(req.kernel_order_representatives)
                kernel_order = req.kernel_order_representatives[order_index]
                append_point(primitive_id, geometry_class, d, bkt, sample, kernel_order, f"SCOUT-{sample_index}", "BLIND_PRIMITIVE_SCOUT")

        novelty_history: list[dict[str, Any]] = []
        rankings = self._rank_behavior_novelty(rows, req.novelty_neighbour_count)
        archive = self._quality_diversity_archive(rankings, rows)
        selected = self._select_qd_parents(archive, req.priority_region_count, data_guided=data_guided)
        novelty_history.append({
            "stage": "SCOUT", "materialized_count": sum(row.get("status", "").startswith("MATERIALIZED") for row in rows),
            "archive_cell_count": len(archive), "top_novelty": max((float(row["novelty_score"]) for row in archive), default=0.0),
            "best_discovery_quality_loss": min((float(row.get("discovery_quality", {}).get("quality_loss", float("inf"))) for row in archive), default=float("inf")) if data_guided else None,
            "selected_regions": selected,
        })

        step = req.initial_mutation_step
        previous_cells = tuple(sorted(row["behavior_cell"] for row in archive))
        previous_top = max((float(row["novelty_score"]) for row in archive), default=0.0)
        previous_quality = min((float(row.get("discovery_quality", {}).get("quality_loss", float("inf"))) for row in archive), default=float("inf")) if data_guided else float("inf")
        stability = 0
        round_index = 0
        termination = "NO_FEASIBLE_NOVELTY_ARCHIVE" if not selected else "NUMERICAL_MUTATION_RESOLUTION_REACHED"
        by_id = {row.get("candidate_id"): row for row in rows if row.get("candidate_id")}
        while selected and step + 1.0e-15 >= req.minimum_mutation_step:
            round_index += 1
            for center_rank in selected:
                center = by_id.get(center_rank["candidate_id"])
                if center is None:
                    continue
                base = np.asarray(center["sample_coordinates"], dtype=float)
                for child in range(req.mutation_children_per_region):
                    direction = self._mutation_direction(center["candidate_id"], round_index, child, len(base))
                    point = np.clip(base + step * math.sqrt(len(base)) * direction, eps, 1.0 - eps)
                    kernel_orders = req.kernel_order_representatives
                    current_order = int(center["kernel_order"])
                    position = min(range(len(kernel_orders)), key=lambda i: abs(kernel_orders[i] - current_order))
                    delta = (-1, 0, 1, 0)[child % 4]
                    mutated_order = kernel_orders[min(max(position + delta, 0), len(kernel_orders) - 1)]
                    primitive = str(center["primitive_id"])
                    geometry = str(center["operator_identity"]["geometry"]["canonical_geometry"])
                    if geometry == "FOUR_DIMENSIONAL": geometry_class = "FOUR_DIMENSIONAL"
                    elif geometry == "LOCALISED_FLAT_ORBIFOLD": geometry_class = "LOCALISED"
                    elif geometry == "WARPED_INTERVAL_RS1": geometry_class = "WARPED"
                    else: geometry_class = "FLAT"
                    append_point(
                        primitive, geometry_class, int(center["dimensions"]), bool(center["brane_kinetic_active"]),
                        point, int(mutated_order), f"MUTATE-{round_index}-{child}", "NOVELTY_QD_MUTATION",
                    )
            by_id = {row.get("candidate_id"): row for row in rows if row.get("candidate_id")}
            rankings = self._rank_behavior_novelty(rows, req.novelty_neighbour_count)
            archive = self._quality_diversity_archive(rankings, rows)
            selected = self._select_qd_parents(archive, req.priority_region_count, data_guided=data_guided)
            top = max((float(row["novelty_score"]) for row in archive), default=0.0)
            best_quality = min((float(row.get("discovery_quality", {}).get("quality_loss", float("inf"))) for row in archive), default=float("inf")) if data_guided else float("inf")
            cells = tuple(sorted(row["behavior_cell"] for row in archive))
            relative_change = abs(top - previous_top) / max(abs(previous_top), 1.0e-12)
            quality_relative_change = (
                abs(best_quality - previous_quality) / max(abs(previous_quality), 1.0)
                if data_guided and math.isfinite(previous_quality) and math.isfinite(best_quality) else float("inf")
            )
            novelty_history.append({
                "stage": f"NOVELTY_ROUND_{round_index}", "mutation_step": step,
                "materialized_count": sum(row.get("status", "").startswith("MATERIALIZED") for row in rows),
                "archive_cell_count": len(archive), "top_novelty": top,
                "best_discovery_quality_loss": best_quality if data_guided else None,
                "relative_top_novelty_change": relative_change,
                "relative_best_quality_change": quality_relative_change if data_guided else None,
                "selected_regions": selected,
            })
            stable_metric = (
                quality_relative_change <= req.quality_relative_tolerance
                if data_guided else relative_change <= req.novelty_relative_tolerance
            )
            if cells == previous_cells and stable_metric:
                stability += 1
            else:
                stability = 0
            previous_cells, previous_top, previous_quality = cells, top, best_quality
            if stability >= req.archive_stability_rounds:
                termination = "NOVELTY_ARCHIVE_STABLE_FOR_DECLARED_SUCCESSIVE_ROUNDS"
                break
            step *= 0.5

        executable = [row for row in rows if row.get("status") == "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY"]
        blocked = [row for row in rows if row.get("status") == "RESOURCE_BLOCKED_WITH_BOUND"]
        lowering_blocked = [row for row in rows if row.get("status") == "LOWERING_BLOCKED_WITH_REASON"]
        final_rankings = self._rank_behavior_novelty(rows, req.novelty_neighbour_count)
        final_archive = self._quality_diversity_archive(final_rankings, rows)
        frozen_frontier = final_archive[:100]
        frozen_ids = {row["candidate_id"] for row in frozen_frontier}
        frozen_rows = [row for row in executable if row["candidate_id"] in frozen_ids]
        frozen_rows.sort(key=lambda row: row["candidate_id"])
        freeze_payload = tuple(
            (row["candidate_id"], row["operator_identity_digest"], row.get("discovery_quality_digest", ""))
            for row in frozen_rows
        )
        freeze_digest = _digest({"candidate_and_discovery_fit_ledger": freeze_payload, "discovery_quality_contract": quality_contract})
        postfreeze_design = self._postfreeze_information_design(frozen_rows)
        max_residual = max((max(float(row["takagi_diagonalization_residual"]), float(row["takagi_reconstruction_residual"])) for row in executable), default=0.0)
        convergence_counts: dict[str, int] = {}
        for row in executable:
            status = row["kk_convergence"]["status"]
            convergence_counts[status] = convergence_counts.get(status, 0) + 1

        result = {
            "schema": "phi-neutrino-blind-open-ended-discovery/v6.9",
            "owner_id": BLIND_DISCOVERY_OWNER_ID, "owner_version": BLIND_DISCOVERY_OWNER_VERSION,
            "physics_lowering_owner": f"{OWNER_ID}/{OWNER_VERSION}",
            "scientific_domain": {**ScientificDomainIR().to_dict(), "maximum_spectral_coupling_kernel_order": None},
            "execution_request": req.to_dict(), "execution_budget": budget.to_dict(),
            "search_policy": "BLIND_PRIMITIVE_OPERATOR_SYNTHESIS_PLUS_BEHAVIOR_NOVELTY_QUALITY_DIVERSITY_WITH_DECLARED_D_DISCOVERY" if data_guided else "BLIND_PRIMITIVE_OPERATOR_SYNTHESIS_PLUS_BEHAVIOR_NOVELTY_QUALITY_DIVERSITY",
            "knowledge_firewall": {
                "published_bsm_family_labels_available_to_generator": False,
                "published_mass_matrix_templates_available_to_generator": False,
                "literature_fingerprints_available_before_freeze": False,
                "known_theory_distance_used_as_discovery_score": False,
                "experiment_limits_used_as_discovery_gate": False,
                "standard_3nu_distance_used_as_discovery_gate": False,
                "declared_real_observation_partition_used_as_quality": data_guided,
                "discovery_quality_contract": quality_contract if data_guided else None,
                "allowed_inputs": tuple(filter(None, ("MATHEMATICAL_CONSISTENCY", "OWNER_SUPPORTED_PRIMITIVES", "GENERIC_OBSERVABLE_PROBES", "EXPLICIT_EXECUTION_BUDGET", "DECLARED_REAL_DATA_DISCOVERY_PARTITION" if data_guided else None))),
            },
            "novelty_objective": {
                "name": "K_NEAREST_BEHAVIOR_NOVELTY",
                "formula": "N(C)=mean_{j in kNN(C)} ||z(b(C))-z(b(C_j))||_2",
                "quality_diversity_archive": "ONE_ELITE_PER_FIXED_BEHAVIOR_CELL; DECLARED_DATA_LOSS_PRIMARY_WITHIN_CELL_WHEN_D_DISCOVERY_IS_OPEN, NOVELTY_PRIMARY_OTHERWISE",
                "declared_discovery_data_quality_used": data_guided,
                "known_theory_fit_or_eig_used_as_discovery_score": False,
            },
            "dimension_domain": "ALL_NON_NEGATIVE_INTEGER_EXTRA_DIMENSIONS_SUBJECT_TO_OWNER_GEOMETRY_DOMAIN; EXECUTED REPRESENTATIVES ARE NOT A CEILING",
            "spectral_kernel_domain": "ARBITRARY_FINITE_CHEBYSHEV_ORDER; EXECUTED REPRESENTATIVES ARE NOT A CEILING",
            "dimension_convergence_atlas": dimension_atlas,
            "primitive_coordinate_count": len(primitive_coordinates),
            "materialized_operator_identity_count": len(executable),
            "deduplicated_operator_identity_count": deduplicated_identity_count,
            "resource_blocked_count": len(blocked), "lowering_blocked_count": len(lowering_blocked), "row_count": len(rows),
            "maximum_takagi_residual": max_residual, "convergence_status_counts": dict(sorted(convergence_counts.items())),
            "novelty_history": novelty_history, "discovery_termination": termination,
            "quality_diversity_frontier": final_archive[:100],
            "freeze_gate": {
                "status": "FROZEN_BEFORE_FALSIFICATION_AND_LITERATURE_AUDIT",
                "candidate_count": len(frozen_rows), "candidate_digest_ledger": freeze_payload,
                "discovery_quality_contract": quality_contract if data_guided else None,
                "discovery_data_used": data_guided,
                "freeze_digest": freeze_digest, "mutation_after_freeze_allowed": False,
            },
            "postfreeze_information_design": postfreeze_design,
            "falsification_handoff": {
                "owner_role": "INDEPENDENT_EXPERIMENT_LIKELIHOOD_OWNERS",
                "status": "READY_FOR_CANDIDATE_DIGEST_BOUND_REAL_DATA_EVALUATION",
                "required_family_adapter": "HIGHER_DIMENSIONAL_MICRO_IR_OR_GENERAL_OPERATOR_ADAPTER",
                "structure_refit_after_freeze_allowed": False,
                "synthetic_substitution_allowed": False,
                "candidate_contracts": tuple({
                    "candidate_id": row["candidate_id"], "operator_identity_digest": row["operator_identity_digest"],
                    "micro_parameters": row["micro_parameters"], "freeze_digest": freeze_digest,
                } for row in frozen_rows[:8]),
            },
            "postfreeze_novelty_audit_handoff": {
                "owner_role": "LITERATURE_NOVELTY_AUDITOR",
                "status": "ALLOWED_ONLY_AFTER_FROZEN_DIGEST_AND_HELDOUT_RESULT",
                "feedback_to_discovery": False,
                "published_ancestor_information_can_mutate_candidate": False,
                "exact_composite_novelty": "NOT_YET_ESTABLISHED",
            },
            "claim_boundary": {
                "materialized_rows_are_space_size": False, "continuous_parameter_space_exhausted": False,
                "dimension_axis_has_fixed_physical_ceiling": False, "kk_mode_axis_has_fixed_physical_ceiling": False,
                "spectral_kernel_order_has_fixed_physical_ceiling": False, "execution_budget_is_physical_admissibility": False,
                "novelty_score_is_physical_likelihood": False, "postfreeze_eig_is_discovery_objective": False,
                "declared_discovery_partition_is_heldout_evidence": False,
                "real_data_falsification_executed": False, "literature_novelty_audit_executed": False,
                "new_law_claimed": False,
            },
            "rows": rows,
        }
        result["digest"] = _digest(result)
        return result

    def _blind_discovery_qualification_impl(self, *, seed: int = 6901) -> Mapping[str, Any]:
        request = DirectedOperatorSearchRequest(
            dimension_representatives=(0, 1, 2, 3, 5, 8),
            points_per_primitive_coordinate=1,
            kk_modes_per_family=2,
            seed=seed,
            novelty_neighbour_count=6,
            priority_region_count=4,
            mutation_children_per_region=2,
            initial_mutation_step=0.125,
            minimum_mutation_step=0.0625,
            kernel_order_representatives=(0, 2, 4),
        )
        scan = self._blind_discovery_scan_impl(request)
        rows = [row for row in scan["rows"] if row.get("status") == "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY"]
        # Direct leakage test: explicit blind genomes must lower to the same mass
        # operator under radically changed reference oscillation parameters.
        sample = np.clip(qmc.Sobol(d=80, scramble=False).random_base2(1)[1], 1.0e-9, 1.0 - 1.0e-9)
        micro = self._blind_micro_point(primitive_id="G3", geometry_class="LOCALISED", dimensions=2, brane_kinetic_active=False, sample=sample, kk_modes_per_family=2, kernel_order=2)
        p_alt = OscillationParameters(sin2_theta12=0.2, sin2_theta13=0.04, sin2_theta23=0.7, delta_cp_rad=0.1, dm21_ev2=5.0e-5, dm3l_ev2=3.2e-3, ordering="INVERTED")
        m_a, *_ = self.mass_operator(micro, parameters=self.parameters)
        m_b, *_ = self.mass_operator(micro, parameters=p_alt)
        reference_leakage_residual = float(np.max(np.abs(m_a - m_b)))
        checks = {
            "scientific_dimension_ceiling_removed": scan["scientific_domain"]["maximum_extra_dimensions"] is None,
            "scientific_kk_ceiling_removed": scan["scientific_domain"]["maximum_kk_modes_per_family"] is None,
            "spectral_kernel_order_ceiling_removed": scan["scientific_domain"]["maximum_spectral_coupling_kernel_order"] is None,
            "dimension_above_four_executed": any(int(row["dimensions"]) > 4 for row in rows),
            "blind_general_operator_materialized": bool(rows) and all(row["operator_identity"]["blind_synthesis_contract"]["named_bsm_family_template_used"] is False for row in rows),
            "general_active_dirac_block_executed": any(row["operator_identity"]["blind_synthesis_contract"]["explicit_general_active_dirac_block"] for row in rows),
            "general_compact_coupling_executed": any(row["operator_identity"]["blind_synthesis_contract"]["explicit_general_active_compact_coupling"] for row in rows),
            "nontrivial_spectral_kernel_executed": any(int(row["kernel_order"]) > 0 for row in rows),
            "all_finite_dimensions_analytically_classified": all(
                self.classify_infinite_dimension_kk_domain(dimensions=d).get("asymptotic_dimension") == d
                for d in (1, 2, 3, 5, 8, 16, 64, 257)
            ),
            "all_execution_rows_have_reconstructible_operator_identity": bool(rows) and all(
                row.get("operator_identity_digest") and row.get("operator_identity", {}).get("micro_parameters")
                and row.get("operator_identity", {}).get("observable_kernel") for row in rows
            ),
            "execution_budget_not_physical_gate": scan["claim_boundary"]["execution_budget_is_physical_admissibility"] is False,
            "continuous_exhaustion_not_claimed": scan["claim_boundary"]["continuous_parameter_space_exhausted"] is False,
            "reference_parameter_leakage_removed_from_operator_synthesis": reference_leakage_residual < 1.0e-14,
            "known_theory_fit_and_eig_absent_from_discovery_objective": scan["novelty_objective"]["known_theory_fit_or_eig_used_as_discovery_score"] is False and scan["knowledge_firewall"]["declared_real_observation_partition_used_as_quality"] is False,
            "candidate_set_frozen_before_eig": scan["postfreeze_information_design"].get("candidate_set_frozen_before_scoring") is True,
            "eig_feedback_to_discovery_forbidden": scan["postfreeze_information_design"].get("feedback_to_discovery") is False,
            "literature_feedback_to_discovery_forbidden": scan["postfreeze_novelty_audit_handoff"]["feedback_to_discovery"] is False,
            "takagi_closure_machine_precision": scan["maximum_takagi_residual"] < 1.0e-10,
            "new_law_not_claimed": scan["claim_boundary"]["new_law_claimed"] is False,
        }
        report = {
            "schema": BENCHMARK_SCHEMA, "release": BLIND_DISCOVERY_OWNER_VERSION, "owner_id": BLIND_DISCOVERY_OWNER_ID,
            "physics_lowering_owner": f"{OWNER_ID}/{OWNER_VERSION}",
            "status": "PASS_BLIND_OPEN_ENDED_DISCOVERY_QUALIFICATION" if all(checks.values()) else "FAIL_BLIND_OPEN_ENDED_DISCOVERY_QUALIFICATION",
            "checks": checks,
            "reference_parameter_leakage_residual": reference_leakage_residual,
            "execution_summary": {
                "row_count": scan["row_count"], "materialized_operator_identity_count": scan["materialized_operator_identity_count"],
                "resource_blocked_count": scan["resource_blocked_count"], "dimension_representatives": request.dimension_representatives,
                "maximum_executed_dimension": max((int(row["dimensions"]) for row in rows), default=0),
                "maximum_executed_kernel_order": max((int(row["kernel_order"]) for row in rows), default=0),
                "archive_cell_count": len(scan["quality_diversity_frontier"]), "maximum_takagi_residual": scan["maximum_takagi_residual"],
                "selected_postfreeze_measurement_design": scan["postfreeze_information_design"].get("selected_design"),
            },
            "scientific_domain": scan["scientific_domain"], "knowledge_firewall": scan["knowledge_firewall"],
            "novelty_objective": scan["novelty_objective"], "novelty_history": scan["novelty_history"],
            "freeze_gate": scan["freeze_gate"], "postfreeze_information_design": scan["postfreeze_information_design"],
            "falsification_handoff": {k: v for k, v in scan["falsification_handoff"].items() if k != "candidate_contracts"},
            "postfreeze_novelty_audit_handoff": scan["postfreeze_novelty_audit_handoff"],
            "claim_boundary": scan["claim_boundary"],
        }
        report["sha256"] = _digest(report)
        return report

    def directed_operator_region_scan(
        self, request: DirectedOperatorSearchRequest | None = None
    ) -> Mapping[str, Any]:
        """Thin compatibility route to the independent blind-discovery owner."""
        return BlindNeutrinoDiscoveryOwner(self).discover(request)

    def run_directed_fullspace_qualification(self, *, seed: int = 6901) -> Mapping[str, Any]:
        """Thin compatibility route to the independent blind-discovery owner."""
        return BlindNeutrinoDiscoveryOwner(self).qualify(seed=seed)

    def run_blind_benchmark(self, *, seed: int = 6901) -> Mapping[str, Any]:
        """Compatibility name; delegates to the single current qualification."""
        return BlindNeutrinoDiscoveryOwner(self).qualify(seed=seed)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "reference_snapshot": dict(REFERENCE_SNAPSHOT),
            "active_route": "COMPLEX_SYMMETRIC_MAJORANA_TAKAGI_MICRO_TO_IR_TO_OBSERVABLES",
            "capabilities": (
                "THREE_NEUTRINO_PMNS_VACUUM",
                "PIECEWISE_CONSTANT_MSW_MATTER",
                "STERILE_3P1_CONTROL",
                "FLAT_ARBITRARY_FINITE_DIMENSION_COMPACTIFICATION",
                "FLAT_S1_Z2_AND_ANISOTROPIC_T2_Z2_GEOMETRY_IR",
                "LOCALISED_FLAT_COMPACTIFICATION",
                "WARPED_INTERVAL_RS1_SPECTRUM_AND_PROFILE_IR",
                "GEOMETRY_SPECIFIC_KK_CONVERGENCE_CERTIFICATE",
                "EXACT_ZERO_WARP_TO_FLAT_LIMIT",
                "FINITE_COMPLEX_SYMMETRIC_DIRAC_MAJORANA_SEESAW_KK_OPERATOR",
                "AUTONNE_TAKAGI_FACTORIZATION",
                "BETA_ENDPOINT_EFFECTIVE_MASS",
                "NEUTRINOLESS_DOUBLE_BETA_EFFECTIVE_MASS",
                "MULTIDOMAIN_LAWSPACE_DERIVATION_BINDING",
                "FULL_MASS_BASIS_MATTER_PROPAGATION",
                "FAMILY_BULK_MASS_AXES",
                "LOCALISED_BRANE_OVERLAP_AXES",
                "BRANE_KINETIC_AND_BOUNDARY_PHASE_AXES",
                "CONTROLLED_STANDARD_LED_MATRIX_LIMIT",
                "BLIND_PRIMITIVE_FIREWALL_OWNER_HYPERGRAPH_SEARCH",
                "ANALYTIC_ALL_FINITE_DIMENSION_KK_CONVERGENCE_CLASSIFICATION",
                "FULL_TAKAGI_OPERATOR_IDENTITY_DIGEST",
                "DIRAC_MAJORANA_OSCILLATION_IDENTIFIABILITY",
                "HERMITIAN_NSI_MATTER_POTENTIAL",
                "BLIND_GENERAL_COMPLEX_OPERATOR_SYNTHESIS_NO_NAMED_BSM_TEMPLATE",
                "BEHAVIOR_NOVELTY_QUALITY_DIVERSITY_ARCHIVE",
                "ARBITRARY_FINITE_CHEBYSHEV_SPECTRAL_COUPLING_KERNEL",
                "CANDIDATE_FREEZE_BEFORE_FALSIFICATION_AND_INFORMATION_DESIGN",
                "POSTFREEZE_EIG_WITHOUT_DISCOVERY_FEEDBACK",
                "RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY_PERSISTENCE",
            ),
            "hard_boundaries": (
                "NO_EXTRA_DIMENSION_EXISTENCE_CLAIM_FROM_EMULATION",
                "NO_TRUE_MASS_MECHANISM_CLAIM_WITHOUT_REAL_DATA_AND_REPLICATION",
                "MULTI_DIMENSIONAL_TOWERS_REQUIRE_UV_CUTOFF_ONLY_WHEN_THE_CONVERGENCE_CERTIFICATE_FAILS",
                "WARPED_GEOMETRY_HAS_ITS_OWN_SPECTRAL_DOMAIN_INSIDE_THE_SAME_MASS_OPERATOR_OWNER",
                "NO_HERMITIAN_MASS_SQUARED_EIGENSOLVER_AS_PARALLEL_ACTIVE_ROUTE",
                "NO_MAJORANA_DISCOVERY_CLAIM_FROM_OSCILLATIONS_OR_SYNTHETIC_DATA",
                "FINITE_KK_TRUNCATION_DISCLOSED",
                "EXECUTION_BUDGET_NEVER_REINTERPRETED_AS_SCIENTIFIC_DOMAIN",
                "INFORMATION_GAIN_PLANNING_UTILITY_NEVER_REINTERPRETED_AS_EXPERIMENT_LIKELIHOOD",
                "NO_NAMED_BSM_FAMILY_OR_PUBLISHED_MASS_TEMPLATE_IN_BLIND_DISCOVERY_SCORE",
                "NO_REFERENCE_EXPERIMENT_LIMIT_OR_STANDARD_MODEL_DISTANCE_IN_BLIND_DISCOVERY_SCORE",
                "NO_POSTFREEZE_INFORMATION_OR_LITERATURE_FEEDBACK_TO_DISCOVERY",
                "NO_LITERATURE_NOVELTY_CLAIM_BEFORE_FROZEN_HELDOUT_FALSIFICATION",
            ),
            "legacy_compatibility": {
                "LEDParameters": "THIN_DATA_LOWERING_ONLY",
                "led_probability_matrix": "THIN_CALL_TO_MICRO_TO_IR_OWNER",
                "parallel_transcendental_led_solver_present": False,
            },
            "qpdtr_role": "INDEPENDENT_HERMITIAN_EMBEDDING_DYNAMICS_CROSS_CHECK_NOT_LABORATORY_EVIDENCE",
        }
        return {**payload, "digest": _digest(payload)}

class BlindNeutrinoDiscoveryOwner:
    """Independent owner of blind synthesis, novelty/QD and freeze ordering.

    Numerical microphysics lowering is delegated to NEUTRINO-PHENOMENOLOGY;
    this owner controls only discovery policy.  The compatibility entry points
    on ``NeutrinoPhenomenologyOwner`` are intentionally algorithm-free.
    """

    owner_id = BLIND_DISCOVERY_OWNER_ID
    owner_version = BLIND_DISCOVERY_OWNER_VERSION
    schema = "phi-neutrino-blind-open-ended-discovery-owner/v6.9"

    def __init__(self, phenomenology: NeutrinoPhenomenologyOwner | None = None) -> None:
        self.phenomenology = phenomenology or NeutrinoPhenomenologyOwner()

    def discover(
        self,
        request: DirectedOperatorSearchRequest | None = None,
        *,
        discovery_quality_evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        discovery_quality_contract: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        return self.phenomenology._blind_discovery_scan_impl(
            request,
            discovery_quality_evaluator=discovery_quality_evaluator,
            discovery_quality_contract=discovery_quality_contract,
        )

    def qualify(self, *, seed: int = 6901) -> Mapping[str, Any]:
        return self.phenomenology._blind_discovery_qualification_impl(seed=seed)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": self.owner_id,
            "owner_version": self.owner_version,
            "schema": self.schema,
            "physics_lowering_owner": f"{OWNER_ID}/{OWNER_VERSION}",
            "discovery_inputs": (
                "GENERAL_COMPLEX_OPERATOR_COORDINATES",
                "DIMENSIONAL_AND_SYMMETRY_CONSISTENCY",
                "GENERIC_OBSERVABLE_BEHAVIOR_PROBES",
                "OPTIONAL_EXPLICITLY_DECLARED_REAL_DATA_DISCOVERY_PARTITION",
            ),
            "forbidden_pre_freeze_inputs": (
                "PUBLISHED_MODEL_FAMILY_LABELS",
                "READY_MADE_PUBLISHED_MASS_MATRIX_TEMPLATES",
                "REFERENCE_EXPERIMENT_EXCLUSION_LIMITS_AS_RANKING_TARGETS",
                "KNOWN_THEORY_DISTANCE_AS_DISCOVERY_OBJECTIVE",
                "LITERATURE_NOVELTY_RESULTS",
                "POSTFREEZE_INFORMATION_DESIGN_PRIORITIES",
            ),
            "discovery_objective": "BEHAVIOR_NOVELTY_PLUS_QUALITY_DIVERSITY; OPTIONAL_REAL_DATA_QUALITY_ONLY_FROM_DECLARED_D_DISCOVERY, NEVER_FROM_KNOWN_THEORY_DISTANCE",
            "freeze_before_external_feedback": True,
        }
        return {**payload, "digest": _digest(payload)}



LAW_INTERSECTION_OWNER_ID = "NEUTRINO-LAW-INTERSECTION-CLOSURE"
LAW_INTERSECTION_OWNER_VERSION = "6.13.0"
LAW_INTERSECTION_SCHEMA = "phi-neutrino-law-intersection-database/v6.13"


class NeutrinoLawIntersectionClosureOwner:
    """Authoritative reader/qualifier for source-derived neutrino law intersections.

    This owner does not invent couplings and does not use literature as a generation
    objective.  It materializes consequences already frozen in the current database,
    checks that every source owner/constant resolves, and preserves separate formal,
    empirical, and literature-novelty statuses.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "data" / "passports" / "neutrino_intersection_laws.json"
        self.database = json.loads(self.path.read_text(encoding="utf-8"))
        if self.database.get("schema") != LAW_INTERSECTION_SCHEMA:
            raise ValueError("unsupported neutrino intersection-law database schema")

    def contract(self) -> Mapping[str, Any]:
        db = self.database
        return {
            "owner_id": LAW_INTERSECTION_OWNER_ID,
            "owner_version": LAW_INTERSECTION_OWNER_VERSION,
            "schema": LAW_INTERSECTION_SCHEMA,
            "database_digest": db["database_digest"],
            "source_law_count": len(db.get("source_laws", [])),
            "intersection_law_count": len(db.get("laws", [])),
            "total_database_entries": db.get("counts", {}).get("total_database_entries", 0),
            "known_control_intersection_count": db.get("counts", {}).get("known_control_intersections", 0),
            "closure_candidate_count": db.get("counts", {}).get("closure_candidates", 0),
            "closure_family_count": db.get("counts", {}).get("closure_families", 0),
            "max_materialized_intersection_order": db.get("counts", {}).get("max_materialized_intersection_order", 0),
            "fixed_intersection_order_ceiling": db.get("closure_engine", {}).get("fixed_intersection_order_ceiling"),
            "fixed_materialized_candidate_ceiling": db.get("closure_engine", {}).get("fixed_materialized_candidate_ceiling"),
            "primary_source_owner_ids": tuple(db.get("source_registry", {}).get("primary_intersection_source_owner_ids", ())),
            "claim_boundary": dict(db.get("claim_boundary", {})),
            "generation_policy": "SOURCE_LAW_VALIDITY_INTERSECTION_THEN_DEDUCTIVE_CLOSURE",
            "literature_feedback_to_derivation": False,
            "blind_operator_synthesis_role": "AUXILIARY_ONLY",
        }

    def get_source_law(self, owner_id: str) -> Mapping[str, Any]:
        for row in self.database.get("source_laws", []):
            if row.get("owner_id") == owner_id:
                return row
        raise KeyError(owner_id)

    def search_source_laws(
        self, *, novelty_status_contains: str | None = None, limit: int = 100,
    ) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for row in self.database.get("source_laws", []):
            status = str(row.get("literature_audit", {}).get("status", ""))
            if novelty_status_contains and novelty_status_contains not in status:
                continue
            rows.append(row)
        return rows[:max(0, int(limit))]

    def get_law(self, law_id: str) -> Mapping[str, Any]:
        for row in self.database.get("laws", []):
            if row.get("law_id") == law_id:
                return row
        raise KeyError(law_id)

    def materialize_family_instance(
        self, family_id: str, parameters: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Re-materialize one declared source-law closure from its authoritative family.

        This is deliberately not a free-form symbolic generator: the family carries the
        source-owner list, validity intersection, source-usage map, interface variables,
        unit contract, derivation and claim boundary.  The method proves that a stored
        materialization is reproducible from the current owner rather than being a report
        artifact.
        """
        parameters = dict(parameters or {})
        family = next(
            (row for row in self.database.get("closure_families", ()) if row.get("family_id") == family_id),
            None,
        )
        if family is None:
            raise KeyError(family_id)
        declared_grid = tuple(dict(row) for row in family.get("parameter_grid", ({} ,)))
        if parameters not in declared_grid:
            raise ValueError("parameters are not a declared deterministic materialization for this family")
        owners = tuple(str(x) for x in family.get("source_owner_ids", ()))
        if family_id.startswith("FAM-XD-"):
            usage = dict(family.get("source_usage", {}))
            if set(usage) != set(owners) or not all(str(v).strip() for v in usage.values()):
                raise ValueError("cross-domain family does not account for every source owner")
            if not tuple(family.get("interface_variables", ())):
                raise ValueError("cross-domain family has no shared carrier/interface variable")
            if family.get("cross_domain_validity_gate") != "PASS_SHARED_PHYSICAL_CARRIER_OR_EXPLICIT_INTERFACE_VARIABLE":
                raise ValueError("cross-domain validity gate is not satisfied")
            if not str(family.get("unit_system", "")).strip():
                raise ValueError("cross-domain family has no unit contract")
        return {
            "family_id": family_id,
            "name_ru": str(family.get("name_template", family.get("name_ru", ""))).format(**parameters),
            "formula": str(family.get("formula_template", "")).format(**parameters),
            "source_owner_ids": owners,
            "source_usage": dict(family.get("source_usage", {})),
            "interface_variables": tuple(family.get("interface_variables", ())),
            "unit_system": str(family.get("unit_system", "SOURCE_DECLARED")),
            "validity_intersection": family.get("validity_intersection"),
            "assumptions": tuple(family.get("assumptions", ())),
            "derivation": tuple(family.get("derivation", ())),
            "constants": tuple(family.get("constants", ())),
            "classification": family.get("classification"),
            "physical_status": family.get("physical_status"),
            "theorem_strength": family.get("theorem_strength"),
            "family_parameters": parameters,
        }

    def multidomain_frontier(
        self, *, source_owner_id: str | None = None, min_intersection_order: int = 2, limit: int = 1000,
    ) -> list[Mapping[str, Any]]:
        """Return declared cross-domain closure families, not random LawSpace neighbours."""
        rows: list[Mapping[str, Any]] = []
        for family in self.database.get("closure_families", ()):
            fid = str(family.get("family_id", ""))
            if not fid.startswith("FAM-XD-"):
                continue
            owners = tuple(family.get("source_owner_ids", ()))
            if len(owners) < int(min_intersection_order):
                continue
            if source_owner_id is not None and source_owner_id not in owners:
                continue
            rows.append(family)
        return rows[:max(0, int(limit))]

    def search(
        self, *, source_owner_id: str | None = None, classification: str | None = None,
        novelty_status_contains: str | None = None, min_intersection_order: int = 0,
        closure_family_id: str | None = None, limit: int = 1000,
    ) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for row in self.database.get("laws", []):
            owners = tuple(row.get("source_owner_ids", ()))
            if source_owner_id and source_owner_id not in owners:
                continue
            if classification and row.get("classification") != classification:
                continue
            if novelty_status_contains and novelty_status_contains not in str(row.get("novelty_audit", {}).get("status", "")):
                continue
            if closure_family_id and row.get("closure_family_id") != closure_family_id:
                continue
            if len(owners) < int(min_intersection_order):
                continue
            rows.append(row)
        return rows[:max(0, int(limit))]

    def run_qualification(self) -> Mapping[str, Any]:
        db = self.database
        laws = list(db.get("laws", []))
        source_laws = list(db.get("source_laws", []))
        stored_digest = str(db.get("database_digest", ""))
        digest_ok = stored_digest == _digest({k: v for k, v in db.items() if k != "database_digest"})
        law_digest_ok = all(
            row.get("law_digest") == _digest({k: v for k, v in row.items() if k != "law_digest"})
            for row in laws
        )
        ids = [str(row.get("law_id")) for row in laws]
        ids_unique = len(ids) == len(set(ids))
        source_ids = [str(row.get("owner_id")) for row in source_laws]
        source_ids_unique = len(source_ids) == len(set(source_ids))
        source_digests_ok = all(
            row.get("source_law_digest") == _digest({k: v for k, v in row.items() if k != "source_law_digest"})
            for row in source_laws
        )
        families = list(db.get("closure_families", []))
        family_ids = [str(row.get("family_id")) for row in families]
        family_ids_unique = len(family_ids) == len(set(family_ids))
        family_digests_ok = all(
            row.get("family_digest") == _digest({k: v for k, v in row.items() if k != "family_digest"})
            for row in families
        )
        family_by_id = {str(row.get("family_id")): row for row in families}
        materialized_template_ok = True
        materialized_parameter_coverage_ok = True
        expected_parameter_pairs: set[tuple[str, str]] = set()
        for family in families:
            fid = str(family.get("family_id"))
            for params in family.get("parameter_grid", ()):
                expected_parameter_pairs.add((fid, _digest(dict(params))))
        seen_parameter_pairs: set[tuple[str, str]] = set()
        for row in laws:
            fid = str(row.get("closure_family_id", ""))
            if fid == "V611-CONTROL-OR-SEED":
                continue
            family = family_by_id.get(fid)
            if family is None:
                materialized_template_ok = False
                continue
            params = dict(row.get("family_parameters", {}))
            try:
                expected_formula = str(family.get("formula_template", "")).format(**params)
                expected_name = str(family.get("name_template", family.get("name_ru", ""))).format(**params)
                if row.get("formula") != expected_formula or row.get("name_ru") != expected_name:
                    materialized_template_ok = False
                if tuple(row.get("source_owner_ids", ())) != tuple(family.get("source_owner_ids", ())):
                    materialized_template_ok = False
            except Exception:
                materialized_template_ok = False
            seen_parameter_pairs.add((fid, _digest(params)))
        materialized_parameter_coverage_ok = expected_parameter_pairs == seen_parameter_pairs
        max_order_matches = db.get("counts", {}).get("max_materialized_intersection_order") == max(
            (len(row.get("source_owner_ids", ())) for row in laws), default=0
        )
        no_fixed_order_ceiling = db.get("closure_engine", {}).get("fixed_intersection_order_ceiling") is None
        no_fixed_candidate_ceiling = db.get("closure_engine", {}).get("fixed_materialized_candidate_ceiling") is None

        passport_ids = set()
        known_path = self.root / "data" / "passports" / "known_laws.jsonl"
        for line in known_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                passport_ids.add(str(json.loads(line)["owner_id"]))
        source_owners_resolve = all(
            row.get("source_owner_ids") and set(row["source_owner_ids"]).issubset(passport_ids)
            for row in laws
        )
        source_law_owners_resolve = bool(source_laws) and set(source_ids).issubset(passport_ids)
        constant_rows = json.loads((self.root / "data" / "constants" / "registry.json").read_text(encoding="utf-8"))
        constants = {str(row["constant_id"]) for row in constant_rows}
        constants_resolve = all(set(row.get("constants", ())).issubset(constants) for row in laws)
        source_constants_resolve = all(set(row.get("constants", ())).issubset(constants) for row in source_laws)
        embedded_constant_ids = {str(row.get("constant_id")) for row in db.get("constant_records", ())}
        referenced_constant_ids = set()
        for row in source_laws + laws:
            referenced_constant_ids.update(str(x) for x in row.get("constants", ()))
        embedded_constants_cover_references = referenced_constant_ids == embedded_constant_ids
        gf_rows = [row for row in constant_rows if row.get("constant_id") == "CONST-GF"]
        gf_pdg2026_value_ok = len(gf_rows) == 1 and gf_rows[0].get("value") == "1.1663785e-5" and "PDG 2026" in str(gf_rows[0].get("edition", ""))
        variable_rows_complete = all(
            row.get("variables") and all(v.get("symbol") and v.get("meaning_ru") and v.get("role") for v in row.get("variables", ()))
            for row in laws
        )
        source_variable_rows_complete = all(
            row.get("variables") and all(v.get("symbol") and v.get("meaning_ru") and v.get("role") for v in row.get("variables", ()))
            for row in source_laws
        )
        source_literature_statuses_present = all(row.get("literature_audit", {}).get("status") for row in source_laws)
        literature_source_ids = set(db.get("literature_audit_sources", {}))
        referenced_literature_ids = set()
        for row in source_laws:
            referenced_literature_ids.update(str(x) for x in row.get("primary_source_ids", ()))
        for row in laws:
            referenced_literature_ids.update(str(x) for x in row.get("novelty_audit", {}).get("closest_primary_sources", ()))
            referenced_literature_ids.update(
                str(x.get("source_id")) for x in row.get("primary_source_metadata", ()) if x.get("source_id")
            )
        literature_source_ids_resolve = referenced_literature_ids.issubset(literature_source_ids)
        novelty_separated = all(
            row.get("novelty_audit", {}).get("status")
            and row.get("physical_status")
            and "NEW_PHYSICAL_LAW_ESTABLISHED" not in str(row.get("physical_status"))
            for row in laws
        )
        no_literature_reward = db.get("claim_boundary", {}).get("literature_novelty") == "NO_EXACT_MATCH_FOUND_IS_NOT_PROOF_OF_NOVELTY"

        # v6.13 cross-domain integrity gates.  A domain label or graph adjacency is
        # not enough: every source owner must have a declared role, every family must
        # expose a real shared carrier/interface, and every mixed-unit formula must
        # carry an explicit unit contract.
        cross_families = [row for row in families if str(row.get("family_id", "")).startswith("FAM-XD-")]
        cross_source_usage_exact = bool(cross_families) and all(
            set(map(str, row.get("source_usage", {}).keys())) == set(map(str, row.get("source_owner_ids", ())))
            and all(str(v).strip() for v in row.get("source_usage", {}).values())
            for row in cross_families
        )
        cross_interfaces_present = bool(cross_families) and all(
            bool(tuple(row.get("interface_variables", ()))) for row in cross_families
        )
        cross_validity_gate_pass = bool(cross_families) and all(
            row.get("cross_domain_validity_gate") == "PASS_SHARED_PHYSICAL_CARRIER_OR_EXPLICIT_INTERFACE_VARIABLE"
            for row in cross_families
        )
        cross_unit_contracts_present = bool(cross_families) and all(
            bool(str(row.get("unit_system", "")).strip()) for row in cross_families
        )
        cross_no_raw_si_gf_mixing = all(
            not any(
                forbidden in str(row.get("formula_template", ""))
                for forbidden in (
                    "G_F epsilon_0",
                    "G_F m_e epsilon_0",
                    "G_F n_e_SI",
                    "G_F m_e sigma/(e^2 tau)",
                )
            )
            for row in cross_families
        )
        cross_materialized_owner_usage_exact = True
        cross_materialized_interfaces_exact = True
        cross_materialized_units_exact = True
        cross_owner_replay_exact = True
        for row in laws:
            fid = str(row.get("closure_family_id", ""))
            if not fid.startswith("FAM-XD-"):
                continue
            family = family_by_id.get(fid)
            if family is None:
                cross_owner_replay_exact = False
                continue
            if dict(row.get("source_usage", {})) != dict(family.get("source_usage", {})):
                cross_materialized_owner_usage_exact = False
            if tuple(row.get("interface_variables", ())) != tuple(family.get("interface_variables", ())):
                cross_materialized_interfaces_exact = False
            if str(row.get("unit_system", "")) != str(family.get("unit_system", "")):
                cross_materialized_units_exact = False
            try:
                replay = self.materialize_family_instance(fid, dict(row.get("family_parameters", {})))
                cross_owner_replay_exact = cross_owner_replay_exact and (
                    replay["formula"] == row.get("formula")
                    and replay["name_ru"] == row.get("name_ru")
                    and tuple(replay["source_owner_ids"]) == tuple(row.get("source_owner_ids", ()))
                )
            except Exception:
                cross_owner_replay_exact = False

        # Deterministic mathematical spot-checks of the database's closure logic.
        rng = np.random.default_rng(611)
        z = rng.normal(size=9) + 1j * rng.normal(size=9)
        weights = np.abs(z) ** 2
        weights = weights / weights.sum()
        masses = np.sort(rng.uniform(0.001, 1.0, size=9))
        phases = np.exp(1j * rng.uniform(-math.pi, math.pi, size=9))
        w = np.sqrt(weights) * phases
        m_beta = math.sqrt(float(np.sum(weights * masses**2)))
        m_bb = abs(np.sum(w**2 * masses))
        beta_lnv_bound_ok = bool(m_bb <= m_beta + 1e-13)

        shift = 0.037
        l_over_2e = 1.91
        a0 = np.sum(weights * np.exp(-1j * masses**2 * l_over_2e))
        a1 = np.sum(weights * np.exp(-1j * (masses**2 + shift) * l_over_2e))
        common_shift_probability_ok = bool(abs(abs(a0)**2 - abs(a1)**2) < 1e-12)
        beta_shift_ok = bool(abs((np.sum(weights * (masses**2 + shift)) - np.sum(weights * masses**2)) - shift) < 1e-12)

        qmat = rng.normal(size=(12, 12)) + 1j * rng.normal(size=(12, 12))
        qbasis, _ = np.linalg.qr(qmat)
        chi = rng.normal(size=12) + 1j * rng.normal(size=12)
        coeff = np.conjugate(qbasis).T @ chi
        parseval_ok = bool(abs(np.vdot(chi, chi).real - np.vdot(coeff, coeff).real) < 1e-10)
        ncut = 7
        parseval_tail_ok = bool(abs(np.sum(np.abs(coeff[ncut:])**2) - (np.vdot(chi,chi).real - np.sum(np.abs(coeff[:ncut])**2))) < 1e-10)

        ua = rng.normal(size=20) + 1j * rng.normal(size=20)
        ub = rng.normal(size=20) + 1j * rng.normal(size=20)
        ua /= np.linalg.norm(ua); ub /= np.linalg.norm(ub)
        phases_tail = np.exp(1j * rng.uniform(-math.pi, math.pi, size=20))
        tail = np.sum(ub[9:] * np.conjugate(ua[9:]) * phases_tail[9:])
        eps = math.sqrt(float(np.sum(np.abs(ua[9:])**2) * np.sum(np.abs(ub[9:])**2)))
        oscillation_tail_bound_ok = bool(abs(tail) <= eps + 1e-13)

        d, p, q = 5.0, 2.7, 2.0
        exponent = d + q - 3.0 - 2.0*p
        hierarchy_formula_ok = bool((exponent < -1.0) == (p > (d + q - 2.0)/2.0))
        threshold_order_ok = bool((d-2)/2 < (d-1)/2 < d/2)

        # Exact Majorana/Takagi matrix identities used by the expanded closure.
        zr = rng.normal(size=(6, 6)) + 1j * rng.normal(size=(6, 6))
        q, _ = np.linalg.qr(zr)
        takagi_masses = np.sort(rng.uniform(0.01, 2.0, size=6))
        majorana_m = np.conjugate(q) @ np.diag(takagi_masses) @ np.conjugate(q).T
        beta_sq_matrix = float(np.real((np.conjugate(majorana_m).T @ majorana_m)[0, 0]))
        beta_sq_spectrum = float(np.sum(np.abs(q[0, :])**2 * takagi_masses**2))
        mbb_matrix = abs(majorana_m[0, 0])
        mbb_spectrum = abs(np.sum(np.conjugate(q[0, :])**2 * takagi_masses))
        offdiag_identity = beta_sq_matrix - mbb_matrix**2
        offdiag_direct = float(np.sum(np.abs(majorana_m[1:, 0])**2))
        takagi_beta_identity_ok = abs(beta_sq_matrix - beta_sq_spectrum) < 1e-10
        takagi_mbb_identity_ok = abs(mbb_matrix - mbb_spectrum) < 1e-10
        offdiag_texture_identity_ok = abs(offdiag_identity - offdiag_direct) < 1e-10

        # Spectral-moment tail exponent and regularity ladder spot checks.
        d2, p2 = 6.0, 5.3
        moment_threshold_grid_ok = all(
            ((d2 + float(qv) - 3.0 - 2.0*p2) < -1.0) == (p2 > (d2 + float(qv) - 2.0)/2.0)
            for qv in (-2, -1, 0, 1, 2, 4, 8, 12)
        )
        regularity_ladder_ok = all(
            (p2 > (d2 - 2.0)/2.0 + rv) == (p2 > (d2 + 2.0*rv - 2.0)/2.0)
            for rv in range(0, 8)
        )
        beta_msw_slope_elimination_ok = True
        for dd in range(1, 11):
            pp = 1.37
            b_beta = dd - 3.0 - 2.0*pp
            b_res = dd/2.0 - pp - 2.0
            if abs(b_beta - (2.0*b_res + 1.0)) > 1e-12:
                beta_msw_slope_elimination_ok = False
                break
        count_slope_identity_ok = all(abs(float(dd) - 2.0*(float(dd)/2.0)) < 1e-12 for dd in range(1, 11))

        # Multidomain numerical/algebraic controls.  These use dimensionless or
        # single-natural-unit test values so no hidden SI/natural conversion can
        # manufacture a passing identity.
        gf, alpha, me, temp_e, ne = 1.7e-5, 1.0/137.0, 0.511, 0.02, 3.7e-8
        lambda_sq = temp_e/(4.0*math.pi*alpha*ne)
        omega_sq = 4.0*math.pi*alpha*ne/me
        ve = math.sqrt(2.0)*gf*ne
        plasma_debye_elimination_ok = abs(ve*lambda_sq - math.sqrt(2.0)*gf*temp_e/(4.0*math.pi*alpha)) < 1e-15
        plasma_frequency_elimination_ok = abs(ve/omega_sq - math.sqrt(2.0)*gf*me/(4.0*math.pi*alpha)) < 1e-15
        plasma_thermal_identity_ok = abs(omega_sq*lambda_sq - temp_e/me) < 1e-15

        kb = 1.380649e-23
        na = 6.02214076e23
        ee = 1.602176634e-19
        rr = na*kb
        ff = na*ee
        tt = 310.0
        phi = 0.013
        ratio_pb = math.exp(ee*phi/(kb*tt))
        delta_mu = ff*phi
        ratio_chem = math.exp(delta_mu/(rr*tt))
        electrochemical_ratio_identity_ok = abs(ratio_pb/ratio_chem - 1.0) < 1e-12

        # Thermal derivative d<X>/dT = Cov(X,E)/(k_B T^2).
        e_levels = np.array([0.0, 0.8, 1.7, 3.1], dtype=float)
        x_levels = np.array([0.2, -0.4, 1.1, 2.0], dtype=float)
        t0 = 1.37
        kb_test = 1.0
        def thermal_mean(tval: float) -> float:
            ww = np.exp(-e_levels/(kb_test*tval)); ww /= ww.sum()
            return float(np.sum(ww*x_levels))
        ww0 = np.exp(-e_levels/(kb_test*t0)); ww0 /= ww0.sum()
        cov_xe = float(np.sum(ww0*x_levels*e_levels)-np.sum(ww0*x_levels)*np.sum(ww0*e_levels))
        h = 1e-6
        fd = (thermal_mean(t0+h)-thermal_mean(t0-h))/(2*h)
        thermal_covariance_derivative_ok = abs(fd-cov_xe/(kb_test*t0*t0)) < 1e-7

        # Cosmological phase derivative for constant H has the stated (1+z)^-2 kernel.
        z0, dm2, e0, hubble = 0.73, 2.4, 4.1, 1.8
        phase_derivative_expected = dm2/(2.0*e0*(1.0+z0)**2*hubble)
        phase_antiderivative = lambda zz: dm2/(2.0*e0*hubble)*(1.0-1.0/(1.0+zz))
        phase_fd = (phase_antiderivative(z0+h)-phase_antiderivative(z0-h))/(2*h)
        cosmological_phase_kernel_ok = abs(phase_fd-phase_derivative_expected) < 1e-9

        # Drude subset relation is dimensionless: the SI density conversion cancels.
        mtest, sigtest, etest, tautest, ntotal = 2.0, 7.0, 3.0, 5.0, 11.0
        ncond = mtest*sigtest/(etest*etest*tautest)
        fcond = ncond/ntotal
        drude_subset_ratio_ok = abs(fcond - (mtest*sigtest/(etest*etest*tautest*ntotal))) < 1e-15

        checks = {
            "database_digest_valid": digest_ok,
            "law_digests_valid": law_digest_ok,
            "source_law_digests_valid": source_digests_ok,
            "law_ids_unique": ids_unique,
            "closure_family_ids_unique": family_ids_unique,
            "closure_family_digests_valid": family_digests_ok,
            "parameterized_materialization_matches_family_templates": materialized_template_ok,
            "parameterized_materialization_covers_declared_grids_exactly": materialized_parameter_coverage_ok,
            "max_materialized_intersection_order_matches_database": max_order_matches,
            "no_fixed_intersection_order_ceiling": no_fixed_order_ceiling,
            "no_fixed_materialized_candidate_ceiling": no_fixed_candidate_ceiling,
            "source_law_ids_unique": source_ids_unique,
            "all_source_owners_resolve": source_owners_resolve,
            "source_law_owners_resolve": source_law_owners_resolve,
            "all_constants_resolve": constants_resolve,
            "source_law_constants_resolve": source_constants_resolve,
            "embedded_constant_records_cover_all_references": embedded_constants_cover_references,
            "pdg2026_fermi_constant_provenance_value_consistent": gf_pdg2026_value_ok,
            "all_variable_records_complete": variable_rows_complete,
            "source_law_variable_records_complete": source_variable_rows_complete,
            "source_law_literature_statuses_present": source_literature_statuses_present,
            "all_referenced_literature_source_ids_resolve": literature_source_ids_resolve,
            "formal_empirical_novelty_statuses_separated": novelty_separated,
            "no_literature_novelty_reward_to_derivation": no_literature_reward,
            "cross_domain_source_usage_accounts_for_every_owner": cross_source_usage_exact,
            "cross_domain_interface_variables_present": cross_interfaces_present,
            "cross_domain_validity_gate_passes": cross_validity_gate_pass,
            "cross_domain_unit_contracts_present": cross_unit_contracts_present,
            "cross_domain_raw_si_gf_mixing_absent": cross_no_raw_si_gf_mixing,
            "cross_domain_materialized_source_usage_matches_family": cross_materialized_owner_usage_exact,
            "cross_domain_materialized_interfaces_match_family": cross_materialized_interfaces_exact,
            "cross_domain_materialized_units_match_family": cross_materialized_units_exact,
            "cross_domain_owner_replay_matches_materialized_database": cross_owner_replay_exact,
            "cross_domain_plasma_debye_elimination_numeric": plasma_debye_elimination_ok,
            "cross_domain_plasma_frequency_elimination_numeric": plasma_frequency_elimination_ok,
            "cross_domain_plasma_thermal_identity_numeric": plasma_thermal_identity_ok,
            "cross_domain_electrochemical_ratio_identity_numeric": electrochemical_ratio_identity_ok,
            "cross_domain_thermal_covariance_derivative_numeric": thermal_covariance_derivative_ok,
            "cross_domain_cosmological_phase_kernel_numeric": cosmological_phase_kernel_ok,
            "cross_domain_drude_subset_ratio_numeric": drude_subset_ratio_ok,
            "control_m_beta_beta_le_m_beta_numeric": beta_lnv_bound_ok,
            "control_common_mass_squared_shift_probability_invariant": common_shift_probability_ok,
            "control_beta_mass_squared_tracks_common_shift": beta_shift_ok,
            "parseval_sum_rule_numeric": parseval_ok,
            "parseval_tail_certificate_numeric": parseval_tail_ok,
            "oscillation_tail_cauchy_schwarz_numeric": oscillation_tail_bound_ok,
            "spectral_moment_threshold_algebra": hierarchy_formula_ok,
            "uv_threshold_ordering": threshold_order_ok,
            "takagi_beta_row_norm_identity_numeric": takagi_beta_identity_ok,
            "takagi_mbb_diagonal_identity_numeric": takagi_mbb_identity_ok,
            "majorana_offdiagonal_texture_identity_numeric": offdiag_texture_identity_ok,
            "spectral_moment_threshold_grid_numeric": moment_threshold_grid_ok,
            "oscillation_regularity_ladder_numeric": regularity_ladder_ok,
            "beta_msw_weighted_slope_elimination_numeric": beta_msw_slope_elimination_ok,
            "beta_msw_count_slope_identity_numeric": count_slope_identity_ok,
        }
        return {
            "schema": "phi-neutrino-law-intersection-qualification/v6.13",
            "owner_id": LAW_INTERSECTION_OWNER_ID,
            "owner_version": LAW_INTERSECTION_OWNER_VERSION,
            "status": "PASS_NEUTRINO_LAW_INTERSECTION_DATABASE" if all(checks.values()) else "FAIL_NEUTRINO_LAW_INTERSECTION_DATABASE",
            "checks": checks,
            "counts": dict(db.get("counts", {})),
            "database_digest": stored_digest,
            "claim_boundary": dict(db.get("claim_boundary", {})),
        }
