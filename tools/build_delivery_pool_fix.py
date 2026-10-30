#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recompile only the pool owner after correcting pinned legacy destinations."""
import argparse,json
from pathlib import Path
from expert_q4 import record,write_json,require
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='delivery_followup','Explicit current experimental owner required');a.out.mkdir(parents=True,exist_ok=False)
 cmd=prior['all_Q2_optimized_monitor']['commands'][1];text=Path(cmd[cmd.index('-c')+1]).read_text()
 result,jobs,sources=link(a.parent,a.out,dict(owner=(cmd,text)),[Path(__file__),ROOT/'native/app/delivery_read_pool.h'])
 for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
 for key in ('cold_request','delivery_followup'):result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
 result['delivery_pool_fix']=dict(legacy_original_targets_preserved_at_depth2_3_4=True,actual_source=sources['owner'],command=jobs['owner'],pool_header=record(ROOT/'native/app/delivery_read_pool.h'),prior_failed_native_case=11120)
 seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='legacy_destination_pin_fix',original_memory_identity_driver_and_completion_guards=True,original_streaming_payload_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
 print('Only the pool owner recompiled; prior completed bundle/wide comparisons are not repeated.')

if __name__=='__main__':main()
