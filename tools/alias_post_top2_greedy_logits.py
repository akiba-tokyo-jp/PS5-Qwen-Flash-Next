#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Share unchanged full sampled/raw logit rows for the isolated greedy chain."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);cc=n['post_top2_compact_sampler_outputs']['commands']['context'];ctx=Path(cc[cc.index('-c')+1]).read_text()
 ctx=once(ctx,'    const bool post_compact=has_sampling&&qwen_post_compact_greedy_outputs();','''    const bool post_compact=has_sampling&&qwen_post_compact_greedy_outputs();
    const bool post_alias=post_compact&&has_logits&&!has_embd&&!has_embd_nextn&&!embd_layer_inp_float_count&&
        cparams.n_seq_max==1&&sampling.samplers.size()==1&&sampling.samplers.count(0)==1;
''')
 ctx=once(ctx,'(logits.size + embd.size + embd_nextn.size + embd_layer_inp_float_count + backend_float_count) * sizeof(float)',
  '((post_alias?0:logits.size) + embd.size + embd_nextn.size + embd_layer_inp_float_count + backend_float_count) * sizeof(float)')
 ctx=once(ctx,'    offset += logits.size * sizeof(float);','    offset += (post_alias?0:logits.size) * sizeof(float);')
 # Greedy leaves logits unchanged; both public full-vocabulary views point to
 # the returned sampled row. The framework intentionally skips raw downloads
 # when every sequence is sampled, so a separate raw plane would be stale.
 ctx=once(ctx,'        if (logits.size > 0) {','        if (logits.size > 0 && logits.data != sampling.logits.data) {')
 en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text()
 engine='''#include <mutex>
#include <cstdio>
#include "llama.h"
namespace {std::mutex post_decode_log_mutex;char post_decode_log[768]{};
void post_decode_capture(enum ggml_log_level level,const char*text,void*){if(level>=GGML_LOG_LEVEL_ERROR){std::lock_guard<std::mutex>lock(post_decode_log_mutex);std::snprintf(post_decode_log,sizeof(post_decode_log),"%s",text?text:"");}}}
'''+engine
 engine=once(engine,'        if (llama_process(context_, LLAMA_PROCESS_TYPE_DECODE, batch_) != 0)\n            throw std::runtime_error("Model decode failed");','''        {std::lock_guard<std::mutex>lock(post_decode_log_mutex);post_decode_log[0]=0;}
        llama_log_set(post_decode_capture,nullptr);
        const auto post_status=llama_process(context_,LLAMA_PROCESS_TYPE_DECODE,batch_);
        llama_log_set(nullptr,nullptr);
        if(post_status!=0){std::lock_guard<std::mutex>lock(post_decode_log_mutex);throw std::runtime_error(std::string("Model decode failed status=")+std::to_string(post_status)+" detail="+post_decode_log);}
''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,full_raw_and_sampled_rows_share_one_unchanged_greedy_plane=True,
  complete_F32_rows_not_replaced_by_compact_tokens=True,raw_download_was_skipped_by_existing_all_sequences_sampled_rule=True,alias_row_reorder_once=True,CPU_heap_cap_not_raised=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),context=(cc,ctx)),[Path(__file__)])
 update_sources(r,jobs,sources);r['post_top2_compact_sampler_outputs']['actual_sources']['context']=sources['context'];r['post_top2_compact_sampler_outputs']['commands']['context']=jobs['context'];r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['post_top2_C4_full_logit_alias']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),full_F32_counts_raw_API_width2_checkpoint_and_finite_checks_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
