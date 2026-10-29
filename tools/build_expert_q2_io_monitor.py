#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose only positively compared I/O winners with the selected normal app."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_expert_q2_optimized_monitor import SCOPE as OLD_SCOPE,MODEL_SCOPE
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def monitor_scope(flags):
 require(type(flags)is int and 0<=flags<=7,'Qualified three-bit selection required')
 return dict(OLD_SCOPE,schema='ps5-qwen-Q2-IO-reduction-monitor-v1',adjacent_bundle_groups=True,
     extra_bundles=84 if flags&1 else 0,temporal_protection_window=144 if flags&2 else 0,
     maximum_parallel_source_reads=4 if flags&4 else 2,additional_source_workers=3 if flags&4 else 0,
     qualified_winner_flags=flags,diagnostic_occupancy_disabled=True)
def normal_owner(text,flags):
 text=once(text,'        if(!Q2_quad_mode)source_occupancy.begin();','')
 text=once(text,'        if(!Q2_quad_mode)source_occupancy.end();source_latency.completed(got,ns);return got;',
  '        source_latency.completed(got,ns);return got;')
 if not flags&1:
  text=once(text,'admit_Q2_bundle(window);admit_Q2_extra(window);','admit_Q2_bundle(window);')
  text=once(text,'    if(!Q2_extra_verified||Q2_extra_fd<0||!ops.close_file(Q2_extra_fd))throw std::runtime_error("Extra bundle did not positively close");Q2_extra_fd=-1;Q2_extra_verified=Q2_extra_mode=false;','')
 if not flags&4:
  text=once(text,'        quad_=std::make_unique<qwen_app::BoundedReadPool>([this](const qwen_app::BoundedReadRequest&r){return read_at(r.fd,r.target,r.bytes,r.offset);});quad_->start();','')
  text=once(text,'        if(!quad_)throw std::runtime_error("Four-demand worker owner is absent");quad_->stop_completed();quad_.reset();','')
 return text+'''
extern "C" void qwen_app_select_Q2_normal_IO(unsigned flags){
    required().require_completed_window();ops.require_metadata_idle();
    if(flags!='''+str(flags)+'''||!Q2_bundle_verified||((flags&1)&&!Q2_extra_verified))throw std::runtime_error("Only the qualified normal I/O selection is admitted");
    Q2_adjacent_merge=true;Q2_extra_mode=flags&1;Q2_quad_mode=flags&4;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','comparison','selection','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());comparison=json.loads(a.comparison.read_text());selection=json.loads(a.selection.read_text());flags=selection['selected_flags']
 require(prior['all_Q2_optimized_monitor']['scope']==OLD_SCOPE and selection['completed']and selection['all_three_native_ABBA_completed']and selection['full_F32_and_ordered_routes_exact'],'Complete normal parent and same-model selection required')
 scope=monitor_scope(flags);frozen=active_link_inputs(prior)+active_link_inputs(comparison)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(x)for x in (a.parent,a.comparison,a.selection,Path(__file__))]
 for r in frozen:require(record(r['path'])==r,'Exact composed input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();entry=a.out/'entry.private.cpp';oldentry=prior['all_Q2_optimized_monitor']['actual_entry'];text=Path(oldentry['path']).read_text()
 text='#include <cstdint>\nextern "C" void qwen_app_select_Q2_normal_IO(unsigned);\nextern "C" void qwen_app_select_Q2_temporal(unsigned);\n'+text
 text=once(text,literal(OLD_SCOPE),literal(scope))
 text=once(text,'{"maximum_parallel_source_reads", selected ? 2 : 1}',
  '{"maximum_parallel_source_reads", selected ? '+str(4 if flags&4 else 2)+' : 1}')
 text=once(text,'qwen_app_select_Q2_reader(1);qwen_app_select_Q2_bundle(true);',
  'qwen_app_select_Q2_reader(1);qwen_app_select_Q2_bundle(true);qwen_app_select_Q2_normal_IO('+str(flags)+');')
 text=once(text,'qwen_app_select_Q2_probation(true);','qwen_app_select_Q2_probation(true);qwen_app_select_Q2_temporal('+str(144 if flags&2 else 0)+');')
 entry.write_text(text,newline='\n');oldowner=comparison['all_Q2_IO_measurement']['owner'];owner=a.out/'owner.private.cpp';owner.write_text(normal_owner(Path(oldowner['path']).read_text(),flags),newline='\n')
 reader=a.out/'resident-mapped-source.private.h';reader.write_bytes(Path(comparison['all_Q2_IO_reduction']['actual_reader']['path']).read_bytes())
 for name in ('Q2-bundle-plan.private.h','Q2-extra-bundle-plan.private.h'):(a.out/name).write_bytes((Path(oldowner['path']).parent/name).read_bytes())
 jobs=[];replacements={}
 for label,source,base,original in [('entry',entry,prior['compile_commands'][0],oldentry),('owner',owner,comparison['all_Q2_IO_measurement']['commands'][1],oldowner)]:
  cmd=base.copy();old=cmd[cmd.index('-o')+1];obj=a.out/(label+'.o');cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(Path(original['path']).parent)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  if label=='owner':old=prior['all_Q2_optimized_monitor']['commands'][1];old=old[old.index('-o')+1]
  require(prior['link_command'].count(old)==1,'One selected composed object required');replacements[old]=str(obj);jobs.append(cmd)
 oldcache=prior['expert_q2_model']['commands'][1];oldcache=oldcache[oldcache.index('-o')+1];cachecmd=comparison['expert_q2_model']['commands'][1];newcache=cachecmd[cachecmd.index('-o')+1];require(prior['link_command'].count(oldcache)==1,'Exact cache override required');replacements[oldcache]=newcache
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate(jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3500:]);print(json.dumps(dict(normal_IO_build_step=i+1,total=3)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen composed input changed')
 frozen +=[record(x)for x in (entry,owner,reader,a.out/'Q2-bundle-plan.private.h',a.out/'Q2-extra-bundle-plan.private.h',a.out/'entry.o',a.out/'owner.o')]
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[jobs[0]],source_parent=record(a.parent),inputs_before=list({r['path']:r for r in frozen}.values()),lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(actual_entry=record(entry),actual_cache=comparison['expert_q2_model']['actual_cache'],reader_header=record(reader),commands=[jobs[0],cachecmd])
 receipt['all_Q2_optimized_monitor'].update(scope=scope,commands=jobs+[prior['all_Q2_optimized_monitor']['commands'][2]],actual_entry=record(entry),actual_owner=record(owner),actual_reader=record(reader),production_adopted=False)
 receipt['all_Q2_IO_normal']=dict(scope=scope,flags=flags,selection=record(a.selection),extra_pack=comparison['all_Q2_IO_reduction']['extra_pack'],diagnostic_occupancy_disabled=True,normal_validation_pending=True)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Import/dispatch audit failed');write_json(target,receipt)
 print('Qualified winners composed with the exact normal prefix/final-consumer engine.',flush=True)
if __name__=='__main__':main()
