#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build bound CPU observations or a once-only GPU-free title launcher."""
import argparse,base64,hashlib,json,os,re,secrets,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--qualified-build',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--probe-kind',choices=('loaded','paths-and-samples','bindings','title-launch'),default='loaded')
    p.add_argument('--bundle-proof',type=Path)
    p.add_argument('--services-from',type=Path);p.add_argument('--title-probe',type=Path)
    a=p.parse_args();m=json.loads(a.qualified_build.read_text());base=a.qualified_build.parent
    if m.get('GPU_calls')!=0 or m.get('title_launches')!=0 or m.get('full_file_hashes')!=11:
        raise ValueError('Actual final native readback donor required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-AMPR-discovery-'+nonce
    header=(base/'recovery_context.h').read_text()
    header,n=re.subn(r'^#define RECOVERY_NONCE .*$', '#define RECOVERY_NONCE '+json.dumps(nonce),header,flags=re.M);assert n==1
    header,n=re.subn(r'^#define RECOVERY_LOG .*$', '#define RECOVERY_LOG '+json.dumps(prefix+'.log'),header,flags=re.M);assert n==1
    if a.services_from:
        services=json.loads(a.services_from.read_text())['current_services'];latest=[r for r in services if r['phase']=='2']
        assert len(latest)==7 and all(r['found']=='1'and r['tracer']=='0'for r in latest)
        rows=['{'+json.dumps(r['name'])+f",{r['pid']},{r['ppid']},{r['uid']}U,{r['sec']}LL,{r['usec']}LL"+'},'for r in latest]
        header,n=re.subn(r'(static const struct expected_process expected_processes\[\]=\{\n).*?(\n\};)',lambda m:m[1]+'\n'.join(rows)+m[2],header,flags=re.S);assert n==1
    (a.out/'recovery_context.h').write_text(header,newline='\n')
    text=(base/'files.h').read_text();rows=re.findall(r'^\{"[^\"]+",\d+ULL,"[0-9a-f]{64}"\},$',text,re.M)
    assert len(rows)==11
    if a.probe_kind=='title-launch':
        if not a.title_probe or not a.services_from:raise ValueError('GPU-free title and current service binding required')
        title=json.loads(a.title_probe.read_text());assert title['GPU_archives_linked']==0 and title['APR_read_submits']==0 and title['integrity_verified']
        q=title['SELF'];root='/data/ai/native-moss-image-sft/PPSA99190'
        rows[0]='{'+json.dumps(root+'/eboot.bin')+','+str(q['bytes'])+'ULL,'+json.dumps(q['sha256'])+'},'
        control=title['control'];rows=rows[:6]+['{'+json.dumps(root+'/qwen-runtime/'+Path(title['context']['APR_CONTROL_FILE']).name)+','+str(control['bytes'])+'ULL,'+json.dumps(control['sha256'])+'},',
            '{'+json.dumps('/system_ex/app/PPSA99190/eboot.bin')+','+str(q['bytes'])+'ULL,'+json.dumps(q['sha256'])+'},']
    files='struct file_check {const char*path;uint64_t bytes;const char*hash;};\nstatic const struct file_check files[]={\n'+'\n'.join(rows if a.probe_kind=='title-launch'else rows[:6])+'\n};\n'
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
    if a.probe_kind=='bindings':
        names=('sceKernelDlsym','pread','sceKernelAioSubmitReadCommands',
            'sceKernelAprResolveFilepathsToIds','sceKernelAprGetFileSize','sceKernelAprGetFileStat',
            'sceKernelAprSubmitCommandBuffer','sceKernelAprSubmitCommandBufferAndGetResult','sceKernelAprWaitCommandBuffer',
            'sceAmprCommandBufferConstructor','sceAmprAprCommandBufferConstructor','sceAmprCommandBufferSetBuffer',
            'sceAmprAprCommandBufferReadFile','sceAmprCommandBufferWriteAddressOnCompletion',
            'sceAmprCommandBufferWriteKernelEventQueue_04_00')
        rows=[]
        for name in names:
            digest=hashlib.sha1(name.encode()+bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')).digest()[:8][::-1]
            nid=base64.b64encode(digest,altchars=b'+-').decode().rstrip('=');assert len(nid)==11
            rows.append('{'+json.dumps(name)+','+json.dumps(nid)+'},')
        (a.out/'binding_symbols.h').write_text('struct binding_symbol {const char*name;const char*nid;};\nstatic const struct binding_symbol binding_symbols[]={\n'+'\n'.join(rows)+'\n};\n',newline='\n')
    source=ROOT/'native/qwen_flash_next'/dict(loaded='ampr_capability_probe.c',bindings='apr_address_probe.c',**{'paths-and-samples':'ampr_path_sample_probe.c','title-launch':'apr_title_launch.c'})[a.probe_kind]
    commands=[[x.replace(str(base),str(a.out))for x in cmd]for cmd in m['commands']]
    commands[0][commands[0].index('-c')+1]=str(source)
    if a.probe_kind=='title-launch':commands[-1].append('-l:libSceUserService.so')
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'build-{i}.private.log').write_bytes(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'moss-kernel-observer.elf';nm=Path(commands[0][0]).with_name('llvm-nm.exe')
    imports=subprocess.check_output([str(nm),'--undefined-only',str(a.out/'observer.o')],text=True)
    forbidden=r'\b(?:kill|ptrace|nmount|unmount|mmap|sceAgc\w*|sceKernelApr\w*|sceAmpr\w*|sceKernelLoadStartModule|sceSysmoduleLoadModuleInternal|kernel_set\w*|kernel_proc_set\w*)\b'
    if a.probe_kind!='title-launch':forbidden+=r'|\bsceSystemServiceLaunchApp\b'
    if re.search(forbidden,imports):raise ValueError('Discovery must not submit, load, map or modify kernel/process state')
    value=dict(schema='ps5-qwen-AMPR-prerequisite-build-v2',nonce=nonce,artifact=record(artifact),
        source=record(source),builder=record(__file__),inputs=[record(p)for p in a.out.glob('*.h')]+[record(a.out/'qualified_recovery_guard.c')],
        commands=commands,remote_elf=prefix+'.elf',remote_log=prefix+'.log',
        qualified_donor=record(a.qualified_build),CPU_only=True,module_loads=0,IO_submits=0,GPU_calls=0,title_launches=0,
        probe_kind=a.probe_kind)
    if a.probe_kind=='paths-and-samples':
        value.update(bundle_proof=record(a.bundle_proof),samples=[dict(source=p,source_offset=0,raw_bytes=1536000,padded_bytes=1540096)for p in chosen],
            remote_samples=prefix+'.samples.bin',sample_bytes=16*1540096)
    if a.services_from:value['services_observation']=record(a.services_from)
    if a.probe_kind=='title-launch':value.update(title_probe=record(a.title_probe),title_launches=1,explicit_module_loads=0,implicit_dependency='SceUserService')
    (a.out/'manifest.private.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(discovery_built=True,CPU_only=True,IO_submits=0,GPU_calls=0)))
if __name__=='__main__':main()
