#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""GPU-free CPU probe with a pinned entropy codec and existing real samples."""
from pathlib import Path
import argparse,hashlib,json,os,secrets,struct,subprocess
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ('qualified-build','container','samples','codec-dir','out'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();OUT=a.out;OUT.mkdir(parents=True,exist_ok=False);(OUT/'tmp').mkdir()
def load(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',newline='\n')
parent=a.qualified_build;m=load(parent);base=parent.parent
if not m['CPU_only']or m['GPU_calls']or m['title_launches']:raise ValueError('A GPU-free qualified build is required')
nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-Kraken-CPU-'+nonce
header=(base/'recovery_context.h').read_text().replace(m['remote_log'],remote+'.log').replace(m['nonce'],nonce)
assert '#define RECOVERY_LOG '+json.dumps(remote+'.log')in header
(OUT/'recovery_context.h').write_text(header)
for name in('current_files.h','qualified_recovery_guard.c'):(OUT/name).write_bytes((base/name).read_bytes())
container=a.container;encoded=container.read_bytes();meta=load(a.samples);sources=meta['samples']
records=[];pos=0
while pos<len(encoded):
    assert encoded[pos:pos+8]==b'QKRK001\0';version,count,raw,padded=struct.unpack_from('<IIII',encoded,pos+8);assert(version,count,raw)==(1,12,1536000)
    assert 0<padded<=1540096 and padded%4096==0 and pos+padded<=len(encoded)
    blocks=[]
    for i in range(count):
        offset,stored,n,flags,first=struct.unpack_from('<qiiii',encoded,pos+32+i*24);assert flags==0 and 0<stored<=n<=131072 and 32+count*24<=offset and offset+stored<=padded
        blocks.append((offset,stored,n,flags))
    assert sum(x[2]for x in blocks)==raw and all(a[0]+a[1]<=b[0]for a,b in zip(blocks,blocks[1:]))
    records.append(dict(offset=pos,padded=padded,blocks=blocks));pos+=padded
assert pos==len(encoded)and len(records)==len(sources)==16
context='#pragma once\n#include <stdint.h>\n#define KRAKEN_SOURCE '+json.dumps(remote+'.bin')+'\n#define KRAKEN_SOURCE_BYTES '+str(len(encoded))+'ULL\n#define KRAKEN_SOURCE_SHA256 '+json.dumps(hashlib.sha256(encoded).hexdigest())+'\n'
context+='struct kraken_chunk{uint32_t offset,stored,raw,flags;};\nstruct kraken_sample{const char*path;uint64_t key[10];uint64_t source_offset,compressed_offset;uint32_t compressed_padded;const char*raw_SHA256;struct kraken_chunk chunks[12];};\nstatic const struct kraken_sample kraken_samples[]={\n'
for sample,entry in zip(sources,records):
    original=sample['source'];source=original['source'];assert len(source['identity'])==10
    context+='{'+json.dumps(source['path'])+',{'+','.join(str(x)+'ULL'for x in source['identity'])+'},'+str(original['source_offset'])+'ULL,'+str(entry['offset'])+'ULL,'+str(entry['padded'])+'U,'+json.dumps(sample['original_raw_SHA256'])+',{'+','.join('{'+','.join(str(x)+'U'for x in b)+'}'for b in entry['blocks'])+'}},\n'
context+='};\n';(OUT/'kraken_probe_inputs.h').write_text(context)
codec=a.codec_dir;(OUT/'kraken-core.cpp').write_bytes((codec/'kraken-core.cpp').read_bytes())
portable=(codec/'stdafx.h').read_text().replace('<cstdint>','<stdint.h>').replace('<cstdio>','<stdio.h>').replace('<cstdlib>','<stdlib.h>').replace('<cstring>','<string.h>').replace('<cassert>','<assert.h>')
(OUT/'stdafx.h').write_text(portable)
root_source=ROOT/'native/qwen_flash_next/kraken_cpu_probe.c';body_source=ROOT/'native/qwen_flash_next/kraken_cpu_benchmark.cpp';adapter=ROOT/'native/app/kraken_entropy_codec.cpp'
for source in(root_source,body_source,adapter):(OUT/source.name).write_bytes(source.read_bytes())
commands=[];c=m['commands'][0].copy()
c=[x.replace(str(base),str(OUT))for x in c];c[c.index('-c')+1]=str(OUT/root_source.name);c[c.index('-o')+1]=str(OUT/'observer.o');commands.append(c)
for source,target,upstream in[(OUT/body_source.name,'bench.o',False),(OUT/adapter.name,'adapter.o',False),(OUT/'kraken-core.cpp','codec.o',True)]:
    cmd=c.copy();cmd[0]=str(Path(cmd[0]).with_name('clang++.exe'));cmd=[x for x in cmd if x!='-std=gnu11'];cmd[1:1]=['-std=c++17','-fno-exceptions','-fno-rtti','-msse4.1']
    if upstream:cmd=[x for x in cmd if x not in('-Wall','-Wextra','-Werror')]+['-w']
    cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(OUT/target);commands.append(cmd)
link=[x.replace(str(base),str(OUT))for x in m['commands'][1]]
at=link.index(str(OUT/'observer.o'))+1;link[at:at]=[str(OUT/x)for x in('bench.o','adapter.o','codec.o')];commands.append(link)
for i,cmd in enumerate(commands):
    result=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(OUT/'tmp'),TEMP=str(OUT/'tmp')))
    (OUT/f'build-{i}.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(str(i)+': '+(result.stdout+result.stderr).decode(errors='replace')[-4500:])
artifact=OUT/'moss-kernel-observer.elf';nm=Path(c[0]).with_name('llvm-nm.exe');undefined=subprocess.check_output([str(nm),'--undefined-only',str(artifact)],text=True)
if any(x in undefined for x in('sceAgc','ggml_','vkCreate','kernel_set','ptrace','kill','sceSystemServiceLaunch')):raise ValueError('Unapproved runtime dependency')
value=dict(schema='ps5-Kraken-CPU-probe-v1',nonce=nonce,artifact=record(artifact),source=record(root_source),builder=record(__file__),qualified_donor=record(parent),
    inputs=[record(a.container),record(a.samples)]+[record(p)for p in OUT.glob('*.h')]+[record(OUT/'qualified_recovery_guard.c'),record(body_source),record(adapter),record(codec/'source.private.json')]+[record(OUT/x)for x in(root_source.name,body_source.name,adapter.name,'kraken-core.cpp')],
    commands=commands,remote_elf=remote+'.elf',remote_log=remote+'.log',fixture=dict(local=record(container),remote=remote+'.bin'),module_loads=0,GPU_calls=0,title_launches=0,APR_calls=0,hardware_decoder=False,matched_reversal='ABBA',samples=16,upstream_revision='05038060aa68f9187ae9923b2388ca8db40e58d1',production_adoption_eligible=False)
save(OUT/'manifest.private.json',value);print(json.dumps(dict(built=True,samples=16,whole_Expert_reads=True,hardware_decoder=False)))
