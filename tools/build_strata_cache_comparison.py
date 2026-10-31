#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare3072/3424 active cache slots in the same fully priced3425-plane banks."""
import argparse,copy,json,re,shlex
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import recipes,literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from rebind_cache_provenance import rebind_cache
ROOT=Path(__file__).resolve().parents[1]
SLOTS=3424;GROWTH=(SLOTS-3072)*1536000;CACHE=4720619520+GROWTH;TRANSFER=3207049216+GROWTH;SINGLE=2<<30;REQUESTS=14
SCOPE=dict(schema='ps5-qwen-strata-cache-comparison-v1',requests=REQUESTS,model_loads=1,active_slots=[3072,3424],physical_planes=3425,
 cache_bytes=CACHE,postload_quota_bytes=(1792<<20)+TRANSFER,postload_single_buffer_bytes=SINGLE,
 order=[0,0,1,1,0],quality_requests=4,inference_padding_pages=0,OS_minimum_preserved=True,original_physical_reserves=True,
 original_model_payloads=True,complete_finite_F32=True,cross_capacity_route_and_bit_equality_required=False,automatic_retries=0)
def header(command,name):
 source=Path(command[command.index('-c')+1]);dirs=[source.parent]+[Path(command[i+1])for i,x in enumerate(command[:-1])if x=='-I']
 return next(d/name for d in dirs if(d/name).is_file())
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','control','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());control=json.loads(a.control.read_text());a.out.mkdir(parents=True,exist_ok=False)
 require((SLOTS-1381)*1536000+(24<<20)<3163852800,'Existing measured resident saving must pay for the larger banks')
 seed=copy.deepcopy(n);oldgpu=seed['lossless_shader_storage']['vulkan_object'];newgpu=control['lossless_shader_storage']['vulkan_object']
 require(seed['link_command'].count(oldgpu['path'])==1,'One actual GPU replacement required')
 seed['link_command'][seed['link_command'].index(oldgpu['path'])]=newgpu['path']
 for k in('bounded_model_source_manifest','bounded_model_source_overrides','lossless_shader_storage','shader_resource_manifest'):seed[k]=control[k]
 frozen={x['path']:x for x in seed['inputs_before']}
 for row in active_link_inputs(control):
  if row['path']in frozen:require(frozen[row['path']]==row,'Unambiguous original GPU dependency required')
  frozen[row['path']]=row
 seed['inputs_before']=list(frozen.values());seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
 ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1];cc=n['routing_sharing']['commands'][1];en=n['routing_sharing']['commands'][2]
 pc=next(c for c in recipes(n)if c[c.index('-c')+1].endswith('padding.private.cpp')and c[c.index('-o')+1]in n['link_command'])
 profile=header(ec,'resident_output_q8_profile.h');budget=header(oc,'device_buffer_budget.h');reset=header(cc,'resident_output_q8_cache_reset.h')
 generated={
 'resident_output_q8_profile.h':once(once(profile.read_text(),'cache_transfer=3207049216','cache_transfer='+str(TRANSFER)),'cache_budget=4720619520','cache_budget='+str(CACHE)),
 'device_buffer_budget.h':once(once(budget.read_text(),'+ 3207049216ull','+ '+str(TRANSFER)+'ull'),'model_postload_single_buffer = 1600ull << 20','model_postload_single_buffer = 2ull << 30'),
 'resident_output_q8_cache_reset.h':reset.read_text().replace('3072','3424').replace('1381','3072').replace('3073','3425')}
 names={}
 rows=[r for r in n['CPU_metadata_scope']['changed_sources']if r['object_path']in n['link_command']]
 commands={r['object_path']:r['command'].copy()for r in rows}
 for cmd in(ec,oc,cc,en,pc):commands[cmd[cmd.index('-o')+1]]=cmd.copy()
 for name,body in generated.items():
  dest=a.out/name;dest.write_text(body,newline='\n');targets={ROOT/'native/app'/name,ROOT.with_name(ROOT.name+'-refill')/'native/app'/name}
  for cmd in commands.values():
   dirs=[Path(cmd[cmd.index('-c')+1]).parent]+[Path(cmd[i+1])for i,x in enumerate(cmd[:-1])if x=='-I']
   targets.update(d/name for d in dirs if(d/name).is_file())
  for target in targets:names[target]=dest
 overlay=a.out/'cache-headers.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=k.resolve().as_posix(),**{'external-contents':v.resolve().as_posix()})for k,v in sorted(names.items())]))
 entry=Path(ec[ec.index('-c')+1]).read_text();changes={}
 def scope_update(old):
  v=copy.deepcopy(old)
  mapping={'active_cache_slots':SLOTS,'expected_active_Q2_slots':SLOTS,'cache_budget_bytes':CACHE,'transferred_postload_quota_bytes':TRANSFER,'postload_single_buffer_bytes':SINGLE}
  for k,value in mapping.items():
   if k in v:v[k]=value
  if v.get('maximum_requests')==16:v['maximum_requests']=REQUESTS
  return v
 for key,member in(('all_Q2_optimized_monitor','scope'),('expert_q2_model','scope'),('output_Q8_normal','probation_scope'),('resident_all_Q8','scope'),('cold_request','scope'),('limit_margin_probe','scope')):
  old=n[key][member];new=scope_update(old);needle=literal(old)
  if needle in entry:entry=entry.replace(needle,literal(new))
  changes[(key,member)]=new
 entry=once(entry,'        constexpr unsigned request_count=16;','        constexpr unsigned request_count=14;')
 entry=once(entry,'        qwen_limit_probe_stage(1);','        if(policy.at("native_strata_cache_comparison")!=Json::parse('+literal(SCOPE)+'))throw std::runtime_error("Exact cache3424 comparison scope required");\n        qwen_limit_probe_stage(1);')
 entry=once(entry,'const bool second=false;const unsigned phase=ordinal/2,task=0;constexpr unsigned order[]={0,0,1,1,0,2,2,0};const unsigned arm=order[phase],hash_arm=ordinal%2;const bool compare=ordinal>=2,keep=hash_arm!=0;',
   'const bool second=false;const unsigned phase=ordinal/2,task=ordinal<10?0:ordinal-10;constexpr unsigned order[]={0,0,1,1,0};const unsigned arm=ordinal<10?order[phase]:1,hash_arm=ordinal%2;const bool compare=ordinal>=2&&ordinal<10,keep=ordinal<10&&hash_arm!=0;')
 entry=once(entry,'const char *arm_name=arm==0?"control-original448-keys":arm==1?"current-miss676-keys":"GDN-four-columns";',
   'const char *arm_name=arm==0?"cache3072":"cache3424";')
 entry=once(entry,'qwen_app_select_weight_retention(keep);qwen_app_row_cache_select(true,!keep);qwen_app_protection_begin(true,!keep);qwen_app_io_trial_select(arm==1);qwen_app_gdn_trial_select(arm==2);',
   'qwen_app_select_weight_retention(keep);qwen_app_select_output_Q8_slots(arm?3424:3072);qwen_app_row_cache_select(true,!keep);qwen_app_protection_begin(task==0,!keep);qwen_app_io_trial_select(true);')
 entry='extern "C" void qwen_app_select_output_Q8_slots(unsigned);\n'+entry
 entry=re.sub(r'^extern "C"[^\n]*qwen_app_gdn_trial_[^\n]*\n','',entry,flags=re.M)
 entry=entry.replace('qwen_app_gdn_trial_selections()','0ull').replace('qwen_app_gdn_trial_release();','')
 entry=once(entry,'if(compare&&arm!=2&&io_max_error!=0)','if(compare&&arm==0&&io_max_error!=0)')
 entry=entry.replace('{"active_cache_slots",3072}','{"active_cache_slots",qwen_app_output_Q8_slots()}')
 entry=once(entry,'{"cache_reset_before_request",i%2==0}','{"cache_reset_before_request",i>=10||i%2==0},{"active_slots",i<10&&i/2!=2&&i/2!=3?3072:3424}')
 # Compute KL only after the native request timer has stopped. The extra row
 # copy is present in every arm, and the same33-row buffer is reused.
 entry=once(entry,'std::array<std::vector<float>,2>io_reference;',
   'std::vector<float>io_current(resident_reference_rows*columns);\n        std::array<std::vector<float>,2>io_reference;')
 entry=once(entry,'auto&ref=io_reference[hash_arm];for(std::size_t i=0;i<count;++i)',
   'std::copy_n(v,count,io_current.data()+rows*columns);auto&ref=io_reference[hash_arm];for(std::size_t i=0;i<count;++i)')
 pos='            row["phase"]=phase;'
 kl='''            if(compare){double total_kl=0;unsigned top_same=0;auto&ref=io_reference[hash_arm];
                for(std::size_t rowno=0;rowno<rows;++rowno){const auto off=rowno*columns;auto*a=ref.data()+off;auto*b=io_current.data()+off;
                    const auto ma=*std::max_element(a,a+columns),mb=*std::max_element(b,b+columns);double sa=0,sb=0;
                    for(std::size_t j=0;j<columns;++j){sa+=std::exp(double(a[j])-ma);sb+=std::exp(double(b[j])-mb);}
                    const double za=double(ma)+std::log(sa),zb=double(mb)+std::log(sb);double kl=0;
                    for(std::size_t j=0;j<columns;++j){const double lp=double(a[j])-za;kl+=std::exp(lp)*(lp-(double(b[j])-zb));}total_kl+=std::max(0.0,kl);
                    top_same+=std::max_element(a,a+columns)-a==std::max_element(b,b+columns)-b;
                }row["quality_distribution"]={{"positions",rows},{"mean_KL",total_kl/rows},{"top1_agreement",double(top_same)/rows},{"same_prefix_tokens",true},{"outside_request_timer",true}};
            }
'''
 entry=once(entry,pos,kl+pos)
 # Physical capacity and the active metadata capacity are reported separately.
 cache=Path(cc[cc.index('-c')+1]).read_text();cache=cache.replace('g.n_slots < 3072','g.n_slots < 3424')
 cache=cache.replace('groups[0].n_slots!=1381&&groups[0].n_slots!=3072','groups[0].n_slots!=3072&&groups[0].n_slots!=3424')
 cache=cache.replace('slots!=1381&&slots!=3072','slots!=3072&&slots!=3424')
 cache=once(cache,'output_Q8_selected_slots=3072','output_Q8_selected_slots=3424')
 ownercmd=control['all_Q2_optimized_monitor']['commands'][1];owner=Path(ownercmd[ownercmd.index('-c')+1]).read_text()
 ownerheader=header(ownercmd,'limit-winner-bundle.private.h');(a.out/ownerheader.name).write_bytes(ownerheader.read_bytes())
 entry_obj=ec[ec.index('-o')+1];owner_obj=oc[oc.index('-o')+1];cache_obj=cc[cc.index('-o')+1];engine_obj=en[en.index('-o')+1];padding_obj=pc[pc.index('-o')+1]
 variants={};originals={}
 for i,(obj,cmd)in enumerate(commands.items()):
  src=Path(cmd[cmd.index('-c')+1]);text=src.read_text();label='app'+str(i)
  if obj==entry_obj:label='entry';text=entry
  elif obj==owner_obj:label='owner';text=owner;cmd=ownercmd.copy();cmd[cmd.index('-o')+1]=owner_obj
  elif obj==cache_obj:label='cache';text=cache
  elif obj==engine_obj:label='engine'
  elif obj==padding_obj:label='padding';text=once(text,'1600ull<<20','2ull<<30')
  cmd+=['-ivfsoverlay',str(overlay)];variants[label]=(cmd,text);originals[label]=record(src)
 r,jobs,sources=link(seedpath,a.out,variants,[Path(__file__),a.control,overlay,ownerheader,a.out/ownerheader.name,*[a.out/k for k in generated],*[x for x in names if x.is_file()]])
 r['CPU_metadata_scope']['changed_sources']=[dict(original=originals[k],source=sources[k],object_path=jobs[k][jobs[k].index('-o')+1],command=jobs[k])for k in jobs if k not in('entry','cache','engine','padding')]
 for (key,member),v in changes.items():r[key][member]=v
 scope=r['all_Q2_optimized_monitor']['scope'];model=r['expert_q2_model']['scope']
 for key in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):r[key].update(scope=scope,model_scope=model)
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor'].update(actual_entry=sources['entry'],actual_owner=sources['owner']);r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['all_Q2_optimized_monitor']['commands'][1]=jobs['owner'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['cold_request']['device_ledger_cap_bytes']=(1792<<20)+TRANSFER
 r['resident_cache3072'].update(active_slots=SLOTS,physical_planes=SLOTS+1,cache_budget_bytes=CACHE,transferred_postload_quota_bytes=TRANSFER,postload_single_buffer_bytes=SINGLE)
 r['resident_weight_normal']['active_slots']=SLOTS;r['memory_quality_cohort'].update(requests=REQUESTS,scope=scope,model_scope=model);r['small_rows_cohort']['requests']=REQUESTS;r['speed_followup']['requests']=REQUESTS
 r['strata_cache_comparison']=dict(scope=SCOPE,header_overlay=record(overlay),headers={k:record(a.out/k)for k in generated},requests=REQUESTS,physical_slots=SLOTS,production_adopted=False)
 write_json(a.out/'unsealed-link.private.json',r)
 rebind_cache(r,a.out,jobs['cache'],sources['cache']);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='priced3424_cache_comparison',CPU_heap_limit_bytes=512<<20,workspace_bytes=48<<20,cache_slots=SLOTS,original_physical_reserves=True,OS_minimum_preserved=True,inference_padding_pages=0,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
