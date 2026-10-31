#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build bounded CPU-only requantization of exact current immutable Expert sources."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('model','source-map','protected','control','base-build','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();model=json.loads(a.model.read_text());maps=json.loads(a.source_map.read_text());protected=json.loads(a.protected.read_text())['physical'];control=json.loads(a.control.read_text());base=json.loads(a.base_build.read_text())
    require(record(a.model)['sha256']=='8b67b85e6cb2f3fd910e900b0299c3325d8717814f0ffab9ef505cab1dfc686b','Exact installed Q8 parent required')
    require(base['CPU_only']and base['owned_Direct_bytes']==8<<20 and len(protected)==559,'Qualified bounded CPU ABI and both protected source maps required')
    physical=maps['physical'];logical=maps['logical'];plans=maps['ranges']
    selected=[t for t in model['tensors']if re.fullmatch(r'blk\.\d+\.ffn_(gate|up)_exps\.weight',t['name'])and int(t['name'].split('.')[1])<48]
    require(len(selected)==96,'Complete Gate/Up selection required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);root=TITLE+'/expert-q2-'+nonce;remote='/data/ai/moss-qwen-Q2-repack-'+nonce
    canonical=lambda path:TITLE+path[5:] if path.startswith('/app0/')else path
    ident=lambda key:'{'+','.join(str(v)+'ULL'for v in key)+'}'
    header='#pragma once\nstruct Protected{const char*path;std::array<std::uint64_t,10>identity;};\nstatic const Protected protected_files[]={'+','.join('{'+json.dumps(canonical(r['path']))+','+ident(r['identity'])+'}'for r in protected)+'};\n'
    header+='struct RepackSlice{const char*path;std::array<std::uint64_t,10>identity;std::uint64_t logical,offset,bytes;};\nstruct RepackTensor{const char*name;const char*output;const char*input_sha256;const RepackSlice*source;unsigned slices;};\n'
    rows=[];bindings=[];protected_pairs={(r['path'],tuple(r['identity']))for r in protected}
    for i,t in enumerate(selected):
        require(t['type']=='Q2_K'and t['shape']==[2560,640,512]and t['bytes']==275251200,'Exact current Q2_K geometry required')
        file=next(f for f in logical if f['path'].endswith('/'+t['file']));ranges=next(q for q in plans if q['path']==file['path'])['segments'];slices=[]
        for logical_offset,length,physical_index,physical_offset in ranges:
            lo=max(t['offset'],logical_offset);hi=min(t['offset']+t['bytes'],logical_offset+length)
            if lo>=hi:continue
            source=physical[physical_index];require((source['path'],tuple(source['identity']))in protected_pairs,'Source escaped both protected model maps')
            slices.append(dict(path=canonical(source['path']),identity=source['identity'],logical=lo-t['offset'],offset=physical_offset+lo-logical_offset,bytes=hi-lo))
        cursor=0
        for row in slices:require(row['logical']==cursor,'Selected source coverage has a gap');cursor+=row['bytes']
        require(cursor==t['bytes'],'Complete current tensor coverage required')
        name='repack_slices_'+str(i)
        header+='static const RepackSlice '+name+'[]={'+','.join('{'+json.dumps(r['path'])+','+ident(r['identity'])+','+','.join(str(r[k])+'ULL'for k in ('logical','offset','bytes'))+'}'for r in slices)+'};\n'
        output=root+'/precision.part'+str(i)+'.bin';rows.append('{'+json.dumps(t['name'])+','+json.dumps(output)+','+json.dumps(t['payload_sha256'])+','+name+','+str(len(slices))+'}')
        bindings.append(dict(tensor=t,output=output,slices=slices))
    header+='static const RepackTensor repack_tensors[]={'+','.join(rows)+'};\nstatic const char*repack_root='+json.dumps(root)+';\n'
    header+='static const char*control_path='+json.dumps(TITLE+'/eboot.bin')+';\nstatic constexpr std::uint64_t control_bytes='+str(control['bytes'])+'ULL;\nstatic const char*control_hash='+json.dumps(control['sha256'])+';\n'
    h=a.out/'expert-repack-plan.private.h';h.write_text(header,newline='\n')
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.base_build.parent/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.base_build.parent),str(a.out))for v in command]for command in base['commands']]
    source=ROOT/'native/qwen_flash_next/expert_q2_repack_native.cpp';codec=ROOT/'tools/expert_q2_repack.c';commands[1][commands[1].index('-c')+1]=str(source)
    encoder=list(commands[0]);encoder[encoder.index('-c')+1]=str(codec);encoder[encoder.index('-o')+1]=str(a.out/'repack-codec.o')
    encoder=[x for x in encoder if not x.startswith('-std=')]+['-std=c11','-ffp-contract=off','-mf16c']
    commands.insert(-1,encoder);commands[-1].insert(commands[-1].index('-o'),str(a.out/'repack-codec.o'))
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe'
    imports={line.split()[0]for line in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if line.split()}
    require(not any(re.search('(sceAgc|LaunchApp|KillApp|ptrace|rename|unlink|ftruncate)',n)for n in imports),'Conversion may only create exclusive new files')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,
        model=record(a.model),source_map=record(a.source_map),protected=record(a.protected),control_SELF=control,bindings=bindings,
        new_directory=root,app0_directory='/app0/'+root.rsplit('/',1)[1],output_bytes=96*235929600,
        original_BF16_direct_quantization_claimed=False,conversion='current_Q2_K_to_F32_to_Q2_0_reference',
        remote_elf=remote+'.elf',remote_log=remote+'.log',owned_Direct_bytes=8<<20,
        maximum_executions=1,GPU_calls=0,title_launches=0,automatic_retries=0,imports=sorted(imports),
        inputs=[record(x)for x in (Path(__file__),source,codec,h,a.model,a.source_map,a.protected,a.control,a.base_build,
          *[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])]))
    print('Exact native current-weight Q2 repack built; no console execution.')

if __name__=='__main__':main()
