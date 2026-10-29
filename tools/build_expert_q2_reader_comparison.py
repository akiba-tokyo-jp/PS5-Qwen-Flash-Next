#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build two independent reader ABBA comparisons in one bounded Q2 lifetime."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from build_expert_q2_policy_comparison import POLICY_SCOPE as OLD_SCOPE,MODEL_SCOPE as OLD_MODEL,IO_SCOPE as OLD_IO
from expert_q2_reader_candidates import candidate_header
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
MODES=[0,0,1,1,0,0,2,2,0]
SCOPE=dict(schema='ps5-qwen-all-Q2-reader-two-ABBA-v1',enabled=True,maximum_requests=9,warmup_requests=1,
 order=MODES,mode_names=['original','immutable_range_hint','parallel_composite_pair'],maximum_parallel_reads=2,
 expert_eviction_policy='two_touch_probation',active_cache_slots=867,cache_budget_bytes=1333739520,
 original_GPU_math_unchanged=True,original_source_schedule_predicate_required=True,extra_scratch_bytes=0,
 extra_composite_stack_bytes=16384,automatic_retries=0)
MODEL_SCOPE=dict(OLD_MODEL,schema='ps5-qwen-all-Q2-reader-model-v1',maximum_requests=9,timed_requests=8)
IO_SCOPE=dict(OLD_IO,schema='ps5-qwen-all-Q2-reader-IO-v1',maximum_requests=9)
def literal(value):return json.dumps(json.dumps(value,separators=(',',':')))

def entry_source(text):
 text='#include <cstdint>\nextern "C" void qwen_app_select_Q2_reader(unsigned);\nextern "C" void qwen_app_Q2_reader_stats(std::uint64_t*);\n'+text
 for before,after in ((OLD_SCOPE,SCOPE),(OLD_MODEL,MODEL_SCOPE),(OLD_IO,IO_SCOPE)):text=once(text,literal(before),literal(after))
 text=once(text,'policy.at("native_Expert_Q2_policy_comparison")','policy.at("native_Expert_Q2_reader_comparison")')
 text=once(text,'        const unsigned request_count=5;','        const unsigned request_count=9;')
 text=once(text,'            const bool probation=ordinal==2||ordinal==3;',
  '            const unsigned reader_mode=(ordinal==2||ordinal==3)?1:((ordinal==6||ordinal==7)?2:0);')
 text=once(text,'                qwen_app_select_Q2_probation(probation);',
  '                qwen_app_select_Q2_probation(true);\n                qwen_app_select_Q2_reader(reader_mode);')
 text=once(text,'(probation?"two-touch-probation":"aged-lfu-control")',
  '(reader_mode==1?"range-hint":(reader_mode==2?"composite-parallel":"reader-control"))')
 text=once(text,'{"expert_eviction_policy",probation?"two_touch_probation":"aged_lfu"}',
  '{"expert_eviction_policy","two_touch_probation"},{"reader_candidate_mode",reader_mode}')
 text=once(text,'    if (source.schedule_enabled) result.update({','''    std::uint64_t reader_counts[3]{};qwen_app_Q2_reader_stats(reader_counts);
    result["range_hint_hits"]=reader_counts[0];result["range_lookups"]=reader_counts[1];
    result["composite_parallel_pairs"]=reader_counts[2];
    if (source.schedule_enabled) result.update({''')
 return once(text,'{"completed_policy_comparison",true}','{"completed_reader_comparisons",true}')

def owner_source(text):
 return text+'''
extern "C" void qwen_app_select_Q2_reader(unsigned mode){
    required().require_completed_window();ops.require_metadata_idle();
    if(mode>2)throw std::runtime_error("Unknown finite reader comparison mode");
    qwen_app::Q2_reader_candidate_mode.store(mode,std::memory_order_relaxed);
}
extern "C" void qwen_app_Q2_reader_stats(std::uint64_t*out){
    if(!out)throw std::runtime_error("Missing reader snapshot destination");
    const auto values=required().candidate_stats();for(unsigned i=0;i<3;++i)out[i]=values[i];
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out','host-proof'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());proof=json.loads(a.host_proof.read_text())
 require(prior['all_Q2_policy_comparison']['scope']==OLD_SCOPE and proof['completed'],'Qualified exact parent and reader host controls required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'tools/expert_q2_reader_candidates.py'),record(a.host_proof)]
 for row in frozen:require(record(row['path'])==row,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();snapshot=a.out/'generator.private.py';snapshot.write_bytes(Path(__file__).read_bytes())
 old_header=prior['expert_q2_model']['reader_header'];require(record(old_header['path'])==old_header,'Exact compiled reader header required')
 header=a.out/'resident-mapped-source.private.h';header.write_text(candidate_header(Path(old_header['path']).read_text()),newline='\n')
 require(record(header)['sha256']==proof['candidate_header']['sha256'],'Host-checked and native reader bytes differ')
 variants=[('entry',prior['compile_commands'][0],prior['expert_q2_model']['actual_entry'],entry_source),
  ('owner',prior['all_Q2_IO_measurement']['commands'][1],prior['all_Q2_IO_measurement']['owner'],owner_source)]
 commands=[];replacements={};added=[record(snapshot),old_header,record(header)]
 for label,original_command,original_record,derive in variants:
  original=Path(original_record['path']);require(record(original)==original_record,'Actual compiled source changed')
  source=a.out/(label+'.private.cpp');source.write_text(derive(original.read_text()),newline='\n');obj=a.out/(label+'.o');command=original_command.copy();old_obj=command[command.index('-o')+1]
  command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
  if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
  require(prior['link_command'].count(old_obj)==1,'One actual selected object required');replacements[old_obj]=str(obj);commands.append(command);added.extend((record(original),record(source)))
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,command in enumerate(commands+[link]):
  r=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:]);print(json.dumps(dict(reader_comparison_build_step=i+1,total=3)),flush=True)
 for row in frozen:require(record(row['path'])==row,'Frozen source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[commands[0]],source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/'entry.o'),record(a.out/'owner.o')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model']['actual_entry']=record(a.out/'entry.private.cpp');receipt['expert_q2_model']['commands']=[commands[0],prior['expert_q2_model']['commands'][1]]
 receipt['all_Q2_IO_measurement'].update(entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),commands=commands)
 receipt['all_Q2_reader_comparisons']=dict(scope=SCOPE,model_scope=MODEL_SCOPE,IO_scope=IO_SCOPE,commands=commands,actual_header=record(header),original_header=old_header,GPU_objects_and_cache_unchanged=True,host_control=record(a.host_proof),production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(reader_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()
