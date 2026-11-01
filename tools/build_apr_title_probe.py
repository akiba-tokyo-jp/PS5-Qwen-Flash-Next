#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a GPU-free registered-title diagnostic using the qualified native CRT."""
import argparse,base64,hashlib,json,os,re,secrets,struct,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
def title_visible_path(physical):
    prefix='/data/ai/native-moss-image-sft/PPSA99190/'
    if not physical.startswith(prefix):raise ValueError('Source must belong to the existing registered title mount')
    relative=physical[len(prefix):]
    if not relative or any(x in('', '.', '..')for x in relative.split('/')):raise ValueError('Canonical source path required')
    return '/app0/'+relative
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('normal','package','bindings','bundle-proof','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.normal.read_text());package=json.loads(a.package.read_text());bindings=json.loads(a.bindings.read_text());bundle=json.loads(a.bundle_proof.read_text())
    if not bindings['completed']or not bindings['helper_exited']:raise ValueError('Completed exact-NID observation required')
    if not all(r['matches_exact']=='1'for r in bindings['SDK']if 1<=int(r['index'])<=8):raise ValueError('Actual native kernel binding required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16)
    context=dict(APR_TITLE_NONCE=nonce,APR_TITLE_LOG='/app0/qwen-runtime/apr-title-'+nonce+'.log',
        APR_CONTROL_FILE='/app0/qwen-runtime/apr-control-'+nonce+'.bin',APR_EXPERT_FILE=title_visible_path(bundle['parts'][0]['path']))
    (a.out/'apr_title_context.h').write_text(''.join('#define '+k+' '+json.dumps(v)+'\n'for k,v in context.items())+
        '#define APR_BOOT_SEC 1793526511LL\n#define APR_BOOT_USEC 650440LL\n',newline='\n')
    rows=['{'+json.dumps(r['name'])+','+json.dumps(r['nid'])+'},'for r in bindings['names']]
    digest=hashlib.sha1(b'__error'+bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')).digest()[:8][::-1]
    rows.append('{"__error",'+json.dumps(base64.b64encode(digest,altchars=b'+-').decode().rstrip('='))+'},')
    (a.out/'binding_symbols.h').write_text('struct binding_symbol{const char*name;const char*nid;};\nstatic const struct binding_symbol binding_symbols[]={\n'+'\n'.join(rows)+'\n};\n',newline='\n')
    original=n['compile_commands'][0];cc=Path(original[0]);sdk=next(Path(original[i+1]).parent for i,v in enumerate(original[:-1])if v=='-isystem'and original[i+1].replace('\\','/').endswith('/target/include'))
    # Retain the exact target/toolchain flags while dropping optional C++ features.
    def compile(source,obj):
        cmd=original.copy();cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(obj.with_suffix('.d'))
        cmd=[{'-fexceptions':'-fno-exceptions','-fcxx-exceptions':'-fno-exceptions','-frtti':'-fno-rtti'}.get(x,x)for x in cmd]
        cmd[1:1]=['-I',str(a.out),'-I',str(ROOT/'native/app')];return cmd
    sources=[ROOT/'native/qwen_flash_next/apr_static_title_probe.cpp',ROOT/'native/app/native_crt.cpp']
    jobs=[compile(s,a.out/f'{i}.o')for i,s in enumerate(sources)]
    linker=Path(n['link_command'][0]);lib=sdk/'lib';native_layout=Path(n['link_command'][n['link_command'].index('-L')+1])
    libc=next(Path(x)for x in n['link_command']if x.endswith('libc.title.a'));builtins=next(Path(x)for x in n['link_command']if 'libclang_rt.builtins' in x)
    stubs=[lib/(x+'.so')for x in('libSceLibcInternal','libkernel','libSceSystemService')]
    image=a.out/'apr-title.pie.elf'
    link=[str(linker),'-m','elf_x86_64','-pie','-e','_start','-T',str(ROOT/'cmake/native-unwind.ld'),'-L',str(native_layout),'-L',str(lib),
        '--eh-frame-hdr','-z','max-page-size=0x4000','--hash-style=gnu','--exclude-libs=ALL','--gc-sections','--threads=2','--icf=safe',
        '-Map='+str(a.out/'link.private.map'),'-o',str(image),str(a.out/'0.o'),str(a.out/'1.o'),'--start-group',
        str(lib/'libps5platform.a'),str(libc),str(builtins),'--end-group','--as-needed',*[str(x)for x in stubs]]
    tool=Path(package['format_tool']['path']);assert record(tool)==package['format_tool']
    jobs +=[link,[str(cc.with_name('llvm-objcopy.exe')),'--strip-debug',str(image),str(a.out/'stripped.elf')],
        [str(tool),'link','--in',str(a.out/'stripped.elf'),'--out',str(a.out/'eboot.elf'),*[v for s in stubs for v in('--stub',str(s))]],
        [str(tool),'self','--sign','--in',str(a.out/'eboot.elf'),'--out',str(a.out/'eboot.bin')],
        [str(tool),'self','--inspect','--file',str(a.out/'eboot.bin')],
        [str(tool),'self','--extract','--file',str(a.out/'eboot.bin'),'--out',str(a.out/'roundtrip.elf')]]
    frozen=[record(x)for x in sources+[ROOT/'native/app/apr_command_encoder.h',Path(__file__),a.normal,a.package,a.bindings,a.bundle_proof,*a.out.glob('*.h'),lib/'libps5platform.a',libc,builtins,*stubs,native_layout/'ps5-pie.ld',tool]]
    host=Path(package['format_tool_compile'][0]).parent
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'),PATH=str(host)+os.pathsep+str(cc.parent)+os.pathsep+os.environ.get('PATH',''))
    for i,cmd in enumerate(jobs):
        run=subprocess.run(cmd,capture_output=True,timeout=120,env=env)
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(f'Step {i} exited {run.returncode}: '+(run.stdout+run.stderr).decode(errors='replace')[-3500:])
    undefined=subprocess.check_output([str(cc.with_name('llvm-nm.exe')),'--undefined-only',str(image)],text=True)
    if re.search(r'\b(?:vk\w+|ggml_\w+|sceAgc\w+|sceGnm\w+|kill|ptrace|kernel_set\w+)\b',undefined):raise ValueError('GPU/engine/mutation import forbidden')
    before=bytearray((a.out/'eboot.elf').read_bytes());after=(a.out/'roundtrip.elf').read_bytes();before[18:20]=struct.pack('<H',0x3e)
    if before[7]in(0,3):before[7]=9
    if struct.unpack_from('<H',before,16)[0]==0:struct.pack_into('<H',before,16,2)
    phoff=struct.unpack_from('<Q',before,32)[0];phsize,phcount=struct.unpack_from('<HH',before,54)
    assert after[:phoff+phsize*phcount]==before[:phoff+phsize*phcount]
    checked=0
    for i in range(phcount):
        kind,_,offset,_,_,size=struct.unpack_from('<IIQQQQ',before,phoff+i*phsize)
        if kind in(1,2,0x61000000)and size:assert after[offset:offset+size]==before[offset:offset+size];checked+=1
    for row in frozen:assert record(row['path'])==row
    (a.out/'control.private.bin').write_bytes(bytes(((i*17+29)^(i>>8))&255 for i in range(16384)))
    result=dict(schema='ps5-APR-native-title-probe-v1',nonce=nonce,SELF=record(a.out/'eboot.bin'),artifact=record(image),commands=jobs,
        frozen_inputs=frozen,source=record(sources[0]),CRT=record(sources[1]),GPU_archives_linked=0,GPU_calls=0,model_loaded=False,
        APR_read_submits=0,native_writer_dry_run=True,writer_backend='public_source',system_binary_inputs=False,context=context,control=record(a.out/'control.private.bin'),
        integrity_verified=True,roundtrip_segments_verified=checked,driver_changed=False,CI_runs=0)
    (a.out/'manifest.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(native_title_built=True,SELF_bytes=result['SELF']['bytes'],GPU_archives_linked=0,APR_read_submits=0)))
if __name__=='__main__':main()
