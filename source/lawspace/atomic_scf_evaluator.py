"""Dirac-Slater SCF evaluator used by ELECTRONIC-STATE-SPACE-SEARCH.

This module is deliberately *not* a configuration generator.  It evaluates a
caller-supplied electronic occupation hypothesis and an explicit nuclear model.
There is no Aufbau/Madelung order, no element-specific exception table, and no
internal A(Z) or nuclear-radius law.  Search/orchestration belongs to
``ElectronicStateSpaceSearchOwner`` in :mod:`atomic_frontier`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np

from .atomic_dirac_evaluator import CLIGHT, LogGrid, kappa_of, solve_orbital

FM_TO_BOHR = 1.8897261246e-5
ALPHA_X_DEFAULT = 2.0 / 3.0


@dataclass(frozen=True)
class NuclearSphere:
    """Explicit finite nuclear charge hypothesis supplied by another owner."""
    radius_fm: float
    provenance: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.radius_fm) or self.radius_fm <= 0.0:
            raise ValueError("finite nuclear radius_fm must be positive")
        if not str(self.provenance).strip():
            raise ValueError("nuclear provenance is required")


@dataclass(frozen=True)
class Sub:
    n: int
    l: int
    j2: int
    occ: float

    @property
    def kappa(self) -> int:
        return kappa_of(self.l, self.j2)

    @property
    def label(self) -> str:
        return f"n{self.n}_l{self.l}_j2{self.j2}"


def split_config(config: Mapping[tuple[int, int], float]) -> list[Sub]:
    """Split numerical (n,l) occupations into relativistic j subshells.

    The split is degeneracy-weighted (average-of-configuration).  The mapping is
    a representation choice of this evaluator and is returned in receipts; it is
    not a claim that configuration interaction has been solved.
    """
    out: list[Sub] = []
    for (n_raw, l_raw), q_raw in config.items():
        n, l, q = int(n_raw), int(l_raw), float(q_raw)
        if n <= 0 or l < 0 or l >= n:
            raise ValueError(f"invalid orbital coordinates {(n, l)}")
        cap = 2 * (2 * l + 1)
        if q < -1e-12 or q > cap + 1e-12:
            raise ValueError(f"occupation {q} outside [0,{cap}] for {(n,l)}")
        if q <= 1e-12:
            continue
        if l == 0:
            out.append(Sub(n, 0, 1, q))
        else:
            for j2 in (2 * l - 1, 2 * l + 1):
                out.append(Sub(n, l, j2, q * (j2 + 1) / cap))
    return out


def nuclear_potential(grid: LogGrid, Z: float, nucleus: NuclearSphere) -> np.ndarray:
    radius = nucleus.radius_fm * FM_TO_BOHR
    r = grid.r
    return np.where(r >= radius, -Z / r, -Z / (2.0 * radius) * (3.0 - (r / radius) ** 2))


def _hartree(grid: LogGrid, D: np.ndarray) -> np.ndarray:
    inner = grid.cumulative(D)
    outer = grid.reverse_cumulative(D / grid.r)
    return inner / grid.r + outer


def _exchange(grid: LogGrid, D: np.ndarray, alpha_x: float) -> np.ndarray:
    rho = np.maximum(D / (4.0 * math.pi * grid.r ** 2), 0.0)
    return -3.0 * alpha_x * (3.0 * rho / (8.0 * math.pi)) ** (1.0 / 3.0)


def _regularize_origin(grid: LogGrid, D: np.ndarray, radius_fm: float) -> np.ndarray:
    """Remove numerically irregular near-origin density without changing charge."""
    D = np.asarray(D, dtype=float).copy()
    r_cut = 3.0 * radius_fm * FM_TO_BOHR
    i = min(max(int(np.searchsorted(grid.r, r_cut)), 2), grid.n - 2)
    D[:i] = D[i] * (grid.r[:i] / grid.r[i]) ** 2
    return D


@dataclass
class SCFResult:
    Z: int
    N: float
    converged: bool
    iterations: int
    residual: float
    total_energy: float
    eigenvalues: dict
    occupations: dict
    detail: dict = field(default_factory=dict)


def scf(
    Z: int,
    config: Mapping[tuple[int, int], float],
    nucleus: NuclearSphere,
    *,
    grid: LogGrid | None = None,
    max_iter: int = 100,
    tol: float = 1e-6,
    alpha_x: float = ALPHA_X_DEFAULT,
    n_hist: int = 6,
) -> SCFResult:
    """Evaluate one supplied occupation hypothesis with finite-nucleus Dirac-Slater SCF."""
    if not math.isfinite(alpha_x) or alpha_x <= 0.0:
        raise ValueError("alpha_x must be positive and finite")
    subs = split_config(config)
    if not subs:
        raise ValueError("nonempty electronic configuration is required")
    N = float(sum(s.occ for s in subs))
    if abs(N - float(Z)) > 1e-8:
        raise ValueError(f"neutral search requires total occupation Z={Z}, got {N}")

    grid = grid or LogGrid(Z, n_points=1200, r_max=40.0)
    r = grid.r
    Vnuc = nuclear_potential(grid, Z, nucleus)
    tail = -(Z - N + 1.0) / r

    # Neutral, smooth initial potential.  This is a numerical initializer only;
    # candidate ordering is not encoded here.
    screen_length = max(float(Z) ** (-1.0 / 3.0), 1e-3)
    screen = np.exp(-r / screen_length)
    V = np.minimum(screen * Vnuc + (1.0 - screen) * tail, tail)

    hist_V: list[np.ndarray] = []
    hist_R: list[np.ndarray] = []
    guess: dict[str, float] = {}
    eps_out: dict[str, float] = {}
    conv, res, it = False, float("inf"), 0
    E_tot = float("nan")
    D = np.zeros_like(r)

    for it in range(1, max_iter + 1):
        D = np.zeros_like(r)
        eps_out = {}
        ok = True
        for s in subs:
            ans = solve_orbital(Z, s.n, s.kappa, grid, V, eps_guess=guess.get(s.label), tol=1e-9, max_iter=90)
            if ans is None:
                ok = False
                break
            e, P, Q = ans
            if not math.isfinite(e) or e >= 0.0 or e < -1.9 * CLIGHT ** 2:
                ok = False
                break
            guess[s.label] = e
            eps_out[s.label] = e
            d = _regularize_origin(grid, P * P + Q * Q, nucleus.radius_fm)
            nrm = grid.integrate(d)
            if not (nrm > 0.0 and math.isfinite(nrm)):
                ok = False
                break
            D += s.occ * d / nrm
        if not ok:
            break

        VH = _hartree(grid, D)
        VX = _exchange(grid, D, alpha_x)
        V_new = np.minimum(Vnuc + VH + VX, tail)
        R = V_new - V
        res = float(np.max(np.abs(R * r)))
        if res < tol:
            V = V_new
            conv = True

        hist_V.append(V.copy()); hist_R.append(R.copy())
        if len(hist_V) > n_hist:
            hist_V.pop(0); hist_R.pop(0)
        m = len(hist_R)
        if m >= 2:
            B = np.empty((m + 1, m + 1)); B[-1, :] = -1.0; B[:, -1] = -1.0; B[-1, -1] = 0.0
            for a in range(m):
                for b in range(m):
                    B[a, b] = float(np.dot(hist_R[a] * r, hist_R[b] * r))
            rhs = np.zeros(m + 1); rhs[-1] = -1.0
            try:
                coeff = np.linalg.solve(B, rhs)[:m]
                V = sum(c * (hv + 0.4 * hr) for c, hv, hr in zip(coeff, hist_V, hist_R))
                V = np.minimum(V, tail)
            except np.linalg.LinAlgError:
                V = V + 0.3 * R
        else:
            V = V + 0.3 * R

        if conv:
            EH = 0.5 * grid.integrate(D * VH)
            E_tot = sum(s.occ * eps_out[s.label] for s in subs) - EH - 0.25 * grid.integrate(D * VX)
            break

    if not conv and eps_out:
        VH = _hartree(grid, D); VX = _exchange(grid, D, alpha_x)
        EH = 0.5 * grid.integrate(D * VH)
        E_tot = sum(s.occ * eps_out[s.label] for s in subs) - EH - 0.25 * grid.integrate(D * VX)

    return SCFResult(
        Z=Z, N=N, converged=conv, iterations=it, residual=res,
        total_energy=float(E_tot), eigenvalues=eps_out,
        occupations={s.label: s.occ for s in subs},
        detail={
            "grid_points": grid.n,
            "r_max": float(r[-1]),
            "alpha_x": float(alpha_x),
            "nuclear_radius_fm": float(nucleus.radius_fm),
            "nuclear_provenance": nucleus.provenance,
            "configuration_generator_inside_evaluator": False,
            "aufbau_or_madelung_used": False,
        },
    )
