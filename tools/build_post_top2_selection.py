#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare allocation-free finite greedy on the actual Q4/Top2 composition."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include "finite_greedy.h"
#include <atomic>
#include <chrono>
namespace {std::atomic<bool>post_selection{false};std::uint64_t post_selection_stats[6]{};
std::uint64_t post_selection_now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}}
extern "C" void qwen_post_selection_select(bool v){post_selection.store(v);}
extern "C" void qwen_post_selection_stats(std::uint64_t*out){std::copy_n(post_selection_stats,6,out);}
'''

def engine_source(text):
    start=text.index('Token LlamaEngine::next_once() {');end=text.index('\nvoid LlamaEngine::finish()',start)
    body=text[start:end]
    finite='''        for (int i = 0; i < count; ++i) {
            if (!std::isfinite(logits[i])) throw std::runtime_error("Non-finite model logits");
        }'''
    body=once(body,finite,'''        const bool fast_selection=post_selection.load();
        const unsigned selection_arm=fast_selection?1:0;const auto checked_start=post_selection_now();
        llama_token direct_token=LLAMA_TOKEN_NULL;
        if(fast_selection)direct_token=qwen_app::finite_greedy(logits,std::size_t(count));
        else {
'''+finite+'''
        }
        post_selection_stats[selection_arm]+=post_selection_now()-checked_start;
        ++post_selection_stats[4+selection_arm];''')
    body=once(body,'        if(restored_logits_active_) {',
        '''        const auto sample_start=post_selection_now();
        if(fast_selection){pending_=direct_token;llama_sampler_accept(sampler_,pending_);}
        else if(restored_logits_active_) {''')
    body=once(body,'        if (pending_ < 0 || pending_ >= count)',
        '        post_selection_stats[2+selection_arm]+=post_selection_now()-sample_start;\n        if (pending_ < 0 || pending_ >= count)')
    return PREFIX+text[:start]+body+text[end:]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    old=n['GDN_model_comparison']['scope'];require(old['candidate']=='Q4-cache3712-Top2','Actual measured Q4/Top2 parent required')
    scope=dict(old,schema='ps5-qwen-post-top2-selection-v1',candidate='allocation-free-finite-greedy',candidate_id=1,
        control_Experts=2,candidate_Experts=2,candidate_full_vocab_bit_equality_required=True,
        candidate_F32_and_token_equality_required=True,complete_finite_checks_in_both_arms=True,
        GPU_argmax_selected=False,additional_GPU_operations=False,additional_CPU_allocations=0)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    entry=once(entry,literal(old),literal(scope))
    entry='#include <cstdint>\nextern "C" void qwen_post_selection_select(bool);\nextern "C" void qwen_post_selection_stats(std::uint64_t*);\n'+entry
    entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_post_selection_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";',
               'arm==0?"Top2-original-greedy":"Top2-finite-greedy";')
    for old,new in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),
                    ('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),
                    ('else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))',
                     'else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])'),
                    ('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:entry=once(entry,old,new)
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);',
               '            std::uint64_t selection_before[6]{};qwen_post_selection_stats(selection_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["phase"]=phase;',
        '            std::uint64_t selection_after[6]{};qwen_post_selection_stats(selection_after);Json selection_delta=Json::array();for(unsigned i=0;i<6;++i)selection_delta.push_back(selection_after[i]-selection_before[i]);row["selection_timing_delta"]=selection_delta;\n            row["phase"]=phase;')
    en=n['routing_sharing']['commands'][2];engine=engine_source(Path(en[en.index('-c')+1]).read_text())
    variants={k:(cmd+['-I',str(ROOT/'native/app')],text)for k,(cmd,text)in dict(entry=(ec,entry),engine=(en,engine)).items()}
    r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),ROOT/'native/app/finite_greedy.h'])
    update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_selection']=dict(scope=scope,actual_sources=sources,commands=jobs)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='post_top2_finite_greedy_comparison',scope=scope,
        candidate=record(a.out/'receipt.private.json'),original_GPU_and_model_unchanged=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
