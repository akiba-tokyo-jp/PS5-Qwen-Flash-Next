#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a guarded independent shared-FFN prepass during demanded source I/O."""
import argparse,copy,json,os,re,shlex,subprocess
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='prefill32_indexed_streaming','Exact selected application required');a.out.mkdir(parents=True,exist_ok=False);(a.out/'aux-tmp').mkdir()
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';manifest_path=Path(prior['bounded_model_source_manifest']['path']);manifest=json.loads(manifest_path.read_text())
    rows=[r for r in manifest['objects']if r['source'].endswith('ggml-backend.cpp')and r['object']['path']in prior['link_command']];require(len(rows)==1,'One explicit current patched scheduler required');selected=rows[0]
    require(record(Path(selected['object']['path']))==selected['object'],'Actual selected scheduler object changed')
    args=shlex.split(selected['command'],posix=False);args=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in args];original=Path(args[args.index('-c')+1]);recipe=dict(command=selected['command'],directory=str(up))
    require(record(original)['sha256']==manifest['sources'][selected['source']]['patched_sha256'],'Exact currently linked scheduler source required; never substitute the original archive member')
    backend=original.read_text();backend=once(backend,'#include "ggml-backend.h"','#include "ggml-backend.h"\nextern "C" void qwen_app_overlap_after_split(ggml_backend_t,ggml_cgraph*);')
    marker='''            enum ggml_status ec = ggml_backend_graph_compute_async(split_backend, &split->graph);
            if (ec != GGML_STATUS_SUCCESS) {
                return ec;
            }
        } else {'''
    backend=once(backend,marker,marker.replace('        } else {','            qwen_app_overlap_after_split(split_backend,&split->graph);\n        } else {'))
    backend_source=a.out/'overlap-scheduler.private.cpp';backend_source.write_text(backend,newline='\n');backend_object=a.out/'overlap-scheduler.o'
    command=recipe['command'];require(command.count(str(original.resolve()))==1,'One exact scheduler compile input required');command=command.replace(str(original.resolve()),subprocess.list2cmdline([str(backend_source.resolve())]));command,n=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _:'-o '+subprocess.list2cmdline([str(backend_object.resolve())]),command);require(n==1,'One scheduler output required');command+=' -I'+subprocess.list2cmdline([str(original.parent)])
    engine_command=prior['routing_sharing']['commands'][2].copy();runtime=ROOT/'native/app/delivery_overlap.cpp';runtime_object=a.out/'overlap-runtime.o';engine_command[engine_command.index('-c')+1]=str(runtime);engine_command[engine_command.index('-o')+1]=str(runtime_object);engine_command[1:1]=['-I',str(ROOT/'native/app'),'-I',str(up/'ggml/src')]
    if '-MF'in engine_command:engine_command[engine_command.index('-MF')+1]=str(a.out/'overlap-runtime.private.d')
    for i,(cmd,cwd)in enumerate(((command,recipe['directory']),(engine_command,ROOT))):
        run=subprocess.run(cmd,cwd=cwd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'aux-tmp'),TEMP=str(a.out/'aux-tmp')));(a.out/f'aux-{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:]);print(json.dumps(dict(overlap_auxiliary_step=i+1,total=2)),flush=True)
    seed=copy.deepcopy(prior);at=seed['link_command'].index(selected['object']['path']);seed['link_command'][at:at+1]=[str(backend_object),str(runtime_object)];seed['inputs_before'] +=[record(x)for x in (manifest_path,original,backend_source,backend_object,runtime,runtime_object,ROOT/'native/app/delivery_overlap_plan.h')];seed_path=a.out/'overlap-seed.private.json';write_json(seed_path,seed)
    cache_command=prior['routing_sharing']['commands'][1];cache=Path(cache_command[cache_command.index('-c')+1]).read_text()
    cache='''extern "C" void qwen_app_overlap_begin(ggml_backend_t,ggml_cgraph*,int,bool);
extern "C" void qwen_app_overlap_stream_boundary(ggml_backend_t);
extern "C" void qwen_app_overlap_before_scatter();
'''+cache
    # Types must be declared before the hook declarations.
    cache='#include "ggml-backend.h"\n'+cache
    start=cache.index('    bool copy(ggml_backend_t backend,');end=cache.index('    void log_stats()',start)if '    void log_stats()'in cache[start:]else cache.index('\n};',start)
    part=cache[start:end];marker='        // A bounded page-in hint for actual misses, before any upload.'
    part=once(part,marker,'        qwen_app_overlap_begin(backend,graph,il,!fills.empty());\n'+marker)
    # Keep the selected-ID completion fence. Only later completed-upload
    # boundaries may postpone their fence to the first scatter after source I/O.
    boundary=part.index('        qwen_app_overlap_begin(');prefix=part[:boundary];tail=part[boundary:]
    tail=tail.replace('ggml_backend_synchronize(backend);','qwen_app_overlap_stream_boundary(backend);')
    tail=tail.replace('ggml_backend_tensor_set(', 'qwen_app_overlap_before_scatter();ggml_backend_tensor_set(')
    cache=cache[:start]+prefix+tail+cache[end:]
    entry_command=prior['compile_commands'][0];old_entry=Path(entry_command[entry_command.index('-c')+1]).read_text()
    scope=dict(prior['cold_request']['scope'],mode='independent_shared_overlap',additional_GPU_operations=True,guarded_dependency_and_live_range_checks=True,original_driver_unchanged=True,graph_metadata_restored_only_after_positive_completion=True,maximum_subgraph_nodes=1024)
    entry='#include <cstdint>\nextern "C" void qwen_app_overlap_stats(std::uint64_t*);\n'+once(old_entry,literal(prior['cold_request']['scope']),literal(scope))
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t overlap_before[10]{};qwen_app_overlap_stats(overlap_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["cold_request_timing"]=', '            std::uint64_t overlap_after[10]{};qwen_app_overlap_stats(overlap_after);Json overlap_delta=Json::array();for(unsigned i=0;i<10;++i)overlap_delta.push_back(overlap_after[i]-overlap_before[i]);row["independent_GPU_overlap"]={{"delta",overlap_delta},{"no_extra_GPU_buffers",true},{"live_range_and_dependency_proof_required",true}};\n            row["cold_request_timing"]=')
    entry=once(entry,'{"GPU_operations_added", false}','{"GPU_operations_added", true}')
    result,jobs,sources=link(seed_path,a.out,dict(entry=(entry_command,entry),cache=(cache_command,cache)),[Path(__file__),seed_path,original,backend_source,backend_object,runtime,runtime_object,ROOT/'native/app/delivery_overlap_plan.h'])
    for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):require(body(entry,name)==body(old_entry,name),'Original application guard changed')
    result['cold_request'].update(scope=scope,actual_sources=sources,commands=jobs,normal_validation_pending=True,production_adopted=False)
    result['delivery_overlap']=dict(scope=scope,actual_sources=sources,commands=jobs,backend_source=record(backend_source),backend_object=record(backend_object),backend_command=command,runtime_source=record(runtime),runtime_object=record(runtime_object),runtime_command=engine_command,live_alias_refusal_required=True,original_shader_math_and_driver_unchanged=True,no_extra_GPU_buffers=True,positive_fence_before_graph_pointer_restore=True,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='independent_shared_overlap_source_audit',driver_unchanged=True,original_physical_and_memory_guards=True,dependent_or_aliased_subgraphs_refused=True,original_selected_ID_fence_retained=True,graph_pointer_restore_after_positive_fence=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Guarded shared-FFN prepass built; runtime must prove actual eligible intervals and numerical behavior.')


if __name__=='__main__':main()
