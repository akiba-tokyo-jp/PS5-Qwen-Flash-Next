#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One model lifetime, three independent equal-condition Q2 delivery ABBAs."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_expert_q2_adjacent_comparison import SCOPE as OLD_SCOPE,MODEL_SCOPE as OLD_MODEL,IO_SCOPE as OLD_IO
from expert_q2_io_reduction import header_source,owner_source,cache_source
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
MODES=[0,0,1,1,0,0,2,2,0,0,3,3,0]
MODEL_SCOPE=dict(OLD_MODEL,schema='ps5-qwen-Q2-IO-reduction-model-v1',maximum_requests=13,timed_requests=12)
IO_SCOPE=dict(OLD_IO,schema='ps5-qwen-Q2-IO-reduction-observers-v1',maximum_requests=13,
    two_lane_occupancy_valid_only_outside_quad_mode=True,quad_maximum_from_positive_pool_completion=True)
SCOPE=dict(OLD_SCOPE,schema='ps5-qwen-Q2-IO-reduction-three-ABBA-v1',maximum_requests=13,order=MODES,
    mode_names=['adjacent_control','additional_84_Expert_pack','temporal_probation_144','four_demand_reads'],
    extra_bundles=84,maximum_extra_file_bytes=129368064,additional_readonly_source_handles=2,
    additional_worker_threads=3,maximum_parallel_source_reads=4,original_source_schedule_predicate_required=True,
    current_top10_pinned=True,all_original_memory_caps_retained=True)
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def entry_source(text):
 text='''#include <cstdint>
extern "C" void qwen_app_select_Q2_IO_reduction(unsigned);
extern "C" void qwen_app_select_Q2_temporal(unsigned);
extern "C" void qwen_app_Q2_quad_stats(std::uint64_t*);
'''+text
 for a,b in ((OLD_SCOPE,SCOPE),(OLD_MODEL,MODEL_SCOPE),(OLD_IO,IO_SCOPE)):text=once(text,literal(a),literal(b))
 text=once(text,'        const unsigned request_count=5;','        const unsigned request_count=13;')
 text=once(text,'std::array<CompletedRouteEvidence,9> routes;','std::array<CompletedRouteEvidence,13> routes;')
 text=once(text,'            const bool probation=ordinal==2||ordinal==3;',
  '            constexpr unsigned modes[]={'+','.join(map(str,MODES))+'};\n            const auto mode=modes[ordinal];const bool probation=mode!=0;')
 text=once(text,'(probation?"adjacent-bundle-groups":"single-Expert-bundles")',
  '(mode==1?"extra-84-Expert-bundles":mode==2?"temporal-probation-144":mode==3?"four-demand-reads":"adjacent-control")')
 text=once(text,'qwen_app_select_Q2_adjacent(probation);','qwen_app_select_Q2_adjacent(true);qwen_app_select_Q2_IO_reduction(mode);qwen_app_select_Q2_temporal(mode==2?144:0);')
 text=once(text,'    result["adjacent_bundle_calls_saved"]=qwen_app_Q2_merged_calls_saved();','''    result["adjacent_bundle_calls_saved"]=qwen_app_Q2_merged_calls_saved();
    std::uint64_t quad[2]{};qwen_app_Q2_quad_stats(quad);result["quad_batches"]=quad[0];result["quad_peak"]=quad[1];''')
 text=once(text,'{"bundle_candidate",probation}',
  '{"bundle_candidate",probation},{"IO_reduction_mode",mode},{"two_lane_occupancy_valid",mode!=3},{"temporal_window",mode==2?144:0}')
 return text
def extra_plan(pack):
 selection=json.loads(Path(pack['selection']['path']).read_text());require(record(pack['selection']['path'])==pack['selection']and len(selection['Experts'])==84,'Exact additional keys required')
 o=pack['output'];return '#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr const char*Q2_extra_path='+json.dumps('/app0/'+Path(o['path']).name)+';\ninline constexpr const char*Q2_extra_SHA256='+json.dumps(o['sha256'])+';\ninline constexpr std::array<std::uint64_t,10>Q2_extra_expected_identity={'+','.join(str(x)+'ULL'for x in o['identity'])+'};\ninline constexpr std::array<unsigned,2>Q2_extra_keys[]={'+','.join('{'+str(x['layer'])+','+str(x['expert'])+'}'for x in selection['Experts'])+'};\n'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out','extra-pack'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());pack=json.loads(a.extra_pack.read_text());require(prior['all_Q2_bundle_comparison']['scope']==OLD_SCOPE and pack['completed']and pack['CPU_Direct_positively_retired'],'Exact closed parents required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
 frozen +=[record(x)for x in (a.parent,a.extra_pack,Path(__file__),ROOT/'tools/expert_q2_io_reduction.py',ROOT/'native/app/bounded_read_pool.h',ROOT/'native/app/expert_temporal_probation.h')]
 for r in frozen:require(record(r['path'])==r,'Current input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();old_header=prior['all_Q2_bundle_comparison']['actual_header'];header=a.out/'resident-mapped-source.private.h';header.write_text(header_source(Path(old_header['path']).read_text()),newline='\n')
 plan=a.out/'Q2-bundle-plan.private.h';plan.write_bytes((Path(old_header['path']).parent/plan.name).read_bytes());extra=a.out/'Q2-extra-bundle-plan.private.h';extra.write_text(extra_plan(pack),newline='\n')
 jobs=[];replacements={};added=[record(header),record(plan),record(extra)]
 variants=[('entry',prior['compile_commands'][0],prior['expert_q2_model']['actual_entry'],entry_source),('owner',prior['all_Q2_IO_measurement']['commands'][1],prior['all_Q2_IO_measurement']['owner'],owner_source),('cache',prior['expert_q2_model']['commands'][1],prior['expert_q2_model']['actual_cache'],cache_source)]
 for label,base,original,derive in variants:
  require(record(original['path'])==original,'Actual compiled source changed');source=a.out/(label+'.private.cpp');source.write_text(derive(Path(original['path']).read_text()),newline='\n');obj=a.out/(label+'.o');cmd=base.copy();old=cmd[cmd.index('-o')+1];cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(Path(original['path']).parent)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  require(prior['link_command'].count(old)==1,'One actual selected object required');replacements[old]=str(obj);jobs.append(cmd);added +=[record(source),original]
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate(jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3500:]);print(json.dumps(dict(build_step=i+1,total=4)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen build input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[jobs[0]],source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/(x+'.o'))for x in ('entry','owner','cache')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(a.out/'entry.private.cpp'),actual_cache=record(a.out/'cache.private.cpp'),reader_header=record(header),commands=[jobs[0],jobs[2]])
 receipt['all_Q2_IO_measurement'].update(scope=IO_SCOPE,entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),commands=jobs)
 receipt['all_Q2_bundle_comparison'].update(scope=SCOPE,actual_header=record(header),commands=jobs)
 receipt['all_Q2_IO_reduction']=dict(scope=SCOPE,actual_reader=record(header),actual_owner=record(a.out/'owner.private.cpp'),extra_pack=record(a.extra_pack),cache_header=record(ROOT/'native/app/expert_temporal_probation.h'),mode_order=MODES,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Import/dispatch audit failed');write_json(target,receipt)
 print('Three Q2 I/O comparisons linked with original GPU providers and memory caps.',flush=True)
if __name__=='__main__':main()
