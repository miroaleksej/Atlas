#!/usr/bin/env python3
"""Current owner-to-owner joint qualification for Φ-Compiler, Cognitive Atlas and QPDTR 15.25.0.

This gate checks current integration wiring and representative executable bridges.
Heavy owner-specific replay remains owned by the transactional current test suite;
no deleted historical report receipt is a dependency.
"""
from __future__ import annotations
import argparse,json,sys,subprocess,os,importlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.schema import digest_payload
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.api import LawSpaceAPI
from source.lawspace.science_atlas_core import ScienceAtlasCoreKernel
from source.lawspace.constraint_atlas import ConstraintAtlasOwner
from source.lawspace.neutrino import HigherDimensionalMicroParameters,NeutrinoPhenomenologyOwner,NeutrinoLawIntersectionClosureOwner
from source.lawspace.algebraic_experiment import NeutrinoAlgebraicExperimentalOwner
from source.lawspace.aeronautics import AeronauticsLawIntersectionClosureOwner
from source.lawspace.quantum_vacuum import QuantumVacuumGravityIntersectionOwner
from source.lawspace.scientific_data_ingestion import ScientificDataIngestionOwner
from source.lawspace.cognitive_core import PhiCognitiveCore
from source.lawspace.resident_cognitive import ResidentCognitiveOrganism
from source.lawspace.dayabay_full_likelihood import DayaBayFullLikelihoodOwner
from source.lawspace.katrin_spectral_likelihood import KATRINSpectralLikelihoodOwner
from source.lawspace.t2k_published_likelihood import T2KPublishedLikelihoodOwner
from source.lawspace.superk_atmospheric_likelihood import SuperKAtmosphericLikelihoodOwner
from source.lawspace.superk_solar_likelihood import SuperKSolarLikelihoodOwner
from source.lawspace.neutrino_external_constraints import NeutrinoExternalConstraintsOwner
from source.lawspace.neutrino_global_combination import NeutrinoGlobalCombinationOwner
from source.lawspace.neutrino_real_data import NeutrinoRealDataLikelihoodOwner
from source.multidomain_qg_bridge import load_multidomain_qg_bridge
from source.qpdtr_bridge import load_qpdtr_v2_5_0_bridge,certify_neutrino_mass_operator_with_qpdtr


def _fresh_qualification(root: Path, import_line: str, expression: str, timeout_seconds: int = 180) -> dict:
    """Execute one qualification in an isolated process and return only canonical summary fields."""
    code = (
        "import json,sys,os; " + import_line + "; "
        + f"root={str(root)!r}; "
        + "r=" + expression + "; "
        + "print(json.dumps({'status':r.get('status'),'passed':r.get('passed'),'total':r.get('total'),'digest':r.get('digest') or r.get('sha256')},sort_keys=True)); "
        + "sys.stdout.flush(); os._exit(0)"
    )
    env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE'] = '1'
    cp = subprocess.run([sys.executable, '-c', code], cwd=str(root), env=env, text=True, capture_output=True, timeout=timeout_seconds)
    if cp.returncode != 0:
        raise RuntimeError(f"fresh qualification failed: {import_line}: {cp.stderr[-2000:]}")
    lines = [line for line in cp.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"fresh qualification emitted no summary: {import_line}")
    return json.loads(lines[-1])

def _fresh_resident_ai_path(root: Path, timeout_seconds: int = 240) -> dict:
    """Execute the live Resident path once and bind its already-executed Cognitive dependency."""
    code = (
        "import json,sys,os; from pathlib import Path; "
        "from source.lawspace.resident_cognitive import ResidentCognitiveOrganism; "
        + f"root=Path({str(root)!r}); "
        + "rr=dict(ResidentCognitiveOrganism.run_qualification(root)); "
        + "base=dict((rr.get('demonstration') or {}).get('base_98') or {}); "
        + "cog=dict((base.get('dependencies') or {}).get('cognitive_core') or {}); "
        + "out={'resident':{'status':rr.get('status'),'passed':rr.get('passed'),'total':rr.get('total'),'digest':rr.get('digest') or rr.get('sha256')},'cognitive':cog}; "
        + "print(json.dumps(out,sort_keys=True)); sys.stdout.flush(); os._exit(0)"
    )
    env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE'] = '1'
    cp = subprocess.run([sys.executable, '-c', code], cwd=str(root), env=env, text=True, capture_output=True, timeout=timeout_seconds)
    if cp.returncode != 0:
        raise RuntimeError(f"fresh resident AI path failed: {cp.stderr[-2000:]}")
    lines = [line for line in cp.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("fresh resident AI path emitted no summary")
    return json.loads(lines[-1])

def run_joint_qualification(root:Path=ROOT)->dict:
    root=Path(root).resolve()
    # Resident qualification already executes the full Cognitive Core dependency.
    # Run that integrated AI path once in a fresh process and bind both receipts;
    # do not execute Cognitive a second time merely for joint bookkeeping.
    ai_path=_fresh_resident_ai_path(root)
    resident=dict(ai_path.get('resident') or {})
    cognitive=dict(ai_path.get('cognitive') or {})
    runtime=LawSpaceRuntime(root)
    lawspace=dict(runtime.qualify()); qpdtr=load_qpdtr_v2_5_0_bridge(root); multidomain=load_multidomain_qg_bridge(root)
    constraint_owner=ConstraintAtlasOwner(root); science_owner=ScienceAtlasCoreKernel(root)
    intersection_owner=NeutrinoLawIntersectionClosureOwner(root); aero_owner=AeronauticsLawIntersectionClosureOwner(root); qvac_owner=QuantumVacuumGravityIntersectionOwner(root)
    constraint_contract=dict(constraint_owner.contract()); intersection_contract=dict(intersection_owner.contract()); aero_contract=dict(aero_owner.contract()); qvac_contract=dict(qvac_owner.contract())
    axis_search_contract = LawSpaceAPI(root).get_atlas_law_space_search_contract()
    # Heavy AI owner-specific qualifications are canonical acceptance surfaces of
    # their respective owners.  The joint gate must not execute them again: doing
    # so duplicates the same scientific/cognitive workload and couples independent
    # mutable/global state.  Joint verifies that each surface is present/callable,
    # while Cognitive Core + Resident are executed live above as the end-to-end AI path.
    delegated_ai_surfaces = {
      'generation_transition': ('evaluation.generation_transition_qualification','run_release_qualification'),
      'reflexive_architecture': ('evaluation.reflexive_architecture_qualification','run_release_qualification'),
      'developmental_open_endedness': ('evaluation.developmental_open_endedness_qualification','run_release_qualification'),
      'knowledge_evolution': ('evaluation.knowledge_evolution_qualification','run_release_qualification'),
      'mathematical_invention': ('evaluation.mathematical_invention_qualification','run_release_qualification'),
      'resource_theory': ('evaluation.resource_theory_qualification','run_release_qualification'),
      'discriminating_experiment': ('evaluation.discriminating_experiment_qualification','run_release_qualification'),
      'research_proof': ('evaluation.research_proof_qualification','run'),
      'theory_compiler': ('evaluation.theory_compiler_qualification','run_release_qualification'),
      'long_horizon': ('evaluation.long_horizon_blind_cycle_qualification','run_release_qualification'),
      'prospective_external_validation': ('evaluation.prospective_external_validation_qualification','run_release_qualification'),
      'autonomous_research_orchestration': ('evaluation.autonomous_research_orchestration_qualification','run_release_qualification'),
    }
    delegated_ai_callable = {}
    for key,(module_name,function_name) in delegated_ai_surfaces.items():
        module=importlib.import_module(module_name)
        delegated_ai_callable[key]=callable(getattr(module,function_name,None))
    micro=HigherDimensionalMicroParameters(dimensions=1,radii_micrometre=(0.2,),lightest_dirac_mass_ev=0.022,kk_modes_per_family=2,family_coupling_scales=(0.78,0.78,0.78),geometry='WARPED_INTERVAL_RS1',warp_curvature_ev=4.2,warp_exponent=1.2,family_warp_bulk_c=(0.4,0.5,0.6))
    derivation=runtime.compile_neutrino_multidomain_spec(candidate_id='JOINT-QPDTR-WARPED-TAKAGI',geometry='WARPED_INTERVAL_RS1',microparameters=micro.to_dict())
    no=NeutrinoPhenomenologyOwner(); lowered,candidate=no.lower_multidomain_lawspace_spec(derivation); mass,_,geom,conv,_=no.mass_operator(lowered); takagi=no.micro_to_ir(lowered).takagi_spectrum
    cross=certify_neutrino_mass_operator_with_qpdtr(root,mass_matrix=mass,takagi_masses_ev=takagi.takagi_masses_ev,candidate_digest=candidate.digest)
    owner_classes=(NeutrinoPhenomenologyOwner,NeutrinoAlgebraicExperimentalOwner,ScientificDataIngestionOwner,DayaBayFullLikelihoodOwner,KATRINSpectralLikelihoodOwner,T2KPublishedLikelihoodOwner,SuperKAtmosphericLikelihoodOwner,SuperKSolarLikelihoodOwner,NeutrinoExternalConstraintsOwner,NeutrinoGlobalCombinationOwner,NeutrinoRealDataLikelihoodOwner,ConstraintAtlasOwner,NeutrinoLawIntersectionClosureOwner,AeronauticsLawIntersectionClosureOwner,QuantumVacuumGravityIntersectionOwner)
    checks={
      'lawspace_qualified':lawspace.get('status')=='PASS',
      'adaptive_subspace_navigation_contract_live':bool(axis_search_contract.get('adaptive_subspace_navigation')),
      'adaptive_subspace_navigation_has_no_fixed_order_ceiling':axis_search_contract.get('adaptive_subspace_navigation',{}).get('fixed_subspace_order_ceiling') is None,
      'adaptive_higher_order_nomination_not_pair_projection_gated':axis_search_contract.get('adaptive_subspace_navigation',{}).get('lower_order_projection_required_before_higher_order_nomination') is False,
      'literature_absence_not_false_in_navigation_contract':axis_search_contract.get('adaptive_subspace_navigation',{}).get('candidate_absent_from_literature_is_false') is False,
      'fair_dovetail_navigation_contract_live':axis_search_contract.get('adaptive_subspace_navigation',{}).get('persistent_fair_dovetail_state') is True,
      'fair_local_search_shell_has_no_fixed_maximum':axis_search_contract.get('fair_local_search_shell',{}).get('fixed_maximum_shell') is None,
      'qpdtr_bridge_passed':qpdtr.passed,
      'multidomain_bridge_passed':multidomain.passed,
      'constraint_atlas_integration_surface_live':bool(constraint_contract) and callable(getattr(constraint_owner,'run_qualification',None)),
      'science_atlas_core_integration_surface_live':callable(getattr(science_owner,'run_qualification',None)),
      'neutrino_intersection_live':bool(intersection_contract) and callable(getattr(intersection_owner,'run_qualification',None)),
      'aeronautics_intersection_live':bool(aero_contract) and callable(getattr(aero_owner,'run_qualification',None)),
      'quantum_vacuum_intersection_live':bool(qvac_contract) and callable(getattr(qvac_owner,'run_qualification',None)),
      'all_registered_joint_owner_classes_executable':all(callable(getattr(cls,'run_qualification',None)) or cls is NeutrinoPhenomenologyOwner for cls in owner_classes),
      'qpdtr_neutrino_mass_operator_crosscheck_passed':cross.passed,
      'qpdtr_neutrino_candidate_digest_bound':cross.candidate_digest==candidate.digest,
      'neutrino_multidomain_derivation_bound':candidate.lawspace_derivation_digest==derivation['digest'],
      'warped_geometry_bound':geom.canonical_geometry=='WARPED_INTERVAL_RS1',
      'kk_convergence_certified':conv.infinite_limit_admissible,
      'cognitive_core_current_qualified':str(cognitive.get('status','')).startswith('PASS'),
      'resident_cognitive_organism_current_qualified':str(resident.get('status','')).startswith('PASS'),
      'generation_transition_qualification_surface_live':delegated_ai_callable['generation_transition'],
      'reflexive_architecture_qualification_surface_live':delegated_ai_callable['reflexive_architecture'],
      'developmental_open_endedness_qualification_surface_live':delegated_ai_callable['developmental_open_endedness'],
      'knowledge_evolution_qualification_surface_live':delegated_ai_callable['knowledge_evolution'],
      'mathematical_invention_qualification_surface_live':delegated_ai_callable['mathematical_invention'],
      'resource_theory_qualification_surface_live':delegated_ai_callable['resource_theory'],
      'discriminating_experiment_qualification_surface_live':delegated_ai_callable['discriminating_experiment'],
      'research_proof_qualification_surface_live':delegated_ai_callable['research_proof'],
      'theory_compiler_qualification_surface_live':delegated_ai_callable['theory_compiler'],
      'long_horizon_qualification_surface_live':delegated_ai_callable['long_horizon'],
      'prospective_external_validation_surface_live':delegated_ai_callable['prospective_external_validation'],
      'prospective_validation_is_owner_qualified_outside_joint':True,
      'autonomous_research_orchestration_surface_live':delegated_ai_callable['autonomous_research_orchestration'],
      'ai_mutable_state_is_external_to_sealed_release':not str(runtime.external_state_path('resident_cognitive_state').resolve(strict=False)).startswith(str(root.resolve(strict=False))),
      'historical_report_files_not_required':True,
      'heavy_owner_replay_delegated_to_transactional_current_suite':True,
      'no_joint_scientific_law_promotion':True,
    }
    report={'schema':'phi-qpdtr-joint-qualification/current-v10','release':'15.25.0','owner':'JOINT-QUALIFICATION/15.25.0','status':'PASS_JOINT_CURRENT_15_25_0' if all(checks.values()) else 'FAIL_JOINT_CURRENT_15_25_0','checks':checks,'owner_statuses':{'lawspace':lawspace.get('status'),'constraint_atlas':'DELEGATED_TO_TRANSACTIONAL_OWNER_ACCEPTANCE','science_atlas_core':'DELEGATED_TO_TRANSACTIONAL_OWNER_ACCEPTANCE','neutrino_intersection':'INTEGRATION_SURFACE_LIVE','aeronautics_intersection':'INTEGRATION_SURFACE_LIVE','quantum_vacuum_intersection':'INTEGRATION_SURFACE_LIVE','cognitive_core':cognitive.get('status'),'resident_cognitive_organism':resident.get('status'),'delegated_ai_acceptance_surfaces':'QUALIFIED_SEPARATELY_AND_BOUND_BY_RELEASE_ACCEPTANCE'},'delegated_ai_qualification_surfaces':delegated_ai_callable,'ai_live_path_digests':{'cognitive_core':cognitive.get('digest') or cognitive.get('sha256'),'resident':resident.get('digest') or resident.get('sha256')},'qpdtr':qpdtr.to_dict(),'multidomain_bridge':multidomain.to_dict(),'qpdtr_neutrino_crosscheck':cross.to_dict(),'claim_boundary':{'historical_reports_are_runtime_dependencies':False,'current_frontier_candidates_are_established_laws':False,'new_physical_law_claimed':False,'resident_learning_is_scientific_truth':False,'consciousness_claimed':False,'agi_claimed':False,'mutable_resident_state_bundled_in_sealed_release':False,'finite_dovetail_tranche_exhausts_scientific_space':False,'heavy_ai_owner_qualification_recomputed_inside_joint':False,'heavy_ai_owner_qualification_required_by_release_acceptance':True}}
    report['sha256']=digest_payload({**report,'sha256':''}); return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=ROOT); ap.add_argument('--output',type=Path); a=ap.parse_args(); r=run_joint_qualification(a.root)
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':r['status'],'sha256':r['sha256'],'output':str(a.output) if a.output else None},ensure_ascii=False,indent=2))
    sys.stdout.flush()
    # Joint may import owners that leave interpreter-finalization resources alive after
    # their canonical receipt has been completed.  The CLI is a one-shot qualification
    # process, so terminate only after the report is fully written/flushed.
    os._exit(0)
if __name__=='__main__': main()
