#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify lower-precision storage without replacing the live cache context."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--kind',choices=['KV16','RS16'],required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope']
 scope=dict(old,schema='ps5-qwen-next-five-single-context-storage-v1',candidate=a.kind+'-single-context',one_context_for_entire_run=True,all_requests_storage_bits=16,
  within_run_storage_ABBA=False,storage_comparison_requires_separate_F32_run=True,quality_forces_EOS_rejections=True)
 entry=once(entry,literal(old),literal(scope))
 start=entry.index('                llama_free(context);context=nullptr;resident_reused_context=nullptr;');end=entry.index('                resident_reset_empty_context(context,model,startup.admission_report);',start)
 entry=entry[:start]+entry[end:]
 entry=once(entry,'        context = llama_init_from_model(model, qwen_app::streaming_context_params(','        qwen_next_select(6);qwen_native_stage("selected_16bit_storage_before_single_context_creation");\n        context = llama_init_from_model(model, qwen_app::streaming_context_params(')
 if a.kind=='KV16':entry=once(entry,'{"KV_bits",arm?16:32}','{"KV_bits",16}')
 else:entry=once(entry,'{"recurrent_S_bits",arm?16:32}','{"recurrent_S_bits",16}')
 entry=once(entry,'            row["phase"]=phase;','            row["storage_single_context"]=true;row["within_run_storage_ABBA"]=false;\n            row["phase"]=phase;')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__)]);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='single_context_16bit_storage',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
