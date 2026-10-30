#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a new-only immutable publication for shared-Q8 pack and receipt."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1];TITLE='/data/ai/native-moss-image-sft/PPSA99190'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','base-build','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();bound=json.loads(a.preparation.read_text());base=json.loads(a.base_build.read_text())
    require(bound['completed']and bound.get('GGUF_tensor_offsets_contiguous')is True and bound['selected_tensors']==144 and bound['saved_resident_payload_bytes']==221184000,'Complete shared-Q8 payloads and compact contiguous GGUF headers required')
    for row in (bound['parent'],bound['candidate'],bound['pack'],*base['inputs'],base['artifact']):require(record(row['path'])==row,'Publication ancestry changed')
    require(base['completed_build']and base['CPU_only']and base['owned_Direct_bytes']==8<<20,'Original bounded new-file CPU publisher required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);root=TITLE+'/expert-q2-'+nonce;remote='/data/ai/moss-qwen-shared-Q8-publish-'+nonce
    files=[]
    for i,local in enumerate((bound['pack'],bound['candidate'])):
        files.append(dict(local=local,source='/data/ai/moss-qwen-layout-'+nonce+'-512-'+str(i)+'.bin',destination=root+'/'+('resident-shared-Q8.bin'if not i else'model-receipt.json')))
    header=a.out/'resident_output_Q8_publish_plan.h'
    header.write_text('#pragma once\n#include <cstdint>\n#define OUTPUT_Q8_PUBLISH_NONCE '+json.dumps(nonce)+'\ninline constexpr const char*output_Q8_directory='+json.dumps(root)+';\nstruct OutputQ8PublicationFile{const char*source;const char*destination;std::uint64_t bytes;const char*sha256;};\ninline constexpr OutputQ8PublicationFile output_Q8_files[]={'+','.join('{'+json.dumps(f['source'])+','+json.dumps(f['destination'])+','+str(f['local']['bytes'])+'ULL,'+json.dumps(f['local']['sha256'])+'}'for f in files)+'};\n',newline='\n')
    source=(ROOT/'native/qwen_flash_next/resident_output_q8_publish.cpp').read_text()
    source=once(source,'for(unsigned i=0;i<3;++i)','for(unsigned i=0;i<2;++i)')
    source=once(source,'if(i<2)sha256_update(&whole,static_cast<unsigned char*>(window),n);','')
    source=once(source,'    need(digest(whole)==output_Q8_GGUF_SHA256,"Q8 complete concatenated GGUF SHA256 differs");\n    line("WHOLE_Q8_GGUF SHA256="+std::string(output_Q8_GGUF_SHA256)+" bytes=675430560");',
        '    line("SHARED_Q8_COMPLETE immutable_files=2 whole_file_SHA256_and_EOF=1 candidate_whole_GGUF_hash_claimed=0");')
    actual=a.out/'shared-Q8-publication.private.cpp';actual.write_text(source,newline='\n')
    for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/n).write_bytes((a.base_build.parent/n).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.base_build.parent),str(a.out))for v in c]for c in base['commands']]
    commands[1][commands[1].index('-c')+1]=str(actual)
    for i,c in enumerate(commands):
        run=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode()[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={r.split()[0]for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if r.split()}
    require(names<=base['runtime_imports'].keys(),'New unaudited CPU import: '+str(names-base['runtime_imports'].keys()))
    require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'CPU publication cannot delete originals, launch a title or use GPU')
    write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-resident-shared-Q8-publication-build-v1',completed_build=True,CPU_only=True,
        artifact=record(artifact),commands=commands,nonce=nonce,files=files,new_directory=root,app0_directory='/app0/'+root.rsplit('/',1)[1],
        candidate_receipt=bound['candidate'],base_receipt=bound['parent'],remote_elf=remote+'.elf',remote_log=remote+'.log',owned_Direct_bytes=8<<20,
        maximum_executions=1,automatic_retries=0,original_source_writes=0,GPU_calls=0,title_launches=0,
        inputs=[record(x)for x in (Path(__file__),a.preparation,a.base_build,header,actual,*[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])],runtime_imports={n:base['runtime_imports'][n]for n in sorted(names)}))
    print('New-only shared-Q8 CPU publisher built for two immutable files; no console operations.')
if __name__=='__main__':main()
