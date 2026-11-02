#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile a recovered entry view for comparison; never qualify it by compilation."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from build_performance_quantizer import record
from additional_cache_variant import geometry as additional_geometry
from driver_table_storage import sections
from build_limit_margin_probe import DECL as limit_declarations
from resident_table_admission import incremental_header,direct_header
from resident_kernel_min_scope import system_header as minimum_system_header,source_header as minimum_source_header
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','recovered','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    recovered=load(args.recovered)
    need(recovered['completed'] and recovered['embedded_parent_and_candidate_metadata_byte_exact'] and
         recovered['selected_causal_header_byte_exact'],'Exact recovered selected metadata required')
    for row in recovered['outputs']:
        need(record(row['path'])==row,'Recovered metadata changed')
        if Path(row['path']).suffix=='.h':shutil.copyfile(row['path'],args.out/Path(row['path']).name)
    native=load(args.current/'provenance/native-link.receipt.private.json');active=load(args.current/'active-console.private.json')
    command=native['compile_commands'][0].copy();original_source=command[command.index('-c')+1]
    source=args.out/'entry.private.cpp';text=Path(next(r['path'] for r in recovered['outputs'] if Path(r['path']).name=='entry.private.cpp')).read_text(encoding='utf-8')
    source.write_text('#line 1 '+json.dumps(original_source)+'\n'+text,encoding='utf-8',newline='\n')
    # Recover the original writer for the control; request-end durability is a
    # separately composed candidate, not an unrecorded header substitution.
    old=subprocess.check_output(['git','show','2b683814c9b6ed18c13352963c0a989f9e4d0b15:native/app/durable_token_ledger.h'],cwd=ROOT)
    (args.out/'durable_token_ledger.h').write_bytes(old)
    budgets=dict(model_postload_device_budget=active['postload_device_budget_bytes'],
        model_postload_single_buffer=active['postload_single_buffer_bytes'],model_internal_workspace_budget=48<<20)
    need(budgets['model_postload_device_budget']==6199160832 and budgets['model_postload_single_buffer']==2<<30,
         'Exact selected current application quotas required')
    budget=(ROOT/'native/app/device_buffer_budget.h').read_text()
    for name,value in budgets.items():
        budget,count=re.subn(r'(inline constexpr std::uint64_t '+name+r' = )[^;]+;',r'\g<1>'+str(value)+'ull;',budget)
        need(count==1,'One selected budget definition required')
    (args.out/'device_buffer_budget.h').write_text(budget,encoding='utf-8',newline='\n')
    profile=(ROOT/'native/app/resident_output_q8_profile.h').read_text()
    values=dict(resident_output_Q8_cache_transfer=4190089216,resident_output_Q8_cache_budget=5703659520,
                resident_output_Q8_postload_budget=budgets['model_postload_device_budget'])
    for name,value in values.items():
        profile,count=re.subn(r'(inline constexpr std::uint64_t '+name+r'=)[^;]+;',r'\g<1>'+str(value)+'ull;',profile)
        need(count==1,'One selected profile definition required')
    profile=profile.replace('resident_output_Q8_payload_saving-(16ull<<20)',
        'resident_output_Q8_payload_saving+221184000ull+3163852800ull+1038090240ull-(16ull<<20)')
    (args.out/'resident_output_q8_profile.h').write_text(profile,encoding='utf-8',newline='\n')
    reset=(ROOT/'native/app/resident_output_q8_cache_reset.h').read_text().replace('997','3712').replace('867','3072')
    (args.out/'resident_output_q8_cache_reset.h').write_text(reset,encoding='utf-8',newline='\n')
    prefill=(ROOT/'native/app/prefill16_policy.h').read_text()
    # The selected native entry and engine use the already qualified width32.
    prefill=prefill.replace('return width==4||width==16;', 'return width==4||width==16||width==32;')
    (args.out/'prefill16_policy.h').write_text(prefill,encoding='utf-8',newline='\n')
    declarations='extern "C" bool qwen_app_resident_CPU_metadata_scope_active();\n'
    declarations+='extern "C" void qwen_app_select_resident_CPU_metadata_scope(bool);\n'
    declarations+='extern "C" bool qwen_app_resident_GPU_OS_reserve_active();\n'
    declarations+='extern "C" void qwen_app_activate_resident_GPU_OS_reserve();\n'
    (args.out/'resident_CPU_metadata_scope.h').write_text(declarations,encoding='utf-8',newline='\n')
    system=(ROOT/'native/app/system_memory.h').read_text()
    system=system.replace('namespace qwen_app {','#include "resident_CPU_metadata_scope.h"\n'+limit_declarations+'\nnamespace qwen_app {',1)
    old='const auto extra=std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size);'
    need(system.count(old)==1,'One original complete system-memory selector required')
    system=system.replace(old,'const auto extra=qwen_app_resident_CPU_metadata_scope_active()?21ull:std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size);',1)
    system=minimum_system_header(system)
    lines=[line for line in system.splitlines() if 'const auto extra=' in line];need(len(lines)==1,'One selected system-memory price required')
    system=system.replace(lines[0],lines[0].replace('const auto extra=','const auto original_extra=')+
        '\n    const auto extra=qwen_limit_probe_extra(s.kernel_free,s.kernel_minimum,s.kernel_reserved,original_extra);',1)
    (args.out/'system_memory.h').write_text(system,encoding='utf-8',newline='\n')
    phase=(ROOT/'native/app/resident_phase_vm.h').read_text()
    phase=phase.replace('std::max<std::uint64_t>(m.kernel_reserved,256)',
        '(qwen_app_resident_CPU_metadata_scope_active()?21ull:std::max<std::uint64_t>(m.kernel_reserved,256))')
    phase=minimum_source_header(phase)
    (args.out/'resident_phase_vm.h').write_text(phase,encoding='utf-8',newline='\n')
    for name,transform in (('resident_incremental_tables.h',incremental_header),('resident_direct_tables.h',direct_header)):
        (args.out/name).write_text(transform((ROOT/'native/app'/name).read_text()),encoding='utf-8',newline='\n')
    routes=(ROOT/'native/app/completed_expert_routes.h').read_text().replace('std::uint8_t layer=0, tokens=0;',
        'std::uint8_t layer=0, tokens=0, experts=10;').replace('std::uint16_t,40>','std::uint16_t,320>')
    (args.out/'completed_expert_routes.h').write_text(routes,encoding='utf-8',newline='\n')
    (args.out/'padded_cache_geometry.h').write_text(additional_geometry((ROOT/'native/app/padded_cache_geometry.h').read_text()),
        encoding='utf-8',newline='\n')
    mappings={}
    for name in ('device_buffer_budget.h','resident_output_q8_profile.h','resident_output_q8_cache_reset.h','prefill16_policy.h','durable_token_ledger.h',
                 'system_memory.h','resident_phase_vm.h','resident_incremental_tables.h','resident_direct_tables.h','completed_expert_routes.h','padded_cache_geometry.h'):
        mappings[(ROOT/'native/app'/name).resolve().as_posix()]=(args.out/name).resolve().as_posix()
    overlay=args.out/'selected-view.private.json'
    save(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},
        roots=[dict(type='file',name=name,**{'external-contents':path}) for name,path in mappings.items()]))
    filtered=[];skip=False
    for argument in command:
        if skip:skip=False;continue
        if argument=='-ivfsoverlay':skip=True;continue
        filtered.append(argument)
    command=filtered;command[1:1]=['-I',str(args.out),'-ivfsoverlay',str(overlay),'-ferror-limit=0']
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-5000:])
    old_sections=sections(Path(recovered['actual_entry']['path']).read_bytes());new_sections=sections(obj.read_bytes())
    old_names={s['name'] for s in old_sections};new_names={s['name'] for s in new_sections}
    old_text={s['name']:s['data'] for s in old_sections if s['name'].startswith('.text')}
    new_text={s['name']:s['data'] for s in new_sections if s['name'].startswith('.text')}
    changed=[name for name in old_text.keys()&new_text.keys() if old_text[name]!=new_text[name]]
    report=dict(completed=True,recovered=record(args.recovered),source=record(source),artifact=record(obj),command=command,
        selected_quota_values=budgets,object_byte_exact=record(obj)['sha256']==recovered['actual_entry']['sha256'],
        changed_common_text_sections=len(changed),changed_text_names=sorted(changed),
        added_sections=sorted(new_names-old_names),removed_sections=sorted(old_names-new_names),
        source_view_audit_and_native_control_still_required=True,PS5_operations=0,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('recovered','source','artifact','command','changed_text_names','added_sections','removed_sections')}))


if __name__=='__main__':main()
