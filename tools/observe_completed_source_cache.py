#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect and retire resident cache only in positively completed model read ranges."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import urllib.parse
from build_performance_quantizer import record
from finalize_model_pread_observation import decode
from start_success_route import load,need,save
from success_case_control import ALIAS,build,complete,current_files,execute,lan_module


def ranges(current,trace_path):
    proof=load(trace_path);case=load(proof['case']['path']);terminal=load(case['terminal']['path']);closed=load(proof['closure']['path'])
    need(proof['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
        not closed['unknown_completion'] and all(record(proof[k]['path'])==proof[k] for k in ('case','closure','raw','native_audit')),
        'Exact already completed model source calls and positive ordinary closure required')
    rows=decode(Path(proof['raw']['path']).read_bytes(),load(proof['native_audit']['path']),
        {k:terminal[k] for k in ('run_id','pid','candidate_SELF_sha256','model_receipt_sha256')})
    source=current/'provenance/model-source-plan.private.json';bundle=current/'provenance/required-bundle-inputs.private.json'
    sources=load(source)['physical']+load(bundle)['rows'];known={}
    for row in sources:
        key=(row['identity'][1],row['bytes'])
        if key in known:need(known[key]==row,'Original immutable source identities must not be ambiguous')
        known[key]=row
    spans=defaultdict(list);calls=0;devices=set()
    for row in rows:
        if not row['candidate']:continue
        need(row['identity_equal'] and row['returned']==row['bytes'],'Only positively returned unchanged source ranges may be selected')
        key=(row['identity'][1],row['identity'][2]);need(key in known,'Every actual source read must bind a retained current input')
        source_row=known[key];expected=source_row['identity'];actual=row['identity']
        observed=tuple(actual[i] for i in (0,1,3,4,5,2,8,9,10,11));devices.add(observed[0])
        need(tuple(expected[1:])==observed[1:] and
            0<=row['offset']<row['offset']+row['bytes']<=source_row['bytes'] and not((row['offset']|row['bytes'])%16384),
            'Original source identity fields and aligned extent must match; only the authenticated title device may translate')
        spans[key].append((row['offset'],row['offset']+row['bytes']));calls+=1
    files=[];extents=[]
    for key,values in sorted(spans.items()):
        row=known[key];need(row['path'].startswith('/app0/') and '..' not in row['path'].split('/'),'One owned mounted source path required')
        index=len(files);files.append(dict(row,mounted_path=ALIAS+row['path'][5:]))
        merged=[]
        for begin,end in sorted(values):
            if merged and begin<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((begin,end))
        for begin,end in merged:
            while begin<end:
                size=min(8<<20,end-begin);extents.append(dict(file=index,offset=begin,bytes=size));begin+=size
    plan=load(Path(proof['case']['path']).parent/'case/plan.private.json')
    need(calls==3456 and len(files)==80 and len(devices)==1 and 1<=len(extents)<=4096 and
        load(plan['model_proof']['path'])['current_boot']==load(current/'active-console.private.json')['current_boot'],
        'One finite original current-boot cold-request source cohort and one title device required')
    return files,extents,[record(trace_path),record(source),record(bundle),proof['raw'],proof['closure']]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','trace-proof','API-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true')
    p.add_argument('--finalize-returned',action='store_true',help='Analyze only the already retired native helper and saved raw receipt')
    p.add_argument('--completed-scope',type=Path,action='append',default=[],help='Skip only the positively retired exact prefix; never repeat it')
    p.add_argument('--maximum-sync-calls',type=int,choices=(32,128),default=32)
    a=p.parse_args();need(sum((a.execute,a.collect,a.finalize_returned))<=1,'Submit once, collect the same operation, or finalize saved evidence')
    state=load(a.current/'active-console.private.json');API=load(a.API_proof)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'] and
        API['completed'] and API['ordinary_CPU_API_qualified'] and API['full_input_SHA_before_and_after'] and
        API['observations']['unmapped']==API['observations']['fd_closed']==1,'The ordinary CPU mapping API and positive idle ownership must be qualified')
    selected=current_files(a.current);files,extents,inputs=ranges(a.current,a.trace_proof)
    cursor=0
    for path in a.completed_scope:
        previous=load(path);intent=load(path.parent/'intent.private.json')
        need(previous['completed'] and previous['all_observed_mappings_and_FDs_positively_retired'] and
            previous['native']['helper_exited'] and previous['native']['helper_files_removed'] and
            intent['files']==files and intent['ranges']==extents and intent['boot']==state['current_boot'] and
            intent.get('starting_range_index',0)==cursor and 0<previous['observations']['scanned']<=len(extents)-cursor,
            'Only a positive exact original-range prefix may be reused without replay')
        cursor+=previous['observations']['scanned'];inputs.append(record(path))
    need(cursor<len(extents),'The exact source scope has already been completely scanned')
    need(a.maximum_sync_calls==32 or a.completed_scope,'A larger sequential batch requires the completed first32-call native scope')
    if not a.collect and not a.finalize_returned:
        a.out.mkdir(parents=True,exist_ok=False)
        context='''#include <sys/mman.h>
struct SourceCacheFile{const char*path;uint64_t identity[10];};
static const struct SourceCacheFile cache_files[]={FILES};
struct SourceCacheRange{unsigned file;uint64_t offset,bytes;};
static const struct SourceCacheRange cache_ranges[]={RANGES};
static uint32_t source_cache_free(void){uint32_t v=0;size_t n=4;return !sysctlbyname("vm.stats.vm0.v_free_count",&v,&n,0,0)&&n==4?v:0;}
static int source_cache_identity(const struct stat*s,const struct SourceCacheFile*f,dev_t mounted){
 const uint64_t*a=f->identity;return S_ISREG(s->st_mode)&&s->st_size>0&&!(s->st_mode&0022)&&
  ((uint64_t)s->st_dev==a[0]||s->st_dev==mounted)&&(uint64_t)s->st_ino==a[1]&&(uint64_t)s->st_mode==a[2]&&
  (uint64_t)s->st_uid==a[3]&&(uint64_t)s->st_gid==a[4]&&(uint64_t)s->st_size==a[5]&&
  (uint64_t)s->st_mtim.tv_sec==a[6]&&(uint64_t)s->st_mtim.tv_nsec==a[7]&&
  (uint64_t)s->st_ctim.tv_sec==a[8]&&(uint64_t)s->st_ctim.tv_nsec==a[9];
}
static int case_retire_completed_images(int*calls){
 const uint64_t guard=UINT64_C(0xd894ac657b021fe3);struct stat root;
 if(lstat(MOUNT,&root)||!S_ISDIR(root.st_mode))return 0;
 unsigned scanned=0,resident=0,remaining=0,invalidated=0;uint64_t scanned_bytes=0;
 uint32_t free_begin=source_cache_free();uint64_t begun=qwen_launch_now(NULL);int returned_error=0;
 for(unsigned index=FIRST_RANGE;index<sizeof(cache_ranges)/sizeof(cache_ranges[0]);++index){
  if(*calls>=MAXIMUM_SYNC_CALLS||source_cache_free()<1154||qwen_launch_now(NULL)-begun>UINT64_C(20000000000))break;
  const struct SourceCacheRange*r=cache_ranges+index;const struct SourceCacheFile*f=cache_files+r->file;
  struct stat before,after;int fd=open(f->path,O_RDONLY|O_NOFOLLOW);if(fd<0)return 0;
  if(fstat(fd,&before)||!source_cache_identity(&before,f,root.st_dev)){close(fd);return 0;}
  void*address=mmap(NULL,r->bytes,PROT_READ,MAP_SHARED,fd,(off_t)r->offset);
  if(address==MAP_FAILED){int error=errno;if(close(fd))return 0;report("SOURCE_CACHE_MAP_RETURNED index=%u error=%d",index,error);returned_error=1;break;}
  struct {uint64_t before;unsigned char pages[512];uint64_t after;} v={guard,{0},guard};
  int first=mincore(address,r->bytes,(char*)v.pages),second=-2,sync_rc=-2,sync_error=0;
  unsigned found=0,after_count=0;
  if(!first&&v.before==guard&&v.after==guard)for(unsigned i=0;i<r->bytes/16384;++i)found+=(v.pages[i]&1)!=0;
  if(found){errno=0;++*calls;sync_rc=msync(address,r->bytes,MS_SYNC|MS_INVALIDATE);sync_error=errno;
   memset(v.pages,0,sizeof(v.pages));second=mincore(address,r->bytes,(char*)v.pages);
   if(!second&&v.before==guard&&v.after==guard)for(unsigned i=0;i<r->bytes/16384;++i)after_count+=(v.pages[i]&1)!=0;}
  const int unmapped=!munmap(address,r->bytes);const int identity=!fstat(fd,&after)&&unchanged(&before,&after);
  const int closed=!close(fd);++scanned;scanned_bytes+=r->bytes;resident+=found;remaining+=after_count;
  if(found&&sync_rc==0&&second==0&&after_count<found)invalidated+=found-after_count;
  if(!report("SOURCE_CACHE_RANGE index=%u file=%u offset=%llu bytes=%llu resident=%u remaining=%u first_rc=%d sync_rc=%d sync_errno=%d second_rc=%d canaries=%d unmapped=%d fd_closed=%d identity_exact=%d free=%u",
   index,r->file,(unsigned long long)r->offset,(unsigned long long)r->bytes,found,after_count,first,sync_rc,sync_error,second,
   v.before==guard&&v.after==guard,unmapped,closed,identity,source_cache_free()))return 0;
  if(!unmapped||!closed||!identity||v.before!=guard||v.after!=guard)return 0;
  if(first||(found&&(sync_rc||second))){returned_error=1;break;}
 }
 return report("SOURCE_CACHE_COMPLETE scanned=%u total=%u scanned_bytes=%llu resident=%u remaining=%u invalidated=%u sync_calls=%d returned_error=%d free_before=%u free_after=%u source_writes=0 touched_mapping_bytes=0 GPU_calls=0",
  scanned,(unsigned)(sizeof(cache_ranges)/sizeof(cache_ranges[0])),(unsigned long long)scanned_bytes,resident,remaining,invalidated,*calls,returned_error,free_begin,source_cache_free());
}
'''.replace('FIRST_RANGE',str(cursor)).replace('MAXIMUM_SYNC_CALLS',str(a.maximum_sync_calls))
        file_rows=','.join('{'+json.dumps(row['mounted_path'])+',{'+','.join(str(x)+'ULL' for x in row['identity'])+'}}' for row in files)
        range_rows=','.join('{'+str(row['file'])+','+str(row['offset'])+'ULL,'+str(row['bytes'])+'ULL}' for row in extents)
        context=context.replace('FILES',file_rows).replace('RANGES',range_rows)
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        save(a.out/'intent.private.json',dict(inputs=inputs+[record(a.API_proof)],files=files,ranges=extents,boot=state['current_boot'],
            selected=selected,maximum_live_mapping_bytes=8<<20,maximum_sync_calls=a.maximum_sync_calls,maximum_scope_seconds=20,
            starting_range_index=cursor,completed_scopes_reused=[record(path) for path in a.completed_scope],
            only_previously_completed_original_read_ranges=True,source_writes=0,touched_mapping_bytes=0,global_cache_purge=False))
        if not a.execute:return
    else:
        intent=load(a.out/'intent.private.json');need(intent['boot']==state['current_boot'] and intent['selected']==selected and
            intent['files']==files and intent['ranges']==extents,'Only the same consumed source-cache scope may be collected')
        plan=load(a.out/'native/plan.private.json')
    if a.finalize_returned:
        result=load(a.out/'native/result.private.json')
        need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and
            record(result['raw']['path'])==result['raw'],'Only saved positive native retirement may be finalized without console calls')
    elif a.collect:
        lan=lan_module()
        need((a.out/'native/execution/execution.once.private.json').exists(),'Only the same submitted operation may be collected')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:result=execute(lan_module(),plan,a.out/'native',60)
    need(result['completed'] and result['operation_calls']<=a.maximum_sync_calls,'All actual CPU mappings/fds and the helper must positively retire')
    rows=re.findall(rb'SOURCE_CACHE_COMPLETE (.*)',Path(result['raw']['path']).read_bytes());need(len(rows)==1,'One exact complete range receipt required')
    observations={k.decode():int(v) for k,v in re.findall(rb'\b([A-Za-z_]+)=(-?\d+)',rows[0])}
    save(a.out/'result.private.json',dict(completed=True,native=result,observations=observations,
        all_observed_mappings_and_FDs_positively_retired=True,source_writes=0,global_cache_purge=False,
        only_actual_completed_source_ranges=True,full_scope_scanned=cursor+observations['scanned']==len(extents),
        starting_range_index=cursor,remaining_ranges=len(extents)-cursor-observations['scanned'],
        model_launch_admission=False,exclusive_global_RAM_gain_claimed=False))
    print(dict(completed=True,observations=observations,model_launch_admission=False))


if __name__=='__main__':main()
