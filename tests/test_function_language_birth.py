import numpy as np

from source.lawspace.mathematical_invention import FunctionLanguageBirthEngine, MathematicalInventionKernel
from source.lawspace.query_research import QueryDrivenResearchOwner, predict_function_hypothesis


def _zero_dims(names):
    return {name: [0, 0, 0, 0, 0, 0, 0] for name in names}


def _surface(seed=2718, n=240):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2.5, 2.5, (n, 4))
    obs = {f"x{i}": x[:, i] for i in range(4)}
    dims = _zero_dims([*obs, "y"])
    return rng, x, obs, dims


def test_mathematical_invention_kernel_exposes_function_language_component_without_new_owner():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    kernel = MathematicalInventionKernel(root)
    contract = kernel.contract()
    assert contract["owner_id"].startswith("PHI-MATHEMATICAL-INVENTION-KERNEL/")
    assert contract["components"]["function_language_birth"] == "FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT"
    c = kernel.function_language.contract()
    assert c["authority"] == contract["owner_id"]
    assert c["fixed_global_language_catalog_is_primary_space"] is False


def test_polynomial_control_does_not_birth_unneeded_language():
    rng, x, obs, dims = _surface(seed=19)
    obs["y"] = 0.8 + 0.4*x[:, 0] - 0.25*x[:, 1] + 0.7*x[:, 0]*x[:, 1] + rng.normal(0, 0.015, len(x))
    out = QueryDrivenResearchOwner().search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=20, permutation_count=0,
    )
    assert out["function_language_birth"]["status"] == "CURRENT_LANGUAGE_RESIDUAL_WITHIN_BIRTH_TOLERANCE"
    assert out["function_language_birth"]["generated_languages"] == []
    assert out["search_surface"]["born_language_hypotheses_examined_total"] == 0
    assert out["hypotheses"][0]["function_family"] == "STANDARDIZED_TOTAL_DEGREE_POLYNOMIAL"
    assert out["hypotheses"][0]["cross_validated_nrmse"] < 0.04


def test_periodic_residual_births_language_and_beats_polynomial_grammar():
    rng, x, obs, dims = _surface(seed=23)
    obs["y"] = 1.2*np.sin(3*x[:, 0]) + 0.35*np.cos(2*x[:, 1]) + rng.normal(0, 0.05, len(x))
    q = QueryDrivenResearchOwner()
    old = q.search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=100, permutation_count=0, function_language_birth=False,
    )
    new = q.search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=100, permutation_count=0, function_language_birth=True,
    )
    assert old["hypotheses"][0]["cross_validated_nrmse"] > 0.70
    assert new["function_language_birth"]["status"] == "FUNCTION_LANGUAGE_BIRTH_WARRANTED"
    assert "PERIODIC" in [r["family"] for r in new["function_language_birth"]["generated_languages"]]
    assert new["hypotheses"][0]["function_family"] == "PERIODIC"
    assert new["hypotheses"][0]["cross_validated_nrmse"] < 0.20
    assert new["hypotheses"][0]["cross_validated_nrmse"] < 0.30 * old["hypotheses"][0]["cross_validated_nrmse"]
    pred = predict_function_hypothesis(new["hypotheses"][0], x)
    assert np.all(np.isfinite(pred)) and len(pred) == len(x)


def test_local_bivariate_residual_births_kernel_language():
    rng, x, obs, dims = _surface(seed=29)
    obs["y"] = (
        np.exp(-1.5*((x[:, 0]-0.7)**2 + (x[:, 1]+0.5)**2))
        + 0.4*np.exp(-2.0*((x[:, 0]+1.1)**2 + (x[:, 1]-1.0)**2))
        + rng.normal(0, 0.03, len(x))
    )
    q = QueryDrivenResearchOwner()
    old = q.search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=100, permutation_count=0, function_language_birth=False,
    )
    new = q.search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=100, permutation_count=0,
    )
    born = [r["family"] for r in new["function_language_birth"]["generated_languages"]]
    assert "KERNEL" in born
    kernel = next(h for h in new["hypotheses"] if h["function_family"] == "KERNEL")
    assert set(kernel["coordinate_indices"]) == {0, 1}
    assert kernel["cross_validated_nrmse"] < 0.55
    assert kernel["cross_validated_nrmse"] < 0.70 * old["hypotheses"][0]["cross_validated_nrmse"]


def test_dynamic_language_birth_is_replayed_inside_permutation_null():
    rng, x, obs, dims = _surface(seed=31, n=180)
    obs["y"] = np.sin(3*x[:, 0]) + rng.normal(0, 0.06, len(x))
    out = QueryDrivenResearchOwner().search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=80, return_limit=20, permutation_count=5, permutation_seed=7,
    )
    null = out["permutation_null"]
    assert null["entire_function_surface_refit_each_permutation"] is True
    assert null["dynamic_function_language_birth_replayed_each_permutation"] is True
    assert null["structural_hypotheses_replayed_per_permutation_min"] >= out["search_surface"]["baseline_polynomial_hypotheses_examined_total"]
    assert out["claim_boundary"]["selected_cv_score_is_unbiased_post_selection_generalization_estimate"] is False
    assert out["claim_boundary"]["function_language_birth_is_world_mathematical_novelty_claim"] is False


def test_structureless_residual_does_not_force_language_birth():
    rng, x, obs, dims = _surface(seed=99)
    obs["y"] = rng.normal(0, 1.0, len(x))
    out = QueryDrivenResearchOwner().search_function_forms(
        observations=obs, dimensions=dims, target_name="y", axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100, return_limit=20, permutation_count=0,
    )
    assert out["function_language_birth"]["status"] == "NO_OPERATION_SIGNAL_ABOVE_BIRTH_GATE"
    assert out["function_language_birth"]["generated_languages"] == []
    assert out["search_surface"]["born_language_hypotheses_examined_total"] == 0


def test_operator_language_birth_uses_translation_meta_primitives_not_differential_catalog():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    kernel = MathematicalInventionKernel(root)
    c = kernel.operator_language.contract()
    assert c["authority"] == kernel.contract()["owner_id"]
    assert c["named_differential_operator_catalog_used"] is False
    assert c["fixed_derivative_order_catalog_used"] is False
    assert c["fixed_global_operator_rank_ceiling"] is None
    language = kernel.operator_language.invent(
        coordinate_dimensions={"t":[0,0,1,0,0,0,0],"x":[1,0,0,0,0,0,0],"y":[1,0,0,0,0,0,0]},
        field_dimensions={
            "u":[1,0,-1,0,0,0,0],"v":[1,0,-1,0,0,0,0],
            "p":[-1,1,-2,0,0,0,0],"rho":[-3,1,0,0,0,0,0],"nu":[2,0,-1,0,0,0,0],
        },
        target_field="u", search_shell_budget=6,
    )
    assert language["status"] == "GENERATED_OPERATOR_LANGUAGE"
    assert language["target_action"]["coordinate"] == "t"
    assert language["target_action"]["moment_rank"] == 1
    assert all(row["coordinate"] != "t" for row in language["generated_signatures"])
    ranks={row["moment_rank"] for row in language["generated_signatures"]}
    assert {1,2,3}.issubset(ranks)
    assert language["search_may_resume_beyond_budget"] is True
    assert language["claim_boundary"]["resource_budget_is_scientific_rank_ceiling"] is False


def test_operator_language_can_expand_pointwise_carrier_depth_without_named_term_catalog():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    kernel = MathematicalInventionKernel(root)
    common = dict(
        coordinate_dimensions={"t":[0,0,1,0,0,0,0],"x":[1,0,0,0,0,0,0]},
        field_dimensions={
            "u":[1,0,-1,0,0,0,0],"a":[1,0,-1,0,0,0,0],
            "c":[0,0,0,0,0,0,0],"d":[0,0,0,0,0,0,0],
        },
        target_field="u", search_shell_budget=5,
    )
    depth1 = kernel.operator_language.invent(**common, carrier_factor_budget=1)
    depth2 = kernel.operator_language.invent(**common, carrier_factor_budget=2)
    wanted = {
        "kind":"POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE",
        "response_field":"u","coordinate":"x","moment_rank":1,
        "carrier_factors":[{"field":"c","power":1},{"field":"u","power":1}],
        "carrier_factor_count":2,
    }
    def has(language):
        return any(all(row.get(k)==v for k,v in wanted.items()) for row in language["generated_signatures"])
    assert has(depth1) is False
    assert has(depth2) is True
    assert depth2["generated_signature_count"] > depth1["generated_signature_count"]
    assert depth2["claim_boundary"]["carrier_factor_budget_is_scientific_ceiling"] is False
