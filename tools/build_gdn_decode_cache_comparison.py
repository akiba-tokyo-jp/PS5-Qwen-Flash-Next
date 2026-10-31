#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare GDN on the original3072 cache after a larger loading-scope refusal."""
import argparse,copy,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from build_strata_cache_comparison import header
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from rebind_cache_provenance import rebind_cache
from strata_winner_providers import merge
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('normal','checkpoint','providers','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();normal=json.loads(a.normal.read_text());cp=json.loads(a.checkpoint.read_text());n=json.loads(a.providers.read_text());a.out.mkdir(parents=True,exist_ok=False)
 seed=merge(normal,cp,n,True);seed['limit_margin_probe']=copy.deepcopy(n['limit_margin_probe']);seed['inputs_before'] +=[record(a.normal),record(a.checkpoint),record(a.providers)];seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();changes={}
 values=dict(active_cache_slots=3072,expected_active_Q2_slots=3072,cache_budget_bytes=4720619520,transferred_postload_quota_bytes=3207049216,postload_single_buffer_bytes=1677721600)
 for key,member in(('all_Q2_optimized_monitor','scope'),('expert_q2_model','scope'),('output_Q8_normal','probation_scope'),('resident_all_Q8','scope'),('cold_request','scope'),('limit_margin_probe','scope')):
  old=n[key][member];new=copy.deepcopy(old)
  for k,v in values.items():
   if k in new:new[k]=v
  if literal(old)in entry:entry=entry.replace(literal(old),literal(new))
  changes[(key,member)]=new
 old=n['GDN_model_comparison']['scope'];scope=dict(old,active_cache_slots=3072,physical_cache_planes=3073,original_3072_geometry_to_reduce_application_owned_consumption=True)
 entry=once(entry,literal(old),literal(scope))
 entry=entry.replace('qwen_app_select_output_Q8_slots(3424)','qwen_app_select_output_Q8_slots(3072)').replace('{"active_slots",3424}','{"active_slots",3072}')
 require('qwen_app_select_output_Q8_slots(3424)'not in entry,'No larger cache selection may survive')
 names={};nc=normal['compile_commands'][0];dirs=[]
 for cmd in(ec,nc):dirs+=[Path(cmd[cmd.index('-c')+1]).parent]+[Path(cmd[i+1])for i,x in enumerate(cmd[:-1])if x=='-I']
 for name in('resident_output_q8_profile.h','device_buffer_budget.h','resident_output_q8_cache_reset.h'):
  donor=header(nc,name);dest=a.out/name;dest.write_bytes(donor.read_bytes())
  targets={ROOT/'native/app'/name,ROOT.with_name(ROOT.name+'-refill')/'native/app'/name,*[d/name for d in dirs if(d/name).is_file()]}
  for target in targets:names[target]=dest
 overlay=a.out/'decode-headers.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=k.resolve().as_posix(),**{'external-contents':v.resolve().as_posix()})for k,v in sorted(names.items())]))
 # Replace the normal seed's entry with the existing exact14-request harness.
 command=ec.copy();current=normal['compile_commands'][0];command[command.index('-o')+1]=current[current.index('-o')+1];command+=['-ivfsoverlay',str(overlay)]
 entry='#include "device_buffer_budget.h"\nstatic_assert(qwen_app::model_postload_device_budget==5086097408ull,"Original3072 quota required");\n'+entry
 r,jobs,sources=link(seedpath,a.out,dict(entry=(command,entry)),[Path(__file__),ROOT/'tools/strata_winner_providers.py',overlay,*set(names.values())])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for(key,member),v in changes.items():r[key][member]=v
 scope_model=r['expert_q2_model']['scope'];scope_normal=r['all_Q2_optimized_monitor']['scope']
 for key in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):r[key].update(scope=scope_normal,model_scope=scope_model)
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['GDN_model_comparison']=copy.deepcopy(n['GDN_model_comparison']);r['GDN_model_comparison'].update(scope=scope);r['GDN_model_comparison']['actual_sources']['entry']=sources['entry'];r['GDN_model_comparison']['commands']['entry']=jobs['entry']
 r['checkpoint_model_comparison']=cp['checkpoint_model_comparison'];r['checkpoint_model_comparison']['active_for_this_test']=False
 r['memory_quality_cohort']=dict(n['memory_quality_cohort'],requests=14,scope=scope_normal,model_scope=scope_model);r['small_rows_cohort']=dict(n['small_rows_cohort'],requests=14);r['speed_followup']=dict(n['speed_followup'],requests=14)
 r['GDN_decode_cache_comparison']=dict(active_slots=3072,physical_planes=3073,application_cache_reduction_bytes=540672000,headers=[record(v)for v in set(names.values())],overlay=record(overlay),OS_threshold_not_relaxed=True)
 rebind_cache(r,a.out/'cache-provenance',r['routing_sharing']['commands'][1],r['routing_sharing']['actual_sources']['cache']);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='original3072_GDN_model_comparison',requests=14,cache_slots=3072,
  original_driver_model_OS_physical_workspace_and_positive_completion=True,application_cache_reduction_bytes=540672000,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
