"""Query-driven scientific research over supplied observations.

Authoritative focused mode: observations/question -> finite search surface -> ranked
mathematical candidates.  The display limit is never the multiplicity budget: null
calibration records and replays the complete examined surface.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Any, Mapping, Sequence
import math
import numpy as np

from source.phi_compiler_owner import _fraction_nullspace
from .schema import digest_payload
from .dimensional_law_birth import collapse_score

OWNER_ID = "QUERY-DRIVEN-RESEARCH/1.0.0"
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
        candidates=[]; examined_subsets=0; groups_examined=0
        for k in range(max(2,int(min_subset_size)),maxk+1):
            for subset in combinations(feature_names,k):
                examined_subsets+=1
                matrix=[[Fraction(int(dimensions[n][i])) for n in subset] for i in range(7)]
                ns=_fraction_nullspace(matrix)
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
              "p1_groups_examined_total":groups_examined,"unique_mathematical_candidates_total":len(ranked),
              "display_limit":int(return_limit),"display_limit_is_search_budget":False},
              "candidates":ranked[:int(return_limit)],"permutation_null":null_summary,
              "claim_boundary":{"returned_count_is_multiplicity_count":False,
              "all_examined_candidates_are_accounted_for":True,"candidate_is_confirmed_law":False,
              "query_mode_replaces_open_discovery_frontier":False}}
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
