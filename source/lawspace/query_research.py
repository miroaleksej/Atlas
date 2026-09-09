"""Query-driven scientific research over supplied observations.

Authoritative focused mode: observations/question -> finite search surface -> ranked
mathematical candidates.  The display limit is never the multiplicity budget: null
calibration records and replays the complete examined surface.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from typing import Any, Mapping, Sequence
import math
import numpy as np

from source.phi_compiler_owner import _fraction_nullspace
from .schema import digest_payload
from .dimensional_law_birth import collapse_score
from .mathematical_invention import FunctionLanguageBirthEngine

OWNER_ID = "QUERY-DRIVEN-RESEARCH/1.2.0"
BASIS=("L","M","T","I","Theta","N","J")


def _canon(v: Sequence[Fraction], names: Sequence[str]) -> tuple[tuple[str,int],...]:
    den=1
    for x in v: den=math.lcm(den,Fraction(x).denominator)
    ints=[int(Fraction(x)*den) for x in v]
    g=0
    for x in ints:
        if x:g=math.gcd(g,abs(x))
    if g:ints=[x//g for x in ints]
    first=next((x for x in ints if x),1)
    if first<0:ints=[-x for x in ints]
    return tuple((str(n),int(e)) for n,e in zip(names,ints) if e)


def _complexity(group): return sum(abs(e) for _,e in group)

def _formula(group):
    return " * ".join(n if e==1 else f"{n}^{e}" for n,e in group)

def _coordinate(group, values):
    out=np.ones(len(next(iter(values.values()))),float)
    for n,e in group: out*=np.asarray(values[n],float)**e
    return out


def _monomial_exponents(nvars: int, degree: int) -> tuple[tuple[int, ...], ...]:
    """Deterministic total-degree polynomial basis, excluding the intercept."""
    rows=[]
    for exps in product(range(int(degree)+1), repeat=int(nvars)):
        total=sum(exps)
        if 1 <= total <= int(degree):
            rows.append(tuple(int(x) for x in exps))
    rows.sort(key=lambda e:(sum(e), e))
    return tuple(rows)


def _poly_design(z: np.ndarray, exponents: Sequence[Sequence[int]]) -> np.ndarray:
    z=np.asarray(z,float)
    cols=[np.ones(z.shape[0],float)]
    for exp in exponents:
        col=np.ones(z.shape[0],float)
        for j,power_ in enumerate(exp):
            if int(power_): col*=z[:,j]**int(power_)
        cols.append(col)
    return np.column_stack(cols)


def _folds(n: int, group_ids: Sequence[str] | None = None, *, seed: int = 1729) -> tuple[np.ndarray, ...]:
    if group_ids is not None:
        groups=np.asarray([str(x) for x in group_ids],dtype=object)
        if len(groups)!=int(n): raise ValueError("group_ids length must equal observation row count")
        unique=[]
        for x in groups:
            if x not in unique: unique.append(x)
        if len(unique)<3: raise ValueError("grouped validation requires at least three groups")
        return tuple(np.flatnonzero(groups==g) for g in unique)
    k=min(5,max(3,int(n)//20 if int(n)>=60 else 3))
    order=np.random.default_rng(int(seed)).permutation(int(n))
    return tuple(np.sort(x) for x in np.array_split(order,k) if len(x))


def _fit_polynomial_cv(pi_matrix: np.ndarray, y: np.ndarray, coordinate_indices: Sequence[int], degree: int,
                       folds: Sequence[np.ndarray]) -> Mapping[str,Any] | None:
    coords=tuple(int(i) for i in coordinate_indices)
    if not coords: return None
    x=np.asarray(pi_matrix[:,coords],float); y=np.asarray(y,float)
    if x.ndim==1: x=x[:,None]
    exps=_monomial_exponents(x.shape[1],int(degree)); ncoef=1+len(exps)
    oof=np.full(len(y),np.nan,float); ranks=[]
    all_idx=np.arange(len(y))
    for val_idx in folds:
        train_idx=np.setdiff1d(all_idx,np.asarray(val_idx,int),assume_unique=False)
        if len(train_idx) <= ncoef+2: return None
        xt=x[train_idx]; xv=x[np.asarray(val_idx,int)]; yt=y[train_idx]
        mu=np.mean(xt,axis=0); sigma=np.std(xt,axis=0)
        if np.any(~np.isfinite(mu)) or np.any(~np.isfinite(sigma)) or np.any(sigma<=1e-14): return None
        zt=(xt-mu)/sigma; zv=(xv-mu)/sigma
        Xt=_poly_design(zt,exps); Xv=_poly_design(zv,exps)
        beta,_,rank,_=np.linalg.lstsq(Xt,yt,rcond=None)
        if int(rank)<min(Xt.shape):
            return None
        oof[np.asarray(val_idx,int)]=Xv@beta; ranks.append(int(rank))
    mask=np.isfinite(oof)&np.isfinite(y)
    if mask.sum()!=len(y): return None
    denom=float(np.std(y[mask]))
    if denom<=1e-14: return None
    rmse=float(np.sqrt(np.mean((oof[mask]-y[mask])**2)))
    nrmse=rmse/denom
    ss_res=float(np.sum((oof[mask]-y[mask])**2)); ss_tot=float(np.sum((y[mask]-np.mean(y[mask]))**2))
    r2=float(1.0-ss_res/ss_tot) if ss_tot>0 else None
    mu=np.mean(x,axis=0); sigma=np.std(x,axis=0)
    if np.any(sigma<=1e-14): return None
    X=_poly_design((x-mu)/sigma,exps); beta,_,rank,_=np.linalg.lstsq(X,y,rcond=None)
    return {
        "coordinate_indices":list(coords),"polynomial_degree":int(degree),"term_count":int(ncoef),
        "cross_validated_nrmse":float(nrmse),"cross_validated_r2":r2,"oof_rmse":rmse,
        "minimum_fold_rank":min(ranks) if ranks else None,"full_fit_rank":int(rank),
        "_oof_predictions":[float(v) for v in oof],
        "standardization":{"mean":[float(v) for v in mu],"scale":[float(v) for v in sigma]},
        "monomial_exponents":[list(e) for e in exps],"coefficients":[float(v) for v in beta],
    }


def _ridge_solve(X: np.ndarray, y: np.ndarray, ridge: float = 1e-8) -> tuple[np.ndarray,int]:
    X=np.asarray(X,float); y=np.asarray(y,float)
    if X.ndim!=2 or len(X)!=len(y): raise ValueError("invalid ridge design")
    reg=np.eye(X.shape[1],dtype=float)*float(ridge)
    if X.shape[1]: reg[0,0]=0.0
    try:
        beta=np.linalg.solve(X.T@X+reg,X.T@y)
    except np.linalg.LinAlgError:
        beta=np.linalg.lstsq(X,y,rcond=None)[0]
    return beta,int(np.linalg.matrix_rank(X))


def _standardize_fit(x: np.ndarray) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    x=np.asarray(x,float)
    mu=np.mean(x,axis=0); scale=np.std(x,axis=0)
    if np.any(~np.isfinite(mu)) or np.any(~np.isfinite(scale)) or np.any(scale<=1e-14):
        raise ValueError("degenerate coordinate scale")
    return (x-mu)/scale,mu,scale


def _linear_language_design_train(z: np.ndarray, family: str, variant: Mapping[str,Any]) -> tuple[np.ndarray,Mapping[str,Any]]:
    z=np.asarray(z,float); n,p=z.shape; cols=[np.ones(n,float)]
    state: dict[str,Any]={"family":str(family),"variant":dict(variant)}
    if family=="EXPONENTIAL":
        scale=float(variant.get("scale",1.0)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            q=np.clip(scale*z[:,j],-4.0,4.0); cols.extend((np.exp(q),np.exp(-q)))
    elif family=="LOGARITHMIC":
        scale=float(variant.get("scale",1.0)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            q=z[:,j]; cols.extend((np.sign(q)*np.log1p(scale*np.abs(q)),np.log1p(scale*q*q)))
    elif family=="PERIODIC":
        max_frequency=int(variant.get("max_frequency",2)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            for w in range(1,max_frequency+1): cols.extend((np.sin(w*z[:,j]),np.cos(w*z[:,j])))
    elif family=="PIECEWISE":
        qs=tuple(float(q) for q in variant.get("quantiles",(0.33,0.67)))
        thresholds=[]; cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            th=[float(v) for v in np.quantile(z[:,j],qs)]; thresholds.append(th)
            for t in th: cols.append(np.maximum(0.0,z[:,j]-t))
        state["thresholds"]=thresholds
    elif family=="KERNEL":
        gamma=float(variant.get("gamma",1.0)); max_centers=int(variant.get("max_centers",8))
        k=max(2,min(max_centers,max(2,n//4),n))
        first=int(np.argmin(np.sum((z-np.mean(z,axis=0))**2,axis=1))); chosen=[first]
        while len(chosen)<k:
            d2=np.min(np.sum((z[:,None,:]-z[np.asarray(chosen)][None,:,:])**2,axis=2),axis=1)
            d2[np.asarray(chosen)]=-1.0; nxt=int(np.argmax(d2))
            if nxt in chosen: break
            chosen.append(nxt)
        centers=z[np.asarray(chosen)]
        cols.extend(z[:,j] for j in range(p))
        d2=np.sum((z[:,None,:]-centers[None,:,:])**2,axis=2)
        cols.extend(np.exp(-gamma*d2[:,j]) for j in range(d2.shape[1]))
        state["centers"]=[[float(v) for v in row] for row in centers]; state["gamma"]=gamma
    elif family=="LATENT":
        k=max(1,min(int(variant.get("components",1)),p)); degree=int(variant.get("degree",2))
        _,_,vt=np.linalg.svd(z,full_matrices=False); components=vt[:k]
        latent=z@components.T; exps=_monomial_exponents(k,degree)
        for exp in exps:
            col=np.ones(n,float)
            for j,pow_ in enumerate(exp):
                if int(pow_): col*=latent[:,j]**int(pow_)
            cols.append(col)
        state["components"]=[[float(v) for v in row] for row in components]
        state["latent_exponents"]=[list(e) for e in exps]
    else:
        raise ValueError(f"unsupported linear language family {family}")
    return np.column_stack(cols),state


def _linear_language_design_predict(z: np.ndarray, state: Mapping[str,Any]) -> np.ndarray:
    z=np.asarray(z,float); n,p=z.shape; family=str(state["family"]); variant=dict(state.get("variant",{})); cols=[np.ones(n,float)]
    if family=="EXPONENTIAL":
        scale=float(variant.get("scale",1.0)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            q=np.clip(scale*z[:,j],-4.0,4.0); cols.extend((np.exp(q),np.exp(-q)))
    elif family=="LOGARITHMIC":
        scale=float(variant.get("scale",1.0)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            q=z[:,j]; cols.extend((np.sign(q)*np.log1p(scale*np.abs(q)),np.log1p(scale*q*q)))
    elif family=="PERIODIC":
        max_frequency=int(variant.get("max_frequency",2)); cols.extend(z[:,j] for j in range(p))
        for j in range(p):
            for w in range(1,max_frequency+1): cols.extend((np.sin(w*z[:,j]),np.cos(w*z[:,j])))
    elif family=="PIECEWISE":
        cols.extend(z[:,j] for j in range(p)); thresholds=state.get("thresholds",[])
        for j in range(p):
            for t in thresholds[j]: cols.append(np.maximum(0.0,z[:,j]-float(t)))
    elif family=="KERNEL":
        centers=np.asarray(state.get("centers",[]),float); gamma=float(state.get("gamma",1.0)); cols.extend(z[:,j] for j in range(p))
        d2=np.sum((z[:,None,:]-centers[None,:,:])**2,axis=2)
        cols.extend(np.exp(-gamma*d2[:,j]) for j in range(d2.shape[1]))
    elif family=="LATENT":
        components=np.asarray(state.get("components",[]),float); latent=z@components.T
        for exp in state.get("latent_exponents",[]):
            col=np.ones(n,float)
            for j,pow_ in enumerate(exp):
                if int(pow_): col*=latent[:,j]**int(pow_)
            cols.append(col)
    else:
        raise ValueError(f"unsupported linear language family {family}")
    return np.column_stack(cols)


def _fit_language_model(x: np.ndarray, y: np.ndarray, family: str, variant: Mapping[str,Any]) -> Mapping[str,Any] | None:
    x=np.asarray(x,float); y=np.asarray(y,float)
    try: z,mu,scale=_standardize_fit(x)
    except ValueError: return None
    ridge=float(variant.get("ridge",1e-6))
    if family=="RATIONAL":
        num_degree=int(variant.get("numerator_degree",1)); exps=_monomial_exponents(z.shape[1],num_degree)
        P=_poly_design(z,exps); Q=z
        A=np.column_stack((P,-y[:,None]*Q))
        if len(y)<=A.shape[1]+2: return None
        beta,rank=_ridge_solve(A,y,ridge)
        pc=beta[:P.shape[1]]; qc=beta[P.shape[1]:]
        state={"family":family,"variant":dict(variant),"mean":[float(v) for v in mu],"scale":[float(v) for v in scale],
               "numerator_exponents":[list(e) for e in exps],"numerator_coefficients":[float(v) for v in pc],
               "denominator_coefficients":[float(v) for v in qc]}
        pred=_predict_language_model(x,state)
        if pred is None or np.any(~np.isfinite(pred)): return None
        return {"model_state":state,"rank":rank,"term_count":int(len(beta))}
    try: X,state0=_linear_language_design_train(z,family,variant)
    except Exception: return None
    if len(y)<=X.shape[1]+2: return None
    beta,rank=_ridge_solve(X,y,ridge)
    state={**dict(state0),"mean":[float(v) for v in mu],"scale":[float(v) for v in scale],"coefficients":[float(v) for v in beta]}
    pred=_predict_language_model(x,state)
    if pred is None or np.any(~np.isfinite(pred)): return None
    return {"model_state":state,"rank":rank,"term_count":int(X.shape[1])}


def _predict_language_model(x: np.ndarray, state: Mapping[str,Any]) -> np.ndarray | None:
    x=np.asarray(x,float); mu=np.asarray(state["mean"],float); scale=np.asarray(state["scale"],float); z=(x-mu)/scale
    family=str(state["family"])
    if family=="RATIONAL":
        exps=state.get("numerator_exponents",[]); P=_poly_design(z,exps); pc=np.asarray(state["numerator_coefficients"],float); qc=np.asarray(state["denominator_coefficients"],float)
        denom=1.0+z@qc
        if np.any(np.abs(denom)<0.05): return None
        return (P@pc)/denom
    X=_linear_language_design_predict(z,state); return X@np.asarray(state["coefficients"],float)


def _fit_born_language_cv(pi_matrix: np.ndarray, y: np.ndarray, coordinate_indices: Sequence[int], family: str,
                           variant: Mapping[str,Any], folds: Sequence[np.ndarray]) -> Mapping[str,Any] | None:
    coords=tuple(int(i) for i in coordinate_indices); x=np.asarray(pi_matrix[:,coords],float); y=np.asarray(y,float)
    if x.ndim==1:x=x[:,None]
    oof=np.full(len(y),np.nan,float); ranks=[]; all_idx=np.arange(len(y))
    for val_idx in folds:
        train_idx=np.setdiff1d(all_idx,np.asarray(val_idx,int),assume_unique=False)
        fit=_fit_language_model(x[train_idx],y[train_idx],family,variant)
        if fit is None:return None
        pred=_predict_language_model(x[np.asarray(val_idx,int)],fit["model_state"])
        if pred is None or np.any(~np.isfinite(pred)):return None
        oof[np.asarray(val_idx,int)]=pred; ranks.append(int(fit["rank"]))
    denom=float(np.std(y))
    if denom<=1e-14 or np.any(~np.isfinite(oof)): return None
    rmse=float(np.sqrt(np.mean((oof-y)**2))); nrmse=rmse/denom
    ss_res=float(np.sum((oof-y)**2)); ss_tot=float(np.sum((y-np.mean(y))**2)); r2=float(1.0-ss_res/ss_tot) if ss_tot>0 else None
    full=_fit_language_model(x,y,family,variant)
    if full is None:return None
    return {"coordinate_indices":list(coords),"function_family":family,"family_variant":dict(variant),"term_count":int(full["term_count"]),
            "cross_validated_nrmse":float(nrmse),"cross_validated_r2":r2,"oof_rmse":rmse,"minimum_fold_rank":min(ranks) if ranks else None,
            "full_fit_rank":int(full["rank"]),"model_state":full["model_state"],"_oof_predictions":[float(v) for v in oof]}


def predict_function_hypothesis(hypothesis: Mapping[str,Any], pi_matrix: Sequence[Sequence[float]]) -> np.ndarray:
    """Predict a fitted Query function-form hypothesis on a Pi matrix."""
    arr=np.asarray(pi_matrix,float); coords=[int(i) for i in hypothesis.get("coordinate_indices",[])]
    x=arr[:,coords] if coords else arr
    family=str(hypothesis.get("function_family",""))
    if family=="STANDARDIZED_TOTAL_DEGREE_POLYNOMIAL":
        mu=np.asarray(hypothesis["standardization"]["mean"],float); scale=np.asarray(hypothesis["standardization"]["scale"],float); z=(x-mu)/scale
        return _poly_design(z,hypothesis["monomial_exponents"])@np.asarray(hypothesis["coefficients"],float)
    pred=_predict_language_model(x,hypothesis["model_state"])
    if pred is None: raise ValueError("function-language hypothesis is undefined on requested coordinates")
    return np.asarray(pred,float)


def _language_variants(family: str, coord_count: int) -> tuple[Mapping[str,Any],...]:
    if family=="RATIONAL": return ({"numerator_degree":1,"ridge":1e-6},{"numerator_degree":2,"ridge":1e-5})
    if family=="EXPONENTIAL": return ({"scale":0.5,"ridge":1e-5},{"scale":1.0,"ridge":1e-5},{"scale":2.0,"ridge":1e-4})
    if family=="LOGARITHMIC": return ({"scale":0.5,"ridge":1e-6},{"scale":1.0,"ridge":1e-6},{"scale":2.0,"ridge":1e-5})
    if family=="PERIODIC": return ({"max_frequency":1,"ridge":1e-5},{"max_frequency":2,"ridge":1e-5},{"max_frequency":3,"ridge":1e-4})
    if family=="PIECEWISE": return ({"quantiles":[0.5],"ridge":1e-5},{"quantiles":[0.33,0.67],"ridge":1e-5},{"quantiles":[0.25,0.5,0.75],"ridge":1e-4})
    if family=="KERNEL": return ({"gamma":0.35,"max_centers":12,"ridge":1e-4},{"gamma":0.8,"max_centers":18,"ridge":1e-4},{"gamma":1.6,"max_centers":24,"ridge":1e-3})
    if family=="LATENT":
        ks=tuple(range(1,min(3,int(coord_count))+1)); return tuple({"components":k,"degree":2,"ridge":1e-5} for k in ks)
    return ()


def _born_specs(receipt: Mapping[str,Any], p: int, remaining_budget: int) -> tuple[tuple[str,tuple[int,...],Mapping[str,Any],str],...]:
    out=[]; full=tuple(range(int(p)))
    for lang in receipt.get("generated_languages",[]):
        family=str(lang.get("family","")); pref=[int(i) for i in lang.get("coordinate_preference",[]) if 0<=int(i)<int(p)]
        coordsets=[full]
        if pref: coordsets.append((pref[0],))
        if len(pref)>=2: coordsets.append(tuple(sorted(pref[:2])))
        seen=[]
        for c in coordsets:
            if c not in seen: seen.append(c)
        for coords in seen:
            for variant in _language_variants(family,len(coords)):
                out.append((family,tuple(coords),dict(variant),str(lang.get("language_id",""))))
                if len(out)>=int(remaining_budget): return tuple(out)
    return tuple(out)


def _function_specs(nullity: int, *, hypothesis_budget: int = 100) -> tuple[tuple[tuple[int,...],int], ...]:
    """Finite query tranche; not a global scientific-space ceiling."""
    p=int(nullity); budget=int(hypothesis_budget)
    if not (10 <= budget <= 100): raise ValueError("hypothesis_budget must be in [10,100]")
    degrees=(1,2,3,4) if p<=3 else (1,2,3)
    all_specs=[]
    for s in range(1,p+1):
        for coords in combinations(range(p),s):
            for degree in degrees:
                all_specs.append((tuple(coords),int(degree)))
    # Guarantee the full manifold is examined before lower-dimensional refinements are truncated.
    full=[x for x in all_specs if len(x[0])==p]
    rest=[x for x in all_specs if len(x[0])!=p]
    rest.sort(key=lambda x:(len(x[0]),x[1],x[0]))
    ordered=[]
    for x in full+rest:
        if x not in ordered: ordered.append(x)
    return tuple(ordered[:budget])

class QueryDrivenResearchOwner:
    owner_id=OWNER_ID

    def search_observations(self, *, observations: Mapping[str, Sequence[float]],
                            dimensions: Mapping[str, Sequence[int]],
                            target_name: str | None=None,
                            question: str | None=None,
                            return_limit: int=25,
                            min_subset_size: int=2,
                            max_subset_size: int | None=None,
                            permutation_count: int=0,
                            permutation_seed: int=0) -> Mapping[str,Any]:
        if not (10 <= int(return_limit) <= 100):
            raise ValueError("return_limit must be in [10,100]")
        obs={str(k):np.asarray(v,float) for k,v in observations.items()}
        if not obs: raise ValueError("observations are empty")
        lengths={len(v) for v in obs.values()}
        if len(lengths)!=1: raise ValueError("all observation columns must have equal length")
        if target_name is not None and target_name not in obs: raise ValueError("target_name missing")
        feature_names=[n for n in obs if n!=target_name]
        for n in feature_names:
            d=dimensions.get(n)
            if d is None or len(d)!=7: raise ValueError(f"missing 7D dimension for {n}")
        maxk=min(len(feature_names), int(max_subset_size or len(feature_names)))
        candidates=[]; examined_subsets=0; groups_examined=0; p_gt_1_subsets=0
        for k in range(max(2,int(min_subset_size)),maxk+1):
            for subset in combinations(feature_names,k):
                examined_subsets+=1
                matrix=[[Fraction(int(dimensions[n][i])) for n in subset] for i in range(7)]
                ns=_fraction_nullspace(matrix)
                if len(ns)>1:
                    p_gt_1_subsets+=1
                    continue
                if len(ns)!=1: continue
                groups_examined+=1
                group=_canon(ns[0],subset)
                if not group: continue
                row={"axis_names":list(subset),"pi_group":[{"name":n,"exponent":e} for n,e in group],
                     "formula":_formula(group),"complexity":_complexity(group),"nullity":1}
                if target_name is None:
                    row.update({"representation":"PI_EQUALS_CONSTANT","scalar_equation_frozen":True,
                                "candidate_equation":_formula(group)+" = C_DIMENSIONLESS"})
                else:
                    pi=_coordinate(group,obs)
                    try: coll=collapse_score(pi,obs[target_name])
                    except Exception: coll=math.inf
                    row.update({"representation":"TARGET_AS_FUNCTION_OF_PI","scalar_equation_frozen":True,
                                "candidate_equation":f"{target_name} = f({_formula(group)})",
                                "collapse_score":float(coll)})
                row["signature"]=digest_payload({"group":row["pi_group"],"target":target_name})
                candidates.append(row)
        # Deduplicate mathematical candidates before ranking; candidate ids are not diversity.
        unique={}
        for r in candidates:
            key=r["signature"]
            old=unique.get(key)
            if old is None or (r.get("collapse_score",math.inf),r["complexity"]) < (old.get("collapse_score",math.inf),old["complexity"]):
                unique[key]=r
        ranked=list(unique.values())
        if target_name is None:
            ranked.sort(key=lambda r:(r["complexity"],r["formula"],r["signature"]))
        else:
            ranked.sort(key=lambda r:(r["collapse_score"],r["complexity"],r["formula"],r["signature"]))
        for i,r in enumerate(ranked,1):r["rank"]=i

        null_summary=None
        if target_name is not None and permutation_count:
            # Replay the whole already-frozen dimensional candidate surface under permuted target.
            rng=np.random.default_rng(int(permutation_seed)); y=np.asarray(obs[target_name],float)
            groups=[tuple((x["name"],int(x["exponent"])) for x in r["pi_group"]) for r in ranked]
            pis=[_coordinate(g,obs) for g in groups]
            best=[]
            for _ in range(int(permutation_count)):
                yp=rng.permutation(y); scores=[]
                for pi in pis:
                    try:scores.append(collapse_score(pi,yp))
                    except Exception:scores.append(math.inf)
                best.append(min(scores) if scores else math.inf)
            observed=min((r.get("collapse_score",math.inf) for r in ranked),default=math.inf)
            finite=np.asarray([x for x in best if np.isfinite(x)],float)
            p=float((1+np.sum(finite<=observed))/(1+len(finite))) if len(finite) else None
            null_summary={"permutation_count":int(permutation_count),"entire_ranked_surface_replayed":True,
                          "observed_best_collapse":observed,"permutation_best_median":float(np.median(finite)) if len(finite) else None,
                          "familywise_empirical_p":p}
        core={"schema":"phi-query-driven-research/v1","owner":OWNER_ID,"status":"QUERY_RESEARCH_COMPLETE",
              "question":question,"target_name":target_name,"row_count":next(iter(lengths)),
              "feature_names":feature_names,"search_surface":{"subsets_examined_total":examined_subsets,
              "p1_groups_examined_total":groups_examined,"p_gt_1_subsets_deferred_total":p_gt_1_subsets,
              "p_gt_1_deferred_to_function_form_lane":True,"unique_mathematical_candidates_total":len(ranked),
              "display_limit":int(return_limit),"display_limit_is_search_budget":False},
              "candidates":ranked[:int(return_limit)],"permutation_null":null_summary,
              "claim_boundary":{"returned_count_is_multiplicity_count":False,
              "all_examined_candidates_are_accounted_for":True,"candidate_is_confirmed_law":False,
              "query_mode_replaces_open_discovery_frontier":False}}
        return {**core,"digest":digest_payload(core)}


    def search_function_forms(self, *, observations: Mapping[str, Sequence[float]],
                              dimensions: Mapping[str, Sequence[int]], target_name: str,
                              axis_names: Sequence[str] | None = None, question: str | None = None,
                              return_limit: int = 25, hypothesis_budget: int = 100,
                              group_ids: Sequence[str] | None = None,
                              permutation_count: int = 0, permutation_seed: int = 0,
                              function_language_birth: bool = True,
                              language_birth_nrmse: float = 0.08) -> Mapping[str,Any]:
        """Search F(Pi_1,...,Pi_p) on one exact Buckingham manifold (p>1).

        The dimensional kernel is frozen before fitting.  Query mode first
        evaluates its existing polynomial grammar.  If that grammar leaves a
        persistent out-of-fold residual, the *existing* Mathematical Invention
        Kernel diagnoses operation classes that could distinguish the residual
        and births a finite function-language tranche (rational, exponential,
        logarithmic, periodic, piecewise, kernel-local or latent-projection
        signatures).  No new scientific axis is created by this step.

        The requested ``hypothesis_budget`` is the complete finite tranche for
        this query, not a global Atlas-space ceiling.  Every target permutation
        replays polynomial fitting, residual diagnosis, language birth and all
        fits, so data-dependent language creation is included in the familywise
        null rather than treated as free post-selection.
        """
        if not (10 <= int(return_limit) <= 100):
            raise ValueError("return_limit must be in [10,100]")
        if not (10 <= int(hypothesis_budget) <= 100):
            raise ValueError("hypothesis_budget must be in [10,100]")
        obs={str(k):np.asarray(v,float) for k,v in observations.items()}
        if target_name not in obs: raise ValueError("target_name missing")
        lengths={len(v) for v in obs.values()}
        if len(lengths)!=1 or not lengths: raise ValueError("all observation columns must have equal length")
        n=next(iter(lengths))
        features=[str(x) for x in (axis_names if axis_names is not None else [k for k in obs if k!=target_name])]
        if len(features)<2: raise ValueError("at least two feature axes are required")
        if len(set(features))!=len(features): raise ValueError("axis_names must be unique")
        if any(name==target_name or name not in obs for name in features): raise ValueError("axis_names contain missing/target column")
        for name in features:
            d=dimensions.get(name)
            if d is None or len(d)!=7: raise ValueError(f"missing 7D dimension for {name}")
        matrix=[[Fraction(int(dimensions[name][i])) for name in features] for i in range(7)]
        ns=_fraction_nullspace(matrix); p=len(ns)
        if p<=1:
            core={"schema":"phi-query-function-form/v2","owner":OWNER_ID,
                  "status":"FUNCTION_FORM_LANE_REQUIRES_P_GT_1","question":question,"target_name":target_name,
                  "axis_names":features,"row_count":int(n),"nullity":int(p),"hypotheses":[],
                  "claim_boundary":{"law_established":False,"function_form_established":False}}
            return {**core,"digest":digest_payload(core)}
        groups=[_canon(v,features) for v in ns]
        pi_columns=[]; basis_rows=[]
        for j,g in enumerate(groups):
            arr=_coordinate(g,obs)
            if np.any(~np.isfinite(arr)):
                raise ValueError(f"non-finite Pi coordinate generated for basis index {j}")
            pi_columns.append(arr)
            basis_rows.append({"pi_index":j,"pi_group":[{"name":name,"exponent":int(exp)} for name,exp in g],
                               "formula":_formula(g)})
        pi_matrix=np.column_stack(pi_columns); y=np.asarray(obs[target_name],float)
        finite=np.isfinite(y)&np.all(np.isfinite(pi_matrix),axis=1)
        if int(finite.sum())<12: raise ValueError("insufficient finite rows for function-form search")
        pi_matrix=pi_matrix[finite]; y=y[finite]
        gids=None if group_ids is None else [str(group_ids[i]) for i in np.flatnonzero(finite)]
        foldset=_folds(len(y),gids)
        total_budget=int(hypothesis_budget)
        # Reserve room for language birth on larger Pi manifolds without changing
        # the old p=4 surface (which has only 45 polynomial specifications).
        polynomial_budget=min(total_budget,60)
        poly_specs=_function_specs(p,hypothesis_budget=max(10,polynomial_budget))
        birth_engine=FunctionLanguageBirthEngine()

        def fit_surface(target: np.ndarray) -> tuple[list[dict[str,Any]],Mapping[str,Any],int,int]:
            fitted: list[dict[str,Any]]=[]
            for coords,degree in poly_specs:
                row=_fit_polynomial_cv(pi_matrix,target,coords,degree,foldset)
                if row is None: continue
                row.update({"representation":"TARGET_AS_POLYNOMIAL_FUNCTION_OF_PI_VECTOR",
                            "function_family":"STANDARDIZED_TOTAL_DEGREE_POLYNOMIAL",
                            "coordinate_formulas":[basis_rows[i]["formula"] for i in coords],
                            "candidate_equation":f"{target_name} = F_deg{degree}("+", ".join(f"Pi_{i+1}" for i in coords)+")",
                            "nullity":int(p),"language_origin":"CURRENT_QUERY_GRAMMAR"})
                row["signature"]=digest_payload({"basis":basis_rows,"coords":list(coords),"degree":int(degree),"target":target_name,"family":"POLYNOMIAL"})
                fitted.append(row)
            fitted.sort(key=lambda r:(r["cross_validated_nrmse"],r["term_count"],r.get("polynomial_degree",99),r["coordinate_indices"],r["signature"]))
            best_poly=next((r for r in fitted if r.get("function_family")=="STANDARDIZED_TOTAL_DEGREE_POLYNOMIAL"),None)
            if best_poly is None:
                birth={"schema":"phi-mathematical-invention-kernel/v1","component":"FUNCTION-LANGUAGE-BIRTH","status":"NO_LANGUAGE_BIRTH_NO_VALID_BASELINE",
                       "generated_languages":[],"claim_boundary":{"function_language_established":False,"world_law_established":False}}
                birth={**birth,"digest":digest_payload(birth)}
                born_specs=()
            else:
                residual=np.asarray(target,float)-np.asarray(best_poly.get("_oof_predictions",[]),float)
                if bool(function_language_birth):
                    birth=birth_engine.diagnose(coordinates=pi_matrix,residuals=residual,
                                                baseline_nrmse=float(best_poly["cross_validated_nrmse"]),
                                                minimum_birth_nrmse=float(language_birth_nrmse))
                else:
                    birth={"schema":"phi-mathematical-invention-kernel/v1","component":"FUNCTION-LANGUAGE-BIRTH","status":"FUNCTION_LANGUAGE_BIRTH_DISABLED_BY_QUERY",
                           "baseline_cross_validated_nrmse":float(best_poly["cross_validated_nrmse"]),"generated_languages":[],
                           "claim_boundary":{"function_language_established":False,"world_law_established":False}}
                    birth={**birth,"digest":digest_payload(birth)}
                remaining=max(0,total_budget-len(poly_specs))
                born_specs=_born_specs(birth,p,remaining)
            for family,coords,variant,language_id in born_specs:
                row=_fit_born_language_cv(pi_matrix,target,coords,family,variant,foldset)
                if row is None: continue
                row.update({"representation":"TARGET_AS_GENERATED_FUNCTION_LANGUAGE_OF_PI_VECTOR",
                            "coordinate_formulas":[basis_rows[i]["formula"] for i in coords],
                            "candidate_equation":f"{target_name} = {language_id}("+", ".join(f"Pi_{i+1}" for i in coords)+")",
                            "nullity":int(p),"language_origin":"RESIDUAL_DRIVEN_MATHEMATICAL_INVENTION",
                            "language_id":language_id})
                row["signature"]=digest_payload({"basis":basis_rows,"coords":list(coords),"family":family,"variant":variant,"target":target_name,"language_id":language_id})
                fitted.append(row)
            fitted.sort(key=lambda r:(r["cross_validated_nrmse"],r["term_count"],str(r.get("function_family")),r["coordinate_indices"],r["signature"]))
            return fitted,birth,len(poly_specs),len(born_specs)

        fitted,language_birth,poly_examined,born_examined=fit_surface(y)
        for i,row in enumerate(fitted,1): row["rank"]=i
        observed_best=min((r["cross_validated_nrmse"] for r in fitted),default=math.inf)
        null_summary=None
        if int(permutation_count)>0:
            rng=np.random.default_rng(int(permutation_seed)); best=[]; replay_counts=[]; replay_birth_counts=[]
            group_arrays=None
            if gids is not None:
                gid_arr=np.asarray(gids,dtype=object)
                group_arrays=[np.flatnonzero(gid_arr==g) for g in dict.fromkeys(gids)]
            for _ in range(int(permutation_count)):
                if group_arrays is None:
                    yp=rng.permutation(y)
                else:
                    yp=np.asarray(y,float).copy()
                    for idx in group_arrays: yp[idx]=rng.permutation(y[idx])
                pf,birth_b,px,bx=fit_surface(yp)
                vals=[float(row["cross_validated_nrmse"]) for row in pf if np.isfinite(row["cross_validated_nrmse"])]
                best.append(min(vals) if vals else math.inf); replay_counts.append(int(px+bx)); replay_birth_counts.append(int(bx))
            finite_null=np.asarray([x for x in best if np.isfinite(x)],float)
            resolution=1.0/(1.0+int(permutation_count))
            empirical_p=(1.0+float(np.sum(finite_null<=observed_best)))/(1.0+len(finite_null)) if len(finite_null) else None
            if resolution>0.05: null_status="INSUFFICIENT_NULL_RESOLUTION"
            elif empirical_p is not None and empirical_p<=0.05: null_status="PASS_FAMILYWISE_PERMUTATION_NULL"
            else: null_status="NOT_REJECTED_BY_FAMILYWISE_PERMUTATION_NULL"
            null_summary={"status":null_status,"permutation_count":int(permutation_count),
                          "minimum_achievable_p":resolution,"entire_function_surface_refit_each_permutation":True,
                          "dynamic_function_language_birth_replayed_each_permutation":True,
                          "structural_hypotheses_replayed_per_permutation_min":min(replay_counts) if replay_counts else 0,
                          "structural_hypotheses_replayed_per_permutation_median":float(np.median(replay_counts)) if replay_counts else 0.0,
                          "structural_hypotheses_replayed_per_permutation_max":max(replay_counts) if replay_counts else 0,
                          "born_language_hypotheses_replayed_per_permutation_max":max(replay_birth_counts) if replay_birth_counts else 0,
                          "exchangeability_scheme":"WITHIN_VALIDATION_GROUP" if gids is not None else "GLOBAL_ROW_PERMUTATION",
                          "exchangeability_assumption_explicit":True,
                          "observed_best_cross_validated_nrmse":observed_best,
                          "permutation_best_median":float(np.median(finite_null)) if len(finite_null) else None,
                          "familywise_empirical_p":empirical_p}
        target_dim=dimensions.get(target_name)
        if target_dim is None: target_dimensional_status="UNKNOWN_TARGET_DIMENSION"
        elif len(target_dim)!=7: raise ValueError(f"target dimension for {target_name} must be 7D when supplied")
        elif all(int(x)==0 for x in target_dim): target_dimensional_status="DIMENSIONLESS_TARGET"
        else: target_dimensional_status="DIMENSIONAL_TARGET_REQUIRES_RESPONSE_SCALE_FOR_UNIVERSAL_COLLAPSE"

        # Internal OOF vectors are evidence for language birth, not part of the
        # public hypothesis contract.  Remove them only after the complete
        # adaptive surface and permutation null have been generated.
        public=[]
        for row in fitted:
            q=dict(row); q.pop("_oof_predictions",None); public.append(q)
        core={"schema":"phi-query-function-form/v2","owner":OWNER_ID,"status":"MULTI_PI_FUNCTION_FORM_SEARCH_COMPLETE",
              "question":question,"target_name":target_name,"target_dimensional_status":target_dimensional_status,
              "row_count":int(len(y)),"axis_names":features,
              "dimension_kernel":{"rank":int(len(features)-p),"nullity":int(p),"basis":basis_rows,
                                  "exact_rational_kernel_authority":True,"basis_is_unique_physical_parameterization":False},
              "validation":{"kind":"LEAVE_ONE_GROUP_OUT" if gids is not None else "DETERMINISTIC_K_FOLD",
                            "fold_count":len(foldset),"group_count":len(set(gids)) if gids is not None else None},
              "function_language_birth":language_birth,
              "search_surface":{"requested_hypothesis_budget":int(hypothesis_budget),
                                "baseline_polynomial_hypotheses_examined_total":int(poly_examined),
                                "born_language_hypotheses_examined_total":int(born_examined),
                                "generated_language_count":len(language_birth.get("generated_languages",[])),
                                "structural_hypotheses_examined_total":int(poly_examined+born_examined),
                                "structural_hypotheses_fit_total":len(fitted),
                                "surface_exhaustive_for_generated_query_tranche":int(poly_examined+born_examined)<int(hypothesis_budget),
                                "finite_query_tranche_is_global_scientific_space_ceiling":False,
                                "display_limit":int(return_limit),"display_limit_is_search_budget":False},
              "hypotheses":public[:int(return_limit)],"permutation_null":null_summary,
              "claim_boundary":{"candidate_is_confirmed_law":False,"function_family_search_is_complete_over_all_mathematics":False,
                                "polynomial_surface_is_a_query_grammar_not_primary_atlas_space":True,
                                "function_language_birth_changes_coordinates":False,
                                "function_language_birth_is_world_mathematical_novelty_claim":False,
                                "whole_surface_null_replays_dynamic_language_birth":True,
                                "selected_cv_score_is_unbiased_post_selection_generalization_estimate":False,
                                "dimensionally_universal_response_claim_requires_dimensionless_or_scaled_target":True,
                                "independent_world_replication_still_required":True}}
        return {**core,"digest":digest_payload(core)}

    def focus_question(self, *, catalog: Any, question: str,
                       named_observables: Sequence[str], quantity_registry: Mapping[str, Mapping[str,Any]] | None = None,
                       expansion_limit: int = 30) -> Mapping[str,Any]:
        """Map explicit observables into a focused quantity neighborhood, fail-closed on symbols."""
        tokens=[str(x).strip() for x in named_observables if str(x).strip()]
        if not tokens: raise ValueError("named_observables are required")
        registry=dict(quantity_registry or {})
        name_to_q={str(v.get('name_ru','')).strip().lower():str(k) for k,v in registry.items() if str(v.get('name_ru','')).strip()}
        symbol_map={}
        for oid,p in sorted(catalog.passports.items()):
            for s in p.symbols:
                sym=str(s.display or '').strip()
                if sym and s.quantity_id:
                    symbol_map.setdefault(sym,set()).add(str(s.quantity_id))
        seed_q=set(); matched=[]; ambiguous=[]; unresolved=[]
        for raw in tokens:
            t=raw.lower(); qid=None; via=None
            if raw in registry:
                qid=raw; via='QUANTITY_ID'
            elif t in name_to_q:
                qid=name_to_q[t]; via='QUANTITY_NAME'
            else:
                qs=sorted(symbol_map.get(raw,set()))
                if len(qs)==1:
                    qid=qs[0]; via='UNAMBIGUOUS_SYMBOL'
                elif len(qs)>1:
                    ambiguous.append({'token':raw,'quantity_ids':qs}); continue
                else:
                    unresolved.append(raw); continue
            seed_q.add(qid); matched.append({'query_token':raw,'quantity_id':qid,'matched_via':via})
        scored={}
        for oid,p in sorted(catalog.passports.items()):
            qids={str(s.quantity_id) for s in p.symbols if s.quantity_id}
            overlap=len(qids & seed_q)
            if overlap<=0: continue
            for s in p.symbols:
                if not s.quantity_id: continue
                qid=str(s.quantity_id)
                row=scored.setdefault(qid,{'quantity_id':qid,'score':0,'source_owner_ids':set(),'symbols':set(),'domain_ids':set()})
                row['score']+=overlap; row['source_owner_ids'].add(oid); row['symbols'].add(str(s.display)); row['domain_ids'].add(str(p.domain_id))
        expanded=[]
        for qid,row in sorted(scored.items(),key=lambda kv:(-kv[1]['score'],kv[0]))[:int(expansion_limit)]:
            expanded.append({'quantity_id':qid,'score':row['score'],'source_owner_ids':sorted(row['source_owner_ids']),
                             'symbols':sorted(row['symbols']),'domain_ids':sorted(row['domain_ids']),'is_seed':qid in seed_q})
        status='QUESTION_FOCUSED_SUBSPACE_READY' if seed_q and not ambiguous else ('AMBIGUOUS_OBSERVABLES_REQUIRE_PASSPORTS' if ambiguous else 'NO_OBSERVABLES_RESOLVED')
        core={'schema':'phi-query-focus/v2','owner':OWNER_ID,'status':status,'question':str(question),
              'named_observables':tokens,'exact_matches':matched,'ambiguous_observables':ambiguous,'unresolved_observables':unresolved,
              'seed_quantity_ids':sorted(seed_q),'expanded_quantity_neighborhood':expanded,
              'expansion_rule':'REGISTERED_OWNER_QUANTITY_COOCCURRENCE_ONLY',
              'claim_boundary':{'ambiguous_symbol_silently_resolved':False,'nlp_inference_of_unmentioned_physics':False,
                                'target_values_read':False,'focused_subspace_is_a_law':False}}
        return {**core,'digest':digest_payload(core)}
