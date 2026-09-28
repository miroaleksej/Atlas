import numpy as np
from source.lawspace.mathematical_invention import FunctionLanguageBirthEngine
from source.lawspace.query_research import QueryDrivenResearchOwner


def _zero_dims(names):
    return {name: [0,0,0,0,0,0,0] for name in names}


def test_abs_power_contract_is_parameterized_not_catalogued():
    c=FunctionLanguageBirthEngine().contract()
    assert "ABS_POWER" in c["candidate_operations"]
    p=c["parameterized_operation_birth"]["ABS_POWER"]
    assert p["continuous_exponent_search"] is True
    assert p["rational_exponent_snap"] is True
    assert p["target_specific_exponent_catalog_used"] is False


def test_one_third_is_discovered_then_rationally_snapped():
    rng=np.random.default_rng(123); n=240
    x=rng.uniform(-2.5,2.5,(n,3)); obs={f"x{i}":x[:,i] for i in range(3)}
    obs["y"]=0.2*x[:,0]+0.2*x[:,0]**3+2.5*x[:,0]*np.abs(x[:,2])**(1/3)+rng.normal(0,0.005,n)
    out=QueryDrivenResearchOwner().search_function_forms(observations=obs,dimensions=_zero_dims(obs),target_name="y",axis_names=["x0","x1","x2"],hypothesis_budget=100,return_limit=100,permutation_count=0,language_birth_nrmse=0.02)
    h=next(h for h in out["hypotheses"] if h["function_family"]=="ABS_POWER")
    s=h["model_state"]
    assert s["exponent_source"]=="RATIONAL_SNAP"
    assert s["rational_exponent"]=={"numerator":1,"denominator":3}
    assert h["cross_validated_nrmse"]<0.01


def test_irrational_exponent_is_not_forced_to_rational():
    rng=np.random.default_rng(555); n=240; x=rng.uniform(-2,2,(n,2)); p=np.sqrt(2.0)
    obs={"x0":x[:,0],"x1":x[:,1]}; obs["y"]=1.8*x[:,0]*np.abs(x[:,1])**p+0.3*x[:,0]+rng.normal(0,1e-4,n)
    out=QueryDrivenResearchOwner().search_function_forms(observations=obs,dimensions=_zero_dims(obs),target_name="y",axis_names=["x0","x1"],hypothesis_budget=100,return_limit=100,permutation_count=0,language_birth_nrmse=0.01)
    h=next(h for h in out["hypotheses"] if h["function_family"]=="ABS_POWER")
    s=h["model_state"]
    assert s["exponent_source"]=="CONTINUOUS_SEARCH"
    assert s["rational_exponent"] is None
    assert abs(s["continuous_exponent"]-p)<0.01
