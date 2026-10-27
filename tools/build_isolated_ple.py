#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link the unchanged bounded PLE fixture without model/service entry points."""
import argparse,json,os,re,subprocess
from pathlib import Path
from build_preservation_integrity import record
from audit_native_imports import audit
from native_dispatch import audit as dispatch_audit
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('workspace','cache','qualified-native','driver-root','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--split-bank',action='store_true',help='Link only the independent BF16 bank fixture, preserving the shared startup admission')
    p.add_argument('--ready-source-plan',type=Path,help='Explicitly embed an original-byte ten-Expert plan; requires --split-bank')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.ready_source_plan and not a.split_bank:raise ValueError('Original-source plan requires the isolated split-bank title')
    if a.ready_source_plan:
        raw=a.ready_source_plan.read_bytes();plan=json.loads(raw)
        if len(raw)>65536 or plan.get('schema')!='ps5-qwen-ready-original-plan-v1' or len(plan.get('matrices',[]))!=30 or len(set(plan.get('experts',[])))!=10:
            raise ValueError('One bounded original ten-Expert plan required')
        sha=record(a.ready_source_plan)['sha256']
        (a.out/'ready_original_plan.inc').write_text('static constexpr char ready_original_manifest[]='+json.dumps(raw.decode('ascii'))+';\n'
            +'static constexpr char ready_original_manifest_sha256[]="'+sha+'";\n',newline='\n')
    prior=json.loads(a.qualified_native.read_text());source=(ROOT/'native/app/native_main.cpp').read_text()
    if prior['linked_driver']['archive_sha256']!='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925':
        raise ValueError('Exact qualified native driver required')
    def function(signature):
        start=source.index(signature);end=source.index('\n}\n',start)+3;return source[start:end]
    start=source.index('static bool boundary_memory_enabled=');end=source.index('\nenum class ReportWriteMode',start)
    (a.out/'isolated_PLE_boundaries.inc').write_text(source[start:end],newline='\n')
    signatures=('static ModelFileIdentity model_file_identity(','static void validate_prior_shader_CPU(',
        'static Json read_prior_shader_CPU(','static Json diagnostic_VM_population(',
        'static std::uint64_t observed_system_headroom(','static void require_model_CPU_budget(',
        'static void native_log(','static void admit_shader_storage_CPU(')
    (a.out/'isolated_PLE_admission.inc').write_text('\n'.join(function(s)for s in signatures),newline='\n')
    if a.split_bank:
        isolated=ROOT/'native/app/isolated_ple_main.cpp'
        prefix=isolated.read_text().split('int main(int argc,char **argv) {')[0]
        (a.out/'isolated_split_startup.inc').write_text(prefix,newline='\n')
    excluded={'session.cpp','model_checkpoint.cpp','http_app.cpp','ple_slice_admission.cpp',
        'bounded_demo.cpp','chat_prompt.cpp','native_main.cpp','device_state_admission.cpp','native_socket.cpp',
        'monitor_raster.cpp','native_display.cpp','gpu_admission.cpp','palette_gpu_dispatch.cpp','palette_gpu_admission.cpp',
        'vector_bank_admission.cpp','operator_admission.cpp','moe_admission.cpp','lexer.cpp','parser.cpp','runtime.cpp',
        'value.cpp','string.cpp','json.cpp','unicode.cpp','unicode-data.cpp','httplib.cpp','model_integrity.cpp','model_mapping.cpp'}
    commands=prior['compile_commands'];excluded_objects={str(Path(c[c.index('-o')+1]))for c in commands if '-c'in c and Path(c[c.index('-c')+1]).name in excluded}
    command=[x for x in prior['link_command']if x not in excluded_objects]
    image=a.out/('isolated-split-bank.pie.elf'if a.split_bank else 'isolated-PLE.pie.elf');command[command.index('-o')+1]=str(image)
    command=['-Map='+str(a.out/'native-link.private.map')if x.startswith('-Map=')else x for x in command]
    main_cmd=next(c.copy()for c in commands if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    main=ROOT/'native/app'/('isolated_split_bank_main.cpp'if a.split_bank else 'isolated_ple_main.cpp');obj=a.out/(main.stem+'.o')
    main_cmd[main_cmd.index('-c')+1]=str(main);main_cmd[main_cmd.index('-o')+1]=str(obj);main_cmd+=['-I',str(a.out)]
    fixture=ROOT/'native/app'/('split_bank_admission.cpp'if a.split_bank else 'ple_slice_admission.cpp');fixture_obj=a.out/(fixture.stem+'.o')
    fixture_cmd=next(c.copy()for c in commands if '-c'in c and Path(c[c.index('-c')+1]).name=='ple_slice_admission.cpp')
    fixture_cmd[fixture_cmd.index('-c')+1]=str(fixture);fixture_cmd[fixture_cmd.index('-o')+1]=str(fixture_obj)
    additions=[]
    if a.split_bank:
        for name in('split_bank_allocation.cpp','ready_expert_fixture.cpp','ready_expert_native.cpp','ready_original_source.cpp','padded_bank_route.cpp'):
            src=ROOT/'native/app'/name;target=a.out/(src.stem+'.o');c=fixture_cmd.copy()
            c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(target);additions.append(c)
            if name=='ready_original_source.cpp'and a.ready_source_plan:c+=['-DQWEN_READY_ORIGINAL_PLAN=1','-I',str(a.out)]
            # Replace an older qualified route object explicitly. No other
            # qualified runtime/driver member is silently substituted.
            if name=='padded_bank_route.cpp':
                old=next(c for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name==name)
                command.remove(old[old.index('-o')+1])
            command.insert(command.index('--start-group'),str(target))
    command.insert(command.index('--start-group'),str(obj))
    command.insert(command.index('--start-group'),str(fixture_obj))
    new_objects={obj,fixture_obj}
    if a.split_bank:new_objects|={Path(c[c.index('-o')+1])for c in additions}
    fixed_paths={Path(__file__),main,fixture,ROOT/'native/app/native_main.cpp',a.qualified_native,
        a.out/'isolated_PLE_boundaries.inc',a.out/'isolated_PLE_admission.inc'}
    if a.split_bank:fixed_paths|={*[Path(c[c.index('-c')+1])for c in additions],ROOT/'native/app/isolated_ple_main.cpp',a.out/'isolated_split_startup.inc'}
    if a.ready_source_plan:fixed_paths|={a.ready_source_plan,a.out/'ready_original_plan.inc'}
    fixed_paths|={Path(x)for x in command if Path(x).is_file()and Path(x).suffix in('.o','.a','.so','.exe','.ld','.map')}
    fixed_paths-=new_objects;fixed_paths|=set((ROOT/'native/app').glob('*.h'))
    fixed=[record(f)for f in sorted(fixed_paths)]
    prior_rows={r['path']:r for r in prior['inputs_before']}
    for x in command:
        if Path(x).suffix in('.o','.a','.so')and Path(x)not in new_objects:
            if record(x)!=prior_rows.get(str(Path(x))):raise ValueError('Qualified linker input changed: '+x)
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    commands=[main_cmd,fixture_cmd,*additions,command]
    (a.out/'build-intent.private.json').write_text(json.dumps(dict(commands=commands,inputs=fixed,
        model_entry_point_audit_required=True,PS5_operations=0),indent=2)+'\n')
    snapshot=a.out/'source-at-execution';snapshot.mkdir()
    for path in(Path(__file__),main,fixture,ROOT/'native/app/native_main.cpp',*sorted((ROOT/'native/app').glob('*.h'))):(snapshot/path.name).write_bytes(path.read_bytes())
    if a.split_bank:
        for path in(*[Path(c[c.index('-c')+1])for c in additions],ROOT/'native/app/isolated_ple_main.cpp',a.out/'isolated_split_startup.inc'):(snapshot/path.name).write_bytes(path.read_bytes())
    if a.ready_source_plan:(snapshot/'ready_original_plan.inc').write_bytes((a.out/'ready_original_plan.inc').read_bytes())
    for i,c in enumerate(commands):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=240,env=env);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5500:])
    if fixed!=[record(f)for f in sorted(fixed_paths)]:raise ValueError('Isolated PLE inputs changed during build')
    llvm=Path(main_cmd[0]).parent
    raw=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(x in raw for x in('llama_decode','llama_model_load_from_file','llama_init_from_model','LlamaEngine::','serve_http(')):
        raise ValueError('A model/service entry point leaked into the isolated PLE image')
    required=('qwen_native_driver_complete','qwen_native_gpu_initialize',
        'qwen_app::admit_split_bank_backing'if a.split_bank else 'qwen_app::admit_PLE_slice_fixture')
    if a.split_bank and'qwen_app::admit_PLE_slice_fixture'in raw:raise ValueError('Unrelated PLE GPU fixture retained in the split-bank image')
    for symbol in required:
        if symbol not in raw:raise ValueError('Required native PLE implementation absent: '+symbol)
    dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(image)],text=True)
    providers=re.findall(r'Shared library: \[([^\]]+)\]',dynamic)
    receipt=dict(schema='ps5-qwen-isolated-split-bank-build-v1'if a.split_bank else 'ps5-qwen-isolated-PLE-build-v1',artifact=record(image),inputs_before=fixed,
        runtime_providers=providers,linked_driver=prior['linked_driver'],driver=prior['driver'],
        commands=commands,qualified_native=record(a.qualified_native),link_returncode=0,input_hashes_stable=True,
        shared_shader_and_CPU_guards_extracted_verbatim=True,model_loading_entry_points_absent=True,
        model_or_chat_service_executed=False,PS5_operations=0,CI_runs=0)
    if a.ready_source_plan:receipt['compiled_ready_source_plan']=record(a.ready_source_plan)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    imported=audit(a.workspace,a.cache,a.out)
    if imported['missing']:raise ValueError('Actual native module imports missing: '+str(imported['missing']))
    dispatch=dispatch_audit(a.workspace,a.driver_root,image,a.out/'dispatch-audit')
    if not dispatch['passed']:raise ValueError('Actual native driver dispatch audit failed')
    receipt.update(real_module_import_audit=imported,native_dispatch_audit=dispatch)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(isolated_title_link_passed=True,isolated_PLE_link_passed=not a.split_bank,split_bank_scope=a.split_bank,bytes=image.stat().st_size,
        missing_imports=0,model_entry_points_absent=True,actual_dispatch_passed=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
