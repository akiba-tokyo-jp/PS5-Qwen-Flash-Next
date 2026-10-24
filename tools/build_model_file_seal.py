#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a plan-bound CPU file-mode controller; never contact the console."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from model_transport import REMOTE_ROOT,exclusive_json
from transfer_model import validate_original_plan,sha
from resume_conversion import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','plan','qualified-recipe','out'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();cache=a.cache.resolve();workspace=a.workspace.resolve();out=a.out.resolve()
    assert out.is_relative_to(cache) and not out.exists()
    original=validate_original_plan(workspace,cache,a.plan.resolve());plan=original['plan']
    base=json.loads(a.qualified_recipe.read_text());assert base['missing_runtime_imports']==[] and base['unchanged_SHA_provider'] is True
    mutable=cache/'build/application-native/receipt.private.json'
    fixed=[r for r in base['source_inputs'] if Path(r['path']).resolve()!=mutable.resolve()]
    assert fixed==[record(r['path']) for r in fixed]
    expected_crt={'crt1-credential-preserving.o':'8e81fa5b9b8afef702dfd0f7000c908692653e3f5948d69069b5b7c63350e415',
        'patch-syscall-only.o':'096a53aae0289fd7395d8795804cb4de1af1b3407ffc1d58b642ffa7685fc6f1'}
    for name,digest in expected_crt.items():assert any(Path(r['path']).name==name and r['sha256']==digest for r in fixed)
    rows=[dict(path=REMOTE_ROOT+'/'+r['original']['path'],bytes=r['original']['bytes']) for r in plan['files']]
    rows.append(dict(path=REMOTE_ROOT+'/model-receipt.json',bytes=len(original['receipt_bytes'])))
    assert len(rows)==77 and len({r['path'] for r in rows})==77
    out.mkdir();(out/'tmp').mkdir();nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-model-file-seal-'+nonce
    header=out/'model_file_seal_context.h'
    text='#define SEAL_ROOT '+json.dumps(REMOTE_ROOT)+'\n#define SEAL_NONCE '+json.dumps(nonce)+'\n#define SEAL_LOG '+json.dumps(prefix+'.log')+'\n'
    text+='static const struct expected_model_file expected_files[]={\n'
    text+=''.join('{'+json.dumps(r['path'])+',UINT64_C('+str(r['bytes'])+')},\n' for r in rows)+'};\n'
    header.write_text(text,encoding='utf-8',newline='\n')
    old=a.qualified_recipe.resolve().parent
    native,link=[[x.replace(str(old),str(out)) for x in c] for c in base['commands'][1:]]
    source=ROOT/'native/qwen_flash_next/model_file_seal.c';obj=out/'model-file-seal.o';artifact=out/'model-file-seal.elf'
    native[native.index('-c')+1]=str(source);native[native.index('-o')+1]=str(obj)
    index=next(i for i,x in enumerate(link) if Path(x).name==Path(base['object']['path']).name)
    link[index]=str(obj);link[link.index('-o')+1]=str(artifact)
    host=workspace/'toolchain/msys-clang64/clang64/bin';test=ROOT/'tests/model_file_seal.c';stub=ROOT/'tests/stubs/model_file_seal_stubs.h'
    executable=out/'model-file-seal-host.exe'
    host_command=[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'tests/stubs'),'-I',str(out),str(test),'-o',str(executable)]
    paths=[Path(__file__),source,test,stub,header,a.qualified_recipe.resolve(),a.plan.resolve(),Path(native[0]),Path(link[0]),Path(host_command[0])]
    paths += [Path(r['path']) for r in fixed]
    frozen=[record(path) for path in sorted(set(paths))]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(out/'tmp'),TEMP=str(out/'tmp'))
    for label,command in (('host-compile',host_command),('host-checks',[str(executable)]),('native-compile',native),('native-link',link)):
        result=subprocess.run(command,env=env,capture_output=True,timeout=120)
        (out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(label+' failed: '+result.stderr.decode(errors='replace'))
    llvm=Path(native[0]).parent;nm=llvm/'llvm-nm.exe'
    raw=subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True,timeout=30)
    names={line.split()[0] for line in raw.splitlines() if line.split()}
    assert not any(re.search(r'(sceAgc|sceSystemService|ptrace|mmap|mprotect|kernel_set_|kernel_copy|chown|chmod$|setuid|seteuid|unlink|rename)',name) for name in names if name!='fchmod')
    assert 'fchmod' in names
    exports={}
    for row in fixed:
        module=Path(row['path'])
        if module.suffix!='.so' or module.name.endswith('_stub_weak.so'):continue
        defined=subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(module)],text=True,timeout=30)
        for line in defined.splitlines():
            if line.split():exports.setdefault(line.split()[0],module.name)
    assert names<=exports.keys(),names-exports.keys()
    assert frozen==[record(r['path']) for r in frozen]
    exclusive_json(out/'manifest.private.json',dict(schema='ps5-qwen-model-file-seal-build-v1',nonce=nonce,source=record(source),
        artifact=record(artifact),header=record(header),sources=frozen,qualified_recipe=record(a.qualified_recipe),
        plan=record(a.plan),expected_files=rows,maximum_file_mode_changes=77,required_UID=0,required_GID=0,required_mode='0644',
        remote_root=REMOTE_ROOT,remote_elf=prefix+'.elf',remote_log=prefix+'.log',argument='--seal-model-files',
        actual_runtime_imports={n:exports[n] for n in sorted(names)},missing_runtime_imports=[],host_checks=7,
        commands=[host_command,native,link],payload_reads=0,title_launches=0,GPU_calls=0,console_access=False))
    print(json.dumps(dict(controller_built=True,host_checks_passed=7,actual_runtime_imports=len(names),maximum_file_mode_changes=77,console_requests=0)))

if __name__=='__main__':main()
