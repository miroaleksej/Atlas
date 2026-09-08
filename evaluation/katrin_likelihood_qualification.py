#!/usr/bin/env python3
"""Thin evaluator for KATRIN-SPECTRAL-LIKELIHOOD."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.katrin_spectral_likelihood import KATRINSpectralLikelihoodOwner

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=ROOT); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    r=KATRINSpectralLikelihoodOwner(a.root).run_qualification(); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':r['status'],'output':str(a.output)},ensure_ascii=False))
if __name__=='__main__': main()
