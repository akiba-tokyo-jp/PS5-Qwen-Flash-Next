#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a fresh case with its exact loading-reservation policy bound early."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
 for k in ('build-name','package-name','publication'):p.add_argument('--'+k,required=True)
 a=p.parse_args();subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_post_top2_comparison.py'),
  '--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--publication',a.publication],check=True,cwd=ROOT)
 path=ROOT/f'.local/prepared_phase_model_{a.case}.private.py';s=path.read_text();marker="    policy['native_resident_all_Q8']=actual_native['resident_all_Q8']"
 s=once(s,marker,marker+"\n    policy['native_post_top2_loading_reserved']=actual_native['post_top2_loading_reserved']['scope']")
 ast.parse(s);path.write_text(s,newline='\n');print('Fresh loading-only reservation scope bound; no console operations.')
if __name__=='__main__':main()
