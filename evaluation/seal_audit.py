"""Seal audit for Φ-Compiler / ScienceAtlas 0.15.28.0 current state."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.schema import digest_payload
from evaluation.unified_release_qualification import run_release_qualification
from evaluation.release_files import is_local_artifact
RELEASE='0.15.28.0'; OWNER_ID='SEAL-AUDIT/0.15.28.0'
REQUIRED=('README.md','MATHEMATICAL_BOOK.md','MATHEMATICAL_CONTRACT.md','CLAIM_BOUNDARY.md','ACCEPTANCE_REPORT.md','RELEASE_MANIFEST.json','HASHES.txt','FILE_TREE.md','pyproject.toml','Makefile','capabilities.json','invariants.json','reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json','reports/ATLAS_FRONTIER_SCAN_CURRENT.json','data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(root=None):
 root=Path(root or ROOT).resolve(); missing=[x for x in REQUIRED if not (root/x).exists()]
 manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text()) if not missing else {}
 mism=[]
 for row in manifest.get('controlled_files',[]):
  p=root/row['path']
  if not p.exists() or sha(p)!=row['sha256'] or p.stat().st_size!=row['size']: mism.append(row['path'])
 hashes={}
 if (root/'HASHES.txt').exists():
  for line in (root/'HASHES.txt').read_text().splitlines():
   if '  ' in line:
    h,r=line.split('  ',1); hashes[r]=h
 controlled_paths=sorted(str(row.get('path')) for row in manifest.get('controlled_files',[]))
 hash_mism=[r for r,h in hashes.items() if not (root/r).exists() or sha(root/r)!=h]
 hashes_complete_and_exact=sorted(hashes)==controlled_paths and all(hashes.get(row.get('path'))==row.get('sha256') for row in manifest.get('controlled_files',[]))
 actual_files=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and not is_local_artifact(p,root))
 declared_files=sorted(controlled_paths+['RELEASE_MANIFEST.json','HASHES.txt','FILE_TREE.md'])
 unexpected_files=sorted(set(actual_files)-set(declared_files))
 undeclared_missing=sorted(set(declared_files)-set(actual_files))
 current=run_release_qualification(root)
 real=json.loads((root/'reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json').read_text()) if not missing else {}
 scan=json.loads((root/'reports/ATLAS_FRONTIER_SCAN_CURRENT.json').read_text()) if not missing else {}
 checks={'required_files_present':not missing,'manifest_file_hashes_match':not mism,'hashes_txt_match':not hash_mism and hashes_complete_and_exact,'current_state_qualification_pass':current.get('status')=='PASS_CURRENT_STATE_15_28_0','manifest_release_matches':manifest.get('release')==RELEASE,'manifest_blind_real_experiment_digest_matches':manifest.get('blind_real_physics_experiment_digest')==current.get('blind_real_physics_experiment',{}).get('digest'),'manifest_research_freeze_digest_matches':manifest.get('research_freeze_digest')==real.get('research_freeze',{}).get('digest'),'manifest_frontier_scan_digest_matches':manifest.get('frontier_scan_digest')==scan.get('digest')==current.get('frontier_candidate_scan',{}).get('digest'),'manifest_active_candidate_ledger_matches':manifest.get('active_candidate_ledger_sha256')==scan.get('active_candidate_ledger',{}).get('sha256')==current.get('frontier_candidate_scan',{}).get('ledger_sha256'),'manifest_active_candidate_count_matches':manifest.get('active_candidate_count')==scan.get('active_candidate_ledger',{}).get('record_count') and int(manifest.get('active_candidate_count') or 0)>0,'manifest_low_frequency_gust_anomaly_digest_matches':manifest.get('low_frequency_gust_anomaly_digest')==scan.get('hotspots',{}).get('low_frequency_gust_anomaly',{}).get('digest'),'closed_world_no_unexpected_files':not unexpected_files,'closed_world_no_declared_missing_files':not undeclared_missing}
 payload={'schema':'phi-seal-audit/current-v1','release':RELEASE,'owner':OWNER_ID,'status':'PASS_SEAL_AUDIT' if all(checks.values()) else 'FAIL_SEAL_AUDIT','checks':checks,'missing':missing,'manifest_mismatches':mism,'hash_mismatches':hash_mism,'unexpected_files':unexpected_files,'undeclared_missing_files':undeclared_missing,'current_state_digest':current.get('digest')}
 payload['digest']=digest_payload(payload); return payload
if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
