from __future__ import annotations
import itertools, math, re
from fractions import Fraction
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from scipy.optimize import minimize_scalar
from source.phi_compiler_owner import _fraction_nullspace, _fraction_rref, _fraction_json

from contextvars import ContextVar

# Dimensions in this execution are supplied by the Atlas metrology/quantity layer.
# The core owner contains no benchmark-variable dictionary.
_QUANTITY_CONTEXT: ContextVar[dict] = ContextVar('atlas_quantity_context', default={})

def _spec(name):
    ctx=_QUANTITY_CONTEXT.get()
    if name not in ctx:
        raise KeyError(f'missing typed quantity specification for {name!r}')
    return ctx[name]

CANONICAL_DIMENSION_BASIS=("L","M","T","I","Theta","N","J")

def _canonical_dimension_vector(raw):
    """Normalize typed metrology dimensions to the canonical seven-base SI basis.

    Historical adapters used a five-coordinate reduced basis.  They remain
    accepted at the boundary and are padded only for compatibility; all search,
    exact-kernel and born-axis logic operates on the seven-coordinate authority.
    """
    dim=tuple(int(x) for x in raw)
    if len(dim)==7:
        return dim
    if len(dim)==5:
        return dim+(0,0)
    raise ValueError(f"dimension must have 7 canonical coordinates (or legacy 5 at adapter boundary), got {len(dim)}")

def _dim(name): return _canonical_dimension_vector(_spec(name)['dimension'])
def _tags(name): return set(str(x) for x in _spec(name).get('tags', ()))
def _tag(name, tag): return str(tag) in _tags(name)
def _first(names, tag): return next((n for n in names if _tag(n, tag)), None)
def _all(names, tag): return [n for n in names if _tag(n, tag)]
def _field(name, key, default=None): return _spec(name).get(key, default)

ZERO=(0,0,0,0,0,0,0)

@dataclass
class Axis:
    expr:str
    values:np.ndarray
    dim:tuple[int,...]
    kind:str='derived'
    complexity:int=1

    def valid(self):
        return np.all(np.isfinite(self.values)) and np.std(self.values)>1e-14


def canonicalize_conserved_invariant(
    terms, *, trajectory_constant_factors=(), extensive_carrier_powers=None, normalization_anchor=0
):
    """Choose a reproducible physical representative of a conserved quantity.

    Constancy alone identifies an equivalence class: if I is constant along a
    trajectory then f(I) is also constant for every injective monotone f on the
    observed range, and multiplication by a trajectory-constant factor preserves
    constancy.  A physical representative therefore requires an external
    composition principle.  Atlas uses declared extensive carriers when supplied
    and normalizes by one declared anchor term.  Without that composition metadata
    the routine fails closed instead of pretending E and E/m are distinguishable
    from trajectory constancy alone.

    ``terms`` is a sequence of mappings ``{coefficient, powers}``, with integer
    monomial powers.  The routine intentionally does not parse arbitrary formula
    strings; it canonicalizes an already typed additive invariant.
    """
    raw=[dict(t) for t in terms]
    if not raw:
        raise ValueError("at least one additive invariant term is required")
    constants={str(x) for x in trajectory_constant_factors}
    carriers={str(k):int(v) for k,v in dict(extensive_carrier_powers or {}).items() if int(v)}
    if carriers and not set(carriers).issubset(constants):
        raise ValueError("every extensive carrier must be declared trajectory-constant")
    if not carriers:
        payload={
            "status":"CANONICALIZATION_BLOCKED_COMPOSITION_LAW_REQUIRED",
            "observational_equivalence":"I ~ f(I) for injective monotone f on the observed range; I ~ c I for trajectory-constant c",
            "canonical_representative":None,
            "reason":"Trajectory constancy alone cannot choose an extensive invariant over a specific or monotone-transformed invariant.",
        }
        return payload
    normalized=[]
    for term in raw:
        c=Fraction(str(term.get("coefficient",1)))
        powers={str(k):int(v) for k,v in dict(term.get("powers",{})).items() if int(v)}
        for name,power in carriers.items():
            powers[name]=powers.get(name,0)+power
            if powers[name]==0: powers.pop(name)
        normalized.append({"coefficient":c,"powers":powers})
    anchor=int(normalization_anchor)
    if not 0 <= anchor < len(normalized):
        raise ValueError("normalization_anchor is outside the term list")
    anchor_c=normalized[anchor]["coefficient"]
    if anchor_c==0:
        raise ValueError("normalization anchor coefficient cannot be zero")
    if anchor_c < 0:
        anchor_c=-anchor_c
    scale=Fraction(1,1)/anchor_c
    out=[]
    for term in normalized:
        c=term["coefficient"]*scale
        out.append({
            "coefficient":{"numerator":c.numerator,"denominator":c.denominator},
            "powers":dict(sorted(term["powers"].items())),
        })
    payload={
        "status":"CANONICAL_ADDITIVE_EXTENSIVE_INVARIANT",
        "observational_equivalence":"I ~ f(I) for injective monotone f on the observed range; I ~ c I for trajectory-constant c",
        "canonicalization_principle":"DECLARED_COMPOSITION_ADDITIVITY_THEN_ANCHOR_NORMALIZATION",
        "trajectory_constant_factors":sorted(constants),
        "extensive_carrier_powers":dict(sorted(carriers.items())),
        "normalization_anchor":anchor,
        "canonical_terms":out,
        "claim_boundary":{"constancy_alone_selects_canonical_form":False,"composition_law_required":True},
    }
    from .schema import digest_payload
    return {**payload,"digest":digest_payload(payload)}


def exact_dimension_kernel(quantity_names):
    """Exact Buckingham kernel over the canonical 7D metrology authority.

    The arithmetic owner is the existing rational RREF/nullspace implementation
    in ``phi_compiler_owner``; this function only projects typed quantity
    descriptors into that authority and canonicalizes basis vectors for Atlas
    qualification metadata.
    """
    names=tuple(str(n) for n in quantity_names)
    if not names:
        return {"basis":list(CANONICAL_DIMENSION_BASIS),"quantity_names":[],"rank":0,"nullity":0,"groups":[]}
    columns=[_dim(n) for n in names]
    matrix=[[columns[j][i] for j in range(len(names))] for i in range(7)]
    rref,pivots=_fraction_rref(matrix)
    nullspace=_fraction_nullspace(matrix)
    groups=[]
    for vector in nullspace:
        groups.append({names[i]:_fraction_json(v) for i,v in enumerate(vector) if v})
    return {
        "basis":list(CANONICAL_DIMENSION_BASIS),
        "quantity_names":list(names),
        "rank":len(pivots),
        "nullity":len(nullspace),
        "groups":groups,
    }


def safe_pow(x,e):
    with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
        return np.power(x,e)

def monomial_axes(names,X,target_dim,support=4,expmax=3,dimensionless=False,max_axes=4000):
    dims=[np.array(_dim(n),int) for n in names]
    wanted=np.zeros(7,int) if dimensionless else np.array(_canonical_dimension_vector(target_dim),int)
    vals=tuple(i for i in range(-expmax,expmax+1) if i)
    out=[]
    # constant scale for dimensionless target
    if np.all(wanted==0): out.append(Axis('1',np.ones(X.shape[0]),ZERO,'constant',0))
    for k in range(1,min(support,len(names))+1):
      for inds in itertools.combinations(range(len(names)),k):
       for exs in itertools.product(vals,repeat=k):
        dd=np.zeros(7,int)
        for i,e in zip(inds,exs): dd += e*dims[i]
        if not np.array_equal(dd,wanted): continue
        v=np.ones(X.shape[0]); parts=[]; comp=0
        for i,e in zip(inds,exs):
            v*=safe_pow(X[:,i],e); comp+=abs(e)
            parts.append(names[i] if e==1 else f'{names[i]}**{e}')
        if np.all(np.isfinite(v)) and np.std(v)>1e-14:
            out.append(Axis('*'.join(parts),v,tuple(int(x) for x in wanted),'monomial',comp))
            if len(out)>=max_axes: return out
    return dedup_axes(out,max_axes)

def dedup_axes(axes,max_axes=4000):
    out=[]; sigs=set()
    for a in axes:
        v=np.asarray(a.values,float)
        if not np.all(np.isfinite(v)): continue
        s=np.std(v)
        if s<1e-14 and a.expr!='1': continue
        z=(v-np.mean(v))/(s or 1.0)
        sig=tuple(np.round(z[:min(24,len(z))],8))
        # sign-equivalent coordinates are not duplicate because response can be asymmetric
        if sig in sigs: continue
        sigs.add(sig); out.append(a)
        if len(out)>=max_axes: break
    return out

def semantic_axes(names, X):
    """Birth reusable scientific coordinates from typed Atlas descriptors.

    Semantics come from the metrology/state descriptors supplied to the owner,
    never from benchmark variable spellings.  Expressions retain the caller's
    labels only as human-readable projections.
    """
    idx={n:i for i,n in enumerate(names)}; out=[]
    def add(expr,v,dim,kind='semantic',c=2):
        v=np.asarray(v,float)
        if np.all(np.isfinite(v)) and np.std(v)>1e-14: out.append(Axis(expr,v,tuple(dim),kind,c))
    def by_field(field):
        g={}
        for n in names:
            v=_field(n,field)
            if v not in (None,''): g.setdefault(str(v),[]).append(n)
        return g

    # Same-dimension state differences and ratios are generic relations.
    for i,j in itertools.combinations(range(len(names)),2):
        ni,nj=names[i],names[j]; di=_dim(ni); dj=_dim(nj)
        if di==dj:
            add(f'({ni}+{nj})',X[:,i]+X[:,j],di,'typed_additive_state')
            add(f'({ni}-{nj})',X[:,i]-X[:,j],di,'state_difference')
            add(f'({nj}-{ni})',X[:,j]-X[:,i],di,'state_difference')
            with np.errstate(divide='ignore',invalid='ignore'):
                add(f'({ni}/{nj})',X[:,i]/X[:,j],ZERO,'dimensionless_ratio')
                add(f'({nj}/{ni})',X[:,j]/X[:,i],ZERO,'dimensionless_ratio')
                add(f'({ni}/{nj})**2',(X[:,i]/X[:,j])**2,ZERO,'normalized_state_squared',3)
                add(f'({nj}/{ni})**2',(X[:,j]/X[:,i])**2,ZERO,'normalized_state_squared',3)

    # Geometry between repeated states: match components carried by state_id.
    state_groups=by_field('state_id')
    for sa,sb in itertools.combinations(sorted(state_groups),2):
        ca={str(_field(n,'component')):n for n in state_groups[sa] if _field(n,'component') is not None and _tag(n,'position_component')}
        cb={str(_field(n,'component')):n for n in state_groups[sb] if _field(n,'component') is not None and _tag(n,'position_component')}
        common=sorted(set(ca)&set(cb))
        if len(common)>=2:
            pairs=[(ca[c],cb[c]) for c in common]
            if len({_dim(n) for pair in pairs for n in pair})==1:
                d=_dim(pairs[0][0]); d2=sum((X[:,idx[p]]-X[:,idx[q]])**2 for p,q in pairs)
                expr='+'.join(f'({p}-{q})**2' for p,q in pairs)
                add(f'({expr})',d2,tuple(2*z for z in d),'euclidean_distance_squared',2+len(pairs))
                add(f'sqrt({expr})',np.sqrt(np.maximum(d2,0)),d,'euclidean_distance',3+len(pairs))

    # Norms and dot products from typed vector families/components.
    vector_groups=by_field('vector_id')
    for vg,members in vector_groups.items():
        comp={str(_field(n,'component')):n for n in members if _field(n,'component') is not None}
        ns=[comp[k] for k in sorted(comp)]
        if len(ns)>=2 and len({_dim(n) for n in ns})==1:
            d=_dim(ns[0]); q=sum(X[:,idx[n]]**2 for n in ns)
            expr='+'.join(f'{n}**2' for n in ns)
            add(f'({expr})',q,tuple(2*x for x in d),'euclidean_norm_squared',len(ns))
            add(f'sqrt({expr})',np.sqrt(np.maximum(q,0)),d,'euclidean_norm',len(ns)+1)
    for ga,gb in itertools.combinations(sorted(vector_groups),2):
        aa={str(_field(n,'component')):n for n in vector_groups[ga] if _field(n,'component') is not None}
        bb={str(_field(n,'component')):n for n in vector_groups[gb] if _field(n,'component') is not None}
        common=sorted(set(aa)&set(bb))
        if len(common)>=2:
            pairs=[(aa[c],bb[c]) for c in common]
            if len({_dim(n) for p in pairs for n in p})==1:
                d=tuple(2*x for x in _dim(pairs[0][0])); q=sum(X[:,idx[a]]*X[:,idx[b]] for a,b in pairs)
                add('('+'+'.join(f'{a}*{b}' for a,b in pairs)+')',q,d,'dot_product',len(pairs))

    # Barycentric / weighted-state coordinates from generic state and weight tags.
    weights={str(_field(n,'state_id')):n for n in names if _tag(n,'state_weight') and _field(n,'state_id') is not None}
    values_by_family={}
    for n in names:
        sid=_field(n,'state_id'); fam=_field(n,'state_value_family')
        if sid is not None and fam is not None and not _tag(n,'state_weight'):
            values_by_family.setdefault(str(fam),{})[str(sid)]=n
    for fam,vals in values_by_family.items():
        common=sorted(set(vals)&set(weights))
        if len(common)>=2:
            ns=[vals[s] for s in common]; ws=[weights[s] for s in common]
            if len({_dim(n) for n in ns})==1 and len({_dim(w) for w in ws})==1:
                den=sum(X[:,idx[w]] for w in ws)
                with np.errstate(all='ignore'):
                    v=sum(X[:,idx[w]]*X[:,idx[n]] for w,n in zip(ws,ns))/den
                expr='('+'+'.join(f'{w}*{n}' for w,n in zip(ws,ns))+')/('+'+'.join(ws)+')'
                add(expr,v,_dim(ns[0]),'weighted_state_mean',2*len(common)+1)

    # Cross-domain thermal and phase coordinates from quantity semantics.
    kb=_first(names,'boltzmann_constant'); temp=_first(names,'temperature')
    times=_all(names,'time'); freqs=_all(names,'frequency')
    if kb and temp:
        add(f'({kb}*{temp})',X[:,idx[kb]]*X[:,idx[temp]],tuple(a+b for a,b in zip(_dim(kb),_dim(temp))),'thermal_energy',2)
    for fn in freqs:
        for tn in times: add(f'({fn}*{tn})',X[:,idx[fn]]*X[:,idx[tn]],ZERO,'phase_action',2)
    for f1,f2 in itertools.combinations(freqs,2):
        for tn in times: add(f'(({f1}-{f2})*{tn})',(X[:,idx[f1]]-X[:,idx[f2]])*X[:,idx[tn]],ZERO,'detuning_phase',3)
    action=_first(names,'action_constant')
    if action:
        for en in _all(names,'energy'):
            for tn in times:
                with np.errstate(all='ignore'): v=X[:,idx[en]]*X[:,idx[tn]]/X[:,idx[action]]
                add(f'({en}*{tn}/{action})',v,ZERO,'quantum_action_phase',3)
    if action and kb and temp:
        for fn in freqs:
            with np.errstate(all='ignore'): v=X[:,idx[action]]*X[:,idx[fn]]/(X[:,idx[kb]]*X[:,idx[temp]])
            add(f'({action}*{fn}/({kb}*{temp}))',v,ZERO,'thermal_quantum_ratio',4)

    base=list(out)
    for a in base:
        if a.kind=='state_difference':
            for j,n in enumerate(names):
                if _dim(n)==a.dim:
                    with np.errstate(divide='ignore',invalid='ignore'):
                        add(f'({a.expr}/{n})',a.values/X[:,j],ZERO,'normalized_state_difference',a.complexity+1)
                        add(f'({a.expr}/{n})**2',(a.values/X[:,j])**2,ZERO,'normalized_state_squared',a.complexity+2)

    periodic=[n for n in names if _tag(n,'periodic_angle') or _tag(n,'phase_state')]
    for an in periodic:
        ai=idx[an]; add(an,X[:,ai],ZERO,'periodic_angle',1)
        for dn in names:
            if dn==an or _dim(dn)!=ZERO: continue
            add(f'({dn}*{an})',X[:,idx[dn]]*X[:,ai],ZERO,'phase_coupling',2)
            with np.errstate(all='ignore'):
                z=X[:,idx[dn]]*np.sin(X[:,ai]); zc=X[:,idx[dn]]*np.cos(X[:,ai])
            add(f'({dn}*sin({an}))',z,ZERO,'phase_transfer',3)
            add(f'({dn}*cos({an}))',zc,ZERO,'phase_transfer',3)
            if np.all(np.abs(z)<=1+1e-12): add(f'asin({dn}*sin({an}))',np.arcsin(np.clip(z,-1,1)),ZERO,'inverse_phase_transfer',4)

    # Low-order periodic modulation of two dimensionless state coordinates.
    # This is a reusable axis family; it is activated by a periodic state and
    # does not encode any benchmark target expression.
    dimless_states=[n for n in names if _dim(n)==ZERO and n not in periodic]
    for an in periodic:
        pv=X[:,idx[an]]
        for da,db in itertools.combinations(dimless_states,2):
            vv=X[:,idx[da]]*X[:,idx[db]]
            add(f'({da}*{db}*cos({an}))',vv*np.cos(pv),ZERO,'periodic_state_pair_modulation',4)
            add(f'({da}*{db}*sin({an}))',vv*np.sin(pv),ZERO,'periodic_state_pair_modulation',4)

    # Coherent state coordinates are generic same-dimension two-state observables.
    for i,j in itertools.combinations(range(len(names)),2):
        ni,nj=names[i],names[j]; di=_dim(ni)
        if di==ZERO or di!=_dim(nj): continue
        prod=X[:,i]*X[:,j]
        if np.all(prod>=0):
            root=np.sqrt(prod); add(f'sqrt({ni}*{nj})',root,di,'coherent_cross_magnitude',3)
            for ph in periodic:
                pv=X[:,idx[ph]]
                add(f'sqrt({ni}*{nj})*cos({ph})',root*np.cos(pv),di,'coherent_phase_projection',4)
                add(f'sqrt({ni}*{nj})*sin({ph})',root*np.sin(pv),di,'coherent_phase_projection',4)
                add(f'({ni}+{nj}+2*sqrt({ni}*{nj})*cos({ph}))',X[:,i]+X[:,j]+2*root*np.cos(pv),di,'coherent_superposition_intensity',6)

    # Relativistic coordinates use typed roles rather than the spelling c/x/t.
    invariant=_first(names,'invariant_speed'); tvar=_first(names,'time'); xvar=_first(names,'position_scalar')
    if invariant:
        cv=X[:,idx[invariant]]; vel=[n for n in names if n!=invariant and _tag(n,'velocity')]
        for vn in vel:
            with np.errstate(all='ignore'): beta=X[:,idx[vn]]/cv
            add(f'({vn}/{invariant})',beta,ZERO,'relativistic_beta',2)
            add(f'({vn}**2/{invariant}**2)',beta**2,ZERO,'relativistic_beta_squared',3)
        for va,vb in itertools.combinations(vel,2):
            with np.errstate(all='ignore'): z=X[:,idx[va]]*X[:,idx[vb]]/(cv*cv)
            add(f'({va}*{vb}/{invariant}**2)',z,ZERO,'relativistic_pair_coupling',3)
        if tvar and xvar:
            tv=X[:,idx[tvar]]; xv=X[:,idx[xvar]]
            for vn in vel:
                vv=X[:,idx[vn]]
                with np.errstate(all='ignore'):
                    beta2=(vv/cv)**2; gamma=1/np.sqrt(np.abs(1-beta2)); t_mix=tv-vv*xv/(cv*cv); x_mix=xv-vv*tv
                add(f'({tvar}-{vn}*{xvar}/{invariant}**2)',t_mix,_dim(tvar),'spacetime_mixed_time',4)
                add(f'({xvar}-{vn}*{tvar})',x_mix,_dim(xvar),'spacetime_mixed_length',3)
                add(f'({tvar}-{vn}*{xvar}/{invariant}**2)/sqrt(abs(1-{vn}**2/{invariant}**2))',t_mix*gamma,_dim(tvar),'relativistic_spacetime_coordinate',7)
                add(f'({xvar}-{vn}*{tvar})/sqrt(abs(1-{vn}**2/{invariant}**2))',x_mix*gamma,_dim(xvar),'relativistic_spacetime_coordinate',6)

    # Resonance coordinates from typed frequencies.
    for fa,fb in itertools.combinations(freqs,2):
        va=X[:,idx[fa]]; vb=X[:,idx[fb]]; d2=va*va-vb*vb
        add(f'({fa}**2-{fb}**2)',d2,tuple(2*x for x in _dim(fa)),'squared_frequency_detuning',3)
        add(f'({fb}**2-{fa}**2)',-d2,tuple(2*x for x in _dim(fa)),'squared_frequency_detuning',3)
        with np.errstate(all='ignore'):
            add(f'({fa}**2/({fa}**2-{fb}**2))',va*va/d2,ZERO,'normalized_resonance_coordinate',5)
            add(f'({fb}**2/({fb}**2-{fa}**2))',vb*vb/(-d2),ZERO,'normalized_resonance_coordinate',5)

    # Cylindrical/spherical relations from a vector family and a radial magnitude.
    radial=_first(names,'radial_length')
    for vg,members in vector_groups.items():
        comp={str(_field(n,'component')):n for n in members if _field(n,'component') is not None}
        if 'x' in comp and 'y' in comp:
            xa,ya=comp['x'],comp['y']; rho2=X[:,idx[xa]]**2+X[:,idx[ya]]**2; rho=np.sqrt(np.maximum(rho2,0))
            add(f'sqrt({xa}**2+{ya}**2)',rho,_dim(xa),'transverse_radius',3)
            if radial:
                rv=X[:,idx[radial]]
                with np.errstate(all='ignore'): add(f'(sqrt({xa}**2+{ya}**2)/{radial})',rho/rv,ZERO,'transverse_direction_cosine',4)
                if 'z' in comp:
                    za=comp['z']
                    with np.errstate(all='ignore'):
                        add(f'({za}/{radial})',X[:,idx[za]]/rv,ZERO,'axial_direction_cosine',2)
                        add(f'({za}*sqrt({xa}**2+{ya}**2)/{radial}**2)',X[:,idx[za]]*rho/(rv**2),ZERO,'axial_transverse_geometry',5)

    # Statistical orientational coupling from typed ingredients.
    dip=_first(names,'dipole_moment'); field=_first(names,'electric_field'); density=_first(names,'state_density')
    if kb and temp and dip and field:
        with np.errstate(all='ignore'): eta=X[:,idx[dip]]*X[:,idx[field]]/(X[:,idx[kb]]*X[:,idx[temp]])
        add(f'({dip}*{field}/({kb}*{temp}))',eta,ZERO,'thermal_field_coupling',4)
        for an in periodic:
            av=X[:,idx[an]]
            add(f'({dip}*{field}*cos({an})/({kb}*{temp}))',eta*np.cos(av),ZERO,'orientational_thermal_coupling',6)
            add(f'({dip}*{field}*sin({an})/({kb}*{temp}))',eta*np.sin(av),ZERO,'orientational_thermal_coupling',6)
            if density:
                add(f'({density}*{dip}*{field}*cos({an})/({kb}*{temp}))',X[:,idx[density]]*eta*np.cos(av),ZERO,'orientational_state_density_response',7)
                add(f'({density}*{dip}*{field}*sin({an})/({kb}*{temp}))',X[:,idx[density]]*eta*np.sin(av),ZERO,'orientational_state_density_response',7)

    phase_like=[a for a in list(out) if a.dim==ZERO and a.kind in {'periodic_angle','phase_action','detuning_phase','quantum_action_phase','phase_coupling'}]
    for a in phase_like:
        z=a.values
        add(f'sin({a.expr})',np.sin(z),ZERO,'periodic_response',a.complexity+1)
        add(f'cos({a.expr})',np.cos(z),ZERO,'periodic_response',a.complexity+1)
        add(f'sin({a.expr})**2',np.sin(z)**2,ZERO,'periodic_response',a.complexity+2)
        add(f'cos({a.expr})**2',np.cos(z)**2,ZERO,'periodic_response',a.complexity+2)
        add(f'sin({a.expr})*cos({a.expr})',np.sin(z)*np.cos(z),ZERO,'periodic_response',a.complexity+2)

    angle_axes=[Axis(n,X[:,idx[n]],ZERO,'angle',1) for n in periodic]
    angle_axes += [a for a in out if a.dim==ZERO and a.kind=='state_difference']
    for i,j in itertools.combinations(range(len(names)),2):
        if _dim(names[i])!=_dim(names[j]) or _dim(names[i])==ZERO: continue
        aa,bb=X[:,i],X[:,j]; dim=_dim(names[i])
        for ph in angle_axes[:8]:
            with np.errstate(invalid='ignore'):
                rad=aa*aa+bb*bb-2*aa*bb*np.cos(ph.values)
                add(f'sqrt({names[i]}**2+{names[j]}**2-2*{names[i]}*{names[j]}*cos({ph.expr}))',np.sqrt(np.maximum(rad,0)),dim,'cosine_law',7)
    born=list(out)
    for a in born:
        if a.dim==ZERO and a.kind!='angle':
            for e in (2,3,-1,-2):
                with np.errstate(all='ignore'): v=safe_pow(a.values,e)
                add(f'({a.expr})**{e}',v,ZERO,'dimensionless_response_power',a.complexity+abs(e))
    return dedup_axes(out,1800)

def simplify_parameter(k,obj):
    """Compress a response parameter only when the observations preserve the fit.

    Candidate constants are generic low-description-length rationals and rational
    multiples of pi. The target expression is never inspected.
    """
    from fractions import Fraction
    if not math.isfinite(k): return float(k)
    base=float(obj(k))
    candidates=[(100.0,float(k))]
    r=Fraction(k).limit_denominator(32)
    candidates.append((abs(r.numerator)+abs(r.denominator),float(r)))
    rp=Fraction(k/math.pi).limit_denominator(32)
    candidates.append((abs(rp.numerator)+abs(rp.denominator)+2,math.pi*float(rp)))
    tol=max(base*1.00001,1e-11)
    feasible=[]
    for complexity,q in candidates:
        try:e=float(obj(q))
        except Exception:continue
        if math.isfinite(e) and e<=tol:
            feasible.append((complexity,e,abs(q),q))
    if feasible:
        return float(min(feasible)[3])
    return float(k)

def response_candidates(g:Axis, scale:Axis, y:np.ndarray, max_keep=6, calibrate=True, expensive=False):
    """Fit response coordinates from observations only.

    Cheap calibrated families use algebraic linearizations (log, reciprocal,
    inverse-square) rather than a per-pair optimizer. Oscillatory calibration is
    activated only for a small residual-selected subset by ``expensive=True``.
    """
    gv=np.asarray(g.values,float); sv=np.asarray(scale.values,float)
    mask=np.isfinite(gv)&np.isfinite(sv)&np.isfinite(y)&(np.abs(sv)>1e-14)
    if mask.sum()<12: return []
    scale_y=float(np.std(y[mask])) or 1.0
    scored=[]
    def push(expr,r,kind='response',extra=1):
        feat=sv*np.asarray(r,float); m=mask&np.isfinite(feat)
        if m.sum()<12 or np.std(feat[m])<1e-14:return
        a=float(np.dot(feat[m],y[m])/max(np.dot(feat[m],feat[m]),1e-30))
        err=float(np.sqrt(np.mean((y[m]-a*feat[m])**2))/scale_y)
        scored.append((err,Axis(f'({scale.expr})*({expr})',feat,scale.dim,kind,scale.complexity+g.complexity+extra)))
    with np.errstate(all='ignore'):
        direct=[
         (f'({g.expr})',gv),(f'1/({g.expr})',1/gv),(f'sqrt(abs({g.expr}))',np.sqrt(np.abs(gv))),(f'1/sqrt(abs({g.expr}))',1/np.sqrt(np.abs(gv))),
         (f'exp({g.expr})',np.exp(np.clip(gv,-80,80))),(f'exp(-({g.expr}))',np.exp(np.clip(-gv,-80,80))),
         (f'log(abs({g.expr}))',np.log(np.abs(gv))),(f'sin({g.expr})',np.sin(gv)),(f'cos({g.expr})',np.cos(gv)),
         (f'sin({g.expr})**2',np.sin(gv)**2),(f'cos({g.expr})**2',np.cos(gv)**2),(f'tanh({g.expr})',np.tanh(gv)),
         (f'asin({g.expr})',np.arcsin(np.clip(gv,-1,1))),(f'1-cos({g.expr})',1-np.cos(gv)),
         (f'1/(1+({g.expr}))',1/(1+gv)),(f'1/(1-({g.expr}))',1/(1-gv)),(f'1/(1+({g.expr}))**2',1/(1+gv)**2),(f'1/(1-({g.expr}))**2',1/(1-gv)**2),
         (f'1/sqrt(abs(1-({g.expr})))',1/np.sqrt(np.abs(1-gv))),(f'1/sqrt(abs(1+({g.expr})))',1/np.sqrt(np.abs(1+gv))),
         (f'sqrt(abs(1-({g.expr})))',np.sqrt(np.abs(1-gv))),(f'sqrt(abs(1+({g.expr})))',np.sqrt(np.abs(1+gv))),
         (f'1/(exp({g.expr})-1)',1/np.expm1(np.clip(gv,-80,80))),(f'1/(2*cosh({g.expr}))',1/(2*np.cosh(np.clip(gv,-40,40)))),
         (f'(sin({g.expr})/({g.expr}))**2',(np.sin(gv)/np.where(np.abs(gv)>1e-12,gv,1.0))**2),
        ]
    for ex,r in direct: push(ex,r)

    if calibrate:
        gm=gv[mask]; sm=sv[mask]; ym=y[mask]
        # response ratio; amplitude is absorbed by the outer coefficient.
        rr=np.full_like(ym,np.nan)
        ok=np.abs(sm)>1e-14; rr[ok]=ym[ok]/sm[ok]
        def linear_slope(x,z):
            m=np.isfinite(x)&np.isfinite(z)
            if m.sum()<10 or np.std(x[m])<1e-14:return None
            A=np.column_stack([np.ones(m.sum()),x[m]])
            try:b=np.linalg.lstsq(A,z[m],rcond=None)[0]
            except Exception:return None
            return float(b[0]),float(b[1])
        # exp(k g): log|r| = a + k g, valid when r does not cross zero.
        same_sign=np.all(rr[np.isfinite(rr)]>0) or np.all(rr[np.isfinite(rr)]<0)
        if same_sign:
            z=np.log(np.abs(rr)); ab=linear_slope(gm,z)
            if ab is not None:
                _,k=ab
                if math.isfinite(k) and abs(k)<100:
                    with np.errstate(all='ignore'): push(f'exp(({k:.16g})*({g.expr}))',np.exp(np.clip(k*gv,-80,80)),'calibrated_response',2)
        # reciprocal affine r=A/(1+k g): 1/r = A0 + B0 g.
        with np.errstate(all='ignore'):
            z=1/rr
        ab=linear_slope(gm,z)
        if ab is not None and abs(ab[0])>1e-14:
            k=ab[1]/ab[0]
            if math.isfinite(k) and abs(k)<100:
                with np.errstate(all='ignore'): push(f'1/(1+({k:.16g})*({g.expr}))',1/(1+k*gv),'calibrated_response',2)
        # reciprocal-square affine: 1/sqrt(|r|) is affine in g up to amplitude.
        with np.errstate(all='ignore'): z=1/np.sqrt(np.abs(rr))
        ab=linear_slope(gm,z)
        if ab is not None and abs(ab[0])>1e-14:
            k=ab[1]/ab[0]
            if math.isfinite(k) and abs(k)<100:
                with np.errstate(all='ignore'): push(f'1/(1+({k:.16g})*({g.expr}))**2',1/(1+k*gv)**2,'calibrated_response',2)
        # inverse sqrt: 1/r^2 affine; sqrt: r^2 affine. Sign belongs to amplitude.
        with np.errstate(all='ignore'): z=1/(rr*rr)
        ab=linear_slope(gm,z)
        if ab is not None and abs(ab[0])>1e-14:
            k=ab[1]/ab[0]
            if math.isfinite(k) and abs(k)<100:
                with np.errstate(all='ignore'): push(f'1/sqrt(abs(1+({k:.16g})*({g.expr})))',1/np.sqrt(np.abs(1+k*gv)),'calibrated_response',2)
        with np.errstate(all='ignore'): z=rr*rr
        ab=linear_slope(gm,z)
        if ab is not None and abs(ab[0])>1e-14:
            k=ab[1]/ab[0]
            if math.isfinite(k) and abs(k)<100:
                with np.errstate(all='ignore'): push(f'sqrt(abs(1+({k:.16g})*({g.expr})))',np.sqrt(np.abs(1+k*gv)),'calibrated_response',2)
        # Saturating rational response with an additive baseline:
        # y ~= A*scale + B*scale*g/(1+k*g).  The shape parameter k is inferred
        # from observations; the additive coefficients are left to the sparse
        # selector.  Restrict to the dimensionless baseline scale to avoid a
        # combinatorial family explosion.
        if scale.expr=='1':
            gm0=gm; ym0=ym
            def rat_obj(k):
                with np.errstate(all='ignore'):
                    den=1.0+float(k)*gm0
                    r=gm0/den
                ok=np.isfinite(r)&(np.abs(den)>1e-8)
                if ok.sum()<12:return 1e6
                A=np.column_stack([np.ones(ok.sum()),r[ok]])
                try:coef=np.linalg.lstsq(A,ym0[ok],rcond=None)[0]
                except Exception:return 1e6
                pred=A@coef
                return float(np.sqrt(np.mean((ym0[ok]-pred)**2))/scale_y)
            grid=np.linspace(-4.0,4.0,65); vals=np.array([rat_obj(k) for k in grid]); bi=int(np.nanargmin(vals))
            lo=grid[max(0,bi-1)]; hi=grid[min(len(grid)-1,bi+1)]
            try: rr0=minimize_scalar(rat_obj,bounds=(lo,hi),method='bounded',options={'xatol':1e-13,'maxiter':120}); kr=float(rr0.x)
            except Exception: kr=float(grid[bi])
            kr=simplify_parameter(kr,rat_obj)
            with np.errstate(all='ignore'):
                den=1.0+kr*gv; r=gv/den
            push(f'({g.expr})/(1+({kr:.16g})*({g.expr}))',r,'calibrated_rational_response',3)

        # power response |g|^k by log-linearization.
        with np.errstate(all='ignore'):
            lx=np.log(np.abs(gm)); lz=np.log(np.abs(rr))
        ab=linear_slope(lx,lz)
        if ab is not None:
            k=ab[1]
            if math.isfinite(k) and abs(k)<12:
                with np.errstate(all='ignore'): push(f'abs({g.expr})**({k:.16g})',np.abs(gv)**k,'calibrated_response',2)

    if expensive:
        # Only oscillatory/nonlinear phase calibration needs a one-dimensional search.
        gm=gv[mask]; sm=sv[mask]; ym=y[mask]
        fams=[
          ('sin',lambda x,k:np.sin(k*x)),('cos',lambda x,k:np.cos(k*x)),('sin2',lambda x,k:np.sin(k*x)**2),
          ('tanh',lambda x,k:np.tanh(k*x)),('asin',lambda x,k:np.arcsin(np.clip(k*x,-1,1))),
          ('invexpm1',lambda x,k:1/np.expm1(np.clip(k*x,-80,80))),
          ('inv2cosh',lambda x,k:1/(2*np.cosh(np.clip(k*x,-40,40)))),
          ('sinc2',lambda x,k:(np.sin(k*x)/np.where(np.abs(k*x)>1e-12,k*x,1.0))**2),
        ]
        for label,fn in fams:
            def obj(k):
                with np.errstate(all='ignore'):
                    try: feat=sm*fn(gm,float(k))
                    except Exception:return 1e6
                m=np.isfinite(feat)
                if m.sum()<12 or np.std(feat[m])<1e-14:return 1e6
                a=float(np.dot(feat[m],ym[m])/max(np.dot(feat[m],feat[m]),1e-30))
                return float(np.sqrt(np.mean((ym[m]-a*feat[m])**2))/scale_y)
            grid=np.linspace(-12,12,49); vals=np.array([obj(k) for k in grid]); bi=int(np.nanargmin(vals))
            lo=grid[max(0,bi-1)]; hi=grid[min(len(grid)-1,bi+1)]
            try:res=minimize_scalar(obj,bounds=(lo,hi),method='bounded',options={'xatol':1e-13,'maxiter':160}); k=float(res.x)
            except Exception:k=float(grid[bi])
            k=simplify_parameter(k,obj)
            with np.errstate(all='ignore'):
                try:r=fn(gv,k)
                except Exception:continue
            ex={'sin':f'sin(({k:.16g})*({g.expr}))','cos':f'cos(({k:.16g})*({g.expr}))','sin2':f'sin(({k:.16g})*({g.expr}))**2',
                'tanh':f'tanh(({k:.16g})*({g.expr}))','asin':f'asin(({k:.16g})*({g.expr}))','invexpm1':f'1/(exp(({k:.16g})*({g.expr}))-1)',
                'inv2cosh':f'1/(2*cosh(({k:.16g})*({g.expr})))','sinc2':f'(sin(({k:.16g})*({g.expr}))/(({k:.16g})*({g.expr})))**2'}[label]
            push(ex,r,'calibrated_phase_response',3)
    scored.sort(key=lambda x:(x[0],x[1].complexity,x[1].expr))
    return [a for _,a in scored[:max_keep]]

def best_pair_fast(features:Sequence[Axis],y:np.ndarray,tol=1e-10):
    """Find a two-coordinate additive law without trusting normal-equation SSE.

    The Gram-system score is used only as a cheap proposal mechanism. Every
    competitive pair is re-solved by rank-aware least squares and accepted only
    from its *actual* residual on the frozen observations. This prevents false
    near-zero SSE caused by catastrophic cancellation in nearly-collinear
    scientific coordinates.
    """
    if len(features)<2:return None
    keep=[i for i,a in enumerate(features) if np.all(np.isfinite(a.values)) and np.std(a.values)>1e-14]
    if len(keep)<2:return None
    F=np.column_stack([features[i].values for i in keep]); yy=np.asarray(y,float); sy=float(np.std(yy)) or 1.0
    sc=np.sqrt(np.mean(F*F,axis=0)); good=sc>1e-14; F=F[:,good]; keep=[k for k,g in zip(keep,good) if g]; sc=sc[good]
    if F.shape[1]<2:return None
    Z=F/sc; G=Z.T@Z; d=Z.T@yy
    best=None; m=Z.shape[1]
    diag=np.diag(G)
    for i in range(m-1):
        a=G[i,i]; b=G[i,i+1:]; c=diag[i+1:]; di=d[i]; dj=d[i+1:]
        det=a*c-b*b; ok=np.abs(det)>1e-12*max(abs(a),1.0)*np.maximum(np.abs(c),1.0)
        if not np.any(ok):continue
        bi=np.full_like(dj,np.nan,dtype=float); bj=np.full_like(dj,np.nan,dtype=float)
        bi[ok]=(di*c[ok]-b[ok]*dj[ok])/det[ok]
        bj[ok]=(a*dj[ok]-b[ok]*di)/det[ok]
        # Proposal ordering from the normal equations only. Validate several
        # proposals explicitly so ill-conditioning cannot terminate the search.
        y2=float(yy@yy); gain=di*bi+dj*bj
        approx=np.sqrt(np.maximum(y2-gain,0.0)/len(yy))/sy
        approx[~np.isfinite(approx)]=np.inf
        cand_rel=np.argsort(approx)[:min(8,len(approx))]
        for jrel in cand_rel:
            if not ok[jrel]:continue
            j=i+1+int(jrel)
            A=Z[:,[i,j]]
            try:
                coef_z,resid,rank,_=np.linalg.lstsq(A,yy,rcond=None)
            except Exception:
                continue
            if rank<2:continue
            pred=A@coef_z
            e=float(np.sqrt(np.mean((yy-pred)**2))/sy)
            oi,oj=keep[i],keep[j]
            coef=(float(coef_z[0]/sc[i]),float(coef_z[1]/sc[j]))
            comp=features[oi].complexity+features[oj].complexity
            row=(e,comp,oi,oj,coef)
            if best is None or row[:2]<best[:2]:best=row
            if e<tol:
                return {'nrmse':e,'indices':[oi,oj],'coefs':list(coef),'features':[features[oi],features[oj]]}
    if best is None:return None
    e,_,oi,oj,coef=best
    return {'nrmse':e,'indices':[oi,oj],'coefs':list(coef),'features':[features[oi],features[oj]]}

def exact_sparse_pair(features:Sequence[Axis],y:np.ndarray,top=140,tol=1e-10):
    if not features:return None
    sy=float(np.std(y)) or 1.0
    ranked=[]
    for i,a in enumerate(features):
        v=a.values; m=np.isfinite(v)&np.isfinite(y)
        if m.sum()<12 or np.std(v[m])<1e-14:continue
        c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30)); e=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy)
        ranked.append((e,a.complexity,i))
    ranked.sort(); ids=[r[2] for r in ranked[:top]]
    best=None
    for ia in range(len(ids)):
      a=ids[ia]
      for ib in range(ia+1,len(ids)):
        b=ids[ib]; A=np.column_stack([features[a].values,features[b].values]); m=np.all(np.isfinite(A),axis=1)&np.isfinite(y)
        if m.sum()<12:continue
        try:coef=np.linalg.lstsq(A[m],y[m],rcond=None)[0]
        except Exception:continue
        e=float(np.sqrt(np.mean((y[m]-A[m]@coef)**2))/sy)
        row=(e,features[a].complexity+features[b].complexity,a,b,coef)
        if best is None or row[:2]<best[:2]:best=row
        if e<tol:
            return {'nrmse':e,'indices':[a,b],'coefs':coef.tolist(),'features':[features[a],features[b]]}
    return None

def greedy_sparse(features:Sequence[Axis],y:np.ndarray,max_terms=8):
    # center not added: physical target features carry target dimension; coefficients can include constants.
    if not features: return None
    F=np.column_stack([a.values for a in features]); ok=np.all(np.isfinite(F),axis=1)&np.isfinite(y)
    F=F[ok]; yy=y[ok]
    if len(yy)<12:return None
    sy=float(np.std(yy)) or 1.0
    # normalize columns, keep independent signatures
    scales=np.sqrt(np.mean(F*F,axis=0)); valid=scales>1e-14; idx=np.where(valid)[0]; F=F[:,valid]; scales=scales[valid]
    Z=F/scales
    selected=[]; residual=yy.copy(); best=None
    available=list(range(Z.shape[1]))
    for step in range(max_terms):
        corr=np.abs(Z.T@residual); corr[selected]=-np.inf
        # try top correlations because collinearity can make the single top poor
        top=np.argsort(corr)[-min(24,len(corr)):][::-1]
        local=None
        for j in top:
            cand=selected+[int(j)]; A=Z[:,cand]
            try:b,*_=np.linalg.lstsq(A,yy,rcond=None)
            except Exception:continue
            pred=A@b; err=float(np.sqrt(np.mean((yy-pred)**2))/sy)
            score=(err,len(cand))
            if local is None or score<local[0]:local=(score,cand,b,pred)
        if local is None:break
        score,selected,b,pred=local; residual=yy-pred
        if best is None or score<best[0]:best=(score,list(selected),b.copy(),pred.copy())
        if score[0]<1e-11:break
    if best is None:return None
    score,sel,b,pred=best
    orig_idx=idx[np.array(sel)]
    coefs=b/scales[np.array(sel)]
    return {'nrmse':score[0],'indices':orig_idx.tolist(),'coefs':coefs.tolist(),'features':[features[i] for i in orig_idx]}

def _shape_responses(g:Axis):
    z=np.asarray(g.values,float); out=[]
    def add(expr,v,c=1):
        v=np.asarray(v,float)
        if np.all(np.isfinite(v)) and np.std(v)>1e-14: out.append((expr,v,g.complexity+c))
    with np.errstate(all='ignore'):
        add(f'({g.expr})',z,0); add(f'1/({g.expr})',1/z)
        add(f'sqrt(abs({g.expr}))',np.sqrt(np.abs(z)))
        add(f'1/sqrt(abs({g.expr}))',1/np.sqrt(np.abs(z)))
        add(f'exp({g.expr})',np.exp(np.clip(z,-80,80)))
        add(f'exp(-({g.expr}))',np.exp(np.clip(-z,-80,80)))
        add(f'sin({g.expr})',np.sin(z)); add(f'cos({g.expr})',np.cos(z))
        add(f'sin({g.expr})**2',np.sin(z)**2,2); add(f'cos({g.expr})**2',np.cos(z)**2,2)
        add(f'1/(1+({g.expr}))',1/(1+z)); add(f'1/(1-({g.expr}))',1/(1-z))
        add(f'1/(1+({g.expr}))**2',1/(1+z)**2,2); add(f'1/(1-({g.expr}))**2',1/(1-z)**2,2)
        add(f'1/sqrt(abs(1-({g.expr})))',1/np.sqrt(np.abs(1-z)),2)
        add(f'1/sqrt(abs(1+({g.expr})))',1/np.sqrt(np.abs(1+z)),2)
        add(f'1/(exp({g.expr})-1)',1/np.expm1(np.clip(z,-80,80)),2)
        add(f'(sin({g.expr})/({g.expr}))**2',(np.sin(z)/np.where(np.abs(z)>1e-12,z,1.0))**2,2)
    return out

def exact_response_fallback(scales,groups,y,tol=1e-9):
    """Residual-only fallback over typed scientific response coordinates.

    It opens no equation-specific grammar: only low-complexity dimensionless
    groups modulating target-dimensional scales are tested.  A result is
    returned only when the frozen observations are closed to ``tol``.
    """
    sy=float(np.std(y)) or 1.0
    ss=sorted(scales,key=lambda a:(a.complexity,a.expr))[:180]
    gg=sorted([g for g in groups if g.complexity<=6],key=lambda a:(a.complexity,a.expr))[:420]
    best=None
    for g in gg:
        for rex,rv,rc in _shape_responses(g):
            for s0 in ss:
                with np.errstate(all='ignore'): f=s0.values*rv
                if not np.all(np.isfinite(f)) or np.std(f)<1e-14:continue
                c=float(np.dot(f,y)/max(np.dot(f,f),1e-30)); e=float(np.sqrt(np.mean((y-c*f)**2))/sy)
                row=(e,s0.complexity+rc,s0,g,rex,c,f)
                if best is None or row[:2]<best[:2]:best=row
                if e<tol:
                    a=Axis(f'({s0.expr})*({rex})',f,s0.dim,'residual_activated_response',s0.complexity+rc)
                    return {'nrmse':e,'indices':[0],'coefs':[c],'features':[a]}
    return None

def shared_response_pair_fallback(scales,groups,y,tol=1e-9):
    """Search two typed additive contributions sharing one born response."""
    sy=float(np.std(y)) or 1.0
    ss=sorted(scales,key=lambda a:(a.complexity,a.expr))[:120]
    gg=sorted([g for g in groups if g.kind!='monomial' and g.complexity<=5],key=lambda a:(a.complexity,a.expr))[:120]
    for g in gg:
        for rex,rv,rc in _shape_responses(g):
            F=[]; meta=[]
            for s0 in ss:
                f=s0.values*rv
                if np.all(np.isfinite(f)) and np.std(f)>1e-14:
                    F.append(f);meta.append((s0,rex,rc))
            if len(F)<2:continue
            feats=[Axis(f'({m[0].expr})*({m[1]})',v,m[0].dim,'shared_response_contribution',m[0].complexity+m[2]) for v,m in zip(F,meta)]
            r=best_pair_fast(feats,y,tol=tol)
            if r is not None and r['nrmse']<tol:return r
    return None

def baseline_modulated_fallback(scales,groups,y,tol=1e-9):
    """Find baseline + dimensionless modulation from independently born axes."""
    sy=float(np.std(y)) or 1.0
    base=sorted(scales,key=lambda a:(a.complexity,a.expr))[:100]
    sem=[g for g in groups if g.kind!='monomial' and g.complexity<=5][:120]
    low=[g for g in groups if g.complexity<=4][:180]
    for s0 in base:
        for a in sem:
            for b in low:
                if a.expr==b.expr:continue
                with np.errstate(all='ignore'): f=s0.values*a.values*b.values
                if not np.all(np.isfinite(f)) or np.std(f)<1e-14:continue
                A=np.column_stack([s0.values,f]);
                if not np.all(np.isfinite(A)):continue
                try:coef,_,rank,_=np.linalg.lstsq(A,y,rcond=None)
                except Exception:continue
                if rank<2:continue
                e=float(np.sqrt(np.mean((y-A@coef)**2))/sy)
                if e<tol:
                    f2=Axis(f'({s0.expr})*({a.expr})*({b.expr})',f,s0.dim,'residual_semantic_coupling',s0.complexity+a.complexity+b.complexity+1)
                    return {'nrmse':e,'indices':[0,1],'coefs':coef.tolist(),'features':[s0,f2]}
    return None

def rational_baseline_fallback(scales,groups,y,tol=1e-9):
    """Infer a saturating dimensionless response with an additive baseline."""
    ones=[s for s in scales if s.expr=='1']
    if not ones:return None
    sy=float(np.std(y)) or 1.0; one=ones[0]
    pool=[g for g in groups if g.complexity<=5]
    yy=np.asarray(y,float); syy=float(np.std(yy)) or 1.0
    def gscore(g):
        v=np.asarray(g.values,float); m=np.isfinite(v)&np.isfinite(yy)
        if m.sum()<12 or np.std(v[m])<1e-14:return (1e9,g.complexity,g.expr)
        z=(v[m]-np.mean(v[m]))/(np.std(v[m]) or 1.0); q=(yy[m]-np.mean(yy[m]))/(np.std(yy[m]) or 1.0)
        return (-abs(float(np.mean(z*q))),g.complexity,g.expr)
    gg=sorted(pool,key=gscore)[:100]
    for g in gg:
        gv=g.values
        def obj(k):
            with np.errstate(all='ignore'): den=1+float(k)*gv; r=gv/den
            ok=np.isfinite(r)&(np.abs(den)>1e-8)
            if ok.sum()<12:return 1e6
            A=np.column_stack([np.ones(ok.sum()),r[ok]])
            try:coef=np.linalg.lstsq(A,y[ok],rcond=None)[0]
            except Exception:return 1e6
            return float(np.sqrt(np.mean((y[ok]-A@coef)**2))/sy)
        grid=np.linspace(-4,4,81); vals=np.array([obj(k) for k in grid]); bi=int(np.nanargmin(vals))
        lo=grid[max(0,bi-1)];hi=grid[min(len(grid)-1,bi+1)]
        try:r0=minimize_scalar(obj,bounds=(lo,hi),method='bounded',options={'xatol':1e-13,'maxiter':120});k=float(r0.x)
        except Exception:k=float(grid[bi])
        k=simplify_parameter(k,obj)
        with np.errstate(all='ignore'): den=1+k*gv; rv=gv/den
        if not np.all(np.isfinite(rv)):continue
        A=np.column_stack([np.ones(len(y)),rv]);coef=np.linalg.lstsq(A,y,rcond=None)[0]
        e=float(np.sqrt(np.mean((y-A@coef)**2))/sy)
        if e<tol:
            a=Axis(f'({g.expr})/(1+({k:.16g})*({g.expr}))',rv,ZERO,'residual_rational_response',g.complexity+3)
            return {'nrmse':e,'indices':[0,1],'coefs':coef.tolist(),'features':[one,a]}
    return None

def metrology_gap_monomial(names,X,y,max_support=4):
    sy=float(np.std(y)) or 1.0; best=None; vals=(-2,-1,1,2)
    for k in range(1,min(max_support,len(names))+1):
      for inds in itertools.combinations(range(len(names)),k):
       for exs in itertools.product(vals,repeat=k):
        v=np.ones(len(y)); parts=[]
        with np.errstate(all='ignore'):
         for i,e in zip(inds,exs): v*=safe_pow(X[:,i],e); parts.append(names[i] if e==1 else f'{names[i]}**{e}')
        if not np.all(np.isfinite(v)) or np.std(v)<1e-14: continue
        c=float(np.dot(v,y)/max(np.dot(v,v),1e-30));err=float(np.sqrt(np.mean((y-c*v)**2))/sy)
        row=(err,sum(abs(e) for e in exs),Axis('*'.join(parts),v,ZERO,'metrology_gap_empirical_scale',sum(abs(e) for e in exs)),c)
        if best is None or row[:2]<best[:2]:best=row
        if err<1e-10:return {'nrmse':err,'indices':[0],'coefs':[c],'features':[row[2]],'metrology_gap':True}
    return None

def discover(names,X,y,target_name, max_dimless=160, max_scales=160, search_shell=0):
    shell=int(search_shell)
    if shell<0: raise ValueError("search_shell must be non-negative")
    # Shell 0 is byte-for-byte the historical 15.13 execution envelope.  Every
    # positive shell expands local budgets/orders; no maximum shell exists.
    B=lambda base: int(base)*(shell+1)
    O=lambda base: int(base)+shell
    td=_dim(target_name)
    sem=semantic_axes(names,X)
    # Axis-lifecycle short circuit: if already-born scientific coordinates close
    # the observations, do not materialize a larger response space.
    early=[a for a in sem if a.dim==td]
    early += monomial_axes(names,X,td,support=min(O(3),len(names)),expmax=O(3),max_axes=B(800))
    early=dedup_axes(early,B(1200))
    sy0=float(np.std(y)) or 1.0
    singles=[]
    for i,a in enumerate(early):
        v=a.values; m=np.isfinite(v)&np.isfinite(y)
        if m.sum()<12 or np.std(v[m])<1e-14: continue
        c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30))
        e=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy0)
        if e<1e-9: singles.append((a.complexity,e,i,c))
    if singles:
        _,e,i,c=min(singles); return {'fit':{'nrmse':e,'indices':[i],'coefs':[c],'features':[early[i]]},'scale_count':len(early),'group_count':0,'feature_count':len(early),'semantic_count':len(sem),'metrology_gap':False}
    ep=best_pair_fast(early,y,tol=1e-9)
    if ep is not None and ep['nrmse']<1e-9:
        return {'fit':ep,'scale_count':len(early),'group_count':0,'feature_count':len(early),'semantic_count':len(sem),'metrology_gap':False}
    # Fast evidence-driven modulation over already-born typed coordinates.
    # This is a general Atlas operation: combine a target-dimensional state
    # coordinate with a dimensionless coupling/response coordinate before any
    # broad search region is materialized.
    sem_scales=sorted([a for a in sem if a.dim==td and a.complexity<=5],key=lambda a:(a.complexity,a.expr))[:B(48)]
    sem_groups=sorted([a for a in sem if a.dim==ZERO and a.complexity<=6],key=lambda a:(a.complexity,a.expr))[:B(96)]
    for sc0 in sem_scales:
        for g0 in sem_groups:
            rr=response_candidates(g0,sc0,y,max_keep=4,calibrate=True,expensive=False)
            for a0 in rr:
                v=a0.values; m=np.isfinite(v)&np.isfinite(y)
                if m.sum()<12: continue
                c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30))
                e=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy0)
                if e<1e-9:
                    fit={'nrmse':e,'indices':[0],'coefs':[c],'features':[a0]}
                    return {'fit':fit,'scale_count':len(early),'group_count':len(sem_groups),'feature_count':len(early)+1,'semantic_count':len(sem),'metrology_gap':False}
    # Quantity-type response gate.  Angular/phase targets admit inverse
    # periodic response of dimensionless scientific groups; the group itself is
    # born from metrology, not from the target formula.
    if _tag(target_name,'periodic_angle') or _tag(target_name,'phase_state'):
        one=Axis('1',np.ones(len(y)),ZERO,'constant',0)
        inv_groups=dedup_axes([a for a in sem if a.dim==ZERO]+monomial_axes(names,X,ZERO,support=min(O(3),len(names)),expmax=O(3),dimensionless=True,max_axes=B(320)),B(320))
        for g0 in sorted(inv_groups,key=lambda a:(a.complexity,a.expr))[:B(160)]:
            for a0 in response_candidates(g0,one,y,max_keep=8,calibrate=True,expensive=False):
                if 'asin' not in a0.expr: continue
                v=a0.values; m=np.isfinite(v)&np.isfinite(y)
                if m.sum()<12: continue
                c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30))
                e=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy0)
                if e<1e-9:
                    fit={'nrmse':e,'indices':[0],'coefs':[c],'features':[a0]}
                    return {'fit':fit,'scale_count':len(early),'group_count':len(inv_groups),'feature_count':len(early)+1,'semantic_count':len(sem),'metrology_gap':False}
    # Positive exponential scientific response y = A*s*exp(k*g), with g an
    # already-born dimensionless coordinate.  k is inferred from observations.
    # This covers statistical/attenuation responses without a named target law.
    if np.all(y>0):
        semg0=sorted([a for a in sem if a.dim==ZERO and a.kind in {'normalized_state_squared','normalized_state_difference','dimensionless_ratio','phase_action','thermal_quantum_ratio'}], key=lambda a:(a.complexity,a.expr))[:B(80)]
        escales=sorted(early,key=lambda a:(a.complexity,a.expr))[:B(60)]
        bestexp=None
        for sc0 in escales:
            sv=sc0.values; m=np.isfinite(sv)&(np.abs(sv)>1e-14)&np.isfinite(y)&(y>0)
            if m.sum()<12: continue
            for g0 in semg0[:B(180)]:
                gv=g0.values; mm=m&np.isfinite(gv)
                if mm.sum()<12 or np.std(gv[mm])<1e-14: continue
                rr=y[mm]/sv[mm]
                if not (np.all(rr>0) or np.all(rr<0)): continue
                z=np.log(np.abs(rr)); gg=gv[mm]
                gmean=float(np.mean(gg)); zmean=float(np.mean(z)); dg=gg-gmean
                den=float(np.dot(dg,dg))
                if den<=1e-30: continue
                k=float(np.dot(dg,z-zmean)/den); intercept=zmean-k*gmean
                amp=float(np.sign(np.mean(rr))*np.exp(intercept))
                with np.errstate(all='ignore'): feat=sv*np.exp(np.clip(k*gv,-80,80))
                ok=np.isfinite(feat)
                if ok.sum()<12: continue
                c=float(np.dot(feat[ok],y[ok])/max(np.dot(feat[ok],feat[ok]),1e-30))
                e=float(np.sqrt(np.mean((y[ok]-c*feat[ok])**2))/sy0)
                row=(e,sc0.complexity+g0.complexity,sc0,g0,k,c,feat)
                if bestexp is None or row[:2]<bestexp[:2]: bestexp=row
        if bestexp is not None and bestexp[0]<1e-9:
            e,_,sc0,g0,k,c,feat=bestexp
            def eo(q):
                with np.errstate(all='ignore'): ff=sc0.values*np.exp(np.clip(float(q)*g0.values,-80,80))
                ok=np.isfinite(ff)
                cc=float(np.dot(ff[ok],y[ok])/max(np.dot(ff[ok],ff[ok]),1e-30))
                return float(np.sqrt(np.mean((y[ok]-cc*ff[ok])**2))/sy0)
            k=simplify_parameter(k,eo)
            with np.errstate(all='ignore'): feat=sc0.values*np.exp(np.clip(k*g0.values,-80,80))
            ok=np.isfinite(feat); c=float(np.dot(feat[ok],y[ok])/max(np.dot(feat[ok],feat[ok]),1e-30)); e=float(np.sqrt(np.mean((y[ok]-c*feat[ok])**2))/sy0)
            ax=Axis(f'({sc0.expr})*exp(({k:.16g})*({g0.expr}))',feat,td,'evidence_born_exponential_response',sc0.complexity+g0.complexity+2)
            fit={'nrmse':e,'indices':[0],'coefs':[c],'features':[ax]}
            return {'fit':fit,'scale_count':len(early),'group_count':len(semg0),'feature_count':len(early)+1,'semantic_count':len(sem),'metrology_gap':False}
    # Generic dimensionless saturating response inferred from observations.
    # This is activated only after the already-born exact gate fails.
    if td==ZERO:
        dg=monomial_axes(names,X,ZERO,support=min(O(3),len(names)),expmax=O(3),dimensionless=True,max_axes=B(320))
        dg=dedup_axes([a for a in sem if a.dim==ZERO]+dg,B(320))
        sy=float(np.std(y)) or 1.0; proposals=[]
        grid=np.linspace(-4.0,4.0,49)
        for g0 in dg:
            gv=g0.values; m=np.isfinite(gv)&np.isfinite(y)
            if m.sum()<12: continue
            best=(1e9,None,None)
            for k in grid:
                den=1+k*gv[m]
                ok=np.abs(den)>1e-8
                if ok.sum()<12: continue
                r=gv[m][ok]/den[ok]
                A=np.column_stack([np.ones(ok.sum()),r])
                try:c=np.linalg.lstsq(A,y[m][ok],rcond=None)[0]
                except Exception:continue
                e=float(np.sqrt(np.mean((y[m][ok]-A@c)**2))/sy)
                if e<best[0]: best=(e,k,c)
            proposals.append((best[0],g0,best[1]))
        for _,g0,k0 in sorted(proposals,key=lambda z:z[0])[:B(6)]:
            if k0 is None: continue
            gv=g0.values; m=np.isfinite(gv)&np.isfinite(y)
            def obj(k):
                den=1+float(k)*gv[m]; ok=np.abs(den)>1e-8
                if ok.sum()<12:return 1e6
                r=gv[m][ok]/den[ok]; A=np.column_stack([np.ones(ok.sum()),r])
                try:c=np.linalg.lstsq(A,y[m][ok],rcond=None)[0]
                except Exception:return 1e6
                return float(np.sqrt(np.mean((y[m][ok]-A@c)**2))/sy)
            lo=max(-4.0,float(k0)-0.25); hi=min(4.0,float(k0)+0.25)
            try:k=float(minimize_scalar(obj,bounds=(lo,hi),method='bounded',options={'xatol':1e-13,'maxiter':100}).x)
            except Exception:k=float(k0)
            k=simplify_parameter(k,obj); den=1+k*gv
            if np.any(np.abs(den)<1e-8): continue
            rv=gv/den; A=np.column_stack([np.ones(len(y)),rv])
            try:c=np.linalg.lstsq(A,y,rcond=None)[0]
            except Exception:continue
            e=float(np.sqrt(np.mean((y-A@c)**2))/sy)
            if e<1e-9:
                f0=Axis('1',np.ones(len(y)),ZERO,'constant',0)
                f1=Axis(f'({g0.expr})/(1+({k:.16g})*({g0.expr}))',rv,ZERO,'evidence_born_rational_response',g0.complexity+3)
                fit={'nrmse':e,'indices':[0,1],'coefs':[float(c[0]),float(c[1])],'features':[f0,f1]}
                return {'fit':fit,'scale_count':len(early),'group_count':len(dg),'feature_count':len(early)+2,'semantic_count':len(sem),'metrology_gap':False}
    # include semantic axes in scale/group pool when dimensions match
    scales=monomial_axes(names,X,td,support=min(O(4),len(names)),expmax=O(3),max_axes=B(3500))
    # next coefficient shell allows fourth powers when dimensional evidence requires them
    scales += monomial_axes(names,X,td,support=min(O(4),len(names)),expmax=O(4),max_axes=B(1800))
    scales += [a for a in sem if a.dim==td]
    # fractional/root scaling is a typed coordinate when a squared physical scale has twice the target dimension
    twice=tuple(2*z for z in td)
    for a in monomial_axes(names,X,twice,support=min(O(4),len(names)),expmax=O(3),max_axes=B(500)):
        if np.all(a.values>=0): scales.append(Axis(f'sqrt({a.expr})',np.sqrt(a.values),td,'typed_square_root_scale',a.complexity+1))
    # typed composition with born semantic/geometric axes: only dimensions required by the target are materialized
    sem_nonzero=[a for a in sem if a.dim!=ZERO]
    seen_req={}
    for a in sem_nonzero:
        for op in ('mul','div'):
            req=tuple(int(t-a0) for t,a0 in zip(td,a.dim)) if op=='mul' else tuple(int(t+a0) for t,a0 in zip(td,a.dim))
            if req not in seen_req:
                seen_req[req]=monomial_axes(names,X,req,support=min(O(3),len(names)),expmax=O(3),max_axes=B(500))
            # Activate compatible coefficients by evidence, not enumeration order.
            cand=[]; sy0=float(np.std(y)) or 1.0
            for b in seen_req[req]:
                with np.errstate(all='ignore'):
                    v=b.values*a.values if op=='mul' else b.values/a.values
                if not np.all(np.isfinite(v)) or np.std(v)<=1e-14: continue
                c=float(np.dot(v,y)/max(np.dot(v,v),1e-30)); e=float(np.sqrt(np.mean((y-c*v)**2))/sy0)
                cand.append((e,b.complexity,b,v))
            cand.sort(key=lambda q:(q[0],q[1],q[2].expr))
            for _,_,b,v in cand[:B(32)]:
                ex=f'({b.expr})*({a.expr})' if op=='mul' else f'({b.expr})/({a.expr})'
                scales.append(Axis(ex,v,td,'typed_semantic_composite',b.complexity+a.complexity+1))
    groups=[a for a in sem if a.dim==ZERO] + monomial_axes(names,X,ZERO,support=min(O(4),len(names)),expmax=O(3),dimensionless=True,max_axes=B(3500))
    # Ratios to born physical scales create dimensionless scientific response coordinates.
    for a in [q for q in sem if q.dim!=ZERO]:
        for b in monomial_axes(names,X,a.dim,support=min(O(3),len(names)),expmax=O(3),max_axes=B(180))[:B(80)]:
            with np.errstate(all='ignore'):
                v1=b.values/a.values; v2=a.values/b.values
            if np.all(np.isfinite(v1)): groups.append(Axis(f'({b.expr})/({a.expr})',v1,ZERO,'normalized_physical_response',b.complexity+a.complexity+1))
            if np.all(np.isfinite(v2)): groups.append(Axis(f'({a.expr})/({b.expr})',v2,ZERO,'normalized_physical_response',b.complexity+a.complexity+1))
    # Dimensionless base variables may couple to an already-born invariant without changing type.
    base_dimless=[(n,X[:,i]) for i,n in enumerate(names) if _dim(n)==ZERO]
    seed_groups=list(groups)
    for n,vn in base_dimless:
        for g0 in seed_groups:
            if g0.complexity>6 or n in g0.expr: continue
            with np.errstate(all='ignore'):vv=vn*g0.values
            if np.all(np.isfinite(vv)): groups.append(Axis(f'({n})*({g0.expr})',vv,ZERO,'dimensionless_coupling',g0.complexity+2))
    # For dimensionless observables, a raw dimensionless state may be modulated
    # by an independently born dimensionless scientific response.  Activate only
    # evidence-ranked products; this is the dimensionless analogue of a typed
    # physical scale times a response coordinate.
    if td==ZERO:
        raw_dimless=[Axis(n,X[:,i],ZERO,'raw_dimensionless_state',1) for i,n in enumerate(names) if _dim(n)==ZERO]
        sem_resp=[a for a in sem if a.dim==ZERO and a.kind not in {'state_difference','dimensionless_ratio','normalized_state_difference','dimensionless_response_power'} and a.complexity<=7]
        sy_mod=float(np.std(y)) or 1.0; mods=[]
        for r0 in raw_dimless:
            for a0 in sem_resp:
                if r0.expr in a0.expr: continue
                with np.errstate(all='ignore'): v=r0.values*a0.values
                if not np.all(np.isfinite(v)) or np.std(v)<1e-14: continue
                c=float(np.dot(v,y)/max(np.dot(v,v),1e-30)); e=float(np.sqrt(np.mean((y-c*v)**2))/sy_mod)
                mods.append((e,r0.complexity+a0.complexity,r0,a0,v))
        mods.sort(key=lambda q:(q[0],q[1],q[2].expr,q[3].expr))
        for _,_,r0,a0,v in mods[:B(120)]:
            scales.append(Axis(f'({r0.expr})*({a0.expr})',v,ZERO,'dimensionless_state_modulation',r0.complexity+a0.complexity+1))

    # Born semantic/typed coordinates are authoritative research coordinates and
    # must never be pruned merely because a generic monomial enumerator filled the
    # numerical budget first. Generic candidates use the remaining search budget.
    protected_scales=[a for a in scales if a.kind!='monomial']
    generic_scales=[a for a in scales if a.kind=='monomial']
    scales=dedup_axes(protected_scales+generic_scales,B(3500))

    # A dimensionless scientific response may couple multiplicatively to another
    # already-born dimensionless response without changing physical type. Activate
    # only low-complexity pairs involving at least one semantic coordinate; this is
    # an axis-lifecycle operation, not an unrestricted expression-tree product.
    sem_dimless=[a for a in groups if a.kind!='monomial' and a.complexity<=6]
    low_dimless=[a for a in groups if a.complexity<=4]
    coupled=[]
    seen_pair=set()
    for a in sem_dimless[:B(160)]:
        for b in low_dimless[:B(240)]:
            if a.expr==b.expr: continue
            key=tuple(sorted((a.expr,b.expr)))
            if key in seen_pair: continue
            seen_pair.add(key)
            with np.errstate(all='ignore'): v=a.values*b.values
            if np.all(np.isfinite(v)) and np.std(v)>1e-14:
                coupled.append(Axis(f'({a.expr})*({b.expr})',v,ZERO,'semantic_response_coupling',a.complexity+b.complexity+1))
            if len(coupled)>=B(1200): break
        if len(coupled)>=B(1200): break
    groups=dedup_axes([a for a in groups if a.kind!='monomial']+coupled+[a for a in groups if a.kind=='monomial'],B(5000))
    sy=float(np.std(y)) or 1.0
    # cheap scale ranking by best linear coefficient; keep diversity but don't discard all nonlinear candidates
    def linerr(a):
        v=a.values; m=np.isfinite(v)&np.isfinite(y)
        if m.sum()<12:return 1e9
        c=np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30); return float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy)
    low=sorted([a for a in scales if a.complexity<=6],key=lambda a:(a.complexity,a.expr))
    ranked=sorted(scales,key=lambda a:(linerr(a),a.complexity,a.expr))
    # Preserve evidence-born semantic/typed axes through the second (runtime)
    # pruning stage as well.  Rank them by observed explanatory power, then fill
    # the remaining budget with low-complexity/generic scales.
    protected_ranked=sorted([a for a in scales if a.kind!='monomial'],key=lambda a:(linerr(a),a.complexity,a.expr))
    protected_low=sorted([a for a in scales if a.kind!='monomial' and a.complexity<=6],key=lambda a:(a.complexity,a.expr))
    scales=dedup_axes(protected_ranked[:B(160)]+protected_low+low+ranked,max(B(max_scales),B(320)))[:max(B(max_scales),B(320))]
    # dimensionless groups ranked by monotonic correlation with normalized targets across best scales, plus semantic axes protected
    semg=[g for g in groups if g.kind!='monomial']
    # use correlations with y and rank transforms; dimensionless physics groups can be invisible to raw y, so retain low complexity monomials
    groups=sorted(groups,key=lambda g:(g.complexity, g.expr))
    protected=dedup_axes(semg,B(360))
    rest=[g for g in groups if g.expr not in {p.expr for p in protected}]
    groups=dedup_axes(protected+[g for g in rest if g.complexity<=5]+rest,max(B(max_dimless),B(320)))[:max(B(max_dimless),B(320))]

    # direct scales are already valid response features
    feats=list(scales)
    # lazy activation: response coordinates only for scales/groups that survive coarse interaction screening
    pair_scores=[]
    # use quick direct response set via response_candidates; cap product by screening groups on each of top scales
    for si,s in enumerate(scales[:min(B(50),len(scales))]):
        # ratio r to score groups by correlation / monotonic relation
        mask=np.isfinite(s.values)&(np.abs(s.values)>1e-14)&np.isfinite(y)
        if mask.sum()<12: continue
        r=np.zeros_like(y); r[mask]=y[mask]/s.values[mask]
        rg=[]
        for gi,g in enumerate(groups):
            gm=g.values[mask]
            if not np.all(np.isfinite(gm)) or np.std(gm)<1e-14:continue
            # Pearson + correlations after a few generic shape diagnostics
            z=(gm-np.mean(gm))/(np.std(gm) or 1); rr=(r[mask]-np.mean(r[mask]))/(np.std(r[mask]) or 1)
            sc=abs(float(np.mean(z*rr)))
            with np.errstate(all='ignore'):
                for tv in (np.abs(gm), gm*gm, 1/np.where(np.abs(gm)>1e-12,gm,np.nan)):
                    ok=np.isfinite(tv)
                    if ok.sum()>8 and np.std(tv[ok])>1e-14:
                        sc=max(sc,abs(float(np.corrcoef(tv[ok],r[mask][ok])[0,1])))
            if g.kind!='monomial': sc=max(sc,0.15) # semantic coordinates get a fair probe
            rg.append((sc,gi))
        rg.sort(reverse=True)
        for _,gi in rg[:min(B(16),len(rg))]: pair_scores.append((si,gi))
    seen=set(); pair_direct=[]
    for si,gi in pair_scores:
        key=(si,gi)
        if key in seen:continue
        seen.add(key)
        ds=response_candidates(groups[gi],scales[si],y,max_keep=4,calibrate=True,expensive=False)
        feats.extend(ds)
        # rank pair by its best direct one-feature error; calibration is activated only for survivors
        be=1e9
        for a in ds:
            v=a.values; m=np.isfinite(v)&np.isfinite(y)
            if m.sum()<12: continue
            c=np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30)
            be=min(be,float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy))
        pair_direct.append((be,si,gi))
    pair_direct.sort(key=lambda z:z[0])
    for _,si,gi in pair_direct[:B(12)]:
        feats.extend(response_candidates(groups[gi],scales[si],y,max_keep=5,calibrate=True,expensive=True))
    # Canonical scientific response axes are activated directly when their typed semantics exist.
    canonical_kinds={'periodic_angle','phase_coupling','phase_transfer','inverse_phase_transfer','phase_action','detuning_phase','quantum_action_phase','thermal_quantum_ratio','normalized_physical_response','dimensionless_coupling','coherent_phase_projection','coherent_superposition_intensity','periodic_response','relativistic_beta','relativistic_beta_squared','relativistic_pair_coupling','semantic_response_coupling','dimensionless_response_power','dimensionless_ratio','normalized_state_difference'}
    canon=sorted([g for g in groups if g.kind in canonical_kinds],key=lambda a:(a.complexity,a.kind,a.expr))
    # Coherent phase-ratio coordinate for a periodic angle and a dimensionless multiplier.
    interference=[]
    angle_sem=[g for g in groups if g.kind=='periodic_angle']
    phase_sem=[g for g in groups if g.kind=='phase_coupling']
    for a0 in angle_sem[:B(8)]:
        for p0 in phase_sem[:B(24)]:
            # retain only couplings that contain the same angle coordinate
            if a0.expr not in p0.expr: continue
            for s0 in scales[:B(80)]:
                av=a0.values; pv=p0.values; sv=s0.values; mask=np.isfinite(av)&np.isfinite(pv)&np.isfinite(sv)&np.isfinite(y)
                if mask.sum()<12: continue
                sy0=float(np.std(y[mask])) or 1.0
                def obj(k):
                    with np.errstate(all='ignore'):
                        den=np.sin(k*av[mask]); r=(np.sin(k*pv[mask])/den)**2; f=sv[mask]*r
                    ok=np.isfinite(f)&(np.abs(den)>1e-8)
                    if ok.sum()<12:return 1e6
                    c=np.dot(f[ok],y[mask][ok])/max(np.dot(f[ok],f[ok]),1e-30)
                    return float(np.sqrt(np.mean((y[mask][ok]-c*f[ok])**2))/sy0)
                grid=np.linspace(0.05,6.0,B(48)); vals=np.array([obj(k) for k in grid]); bi=int(np.nanargmin(vals)); lo=grid[max(0,bi-1)];hi=grid[min(len(grid)-1,bi+1)]
                try:rr=minimize_scalar(obj,bounds=(lo,hi),method='bounded',options={'xatol':1e-13,'maxiter':160});k=float(rr.x)
                except Exception:k=float(grid[bi])
                k=simplify_parameter(k,obj)
                with np.errstate(all='ignore'):
                    den=np.sin(k*av); r=(np.sin(k*pv)/den)**2; f=sv*r
                if np.all(np.isfinite(f)):
                    interference.append(Axis(f'({s0.expr})*(sin(({k:.16g})*({p0.expr}))/sin(({k:.16g})*({a0.expr})))**2',f,s0.dim,'coherent_phase_ratio',s0.complexity+a0.complexity+p0.complexity+3))
    feats.extend(interference)
    primitive_feats=dedup_axes([s0 for s0 in scales if s0.complexity<=5] + [a for a in sem if a.dim==td and a.complexity<=6] + interference,B(1200))
    core_feats=[s0 for s0 in scales if s0.complexity<=7][:B(360)] + interference
    for s0 in list(core_feats):
        for g0 in canon[:B(24)]:
            # retain the full small direct family for the exact typed additive gate
            core_feats.extend(response_candidates(g0,s0,y,max_keep=30,calibrate=False,expensive=False))
    core_feats=dedup_axes(core_feats,B(4200))
    for s0 in scales[:B(120)]:
        for g0 in canon[:B(24)]:
            feats.extend(response_candidates(g0,s0,y,max_keep=4,calibrate=True,expensive=(g0.kind in {'periodic_angle','phase_coupling','phase_action','detuning_phase','quantum_action_phase','thermal_quantum_ratio'})))
    feats=dedup_axes(feats,B(6500))
    # Prefer the simplest exact single coordinate before additive residual synthesis.
    best_single=None; exact_singles=[]
    for i,a in enumerate(feats):
        v=a.values; m=np.isfinite(v)&np.isfinite(y)
        if m.sum()<12 or np.std(v[m])<1e-14: continue
        c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30)); err=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/sy)
        row=(err,a.complexity,i,c)
        if err<1e-9: exact_singles.append((a.complexity,err,i,c))
        if best_single is None or row[:2]<best_single[:2]: best_single=row
    if exact_singles:
        cc,err,i,c=min(exact_singles); best_single=(err,cc,i,c)
    if best_single is not None and best_single[0]<1e-9:
        err,_,i,c=best_single; fit={'nrmse':err,'indices':[i],'coefs':[c],'features':[feats[i]]}
    else:
        # First test the complete low-complexity scientific core without ranking by single-term fit.
        core_pair=best_pair_fast(core_feats,y,tol=1e-9)
        if core_pair is not None and core_pair['nrmse']<1e-9:
            fit=core_pair
        else:
            primitive_multi=greedy_sparse(primitive_feats,y,max_terms=O(5))
            if primitive_multi is not None and primitive_multi['nrmse']<1e-9:
                fit=primitive_multi
            else:
                core_multi=greedy_sparse(core_feats,y,max_terms=O(5))
                if core_multi is not None and core_multi['nrmse']<1e-9:
                    fit=core_multi
                else:
                    fit=exact_sparse_pair(feats,y,top=220,tol=1e-9)
                    if fit is None:
                        fit=greedy_sparse(feats,y,max_terms=O(8))
    if fit is None or fit.get('nrmse',1.0)>1e-6:
        # Residual-driven activation: reuse the same typed scales/groups but open
        # broader scientific modulation only after the ordinary path failed.
        fallback_order=(rational_baseline_fallback,exact_response_fallback,shared_response_pair_fallback,baseline_modulated_fallback) if td==ZERO else (exact_response_fallback,shared_response_pair_fallback,baseline_modulated_fallback,rational_baseline_fallback)
        for fb in fallback_order:
            rr=fb(scales,groups,y,tol=1e-9)
            if rr is not None and rr.get('nrmse',1.0)<1e-9:
                fit=rr; break
    if fit is None or fit.get('nrmse',1.0)>1e-6:
        # Open the next owner-connected higher-order axis shell only after lower
        # shells fail.  This is an execution shell, not a global physics ceiling.
        higher=monomial_axes(names,X,td,support=min(O(5),len(names)),expmax=O(4),max_axes=B(6000))
        hs=None; syh=float(np.std(y)) or 1.0
        for a0 in higher:
            v=a0.values; m=np.isfinite(v)&np.isfinite(y)
            if m.sum()<12: continue
            c=float(np.dot(v[m],y[m])/max(np.dot(v[m],v[m]),1e-30))
            e=float(np.sqrt(np.mean((y[m]-c*v[m])**2))/syh)
            row=(e,a0.complexity,a0,c)
            if hs is None or row[:2]<hs[:2]: hs=row
        if hs is not None and hs[0]<1e-9:
            fit={'nrmse':hs[0],'indices':[0],'coefs':[hs[3]],'features':[hs[2]]}
    if fit is None or fit.get('nrmse',1.0)>1e-6:
        mg=metrology_gap_monomial(names,X,y,max_support=min(O(5),len(names)))
        if mg is not None and mg['nrmse']<1e-9: fit=mg
    return {'fit':fit,'scale_count':len(scales),'group_count':len(groups),'feature_count':len(feats),'semantic_count':len(sem),'metrology_gap':bool(fit and fit.get('metrology_gap'))}

ATLAS_LAW_SPACE_OWNER = "ATLAS-LAW-SPACE-SEARCH/1.0.0"
SCIENTIFIC_AXIS_SPACE_OWNER = "SCIENTIFIC-AXIS-SPACE/1.0.0"  # compatibility adapter id

_COORDINATE_ARCHETYPE_AXIS = {
    'state_difference':'state_difference_coordinate',
    'typed_additive_state':'typed_additive_coordinate',
    'normalized_state_difference':'state_difference_coordinate',
    'normalized_state_squared':'dimensionless_ratio_coordinate',
    'dimensionless_ratio':'dimensionless_ratio_coordinate',
    'euclidean_distance_squared':'euclidean_distance_coordinate',
    'euclidean_distance':'euclidean_distance_coordinate',
    'euclidean_subspace_norm':'euclidean_norm_coordinate',
    'euclidean_subspace_norm_squared':'euclidean_norm_coordinate',
    'euclidean_norm':'euclidean_norm_coordinate',
    'euclidean_norm_squared':'euclidean_norm_coordinate',
    'dot_product':'dot_product_coordinate',
    'weighted_state_mean':'weighted_state_mean_coordinate',
    'thermal_energy':'thermal_energy_coordinate',
    'phase_action':'phase_action_coordinate',
    'detuning_phase':'detuning_phase_coordinate',
    'quantum_action_phase':'quantum_action_phase_coordinate',
    'thermal_quantum_ratio':'thermal_quantum_ratio_coordinate',
    'periodic_angle':'periodic_phase_structure',
    'phase_coupling':'periodic_phase_structure',
    'phase_transfer':'periodic_phase_structure',
    'periodic_state_pair_modulation':'response_coordinate_structure',
    'inverse_phase_transfer':'periodic_phase_structure',
    'periodic_response':'periodic_response_coordinate',
    'coherent_cross_magnitude':'coherent_cross_magnitude_coordinate',
    'coherent_phase_projection':'coherent_phase_projection_coordinate',
    'coherent_superposition_intensity':'coherent_superposition_intensity_coordinate',
    'relativistic_beta':'relativistic_beta_coordinate',
    'relativistic_beta_squared':'relativistic_beta_coordinate',
    'relativistic_pair_coupling':'relativistic_pair_coupling_coordinate',
    'spacetime_mixed_time':'relativistic_spacetime_coordinate',
    'spacetime_mixed_length':'relativistic_spacetime_coordinate',
    'relativistic_spacetime_coordinate':'relativistic_spacetime_coordinate',
    'squared_frequency_detuning':'resonance_coordinate',
    'normalized_resonance_coordinate':'resonance_coordinate',
    'transverse_radius':'euclidean_norm_coordinate',
    'transverse_direction_cosine':'direction_cosine_coordinate',
    'axial_direction_cosine':'direction_cosine_coordinate',
    'axial_transverse_geometry':'direction_cosine_coordinate',
    'thermal_field_coupling':'orientational_thermal_coordinate',
    'orientational_thermal_coupling':'orientational_thermal_coordinate',
    'orientational_state_density_response':'orientational_thermal_coordinate',
    'cosine_law':'cosine_law_coordinate',
    'dimensionless_response_power':'response_coordinate_structure',
    'semantic_response_coupling':'response_coordinate_structure',
    'dimensionless_state_modulation':'response_coordinate_structure',
    'typed_square_root_scale':'scale_invariance_structure',
    'evidence_born_exponential_response':'evidence_born_response_coordinate',
    'evidence_born_rational_response':'evidence_born_response_coordinate',
    'residual_rational_response':'evidence_born_response_coordinate',
    'metrology_gap_empirical_scale':'metrology_consistency',
    'calibrated_response':'evidence_born_response_coordinate',
    'monomial':'dimensionless_group_structure',
    'constant':'scale_invariance_structure',
}


def _normalize_quantity_specs(variable_names, target_name, quantity_specs):
    specs={str(k):dict(v) for k,v in dict(quantity_specs or {}).items()}
    required=list(variable_names)+[str(target_name)]
    missing=[n for n in required if n not in specs]
    if missing: raise ValueError(f"Atlas law-space search requires typed quantity descriptors for {missing}")
    for n in required:
        d=specs[n].get('dimension')
        if not isinstance(d,(list,tuple)) or len(d) not in (5,7):
            raise ValueError(f"{n}: dimension must be canonical 7D or legacy 5D boundary descriptor")
        specs[n]['_input_dimension_arity']=len(d)
        specs[n]['dimension']=_canonical_dimension_vector(d)
        specs[n]['tags']=tuple(str(x) for x in specs[n].get('tags',()))
    return specs


class AtlasLawSpaceSearchOwner:
    """Generic Atlas search over typed scientific coordinates.

    The owner consumes observations plus metrology/state descriptors supplied by
    the domain/adapter layer.  It owns no benchmark-variable dictionary and no
    target-law catalogue.  Reusable coordinate classes resolve to canonical
    DomainAxisRegistry axes; relation results remain hypotheses and are routed to
    the ordinary scientific-promotion boundary rather than becoming laws here.
    """
    owner_id = ATLAS_LAW_SPACE_OWNER

    def contract(self):
        from .schema import digest_payload
        payload = {
            "owner_id": self.owner_id,
            "atlas_role": "OWNER_CONNECTED_MULTIDIMENSIONAL_LAW_SPACE_SEARCH",
            "scientific_space": [
                "canonical_domain_axes", "metrology_quantity_descriptors", "state_relations",
                "geometry", "scale_invariance", "dimensionless_groups", "periodic_phase",
                "thermal_coupling", "relativistic_coupling", "resonance", "coherence",
                "response_coordinates", "adaptive_axis_lifecycle",
            ],
            "target_expression_visible": False,
            "known_law_catalog_required": False,
            "expression_tree_is_primary_search_space": False,
            "benchmark_variable_dictionary_in_owner": False,
            "canonical_dimension_basis": list(CANONICAL_DIMENSION_BASIS),
            "dimension_authority": "EXACT_RATIONAL_7D_KERNEL_VIA_PHI_COMPILER_OWNER",
            "legacy_five_coordinate_descriptors": "BOUNDARY_COMPATIBILITY_ONLY_PADDED_TO_7D",
            "qualification_kernel": {
                "exact_dimension_kernel": True,
                "conservation_invariant_canonicalization": "COMPOSITION_ADDITIVITY_REQUIRED__TRAJECTORY_CONSTANCY_ALONE_INSUFFICIENT",
                "mdl_exponent_complexity": True,
                "convention_artifact_gate": "REQUIRES_DECLARED_ALTERNATE_METROLOGY_CONVENTION",
                "known_derivability_gate": "OWNED_BY_EXISTING_SOURCE_LAW_AND_PROMOTION_PATHS",
                "data_collapse_gate": "AVAILABLE_WHEN_MULTI_SYSTEM_EVIDENCE_IS_SUPPLIED",
                "regime_transition_gate": "DOMAIN_EVIDENCE_REQUIRED",
                "cross_system_transfer_gate": "DOMAIN_EVIDENCE_REQUIRED",
                "whole_pipeline_permutation_null": "REQUIRED_BEFORE_SCIENTIFIC_PROMOTION_NOT_EXECUTED_ON_RAW_COORDINATE_BIRTH",
            },
            "axis_birth_policy": "CANONICAL_AXES_FIRST__RESEARCH_LOCAL_BIRTH__COMMON_ADMISSION_PROMOTION_FOR_NOVEL_AXES",
            "axis_persistence_policy": "CANONICAL_AXES_ARE_APPEND_ONLY_AND_REUSABLE; DORMANT_DOES_NOT_MEAN_FORGOTTEN",
            "relation_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.2.0",
            "dynamic_axis_admission_owner": "DYNAMIC-AXIS-ADMISSION/6.24.0",
            "dynamic_axis_promotion_owner": "DYNAMIC-AXIS-PROMOTION/8.0.0",
            "fixed_global_axis_ceiling": None,
            "fixed_global_response_family_ceiling": None,
            "fair_local_search_shell": {
                "parameter": "search_shell >= 0",
                "fixed_maximum_shell": None,
                "shell_zero_preserves_15_13_behavior": True,
                "feature_caps_are_per_shell_execution_budgets": True,
                "support_order_grows_without_fixed_ceiling": True,
                "exponent_order_grows_without_fixed_ceiling": True,
                "sparse_term_budget_grows_without_fixed_ceiling": True,
                "persistent_shell_schedule_owner": "CandidateGenerationPipeline/6.27.0::DOVETAIL",
            },
            "adaptive_subspace_navigation": {
                "authoritative_frontier_owner": "CandidateGenerationPipeline",
                "hypothesis_space": "UNION_OVER_LOCAL_AXIS_SUBSPACES_S_K",
                "fixed_subspace_order_ceiling": None,
                "all_axes_used_simultaneously_by_default": False,
                "lower_order_projection_required_before_higher_order_nomination": False,
                "nomination_sources": [
                    "EXACT_PAIR_FRONTIER", "OWNER_COBOUND_HIGHER_ORDER", "TYPED_BRIDGE_MOTIF",
                    "BRIDGE_CONNECTED_OWNER_MERGE", "SEMANTIC_ROLE_HIGHER_ORDER_MOTIF",
                ],
                "candidate_absent_from_literature_is_false": False,
                "candidate_requires_problem_applicability_experiment_contract": True,
                "persistent_fair_dovetail_state": True,
                "fixed_dovetail_step_ceiling": None,
                "all_finite_axis_subsets_eventually_addressable_under_repeated_advance": True,
            },
            "claim_boundary": "RELATION_HYPOTHESIS_WITHIN_EXECUTED_ATLAS_REGION_NOT_WORLD_LAW",
        }
        return {**payload, "digest": digest_payload(payload)}

    def discover(self, *, variable_names, values, target_values, target_name, quantity_specs, domain_ids=("physics","metrology"), search_shell=0):
        from .domains import DOMAIN_REGISTRIES
        from .schema import digest_payload
        X=np.asarray(values,dtype=float); y=np.asarray(target_values,dtype=float)
        names=tuple(str(x) for x in variable_names); target=str(target_name)
        if X.ndim!=2 or X.shape[0]!=y.shape[0] or X.shape[1]!=len(names):
            raise ValueError("typed observation matrix shape mismatch")
        specs=_normalize_quantity_specs(names,target,quantity_specs)
        unknown_domains=[d for d in domain_ids if d not in DOMAIN_REGISTRIES]
        if unknown_domains: raise ValueError(f"unknown Atlas domains {unknown_domains}")
        token=_QUANTITY_CONTEXT.set(specs)
        try:
            exact_kernel=exact_dimension_kernel(names+(target,))
            predictor_kernel=exact_dimension_kernel(names)
            result=discover(names,X,y,target,search_shell=int(search_shell))
        finally:
            _QUANTITY_CONTEXT.reset(token)
        fit=result.get('fit'); out={k:v for k,v in result.items() if k!='fit'}
        out.update({
            "owner_id": self.owner_id,
            "domain_ids": list(domain_ids),
            "quantity_descriptor_count": len(specs),
            "target_expression_visible": False,
            "known_law_catalog_used": False,
            "benchmark_variable_dictionary_used_by_owner": False,
            "local_search_continuation": {
                "search_shell": int(search_shell),
                "fixed_maximum_shell": None,
                "shell_zero_preserves_15_13_execution_envelope": True,
                "feature_budgets_grow_with_shell": True,
                "monomial_support_and_exponent_order_grow_with_shell": True,
                "sparse_term_budget_grows_with_shell": True,
                "shell_is_execution_tranche_not_scientific_truth_gate": True,
            },
            "dimensional_qualification": {
                "canonical_basis": list(CANONICAL_DIMENSION_BASIS),
                "predictor_kernel": predictor_kernel,
                "relation_kernel_with_target": exact_kernel,
                "exact_arithmetic": True,
                "legacy_dimension_padding_used": any(int(specs[n].get("_input_dimension_arity",7))==5 for n in names+(target,)),
                "status": "EXACT_DIMENSION_KERNEL_COMPUTED",
            },
        })
        if fit is None:
            out.update({"status":"ATLAS_COORDINATE_OR_REPRESENTATION_GAP","selected_relation":None,"canonical_axis_bindings":[]})
        else:
            kinds=[a.kind for a in fit.get('features',())]
            bindings=[]; unresolved=[]
            physics=DOMAIN_REGISTRIES.get('physics')
            for kind in kinds:
                axis_id=_COORDINATE_ARCHETYPE_AXIS.get(kind)
                if axis_id and physics and axis_id in physics.axes:
                    bindings.append({"coordinate_kind":kind,"domain_id":"physics","axis_id":axis_id,"registry_status":"CANONICAL_REUSABLE"})
                else:
                    unresolved.append(kind)
            predictions=np.zeros_like(y,dtype=float)
            for c,a in zip(fit.get('coefs',()),fit.get('features',())): predictions += float(c)*np.asarray(a.values,float)
            relation={
                "coefficients":[float(x) for x in fit.get('coefs',())],
                "coordinate_projections":[a.expr for a in fit.get('features',())],
                "coordinate_kinds":kinds,
                "canonical_axis_ids":[b['axis_id'] for b in bindings],
            }
            out.update({
                "status":"PROVISIONAL_RELATION_HYPOTHESIS_WITHIN_ATLAS_SPACE" if fit.get('nrmse',1.0)<1e-9 else "ATLAS_COORDINATE_OR_REPRESENTATION_GAP",
                "train_nrmse":float(fit.get('nrmse',float('inf'))),
                "selected_relation":relation,
                "canonical_axis_bindings":bindings,
                "unresolved_coordinate_kinds":sorted(set(unresolved)),
                "research_cycle_binding":{
                    "dynamic_axis_admission_owner":"DYNAMIC-AXIS-ADMISSION/6.24.0",
                    "dynamic_axis_promotion_owner":"DYNAMIC-AXIS-PROMOTION/8.0.0",
                    "scientific_promotion_owner":"SCIENTIFIC-PROMOTION-CORE/9.2.0",
                    "law_auto_promoted":False,
                    "next_gate":"UNCERTAINTY__OOD__ALTERNATIVES__IDENTIFIABILITY__REPLICATION",
                },
                "relation_hypothesis":{
                    "model_class":"ATLAS_COORDINATE_RELATION",
                    "active_axes":[b['axis_id'] for b in bindings],
                    "predictions_train":[float(x) for x in predictions],
                    "provenance":self.owner_id,
                    "promotion_status":"PROVISIONAL_NOT_LAW",
                },
            })
        out['digest']=digest_payload(out); return out


class ScientificAxisSpaceOwner:
    """Compatibility adapter for 15.5 callers.

    It delegates to AtlasLawSpaceSearchOwner.  New callers must pass typed
    ``quantity_specs``; benchmark-specific name semantics are intentionally not
    retained in source code.
    """
    owner_id = SCIENTIFIC_AXIS_SPACE_OWNER
    def contract(self):
        c=dict(AtlasLawSpaceSearchOwner().contract())
        c.update({"owner_id":self.owner_id,"compatibility_adapter":True,"authoritative_owner":ATLAS_LAW_SPACE_OWNER})
        from .schema import digest_payload
        c['digest']=digest_payload({k:v for k,v in c.items() if k!='digest'}); return c
    def discover(self, *, variable_names, values, target_values, target_name, quantity_specs=None, domain_ids=("physics","metrology"), search_shell=0):
        if quantity_specs is None:
            raise ValueError("SCIENTIFIC-AXIS-SPACE compatibility adapter no longer owns variable semantics; supply quantity_specs")
        return AtlasLawSpaceSearchOwner().discover(variable_names=variable_names,values=values,target_values=target_values,target_name=target_name,quantity_specs=quantity_specs,domain_ids=domain_ids,search_shell=search_shell)

