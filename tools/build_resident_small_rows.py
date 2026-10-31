#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Batch immutable PLE/embedding rows on existing bounded source workers."""
import argparse,copy,json,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from build_model_io import validate_overrides
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    require(prior['resident_all_Q8']['scope']['active_cache_slots']==1381,
            'Independent resident-Q8 control required for the row-only comparison')
    oc=prior['all_Q2_optimized_monitor']['commands'][1]
    op=Path(oc[oc.index('-c')+1]);owner=op.read_text()
    reader=Path(prior['cold_request']['source_header']['path'])
    header=once(reader.read_text(),'    bool borrowed_window_contains(',
                '#include "resident_small_rows.inc"\n    bool borrowed_window_contains(')
    (a.out/'resident-mapped-source.private.h').write_text(header,newline='\n')
    owner+='''
namespace {bool small_rows_selected=false;std::array<std::uint64_t,5>small_rows_counters{};}
extern "C" void qwen_app_small_rows_select(bool enabled){
 required().require_completed_window();ops.require_metadata_idle();small_rows_selected=enabled;
}
extern "C" void qwen_app_small_rows_stats(std::uint64_t*out){
 if(!out)throw std::runtime_error("Small-row counters require an owned destination");
 std::copy(small_rows_counters.begin(),small_rows_counters.end(),out);
}
extern "C" bool qwen_app_small_rows(const void*const*addresses,unsigned count,std::size_t bytes,
 void*opaque,void(*consume)(void*,unsigned,const void*)){
 if(!small_rows_selected)return false;
 required().require_completed_window();ops.require_metadata_idle();
 if(!qwen_app_model_compute_limits_enabled()||!parallel_ready.load()||!addresses||!opaque||!consume||!count||count>8)
  throw std::runtime_error("Small-row batch requires the original live source owner");
 std::array<std::uintptr_t,8>at{};for(unsigned i=0;i<count;++i)at[i]=reinterpret_cast<std::uintptr_t>(addresses[i]);
 return required().upload_small_rows(at,count,bytes,
  [&](const auto&r,unsigned n,const auto&leases,const auto&before,const auto&use){ops.stream(r,n,leases,before,use);},
  [&](unsigned i,const void*data){consume(opaque,i,data);},small_rows_counters);
}
'''
    io_path=Path(prior['bounded_model_source_manifest']['path']);io=json.loads(io_path.read_text())
    item=next(x for x in io['objects']if x['source']=='ggml/src/ggml-cpu/ops.cpp')
    # Parse Windows compile arguments without interpreting shell expansion.
    command=[x[1:-1]if len(x)>1 and x[0]==x[-1]=='"'else x
             for x in shlex.split(item['command'],posix=False)]
    source=Path(command[command.index('-c')+1]);ops_text=source.read_text()
    begin=ops_text.index('        for (int64_t row = 0; row < ggml_nelements(ids); ++row) {',
                         ops_text.index('void ggml_compute_forward_get_rows('))
    end=ops_text.index('        return;\n    }',begin)
    old=ops_text[begin:end]
    key_begin=old.index('            const int64_t z =');key_end=old.index('            size_t copied = 0;')
    gather=old[key_begin:key_end]
    gather=gather.replace('            ', '                ')
    replacement='''        for(int64_t first=0;first<ggml_nelements(ids);first+=8){
            const unsigned n=unsigned(std::min<int64_t>(8,ggml_nelements(ids)-first));
            std::array<const void*,8>keys{};std::array<float*,8>outputs{};
            for(unsigned i=0;i<n;++i){const int64_t row=first+i;
'''+gather+'''                keys[i]=key;outputs[i]=output;
            }
            struct Batch {std::array<float*,8>*outputs;ggml_type type;int64_t columns;std::size_t bytes;};
            Batch batch{&outputs,src0->type,src0->ne[0],bytes};
            const auto consume=[](void*opaque,unsigned i,const void*window){
                auto&b=*static_cast<Batch*>(opaque);
                if(b.type==GGML_TYPE_BF16)ggml_cpu_bf16_to_fp32(static_cast<const ggml_bf16_t*>(window),(*b.outputs)[i],b.columns);
                else memcpy((*b.outputs)[i],window,b.bytes);
            };
            if(qwen_app_small_rows(keys.data(),n,bytes,&batch,consume))continue;
            for(unsigned i=0;i<n;++i){std::size_t copied=0;
                const void*window=qwen_app_model_source_chunk(keys[i],bytes,&copied);
                GGML_ASSERT(copied==bytes);consume(&batch,i,window);qwen_app_model_source_chunk_completed();
            }
        }
'''
    ops_text=ops_text[:begin]+replacement+ops_text[end:]
    ops_text=('#include <array>\n#include <algorithm>\n#include <cstddef>\n'
        'extern "C" bool qwen_app_small_rows(const void*const*,unsigned,std::size_t,void*,void(*)(void*,unsigned,const void*));\n')+ops_text
    result,jobs,sources=link(a.parent,a.out,dict(owner=(oc,owner),small_rows_ops=(command,ops_text)),
        [Path(__file__),io_path,reader,ROOT/'native/app/resident_small_rows.inc',a.out/'resident-mapped-source.private.h'])
    item['object']=record(a.out/'small_rows_ops.o');item['command']=' '.join(jobs['small_rows_ops'])
    io['sources'][item['source']]['patched_sha256']=sources['small_rows_ops']['sha256']
    manifest=a.out/'model-io.private.json';write_json(manifest,io)
    result['bounded_model_source_manifest']=record(manifest)
    result['bounded_model_source_overrides']=validate_overrides(manifest,Path(result['engine_receipt']['path']))
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_owner']=sources['owner']
    result['resident_small_rows']=dict(maximum_logical_rows=8,maximum_row_bytes=5120,
        existing_source_workers=4,extra_GPU_buffers=0,extra_scratch_bytes=0,
        overlap_and_adjacent_extents_merged=True,original_source_identity_and_reserves_preserved=True,
        candidate_default=False,actual_sources=sources,commands=jobs,native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_small_row_batch',
        original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,
        cache_slots=1381,driver_unchanged=True,all_weight_payloads_unchanged=True,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
