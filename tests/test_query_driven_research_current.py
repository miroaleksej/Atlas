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


def _multipi_memory_data(n=240):
    rng=np.random.default_rng(20260908)
    # Positive, independent physical scales near unity keep the exact Pi basis numerically well conditioned.
    tau=np.exp(rng.normal(0.0,0.35,n))
    D=np.exp(rng.normal(0.0,0.30,n))
    L=np.exp(rng.normal(0.0,0.25,n))
    k=np.exp(rng.normal(0.0,0.30,n))
    E=np.exp(rng.normal(0.0,0.35,n))
    eta=np.exp(rng.normal(0.0,0.30,n))
    rho=np.exp(rng.normal(0.0,0.20,n))
    pi1=tau*D/L**2
    pi2=tau*k
    pi3=tau*E/eta
    pi4=tau*E/(rho*D)
    y=2.0+0.45*pi1+0.55*pi2-0.35*pi3+0.25*pi4+0.70*pi1*pi4+rng.normal(0.0,0.025,n)
    obs={'tau':tau,'D':D,'L':L,'k':k,'E':E,'eta':eta,'rho':rho,'yield':y}
    dims={
        'tau':[0,0,1,0,0,0,0],
        'D':[2,0,-1,0,0,0,0],
        'L':[1,0,0,0,0,0,0],
        'k':[0,0,-1,0,0,0,0],
        'E':[-1,1,-2,0,0,0,0],
        'eta':[-1,1,-1,0,0,0,0],
        'rho':[-3,1,0,0,0,0,0],
    }
    groups=[f'system-{i%6}' for i in range(n)]
    return obs,dims,groups


def test_query_mode_p_gt_1_searches_function_form_and_replays_full_surface():
    obs,dims,groups=_multipi_memory_data()
    out=QueryDrivenResearchOwner().search_function_forms(
        observations=obs,dimensions=dims,target_name='yield',
        axis_names=['tau','D','L','k','E','eta','rho'],
        question='does reaction-diffusion memory collapse on a four-Pi manifold?',
        return_limit=25,hypothesis_budget=100,group_ids=groups,
        permutation_count=19,permutation_seed=41,
    )
    assert out['status']=='MULTI_PI_FUNCTION_FORM_SEARCH_COMPLETE'
    assert out['dimension_kernel']['nullity']==4
    assert [x['formula'] for x in out['dimension_kernel']['basis']]==[
        'tau * D * L^-2','tau * k','tau * E * eta^-1','tau * D^-1 * E * rho^-1'
    ]
    assert out['search_surface']['structural_hypotheses_examined_total']==45
    assert out['search_surface']['display_limit_is_search_budget'] is False
    assert out['search_surface']['finite_query_tranche_is_global_scientific_space_ceiling'] is False
    top=out['hypotheses'][0]
    assert set(top['coordinate_indices'])=={0,1,2,3}
    assert top['polynomial_degree']==2
    assert top['cross_validated_nrmse'] < 0.05
    assert out['permutation_null']['entire_function_surface_refit_each_permutation'] is True
    assert out['permutation_null']['dynamic_function_language_birth_replayed_each_permutation'] is True
    assert out['permutation_null']['structural_hypotheses_replayed_per_permutation_min']>=45
    assert out['permutation_null']['exchangeability_scheme']=='WITHIN_VALIDATION_GROUP'
    assert out['permutation_null']['minimum_achievable_p']==0.05
    assert out['claim_boundary']['selected_cv_score_is_unbiased_post_selection_generalization_estimate'] is False


def test_scalar_query_reports_p_gt_1_deferred_instead_of_silently_dropping_it():
    obs,dims,_=_multipi_memory_data(120)
    out=QueryDrivenResearchOwner().search_observations(
        observations=obs,dimensions=dims,target_name='yield',return_limit=25,
        min_subset_size=7,max_subset_size=7,permutation_count=0,
    )
    assert out['search_surface']['p_gt_1_subsets_deferred_total']==1
    assert out['search_surface']['p_gt_1_deferred_to_function_form_lane'] is True
