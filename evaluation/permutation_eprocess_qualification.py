"""Executable qualification of the finite-group permutation e-process owner.

The qualification deliberately separates four claims:
1. finite-group normalisation and frozen-journal purity are implementation invariants;
2. C6 three-epoch signal accumulation is a power demonstration;
3. 1000 independent C6 noise paths are an empirical Type-I calibration sanity check,
   not a proof of Ville's inequality;
4. the S6 identity-max fixture is selected after orbit inspection solely to demonstrate
   the |S| resolution ceiling and MUST NOT be read as prospective power calibration.
"""
from __future__ import annotations

import json, random, sys
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
EXT_SRC=ROOT/'extensions'/'ATLAS_AI_RESEARCH_EXTENSION_v0_10_0'/'src'
if str(EXT_SRC) not in sys.path: sys.path.insert(0,str(EXT_SRC))
from scienceatlas_ai.genesis_shells import GenesisJournal, ShellLadder
from scienceatlas_ai.permutation_eprocess import EProcessEpochPlan, GainPowerMixture, PermutationEProcessOwner, PermutationGroup
from source.lawspace.schema import digest_payload

REPORT_REL='data/frontiers/PERMUTATION_EPROCESS_QUALIFICATION_CURRENT.json'

XSETS_RAW=[
 [(1,1),(2,3),(3,2),(4,6),(5,4),(6,5)],
 [(1,2),(2,5),(3,1),(4,4),(5,6),(6,3)],
 [(1,6),(2,1),(3,5),(4,2),(5,3),(6,4)],
]

def Xset(raw): return [{'x':Fraction(x),'z':Fraction(z)} for x,z in raw]
XSETS=[Xset(x) for x in XSETS_RAW]

def mean_incumbent(rows_fit, rows_seal):
    mean=sum((y for _,y in rows_fit),Fraction(0))/len(rows_fit)
    return sum(((y-mean)**2 for _,y in rows_seal),Fraction(0))

def F(payload): return Fraction(int(payload['numerator']),int(payload['denominator']))

def run_epoch(owner, journal, *, key, X, Y, group, shell_index, epoch_tag):
    plan=EProcessEpochPlan(target_axis='y',input_axes=('x','z'),shell=ShellLadder().shell(shell_index),
        group=group,score=GainPowerMixture(powers=(1,2,4,8)),fit_size=3,per_target_alpha=Fraction(1,20),
        conditional_group_invariance_attested=True,acquisition_plan_digest=f'QUALIFIED_PRECOMMIT:{epoch_tag}')
    return owner.assess_epoch(target_key=key,plan=plan,rows=list(zip(X,Y)),
        sample_ids=[f'{epoch_tag}-s{i}' for i in range(6)],live_genesis_journal=journal,
        incumbent_fit=mean_incumbent,incumbent_owner_ids=())

def run(*, noise_paths: int=1000, persist: bool=False, root: Path|None=None)->dict[str,Any]:
    root=Path(root or ROOT)
    c6=PermutationGroup.cyclic(6); s6=PermutationGroup.symmetric(6)
    # Non-empty live journal to prove orbit scoring does not mutate it.
    journal=GenesisJournal(); journal.failed_families['unrelated-context']=['syn:historical']; journal.families_charged['unrelated-context']=64
    journal_before=json.dumps(journal.to_json(),sort_keys=True,separators=(',',':'))

    strong=[Fraction(v) for v in [11,-3,0,20,11,4]]
    g0=run_epoch(PermutationEProcessOwner(),journal,key='strong-g0',X=XSETS[0],Y=strong,group=c6,shell_index=0,epoch_tag='strong-g0')
    g1=run_epoch(PermutationEProcessOwner(),journal,key='strong-g1',X=XSETS[0],Y=strong,group=c6,shell_index=1,epoch_tag='strong-g1')
    gains0=g0['orbit_summary']['gains_bp']; gains1=g1['orbit_summary']['gains_bp']
    improvement=[i for i,(a,b) in enumerate(zip(gains0,gains1,strict=True)) if b>a]

    # Same mathematical group, reversed enumeration order: exact identity e must not change.
    c6_rev=PermutationGroup(6,tuple(reversed(c6.elements)),'C6-reversed-enumeration')
    g1_rev=run_epoch(PermutationEProcessOwner(),journal,key='strong-g1-rev',X=XSETS[0],Y=strong,group=c6_rev,shell_index=1,epoch_tag='strong-g1-rev')

    # Three predetermined signal epochs, no post-hoc score tuning.
    signal_owner=PermutationEProcessOwner(); signal_journal=GenesisJournal(); signal=[]
    for t,X in enumerate(XSETS):
        Y=[Fraction(2)+3*d['x']-2*d['z'] for d in X]
        r=run_epoch(signal_owner,signal_journal,key='signal',X=X,Y=Y,group=c6,shell_index=1,epoch_tag=f'signal-{t}')
        signal.append({'epoch_e':r['record']['epoch_e'],'cumulative_e':r['record']['cumulative_e'],
                       'crossed':r['record']['crossed_per_target_threshold']})

    # 1000 independent null paths x 3 fresh epochs.  This is an executable sanity
    # calibration of the implementation, not a replacement for the mathematical proof.
    rng=random.Random(20260907); crossings=0
    for path in range(noise_paths):
        owner=PermutationEProcessOwner(); j=GenesisJournal(); crossed=False
        for t,X in enumerate(XSETS):
            Y=[Fraction(rng.randint(-20,20)) for _ in range(6)]
            r=run_epoch(owner,j,key='noise',X=X,Y=Y,group=c6,shell_index=1,epoch_tag=f'noise-{path}-{t}')
            crossed = crossed or bool(r['record']['crossed_per_target_threshold'])
        crossings += int(crossed)

    # S6 resolution demonstration.  This fixture was selected AFTER exhaustive orbit
    # inspection and reoriented to place the unique orbit maximum at identity.  It is
    # a ceiling demonstration only, never prospective power evidence.
    selected_s6=[Fraction(v) for v in [3,7,-10,8,-19,-20]]
    s6r=run_epoch(PermutationEProcessOwner(),GenesisJournal(),key='s6-selected-demo',X=XSETS[0],Y=selected_s6,
                  group=s6,shell_index=1,epoch_tag='s6-selected-after-orbit-scan')

    journal_after=json.dumps(journal.to_json(),sort_keys=True,separators=(',',':'))
    signal_final=F(signal[-1]['cumulative_e'])
    s6_e=F(s6r['record']['epoch_e'])
    checks={
      'c6_group_laws_exact': c6.verify_group_laws()['valid'],
      's6_group_laws_exact': s6.verify_group_laws()['valid'],
      'c6_g1_strictly_expands_winner_search_on_strong_fixture': bool(improvement) and gains1[4]>gains0[4],
      'finite_group_orbit_average_e_is_exactly_one': g1['score']['orbit_average_e']=={'numerator':1,'denominator':1},
      'orbit_enumeration_order_does_not_change_identity_e': g1['score']['identity_e']==g1_rev['score']['identity_e'],
      'live_genesis_journal_is_byte_stable_across_orbit_scoring': journal_before==journal_after,
      'three_fresh_signal_epochs_cross_per_target_threshold': signal_final>=20,
      'type1_1000_path_empirical_crossing_rate_at_most_5pct': crossings*20<=noise_paths,
      's6_selected_demo_has_unique_identity_maximum': s6r['record']['identity_gain_bp']==s6r['record']['max_gain_bp'] and s6r['record']['max_gain_multiplicity']==1,
      's6_selected_demo_can_exceed_per_target_20_with_preregistered_exact_mixture': s6_e>=20,
      'evidence_is_explicitly_per_target_only': s6r['claim_boundary']['per_target_only'] is True and s6r['claim_boundary']['system_wide_error_control'] is False,
    }
    payload={
      'schema':'scienceatlas-permutation-eprocess-qualification/v1','release':'15.20.0','owner':'PERMUTATION-EPROCESS-QUALIFICATION/15.20.0',
      'status':'PASS_PERMUTATION_EPROCESS_15_20_0' if all(checks.values()) else 'FAIL_PERMUTATION_EPROCESS_15_20_0',
      'checks':checks,'score':GainPowerMixture(powers=(1,2,4,8)).to_json(),
      'c6_strong_fixture':{'y':[11,-3,0,20,11,4],'G0_gain_bp':gains0,'G1_gain_bp':gains1,'g1_improvement_positions':improvement,
                           'G1_identity_e':g1['record']['epoch_e'],'orbit_average_e':g1['score']['orbit_average_e']},
      'three_epoch_signal':{'law':'y=2+3*x-2*z','trajectory':signal,'final_cumulative_e':signal[-1]['cumulative_e'],'per_target_threshold':{'numerator':20,'denominator':1}},
      'type1_empirical_calibration':{'paths':noise_paths,'epochs_per_path':3,'group':'C6','seed':20260907,'crossings':crossings,
          'crossing_rate':{'numerator':crossings,'denominator':noise_paths},'threshold':20,'is_mathematical_proof':False},
      's6_resolution_demo':{'group_size':720,'fixture_y':[3,7,-10,8,-19,-20],'identity_e':s6r['record']['epoch_e'],
          'identity_gain_bp':s6r['record']['identity_gain_bp'],'max_gain_bp':s6r['record']['max_gain_bp'],'max_gain_multiplicity':s6r['record']['max_gain_multiplicity'],
          'selected_after_exhaustive_orbit_scan':True,'reoriented_to_identity_after_scan':True,'prospective_power_calibration':False,
          'real_data_selection_rule_permitted':False,'purpose':'RESOLUTION_CEILING_DEMONSTRATION_ONLY'},
      'claim_boundary':{
          'per_target_only':True,'ville_threshold_20_is_system_wide_guarantee':False,'system_wide_error_control':False,
          'global_online_controller':'UNIMPLEMENTED','atlas_wide_promotion_allowed_from_eprocess_crossing_alone':False,
          'type1_empirical_calibration_is_proof':False,'finite_group_identity_is_implementation_check':True,
          's6_selected_fixture_is_prospective_power_evidence':False,
          'conditional_group_invariance_under_null_is_required_for_each_fresh_epoch':True,
          'frozen_genesis_journal_required_for_orbit_scoring':True,
      }
    }
    payload['digest']=digest_payload(payload)
    if persist:
        path=root/REPORT_REL; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return payload

if __name__=='__main__':
    print(json.dumps(run(persist=True),indent=2,sort_keys=True))
