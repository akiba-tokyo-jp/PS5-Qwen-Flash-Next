#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one read-only, identity-bound cache-invalidation experiment."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
CODE=r'''
#include <sys/mman.h>
static void reclaim_free(const char *phase){
 uint32_t free=0,min=0,reserved=0;size_t n=4;int a=sysctlbyname("vm.stats.vm0.v_free_count",&free,&n,0,0);
 n=4;int b=sysctlbyname("vm.stats.vm0.v_free_min",&min,&n,0,0);n=4;int c=sysctlbyname("vm.stats.vm0.v_free_reserved",&reserved,&n,0,0);
 report("PACK_CACHE_MEMORY phase=%s queries_ok=%d free=%u minimum=%u reserved=%u GPU_calls=0",phase,!a&&!b&&!c,free,min,reserved);
}
static int reclaim_key(const struct stat*s){
 uint64_t k[]={s->st_dev,s->st_ino,s->st_mode,s->st_uid,s->st_gid,s->st_size,s->st_mtim.tv_sec,s->st_mtim.tv_nsec,s->st_ctim.tv_sec,s->st_ctim.tv_nsec};
 return !memcmp(k,reclaim_identity,sizeof(k))&&S_ISREG(s->st_mode);
}
static void reclaim_closed_pack(void){
 struct stat before,after;reclaim_free("before_map");
 int fd=open(reclaim_path,O_RDONLY|O_NOFOLLOW);if(fd<0){report("PACK_CACHE_MAP admitted=0 errno=%d",errno);return;}
 if(reclaim_pending_upload){
  if(fstat(fd,&before)||!S_ISREG(before.st_mode)||(uint64_t)before.st_size!=reclaim_identity[5]){report("PENDING_SELF_FLUSH admitted=0");close(fd);return;}
  errno=0;int synced=fsync(fd),saved=errno;report("PENDING_SELF_FLUSH returned=1 rc=%d errno=%d",synced,saved);reclaim_free("after_fsync");
  if(synced||fstat(fd,&before)){close(fd);return;}
  uint64_t k[]={before.st_dev,before.st_ino,before.st_mode,before.st_uid,before.st_gid,before.st_size,before.st_mtim.tv_sec,before.st_mtim.tv_nsec,before.st_ctim.tv_sec,before.st_ctim.tv_nsec};memcpy(reclaim_identity,k,sizeof(k));
 }
 if(fstat(fd,&before)||!reclaim_key(&before)||lstat(reclaim_path,&after)||!reclaim_key(&after)){report("PACK_CACHE_IDENTITY refused=1");close(fd);return;}
 errno=0;void *p=mmap(0,reclaim_identity[5],PROT_READ,MAP_SHARED,fd,0);int saved=errno;
 if(p==MAP_FAILED){report("PACK_CACHE_MAP admitted=1 returned=0 errno=%d",saved);close(fd);return;}
 report("PACK_CACHE_MAP admitted=1 returned=1 read_only=1 bytes=%llu",(unsigned long long)reclaim_identity[5]);reclaim_free("after_map");
 errno=0;int rc=msync(p,reclaim_identity[5],MS_SYNC|MS_INVALIDATE);saved=errno;
 report("PACK_CACHE_INVALIDATE returned=1 rc=%d errno=%d source_write_calls=0",rc,saved);reclaim_free("after_invalidate");
 int unmapped=!munmap(p,reclaim_identity[5]);int identity=!fstat(fd,&after)&&reclaim_key(&after)&&!lstat(reclaim_path,&after)&&reclaim_key(&after);int closed=!close(fd);
 report("PACK_CACHE_FINAL virtual_mapping_released=%d descriptor_closed=%d sealed_identity_unchanged=%d GPU_calls=0",unmapped,closed,identity);reclaim_free("after_close");
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('template','out'):p.add_argument('--'+k,type=Path,required=True)
 group=p.add_mutually_exclusive_group(required=True);group.add_argument('--pack',type=Path);group.add_argument('--pending-upload',type=Path)
 a=p.parse_args();m=json.loads(a.template.read_text())
 if a.pack:
  pack=json.loads(a.pack.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired'],'Positive closed pack required');row=pack['output'];pending=False;input_path=a.pack
 else:
  upload=json.loads(a.pending_upload.read_text());returned=json.loads((a.pending_upload.parent/'transfer-returned.json').read_text());capture=upload['SELF'];require(returned['FTP_completed']and returned['bytes']==capture['bytes']and returned['sha256']==capture['sha256'],'Exact returned owned upload required');require(re.fullmatch(r'/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-[0-9]+\.bin',upload['remote']),'Only unpublished owned SELF allowed');row=dict(path=upload['remote'],bytes=capture['bytes'],sha256=capture['sha256'],identity=[0,0,0,0,0,capture['bytes'],0,0,0,0]);pending=True;input_path=a.pending_upload
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();base=a.template.parent;nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-pack-cache-'+nonce
 h=(base/'observer_context.h').read_text().replace(m['nonce'],nonce);h,n=re.subn(r'^#define OBSERVER_LOG_PATH .*$', '#define OBSERVER_LOG_PATH '+json.dumps(remote+'.log'),h,flags=re.M);require(n==1,'Exact journal binding required')
 (a.out/'observer_context.h').write_text(h,newline='\n');source=(base/'observer.c').read_text();marker='int main(int argc,char **argv){';require(source.count(marker)==1,'Exact observer entry required')
 constants='static const char *reclaim_path='+json.dumps(row['path'])+';\nstatic uint64_t reclaim_identity[]={'+','.join(map(str,row['identity']))+'};\nstatic const int reclaim_pending_upload='+str(int(pending))+';\n'
 source=source.replace(marker,constants+CODE+marker);marker='    int equal=first.fw==last.fw';require(source.count(marker)==1,'Actual idle snapshots required');source=source.replace(marker,'    reclaim_closed_pack();\n'+marker)
 (a.out/'observer.c').write_text(source,newline='\n');commands=[[x.replace(str(base),str(a.out))for x in c]for c in m['commands']]
 for i,c in enumerate(commands):
  r=subprocess.run(c,capture_output=True,timeout=90,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-2500:])
 write_json(a.out/'manifest.private.json',dict(completed_build=True,nonce=nonce,artifact=record(a.out/'moss-kernel-observer.elf'),remote_elf=remote+'.elf',remote_log=remote+'.log',argument='--observe',commands=commands,
  inputs=[record(__file__),record(a.template),record(input_path),record(a.out/'observer.c'),record(a.out/'observer_context.h')],expected_pack=row,owned_pending_upload=pending,CPU_only=True,title_launches=0,GPU_calls=0,OS_counter_writes=0,source_write_calls=0,automatic_retries=0))
 print('Closed immutable pack cache experiment built; no console operation')
if __name__=='__main__':main()
