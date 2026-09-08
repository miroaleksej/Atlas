"""Bridge exact Buckingham coordinates into the existing OperatorGenesis grammar.

The bridge does not invent a second regression engine.  It asks the installed
OperatorGenesisOwner to enumerate its canonical monomial/Laurent families over a
*frozen dimensionless Pi coordinate*, fits on FIT only, and evaluates on SEAL.
It is a representation-adequacy diagnostic; promotion/null accounting remains
owned by OperatorGenesisOwner and is not forged here.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping, Sequence
import math
import numpy as np

from .schema import digest_payload

OWNER_ID = "PI-GENESIS-BRIDGE/1.0.0"


def _f(x: float) -> Fraction:
    return Fraction(str(float(x)))


def _nrmse(y: np.ndarray, p: np.ndarray) -> float:
    s = float(np.std(y))
    return float(np.sqrt(np.mean((p-y)**2)) / s) if s > 0 else math.inf


def _rel(y: np.ndarray, p: np.ndarray) -> Mapping[str, float]:
    r=np.abs(p-y)/np.maximum(np.abs(y),1e-300)
    return {"median":float(np.median(r)),"p90":float(np.quantile(r,.9)),"max":float(np.max(r))}


class PiGenesisBridgeOwner:
    owner_id = OWNER_ID

    def diagnose_monomial_grammar(
        self, *, pi_fit: Sequence[float], y_fit: Sequence[float], pi_seal: Sequence[float], y_seal: Sequence[float],
        max_terms: int = 6, max_degree: int = 8, allow_negative_exponents: bool = False,
        max_families_examined: int = 20_000,
    ) -> Mapping[str, Any]:
        # Local import preserves the existing extension as the sole Genesis owner.
        from scienceatlas_ai.operator_genesis import (
            OperatorGenesisOwner, OperatorGrammar, GenesisBudget, _least_squares, _sse, _gain_bp,
        )
        owner=OperatorGenesisOwner(null_owner=None)
        grammar=OperatorGrammar(max_terms=max_terms,max_degree=max_degree,
                                allow_negative_exponents=allow_negative_exponents,
                                require_constant_term=True)
        # permutation_count is part of the budget schema even though this method
        # intentionally stops before Genesis promotion/null adjudication.
        budget=GenesisBudget(grammar=grammar,max_families_examined=max_families_examined,
                             permutation_count=1,min_sealed_gain_bp=0)
        fit=[({"PI":_f(x)},_f(y)) for x,y in zip(pi_fit,y_fit)]
        seal=[({"PI":_f(x)},_f(y)) for x,y in zip(pi_seal,y_seal)]
        mean_fit=sum((y for _,y in fit),Fraction(0))/len(fit)
        incumbent_sse=sum((y-mean_fit)**2 for _,y in seal)
        best=None
        examined=0
        for family in owner.enumerate_candidates(budget=budget,input_axes=("PI",)):
            examined+=1
            matrix=[family.features(x) for x,_ in fit]
            if any(row is None for row in matrix):
                continue
            params=_least_squares([list(row) for row in matrix if row is not None],[y for _,y in fit])
            if params is None:
                continue
            sealed=_sse(family,params,seal)
            if sealed is None:
                continue
            gain=_gain_bp(incumbent_sse,sealed)
            key=(-gain,family.complexity,family.family_id)
            if best is None or key < best[0]:
                best=(key,gain,family,params,sealed)
        if best is None:
            core={"schema":"phi-pi-genesis-diagnostic/v1","owner":OWNER_ID,"status":"NO_ADMISSIBLE_GENESIS_FAMILY"}
            return {**core,"digest":digest_payload(core)}
        _,gain,family,params,_=best
        yf=np.asarray(y_fit,float); ys=np.asarray(y_seal,float)
        pf=np.array([float(sum(a*b for a,b in zip(family.features(x),params))) for x,_ in fit])
        ps=np.array([float(sum(a*b for a,b in zip(family.features(x),params))) for x,_ in seal])
        core={
            "schema":"phi-pi-genesis-diagnostic/v1","owner":OWNER_ID,
            "status":"PI_COORDINATE_GENESIS_REPRESENTATION_DIAGNOSED",
            "grammar":grammar.to_json(),"families_examined":examined,"winner_family":family.to_json(),
            "winner_family_id":family.family_id,
            "parameters":[{"numerator":p.numerator,"denominator":p.denominator} for p in params],
            "sealed_gain_bp_vs_fit_constant":gain,
            "fit_nrmse":_nrmse(yf,pf),"seal_nrmse":_nrmse(ys,ps),
            "fit_relative_error":_rel(yf,pf),"seal_relative_error":_rel(ys,ps),
            "promotion_attempted":False,"pipeline_null_run":False,
            "claim_boundary":{
                "representation_diagnostic_is_law_promotion":False,
                "pi_coordinate_was_frozen_before_genesis":True,
                "target_used_to_redefine_pi":False,
            },
        }
        return {**core,"digest":digest_payload(core)}

    def diagnose_pade_phi(self, *, pi_fit: Sequence[float], y_fit: Sequence[float], pi_seal: Sequence[float], y_seal: Sequence[float], numerator_degree: int=4) -> Mapping[str, Any]:
        """Bounded rational *diagnostic* over phi=sqrt(Pi), not a Genesis promotion.

        This answers only whether a simple rational grammar is plausibly adequate
        before adding transcendental atoms.  It is deliberately kept outside the
        live Genesis registry until such a grammar has its own null/pricing owner.
        """
        m=int(numerator_degree); n=m+1
        def fit(pi,y):
            ph=np.sqrt(np.asarray(pi,float)); yy=np.asarray(y,float); cols=[]
            for j in range(1,n+1): cols.append(yy*ph**j)
            for i in range(1,m+1): cols.append(-ph**i)
            return np.linalg.lstsq(np.column_stack(cols),1.0-yy,rcond=None)[0]
        def pred(pi,co):
            ph=np.sqrt(np.asarray(pi,float)); b=co[:n];a=co[n:];num=np.ones(len(ph));den=np.ones(len(ph))
            for i,c in enumerate(a,1):num+=c*ph**i
            for j,c in enumerate(b,1):den+=c*ph**j
            return num/den
        co=fit(pi_fit,y_fit); pf=pred(pi_fit,co);ps=pred(pi_seal,co)
        yf=np.asarray(y_fit,float);ys=np.asarray(y_seal,float)
        core={
            "schema":"phi-pi-rational-adequacy-diagnostic/v1","owner":OWNER_ID,
            "status":"PADE_PHI_DIAGNOSTIC_ONLY","phi_transform":"sqrt(PI)",
            "numerator_degree":m,"denominator_degree":n,"coefficients":[float(x) for x in co],
            "fit_nrmse":_nrmse(yf,pf),"seal_nrmse":_nrmse(ys,ps),
            "fit_relative_error":_rel(yf,pf),"seal_relative_error":_rel(ys,ps),
            "claim_boundary":{"part_of_live_genesis_grammar":False,"transcendental_grammar_proven_necessary":False,
                              "rational_grammar_proven_sufficient":False,"law_promotion":False},
        }
        return {**core,"digest":digest_payload(core)}
