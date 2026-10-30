#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep selected IDs live while shared-Expert work precedes slot lookup."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['ordered_overlap']['original_context_archive_member_verified'],'Exact ordered-lifetime parent required');a.out.mkdir(parents=True,exist_ok=False)
    command=prior['normal_performance']['commands']['graph'];source=Path(command[command.index('-c')+1]);text=source.read_text()
    text=once(text,'    if(auto*shared=qwen_app_overlap_graph_take(il))ggml_build_forward_expand(gf,shared);',
        '''    if(auto*shared=qwen_app_overlap_graph_take(il)){
        // Slot lookup still consumes these IDs after the I/O callback. Its
        // original topological lifetime ends too early for the shared prepass.
        // Protect the actual contiguous backing tensor, including view chains.
        auto*root=ids;while(root->view_src)root=root->view_src;
        ggml_set_output(root);ggml_set_output(ids);
        ggml_build_forward_expand(gf,shared);
    }''')
    archive=a.parent.parent/'qualified-runtime-source.private.cpp';require(record(archive)['sha256']==prior['delivery_overlap']['runtime_source']['sha256'],'Exact parent runtime archive required')
    result,jobs,actual=link(a.parent,a.out,dict(graph=(command,text)),[Path(__file__),source,archive])
    for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
    result['routing_sharing']['actual_sources']['graph']=actual['graph']
    result['cold_request']['actual_sources'].update(actual);result['cold_request']['commands'].update(jobs)
    result['ordered_overlap'].update(selected_ID_lifetime_protected=True,original_workspace_cap=True,actual_sources=actual,commands=jobs,allocation_order_qualified=False)
    result['pinned_ID_overlap']=dict(actual_sources=actual,commands=jobs,physical_cache_and_driver_unchanged=True,original_workspace_cap=48<<20,dependent_and_live_alias_refusal_retained=True,selection_values_unmodified=True,GPU_submission_pending_native_qualification=True,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='selected_ID_live_range_protection',original_guards_and_workspace_cap=True,selection_values_unmodified=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Original selected-ID backing kept live; no guard or memory cap relaxed.')


if __name__=='__main__':main()
