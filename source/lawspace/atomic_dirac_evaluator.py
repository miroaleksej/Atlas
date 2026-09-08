"""Pure radial Dirac numerical evaluator for the electronic state-space owner.

This module owns no configuration search, periodic ordering, element exceptions, or
physical frontier decision.  It evaluates a supplied (Z,n,kappa,V) hypothesis.

Radial Dirac equation solver on a logarithmic grid (atomic units).

Large/small component form, energy epsilon measured WITHOUT the rest mass:

    dP/dr = -(kappa/r) P + [(2c^2 + eps - V)/c] Q
    dQ/dr = +(kappa/r) Q - [(eps - V)/c] P

kappa = -(l+1) for j = l+1/2 ;  kappa = +l for j = l-1/2
"""
from __future__ import annotations

import math
import numpy as np

CLIGHT = 137.035999084          # 1/alpha, atomic units
ALPHA = 1.0 / CLIGHT


def kappa_of(l: int, j2: int) -> int:
    """j2 = 2j. kappa = -(l+1) if j=l+1/2 else +l."""
    return -(l + 1) if j2 == 2 * l + 1 else l


def dirac_hydrogenic(Z: float, n: int, kappa: int) -> float:
    """Exact point-nucleus Dirac eigenvalue (binding, rest mass removed)."""
    za = Z * ALPHA
    g = math.sqrt(kappa * kappa - za * za)
    nr = n - abs(kappa)
    denom = math.sqrt(1.0 + (za / (nr + g)) ** 2)
    return CLIGHT ** 2 * (1.0 / denom - 1.0)


class LogGrid:
    """r_i = r0 * exp(i*h); integration is done in x = ln(r) so dr = r dx."""

    def __init__(self, Z: float, n_points: int = 3200, r_max: float = 60.0):
        r0 = 1e-7 / max(Z, 1.0)
        h = math.log(r_max / r0) / (n_points - 1)
        self.n = n_points
        self.h = h
        self.r = r0 * np.exp(h * np.arange(n_points))
        self.rp = self.r * h                      # dr/di

    def integrate(self, f: np.ndarray) -> float:
        """int f(r) dr over the whole grid (trapezoid in x, exact weight r*h)."""
        g = f * self.rp
        return float(np.sum(g) - 0.5 * (g[0] + g[-1]))

    def cumulative(self, f: np.ndarray) -> np.ndarray:
        """int_0^r f dr, cumulative."""
        g = f * self.rp
        out = np.concatenate([[0.0], np.cumsum(0.5 * (g[1:] + g[:-1]))])
        return out

    def reverse_cumulative(self, f: np.ndarray) -> np.ndarray:
        """int_r^inf f dr."""
        tot = self.cumulative(f)
        return tot[-1] - tot


def _derivs(i: int, P: float, Q: float, eps: float, kappa: int,
            grid: LogGrid, V: np.ndarray) -> tuple[float, float]:
    r = grid.r[i]
    v = V[i]
    dP = (-(kappa / r) * P + ((2.0 * CLIGHT ** 2 + eps - v) / CLIGHT) * Q) * grid.rp[i]
    dQ = ((kappa / r) * Q - ((eps - v) / CLIGHT) * P) * grid.rp[i]
    return dP, dQ


def _interp_derivs(x: float, P: float, Q: float, eps: float, kappa: int,
                   grid: LogGrid, V: np.ndarray) -> tuple[float, float]:
    """Derivatives at fractional index x (linear interpolation of r, V, rp)."""
    i0 = int(math.floor(x))
    i1 = min(i0 + 1, grid.n - 1)
    t = x - i0
    r = grid.r[i0] * (1 - t) + grid.r[i1] * t
    v = V[i0] * (1 - t) + V[i1] * t
    rp = grid.rp[i0] * (1 - t) + grid.rp[i1] * t
    dP = (-(kappa / r) * P + ((2.0 * CLIGHT ** 2 + eps - v) / CLIGHT) * Q) * rp
    dQ = ((kappa / r) * Q - ((eps - v) / CLIGHT) * P) * rp
    return dP, dQ


def _rk4_step(i: int, direction: int, P: float, Q: float, eps: float, kappa: int,
              grid: LogGrid, V: np.ndarray) -> tuple[float, float]:
    d = float(direction)
    k1P, k1Q = _interp_derivs(i, P, Q, eps, kappa, grid, V)
    k2P, k2Q = _interp_derivs(i + 0.5 * d, P + 0.5 * d * k1P, Q + 0.5 * d * k1Q, eps, kappa, grid, V)
    k3P, k3Q = _interp_derivs(i + 0.5 * d, P + 0.5 * d * k2P, Q + 0.5 * d * k2Q, eps, kappa, grid, V)
    k4P, k4Q = _interp_derivs(i + d, P + d * k3P, Q + d * k3Q, eps, kappa, grid, V)
    return (P + d * (k1P + 2 * k2P + 2 * k3P + k4P) / 6.0,
            Q + d * (k1Q + 2 * k2Q + 2 * k3Q + k4Q) / 6.0)


def _outward(eps: float, kappa: int, grid: LogGrid, V: np.ndarray, i_match: int):
    """Integrate from the origin. Returns P, Q arrays and node count."""
    Z_eff = -V[0] * grid.r[0]
    l = kappa if kappa > 0 else -kappa - 1
    P = np.zeros(grid.n)
    Q = np.zeros(grid.n)
    r0 = grid.r[0]
    if Z_eff < 0.5:
        # FINITE nucleus: V(0) is finite, the regular series is P ~ r^(l+1).
        #   kappa < 0 :  P = r^(l+1),        Q = P * r (V0 - eps) / (c (2l+3))
        #   kappa > 0 :  P = r^(l+1),        Q = P * (2l+1) / (2 c r)
        V0 = V[0]
        P[0] = r0 ** (l + 1)
        if kappa < 0:
            Q[0] = P[0] * r0 * (V0 - eps) / (CLIGHT * (2 * l + 3))
        else:
            Q[0] = P[0] * (2 * l + 1) / (2.0 * CLIGHT * r0)
    else:
        # POINT nucleus: P ~ r^gamma with gamma = sqrt(kappa^2 - (Z alpha)^2)
        gam = math.sqrt(max(kappa * kappa - (Z_eff * ALPHA) ** 2, 1e-12))
        P[0] = r0 ** gam
        Q[0] = P[0] * CLIGHT * (kappa + gam) / max(Z_eff, 1e-12)
    scale0 = abs(P[0]) + abs(Q[0])
    if scale0 > 0:
        P[0] /= scale0
        Q[0] /= scale0
    nodes = 0
    for i in range(i_match):
        P[i + 1], Q[i + 1] = _rk4_step(i, +1, P[i], Q[i], eps, kappa, grid, V)
        if P[i + 1] * P[i] < 0.0:
            nodes += 1
        if abs(P[i + 1]) > 1e100:
            scale = 1e-100
            P[:i + 2] *= scale
            Q[:i + 2] *= scale
    return P, Q, nodes


def _inward(eps: float, kappa: int, grid: LogGrid, V: np.ndarray, i_match: int):
    """Integrate from r_max inward with exponential-decay start."""
    P = np.zeros(grid.n)
    Q = np.zeros(grid.n)
    lam = math.sqrt(max(-eps * (2.0 + eps / CLIGHT ** 2), 1e-14))
    i_start = grid.n - 1
    # start where the decaying solution is still representable
    for i in range(grid.n - 1, i_match, -1):
        if lam * (grid.r[i] - grid.r[i_match]) < 500.0:
            i_start = i
            break
    P[i_start] = 1e-20
    Q[i_start] = -P[i_start] * lam * CLIGHT / (2.0 * CLIGHT ** 2 + eps)
    nodes = 0
    for i in range(i_start, i_match, -1):
        P[i - 1], Q[i - 1] = _rk4_step(i, -1, P[i], Q[i], eps, kappa, grid, V)
        if P[i - 1] * P[i] < 0.0:
            nodes += 1
        if abs(P[i - 1]) > 1e100:
            scale = 1e-100
            P[i - 1:] *= scale
            Q[i - 1:] *= scale
    return P, Q, nodes, i_start


def _match_index(eps: float, kappa: int, grid: LogGrid, V: np.ndarray) -> int:
    """Classical turning point, clamped away from the grid edges."""
    l = kappa if kappa > 0 else -kappa - 1
    centrifugal = l * (l + 1) / (2.0 * grid.r ** 2)
    diff = eps - V - centrifugal
    idx = np.where(diff < 0.0)[0]
    idx = idx[idx > grid.n // 8]
    i = int(idx[0]) if idx.size else int(0.75 * grid.n)
    return max(grid.n // 8, min(i, grid.n - 200))


def solve_orbital(Z: float, n: int, kappa: int, grid: LogGrid, V: np.ndarray,
                  eps_guess: float | None = None, tol: float = 1e-10, max_iter: int = 200):
    """Bound-state eigenvalue for (n, kappa) in potential V. Returns (eps, P, Q)."""
    l = kappa if kappa > 0 else -kappa - 1
    target_nodes = n - l - 1

    if eps_guess is None:
        eps_guess = dirac_hydrogenic(max(Z - n * n * 0.4, 1.0), n, kappa)
    e_lo, e_hi = -1.2 * CLIGHT ** 2, -1e-8
    eps = max(min(eps_guess, -1e-6), e_lo * 0.9)

    # --- phase 1: bisection on node count -------------------------------
    for _ in range(120):
        i_m = _match_index(eps, kappa, grid, V)
        Po, Qo, no = _outward(eps, kappa, grid, V, i_m)
        Pi, Qi, ni, i_start = _inward(eps, kappa, grid, V, i_m)
        nodes = no + ni
        if nodes > target_nodes:
            e_hi = eps
        elif nodes < target_nodes:
            e_lo = eps
        else:
            break
        eps = 0.5 * (e_lo + e_hi)
    else:
        return None

    # --- phase 2: match the logarithmic derivative -----------------------
    def defect(e: float):
        i_m = _match_index(e, kappa, grid, V)
        Po, Qo, no = _outward(e, kappa, grid, V, i_m)
        Pi, Qi, ni, i_start = _inward(e, kappa, grid, V, i_m)
        if abs(Pi[i_m]) < 1e-300 or abs(Po[i_m]) < 1e-300:
            return None
        s = Po[i_m] / Pi[i_m]
        Pi = Pi * s
        Qi = Qi * s
        P = np.concatenate([Po[:i_m], Pi[i_m:]])
        Q = np.concatenate([Qo[:i_m], Qi[i_m:]])
        P[i_start + 1:] = 0.0
        Q[i_start + 1:] = 0.0
        norm = grid.integrate(P * P + Q * Q)
        if norm <= 0:
            return None
        d = CLIGHT * (Qo[i_m] - Qi[i_m]) * P[i_m] / norm
        return d, P / math.sqrt(norm), Q / math.sqrt(norm), no + ni

    lo, hi = e_lo, e_hi
    for _ in range(max_iter):
        r = defect(eps)
        if r is None:
            return None
        d, P, Q, nodes = r
        if nodes != target_nodes:
            if nodes > target_nodes:
                hi = eps
            else:
                lo = eps
            eps = 0.5 * (lo + hi)
            continue
        step = d
        new = eps + step
        if not (lo < new < hi):
            if d > 0:
                lo = eps
            else:
                hi = eps
            new = 0.5 * (lo + hi)
        if abs(new - eps) < tol * max(1.0, abs(eps)):
            eps = new
            r = defect(eps)
            if r is None:
                return None
            return eps, r[1], r[2]
        if d > 0:
            lo = max(lo, eps)
        else:
            hi = min(hi, eps)
        eps = new
    return eps, P, Q
