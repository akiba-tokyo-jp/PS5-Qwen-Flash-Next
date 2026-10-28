#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe kernel page categories during completed load boundaries, no GPU work."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior=json.loads(a.parent.read_text())
 for row in prior['inputs_before']+[prior['artifact']]:
  if record(row['path'])!=row:raise ValueError('Qualified observation input changed: '+row['path'])
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
 matches=[c.copy()for c in prior['compile_commands']if '-c'in c and 'resident-comparison'in Path(c[c.index('-c')+1]).name];assert len(matches)==1
 recipe=matches[0];original=Path(recipe[recipe.index('-c')+1]);text=original.read_text();main_at=text.index('int main(int argc, char ** argv)')
 helper='''static std::atomic_flag load_VM_lock=ATOMIC_FLAG_INIT;
static qwen_kernel_memory_sample load_VM_samples[20]{};
static std::uint64_t load_VM_copy_bytes[20]{},load_VM_bucket=UINT64_MAX;
static bool load_VM_valid[20]{};static unsigned load_VM_count=0;
static int load_VM_scalar(void *,const char *name,std::uint32_t *value){
    struct {std::uint64_t a;std::uint32_t value;std::uint64_t b;} s{0x659dc9a37164a7d1ull,0,0x659dc9a37164a7d1ull};
    std::size_t bytes=4;if(sysctlbyname(name,&s.value,&bytes,nullptr,0)||bytes!=4||s.a!=0x659dc9a37164a7d1ull||s.b!=s.a)return 0;
    *value=s.value;return 1;
}
static bool observe_load_VM(float progress,void *opaque){
    if(!load_VM_lock.test_and_set()){
        std::uint64_t copied=0;qwen_app_resident_GPU_load_copy_counters(nullptr,&copied);const auto bucket=copied/(512ull<<20);
        if(load_VM_count<20&&bucket!=load_VM_bucket){const auto index=load_VM_count++;
            const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count();
            load_VM_valid[index]=qwen_kernel_memory_observe(nullptr,load_VM_scalar,ns,index,&load_VM_samples[index]);
            load_VM_copy_bytes[index]=copied;load_VM_bucket=bucket;}
        load_VM_lock.clear();
    }
    return observe_model_load(progress,opaque);
}
static Json report_load_VM(){
    if(load_VM_lock.test_and_set())return {{"snapshot_completed",false},{"concurrent_callback",true}};
    Json rows=Json::array();for(unsigned i=0;i<load_VM_count;++i){const auto &s=load_VM_samples[i];
        rows.push_back({{"ordinal",i},{"valid",load_VM_valid[i]},{"completed_GPU_copy_bytes",load_VM_copy_bytes[i]},
            {"ns",s.monotonic_ns},{"free_first",s.free_first},{"free_last",s.free_last},{"active",s.active},
            {"inactive",s.inactive},{"wired",s.wired},{"cache",s.cache},{"total",s.total},
            {"minimum",s.minimum},{"reserved",s.reserved},{"target",s.target}});}
    load_VM_lock.clear();return {{"snapshot_completed",true},{"maximum_samples",20},{"GPU_calls_added",0},
        {"kernel_policy_changes",0},{"global_samples_not_exclusive_attribution",true},{"samples",rows}};
}
'''
 text='#include "kernel_memory_trace.h"\n'+text[:main_at]+helper+text[main_at:]
 old='model_params.progress_callback=observe_model_load;';assert text.count(old)==1;text=text.replace(old,'model_params.progress_callback=observe_load_VM;')
 old='{"last_model_load_error",qwen_app::resident_last_model_error()},';assert text.count(old)==1;text=text.replace(old,old+'{"loader_VM",report_load_VM()},')
 old='        qwen_native_stage("model_load_completed");';assert text.count(old)==1;text=text.replace(old,old+'\n        write_fresh_report(startup.admission_report+".resident.loader-VM",report_load_VM());')
 generated=a.out/'resident-comparison-VM-observation.private.cpp';generated.write_text(text,newline='\n')
 obj=a.out/'resident-comparison-VM-observation.o';old=recipe[recipe.index('-o')+1];recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(original.parent)]
 link=prior['link_command'].copy();assert link.count(old)==1;link=[str(obj)if x==old else x for x in link];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+[record(x)for x in (Path(__file__),a.parent,original,generated,ROOT/'native/app/kernel_memory_trace.h')]
 for index,command in enumerate((recipe,link)):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen observation source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[recipe],source_parent=record(a.parent),
  inputs_before=frozen+[record(obj)],resident_load_VM_observation=dict(maximum_samples=20,source=record(generated),GPU_calls_added=0,kernel_policy_changes=0),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(load_VM_categories_observed=True,GPU_calls_added=0,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
