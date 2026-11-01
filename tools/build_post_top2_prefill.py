#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a phase-specific prefill budget without changing Top2 decode."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import command_for,update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--experts',type=int,choices=(4,),default=4)
    p.add_argument('--adaptive-tail16',action='store_true')
    a=p.parse_args();n=json.loads(a.parent.read_text());old=n['GDN_model_comparison']['scope']
    require(old['candidate']=='Q4-cache3712-Top2','Actual Q4/Top2 parent required')
    a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(old,schema='ps5-qwen-post-top2-prefill-v1',candidate='prefill-Top4-decode-Top2',candidate_id=1,
        control_Experts=2,candidate_Experts=2,control_prefill_Experts=6,candidate_prefill_Experts=4,
        selected_phase_is_explicit=True,KV_precision_preserved=True,quality_changes_reported=True)
    if a.adaptive_tail16:scope.update(candidate='prefill-nonfinal4-final16tokens6-decode2',adaptive_prefill=True,final_prefill_tokens=16,
        extra_prefill_calls_at_most=1,depends_on_prompt_position_not_benchmark_contents=True)
    ec=n['compile_commands'][0];rc=command_for(n,'routing.private.cpp');gc=command_for(n,'graph.private.cpp')
    entry=Path(ec[ec.index('-c')+1]).read_text()
    entry='extern "C" void qwen_post_prefill_select(bool);\n'+entry
    entry=once(entry,literal(old),literal(scope))
    entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_post_prefill_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";',
        'arm==0?"prefill6-decode2":"prefill4-decode2";')
    entry=once(entry,'            row["phase"]=phase;',
        '            row["selected_prefill_Experts"]=arm?4:6;row["selected_decode_Experts"]=2;\n            row["phase"]=phase;')
    entry=reporting(entry)
    if a.adaptive_tail16:
        entry=entry.replace('"prefill4-decode2"','"prefill-nonfinal4-final16tokens6-decode2"')
    routing=Path(rc[rc.index('-c')+1]).read_text()
    routing='namespace {bool post_prefill_four=false;}\nextern "C" void qwen_post_prefill_select(bool v){post_prefill_four=v;}\nextern "C" unsigned qwen_post_prefill_experts(){return post_prefill_four?4:6;}\n'+routing
    routing=once(routing,'return ((six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode()))*8+qwen_next_experts();',
        'return (((six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode()))*8+qwen_next_experts())*8+qwen_post_prefill_experts();')
    if a.adaptive_tail16:
        routing=once(routing,'namespace {bool post_prefill_four=false;}','namespace {bool post_prefill_four=false,post_prefill_final=true;}')
        routing=once(routing,'return post_prefill_four?4:6;','return post_prefill_four&&!post_prefill_final?4:6;')
        routing+='\nextern "C" bool qwen_post_prefill_adaptive(){return post_prefill_four;}\nextern "C" void qwen_post_prefill_boundary(bool final){post_prefill_final=final;}\n'
    graph=Path(gc[gc.index('-c')+1]).read_text()
    graph='extern "C" unsigned qwen_post_prefill_experts();\n'+graph
    graph=once(graph,'if(n_expert==512&&n_expert_used==10&&!qwen_app_route_is_decode())\n        n_expert_used=qwen_app_six_prefill_experts();',
        'if(n_expert==512&&n_expert_used==10&&!qwen_app_route_is_decode())\n        n_expert_used=qwen_post_prefill_experts();')
    variants={k:(c+['-I',str(ROOT/'native/app')],s)for k,(c,s)in dict(entry=(ec,entry),routing=(rc,routing),graph=(gc,graph)).items()}
    if a.adaptive_tail16:
        engine_command=n['routing_sharing']['commands'][2];engine=Path(engine_command[engine_command.index('-c')+1]).read_text()
        engine='extern "C" bool qwen_post_prefill_adaptive();\nextern "C" void qwen_post_prefill_boundary(bool);\n'+engine
        engine=once(engine,'const auto count = std::uint32_t(std::min<std::size_t>(prefill_tokens_, prompt_.size() - i));',
            '''const auto remaining=prompt_.size()-i;
            const auto extent=qwen_post_prefill_adaptive()&&remaining>16?std::min<std::size_t>(prefill_tokens_,remaining-16):std::min<std::size_t>(prefill_tokens_,remaining);
            const auto count=std::uint32_t(extent);qwen_post_prefill_boundary(remaining<=16);''')
        variants['engine']=(engine_command,engine)
    r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),ROOT/'tools/qualify_post_top2_reporting.py'])
    update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_prefill']=dict(scope=scope,actual_sources=sources,commands=jobs,phase_key_covers_both_budgets=True)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='phase_specific_prefill_budget_comparison',
        candidate=record(a.out/'receipt.private.json'),scope=scope,original_GPU_driver_and_model_unchanged=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
