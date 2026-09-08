import numpy as np
from source.lawspace.query_research import QueryDrivenResearchOwner


def _collapse_data():
    rng=np.random.default_rng(11); K=[];Ds=[];Ls=[];ETA=[]
    systems={'catalyst':((1e-2,1e3),(1e-9,1e-7),(1e-4,1e-2)),
             'biofilm':((1e-5,1e-1),(1e-10,1e-9),(1e-5,1e-3)),
             'cell':((1e-3,1e2),(1e-12,1e-10),(1e-7,1e-5))}
    for kr,dr,lr in systems.values():
        for _ in range(120):
            k=10**rng.uniform(*np.log10(kr));D=10**rng.uniform(*np.log10(dr));L=10**rng.uniform(*np.log10(lr));phi=L*np.sqrt(k/D)
            K.append(k);Ds.append(D);Ls.append(L);ETA.append(np.tanh(phi)/phi*np.exp(rng.normal(0,.02)))
    n=len(K)
    obs={'k':K,'D':Ds,'L':Ls,'eta':ETA,'rho':10**rng.uniform(0,3,n),'v':10**rng.uniform(-3,1,n),'mu':10**rng.uniform(-5,-2,n)}
    dims={'k':[0,0,-1,0,0,0,0],'D':[2,0,-1,0,0,0,0],'L':[1,0,0,0,0,0,0],
          'rho':[-3,1,0,0,0,0,0],'v':[1,0,-1,0,0,0,0],'mu':[-1,1,-1,0,0,0,0]}
    return obs,dims


def test_query_mode_recovers_thiele_coordinate_without_formula_hint():
    obs,dims=_collapse_data()
    out=QueryDrivenResearchOwner().search_observations(observations=obs,dimensions=dims,target_name='eta',
        question='what controls reaction diffusion effectiveness?',return_limit=25,max_subset_size=4,permutation_count=20,permutation_seed=99)
    top=out['candidates'][0]
    assert top['formula']=='k * D^-1 * L^2'
    assert top['collapse_score'] < .15
    assert out['search_surface']['subsets_examined_total']==50
    assert out['search_surface']['display_limit_is_search_budget'] is False
    assert out['permutation_null']['entire_ranked_surface_replayed'] is True
    assert out['permutation_null']['observed_best_collapse'] < out['permutation_null']['permutation_best_median']

def test_question_focus_fails_closed_on_ambiguous_bare_symbols():
    from source.lawspace.api import LawSpaceAPI
    import pathlib
    root=pathlib.Path(__file__).resolve().parents[1]
    out=LawSpaceAPI(root).focus_research_question(question='reaction diffusion effectiveness',named_observables=['D','L','k'])
    assert out['status']=='AMBIGUOUS_OBSERVABLES_REQUIRE_PASSPORTS'
    assert out['ambiguous_observables']
    assert out['claim_boundary']['ambiguous_symbol_silently_resolved'] is False
