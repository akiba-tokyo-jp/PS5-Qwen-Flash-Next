#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test one owned readonly file range with synchronous cache invalidation."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse
from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load,need,save
from success_case_control import build,complete,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','closed-primitive','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true')
    p.add_argument('--execute-prepared',action='store_true',help='Use the identical unsubmitted host artifact after import classification')
    a=p.parse_args();need(sum((a.execute,a.collect,a.execute_prepared))<=1,'Submit once or collect the same exact helper')
    state=load(a.current/'active-console.private.json');closed=load(a.closed_primitive)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
        not state['unknown_completion'] and closed['completed'] and closed['CPU_probe_passed'] and
        closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'],
        'Only the completed model-free CPU file after ordinary restoration is eligible')
    selected=current_files(a.current)
    physical='/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/cold-rodata-7d212b9c884f5c77896de960.bin'
    digest='7d212b9c884f5c77896de960ae17cc341cda43b14d6a971f34ca29ebd4badf7f'
    if not a.collect and not a.execute_prepared:
        a.out.mkdir(parents=True,exist_ok=False)
        # This exact immutable input was fully checked by CPU65041. The first
        # native scope maps only its first1MiB, never faults or writes its pages.
        context='''#include <sys/mman.h>
static uint32_t file_cache_free(void){uint32_t v=0;size_t n=4;return !sysctlbyname("vm.stats.vm0.v_free_count",&v,&n,0,0)&&n==4?v:0;}
static int case_retire_completed_images(int*calls){
 const char*path=FILE_PATH;const uint64_t bytes=8388608,extent=1048576;
 struct stat original={0},before={0},after={0};int fd=-1;void*mapping=MAP_FAILED;
 int opened=0,mapped=0,first_rc=-2,second_rc=-2,sync_rc=-2,sync_error=0,unmapped=0,closed=0,identity=0;
 unsigned resident_before=0,resident_after=0;const uint64_t guard=UINT64_C(0xda87e951ab24c67f);
 struct {uint64_t before;unsigned char values[64];uint64_t after;} v={guard,{0},guard};
 uint32_t free_before=file_cache_free(),free_after=0;
 if(!free_before||free_before<1154||lstat(path,&original)||!S_ISREG(original.st_mode)||
    original.st_size!=(off_t)bytes||!original.st_ino||(original.st_mode&0022)||
    !qwen_launch_digest_matches(path,bytes,FILE_SHA))return 0;
 fd=open(path,O_RDONLY|O_NOFOLLOW);if(fd<0)return 0;
 if(fstat(fd,&before)||!unchanged(&original,&before))goto done;opened=1;
 mapping=mmap(NULL,extent,PROT_READ,MAP_SHARED,fd,0);
 if(mapping==MAP_FAILED)goto done;mapped=1;
 first_rc=mincore(mapping,extent,(char*)v.values);
 if(first_rc||v.before!=guard||v.after!=guard)goto done;
 for(unsigned i=0;i<64;++i)resident_before+=(v.values[i]&1)!=0;
 errno=0;++*calls;sync_rc=msync(mapping,extent,MS_SYNC|MS_INVALIDATE);sync_error=errno;
 memset(v.values,0,sizeof(v.values));second_rc=mincore(mapping,extent,(char*)v.values);
 if(!second_rc&&v.before==guard&&v.after==guard)for(unsigned i=0;i<64;++i)resident_after+=(v.values[i]&1)!=0;
done:
 if(mapping!=MAP_FAILED)unmapped=!munmap(mapping,extent);else unmapped=1;
 if(fd>=0){identity=opened&&!fstat(fd,&after)&&unchanged(&before,&after);closed=!close(fd);}else closed=1;
 identity=identity&&!lstat(path,&after)&&unchanged(&original,&after);
 free_after=file_cache_free();
 if(!report("OWNED_FILE_CACHE_RETURNED mapped=%d mincore_before_rc=%d sync_rc=%d sync_errno=%d mincore_after_rc=%d resident_before=%u resident_after=%u range_bytes=%llu free_before=%u free_after=%u canaries=%d unmapped=%d fd_closed=%d identity_exact=%d source_writes=0 GPU_calls=0",
  mapped,first_rc,sync_rc,sync_error,second_rc,resident_before,resident_after,(unsigned long long)extent,
  free_before,free_after,v.before==guard&&v.after==guard,unmapped,closed,identity))return 0;
 return unmapped&&closed&&identity&&v.before==guard&&v.after==guard&&qwen_launch_digest_matches(path,bytes,FILE_SHA);
}
'''.replace('FILE_PATH',json.dumps(physical)).replace('FILE_SHA',json.dumps(digest))
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',a.out/'native',completed_images_context=context)
    else:
        plan=load(a.out/'native/plan.private.json')
        need(plan['old_files']==plan['new_files']==selected and plan['operation']=='retire-completed-images' and
             record(plan['artifact']['path'])==plan['artifact'] and record(plan['context']['path'])==plan['context'],
             'Only the identical source-bound helper may be reused')
        if a.execute_prepared:need(not(a.out/'native/execution/execution.once.private.json').exists(),'Never resubmit an accepted operation')
    need('msync' in plan['imports'] and ('mmap' in plan['imports'] or 'mmap' in ELF(Path(plan['artifact']['path'])).symbols) and 'mincore' in plan['imports'] and
            not any(x in plan['imports'] for x in ('kernel_set','syscall','sceSystemServiceLaunchApp')),
            'Only resolved ordinary CPU mapping APIs may be imported')
    if not(a.out/'intent.private.json').exists():
        save(a.out/'intent.private.json',dict(closed_primitive=record(a.closed_primitive),boot=state['current_boot'],selected=selected,
            input_path=physical,input_bytes=8388608,input_sha256=digest,mapping_range_bytes=1048576,
            source_writes=0,touched_mapping_bytes=0,MS_SYNC=0,MS_INVALIDATE=2,automatic_retries=0,
            primary_reference='https://github.com/freebsd/freebsd-src/blob/releng/11.0/sys/vm/vm_mmap.c'))
    intent=load(a.out/'intent.private.json');need(intent['boot']==state['current_boot'] and intent['selected']==selected,'Exact same idle boot/deployment required')
    if not(a.execute or a.execute_prepared or a.collect):return
    lan=lan_module()
    if a.collect:
        need((a.out/'native/execution/execution.once.private.json').exists(),'Only the same submitted helper may be collected')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:result=execute(lan,plan,a.out/'native',60)
    need(result['completed'] and result['operation_calls']<=1,'One returned CPU range with positive helper retirement required')
    raw=Path(result['raw']['path']).read_bytes()
    row=re.findall(rb'OWNED_FILE_CACHE_RETURNED (.*)',raw);need(len(row)==1,'One complete native cache-range receipt required')
    values={key.decode():int(value) for key,value in re.findall(rb'([a-z_]+)=(-?\d+)',row[0])}
    need(values['unmapped']==values['fd_closed']==values['identity_exact']==values['canaries']==1,'Actual mapping/fd/identity must close positively')
    save(a.out/'result.private.json',dict(completed=True,native=result,observations=values,
        ordinary_CPU_API_qualified=values['mapped']==1 and values['mincore_before_rc']==values['sync_rc']==values['mincore_after_rc']==0,
        full_input_SHA_before_and_after=True,source_writes=0,mapping_pages_touched=0,model_GPU_operations=0,
        global_cache_purge=False,hardware_reclamation_guarantee_claimed=False,model_launch_admission=False))
    print(dict(completed=True,observations=values,model_launch_admission=False))


if __name__=='__main__':main()
