import numpy as np
from pathlib import Path
from source.lawspace.scientific_axis_space import AtlasLawSpaceSearchOwner, ScientificAxisSpaceOwner

ZERO=(0,0,0,0,0)

def _spec(dim,*tags,**extra):
    return {"dimension":tuple(dim),"quantity_kind":"test_quantity","tags":list(tags),**extra}

def _assert_exact(names, X, y, target, specs):
    r = AtlasLawSpaceSearchOwner().discover(variable_names=names, values=X, target_values=y, target_name=target, quantity_specs=specs)
    assert r['status'] == 'PROVISIONAL_RELATION_HYPOTHESIS_WITHIN_ATLAS_SPACE'
    assert r['train_nrmse'] < 1e-9
    assert r['target_expression_visible'] is False
    assert r['known_law_catalog_used'] is False
    assert r['benchmark_variable_dictionary_used_by_owner'] is False
    assert r['research_cycle_binding']['law_auto_promoted'] is False
    return r


def test_scientific_axis_contract_is_atlas_native_not_symbolic_regression():
    c = AtlasLawSpaceSearchOwner().contract()
    assert c['expression_tree_is_primary_search_space'] is False
    assert c['target_expression_visible'] is False
    assert c['known_law_catalog_required'] is False
    assert c['fixed_global_axis_ceiling'] is None
    assert c['benchmark_variable_dictionary_in_owner'] is False
    legacy=ScientificAxisSpaceOwner().contract()
    assert legacy['compatibility_adapter'] is True
    assert legacy['authoritative_owner']=='ATLAS-LAW-SPACE-SEARCH/1.0.0'


def test_gaussian_state_scaling_birth():
    rng=np.random.default_rng(1); theta=rng.uniform(-3,3,160); sigma=rng.uniform(.5,2,160)
    X=np.column_stack([theta,sigma]); y=np.exp(-0.5*(theta/sigma)**2)/(np.sqrt(2*np.pi)*sigma)
    specs={'theta':_spec(ZERO,'periodic_angle'),'sigma':_spec(ZERO),'prob':_spec(ZERO)}
    r=_assert_exact(('theta','sigma'),X,y,'prob',specs)
    assert any('exp' in x for x in r['selected_relation']['coordinate_projections'])
    assert r['selected_relation']['canonical_axis_ids']


def test_relativistic_spacetime_axis_birth():
    rng=np.random.default_rng(2); x=rng.uniform(.2,3,160); c=np.full(160,3.0); u=rng.uniform(.1,2.0,160); t=rng.uniform(.2,3,160)
    X=np.column_stack([x,c,u,t]); y=(t-u*x/c**2)/np.sqrt(1-u**2/c**2)
    specs={'x':_spec((1,0,0,0,0),'position_scalar'),'c':_spec((1,-1,0,0,0),'velocity','invariant_speed'),'u':_spec((1,-1,0,0,0),'velocity'),'t':_spec((0,1,0,0,0),'time'),'t1':_spec((0,1,0,0,0),'time')}
    r=_assert_exact(('x','c','u','t'),X,y,'t1',specs)
    assert 'relativistic_spacetime_coordinate' in r['selected_relation']['coordinate_kinds']
    assert 'relativistic_spacetime_coordinate' in r['selected_relation']['canonical_axis_ids']


def test_orientational_thermal_additive_short_circuit():
    rng=np.random.default_rng(3); n0=rng.uniform(.5,2,160); kb=np.full(160,1.2); T=rng.uniform(1,4,160); th=rng.uniform(-2,2,160); pd=rng.uniform(.2,1,160); Ef=rng.uniform(.2,1,160)
    X=np.column_stack([n0,kb,T,th,pd,Ef]); y=n0*(1+pd*Ef*np.cos(th)/(kb*T))
    specs={
      'n_0':_spec(ZERO,'state_density'),'kb':_spec((2,-2,1,-1,0),'boltzmann_constant'),'T':_spec((0,0,0,1,0),'temperature'),
      'theta':_spec(ZERO,'periodic_angle'),'p_d':_spec((3,-2,1,0,-1),'dipole_moment'),'Ef':_spec((-1,0,0,0,1),'electric_field'),'n':_spec(ZERO),
    }
    r=_assert_exact(('n_0','kb','T','theta','p_d','Ef'),X,y,'n',specs)
    assert len(r['selected_relation']['coordinate_projections']) == 2
    assert r['feature_count'] < 500


def test_evidence_born_rational_response():
    rng=np.random.default_rng(4); n=rng.uniform(.1,1,160); a=rng.uniform(.1,1,160); X=np.column_stack([n,a]); y=1+n*a/(1-n*a/3)
    specs={'n':_spec(ZERO),'alpha':_spec(ZERO),'theta':_spec(ZERO,'periodic_angle')}
    r=_assert_exact(('n','alpha'),X,y,'theta',specs)
    assert any('evidence_born_rational_response' == k for k in r['selected_relation']['coordinate_kinds'])
    assert 'evidence_born_response_coordinate' in r['selected_relation']['canonical_axis_ids']


def test_reusable_scientific_coordinates_live_in_canonical_atlas_registry():
    from source.lawspace.domains import DOMAIN_REGISTRIES
    physics=DOMAIN_REGISTRIES['physics']
    required={
        'state_difference_coordinate','typed_additive_coordinate','dimensionless_ratio_coordinate',
        'euclidean_distance_coordinate','euclidean_norm_coordinate','dot_product_coordinate',
        'thermal_energy_coordinate','phase_action_coordinate','quantum_action_phase_coordinate',
        'coherent_superposition_intensity_coordinate','relativistic_beta_coordinate',
        'relativistic_pair_coupling_coordinate','relativistic_spacetime_coordinate',
        'periodic_response_coordinate','evidence_born_response_coordinate',
    }
    assert required <= set(physics.axes)


def test_public_api_exposes_authoritative_atlas_law_space_and_compat_adapter_only():
    from source.lawspace.api import LawSpaceAPI
    api=LawSpaceAPI(Path(__file__).resolve().parents[1])
    assert {'get_atlas_law_space_search_contract','search_atlas_law_space'} <= set(api.READ_TOOLS)
    current=api.get_atlas_law_space_search_contract()
    legacy=api.get_scientific_axis_space_contract()
    assert current['owner_id']=='ATLAS-LAW-SPACE-SEARCH/1.0.0'
    assert current['axis_persistence_policy'].startswith('CANONICAL_AXES_ARE_APPEND_ONLY')
    assert legacy['compatibility_adapter'] is True
    assert legacy['authoritative_owner']==current['owner_id']


def test_core_convergence_exact_kernel_uses_canonical_seven_dimensional_basis():
    from source.lawspace.scientific_axis_space import AtlasLawSpaceSearchOwner
    rng=np.random.default_rng(21)
    x=rng.uniform(.5,2.0,120)
    current=rng.uniform(.2,1.7,120)
    amount=rng.uniform(.4,1.4,120)
    X=np.column_stack([x,current,amount])
    y=x.copy()
    specs={
        'x':_spec((1,0,0,0,0,0,0)),
        'current':_spec((0,0,0,1,0,0,0)),
        'amount':_spec((0,0,0,0,0,1,0)),
        'target':_spec((1,0,0,0,0,0,0)),
    }
    r=AtlasLawSpaceSearchOwner().discover(variable_names=('x','current','amount'),values=X,target_values=y,target_name='target',quantity_specs=specs)
    q=r['dimensional_qualification']
    assert q['canonical_basis']==['L','M','T','I','Theta','N','J']
    assert q['exact_arithmetic'] is True
    assert q['legacy_dimension_padding_used'] is False
    assert q['relation_kernel_with_target']['rank']==3
    assert q['relation_kernel_with_target']['nullity']==1
    assert q['relation_kernel_with_target']['groups']==[{'x': -1, 'target': 1}]


def test_legacy_five_dimensional_descriptor_is_boundary_compatibility_only():
    rng=np.random.default_rng(22); x=rng.uniform(.4,2.0,100); y=2*x
    specs={'x':_spec((1,0,0,0,0)),'y':_spec((1,0,0,0,0))}
    r=AtlasLawSpaceSearchOwner().discover(variable_names=('x',),values=x[:,None],target_values=y,target_name='y',quantity_specs=specs)
    assert r['dimensional_qualification']['legacy_dimension_padding_used'] is True
    assert r['dimensional_qualification']['canonical_basis']==['L','M','T','I','Theta','N','J']
    assert AtlasLawSpaceSearchOwner().contract()['dimension_authority']=='EXACT_RATIONAL_7D_KERNEL_VIA_PHI_COMPILER_OWNER'


def test_local_law_space_execution_budgets_are_shells_not_scientific_ceilings():
    contract = AtlasLawSpaceSearchOwner().contract()['fair_local_search_shell']
    assert contract['shell_zero_preserves_15_13_behavior'] is True
    assert contract['fixed_maximum_shell'] is None
    assert contract['feature_caps_are_per_shell_execution_budgets'] is True
    assert contract['support_order_grows_without_fixed_ceiling'] is True
    assert contract['exponent_order_grows_without_fixed_ceiling'] is True
    assert contract['sparse_term_budget_grows_without_fixed_ceiling'] is True


def test_conservation_invariant_canonicalization_uses_composition_not_constancy_alone():
    from source.lawspace.scientific_axis_space import canonicalize_conserved_invariant
    specific = [
        {'coefficient':'1','powers':{'g':1,'h':1}},
        {'coefficient':'0.5','powers':{'v':2}},
    ]
    blocked=canonicalize_conserved_invariant(specific)
    assert blocked['status']=='CANONICALIZATION_BLOCKED_COMPOSITION_LAW_REQUIRED'
    r=canonicalize_conserved_invariant(
        specific,
        trajectory_constant_factors=('m',),
        extensive_carrier_powers={'m':1},
        normalization_anchor=0,
    )
    assert r['status']=='CANONICAL_ADDITIVE_EXTENSIVE_INVARIANT'
    assert r['canonical_terms']==[
        {'coefficient':{'numerator':1,'denominator':1},'powers':{'g':1,'h':1,'m':1}},
        {'coefficient':{'numerator':1,'denominator':2},'powers':{'m':1,'v':2}},
    ]
    assert r['claim_boundary']['constancy_alone_selects_canonical_form'] is False
