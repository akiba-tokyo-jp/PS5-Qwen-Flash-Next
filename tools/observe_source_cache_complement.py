#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect only previously unobserved pages of retained application source files."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse
from build_performance_quantizer import record
from observe_completed_source_cache import ranges
from start_success_route import load,need,save
from success_case_control import ALIAS,build,complete,current_files,execute,lan_module


def plan_ranges(current,trace,completed):
    old_files,old_ranges,inputs=ranges(current,trace);cursor=0
    for path in completed:
        done=load(path);intent=load(path.parent/'intent.private.json')
        need(done['completed'] and done['all_observed_mappings_and_FDs_positively_retired'] and
            intent['files']==old_files and intent['ranges']==old_ranges and intent.get('starting_range_index',0)==cursor and
            done['native']['helper_exited'] and done['native']['helper_files_removed'],
            'Reuse the positively retired exact original-read prefix without replay')
        cursor+=done['observations']['scanned'];inputs.append(record(path))
    need(cursor==len(old_ranges),'All original read ranges must already be scanned and retired')
    known={};occupied={}
    for row in old_ranges:
        source=old_files[row['file']];key=(source['identity'][1],source['bytes'])
        occupied.setdefault(key,[]).append((row['offset'],row['offset']+row['bytes']))
    for source in (current/'provenance/model-source-plan.private.json',current/'provenance/required-bundle-inputs.private.json'):
        data=load(source);inputs.append(record(source))
        for row in data.get('physical',data.get('rows',[])):
            key=(row['identity'][1],row['bytes'])
            if key in known:need(known[key]['identity']==row['identity'],'Retained source identities must not conflict')
            else:known[key]=row
    files=[];windows=[]
    for key,row in sorted(known.items()):
        need(row['path'].startswith('/app0/') and '..' not in row['path'].split('/') and len(row['identity'])==10 and
            row['bytes']==row['identity'][5] and row['bytes']>0,'Only original retained owned file extents are eligible')
        index=len(files);files.append(dict(row,mounted_path=ALIAS+row['path'][5:]))
        end=row['bytes']//16384*16384;cursor=0;gaps=[]
        for start,finish in sorted(occupied.get(key,[])):
            if start>cursor:gaps.append((cursor,min(start,end)))
            cursor=max(cursor,finish)
        if cursor<end:gaps.append((cursor,end))
        for start,finish in gaps:
            while start<finish:
                size=min(64<<20,finish-start)
                if size>0:windows.append(dict(file=index,offset=start,bytes=size))
                start+=size
    need(1<=len(files)<=1024 and 1<=len(windows)<=16384,'One bounded application-source complement required')
    return files,windows,inputs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','trace-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--completed-read-scope',type=Path,action='append',required=True)
    p.add_argument('--completed-complement',type=Path,action='append',default=[])
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true')
    a=p.parse_args();need(not(a.execute and a.collect),'Submit once or collect the same exact helper')
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle model/source/device ownership required')
    files,windows,inputs=plan_ranges(a.current,a.trace_proof,a.completed_read_scope);first=0
    for path in a.completed_complement:
        old=load(path);intent=load(path.parent/'intent.private.json')
        need(old['completed'] and old['all_mappings_and_FDs_positively_retired'] and old['starting_window']==first and
            intent['files']==files and intent['windows']==windows and intent['boot']==state['current_boot'],
            'Only positively completed identical complement windows may be skipped')
        first+=old['observations']['scanned'];inputs.append(record(path))
    need(first<len(windows),'This complement has already completed; never repeat it')
    selected=current_files(a.current)
    if not a.collect:
        a.out.mkdir(parents=True,exist_ok=False)
        context='''#include <sys/mman.h>
struct CacheSource{const char*path;uint64_t identity[10];};static const struct CacheSource sources[]={FILES};
struct CacheWindow{unsigned file;uint64_t offset,bytes;};static const struct CacheWindow windows[]={WINDOWS};
static uint32_t complement_free(void){uint32_t v=0;size_t n=4;return !sysctlbyname("vm.stats.vm0.v_free_count",&v,&n,0,0)&&n==4?v:0;}
static int complement_identity(const struct stat*s,const struct CacheSource*f,dev_t mounted){const uint64_t*a=f->identity;
 return S_ISREG(s->st_mode)&&!(s->st_mode&0022)&&((uint64_t)s->st_dev==a[0]||s->st_dev==mounted)&&
 (uint64_t)s->st_ino==a[1]&&(uint64_t)s->st_mode==a[2]&&(uint64_t)s->st_uid==a[3]&&(uint64_t)s->st_gid==a[4]&&
 (uint64_t)s->st_size==a[5]&&(uint64_t)s->st_mtim.tv_sec==a[6]&&(uint64_t)s->st_mtim.tv_nsec==a[7]&&
 (uint64_t)s->st_ctim.tv_sec==a[8]&&(uint64_t)s->st_ctim.tv_nsec==a[9];}
static int case_retire_completed_images(int*calls){
 const uint64_t guard=UINT64_C(0x7821c4bd06ae5f93);struct stat root;
 if(lstat(MOUNT,&root)||!S_ISDIR(root.st_mode))return 0;
 uint64_t bytes=0,found_total=0,remaining_total=0;unsigned scanned=0;int error=0;
 const uint32_t free_before=complement_free();const uint64_t begun=qwen_launch_now(NULL);
 for(unsigned index=FIRST_WINDOW;index<sizeof(windows)/sizeof(windows[0]);++index){
  // A complete64MiB window needs at most eight sequential8MiB sync calls.
  if(*calls>120||complement_free()<1154||qwen_launch_now(NULL)-begun>UINT64_C(20000000000))break;
  const struct CacheWindow*w=windows+index;const struct CacheSource*f=sources+w->file;
  struct stat before,after;int fd=open(f->path,O_RDONLY|O_NOFOLLOW);if(fd<0)return 0;
  if(fstat(fd,&before)||!complement_identity(&before,f,root.st_dev)){close(fd);return 0;}
  void*address=mmap(NULL,w->bytes,PROT_READ,MAP_SHARED,fd,(off_t)w->offset);
  if(address==MAP_FAILED){error=errno;if(close(fd))return 0;report("COMPLEMENT_MAP_RETURNED index=%u error=%d",index,error);break;}
  struct {uint64_t before;unsigned char data[4096];uint64_t after;} pages={guard,{0},guard};
  int first_rc=mincore(address,w->bytes,(char*)pages.data);unsigned found_window=0,remaining_window=0;
  if(!first_rc&&pages.before==guard&&pages.after==guard){
   for(unsigned page=0;page<w->bytes/16384;){
    const unsigned count=w->bytes/16384-page<512?w->bytes/16384-page:512;unsigned found=0;
    for(unsigned i=0;i<count;++i)found+=(pages.data[page+i]&1)!=0;
    found_window+=found;
    if(found){
     struct {uint64_t before;unsigned char data[512];uint64_t after;} returned={guard,{0},guard};
     void*at=(unsigned char*)address+(uint64_t)page*16384;errno=0;++*calls;
     int rc=msync(at,(uint64_t)count*16384,MS_SYNC|MS_INVALIDATE),saved=errno;
     int sampled=mincore(at,(uint64_t)count*16384,(char*)returned.data);unsigned remaining=0;
     if(!sampled)for(unsigned i=0;i<count;++i)remaining+=(returned.data[i]&1)!=0;
     remaining_window+=remaining;
     if(!report("COMPLEMENT_SYNC window=%u page=%u pages=%u resident=%u remaining=%u rc=%d error=%d mincore_rc=%d canaries=%d free=%u",
      index,page,count,found,remaining,rc,saved,sampled,returned.before==guard&&returned.after==guard,complement_free()))return 0;
     if(rc||sampled||returned.before!=guard||returned.after!=guard){error=1;break;}
    }page+=count;
   }
  }else error=1;
  int unmapped=!munmap(address,w->bytes),identity=!fstat(fd,&after)&&unchanged(&before,&after),closed=!close(fd);
  if(!report("COMPLEMENT_WINDOW index=%u bytes=%llu first_rc=%d resident=%u remaining=%u canaries=%d unmapped=%d fd_closed=%d identity_exact=%d",
   index,(unsigned long long)w->bytes,first_rc,found_window,remaining_window,pages.before==guard&&pages.after==guard,unmapped,closed,identity))return 0;
  if(!unmapped||!identity||!closed||pages.before!=guard||pages.after!=guard)return 0;
  ++scanned;bytes+=w->bytes;found_total+=found_window;remaining_total+=remaining_window;if(error)break;
 }
 return report("COMPLEMENT_COMPLETE scanned=%u total=%u bytes=%llu resident=%llu remaining=%llu sync_calls=%d returned_error=%d free_before=%u free_after=%u source_writes=0 touched_mapping_bytes=0 GPU_calls=0",
  scanned,(unsigned)(sizeof(windows)/sizeof(windows[0])),(unsigned long long)bytes,(unsigned long long)found_total,
  (unsigned long long)remaining_total,*calls,error,free_before,complement_free());
}
'''.replace('FIRST_WINDOW',str(first))
        source_rows=','.join('{'+json.dumps(r['mounted_path'])+',{'+','.join(str(v)+'ULL' for v in r['identity'])+'}}' for r in files)
        window_rows=','.join('{'+str(r['file'])+','+str(r['offset'])+'ULL,'+str(r['bytes'])+'ULL}' for r in windows)
        context=context.replace('FILES',source_rows).replace('WINDOWS',window_rows)
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        save(a.out/'intent.private.json',dict(files=files,windows=windows,inputs=inputs,starting_window=first,boot=state['current_boot'],
            selected=selected,maximum_live_readonly_mapping_bytes=64<<20,maximum_sync_extent_bytes=8<<20,
            maximum_sync_calls=128,maximum_scope_seconds=20,original_read_ranges_excluded=True,source_writes=0,mapping_page_accesses=0,global_cache_purge=False))
        if not a.execute:return
    else:
        intent=load(a.out/'intent.private.json');need(intent['files']==files and intent['windows']==windows and
            intent['starting_window']==first and intent['selected']==selected and intent['boot']==state['current_boot'],'Only the same consumed complement may be collected')
        plan=load(a.out/'native/plan.private.json')
    lan=lan_module()
    if a.collect:
        need((a.out/'native/execution/execution.once.private.json').exists(),'Only collect the same submitted helper')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        native=complete(lan,plan,a.out/'native',raw,path)
    else:native=execute(lan,plan,a.out/'native',60)
    need(native['completed'] and native['operation_calls']<=128,'The actual helper and each readonly mapping/fd must retire positively')
    raw=Path(native['raw']['path']).read_bytes();rows=re.findall(rb'COMPLEMENT_COMPLETE (.*)',raw);need(len(rows)==1,'One exact complement completion required')
    observations={k.decode():int(v) for k,v in re.findall(rb'\b([A-Za-z_]+)=(-?\d+)',rows[0])}
    need(observations['returned_error']==0,'A returned API refusal ends this scope without any replay')
    save(a.out/'result.private.json',dict(completed=True,native=native,observations=observations,starting_window=first,
        all_mappings_and_FDs_positively_retired=True,remaining_windows=len(windows)-first-observations['scanned'],
        old_original_read_ranges_replayed=0,source_writes=0,global_cache_purge=False,model_launch_admission=False))
    print(dict(completed=True,observations=observations,remaining_windows=len(windows)-first-observations['scanned']))


if __name__=='__main__':main()
