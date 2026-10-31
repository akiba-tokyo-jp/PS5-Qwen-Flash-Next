#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire an executed, rejected precision payload outside all live/prepared maps."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1];TITLE='/data/ai/native-moss-image-sft/PPSA99190'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('retired-publication','retired-case','protected','prepared-publication','control','base-build','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();pub=json.loads(a.retired_publication.read_text());seal=json.loads(Path(pub['source_integrity']['path']).read_text());model=json.loads(Path(pub['candidate']['path']).read_text());case=json.loads((a.retired_case/'native-model-terminal.private.json').read_text());closed=json.loads((a.retired_case/'restored-complete.private.json').read_text());control=json.loads(a.control.read_text());base=json.loads(a.base_build.read_text())
    require(pub['completed']and case['completed']and closed['completed']and not closed['unknown_completion']and case['all_model_source_device_owners_positively_retired']and case['model_receipt_sha256']==seal['model_receipt_sha256']==pub['candidate']['sha256'],'Completed, closed candidate required')
    require(model['precision_candidate']in ('dense-Q4','router-Q8'),'Only unused non-Expert test overlays may be retired')
    protected=json.loads(a.protected.read_text())['physical'];prepared=json.loads(a.prepared_publication.read_text());ps=json.loads(Path(prepared['source_integrity']['path']).read_text());require(prepared['completed']and ps['source_directory']!=seal['source_directory'],'The prepared Expert candidate must be separate')
    protected +=[*ps['parts'],*ps['headers'],dict(path=ps['source_directory']+'/model-receipt.json',identity=ps['receipt_identity'])]
    selected=seal['parts'];require(0<len(selected)<=32 and all(x['path']not in{p['path']for p in protected}and (x['identity'][0],x['identity'][1])not in{(p['identity'][0],p['identity'][1])for p in protected}for x in selected),'Every target must be outside both live and prepared maps')
    # Complete host copies make this rejected test payload byte-for-byte recoverable.
    for row,native in zip(model['precision_overlay']['parts'],selected):
        require(record(row['path'])==row and row['bytes']==native['bytes']and row['sha256']==native['sha256'],'Retained exact host payload copy required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-retired-precision-'+nonce
    ident=lambda key:'{'+','.join(str(v)+'ULL'for v in key)+'}';canonical=lambda path:TITLE+path[5:]
    h=a.out/'obsolete-weight-plan.private.h';text='#pragma once\nstruct Protected{const char*path;std::array<std::uint64_t,10>identity;};\nstatic const Protected protected_files[]={'+','.join('{'+json.dumps(canonical(x['path']))+','+ident(x['identity'])+'}'for x in protected)+'};\n'
    text+='struct Obsolete{const char*path;std::uint64_t bytes;const char*sha256;std::array<std::uint64_t,10>identity;};\nstatic constexpr unsigned obsolete_count='+str(len(selected))+';\nstatic const Obsolete obsolete_files[]={'+','.join('{'+json.dumps(canonical(x['path']))+','+str(x['bytes'])+'ULL,'+json.dumps(x['sha256'])+','+ident(x['identity'])+'}'for x in selected)+'};\n'
    text+='static const char*obsolete_directory='+json.dumps(seal['canonical_source_directory'])+';\nstatic const char*control_path='+json.dumps(TITLE+'/eboot.bin')+';\nstatic constexpr std::uint64_t control_bytes='+str(control['bytes'])+'ULL;\nstatic const char*control_hash='+json.dumps(control['sha256'])+';\n';h.write_text(text,newline='\n')
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.base_build.parent/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.base_build.parent),str(a.out))for v in cmd]for cmd in base['commands']];source=ROOT/'native/qwen_flash_next/reclaim_obsolete_weights.cpp';commands[1][commands[1].index('-c')+1]=str(source)
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-2500:])
    artifact=a.out/'source-contention.elf';write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,control_SELF=control,protected_source_count=len(protected),retired_parts=len(selected),retired_bytes=sum(x['bytes']for x in selected),maximum_ftruncate_calls=len(selected),remote_elf=remote+'.elf',remote_log=remote+'.log',GPU_calls=0,title_launches=0,automatic_retries=0,inputs=[record(x)for x in (Path(__file__),source,h,a.retired_publication,a.retired_case/'native-model-terminal.private.json',a.retired_case/'restored-complete.private.json',a.protected,a.prepared_publication,a.control,a.base_build)]))
    print('Exact rejected payload retirement built; current, rollback and prepared sources protected.')

if __name__=='__main__':main()
