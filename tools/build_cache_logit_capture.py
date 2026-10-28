#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export original warmup F32 rows after retirement for cross-cache comparison."""
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
  if record(row['path'])!=row:raise ValueError('Qualified cache input changed: '+row['path'])
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
 matches=[c.copy()for c in prior['compile_commands']if '-c'in c and 'resident-comparison'in Path(c[c.index('-c')+1]).name];assert len(matches)==1
 recipe=matches[0];original=Path(recipe[recipe.index('-c')+1]);text=original.read_text()
 assert text.count('const bool prefix_comparison=false;')==1
 at='        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);'
 terminal=text.index('{"schema","ps5-qwen-resident-additional-result-v1"}')
 insertion=text.rfind(at,0,terminal);assert insertion>=0 and terminal-insertion<300
 addition='''        // Persist controlled warmup rows only after every source/device owner retired.
        static_assert(sizeof(float)==4,"Original four-byte F32 representation required");
        static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"Little-endian native F32 required");
        const auto row_bytes=columns*sizeof(float);
        if(reference_rows!=23||!row_bytes||row_bytes>qwen_app::frame_write_window||ledger.live)
            throw std::runtime_error("Bounded retired original F32 reference required");
        qwen_app::require_resident_source_VM(qwen_app::observe_native_system_memory());
        void *F32_window=nullptr;
        if(posix_memalign(&F32_window,qwen_app::frame_write_alignment,qwen_app::frame_write_window)||
           !F32_window||!ps5_heap_owns(F32_window))throw std::runtime_error("Tracked F32 persistence window unavailable");
        Json F32_files=Json::array();
        for(std::size_t row=0;row<reference_rows;++row){
            const auto path=startup.admission_report+".warmup-F32-row-"+std::to_string(row);
            qwen_app::NativeFrameSink sink(path,true,metadata_direct_stage,metadata_direct_guard,
                qwen_app::FrameMetadataABI::native_descriptor,row_bytes);
            qwen_app::stream_direct_report(reference_logits.data()+row*columns,row_bytes,sink,F32_window);
            F32_files.push_back({{"row",row},{"path",path},{"bytes",row_bytes},{"positive_Direct_persistence_completed",true}});
        }
        free(F32_window);
        write_fresh_report(startup.admission_report+".warmup-F32",{{"schema","ps5-qwen-original-warmup-F32-v1"},
            {"pid",getpid()},{"run_id",run},{"active_cache_slots",cache_geometry.active_slots},{"rows",reference_rows},
            {"columns",columns},{"representation","IEEE754-F32-little-endian"},{"files",F32_files},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"source_and_device_owners_retired_before_write",true},{"device_ledger_live_bytes",0}});
'''
 text=text[:insertion]+addition+text[insertion:]
 generated=a.out/'resident-comparison-F32-capture.private.cpp';generated.write_text(text,newline='\n')
 obj=a.out/'resident-comparison-F32-capture.o';old=recipe[recipe.index('-o')+1];recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(original.parent)]
 link=prior['link_command'].copy();assert link.count(old)==1;link=[str(obj)if x==old else x for x in link];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+[record(x)for x in (Path(__file__),a.parent,original,generated,ROOT/'native/app/direct_report.h',ROOT/'native/app/direct_bmp_native.h')]
 for i,command in enumerate((recipe,link)):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen F32 capture source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[recipe],source_parent=record(a.parent),inputs_before=frozen+[record(obj)],
  resident_cache_F32_capture=dict(rows=23,maximum_row_bytes=1048576,source_and_device_retirement_required_before_write=True,source=record(generated)),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(cross_cache_F32_capture_built=True,GPU_calls_added=0,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
