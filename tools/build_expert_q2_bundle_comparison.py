#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build two independent reader ABBA comparisons in one bounded Q2 lifetime."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from build_expert_q2_policy_comparison import POLICY_SCOPE as OLD_SCOPE,MODEL_SCOPE as OLD_MODEL,IO_SCOPE as OLD_IO
from expert_q2_bundle_reader import reader_header as candidate_header,owner_source,cache_source
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-all-Q2-partial-bundle-ABBA-v1',enabled=True,maximum_requests=5,warmup_requests=1,
 order=[False,False,True,True,False],bundled_Experts=336,maximum_bundle_file_bytes=512<<20,
 expert_eviction_policy='two_touch_probation',active_cache_slots=867,cache_budget_bytes=1333739520,
 original_GPU_math_unchanged=True,original_fallback_required=True,additional_scratch_bytes=0,
 additional_readonly_source_handles=1,complete_bundle_SHA256_before_GPU=True,automatic_retries=0)
MODEL_SCOPE=dict(OLD_MODEL,schema='ps5-qwen-all-Q2-bundle-model-v1')
IO_SCOPE=dict(OLD_IO,schema='ps5-qwen-all-Q2-bundle-IO-v1')
def literal(value):return json.dumps(json.dumps(value,separators=(',',':')))
def entry_source(text):
 text='#include <cstdint>\nextern "C" void qwen_app_select_Q2_bundle(bool);\nextern "C" std::uint64_t qwen_app_Q2_bundle_hits();\n'+text
 for before,after in ((OLD_SCOPE,SCOPE),(OLD_MODEL,MODEL_SCOPE),(OLD_IO,IO_SCOPE)):text=once(text,literal(before),literal(after))
 text=once(text,'policy.at("native_Expert_Q2_policy_comparison")','policy.at("native_Expert_Q2_bundle_comparison")')
 text=once(text,'                qwen_app_select_Q2_probation(probation);','                qwen_app_select_Q2_probation(true);\n                qwen_app_select_Q2_bundle(probation);')
 text=once(text,'(probation?"two-touch-probation":"aged-lfu-control")','(probation?"partial-Expert-bundles":"original-Expert-reads")')
 text=once(text,'{"expert_eviction_policy",probation?"two_touch_probation":"aged_lfu"}','{"expert_eviction_policy","two_touch_probation"},{"bundle_candidate",probation}')
 text=once(text,'    if (source.schedule_enabled) result.update({','    result["bundle_Experts"]=qwen_app_Q2_bundle_hits();\n    if (source.schedule_enabled) result.update({')
 return once(text,'{"completed_policy_comparison",true}','{"completed_bundle_comparison",true}')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out','host-proof','pack'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());proof=json.loads(a.host_proof.read_text());pack=json.loads(a.pack.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired']and pack['original_sources_preserved'],'Completed immutable native bundle pack required')
 require(prior['all_Q2_policy_comparison']['scope']==OLD_SCOPE and proof['completed'],'Qualified exact parent and reader host controls required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'tools/expert_q2_bundle_reader.py'),record(a.pack),record(a.host_proof)]
 for row in frozen:require(record(row['path'])==row,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();snapshot=a.out/'generator.private.py';snapshot.write_bytes(Path(__file__).read_bytes())
 old_header=prior['expert_q2_model']['reader_header'];require(record(old_header['path'])==old_header,'Exact compiled reader header required')
 header=a.out/'resident-mapped-source.private.h';header.write_text(candidate_header(Path(old_header['path']).read_text()),newline='\n')
 require(record(header)['sha256']==proof['candidate_header']['sha256'],'Host-checked and native reader bytes differ')
 selection=json.loads(Path(pack['selection']['path']).read_text());require(record(pack['selection']['path'])==pack['selection']and len(selection['Experts'])==336,'Exact bounded bundle keys required')
 plan=a.out/'Q2-bundle-plan.private.h';o=pack['output'];native_path='/app0/'+Path(o['path']).name
 plan.write_text('#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr const char*Q2_bundle_path='+json.dumps(native_path)+';\ninline constexpr const char*Q2_bundle_SHA256='+json.dumps(o['sha256'])+';\ninline constexpr std::array<std::uint64_t,10> Q2_bundle_expected_identity={'+','.join(str(x)+'ULL'for x in o['identity'])+'};\ninline constexpr std::array<unsigned,2>Q2_bundle_keys[]={'+','.join('{'+str(x['layer'])+','+str(x['expert'])+'}'for x in selection['Experts'])+'};\n',newline='\n')
 variants=[('entry',prior['compile_commands'][0],prior['expert_q2_model']['actual_entry'],entry_source),
  ('owner',prior['all_Q2_IO_measurement']['commands'][1],prior['all_Q2_IO_measurement']['owner'],owner_source),
  ('cache',prior['expert_q2_model']['commands'][1],prior['expert_q2_model']['actual_cache'],cache_source)]
 commands=[];replacements={};added=[record(snapshot),old_header,record(header),record(plan)]
 for label,original_command,original_record,derive in variants:
  original=Path(original_record['path']);require(record(original)==original_record,'Actual compiled source changed')
  source=a.out/(label+'.private.cpp');source.write_text(derive(original.read_text()),newline='\n');obj=a.out/(label+'.o');command=original_command.copy();old_obj=command[command.index('-o')+1]
  command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
  if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
  require(prior['link_command'].count(old_obj)==1,'One actual selected object required');replacements[old_obj]=str(obj);commands.append(command);added.extend((record(original),record(source)))
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,command in enumerate(commands+[link]):
  r=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:]);print(json.dumps(dict(bundle_comparison_build_step=i+1,total=4)),flush=True)
 for row in frozen:require(record(row['path'])==row,'Frozen source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[commands[0]],source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/'entry.o'),record(a.out/'owner.o'),record(a.out/'cache.o')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(a.out/'entry.private.cpp'),actual_cache=record(a.out/'cache.private.cpp'),commands=[commands[0],commands[2]])
 receipt['all_Q2_IO_measurement'].update(scope=IO_SCOPE,entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),commands=commands)
 receipt['all_Q2_bundle_comparison']=dict(scope=SCOPE,model_scope=MODEL_SCOPE,IO_scope=IO_SCOPE,commands=commands,actual_header=record(header),original_header=old_header,GPU_math_and_bank_capacity_unchanged=True,pack=record(a.pack),host_control=record(a.host_proof),production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(bundle_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()
