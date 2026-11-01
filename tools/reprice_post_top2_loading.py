#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind an explicit loading-only OS-reservation experiment to actual providers."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());proof=json.loads(a.proof.read_text())
 header=ROOT/'native/app/post_top2_loading_reserve.h';require(proof['completed']and proof['boundary_cases']==27 and any(x==record(header)for x in proof['inputs']),'Exact27-case boundary proof required')
 a.out.mkdir(parents=True,exist_ok=False)
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 matches=[c for c in selected.values()if 'return limit_probe.required(free,minimum,reserved,legacy)-minimum;'in Path(c[c.index('-c')+1]).read_text()]
 require(len(matches)==1,'One actual linked memory-admission provider required');mc=matches[0];memory=Path(mc[mc.index('-c')+1]).read_text()
 memory='#include "post_top2_loading_reserve.h"\nnamespace {qwen_app::PostTop2LoadingReserve post_loading_reserve;}\nextern "C" void qwen_post_loading_reserve_select(bool v){post_loading_reserve.select(v);}\nextern "C" void qwen_post_loading_reserve_stats(std::uint64_t*out){const auto v=post_loading_reserve.stats();std::copy(v.begin(),v.end(),out);}\n'+memory
 memory=once(memory,'return limit_probe.required(free,minimum,reserved,legacy)-minimum;',
  'return limit_probe.required(free,minimum,reserved,post_loading_reserve.extra(free,minimum,reserved,legacy))-minimum;')
 old=n['GDN_model_comparison']['scope'];scope=dict(schema='ps5-qwen-post-top2-loading-reservation-v1',legacy_application_padding_pages=256,
  selected_loading_application_padding_pages=206,expected_OS_minimum_pages=898,expected_OS_reserved_pages=206,
  OS_counter_writes=0,physical_CPU_heap_device_ledger_workspace_and_GPU_completion_unchanged=True,
  once_only_between_loading_phase1_and2=True,no_unchanged_refused_launch_repeated=True,automatic_retries=0)
 comparison=dict(old,loading_application_experiment=scope,original_loading_application_padding_preserved=False)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
 entry='#include <cstdint>\nextern "C" void qwen_post_loading_reserve_select(bool);\nextern "C" void qwen_post_loading_reserve_stats(std::uint64_t*);\n'+entry
 entry=once(entry,literal(old),literal(comparison))
 entry=once(entry,'        qwen_limit_probe_stage(1);','        if(policy.at("native_post_top2_loading_reserved")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact loading-only reservation experiment required");\n        qwen_limit_probe_stage(1);qwen_post_loading_reserve_select(true);')
 entry=once(entry,'        qwen_limit_probe_stage(2);','        qwen_post_loading_reserve_select(false);qwen_limit_probe_stage(2);')
 entry=once(entry,'static Json limit_probe_report(){','static Json limit_probe_report(){\n std::uint64_t post_loading[6]{};qwen_post_loading_reserve_stats(post_loading);')
 entry=once(entry,'return {{"schema","ps5-qwen-limit-probe-result-v1"}',
  'return {{"explicit_loading_reservation_scope",{{"active",bool(post_loading[0])},{"consumed",bool(post_loading[1])},{"calls",post_loading[2]},{"changed_calls",post_loading[3]},{"original256_would_refuse",post_loading[4]},{"minimum_free_pages",post_loading[5]==UINT64_MAX?Json(nullptr):Json(post_loading[5])},{"OS_minimum_pages",898},{"OS_reserved_pages",206},{"selected_padding_pages",206}}},{"schema","ps5-qwen-limit-probe-result-v1"}')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),loading=(mc+['-I',str(ROOT/'native/app')],memory)),[Path(__file__),a.proof,header])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=comparison;r['next_five_comparison'].update(scope=comparison,actual_sources=sources,commands=jobs)
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==mc[mc.index('-o')+1]:row.update(object_path=jobs['loading'][jobs['loading'].index('-o')+1],source=sources['loading'],command=jobs['loading'])
 r['post_top2_loading_reserved']=dict(scope=scope,actual_sources=sources,commands=jobs,boundary_proof=record(a.proof),original_loading_padding_preserved=False)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='explicit_loading_only_OS_reservation',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
