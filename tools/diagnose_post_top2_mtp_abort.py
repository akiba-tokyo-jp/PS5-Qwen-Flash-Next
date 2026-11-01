#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve MTP constructor/graph assertions before the library aborts normally."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text()
 for old,new in [('if(!post_mtp.aux){auto p=llama_context_default_params();','if(!post_mtp.aux){stage("MTP_aux_context_initialization_begin");auto p=llama_context_default_params();'),
  ('post_mtp.batch=llama_batch_ext_init(post_mtp.aux);','stage("MTP_aux_context_initialization_returned");post_mtp.batch=llama_batch_ext_init(post_mtp.aux);'),
  ('llama_memory_clear(llama_get_memory(post_mtp.aux),true);','stage("MTP_aux_memory_clear_begin");llama_memory_clear(llama_get_memory(post_mtp.aux),true);'),
  ('if(llama_process(post_mtp.aux,LLAMA_PROCESS_TYPE_DECODE,post_mtp.batch)!=0)','stage("MTP_aux_graph_compute_begin");if(llama_process(post_mtp.aux,LLAMA_PROCESS_TYPE_DECODE,post_mtp.batch)!=0)')]:engine=once(engine,old,new)
 ec=n['compile_commands'][0];entry='#include "native_failure_journal.h"\n'+Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,durable_native_assertion_callback=True,auxiliary_context_and_compute_stage_boundaries=True,no_GPU_reset_or_retry_from_callback=True)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'        const auto policy = Json::parse(policy_file);','        qwen_app::install_native_assertion_journal();\n        const auto policy = Json::parse(policy_file);')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine)),[Path(__file__),ROOT/'native/app/native_failure_journal.h'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_abort_diagnostic']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),default_abort_behavior_preserved=True,original_math_quotas_and_completion_guards_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
