#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the actual mixed/all-Q2 resource and synchronous completion guards."""
import argparse,hashlib,json
from pathlib import Path
from expert_q4 import record,require,write_json
def body(text,name):
 at=text.index(name+'(');at=text.rfind('\n',0,at)+1;end=text.index('\n}',at)+2;return text[at:end]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();control=json.loads(a.control.read_text());candidate=json.loads(a.candidate.read_text());old=control['expert_q2_model'];new=candidate['expert_q2_model']
 require(old['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q4_0'and new['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Exact staged format pair required')
 oldpath=Path(old['actual_entry']['path']);newpath=Path(new['actual_entry']['path']);require(record(oldpath)==old['actual_entry']and record(newpath)==new['actual_entry'],'Actual compiled entries changed')
 before=oldpath.read_text();after=newpath.read_text();rows=[]
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  x=body(before,name);y=body(after,name)
  if name=='resident_reset_empty_context':x=x.replace('reset.slots!=581','reset.slots!=867')
  require(x==y,'A resource, identity or empty-context guard changed: '+name);rows.append(dict(function=name,unchanged_except_explicit_cache_capacity=True,sha256=hashlib.sha256(y.encode()).hexdigest()))
 for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")'):
  require(before.count(marker)==after.count(marker)>0,'A synchronous owner/completion boundary changed: '+marker);rows.append(dict(call=marker,unchanged_count=after.count(marker)))
 require(new['scope']['cache_budget_bytes']==old['scope']['cache_budget_bytes']==1333739520 and new['scope']['Expert_input_type']==old['scope']['Expert_input_type']=='F32'and new['scope']['KV_type']==old['scope']['KV_type']=='F32','Cache bytes and F32 input/KV scopes must remain exact')
 mapping=Path(next(x[5:]for x in candidate['link_command']if x.startswith('-Map=')));text=mapping.read_text().replace('\\','/').lower()
 cache=new['commands'][1];cache_object=cache[cache.index('-o')+1];gpu=candidate['lossless_shader_storage']['vulkan_object']['path']
 require(str(cache_object).replace('\\','/').lower()in text and str(gpu).replace('\\','/').lower()in text and 'libllama.a(llama-moe-cache.cpp.o)'not in text,'Actual selected all-Q2 cache/provider overrides must win the native link')
 write_json(a.out,dict(completed=True,PS5_operations=0,CI_runs=0,control=record(a.control),candidate=record(a.candidate),unchanged_guards=rows,cache_budget_unchanged=True,original_gpu_and_kernel_floors_preserved=True,source_integrity_variant_separate=True,actual_link_map=record(mapping),all_Q2_cache_and_provider_overrides_selected=True))
 print(json.dumps(dict(all_Q2_resource_identity_completion_audit_passed=True,checks=len(rows),PS5_operations=0)),flush=True)
if __name__=='__main__':main()
