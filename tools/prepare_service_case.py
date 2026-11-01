#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the qualified fourteen-request protocol with exact loading policy."""
import argparse,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
 for k in('build-name','package-name'):p.add_argument('--'+k,required=True)
 p.add_argument('--publication',required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/prepare_post_top2_comparison.py','--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--publication',a.publication],check=True)
 path=ROOT/f'.local/prepared_phase_model_{a.case}.private.py';s=path.read_text();m="policy['native_next_five']=actual_native['next_five_comparison']['scope']";s=once(s,m,m+"\n    policy['native_post_top2_loading_reserved']=actual_native['post_top2_loading_reserved']['scope']");path.write_text(s,newline='\n');print('Exact current loading policy and fresh comparison prepared; no console operation.')
if __name__=='__main__':main()
