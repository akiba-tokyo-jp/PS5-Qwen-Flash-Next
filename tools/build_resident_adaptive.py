#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify multiple completed snapshot replacements in the retained 128-slot profile."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from build_speculative_batch_probe import once
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def engine_source(text):
    text='#include "snapshot_replacement_runtime.h"\n'+text
    marker='    checkpoint_stats_.capture_positions[checkpoint_stats_.captures++]=position_;'
    return once(text,marker,'''    snapshot_replacement_budget.completed(context_,checkpoint_->payload_bytes(),true);
'''+marker)


def entry_source(text):
    text='#include "snapshot_replacement_runtime.h"\n'+text
    text=once(text,'const bool large_cache_candidate=false;','const bool large_cache_candidate=true;')
    text=once(text,'qwen_app::ResidentCheckpointCapacity checkpoint_capacity;',
        'qwen_app::snapshot_replacement_budget.bind(context);')
    old='''            const auto rounded=checkpoint_capacity.new_allocation(context,bytes);
            last_requested_snapshot=bytes;last_new_snapshot=rounded;
            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);'''
    new='''            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);
            const auto CPU=qwen_app::observe_native_system_memory();
            if(CPU.kernel_minimum!=898||CPU.kernel_reserved!=206||CPU.kernel_free<981)
                throw qwen_app::KernelMemoryPressure();
            const auto rounded=qwen_app::begin_snapshot_replacement(context,buffer_type,bytes,ledger.live,qwen_app::model_postload_device_budget);
            last_requested_snapshot=bytes;last_new_snapshot=rounded;'''
    text=once(text,old,new)
    text=once(text,'                checkpoint_capacity.completed(context,last_requested_snapshot,true);',
        '''                if(qwen_app::snapshot_replacement_budget.pending()||qwen_app::snapshot_replacement_budget.payload()!=last_requested_snapshot)
                    throw std::runtime_error("Every actual snapshot must positively complete before capacity reuse");''')
    text=text.replace('ordinal>=9','ordinal>=5').replace('routes.reserve(9)','routes.reserve(5)')
    begin=text.index('        run_arm(7,"warmup",0);');end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text=text[:begin]+'''        run_arm(7,"warmup",0);
        run_arm(7,"fixed-two",0);run_arm(7,"adaptive",0);
        run_arm(7,"adaptive",0);run_arm(7,"fixed-two",0);
        coverage_complete=coverage_complete&&completed.at(2).at("speculation").at("accepted").get<unsigned>()>1&&
            completed.at(3).at("speculation").at("accepted").get<unsigned>()>1;
'''+text[end:]
    text=text.replace('{"active_cache_slots",53}','{"active_cache_slots",128}')
    text=text.replace('{"matched_ABBA_request_ordinals",Json::array({1,2,3,4})}',
        '{"matched_ABBA_request_ordinals",Json::array({1,2,3,4})},{"snapshot_replacement_qualification",true},{"snapshot_replacements",qwen_app::snapshot_replacement_budget.replacements()},{"actual_snapshot_F32_sections",qwen_app::snapshot_witness_sections}')
    text=text.replace('{"adaptive_ABBA_request_ordinals",Json::array({5,6,7,8})}',
        '{"adaptive_ABBA_request_ordinals",Json::array({1,2,3,4})}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen causal parent changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    for path in Path(prior['causal_wide']['actual_entry']['path']).parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    scope=copy.deepcopy(prior['causal_wide']['scope']);scope.update(schema='ps5-qwen-resident-adaptive-speed-v1',maximum_requests=5,active_cache_slots=128)
    old_header=a.out/'speculative_behavior_policy.h';h=old_header.read_text()
    h=h.replace(json.dumps(json.dumps(prior['causal_wide']['scope'],separators=(',',':'))),json.dumps(json.dumps(scope,separators=(',',':'))))
    h=once(h,'p.at("native_padded_expert_cache").at("active_slots")!=53||p.contains("native_large_cache_scope")||',
        'p.at("native_padded_expert_cache").at("active_slots")!=128||!p.contains("native_large_cache_scope")||')
    old_header.write_text(h,newline='\n')
    names=('snapshot_replacement_runtime.h','snapshot_replacement_budget.h','snapshot_layout_witness.h')
    for name in names:(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    sources=[];commands=[];replacements={}
    for i,key in enumerate(('actual_engine','actual_entry')):
        original=Path(prior['causal_wide'][key]['path']);src=a.out/('resident-adaptive-'+key+'.private.cpp')
        src.write_text((engine_source if i==0 else entry_source)(original.read_text()),newline='\n')
        c=prior['causal_wide']['commands'][i].copy();old=c[c.index('-o')+1];obj=a.out/f'{i}.o'
        c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj);c[1:1]=['-I',str(a.out)];c+=['-I',str(original.parent)]
        sources.append(src);commands.append(c);replacements[old]=str(obj)
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    writer=upstream/'src/llama-context.cpp';s=writer.read_text();segment=s[s.index('class llama_io_write_device'):s.index('class llama_io_read_device')]
    if segment.count('mbuf_cur = std::move(mbuf);')!=2 or segment.index('mbuf_cur = std::move(mbuf);')>segment.index('mbuf_cur.buf.reset(ggml_backend_alloc_ctx_tensors_from_buft'):
        raise ValueError('Pinned writer must retire changed-size storage before replacement allocation')
    frozen +=[record(x)for x in(a.parent,Path(__file__),writer,upstream/'src/llama-context.h',upstream/'ggml/src/ggml-vulkan/ggml-vulkan.cpp',*sources,*a.out.glob('*.h'),*(ROOT/'native/app'/n for n in names))]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5500:])
        print(json.dumps(dict(resident_adaptive_build_step=i+1,total=3)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen adaptive source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(c[c.index('-o')+1])for c in commands],
        resident_adaptive=dict(scope=scope,actual_entry=record(sources[1]),actual_engine=record(sources[0]),commands=commands,
            metadata_witness_required_on_every_capture=True,complete_F32_original_state_required=True,new_Direct_metadata_allowance_pages=19,actual_allocator_caps_unchanged=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Resident adaptive native audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(resident_adaptive_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
