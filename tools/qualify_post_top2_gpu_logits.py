#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Require complete backend-sampled F32 rows rather than rejecting their presence."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 require(n['post_top2_GPU_greedy']['scope']['full_F32_evidence_retained'],'Existing full-evidence GPU-greedy composition required')
 command=n['routing_sharing']['commands'][2];engine=Path(command[command.index('-c')+1]).read_text()
 old='llama_get_sampled_logits_ith(context_,-1))';require(engine.count(old)==3,'Ordinary,width-two and checkpoint full-row guards required')
 engine=engine.replace(old,'(!post_gpu_greedy_enabled&&llama_get_sampled_logits_ith(context_,-1)))')
 engine=once(engine,'    stage("inference_decode_synchronization_completed");', '''    if(post_gpu_bound==this){
        const auto full_vocabulary=std::uint32_t(llama_vocab_n_tokens(vocabulary_));
        for(std::uint32_t row=0;row<count;++row)
            if(llama_get_sampled_logits_count_ith(context_,std::int32_t(row))!=full_vocabulary||!llama_get_logits_ith(context_,std::int32_t(row)))
                throw std::runtime_error("Every GPU-sampled row must retain its complete F32 vocabulary");
    }
    stage("inference_decode_synchronization_completed");''')
 r,jobs,sources=link(a.parent,a.out,dict(engine=(command,engine)),[Path(__file__)])
 for value in r.values():
  if isinstance(value,dict)and isinstance(value.get('actual_sources'),dict)and 'engine'in value['actual_sources']:
   value['actual_sources']['engine']=sources['engine']
   if isinstance(value.get('commands'),dict)and 'engine'in value['commands']:value['commands']['engine']=jobs['engine']
 r['post_top2_GPU_greedy']['full_backend_sampled_logits']=dict(all_one_or_two_rows_require_full_vocabulary_count=True,
  original_full_finite_reference_and_checkpoint_checks_retained=True,actual_source=sources['engine'],command=jobs['engine'])
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='complete_backend_sampled_F32_rows',candidate=record(a.out/'receipt.private.json'),actual_GPU_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
