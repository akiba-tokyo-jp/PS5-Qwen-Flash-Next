#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build finite retirement of exact old Q4 parts outside both retained models."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('selection','control','base-build','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();plan=json.loads(a.selection.read_text());control=json.loads(a.control.read_text());base=json.loads(a.base_build.read_text())
    require(plan['completed']and plan['native_changes']==0 and plan['total_bytes']>=24<<30,'Exact unused-part plan required')
    for row in (plan['protected_sources'],plan['original_Q4_proof']):require(record(row['path'])==row,'Original source provenance changed')
    q4=json.loads(Path(plan['original_Q4_proof']['path']).read_text());original=q4['original_receipt']
    require(record(original['path'])==original,'Original BF16 receipt changed')
    original_model=json.loads(Path(original['path']).read_text());source_root=Path(original['path']).parent
    original_stats=[]
    for f in original_model['files']:
        path=source_root/f['path'];st=path.stat();require(st.st_size==f['bytes'],'An original BF16 source is unavailable')
        original_stats.append(dict(path=str(path),bytes=st.st_size,mtime_ns=st.st_mtime_ns,inode=st.st_ino))
    protected=json.loads(Path(plan['protected_sources']['path']).read_text())['physical']
    paths={r['path']for r in protected};inodes={(r['identity'][0],r['identity'][1])for r in protected}
    root='/app0/expert-q4-5baa1a32373ca842a9cfc22ca5b6a583';title='/data/ai/native-moss-image-sft/PPSA99190'
    for row in plan['selected']:
        require(row['path'].startswith(root+'/')and row['path']not in paths and
                (row['identity'][0],row['identity'][1])not in inodes and
                row['bytes']==row['identity'][5]and row['identity'][2:5]==[0o100644,0,0],
                'Only original unreferenced root-owned Q4 parts may be retired')
    require(control['sha256']=='bd390b921eaf6cfee9057cfd01ab1b03ecc48b171c0501a2807b999375dcca49','Exact deployed control required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-obsolete-Q4-'+nonce
    identity=lambda k:'{'+','.join(str(v)+'ULL'for v in k)+'}'
    canonical=lambda path:title+path[5:]
    header='#pragma once\nstruct Protected{const char*path;std::array<std::uint64_t,10>identity;};\n'
    header+='static const Protected protected_files[]={'+','.join('{'+json.dumps(canonical(r['path']))+','+identity(r['identity'])+'}'for r in protected)+'};\n'
    header+='struct Obsolete{const char*path;std::uint64_t bytes;const char*sha256;std::array<std::uint64_t,10>identity;};\n'
    header+='static constexpr unsigned obsolete_count='+str(len(plan['selected']))+';\nstatic const Obsolete obsolete_files[]={'+','.join('{'+json.dumps(canonical(r['path']))+','+str(r['bytes'])+'ULL,'+json.dumps(r['sha256'])+','+identity(r['identity'])+'}'for r in plan['selected'])+'};\n'
    header+='static const char*obsolete_directory='+json.dumps(canonical(root))+';\n'
    header+='static const char*control_path='+json.dumps(title+'/eboot.bin')+';\nstatic constexpr std::uint64_t control_bytes='+str(control['bytes'])+'ULL;\nstatic const char*control_hash='+json.dumps(control['sha256'])+';\n'
    h=a.out/'obsolete-weight-plan.private.h';h.write_text(header,newline='\n')
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):
        (a.out/name).write_bytes((a.base_build.parent/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.base_build.parent),str(a.out))for v in command]for command in base['commands']]
    source=ROOT/'native/qwen_flash_next/reclaim_obsolete_weights.cpp';commands[1][commands[1].index('-c')+1]=str(source)
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe'
    imports={line.split()[0]for line in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if line.split()}
    require(not any(re.search('(sceAgc|LaunchApp|KillApp|ptrace|rename|unlink|chmod|chown|pwrite)',n)for n in imports),'Only the explicit existing-name retirement may write data')
    require('ftruncate'in imports,'The exact public ftruncate provider must be visible')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,
        selection=record(a.selection),original_BF16_receipt=original,original_host_file_stats=original_stats,
        protected_sources=plan['protected_sources'],control_SELF=control,retired_files=len(plan['selected']),retired_bytes=plan['total_bytes'],
        maximum_ftruncate_calls=len(plan['selected']),all_original_hashes_required_before_any_retirement=True,
        complete_host_Q4_archive_claimed=False,original_BF16_and_pinned_regeneration_recipe_retained=True,
        directory_entries_and_directory_identity_preserved=True,active_or_immediate_source_writes=0,
        remote_elf=remote+'.elf',remote_log=remote+'.log',owned_Direct_bytes=8<<20,
        maximum_executions=1,GPU_calls=0,title_launches=0,automatic_retries=0,imports=sorted(imports),
        inputs=[record(x)for x in (Path(__file__),source,h,a.selection,a.control,a.base_build,
             *[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])]))

if __name__=='__main__':main()
