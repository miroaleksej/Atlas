from pathlib import Path
import json

from source.lawspace.eda_chip_design import EDAChipDesignResearchOwner, ORFS_WORKFLOW_COMMIT, qualification_oracle, _parse_orfs_variant
from source.lawspace.api import LawSpaceAPI


def test_eda_backend_fail_closed_without_orfs(tmp_path):
    owner=EDAChipDesignResearchOwner()
    s=owner.backend_status(orfs_flow_root=tmp_path)
    assert s['status']=='EDA_BACKEND_UNAVAILABLE'
    r=owner.evaluate(config={'CORE_UTILIZATION':30,'CORE_ASPECT_RATIO':1.0,'PLACE_DENSITY':0.65,'CTS_CLUSTER_SIZE':30},orfs_flow_root=tmp_path)
    assert r['status']=='BACKEND_UNAVAILABLE'
    assert r['surrogate_used'] is False


def test_orfs_metric_parser_requires_explicit_lvs(tmp_path):
    flow=tmp_path
    logs=flow/'logs/sky130hd/gcd/v'; reports=flow/'reports/sky130hd/gcd/v'; results=flow/'results/sky130hd/gcd/v'
    design=flow/'designs/sky130hd/gcd'
    for p in (logs,reports,results,design): p.mkdir(parents=True,exist_ok=True)
    (design/'config.mk').write_text('export DESIGN_NAME = gcd\n')
    (design/'constraint.sdc').write_text('set clk_period 10\ncreate_clock -name c -period $clk_period [get_ports clk]\n')
    (logs/'6_report.json').write_text(json.dumps({'finish__design__instance__area':600.0,'finish__power__total':0.002,
        'finish__timing__setup__ws':0.2,'finish__timing__drv__setup_violation_count':0,
        'detailedroute__route__drc_errors':0}))
    (reports/'6_drc_count.rpt').write_text('0\n')
    (results/'6_final.gds').write_text('gds')
    r=_parse_orfs_variant(flow,platform='sky130hd',design='gcd',variant='v')
    assert r['gates']['timing_pass'] is True and r['gates']['signoff_drc_pass'] is True
    assert r['gates']['lvs_pass'] is False and r['gates']['all_signoff_gates_pass'] is False
    (logs/'6_lvs.log').write_text('INFO : Congratulations! Netlists match.\n')
    r=_parse_orfs_variant(flow,platform='sky130hd',design='gcd',variant='v')
    assert r['gates']['all_signoff_gates_pass'] is True
    assert abs(r['metrics']['effective_critical_delay_ns']-9.8)<1e-12


def test_route_drc_cannot_substitute_for_missing_signoff_drc(tmp_path):
    flow=tmp_path
    logs=flow/'logs/sky130hd/gcd/v'; reports=flow/'reports/sky130hd/gcd/v'; results=flow/'results/sky130hd/gcd/v'
    design=flow/'designs/sky130hd/gcd'
    for p in (logs,reports,results,design): p.mkdir(parents=True,exist_ok=True)
    (design/'config.mk').write_text('export DESIGN_NAME = gcd\n')
    (design/'constraint.sdc').write_text('set clk_period 10\ncreate_clock -name c -period $clk_period [get_ports clk]\n')
    (logs/'6_report.json').write_text(json.dumps({'finish__design__instance__area':600.0,'finish__power__total':0.002,
        'finish__timing__setup__ws':0.2,'finish__timing__drv__setup_violation_count':0,
        'detailedroute__route__drc_errors':0}))
    (logs/'6_lvs.log').write_text('INFO : Congratulations! Netlists match.\n')
    (results/'6_final.gds').write_text('gds')
    r=_parse_orfs_variant(flow,platform='sky130hd',design='gcd',variant='v')
    assert r['metrics']['route_drc_error_count']==0
    assert r['metrics']['signoff_drc_count'] is None
    assert r['gates']['signoff_drc_pass'] is False
    assert r['gates']['route_drc_is_signoff_substitute'] is False
    assert r['gates']['all_signoff_gates_pass'] is False


def test_missing_setup_violation_count_fails_timing_closed(tmp_path):
    flow=tmp_path
    logs=flow/'logs/sky130hd/gcd/v'; reports=flow/'reports/sky130hd/gcd/v'; results=flow/'results/sky130hd/gcd/v'
    design=flow/'designs/sky130hd/gcd'
    for p in (logs,reports,results,design): p.mkdir(parents=True,exist_ok=True)
    (design/'config.mk').write_text('export DESIGN_NAME = gcd\n')
    (design/'constraint.sdc').write_text('set clk_period 10\ncreate_clock -name c -period $clk_period [get_ports clk]\n')
    (logs/'6_report.json').write_text(json.dumps({'finish__design__instance__area':600.0,'finish__power__total':0.002,
        'finish__timing__setup__ws':0.2,'detailedroute__route__drc_errors':0}))
    (reports/'6_drc_count.rpt').write_text('0\n')
    (logs/'6_lvs.log').write_text('INFO : Congratulations! Netlists match.\n')
    (results/'6_final.gds').write_text('gds')
    r=_parse_orfs_variant(flow,platform='sky130hd',design='gcd',variant='v')
    assert r['gates']['timing_pass'] is False
    assert r['gates']['missing_setup_count_is_pass'] is False
    assert r['gates']['all_signoff_gates_pass'] is False


def test_eda_control_compares_four_equal_budget_strategies():
    r=EDAChipDesignResearchOwner().run_pilot(evaluation_budget=14,warm_start_count=12,candidate_pool_size=96,
        evaluator=qualification_oracle,evaluator_kind='SYNTHETIC_QUALIFICATION_ONLY')
    assert r['status']=='CHIP_PILOT_QUALIFICATION_CONTROL_COMPLETE'
    assert r['scientific_result'] is None
    assert len(r['strategies'])==4
    assert all(x['evaluation_budget']==14 for x in r['strategies'])
    assert all(x['common_warm_start_count']==12 for x in r['strategies'])
    assert r['unique_world_evaluations'] <= 20
    assert len(r['world_evaluations'])==r['unique_world_evaluations']
    assert r['comparison']['atlas_beats_all_baselines'] is None
    assert r['claim_boundary']['qualification_control_is_physical_chip_evidence'] is False


def test_eda_owner_is_exposed_through_single_lawspace_api(tmp_path):
    api=LawSpaceAPI(tmp_path)
    assert 'get_eda_chip_design_contract' in api.READ_TOOLS
    assert 'get_eda_chip_backend_status' in api.READ_TOOLS
    assert 'run_eda_chip_design_pilot' in api.READ_TOOLS
    assert len(ORFS_WORKFLOW_COMMIT)==40
