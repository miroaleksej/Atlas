from __future__ import annotations

import argparse, hashlib, itertools, json, math, sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT_DEFAULT=Path(__file__).resolve().parents[1]
if str(ROOT_DEFAULT) not in sys.path:
    sys.path.insert(0,str(ROOT_DEFAULT))

from evaluation.exoplanet_nasa2026_blind_experiment import (
    DORMANT_AXES, add_base_columns, representative_hosts, residual_frame,
    candidate_vectors, closure_score, sha256_file, source_table_kind,
)
from source.lawspace.mathematical_invention import FunctionLanguageBirthEngine
from source.lawspace.query_research import _fit_language_model, _predict_language_model, _language_variants
from source.lawspace.schema import digest_payload

FOLDS=4
REPEATS=5
STAGE1_REPEATS=3
TOP_COORDS=8
DEEPEN_COORDS=10
STAGE1_SURVIVORS_PER_FAMILY=6


def bucket(group:str,salt:str,folds:int=FOLDS)->int:
    return int(hashlib.sha256(f"{salt}::{group}".encode()).hexdigest()[:16],16)%folds


def add_derived_axes(df:pd.DataFrame, births:Sequence[Mapping[str,Any]]) -> tuple[pd.DataFrame,list[dict[str,Any]]]:
    out=df.copy(); rows=[]
    for birth in births:
        exps=dict(birth.get('exponents',{})); aid=str(birth.get('axis_id','')).strip()
        if not aid or not exps: continue
        col=np.ones(len(out),float); ok=True
        for name,pow_ in exps.items():
            if name not in out.columns: ok=False; break
            col*=np.power(pd.to_numeric(out[name],errors='coerce').to_numpy(float),int(pow_))
        if not ok: continue
        out[aid]=col
        rows.append({**dict(birth),'materialized_column':aid,'finite_count':int(np.isfinite(col).sum())})
    return out,rows


def fit_base(train:pd.DataFrame, axes:Sequence[str]):
    y=train['frozen_log_residual'].to_numpy(float)
    if not axes:
        beta=np.asarray([float(np.mean(y))])
        return {'axes':[],'beta':beta.tolist()}
    # Previous deep shell selected one sparse interaction term. Preserve that exact representation.
    x=np.ones(len(train),float)
    for a in axes: x*=train[a].to_numpy(float)
    X=np.column_stack([np.ones(len(train)),x])
    beta,*_=np.linalg.lstsq(X,y,rcond=None)
    return {'axes':list(axes),'beta':[float(v) for v in beta]}


def predict_base(df:pd.DataFrame,state:Mapping[str,Any])->np.ndarray:
    axes=list(state.get('axes',[])); beta=np.asarray(state['beta'],float)
    if not axes: return np.full(len(df),beta[0],float)
    x=np.ones(len(df),float)
    for a in axes: x*=df[a].to_numpy(float)
    return beta[0]+beta[1]*x


def nrmse(y:np.ndarray,p:np.ndarray)->float:
    den=float(np.std(y))
    return float(np.sqrt(np.mean((y-p)**2))/den) if den>1e-14 else math.inf


def fold_eval(df:pd.DataFrame, *, family:str, zone:Sequence[str], variant:Mapping[str,Any], base_axes:Sequence[str], salt:str):
    gains=[]; rows=[]
    for f in range(FOLDS):
        mask=np.asarray([bucket(str(g),salt)==f for g in df['hostname']],bool)
        te=df.loc[mask]; tr=df.loc[~mask]
        if len(te)<8 or len(tr)<30: continue
        bs=fit_base(tr,base_axes)
        ytr=tr['frozen_log_residual'].to_numpy(float); yte=te['frozen_log_residual'].to_numpy(float)
        btr=predict_base(tr,bs); bte=predict_base(te,bs)
        fit=_fit_language_model(tr[list(zone)].to_numpy(float), ytr-btr, family, variant)
        if fit is None: continue
        rp=_predict_language_model(te[list(zone)].to_numpy(float),fit['model_state'])
        if rp is None or np.any(~np.isfinite(rp)): continue
        b=nrmse(yte,bte); a=nrmse(yte,bte+rp)
        gain=(b-a)/max(abs(b),1e-30)
        gains.append(float(gain)); rows.append({'fold':f,'base_nrmse':b,'candidate_nrmse':a,'relative_gain':float(gain),'train':len(tr),'test':len(te)})
    if not gains:
        return {'passes':False,'valid_fold_count':0,'rows':rows,'robust_margin':-math.inf,'median_gain':-math.inf,'positive_fraction':0.0}
    arr=np.asarray(gains,float); med=float(np.median(arr)); mad=float(np.median(np.abs(arr-med))); sig=1.4826*mad; margin=med-sig; pos=float(np.mean(arr>0))
    passes=bool(len(arr)>=3 and pos>=0.75 and med>0 and margin>0)
    return {'passes':passes,'valid_fold_count':len(arr),'median_gain':med,'mad':mad,'robust_sigma':sig,'robust_margin':margin,'positive_fraction':pos,'rows':rows}


def repeated_stability(df:pd.DataFrame, *, family:str, zone:Sequence[str], variant:Mapping[str,Any], base_axes:Sequence[str], repeats:int):
    parts=[fold_eval(df,family=family,zone=zone,variant=variant,base_axes=base_axes,salt=f'LANG-{family}-R{i:02d}') for i in range(repeats)]
    passes=[bool(p['passes']) for p in parts]; margins=np.asarray([float(p['robust_margin']) for p in parts],float); meds=np.asarray([float(p['median_gain']) for p in parts],float); pos=np.asarray([float(p['positive_fraction']) for p in parts],float)
    allg=[float(r['relative_gain']) for p in parts for r in p['rows']]
    if allg:
        a=np.asarray(allg,float); pm=float(np.median(a)); mad=float(np.median(np.abs(a-pm))); ps=1.4826*mad; pmar=pm-ps; ppos=float(np.mean(a>0))
    else: pm=mad=ps=pmar=ppos=0.0
    passfrac=float(np.mean(passes)) if passes else 0.0
    final=bool(passfrac>=0.60 and float(np.median(margins))>0 and float(np.median(meds))>0 and float(np.median(pos))>=0.75 and pmar>0 and ppos>=0.70)
    return {'passes':final,'repeat_count':repeats,'repeat_pass_fraction':passfrac,'median_repeat_robust_margin':float(np.median(margins)),'median_repeat_gain':float(np.median(meds)),'pooled_median_gain':pm,'pooled_robust_margin':pmar,'pooled_positive_fraction':ppos,'partitions':parts}


def spec_key(s): return (s['family'],tuple(s['zone']),json.dumps(s['variant'],sort_keys=True))


def rank_key(row):
    st=row['stability']
    return (-int(bool(st['passes'])),-float(st['repeat_pass_fraction']),-float(st['pooled_robust_margin']),-float(st['pooled_median_gain']),len(row['zone']),row['family'],tuple(row['zone']),json.dumps(row['variant'],sort_keys=True))


def model_complexity(family:str,zone:Sequence[str],variant:Mapping[str,Any])->int:
    # exact model term count using a tiny non-degenerate dummy is unreliable for LATENT SVD;
    # use deterministic structural proxy only as final tie breaker.
    if family=='EXPONENTIAL': return 1+3*len(zone)
    if family=='LATENT':
        k=min(int(variant.get('components',1)),len(zone)); degree=int(variant.get('degree',2));
        # number monomials up to degree including intercept approximated by comb(k+d,d)
        return math.comb(k+degree,degree)
    return 999


def born_axes_from_model(family:str,zone:Sequence[str],fit:Mapping[str,Any],variant:Mapping[str,Any])->list[dict[str,Any]]:
    state=dict(fit['model_state']); rows=[]
    mu=list(state.get('mean',[])); scale=list(state.get('scale',[]))
    if family=='LATENT':
        for k,w in enumerate(state.get('components',[])):
            core={'family':'LATENT','component_index':k,'source_axis_ids':list(zone),'weights':[float(x) for x in w],'standardization_mean':[float(x) for x in mu],'standardization_scale':[float(x) for x in scale],'expression':'latent_projection(standardized['+','.join(zone)+'])','dimension':[0.0]*7,'origin':'FUNCTION_LANGUAGE_BIRTH_DEEP_SHELL'}
            aid='LATENT-'+digest_payload(core)[:20].upper(); row={**core,'axis_id':aid,'status':'RESEARCH_LOCAL_DERIVED_AXIS_CANDIDATE','activation_state':'RESEARCH_LOCAL_DERIVED_CANDIDATE','canonical':False,'causally_established':False,'promotion_required_for_canonical_registration':True}; rows.append({**row,'digest':digest_payload(row)})
    elif family=='EXPONENTIAL':
        s=float(variant.get('scale',1.0))
        for j,a in enumerate(zone):
            for sign in (1,-1):
                core={'family':'EXPONENTIAL','source_axis_ids':[a],'scale_parameter':s,'sign':sign,'standardization_mean':float(mu[j]),'standardization_scale':float(scale[j]),'expression':f'exp({sign*s:+g}*standardize({a}))','dimension':[0.0]*7,'origin':'FUNCTION_LANGUAGE_BIRTH_DEEP_SHELL'}
                aid='EXP-'+digest_payload(core)[:20].upper(); row={**core,'axis_id':aid,'status':'RESEARCH_LOCAL_DERIVED_AXIS_CANDIDATE','activation_state':'RESEARCH_LOCAL_DERIVED_CANDIDATE','canonical':False,'causally_established':False,'promotion_required_for_canonical_registration':True}; rows.append({**row,'digest':digest_payload(row)})
    elif family=='KERNEL':
        gamma=float(state.get('gamma',variant.get('gamma',1.0)))
        for k,c in enumerate(state.get('centers',[])):
            core={'family':'KERNEL','center_index':k,'source_axis_ids':list(zone),'center':[float(x) for x in c],'gamma':gamma,'standardization_mean':[float(x) for x in mu],'standardization_scale':[float(x) for x in scale],'expression':'rbf(standardized['+','.join(zone)+'])','dimension':[0.0]*7,'origin':'FUNCTION_LANGUAGE_BIRTH_DEEP_SHELL'}
            aid='KERNEL-'+digest_payload(core)[:20].upper(); row={**core,'axis_id':aid,'status':'RESEARCH_LOCAL_DERIVED_AXIS_CANDIDATE','activation_state':'RESEARCH_LOCAL_DERIVED_CANDIDATE','canonical':False,'causally_established':False,'promotion_required_for_canonical_registration':True}; rows.append({**row,'digest':digest_payload(row)})
    return rows


def run(root:Path,csv_path:Path,deep_receipt_path:Path)->dict[str,Any]:
    deep=json.loads(deep_receipt_path.read_text())
    raw=pd.read_csv(csv_path,comment='#'); table_kind=source_table_kind(raw); base=add_base_columns(raw)
    disc=base[base['split']=='discovery']; ranking=[]
    for v in candidate_vectors(): ranking.append((closure_score(disc,v)['rho'],sum(abs(e) for e in v),v,closure_score(disc,v)))
    ranking.sort(); winner=ranking[0][2]; meanlog=float(ranking[0][3]['mean_logC'])
    rep=representative_hosts(base); rf=residual_frame(rep,winner,meanlog)
    rf,materialized=add_derived_axes(rf,deep.get('research_local_derived_axis_births',[]))
    # Keep exactly the complete-case population inherited from the previous shell.
    aug_axes=list(DORMANT_AXES)+[r['materialized_column'] for r in materialized]
    finite=np.all(np.isfinite(rf[['frozen_log_residual',*aug_axes]].to_numpy(float)),axis=1); rf=rf.loc[finite].copy()
    discovery=rf[rf['split']=='discovery'].copy(); validation=rf[rf['split']=='validation'].copy(); sealed=rf[rf['split']=='sealed'].copy()
    base_axes=list(deep.get('effective_predictors') or deep.get('selected_axes') or [])

    # Re-diagnose after the previous deep-shell representation, but retain the already-born
    # LATENT+EXPONENTIAL languages as persistent research state even if the new residual changes ranking.
    base_state=fit_base(discovery,base_axes); residual2=discovery['frozen_log_residual'].to_numpy(float)-predict_base(discovery,base_state)
    birth=FunctionLanguageBirthEngine().diagnose(coordinates=discovery[aug_axes].to_numpy(float),residuals=residual2,baseline_nrmse=float(deep['best_hypothesis']['holdout_nrmse']),minimum_birth_nrmse=0.08,minimum_signal=0.12)
    prior_langs={str(x['family']):x for x in deep['function_language_birth'].get('generated_languages',[]) if str(x.get('family')) in {'LATENT','EXPONENTIAL'}}
    current_langs={str(x['family']):x for x in birth.get('generated_languages',[]) if str(x.get('family')) in {'LATENT','EXPONENTIAL'}}
    langs={**prior_langs,**current_langs}
    families=[f for f in ('LATENT','EXPONENTIAL') if f in langs]
    if not families: raise RuntimeError('persisted LATENT/EXPONENTIAL languages missing')

    original_index={i:n for i,n in enumerate(DORMANT_AXES)}
    derived=[r['materialized_column'] for r in materialized]
    family_pools={}
    for fam in families:
        pref=[original_index[i] for i in langs[fam].get('coordinate_preference',[]) if i in original_index]
        pool=[]
        for n in pref[:TOP_COORDS]:
            if n not in pool: pool.append(n)
        for n in derived:
            if n not in pool: pool.append(n)
        family_pools[fam]=pool

    stage1=[]
    for fam,pool in family_pools.items():
        zones=[]
        if fam=='EXPONENTIAL': zones.extend((x,) for x in pool)
        zones.extend(itertools.combinations(pool,2))
        for zone in zones:
            for variant in _language_variants(fam,len(zone)):
                st=repeated_stability(discovery,family=fam,zone=zone,variant=variant,base_axes=base_axes,repeats=STAGE1_REPEATS)
                stage1.append({'family':fam,'zone':list(zone),'variant':dict(variant),'complexity_proxy':model_complexity(fam,zone,variant),'stability':st})
    stage1.sort(key=rank_key)

    stage2_specs=[]
    for fam in families:
        seeds=[r for r in stage1 if r['family']==fam][:STAGE1_SURVIVORS_PER_FAMILY]
        # Deepen around each surviving zone with coordinates from a wider residual-driven pool.
        lang=langs[fam]; pref=[original_index[i] for i in lang.get('coordinate_preference',[]) if i in original_index]
        wider=[]
        for n in pref[:DEEPEN_COORDS]+derived:
            if n not in wider:wider.append(n)
        for seed in seeds:
            z=tuple(seed['zone'])
            stage2_specs.append({'family':fam,'zone':z,'variant':seed['variant']})
            if len(z)<3:
                for extra in wider:
                    if extra in z: continue
                    nz=tuple(sorted((*z,extra)))
                    for variant in _language_variants(fam,len(nz)):
                        stage2_specs.append({'family':fam,'zone':nz,'variant':dict(variant)})
    uniq={spec_key(s):s for s in stage2_specs}
    stage2=[]
    for s in uniq.values():
        st=repeated_stability(discovery,family=s['family'],zone=s['zone'],variant=s['variant'],base_axes=base_axes,repeats=REPEATS)
        stage2.append({'family':s['family'],'zone':list(s['zone']),'variant':dict(s['variant']),'complexity_proxy':model_complexity(s['family'],s['zone'],s['variant']),'stability':st})
    stage2.sort(key=rank_key)
    selected=stage2[0]

    # Freeze selected discovery representation before looking at outer validation.
    full_base=fit_base(discovery,base_axes); ydis=discovery['frozen_log_residual'].to_numpy(float); bdis=predict_base(discovery,full_base)
    fit=_fit_language_model(discovery[selected['zone']].to_numpy(float),ydis-bdis,selected['family'],selected['variant'])
    if fit is None: raise RuntimeError('selected language model failed full-discovery refit')
    pdis=bdis+_predict_language_model(discovery[selected['zone']].to_numpy(float),fit['model_state'])
    yval=validation['frozen_log_residual'].to_numpy(float); bval=predict_base(validation,full_base); rval=_predict_language_model(validation[selected['zone']].to_numpy(float),fit['model_state']); pval=bval+rval
    discovery_eval={'base_nrmse':nrmse(ydis,bdis),'language_nrmse':nrmse(ydis,pdis)}
    validation_eval={'base_nrmse':nrmse(yval,bval),'language_nrmse':nrmse(yval,pval),'relative_gain':(nrmse(yval,bval)-nrmse(yval,pval))/nrmse(yval,bval)}

    per_family={}
    per_family_outer_validation={}
    born=[]
    for fam in families:
        row=next((r for r in stage2 if r['family']==fam),None)
        if row is None: continue
        # Materialize representation candidates only when discovery stability passes.
        ff=None
        if row['stability']['passes']:
            ff=_fit_language_model(discovery[row['zone']].to_numpy(float),ydis-bdis,fam,row['variant'])
            if ff is not None:
                born.extend(born_axes_from_model(fam,row['zone'],ff,row['variant']))
                dp=_predict_language_model(discovery[row['zone']].to_numpy(float),ff['model_state'])
                vp=_predict_language_model(validation[row['zone']].to_numpy(float),ff['model_state'])
                db=nrmse(ydis,bdis); da=nrmse(ydis,bdis+dp); vb=nrmse(yval,bval); va=nrmse(yval,bval+vp)
                per_family_outer_validation[fam]={
                    'discovery_base_nrmse':db,'discovery_language_nrmse':da,
                    'validation_base_nrmse':vb,'validation_language_nrmse':va,
                    'validation_relative_gain':(vb-va)/max(abs(vb),1e-30),
                    'model_state':ff['model_state'],
                    'validation_used_for_family_selection':False,
                }
        per_family[fam]=row

    current_supported_families=sorted(current_langs)
    current_supported_branch=next((r for r in stage2 if r['family'] in current_supported_families),None)

    payload={
        'schema':'atlas-exoplanet-language-shell-exploratory/v1',
        'protocol':'DISCOVERY_ONLY_SELECTIVE_LANGUAGE_DEEPENING_THEN_OUTER_VALIDATION',
        'source':{'path':str(csv_path),'sha256':sha256_file(csv_path),'table_kind':table_kind},
        'previous_deep_receipt_digest':deep.get('digest'),
        'previous_selected_axes':base_axes,
        'materialized_previous_derived_axes':materialized,
        'counts':{'discovery':len(discovery),'validation':len(validation),'sealed_not_read_for_selection_or_report':len(sealed)},
        'language_state':{'persisted_from_previous_shell':list(prior_langs.values()),'rediagnosed_after_previous_deep_model':birth,'families_explored':families},
        'search':{
            'stage1_policy':'RESIDUAL_PREFERENCE_SINGLE_PAIR_RECONNAISSANCE',
            'stage1_trial_count':len(stage1),'stage1_stability_repeats':STAGE1_REPEATS,
            'stage2_policy':'TOP_DISCOVERY_ZONES_SELECTIVE_TRIPLE_DEEPENING',
            'stage2_trial_count':len(stage2),'stage2_stability_repeats':REPEATS,
            'finite_trial_budget_is_scientific_space_ceiling':False,
            'family_coordinate_pools':family_pools,
            'stage1_top20':stage1[:20],
            'stage2_top30':stage2[:30],
        },
        'selected_discovery_representation':selected,
        'per_family_best_discovery_representation':per_family,
        'per_family_outer_validation_after_discovery_freeze':per_family_outer_validation,
        'current_residual_supported_families':current_supported_families,
        'current_residual_supported_branch':current_supported_branch,
        'discovery_fit':discovery_eval,
        'outer_validation_after_freeze':validation_eval,
        'research_local_language_axis_births':born,
        'sealed_evaluated':False,
        'claim_boundary':{
            'new_law_established':False,'causal_axis_established':False,
            'validation_used_for_language_or_zone_selection':False,
            'sealed_used_for_language_or_zone_selection':False,
            'validation_is_fresh_unseen_confirmation':False,
            'search_is_exhaustive':False,
            'research_local_axes_are_promoted_canonical_axes':False,
        },
    }
    return {**payload,'digest':digest_payload(payload)}



def add_language_axes(df:pd.DataFrame, births:Sequence[Mapping[str,Any]]) -> tuple[pd.DataFrame,list[dict[str,Any]]]:
    """Materialize frozen research-local language axes without promoting them."""
    out=df.copy(); rows=[]
    for birth in births:
        fam=str(birth.get('family','')); aid=str(birth.get('axis_id','')).strip(); col=None
        if not aid: continue
        if fam=='LATENT':
            src=list(birth.get('source_axis_ids',[]))
            if not src or any(a not in out.columns for a in src): continue
            X=np.column_stack([pd.to_numeric(out[a],errors='coerce').to_numpy(float) for a in src])
            mu=np.asarray(birth.get('standardization_mean',[]),float); sc=np.asarray(birth.get('standardization_scale',[]),float); w=np.asarray(birth.get('weights',[]),float)
            if X.shape[1]!=len(mu) or len(mu)!=len(sc) or len(sc)!=len(w): continue
            col=((X-mu)/sc)@w
        elif fam=='EXPONENTIAL':
            src=list(birth.get('source_axis_ids',[]))
            if len(src)!=1 or src[0] not in out.columns: continue
            z=(pd.to_numeric(out[src[0]],errors='coerce').to_numpy(float)-float(birth['standardization_mean']))/float(birth['standardization_scale'])
            col=np.exp(float(birth.get('sign',1))*float(birth.get('scale_parameter',1.0))*z)
        elif fam=='KERNEL':
            src=list(birth.get('source_axis_ids',[]))
            if not src or any(a not in out.columns for a in src): continue
            X=np.column_stack([pd.to_numeric(out[a],errors='coerce').to_numpy(float) for a in src])
            mu=np.asarray(birth.get('standardization_mean',[]),float); sc=np.asarray(birth.get('standardization_scale',[]),float); center=np.asarray(birth.get('center',[]),float)
            if X.shape[1]!=len(mu) or len(mu)!=len(sc) or len(sc)!=len(center): continue
            z=(X-mu)/sc; col=np.exp(-float(birth.get('gamma',1.0))*np.sum((z-center[None,:])**2,axis=1))
        if col is None: continue
        out[aid]=col; rows.append({**dict(birth),'materialized_column':aid,'finite_count':int(np.isfinite(col).sum())})
    return out,rows


def fit_prior_latent_stack(train:pd.DataFrame, deep_axes:Sequence[str], latent_axis:str)->dict[str,Any]:
    """Refit coefficients of the already-frozen deep+L structure inside each discovery fold."""
    deep=fit_base(train,deep_axes); y=train['frozen_log_residual'].to_numpy(float); p0=predict_base(train,deep)
    L=train[latent_axis].to_numpy(float); X=np.column_stack([np.ones(len(train)),L,L*L]); beta,*_=np.linalg.lstsq(X,y-p0,rcond=None)
    return {'deep':deep,'latent_axis':str(latent_axis),'latent_coefficients':[float(v) for v in beta]}


def predict_prior_latent_stack(df:pd.DataFrame,state:Mapping[str,Any])->np.ndarray:
    p=predict_base(df,state['deep']); L=df[str(state['latent_axis'])].to_numpy(float); b=np.asarray(state['latent_coefficients'],float)
    return p+b[0]+b[1]*L+b[2]*L*L


def post_latent_fold_eval(df:pd.DataFrame, *, family:str, zone:Sequence[str], variant:Mapping[str,Any], deep_axes:Sequence[str], latent_axis:str, salt:str):
    gains=[]; rows=[]
    for f in range(FOLDS):
        mask=np.asarray([bucket(str(g),salt)==f for g in df['hostname']],bool); te=df.loc[mask]; tr=df.loc[~mask]
        if len(te)<8 or len(tr)<30: continue
        base=fit_prior_latent_stack(tr,deep_axes,latent_axis); ytr=tr['frozen_log_residual'].to_numpy(float); yte=te['frozen_log_residual'].to_numpy(float)
        btr=predict_prior_latent_stack(tr,base); bte=predict_prior_latent_stack(te,base)
        fit=_fit_language_model(tr[list(zone)].to_numpy(float),ytr-btr,family,variant)
        if fit is None: continue
        rp=_predict_language_model(te[list(zone)].to_numpy(float),fit['model_state'])
        if rp is None or np.any(~np.isfinite(rp)): continue
        bn=nrmse(yte,bte); an=nrmse(yte,bte+rp); gain=(bn-an)/max(abs(bn),1e-30)
        gains.append(float(gain)); rows.append({'fold':f,'base_nrmse':bn,'candidate_nrmse':an,'relative_gain':float(gain),'train':len(tr),'test':len(te)})
    if not gains: return {'passes':False,'valid_fold_count':0,'rows':rows,'robust_margin':-math.inf,'median_gain':-math.inf,'positive_fraction':0.0}
    arr=np.asarray(gains,float); med=float(np.median(arr)); mad=float(np.median(np.abs(arr-med))); sig=1.4826*mad; margin=med-sig; pos=float(np.mean(arr>0))
    return {'passes':bool(len(arr)>=3 and pos>=0.75 and med>0 and margin>0),'valid_fold_count':len(arr),'median_gain':med,'mad':mad,'robust_sigma':sig,'robust_margin':margin,'positive_fraction':pos,'rows':rows}


def post_latent_repeated_stability(df:pd.DataFrame, *, family:str, zone:Sequence[str], variant:Mapping[str,Any], deep_axes:Sequence[str], latent_axis:str, repeats:int):
    parts=[post_latent_fold_eval(df,family=family,zone=zone,variant=variant,deep_axes=deep_axes,latent_axis=latent_axis,salt=f'POSTL-{family}-R{i:02d}') for i in range(repeats)]
    passes=[bool(p['passes']) for p in parts]; margins=np.asarray([float(p['robust_margin']) for p in parts],float); meds=np.asarray([float(p['median_gain']) for p in parts],float); pos=np.asarray([float(p['positive_fraction']) for p in parts],float); allg=[float(r['relative_gain']) for p in parts for r in p['rows']]
    if allg:
        a=np.asarray(allg,float); pm=float(np.median(a)); mad=float(np.median(np.abs(a-pm))); pmar=pm-1.4826*mad; ppos=float(np.mean(a>0))
    else: pm=pmar=ppos=0.0
    passfrac=float(np.mean(passes)) if passes else 0.0
    final=bool(passfrac>=0.60 and float(np.median(margins))>0 and float(np.median(meds))>0 and float(np.median(pos))>=0.75 and pmar>0 and ppos>=0.70)
    return {'passes':final,'repeat_count':repeats,'repeat_pass_fraction':passfrac,'median_repeat_robust_margin':float(np.median(margins)),'median_repeat_gain':float(np.median(meds)),'pooled_median_gain':pm,'pooled_robust_margin':pmar,'pooled_positive_fraction':ppos,'partitions':parts}


def run_post_latent(root:Path,csv_path:Path,deep_receipt_path:Path,previous_language_receipt_path:Path)->dict[str,Any]:
    """Continue from the frozen research-local L axis; validation remains outer-only and sealed unread."""
    deep=json.loads(deep_receipt_path.read_text()); prev=json.loads(previous_language_receipt_path.read_text())
    raw=pd.read_csv(csv_path,comment='#'); table_kind=source_table_kind(raw); base=add_base_columns(raw); disc0=base[base['split']=='discovery']; ranking=[]
    for v in candidate_vectors():
        sc=closure_score(disc0,v); ranking.append((sc['rho'],sum(abs(e) for e in v),v,sc))
    ranking.sort(); winner=ranking[0][2]; meanlog=float(ranking[0][3]['mean_logC'])
    rf=residual_frame(representative_hosts(base),winner,meanlog); rf,prod=add_derived_axes(rf,deep.get('research_local_derived_axis_births',[])); rf,lang=add_language_axes(rf,prev.get('research_local_language_axis_births',[]))
    latent_birth=next((b for b in prev.get('research_local_language_axis_births',[]) if b.get('family')=='LATENT'),None)
    if latent_birth is None: raise RuntimeError('previous language receipt has no LATENT research-local axis')
    latent_axis=str(latent_birth['axis_id']); deep_axes=list(prev.get('previous_selected_axes',[])); aug=list(DORMANT_AXES)+[r['materialized_column'] for r in prod]+[r['materialized_column'] for r in lang]
    finite=np.all(np.isfinite(rf[['frozen_log_residual',*aug]].to_numpy(float)),axis=1); rf=rf.loc[finite].copy(); discovery=rf[rf['split']=='discovery']; validation=rf[rf['split']=='validation']; sealed=rf[rf['split']=='sealed']
    prior=fit_prior_latent_stack(discovery,deep_axes,latent_axis); y=discovery['frozen_log_residual'].to_numpy(float); bp=predict_prior_latent_stack(discovery,prior); post=y-bp; baseline=nrmse(y,bp)
    birth=FunctionLanguageBirthEngine().diagnose(coordinates=discovery[aug].to_numpy(float),residuals=post,baseline_nrmse=baseline,minimum_birth_nrmse=0.08,minimum_signal=0.12)
    langs={str(x['family']):x for x in birth.get('generated_languages',[])}; families=list(langs)
    if not families: raise RuntimeError('post-L residual did not birth a new function language')
    index={i:n for i,n in enumerate(aug)}; persistent=[r['materialized_column'] for r in prod+lang]; pools={}
    for fam,spec in langs.items():
        pool=[]
        for i in spec.get('coordinate_preference',[])[:8]:
            if i in index and index[i] not in pool: pool.append(index[i])
        for name in persistent:
            if name in pool: continue
            if name==latent_axis or name.startswith('DERIVED-') or name in [index.get(i) for i in spec.get('coordinate_preference',[])[:10]]: pool.append(name)
        pools[fam]=pool
    stage1=[]
    for fam,pool in pools.items():
        for zone in [(x,) for x in pool]+list(itertools.combinations(pool,2)):
            for variant in _language_variants(fam,len(zone)):
                st=post_latent_repeated_stability(discovery,family=fam,zone=zone,variant=variant,deep_axes=deep_axes,latent_axis=latent_axis,repeats=1)
                stage1.append({'family':fam,'zone':list(zone),'variant':dict(variant),'complexity_proxy':model_complexity(fam,zone,variant),'stability':st})
    stage1.sort(key=rank_key); stage2_specs=[]
    for fam in families:
        seeds=[r for r in stage1 if r['family']==fam and r['stability']['passes']][:5] or [r for r in stage1 if r['family']==fam][:5]
        wider=[]
        for i in langs[fam].get('coordinate_preference',[])[:12]:
            if i in index and index[i] not in wider: wider.append(index[i])
        for name in persistent:
            if name not in wider: wider.append(name)
        for seed in seeds:
            z=tuple(seed['zone']); stage2_specs.append({'family':fam,'zone':z,'variant':seed['variant']})
            if len(z)<3:
                for extra in wider:
                    if extra in z: continue
                    stage2_specs.append({'family':fam,'zone':tuple(sorted((*z,extra))),'variant':dict(seed['variant'])})
    uniq={spec_key(s):s for s in stage2_specs}; stage2=[]
    for s in uniq.values():
        st=post_latent_repeated_stability(discovery,family=s['family'],zone=s['zone'],variant=s['variant'],deep_axes=deep_axes,latent_axis=latent_axis,repeats=5)
        stage2.append({'family':s['family'],'zone':list(s['zone']),'variant':dict(s['variant']),'complexity_proxy':model_complexity(s['family'],s['zone'],s['variant']),'stability':st})
    stage2.sort(key=rank_key); selected=stage2[0]
    prior=fit_prior_latent_stack(discovery,deep_axes,latent_axis); ydis=discovery['frozen_log_residual'].to_numpy(float); bdis=predict_prior_latent_stack(discovery,prior); fit=_fit_language_model(discovery[selected['zone']].to_numpy(float),ydis-bdis,selected['family'],selected['variant'])
    if fit is None: raise RuntimeError('selected post-L language model failed full-discovery refit')
    dp=_predict_language_model(discovery[selected['zone']].to_numpy(float),fit['model_state']); yval=validation['frozen_log_residual'].to_numpy(float); bval=predict_prior_latent_stack(validation,prior); vp=_predict_language_model(validation[selected['zone']].to_numpy(float),fit['model_state'])
    per_family={}; outer={}; newborn=[]
    for fam in families:
        row=next((r for r in stage2 if r['family']==fam),None); per_family[fam]=row
        if row is not None and row['stability']['passes']:
            ff=_fit_language_model(discovery[row['zone']].to_numpy(float),ydis-bdis,fam,row['variant'])
            if ff is not None:
                dd=_predict_language_model(discovery[row['zone']].to_numpy(float),ff['model_state']); vv=_predict_language_model(validation[row['zone']].to_numpy(float),ff['model_state']); db=nrmse(ydis,bdis); da=nrmse(ydis,bdis+dd); vb=nrmse(yval,bval); va=nrmse(yval,bval+vv)
                outer[fam]={'discovery_base_nrmse':db,'discovery_language_nrmse':da,'validation_base_nrmse':vb,'validation_language_nrmse':va,'validation_relative_gain':(vb-va)/max(abs(vb),1e-30),'model_state':ff['model_state'],'validation_used_for_family_selection':False}; newborn.extend(born_axes_from_model(fam,row['zone'],ff,row['variant']))
    post2=ydis-(bdis+dp); next_birth=FunctionLanguageBirthEngine().diagnose(coordinates=discovery[aug].to_numpy(float),residuals=post2,baseline_nrmse=nrmse(ydis,bdis+dp),minimum_birth_nrmse=0.08,minimum_signal=0.12)
    payload={'schema':'atlas-exoplanet-post-latent-shell/v1','protocol':'FROZEN_RESEARCH_LOCAL_LATENT_AXIS_THEN_DISCOVERY_ONLY_LANGUAGE_BIRTH_AND_SELECTIVE_DEEPENING','source':{'path':str(csv_path),'sha256':sha256_file(csv_path),'table_kind':table_kind},'previous_language_receipt_digest':prev.get('digest'),'previous_latent_axis':latent_birth,'previous_latent_correction_model':prev.get('per_family_outer_validation_after_discovery_freeze',{}).get('LATENT',{}).get('model_state'),'deep_base_axes':deep_axes,'materialized_prior_axes':prod+lang,'counts':{'discovery':len(discovery),'validation':len(validation),'sealed_not_read':len(sealed)},'post_latent_residual_language_birth':birth,'search':{'stage1_policy':'BORN_LANGUAGE_SINGLE_PAIR_RECONNAISSANCE','stage1_trial_count':len(stage1),'stage1_repeats':1,'stage2_policy':'SELECTIVE_DEEPENING_OF_RECONNAISSANCE_SURVIVORS','stage2_trial_count':len(stage2),'stage2_repeats':5,'finite_trial_budget_is_scientific_space_ceiling':False,'family_coordinate_pools':pools,'stage1_top30':stage1[:30],'stage2_top40':stage2[:40]},'selected_discovery_representation':selected,'discovery_fit':{'prior_stack_nrmse':nrmse(ydis,bdis),'new_language_nrmse':nrmse(ydis,bdis+dp)},'outer_validation_after_freeze':{'prior_stack_nrmse':nrmse(yval,bval),'new_language_nrmse':nrmse(yval,bval+vp),'relative_gain':(nrmse(yval,bval)-nrmse(yval,bval+vp))/max(abs(nrmse(yval,bval)),1e-30)},'per_family_best_discovery_representation':per_family,'per_family_outer_validation_after_discovery_freeze':outer,'research_local_new_axis_births':newborn,'next_residual_language_birth_after_selected_discovery_representation':next_birth,'sealed_evaluated':False,'claim_boundary':{'new_law_established':False,'causal_axis_established':False,'validation_used_for_language_or_zone_selection':False,'sealed_used':False,'validation_is_fresh_unseen_confirmation':False,'search_is_exhaustive':False,'newborn_axes_are_canonical':False}}
    return {**payload,'digest':digest_payload(payload)}


def _robust_gain_summary(gains: Sequence[float]) -> dict[str, Any]:
    arr=np.asarray(tuple(float(x) for x in gains),float)
    if len(arr)==0:
        return {'count':0,'median_gain':0.0,'mad':0.0,'robust_sigma':0.0,'robust_margin':0.0,'positive_fraction':0.0,'passes':False}
    med=float(np.median(arr)); mad=float(np.median(np.abs(arr-med))); sig=1.4826*mad; margin=med-sig; pos=float(np.mean(arr>0.0))
    return {'count':int(len(arr)),'median_gain':med,'mad':mad,'robust_sigma':sig,'robust_margin':margin,'positive_fraction':pos,'passes':bool(len(arr)>=4 and pos>=0.75 and med>0.0 and margin>0.0)}


def _tail_stress_post_latent_branch(
    discovery: pd.DataFrame,
    *,
    family: str,
    zone: Sequence[str],
    variant: Mapping[str,Any],
    deep_axes: Sequence[str],
    latent_axis: str,
    tail_fraction: float = 0.15,
) -> dict[str,Any]:
    """Discovery-only regime/tail stress for a nonlinear residual branch.

    Every coordinate in the selected zone is stressed independently in its
    lower and upper empirical tails.  The candidate and its frozen prior stack
    are refit without the stressed rows, then evaluated only on the omitted
    tail.  The same robust gate as the ordinary stability contract is used:
    positive_fraction>=0.75 and median_gain-1.4826*MAD>0.  No validation or
    sealed rows are consumed.
    """
    q=float(tail_fraction); gains=[]; rows=[]
    for axis in tuple(zone):
        values=pd.to_numeric(discovery[axis],errors='coerce').to_numpy(float)
        lo,hi=np.quantile(values,[q,1.0-q])
        for tail,mask in (('LOW',values<=lo),('HIGH',values>=hi)):
            test=discovery.loc[mask]; train=discovery.loc[~mask]
            if len(test)<8 or len(train)<30:
                continue
            base=fit_prior_latent_stack(train,deep_axes,latent_axis)
            ytr=train['frozen_log_residual'].to_numpy(float); yte=test['frozen_log_residual'].to_numpy(float)
            btr=predict_prior_latent_stack(train,base); bte=predict_prior_latent_stack(test,base)
            fit=_fit_language_model(train[list(zone)].to_numpy(float),ytr-btr,family,variant)
            if fit is None:
                continue
            pred=_predict_language_model(test[list(zone)].to_numpy(float),fit['model_state'])
            if pred is None or np.any(~np.isfinite(pred)):
                continue
            before=nrmse(yte,bte); after=nrmse(yte,bte+pred); gain=(before-after)/max(abs(before),1e-30)
            gains.append(float(gain)); rows.append({'axis':axis,'tail':tail,'tail_fraction':q,'train_count':len(train),'test_count':len(test),'base_nrmse':before,'candidate_nrmse':after,'relative_gain':float(gain)})
    return {**_robust_gain_summary(gains),'rows':rows,'validation_used':False,'sealed_used':False}


def run_multibranch_closure(
    root: Path,
    csv_path: Path,
    deep_receipt_path: Path,
    previous_language_receipt_path: Path,
    post_latent_receipt_path: Path,
) -> dict[str,Any]:
    """Close the current residual research tranche with multi-branch search.

    The routine keeps the previously frozen deep axis and LATENT axis, then
    materializes all research-local axes born by the prior two shells.  A broad
    representative-variant reconnaissance covers multiple branch anchors.
    Expensive repeated-CV budget is distributed from discovery-only evidence.
    Final branch promotion requires BOTH repeated host-group stability and the
    discovery-only tail-stress gate.  Validation is reported only after branch
    selection and never rescues a rejected branch; sealed rows remain unread.
    """
    deep=json.loads(deep_receipt_path.read_text()); prev=json.loads(previous_language_receipt_path.read_text()); post=json.loads(post_latent_receipt_path.read_text())
    raw=pd.read_csv(csv_path,comment='#'); table_kind=source_table_kind(raw); base=add_base_columns(raw); disc0=base[base['split']=='discovery']; ranking=[]
    for vector in candidate_vectors():
        score=closure_score(disc0,vector); ranking.append((score['rho'],sum(abs(e) for e in vector),vector,score))
    ranking.sort(); winner=ranking[0][2]; meanlog=float(ranking[0][3]['mean_logC'])
    rf=residual_frame(representative_hosts(base),winner,meanlog)
    rf,prod=add_derived_axes(rf,deep.get('research_local_derived_axis_births',[]))
    rf,old_language=add_language_axes(rf,prev.get('research_local_language_axis_births',[]))
    rf,new_language=add_language_axes(rf,post.get('research_local_new_axis_births',[]))
    latent_birth=next((b for b in prev.get('research_local_language_axis_births',[]) if b.get('family')=='LATENT'),None)
    if latent_birth is None: raise RuntimeError('previous language receipt has no LATENT axis')
    latent_axis=str(latent_birth['axis_id']); post_latent_axes=[str(b['axis_id']) for b in post.get('research_local_new_axis_births',[]) if b.get('family')=='LATENT']
    deep_axis=str((deep.get('research_local_derived_axis_births') or [{}])[0].get('axis_id',''))
    persistent=[r['materialized_column'] for r in prod+old_language+new_language]; aug=list(DORMANT_AXES)+persistent
    finite=np.all(np.isfinite(rf[['frozen_log_residual',*aug]].to_numpy(float)),axis=1); rf=rf.loc[finite].copy(); discovery=rf[rf['split']=='discovery']; validation=rf[rf['split']=='validation']; sealed=rf[rf['split']=='sealed']
    deep_axes=list(prev.get('previous_selected_axes',[])); prior=fit_prior_latent_stack(discovery,deep_axes,latent_axis); y=discovery['frozen_log_residual'].to_numpy(float); bp=predict_prior_latent_stack(discovery,prior); residual=y-bp; baseline=nrmse(y,bp)
    birth=FunctionLanguageBirthEngine().diagnose(coordinates=discovery[aug].to_numpy(float),residuals=residual,baseline_nrmse=baseline,minimum_birth_nrmse=0.08,minimum_signal=0.12)
    languages={str(x['family']):x for x in birth.get('generated_languages',[]) if str(x.get('family')) in {'LATENT','KERNEL'}}
    if not languages: raise RuntimeError('multibranch residual did not birth LATENT or KERNEL')
    index={i:n for i,n in enumerate(aug)}; anchors=[latent_axis,deep_axis,*post_latent_axes]+[r['materialized_column'] for r in old_language if r['materialized_column'] not in {latent_axis,deep_axis,*post_latent_axes}]
    def representative_variant(family:str,zone:Sequence[str])->dict[str,Any]:
        if family=='LATENT': return {'components':min(2,len(zone)),'degree':2,'ridge':1e-5}
        if family=='KERNEL': return {'gamma':0.8,'max_centers':18,'ridge':1e-4}
        raise ValueError(family)
    pools={}; stage1=[]
    for family,spec in languages.items():
        pool=[]
        for i in spec.get('coordinate_preference',[])[:12]:
            if i in index and index[i] not in pool: pool.append(index[i])
        for axis in anchors:
            if axis in aug and axis not in pool: pool.append(axis)
        pool=pool[:18]; pools[family]=pool
        zones=[(x,) for x in pool]+list(itertools.combinations(pool,2))
        for z in ((latent_axis,deep_axis),tuple(post_latent_axes),(latent_axis,*post_latent_axes),(deep_axis,*post_latent_axes),(latent_axis,deep_axis,*post_latent_axes)):
            z=tuple(x for x in z if x in aug)
            if z and len(z)<=3 and z not in zones: zones.append(z)
        for zone in zones:
            variant=representative_variant(family,zone)
            stability=post_latent_repeated_stability(discovery,family=family,zone=zone,variant=variant,deep_axes=deep_axes,latent_axis=latent_axis,repeats=1)
            stage1.append({'family':family,'zone':list(zone),'variant':variant,'stability':stability})
    stage1.sort(key=rank_key); seeds_by_family={}; evidence={}
    for family in languages:
        seeds=[]; seen=set()
        for row in (r for r in stage1 if r['family']==family):
            key=tuple(sorted(row['zone']))
            if key in seen: continue
            if row['stability']['passes'] or len(seeds)<2:
                seeds.append(row); seen.add(key)
            if len(seeds)>=5: break
        seeds_by_family[family]=seeds
        evidence[family]=sum(max(0.0,float(s['stability']['pooled_robust_margin']))*max(0.25,float(s['stability']['pooled_positive_fraction'])) for s in seeds)
    total_evidence=sum(evidence.values()) or 1.0; budgets={family:max(14,int(round(42*evidence[family]/total_evidence))) for family in languages}
    while sum(budgets.values())>48:
        family=max(budgets,key=budgets.get)
        if budgets[family]<=14: break
        budgets[family]-=1
    specs=[]
    for family,seeds in seeds_by_family.items():
        proposals=[]; wider=pools[family][:10]
        for seed in seeds:
            z=tuple(seed['zone']); proposals.append(z)
            if len(z)<3:
                for extra in wider:
                    if extra not in z:
                        nz=tuple(dict.fromkeys((*z,extra)))
                        if len(nz)<=3: proposals.append(nz)
        unique=[]; seen=set()
        for z in proposals:
            if z not in seen: seen.add(z); unique.append(z)
        candidates=[]
        stage1_rank={tuple(r['zone']):i for i,r in enumerate(x for x in stage1 if x['family']==family)}
        for z in unique:
            for variant in _language_variants(family,len(z)):
                candidates.append((family,z,dict(variant)))
        candidates.sort(key=lambda c:(stage1_rank.get(tuple(c[1]),9999),len(c[1]),json.dumps(c[2],sort_keys=True)))
        specs.extend(candidates[:budgets[family]])
    stage2=[]
    for family,zone,variant in specs:
        stability=post_latent_repeated_stability(discovery,family=family,zone=zone,variant=variant,deep_axes=deep_axes,latent_axis=latent_axis,repeats=5)
        stage2.append({'family':family,'zone':list(zone),'variant':dict(variant),'stability':stability})
    stage2.sort(key=rank_key)
    frontier=[]; seen=set()
    for row in stage2:
        key=(row['family'],tuple(sorted(row['zone'])))
        if key in seen: continue
        seen.add(key); stress=_tail_stress_post_latent_branch(discovery,family=row['family'],zone=row['zone'],variant=row['variant'],deep_axes=deep_axes,latent_axis=latent_axis)
        frontier.append({**row,'tail_stress':stress,'joint_pass':bool(row['stability']['passes'] and stress['passes'])})
        if len(frontier)>=12: break
    selected=stage2[0]; fit=_fit_language_model(discovery[selected['zone']].to_numpy(float),residual,selected['family'],selected['variant'])
    if fit is None: raise RuntimeError('selected multibranch model failed full discovery refit')
    dp=_predict_language_model(discovery[selected['zone']].to_numpy(float),fit['model_state']); yval=validation['frozen_log_residual'].to_numpy(float); bval=predict_prior_latent_stack(validation,prior); vp=_predict_language_model(validation[selected['zone']].to_numpy(float),fit['model_state'])
    newborn=born_axes_from_model(selected['family'],selected['zone'],fit,selected['variant']); next_residual=y-(bp+dp); next_birth=FunctionLanguageBirthEngine().diagnose(coordinates=discovery[aug].to_numpy(float),residuals=next_residual,baseline_nrmse=nrmse(y,bp+dp),minimum_birth_nrmse=0.08,minimum_signal=0.12)
    joint=[row for row in frontier if row['joint_pass']]
    payload={'schema':'atlas-exoplanet-multibranch-closure/v2','protocol':'WIDE_RECON_DISCOVERY_EVIDENCE_BUDGETED_DEEPENING_PLUS_DISCOVERY_TAIL_STRESS','source':{'path':str(csv_path),'sha256':sha256_file(csv_path),'table_kind':table_kind},'state':{'deep_axis':deep_axis,'old_latent_axis':latent_axis,'post_latent_axes':post_latent_axes,'persistent_axes':persistent},'counts':{'discovery':len(discovery),'validation':len(validation),'sealed_unread':len(sealed)},'current_language_birth':birth,'search':{'reconnaissance_trial_count':len(stage1),'reconnaissance_repeats':1,'deepening_trial_count':len(stage2),'deepening_repeats':5,'family_coordinate_pools':pools,'discovery_evidence':evidence,'allocated_candidate_budget':budgets,'finite_budget_is_scientific_space_ceiling':False},'frontier':frontier,'joint_pass_count':len(joint),'selected_pre_stress':selected,'discovery_fit':{'prior_stack_nrmse':baseline,'selected_nrmse':nrmse(y,bp+dp),'relative_gain':(baseline-nrmse(y,bp+dp))/max(abs(baseline),1e-30)},'outer_validation_exploratory_only':{'prior_stack_nrmse':nrmse(yval,bval),'selected_nrmse':nrmse(yval,bval+vp),'relative_gain':(nrmse(yval,bval)-nrmse(yval,bval+vp))/max(abs(nrmse(yval,bval)),1e-30)},'newborn_axes_from_pre_stress_selected':newborn,'next_residual_language_birth_after_pre_stress_selected':next_birth,'closure_status':'REPRESENTATION_GAP_FRONTIER_OPEN_NO_STRESS_ROBUST_BRANCH' if not joint else 'STRESS_ROBUST_BRANCH_EXISTS','sealed_evaluated':False,'claim_boundary':{'new_law_established':False,'causal_axis_established':False,'validation_used_for_selection':False,'sealed_used':False,'scientific_confirmation':False,'search_exhaustive':False,'current_cycle_closed_under_declared_budget_and_gates':True,'future_frontier_remains_open':True}}
    return {**payload,'digest':digest_payload(payload)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('deep_receipt'); ap.add_argument('--root',default=str(ROOT_DEFAULT)); ap.add_argument('--out',default=None); ap.add_argument('--previous-language-receipt',default=None); ap.add_argument('--post-latent-receipt',default=None); ap.add_argument('--multibranch-closure',action='store_true'); args=ap.parse_args()
    root=Path(args.root).resolve()
    if args.multibranch_closure:
        if not args.previous_language_receipt or not args.post_latent_receipt:
            raise SystemExit('--multibranch-closure requires --previous-language-receipt and --post-latent-receipt')
        out=run_multibranch_closure(root,Path(args.csv),Path(args.deep_receipt),Path(args.previous_language_receipt),Path(args.post_latent_receipt))
        default_out=root/'reports'/'NASA_EXOPLANET_MULTIBRANCH_CLOSURE_CURRENT.json'
    elif args.previous_language_receipt:
        out=run_post_latent(root,Path(args.csv),Path(args.deep_receipt),Path(args.previous_language_receipt))
        default_out=root/'reports'/'NASA_EXOPLANET_POST_LATENT_SHELL_EXPLORATORY.json'
    else:
        out=run(root,Path(args.csv),Path(args.deep_receipt))
        default_out=root/'reports'/'NASA_EXOPLANET_LANGUAGE_SHELL_EXPLORATORY.json'
    out_path=Path(args.out).resolve() if args.out else default_out
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.multibranch_closure:
        s=out['selected_pre_stress']; born_count=len(out.get('newborn_axes_from_pre_stress_selected',[])); ts=(out.get('frontier') or [{}])[0].get('tail_stress',{})
        print(json.dumps({'selected_family':s['family'],'selected_zone':s['zone'],'variant':s['variant'],'stability':{k:s['stability'][k] for k in ['passes','repeat_pass_fraction','pooled_median_gain','pooled_robust_margin','pooled_positive_fraction']},'tail_stress':{k:ts.get(k) for k in ['passes','median_gain','robust_margin','positive_fraction']},'joint_pass_count':out.get('joint_pass_count'),'closure_status':out.get('closure_status'),'discovery_fit':out['discovery_fit'],'outer_validation_exploratory_only':out['outer_validation_exploratory_only'],'born_axis_count':born_count,'report':str(out_path),'digest':out['digest']},ensure_ascii=False,indent=2))
    else:
        s=out['selected_discovery_representation']; born_count=len(out.get('research_local_language_axis_births',out.get('research_local_new_axis_births',[])))
        print(json.dumps({'selected_family':s['family'],'selected_zone':s['zone'],'variant':s['variant'],'stability':{k:s['stability'][k] for k in ['passes','repeat_pass_fraction','pooled_median_gain','pooled_robust_margin','pooled_positive_fraction']},'discovery_fit':out['discovery_fit'],'outer_validation_after_freeze':out['outer_validation_after_freeze'],'born_axis_count':born_count,'report':str(out_path),'digest':out['digest']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
