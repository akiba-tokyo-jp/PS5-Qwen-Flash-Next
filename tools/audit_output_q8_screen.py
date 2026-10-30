#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify output-only quota coupling and unchanged physical admission bodies."""
import argparse,json,os,subprocess
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control','candidate','workspace','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text())
    before=Path(old['routing_sharing']['actual_sources']['entry']['path']).read_text()
    profile=new.get('output_Q8_normal',new.get('output_Q8_screen'))
    require(profile is not None,'An explicit output-only Q8 profile is required')
    after=Path(profile['actual_sources']['entry']['path']).read_text();checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        x,y=body(before,name),body(after,name)
        if name=='resident_reset_empty_context':x=x.replace('reset.slots!=867','reset.slots!=997'if'output_Q8_normal'in new else'reset.slots!=qwen_app_output_Q8_slots()')
        require(x==y,'Physical/owner/reset body changed outside actual selected slot count: '+name);checks.append(name)
    owner=profile['actual_sources']['owner'];owner_path=Path(owner['path']);header=owner_path.parent/'device_buffer_budget.h'
    expected=(ROOT/'native/app/device_buffer_budget.h').read_text().replace('model_postload_device_budget = 1792ull << 20','model_postload_device_budget = (1792ull << 20) + 199680000ull').replace('model_internal_workspace_budget = 256ull << 20','model_internal_workspace_budget = 248ull << 20')
    require(header.read_text()==expected,'Only explicit resident-to-cache quota transfer and qualified workspace cap permitted')
    start=after.index('int main(int argc, char ** argv) {');first=after.index('    try {',start)
    for flag in ('GGML_VK_DISABLE_INTEGER_DOT_PRODUCT','GGML_VK_DISABLE_COOPMAT','GGML_VK_DISABLE_COOPMAT2'):
        at=after.index('setenv("'+flag+'","1",1)',first);require(at<first+600,'Floating-input selection must precede all device setup')
    require(profile['scope']['integer_activation_quantization_disabled'],'Explicit floating inputs required')
    folder=Path(a.out).parent;folder.mkdir(parents=True,exist_ok=True);host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=folder/'output-Q8-budget.exe'
    cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-Wno-error=misleading-indentation','-I',str(header.parent),'-I',str(ROOT/'native/app'),str(ROOT/'tests/output_q8_cache_budget.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,command in enumerate((cmd,[str(exe)])):
        run=subprocess.run(command,capture_output=True,timeout=180,env=env);(folder/f'output-Q8-budget-{i}.private.log').write_bytes(run.stdout+run.stderr)
        require(run.returncode==0,run.stderr.decode(errors='replace')[-2500:])
    for row in profile['actual_sources'].values():require(record(row['path'])==row,'Compiled Q8 source changed')
    require(new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Native dispatch/imports required')
    write_json(a.out,dict(completed=True,unchanged_guard_families=checks,actual_Q8_bank_boundary_and_metadata_reset_test=True,
        single_buffer_limit_512_MiB=True,CPU_limit_512_MiB=True,physical_Direct_and_system_reserves_unchanged=True,
        actual_output_payload_reduction_required=595968000,postload_cache_transfer=199680000,
        original_full_model_parent_required=True,PS5_operations=0,CI_runs=0,commands=[cmd,[str(exe)]]))
    print('Output-only quota coupling, physical guards, floating inputs and actual cache/bank boundaries passed.')
if __name__=='__main__':main()
