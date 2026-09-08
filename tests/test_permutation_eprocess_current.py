from __future__ import annotations
import json
from fractions import Fraction
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
EXT_SRC=ROOT/'extensions'/'ATLAS_AI_RESEARCH_EXTENSION_v0_10_0'/'src'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(EXT_SRC))
from evaluation.permutation_eprocess_qualification import run
from scienceatlas_ai.genesis_shells import GenesisJournal, ShellLadder
from scienceatlas_ai.permutation_eprocess import EProcessEpochPlan, PermutationEProcessOwner, PermutationGroup

def mean_inc(a,b):
    m=sum((y for _,y in a),Fraction(0))/len(a); return sum(((y-m)**2 for _,y in b),Fraction(0))

def test_permutation_eprocess_full_qualification():
    q=run(noise_paths=1000,persist=False)
    assert q['status']=='PASS_PERMUTATION_EPROCESS_15_20_0', q
    assert q['type1_empirical_calibration']['crossings'] <= 50
    assert q['claim_boundary']['per_target_only'] is True
    assert q['claim_boundary']['system_wide_error_control'] is False
    assert q['s6_resolution_demo']['selected_after_exhaustive_orbit_scan'] is True
    assert q['s6_resolution_demo']['prospective_power_calibration'] is False

def test_reused_epoch_is_refused_and_does_not_change_genesis_journal():
    X=[{'x':Fraction(i+1),'z':Fraction((i*2)%6+1)} for i in range(6)]
    Y=[Fraction(v) for v in [1,4,-2,8,3,0]]
    owner=PermutationEProcessOwner(); journal=GenesisJournal()
    plan=EProcessEpochPlan(target_axis='y',input_axes=('x','z'),shell=ShellLadder().shell(1),group=PermutationGroup.cyclic(6),
        conditional_group_invariance_attested=True,acquisition_plan_digest='precommit-reuse-test')
    ids=[f's{i}' for i in range(6)]
    before=json.dumps(journal.to_json(),sort_keys=True)
    first=owner.assess_epoch(target_key='q',plan=plan,rows=list(zip(X,Y)),sample_ids=ids,live_genesis_journal=journal,incumbent_fit=mean_inc)
    second=owner.assess_epoch(target_key='q',plan=plan,rows=list(zip(X,Y)),sample_ids=ids,live_genesis_journal=journal,incumbent_fit=mean_inc)
    assert first['status']=='PASS_EPROCESS_EPOCH'
    assert second['status']=='REFUSED_REUSED_EPOCH_SAMPLE'
    assert json.dumps(journal.to_json(),sort_keys=True)==before
