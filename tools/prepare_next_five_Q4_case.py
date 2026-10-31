#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the combined Q4/cache experiment to its newly sealed source directory."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);p.add_argument('--publication',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_next_five_case.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name],check=True,cwd=ROOT)
 path=ROOT/f'.local/prepared_phase_model_{a.case}.private.py';text=path.read_text();import json
 text=once(text,"receipt_record=all_Q8_publication['candidate'];op.unchanged(receipt_record)","precision_publication=op.load(Path("+repr(str(a.publication))+"));receipt_record=precision_publication['candidate'];op.unchanged(receipt_record)")
 marker="    policy['native_resident_all_Q8']=actual_native['resident_all_Q8']"
 text=once(text,marker,marker+"\n    policy['native_precision_candidate']=actual_native['precision_candidate']['scope']\n    precision_seal=Path(precision_publication['source_integrity']['path']);op.unchanged(precision_publication['source_integrity'])\n    gate['precision_source_integrity']=dict(schema='ps5-qwen-precision-source-policy-v1',raw=precision_seal.read_bytes().decode('utf-8'),sha256=op.sha(precision_seal))")
 text=once(text,"app['model_receipt']=op.load(all_Q8_seal)['source_directory']+'/model-receipt.json'","app['model_receipt']=op.load(precision_seal)['source_directory']+'/model-receipt.json'")
 text=text.replace('active_cache_slots=3072','active_cache_slots=3712').replace('non_Expert_precision_preserved=False','non_Expert_precision_preserved=False')
 text=text.replace('installed control/candidate A-B-B-A cold-retained pairs','Q4 common-weight3072/3712 A-B-B-A cold-retained pairs; installed Q8 requires separate nearby comparison')
 ast.parse(text);path.write_text(text,newline='\n');print('Newly sealed Q4 sources and explicit3712 geometry bound; no console operation.')
if __name__=='__main__':main()
