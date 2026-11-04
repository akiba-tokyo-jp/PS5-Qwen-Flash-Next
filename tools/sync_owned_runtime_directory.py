#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Positively finish metadata writes for the one owned closed-output directory."""
import argparse
import json
from pathlib import Path
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,complete,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','retirement','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'One submission or collection phase required')
    retired=load(a.retirement);state=load(a.current/'active-console.private.json')
    need(retired['completed'] and retired['archived_and_retired_console_files']>0 and retired['original_runtime_directory_owner_restored'] and
        state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
        'Completed closed-output retirement and positive idle current deployment required')
    lan=lan_module()
    if a.collect:
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'Only collect the same existing operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),4<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);save(a.out/'intent.private.json',dict(retirement=record(a.retirement),
            action='fsync of the exact owned runtime directory after completed output deletion',directory_owner_changes=0,
            file_payload_writes=0,recursive_operations=0,model_or_GPU_operations=0))
        context=r'''
static int case_retire_completed_images(int*calls){
 const char*path=NEW_STAGE "/qwen-runtime";struct stat before,opened,after;
 if(lstat(path,&before)||!S_ISDIR(before.st_mode)||(before.st_mode&07777)!=0755||before.st_uid!=1||before.st_gid)return 0;
 if(!report("BEFORE owned_runtime_directory_open payload_writes=0 owner_changes=0"))return 0;
 int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);if(fd<0)return 0;
 if(fstat(fd,&opened)||!unchanged(&before,&opened)){(void)close(fd);return 0;}
 if(!report("BEFORE owned_runtime_directory_fsync")){(void)close(fd);return 0;}
 ++*calls;int rc=fsync(fd),saved=errno;
 int closed=close(fd);
 if(!report("RETURN owned_runtime_directory_fsync rc=%d errno=%d close_rc=%d",rc,saved,closed)||rc||closed)return 0;
 if(lstat(path,&after)||!unchanged(&before,&after))return 0;
 return report("OWNED_RUNTIME_DIRECTORY_SYNCED identity_owner_mode_unchanged=1 payload_writes=0 GPU_calls=0");
}
'''
        current=current_files(a.current);plan=build(a.workspace,a.mount_plan,current,current,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        if not a.execute:return
        result=execute(lan,plan,a.out/'native',observation_seconds=60)
    need(result['completed'] and result['operation_calls']==1,'One positive owned-directory sync and close required')
    save(a.out/'result.private.json',dict(completed=True,retirement=record(a.retirement),native=record(a.out/'native/result.private.json'),
        directory_syncs=1,directory_identity_owner_mode_unchanged=True,current_seven_natively_hashed=True,
        payload_writes=0,GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0,RAM_recovery_claimed=False))
    print(json.dumps(dict(completed=True,directory_syncs=1,owner_changes=0,GPU_calls=0,RAM_recovery_claimed=False)))


if __name__=='__main__':main()
