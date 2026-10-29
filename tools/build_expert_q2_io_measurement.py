#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a separate all-Q2 per-token/per-read observer; retain GPU math/guards."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-all-Q2-IO-measurement-v1',enabled=True,maximum_requests=3,
    per_token_completed_source_counters=True,individual_pread_wall_times=True,
    histogram_bin_ns=128000,histogram_bins=65,size_bin_bytes=65536,size_bins=17,original_IO_and_GPU_work_unchanged=True,
    HTTP_requests=0,VideoOut_starts=0,automatic_retries=0)

def entry_source(text):
    text='#include "source_read_latency.h"\n'+text
    marker='    if (source.schedule_enabled) result.update({'
    text=once(text,marker,'''    qwen_app::SourceReadLatency::Snapshot calls{};
    qwen_app_source_read_latency(calls.data(),calls.size());
    result["individual_read_calls"]=calls[0];result["individual_read_bytes"]=calls[1];
    result["individual_read_wall_ns"]=calls[2];result["individual_read_errors"]=calls[3];
    for(unsigned i=0;i<qwen_app::SourceReadLatency::bins;++i)
        result["individual_read_histogram_"+std::to_string(i)]=calls[4+i];
    for(unsigned i=0;i<qwen_app::SourceReadLatency::size_bins;++i){
        const auto base=4+qwen_app::SourceReadLatency::bins+3*i;
        result["individual_read_size_calls_"+std::to_string(i)]=calls[base];
        result["individual_read_size_bytes_"+std::to_string(i)]=calls[base+1];
        result["individual_read_size_ns_"+std::to_string(i)]=calls[base+2];
    }
'''+marker)
    text=once(text,'        const unsigned request_count=3;',
        '        if(policy.at("native_Expert_Q2_IO_measurement")!=Json::parse('+json.dumps(json.dumps(SCOPE,separators=(',',':')))+'))\n'
        '            throw std::runtime_error("Exact all-Q2 IO measurement scope required");\n        const unsigned request_count=3;')
    text=once(text,'                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});',
        '                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms},\n'
        '                    {"completed_performance",performance_snapshot(*engine)},\n'
        '                    {"Expert_uploaded_bytes",engine->expert_cache_metrics()->uploaded_bytes}});')
    return once(text,'{"requests",completed},{"model_loads",1}',
        '{"completed_IO_measurement",true},{"per_token_source_snapshots",true},{"requests",completed},{"model_loads",1}')

def owner_source(text):
    text='#include "source_read_latency.h"\nnamespace {qwen_app::SourceReadLatency source_latency;}\n'+text
    text=once(text,'        return pread(fd, target, bytes, static_cast<off_t>(offset));',
        '''        const auto begun=qwen_app::ProfileClock::now();
        const auto got=pread(fd,target,bytes,static_cast<off_t>(offset));
        const auto ns=qwen_app::profile_elapsed_ns(begun);
        source_latency.completed(got,ns);return got;''')
    return text+'''
extern "C" void qwen_app_source_read_latency(std::uint64_t*out,std::size_t count){
    if(!out||count!=qwen_app::SourceReadLatency::fields)
        throw std::runtime_error("Exact read-latency snapshot geometry required");
    const auto point=source_latency.snapshot();
    for(std::size_t i=0;i<count;++i)out[i]=point[i];
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());details=prior['expert_q2_model']
    require(details['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE' and
        prior['all_Q2_payload_preflight']['GPU_and_memory_guards_unchanged'],'Exact qualified all-Q2 preflight parent required')
    frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
    frozen +=[record(a.parent),record(__file__),record(ROOT/'native/app/source_read_latency.h')]
    for row in frozen:require(record(row['path'])==row,'Qualified input changed')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    local_header=a.out/'source_read_latency.h'
    local_header.write_bytes((ROOT/'native/app/source_read_latency.h').read_bytes())
    entry_command=prior['compile_commands'][0].copy();old_entry=Path(entry_command[entry_command.index('-c')+1])
    owner_command=prior['all_Q2_payload_preflight']['command'].copy()
    old_owner=Path(owner_command[owner_command.index('-c')+1])
    actual_owner=record(old_owner)
    require(all(actual_owner[k]==details['source_owner'][k]for k in ('bytes','sha256')),
        'The command source must be byte-identical to the qualified source owner')
    commands=[];replacements={};sources=[record(local_header)]
    for label,command,original,derive in (('entry',entry_command,old_entry,entry_source),('owner',owner_command,old_owner,owner_source)):
        source=a.out/(label+'.private.cpp');source.write_text(derive(original.read_text()),newline='\n')
        obj=a.out/(label+'.o');old_obj=command[command.index('-o')+1]
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        # Reproduce the original quoted-header directory without putting the
        # current checkout ahead of its qualified phase-specific headers.
        command[1:1]=['-I',str(original.parent)]
        if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
        commands.append(command);replacements[old_obj]=str(obj);sources +=[record(original),record(source)]
    # The corrected owner's command object is the current link input, not the
    # original pre-correction owner output named by an inherited command.
    current_owner=prior['all_Q2_payload_preflight']['object']['path']
    require(current_owner in replacements,'Current admitted owner must be replaced exactly')
    for old in replacements:require(prior['link_command'].count(old)==1,'One exact object replacement required')
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf'
    link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    for i,command in enumerate(commands+[link]):
        r=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(IO_measurement_build_step=i+1,total=3)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Frozen input changed during build')
    result=copy.deepcopy(prior);result.update(artifact=record(image),link_command=link,
        source_parent=record(a.parent),compile_commands=[commands[0]],
        inputs_before=frozen+sources+[record(a.out/'entry.o'),record(a.out/'owner.o')],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    result['expert_q2_model']['actual_entry']=record(a.out/'entry.private.cpp')
    result['all_Q2_IO_measurement']=dict(scope=SCOPE,entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),
        commands=commands,unchanged_GPU_objects=True,unchanged_memory_owner_completion_guards=True,
        no_per_read_logs_or_allocations=True,extra_static_counter_bytes=120*8)
    target=a.out/'receipt.private.json';write_json(target,result)
    result['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Native import/dispatch audit failed')
    write_json(target,result);print(json.dumps(dict(IO_measurement_built=True,PS5_operations=0,CI_runs=0)))

if __name__=='__main__':main()
