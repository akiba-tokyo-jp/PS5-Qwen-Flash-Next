#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the expanded-cache scope to the exact inherited cold-request check."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','control','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=json.loads(a.parent.read_text());c=json.loads(a.control.read_text())
    require(r['resident_cache3072']['active_slots']==3072 and
            r['resident_retention_cohort']['requests']==12,'Exact finite retention candidate required')
    a.out.mkdir(parents=True,exist_ok=False)
    cmd=r['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
    text=once(text,literal(c['cold_request']['scope']),literal(r['cold_request']['scope']))
    text=once(text,'{"empty_expert_cache_before_independent_request",true}',
        '{"empty_expert_cache_before_independent_request",false},{"request_state_still_empty",true}')
    result,jobs,sources=link(a.parent,a.out,dict(entry=(cmd,text)),[Path(__file__),a.control])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8',
                'resident_cache3072','memory_quality_cohort'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry']
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    result['routing_winners_normal']['actual_entry']=sources['entry']
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,
        kind='resident_cache_scope_binding_only',original_physical_and_kernel_guards_preserved=True,
        CPU_heap_limit_bytes=512<<20,workspace_bytes=48<<20,cache_slots=3072,
        Expert_Q2_payloads_unchanged=True,driver_unchanged=True,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
