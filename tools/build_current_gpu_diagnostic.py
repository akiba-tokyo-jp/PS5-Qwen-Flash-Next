#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse an identical qualified timestamp provider for the current composition."""
import copy,json,sys
from pathlib import Path
import build_gpu_kernel_timing as timing
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json

original_link=timing.link
qualified=None
def reuse_link(parent,out,variants,inputs):
    prior=json.loads(Path(parent).read_text());q=json.loads(qualified.read_text());g=q['GPU_kernel_timing']
    require(g['diagnostic_only']and g['per_graph_fence_timeout_ns']==5000000000 and g['query_result_WAIT_flag']is False,'Previously bounded qualified query provider required')
    require(prior['driver']==q['driver']and prior['lossless_shader_storage']['vulkan_object']==g['original_GPU_object'],'The actual current GPU code and driver must be identical')
    source=g['actual_sources']['GPU'];require(record(Path(source['path']))==source,'Qualified timestamp source changed')
    require(variants['GPU'][1]==Path(source['path']).read_text(),'Current generated GPU diagnostic differs; do not reuse its object')
    command=g['commands']['GPU'];obj=Path(command[command.index('-o')+1]);captured=next(r for r in q['inputs_before']if Path(r['path'])==obj);require(record(obj)==captured,'Qualified GPU object changed')
    seed=copy.deepcopy(prior);old=g['original_GPU_object']['path'];require(seed['link_command'].count(old)==1,'One exact selected GPU provider required');seed['link_command'][seed['link_command'].index(old)]=str(obj)
    seed['inputs_before'] +=[record(qualified),source,captured];path=Path(out)/'reuse-seed.private.json';write_json(path,seed)
    scope=dict(prior['cold_request']['scope'],mode='current_GPU_timestamp_diagnostic',additional_GPU_operations=True,diagnostic_scheduling_changes=True,ordinary_speed_comparison_valid=False)
    cmd,text=variants['entry'];text=once(text,literal(prior['cold_request']['scope']),literal(scope));result,jobs,sources=original_link(path,out,dict(entry=(cmd,text)),[*inputs,qualified,Path(source['path']),obj,Path(__file__)])
    jobs['GPU']=command;sources['GPU']=source
    result['cold_request'].update(scope=scope,normal_validation_pending=True,production_adopted=False)
    result['cold_request']['actual_sources']['entry']=sources['entry'];result['cold_request']['commands']['entry']=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    result['reused_timestamp_provider']=dict(qualification=record(qualified),actual_source=source,actual_object=captured,compiled_again=False)
    return result,jobs,sources

def main():
    global qualified
    i=sys.argv.index('--qualified-GPU');qualified=Path(sys.argv[i+1]);del sys.argv[i:i+2]
    timing.link=reuse_link;timing.main()
    out=Path(sys.argv[sys.argv.index('--out')+1]);r=json.loads((out/'receipt.private.json').read_text())
    write_json(out/'core-safety.private.json',dict(completed=True,kind='current_GPU_diagnostic_reusing_identical_provider',driver_and_original_physical_reserves_preserved=True,
        per_graph_fence_ns=5000000000,query_WAIT_flag=False,diagnostic_only=True,candidate=record(out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
