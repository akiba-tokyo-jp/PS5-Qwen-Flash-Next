#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a loaded-module-only CPU prerequisite; never connect or execute."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--qualified-build',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--probe-kind',choices=('loaded','paths-and-samples'),default='loaded')
    p.add_argument('--bundle-proof',type=Path)
    a=p.parse_args();m=json.loads(a.qualified_build.read_text());base=a.qualified_build.parent
    if m.get('GPU_calls')!=0 or m.get('title_launches')!=0 or m.get('full_file_hashes')!=11:
        raise ValueError('Actual final native readback donor required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-AMPR-discovery-'+nonce
    header=(base/'recovery_context.h').read_text()
    header,n=re.subn(r'^#define RECOVERY_NONCE .*$', '#define RECOVERY_NONCE '+json.dumps(nonce),header,flags=re.M);assert n==1
    header,n=re.subn(r'^#define RECOVERY_LOG .*$', '#define RECOVERY_LOG '+json.dumps(prefix+'.log'),header,flags=re.M);assert n==1
    (a.out/'recovery_context.h').write_text(header,newline='\n')
    text=(base/'files.h').read_text();rows=re.findall(r'^\{"[^\"]+",\d+ULL,"[0-9a-f]{64}"\},$',text,re.M)
    assert len(rows)==11
    files='struct file_check {const char*path;uint64_t bytes;const char*hash;};\nstatic const struct file_check files[]={\n'+'\n'.join(rows[:6])+'\n};\n'
    (a.out/'current_files.h').write_text(files,newline='\n')
    guard=(ROOT/'native/qwen_flash_next/recovery_guard.c').read_text()
    old='(k.ki_stat==SRUN||k.ki_stat==SSLEEP)';assert guard.count(old)==1
    guard=guard.replace(old,'(k.ki_stat==SRUN||k.ki_stat==SSLEEP||(k.ki_stat==SLOCK&&!strcmp(expected->name,"SceShellCore")))')
    (a.out/'qualified_recovery_guard.c').write_text(guard,newline='\n')
    if a.probe_kind=='paths-and-samples':
        if not a.bundle_proof:raise ValueError('Actual current sealed triplet proof required')
        proof=json.loads(a.bundle_proof.read_text());parts=proof['parts']
        assert proof['completed'] and proof['per_part']==348 and proof['quantized_bits_unchanged']
        chosen=[parts[round(i*(len(parts)-1)/15)]for i in range(16)]
        header='#pragma once\n#define SAMPLE_OUTPUT '+json.dumps(prefix+'.samples.bin')+'\n'
        header+='struct sample_source {const char *path;uint64_t key[10];uint64_t offset;unsigned ordinal;};\nstatic const struct sample_source samples[]={\n'
        for part in chosen:
            assert len(part['identity'])==10 and part['identity'][5]==part['bytes']
            header+='{'+json.dumps(part['path'])+',{'+','.join(str(x)+'ULL'for x in part['identity'])+'},0ULL,'+str(part['first_Expert'])+'U},\n'
        header+='};\n';(a.out/'sample_sources.h').write_text(header,newline='\n')
    source=ROOT/'native/qwen_flash_next'/('ampr_capability_probe.c'if a.probe_kind=='loaded'else'ampr_path_sample_probe.c')
    commands=[[x.replace(str(base),str(a.out))for x in cmd]for cmd in m['commands']]
    commands[0][commands[0].index('-c')+1]=str(source)
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'build-{i}.private.log').write_bytes(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'moss-kernel-observer.elf';nm=Path(commands[0][0]).with_name('llvm-nm.exe')
    imports=subprocess.check_output([str(nm),'--undefined-only',str(a.out/'observer.o')],text=True)
    forbidden=r'\b(?:kill|ptrace|nmount|unmount|mmap|sceAgc\w*|sceKernelApr\w*|sceAmpr\w*|sceKernelLoadStartModule|sceSysmoduleLoadModuleInternal|kernel_set\w*|kernel_proc_set\w*)\b'
    if re.search(forbidden,imports):raise ValueError('Discovery must not submit, load, map or modify kernel/process state')
    value=dict(schema='ps5-qwen-AMPR-loaded-capability-build-v1',nonce=nonce,artifact=record(artifact),
        source=record(source),builder=record(__file__),inputs=[record(p)for p in a.out.glob('*.h')]+[record(a.out/'qualified_recovery_guard.c')],
        commands=commands,remote_elf=prefix+'.elf',remote_log=prefix+'.log',
        qualified_donor=record(a.qualified_build),CPU_only=True,module_loads=0,IO_submits=0,GPU_calls=0,title_launches=0,
        probe_kind=a.probe_kind)
    if a.probe_kind=='paths-and-samples':
        value.update(bundle_proof=record(a.bundle_proof),samples=[dict(source=p,source_offset=0,raw_bytes=1536000,padded_bytes=1540096)for p in chosen],
            remote_samples=prefix+'.samples.bin',sample_bytes=16*1540096)
    (a.out/'manifest.private.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(discovery_built=True,CPU_only=True,IO_submits=0,GPU_calls=0)))
if __name__=='__main__':main()
