#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare F16 recurrent S storage with original F32 compute and Attention KV."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from build_next_five_comparison import command_for,update_sources,ROOT
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);(a.out/'memory-tmp').mkdir()
 up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';original=up/'src/llama-memory-recurrent.cpp';source=a.out/'recurrent.private.cpp'
 body='#include "next_five_policy.h"\n'+original.read_text();body=once(body,'    this->n_rs_seq = n_rs_seq;','    this->n_rs_seq = n_rs_seq;\n    if(qwen_next_variant()==6){if(type_s!=GGML_TYPE_F32)throw std::runtime_error("Original recurrent S type required");type_s=GGML_TYPE_F16;}')
 source.write_text(body,newline='\n');obj=a.out/'recurrent.o';cmd=command_for(n,'graph.private.cpp').copy();cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
 cmd+=['-I',str(up/'src'),'-I',str(ROOT/'native/app')]
 if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'recurrent.private.d')
 run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'memory-tmp'),TEMP=str(a.out/'memory-tmp')));(a.out/'memory-build.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2500:])
 seed=copy.deepcopy(n);archive=next(x for x in seed['link_command']if Path(x).name=='libllama.a');seed['link_command'].insert(seed['link_command'].index(archive),str(obj));seed['inputs_before']+=[record(source),record(obj),record(original),record(__file__)]
 seedpath=a.out/'seed.private.json';write_json(seedpath,seed);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='recurrent-S-F16',candidate_id=6,recurrent_S_storage_bits=[32,16],Attention_KV_bits=32,convolution_and_PLE_state_bits=32,recurrent_arithmetic_bits=32)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?1:0);','qwen_next_select(arm?6:0);');entry=once(entry,'arm==0?"installed-control":"routing4";','arm==0?"S-F32":"S-F16";')
 entry=once(entry,'                resident_reset_empty_context(context,model,startup.admission_report);','                llama_free(context);context=nullptr;resident_reused_context=nullptr;\n                context=llama_init_from_model(model,qwen_app::streaming_context_params(256,memory_budget.expert_cache,32));\n                if(!context)throw std::runtime_error("Changed recurrent context allocation failed");\n                resident_reset_empty_context(context,model,startup.admission_report);')
 entry=once(entry,'{"KV_bits",32}','{"KV_bits",32},{"recurrent_S_bits",arm?16:32}')
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry)),[Path(__file__),source,obj,original,ROOT/'native/app/next_five_policy.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['next_five_recurrent_override']=dict(original=record(original),source=record(source),object=record(obj),command=cmd,archive_object_shadowed='llama-memory-recurrent.cpp.o',all_other_memory_implementations_unchanged=True)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='recurrent_S_F16_storage',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
