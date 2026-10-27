#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a smaller resident comparison from frozen original admission/objects.

Only this dedicated test entry supports ten bounded requests. Original model
arithmetic, precision, source identity/mapping, pool and completion checks remain.
No deployment, console execution or CI is performed by this builder.
"""
import argparse,copy,hashlib,json,os,re,shlex,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as audit_dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=('native_CPU_phase_control','native_SELF_read_control','native_cache_layout_phase_memory',
    'native_frame_CPU_diagnostic','native_large_cache_scope','native_mapped_streaming_copy',
    'native_metadata_memory_diagnostic','native_model_free_speculation','native_owned_mapped_probe',
    'native_padded_bank_layout_probe','native_predictive_cache','native_report_CPU_diagnostic',
    'native_shader_startup_memory_diagnostic','native_source_contention_probe',
    'native_source_stage_memory_diagnostic','native_direct_frame_evidence')

def specialize(source,tail,reuse_launch_integrity=False,receipt_diagnostic=False,measure_worker_memory=False,incremental_tables=False,delegate_shader=False,gpu_initializer_calibration=False):
    at=source.index('int main(int argc, char ** argv)');end=source.index('        const auto * chat_template',at)
    prefix=source[:at];body=source[at:end]
    flags=('native_display','monitor_validation','display_validation','runtime_validation','memory_validation',
        'palette_validation','vector_bank_validation','device_state_validation','PLE_slice_validation',
        'model_validation','operator_validation','moe_validation','vulkan_global_discovery')
    for flag in flags:body=re.sub(r'\bstartup\.'+flag+r'\b','false',body)
    body=re.sub(r'\bstartup\.first_generation_validation\b','true',body)
    for key in FORBIDDEN:body=body.replace('policy.contains("'+key+'")','false')
    old='        const auto startup = qwen_app::read_startup(argc, argv);'
    guard='\n        if(!startup.first_generation_validation||'+ '||'.join('startup.'+f for f in flags)+')\n'
    guard+='            throw std::runtime_error("Resident entry requires only the explicit headless first-generation startup");'
    assert body.count(old)==1;body=body.replace(old,old+guard)
    old='qwen_app::require_native_validation_policy(policy, mode, false);'
    assert body.count(old)==1
    body=body.replace(old,'qwen_app::require_resident_comparison_policy(policy);\n'
        '        const bool resident_CPU_calibration=policy.at("native_resident_comparison").at("CPU_startup_calibration").get<bool>();\n'
        '        const auto &checkpoint_proof=policy.at("native_resident_checkpoint");\n'
        '        qwen_app::require_model_free_checkpoint_report(read_completed_native_report(checkpoint_proof),checkpoint_proof);')
    original_GPU='        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());'
    model_region=body.index('        const bool indexed_fixture_requested=')
    GPU_at=body.index(original_GPU,model_region)
    if body[model_region:].count(original_GPU)!=1:raise ValueError('Unique model GPU start boundary required')
    # Explicit resident scope separates CPU preparation from later GPU pricing.
    # Retain all original operational, heap, identity, source and pool checks.
    CPU_prefix=body[:GPU_at].replace('qwen_app::admit_native_startup_memory()',
                                     'qwen_app::admit_native_system_memory()')
    CPU_prefix=CPU_prefix.replace('initial_memory_report["startup_kernel_target_required"]=true;',
        'initial_memory_report["startup_kernel_target_required"]=false;\n'
        '            initial_memory_report["CPU_phase_operational_policy"]=true;')
    body=CPU_prefix+body[GPU_at:];GPU_at=body.index(original_GPU,model_region)
    priced_GPU='''        qwen_native_stage("resident_CPU_preflight_complete_GPU_not_started");
        resident_sample("CPU_preflight_complete");
        if(resident_CPU_calibration) {
            const auto sources=qwen_app::native_model_source_stats();
            if(sources.chunks!=sources.completed_windows)throw std::runtime_error("CPU calibration source completion missing");
            // Source retirement uses the ordinary ledger-owner check even when
            // the ledger is empty. Establish that CPU producer without creating
            // a Vulkan instance/device or reserving any device buffer.
            qwen_app::enforce_native_model_compute_limits();
            const auto empty_ledger=qwen_app::native_model_device_stats();
            if(empty_ledger.live||empty_ledger.peak||empty_ledger.allocations)
                throw std::runtime_error("CPU calibration unexpectedly owns device allocations");
            qwen_app::stop_native_model_sources();
            resident_sample("CPU_sources_retired");
            struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
            write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
            write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-resident-CPU-startup-calibration-v1"},
                {"pid",getpid()},{"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"completed",true},{"CPU_preparation_completed",true},{"original_identity_metadata_and_virtual_rehearsal_passed",true},
                {"source_workers_stopped",true},{"source_chunks",sources.chunks},{"source_completed_windows",sources.completed_windows},
                {"CPU_heap_peak_bytes",heap.peak_bytes},{"model_loaded",false},{"GPU_calls",0},{"model_requests",0},
                {"ordinary_OS_close_required",true}});
            qwen_native_stage("resident_CPU_calibration_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)usleep(1000000);
        }
        {
            const auto memory=qwen_app::admit_native_system_memory();
            const auto floor=std::uint64_t(memory.kernel_minimum)+std::max<std::uint64_t>(memory.kernel_reserved,256);
            const auto required=std::max<std::uint64_t>(memory.kernel_target,floor+1897+256+256);
            write_fresh_report(startup.admission_report+".resident.before-GPU",{{"free_pages",memory.kernel_free},
                {"required_pages",required},{"observed_prior_model_phase_decline",1897},
                {"variation_pages",256},{"provisional_worker_pages",256},{"GPU_calls",0}});
            if(qwen_app::admit_native_system_memory().kernel_free<required)throw qwen_app::KernelMemoryPressure();
        }
        qwen_native_stage("resident_measured_GPU_phase_admitted_starting_GPU");
'''
    body=body[:GPU_at]+priced_GPU+body[GPU_at:]
    if gpu_initializer_calibration:
        if measure_worker_memory or receipt_diagnostic:
            raise ValueError('GPU initializer scope must not repeat worker or receipt-only calibration')
        needle='        if(false)\n            isolated_large_cache_layout(startup,policy,native_resources_started);'
        if body.count(needle)!=1:raise ValueError('Unique completed static GPU-resource frontier required')
        body=body.replace(needle,'#include "resident_gpu_calibration.inc"\n'+needle)
        prefix='#include "resident_gpu_calibration_policy.h"\n#include "ggml-vulkan.h"\n'+prefix
        old_checkpoint='''        const auto &checkpoint_proof=policy.at("native_resident_checkpoint");
        qwen_app::require_model_free_checkpoint_report(read_completed_native_report(checkpoint_proof),checkpoint_proof);'''
        if body.count(old_checkpoint)!=1:raise ValueError('Unique model-only checkpoint prerequisite required')
        body=body.replace(old_checkpoint,'''        if(policy.contains("native_resident_GPU_initialization_calibration"))
            qwen_app::require_resident_gpu_calibration_policy(policy);
        else {
'''+old_checkpoint+'\n        }')
    if measure_worker_memory:
        needle='''        {
            const auto memory=qwen_app::admit_native_system_memory();
            const auto floor=std::uint64_t(memory.kernel_minimum)+std::max<std::uint64_t>(memory.kernel_reserved,256);
            const auto required=std::max<std::uint64_t>(memory.kernel_target,floor+1897+256+256);'''
        replacement='''        const auto worker_memory=resident_worker_memory();
        write_fresh_report(startup.admission_report+".resident.worker-memory",{{"completed",true},{"lifetimes",worker_memory.completed},
            {"maximum_sampled_worker_VM_decline_pages",worker_memory.worker_pages},{"maximum_matched_idle_decline_pages",worker_memory.idle_pages},
            {"IO_payload_reads",0},{"GPU_calls",0},{"sampled_maxima_not_universal_minima",true}});
        {
            const auto memory=qwen_app::admit_native_system_memory();
            const auto floor=std::uint64_t(memory.kernel_minimum)+std::max<std::uint64_t>(memory.kernel_reserved,256);
            const auto required=std::max<std::uint64_t>(memory.kernel_target,floor+1958+worker_memory.worker_pages+worker_memory.idle_pages);'''
        if body.count(needle)!=1:raise ValueError('Exact provisional worker/variation pricing boundary required')
        body=body.replace(needle,replacement).replace('{"variation_pages",256},{"provisional_worker_pages",256}',
            '{"variation_pages",worker_memory.idle_pages},{"measured_worker_pages",worker_memory.worker_pages},{"provisional_allowances_replaced",true}')
        body=body.replace('{"observed_prior_model_phase_decline",1897}',
            '{"observed_prior_remaining_GPU_load_interval",1958},{"prior_before_interval_pages",3373},{"prior_after_context_pages",1415},{"interval_includes_final_CPU_source_setup",true}')
    if incremental_tables:
        needle='        qwen_app::restore_native_driver_tables();'
        replacement='''        const Json table_scope={{"schema","ps5-qwen-resident-incremental-tables-v1"},{"enabled",true},
            {"maximum_new_output_pages",1},{"sampled_Direct_metadata_pages",17},{"sampled_idle_pages",2},
            {"per_operation_extra_pages",20},{"all_original_SHA256_required",true},{"GPU_before_complete",false}};
        if(policy.at("native_resident_incremental_tables")!=table_scope)
            throw std::runtime_error("Exact incremental table restoration scope required");
        const auto restored=qwen_app::restore_resident_tables_incrementally();
        write_fresh_report(startup.admission_report+".resident.tables-memory",{{"completed",restored.completed},
            {"tables",restored.tables},{"output_bytes",restored.bytes},{"page_bounded_output_calls",restored.chunks},
            {"free_before",restored.before},{"minimum_sampled_free",restored.minimum},{"free_after",restored.after},
            {"sampled_Direct_allocator_metadata_pages",17},{"sampled_idle_allowance_pages",2},{"maximum_new_output_pages",1},
            {"selected_per_operation_extra_pages",20},{"original_aggregate_extra_pages",512},
            {"memory_refused",restored.memory_refused},{"scratch_live_bytes",restored.live},{"fault",restored.fault},{"GPU_calls",0}});
        if(!restored.completed) {
            if(restored.memory_refused)throw qwen_app::KernelMemoryPressure();
            throw std::runtime_error("Incremental original driver tables failed exact restoration or protection");
        }
'''
        if body.count(needle)!=1:raise ValueError('Unique original driver-table restoration boundary required')
        body=body.replace(needle,replacement)
    if receipt_diagnostic:
        needle='        qwen_app::restore_native_driver_tables();'
        if body.count(needle)!=1 or not reuse_launch_integrity:raise ValueError('Exact pre-restoration receipt diagnostic boundary required')
        diagnostic='''        if(policy.contains("native_resident_receipt_diagnostic")) {
        if(policy.at("native_resident_receipt_diagnostic")!=true||!resident_CPU_calibration)
            throw std::runtime_error("Receipt-only diagnostic requires the zero-model CPU scope");
        resident_sample("receipt_only_before");
        const auto &receipt_binding=policy.at("native_first_generation_validation");
        qwen_app::verify_resident_launch_integrity(policy.at("native_resident_launch_integrity"),
            receipt_binding.at("run_id").get<std::string>(),receipt_binding.at("candidate_SELF_bytes").get<std::uint64_t>(),
            receipt_binding.at("candidate_SELF_sha256").get<std::string>());
        resident_sample("receipt_only_completed");
        write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-resident-receipt-CPU-result-v1"},
            {"completed",true},{"receipt_only",true},{"pid",getpid()},{"run_id",receipt_binding.at("run_id")},
            {"same_launch_native_full_integrity_and_current_inode_passed",true},{"GPU_calls",0},{"model_requests",0},
            {"model_loaded",false},{"driver_tables_restored",false},{"ordinary_OS_close_required",true}});
        qwen_native_stage("resident_receipt_only_completed_waiting_for_ordinary_close_GPU_not_started");
        for(;;)usleep(1000000);
        }
'''
        body=body.replace(needle,diagnostic+needle)
    markers=('main_entered GPU_not_started=1 model_loaded=0',
        'configuration_read GPU_not_started=1 model_loaded=0',
        'policy_admitted GPU_not_started=1 model_loaded=0',
        'startup_integrity_memory_admission_before_IO GPU_not_started=1',
        'startup_integrity_memory_admission_completed GPU_not_started=1',
        'scoped_CPU_Flexible_kernel_memory_admitted_before_model_integrity GPU_not_started=1 model_loaded=0',
        'model_file_integrity_started_before_backend_initialization',
        'source_virtual_CPU_memory_admission_passed_before_probe GPU_not_started=1 model_loaded=0',
        'source_virtual_probe_all_reservations_and_releases_completed_before_backend GPU_not_started=1',
        'bounded_model_source_preflight_passed_before_backend',
        'source_pipeline_CPU_preflight_passed_before_Vulkan GPU_not_started=1')
    for i,marker in enumerate(markers):
        needle='qwen_native_stage("'+marker+'");'
        if body.count(needle)!=1:raise ValueError('Unique startup sample marker required: '+marker)
        body=body.replace(needle,needle+'resident_sample("stage_'+str(i)+'");')
    # Specialization removes only unreachable fixture/transport branches. Keep
    # the original source, metadata, protected virtual, CPU and GPU predicates.
    required=('wait_for_initial_model_CPU_budget','validate_original_footprint','require_prior_metadata',
        'admit_native_model_mapping','admit_native_startup_memory','require_model_CPU_budget',
        'start_native_model_sources','memory_budget.admit','llama_model_load_from_file',
        'enforce_native_model_compute_limits','configure_native_padded_cache','llama_init_from_model')
    if any(x not in body for x in required):raise ValueError('An original admission boundary was omitted')
    extra=''
    if reuse_launch_integrity:
        needle='qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",gate.at("candidate_SELF_bytes").get<std::uint64_t>(),\n                        gate.at("candidate_SELF_sha256").get<std::string>(),60);'
        if body.count(needle)!=1:raise ValueError('Unique resident SELF integrity boundary required')
        body=body.replace(needle,'qwen_app::verify_resident_launch_integrity(policy.at("native_resident_launch_integrity"),\n'
            '                    gate.at("run_id").get<std::string>(),gate.at("candidate_SELF_bytes").get<std::uint64_t>(),\n'
            '                    gate.at("candidate_SELF_sha256").get<std::string>());\n'
            '                qwen_native_stage("resident_same_launch_full_SELF_SHA256_and_current_inode_passed_without_payload_rescan");')
        extra='#include "resident_launch_integrity.h"\n'
        if delegate_shader:
            if receipt_diagnostic:raise ValueError('Shader handoff requires the complete resident CPU preparation path')
            needle='''else qwen_app::verify_resident_launch_integrity(policy.at("native_resident_launch_integrity"),
                    gate.at("run_id").get<std::string>(),gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
                    gate.at("candidate_SELF_sha256").get<std::string>());'''
            replacement='''else {
                    const auto launch_receipt=qwen_app::verify_resident_launch_integrity(policy.at("native_resident_launch_integrity"),
                        gate.at("run_id").get<std::string>(),gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
                        gate.at("candidate_SELF_sha256").get<std::string>(),&policy.at("native_shader_storage").at("external_file"));
                    qwen_app::bind_resident_shader_integrity(launch_receipt,policy.at("native_shader_storage").at("external_file"));
                    qwen_native_stage("resident_current_launch_external_shader_SHA256_and_identity_bound_without_active_title_payload_rescan");
                }'''
            if body.count(needle)!=1:raise ValueError('Exact same-launch integrity call required for shader handoff')
            body=body.replace(needle,replacement)
    elif delegate_shader:raise ValueError('Shader handoff requires same-launch SELF integrity')
    if measure_worker_memory:extra='#include "expert_prefetch_io.h"\n'+extra
    post='\n#include "resident_worker_memory.h"\n'if measure_worker_memory else'\n'
    if incremental_tables:post+='\n#include "resident_incremental_tables.h"\n'
    return '#include "resident_comparison_policy.h"\n'+extra+prefix+'\n#include "resident_startup_trace.h"\n'+post+body+'\n'+tail

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','qualified-native','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--qwen-only-factory',action='store_true',help='Reject other architectures at the original factory; keep Qwen4Exp graph objects unchanged')
    p.add_argument('--reuse-qwen-factory-from',type=Path,help='Reuse only an exact qualified factory object, with source/recipe/object provenance')
    p.add_argument('--reuse-launch-SELF-integrity',action='store_true',help='Require a same-launch native full-hash receipt and current native file identity')
    p.add_argument('--receipt-only-diagnostic',action='store_true',help='Stop the zero-GPU CPU scope immediately after receipt verification')
    p.add_argument('--measure-worker-memory',action='store_true',help='Measure four actual native worker lifetimes and matched idle instead of provisional allowances')
    p.add_argument('--incremental-driver-tables',action='store_true',help='Use page-bounded original-table restoration with per-operation measured accounting')
    p.add_argument('--delegate-shader-launch-integrity',action='store_true',help='Reuse fresh native whole shader-file integrity; keep original per-use frame hashes')
    p.add_argument('--GPU-initializer-calibration',action='store_true',help='Measure one model-free backend lifetime with distinct ordinary-reserve and prior-fixture components')
    a=p.parse_args();prior=json.loads(a.qualified_native.read_text())
    if a.reuse_qwen_factory_from and not a.qwen_only_factory:raise ValueError('Factory reuse requires the exact Qwen-only factory')
    if not prior.get('lossless_driver_tables_link_map_passed'):raise ValueError('Qualified cold-driver native link required')
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Qualified input changed: '+str(row['path']))
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    source=ROOT/'native/app/native_main.cpp';tail=ROOT/'native/app/resident_comparison_tail.inc'
    generated=a.out/'resident-comparison.private.cpp';generated.write_text(specialize(source.read_text(),tail.read_text(),a.reuse_launch_SELF_integrity,a.receipt_only_diagnostic,a.measure_worker_memory,a.incremental_driver_tables,a.delegate_shader_launch_integrity,a.GPU_initializer_calibration),newline='\n')
    c=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    old=c[c.index('-o')+1];obj=a.out/'resident-comparison.o';c[c.index('-c')+1]=str(generated);c[c.index('-o')+1]=str(obj)
    c=[x for x in c if x not in ('-O1','-O2','-O3')]+['-Oz','-ffunction-sections','-fdata-sections','-Wno-unused-variable']
    command=[str(obj)if x==old else x for x in prior['link_command']]
    image=a.out/'qwen-native.pie.elf';command[command.index('-o')+1]=str(image)
    command=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in command]
    extra=[];factory=None;shader_handoff=None
    if a.delegate_shader_launch_integrity:
        from resident_shader_integrity import build as build_shader_handoff
        shader_handoff=build_shader_handoff(prior,a.out/'shader-integrity-overlay')
        for replacement in shader_handoff['replacements']:
            old_shader=replacement['original_object']['path'];new_shader=replacement['object']['path']
            if command.count(old_shader)!=1:raise ValueError('The actual original shader object must be replaced exactly once')
            command=[new_shader if x==old_shader else x for x in command]
    if a.qwen_only_factory:
        upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
        original=upstream/'src/llama-model.cpp';text=original.read_text();start=text.index('static llama_model * llama_model_mapping(');end=text.index('\n}\n',start)+3
        body=text[start:end];target='return new llama_model_qwen4exp(params);'
        if body.count(target)!=1:raise ValueError('Exact original Qwen4Exp factory required')
        replacement='static llama_model * llama_model_mapping(llm_arch arch, const llama_model_params & params) {\n'
        replacement+='    if(arch!=LLM_ARCH_QWEN4EXP)throw std::runtime_error("This original-precision title admits only Qwen4Exp");\n    '+target+'\n}\n'
        modified=a.out/'llama-model-qwen-only.private.cpp';modified.write_text(text[:start]+replacement+text[end:],newline='\n')
        recipes=a.cache/'build/llama-ps5/compile_commands.json';entry=next(x for x in json.loads(recipes.read_text())if Path(x['file']).name=='llama-model.cpp')
        args=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in shlex.split(entry['command'],posix=False)]
        factory_obj=a.out/'llama-model-qwen-only.o';args[args.index('-c')+1]=str(modified);args[args.index('-o')+1]=str(factory_obj)
        args+=['-I',str(original.parent),'-ffunction-sections','-fdata-sections']
        factory=dict(original=record(original),generated=record(modified),original_prefix_and_suffix_preserved=True,
            admitted_architecture='LLM_ARCH_QWEN4EXP',other_architectures_rejected=True,original_graph_sources_and_archives_unchanged=True,
            original_compile_recipe=record(recipes))
        if a.reuse_qwen_factory_from:
            old=json.loads(a.reuse_qwen_factory_from.read_text());proof=old['resident_factory']
            if not old['resident_comparison_entry'] or proof['original']!=factory['original'] or proof['original_compile_recipe']!=factory['original_compile_recipe']:
                raise ValueError('Factory source/recipe changed')
            for key in ('original','generated','original_compile_recipe'):
                if record(proof[key]['path'])!=proof[key]:raise ValueError('Qualified factory input changed')
            if proof['generated']['sha256']!=factory['generated']['sha256']:raise ValueError('Generated factory content changed')
            old_command=proof.get('original_object_compile_command')
            if old_command is None:
                old_command=next(c for c in old['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama-model-qwen-only.private.cpp')
            actual_source=proof.get('actual_object_source',proof['generated'])
            if record(actual_source['path'])!=actual_source or actual_source['sha256']!=factory['generated']['sha256']:
                raise ValueError('Reused factory actual compiled source changed')
            if '-c'not in old_command or Path(old_command[old_command.index('-c')+1])!=Path(actual_source['path']):
                raise ValueError('Reused factory original compile source differs from its recorded object provenance')
            def normalized(c):
                c=c.copy();c[c.index('-c')+1]='SOURCE';c[c.index('-o')+1]='OBJECT';return c
            if normalized(old_command)!=normalized(args):raise ValueError('Factory compile options changed')
            object_row=next(r for r in old['inputs_before']if r['path']==old_command[old_command.index('-o')+1])
            if record(object_row['path'])!=object_row:raise ValueError('Qualified factory object changed')
            factory_obj=Path(object_row['path']);factory.update(reused_object=object_row,reused_from=record(a.reuse_qwen_factory_from),
                original_object_compile_command=old_command,actual_object_source=actual_source)
        else:extra.append((args,Path(entry['directory'])))
        command.insert(command.index('--start-group'),str(factory_obj))
    paths=[Path(__file__),a.qualified_native,source,tail,ROOT/'native/app/resident_comparison_policy.h',
           ROOT/'native/app/resident_startup_trace.h',generated]
    if a.reuse_launch_SELF_integrity:paths += [ROOT/'native/app/resident_launch_integrity.h',ROOT/'native/app/resident_shader_integrity.h']
    if a.measure_worker_memory:paths.append(ROOT/'native/app/resident_worker_memory.h')
    if a.incremental_driver_tables:paths.append(ROOT/'native/app/resident_incremental_tables.h')
    if a.GPU_initializer_calibration:paths += [ROOT/'native/app/resident_gpu_calibration.inc',ROOT/'native/app/resident_gpu_calibration_policy.h']
    if factory:paths+=[Path(factory[k]['path'])for k in ('original','generated','original_compile_recipe')]
    if factory and factory.get('reused_from'):paths+=[a.reuse_qwen_factory_from,factory_obj,Path(factory['actual_object_source']['path'])]
    frozen=[record(x)for x in paths]+prior['inputs_before']
    if shader_handoff:frozen+=shader_handoff['inputs']+[r['object']for r in shader_handoff['replacements']]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    commands=[(c,ROOT),*extra,(command,ROOT)]
    for i,(args,cwd)in enumerate(commands):
        result=subprocess.run(args,cwd=cwd,capture_output=True,timeout=600,env=env)
        (a.out/f'build-{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen resident input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),inputs_before=frozen+[record(obj)],
        source_parent=record(a.qualified_native),link_command=command,compile_commands=[c]+[x[0]for x in extra],
        resident_comparison_entry=True,resident_factory=factory,resident_same_launch_integrity=a.reuse_launch_SELF_integrity,resident_receipt_only_diagnostic=a.receipt_only_diagnostic,resident_worker_memory_measured=a.measure_worker_memory,resident_incremental_driver_tables=a.incremental_driver_tables,resident_shader_integrity_handoff=shader_handoff,console_access=False,PS5_operations=0,CI_runs=0,
        resident_GPU_initializer_calibration=a.GPU_initializer_calibration,
        application_sources=prior['application_sources']+[record(tail)],
        application_headers=prior['application_headers']+[record(ROOT/'native/app/resident_comparison_policy.h'),
            record(ROOT/'native/app/resident_startup_trace.h')])
    if factory:receipt['inputs_before'].append(record(factory_obj))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    imported=audit(a.workspace,a.cache,a.out)
    if imported['missing']:raise ValueError('Missing actual native import')
    llvm=Path(c[0]).parent;symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(x in symbols for x in ('qwen_app::serve_bounded_demo(','qwen_app::NativeDisplay::start(','httplib::Server::listen(')):
        raise ValueError('HTTP/display implementation retained in resident comparison')
    if 'llama_model_load_from_file'not in symbols or 'qwen_app::LlamaEngine::next_with_one_draft('not in symbols:
        raise ValueError('Actual model or speculative arithmetic missing')
    linkmap=(a.out/'native-link.private.map').read_text().replace('\\','/')
    for row in prior['bounded_model_source_overrides']['objects']:
        if Path(row['object']['path']).as_posix()not in linkmap:raise ValueError('An original bounded source override missing')
    if shader_handoff:
        for replacement in shader_handoff['replacements']:
            if Path(replacement['object']['path']).as_posix()not in linkmap or Path(replacement['original_object']['path']).as_posix()in linkmap:
                raise ValueError('Actual shader overlay replacement was not proven in the final link map')
    dispatch=audit_dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if not dispatch['passed']:raise ValueError('Physical native dispatch missing')
    receipt.update(native_dispatch_audit=dispatch,real_module_import_audit=imported,
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']),
        resident_http_and_display_absence_passed=True,link_returncode=0,input_hashes_stable=True)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(resident_comparison_link_passed=True,native_image_bytes=receipt['artifact']['bytes'],qwen_only_factory=bool(factory),PS5_operations=0)))
if __name__=='__main__':main()
