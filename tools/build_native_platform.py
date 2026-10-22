#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build Qwen's native platform member on the host; never deploy or execute it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from driver_inputs import sha, validate_driver
from native_driver import read_archive, hashes, NATIVE_PLATFORM
ROOT=Path(__file__).resolve().parents[1]

def record(path):
    path=Path(path).resolve()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}

def build(args, selected, lock):
    workspace=args.workspace.resolve();out=args.out.resolve()
    original=json.loads(args.composition_manifest.read_text())
    donor=Path(original['archive_path'])
    if (original.get('schema')!='ps5-qwen-native-driver-candidate-v1' or original.get('selected_driver')!=selected or
        original.get('native_members_preserved')!=702 or original.get('base_archive_sha256')!=lock['native_platform_base']['base_archive_sha256'] or
        original.get('archive_sha256')!=lock['native_platform_base']['selected_composition_sha256'] or
        sha(donor)!=original['archive_sha256']):
        raise ValueError('An exact verified native composition is required')
    mesa=workspace/'vendor/PS5_Mesa'
    revision=subprocess.check_output(['git','-C',str(mesa),'rev-parse','HEAD'],text=True).strip()
    if revision!=lock['ps5_vulkan_inference']['mesa_revision']:
        raise ValueError('Native platform Mesa source revision mismatch')
    # Reuse the pinned Mesa recipe, including its generated configuration.
    sys.path.insert(0,str(args.driver_root/'driver/mesa'))
    from build_idle_marker import windows_argv
    database=workspace/'build/gpu_probe/radv-ps5-windows/compile_commands.json'
    rows=json.loads(database.read_text())
    row,=[r for r in rows if r['file'].replace('\\','/').endswith('src/amd/vulkan/winsys/ps5/radv_ps5_platform.c')]
    command=windows_argv(row['command'])
    if '--target=x86_64-sie-ps5' not in command or '-DNDEBUG' not in command:
        raise ValueError('Native platform compile recipe target mismatch')
    out.mkdir(parents=True,exist_ok=False)
    status=out/'operation-status.private.json'
    def phase(value):status.write_text(json.dumps(dict(phase=value,console_access=False,accepted_manifest_published=False))+'\n')
    phase('compiling_native_platform')
    compiler=workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
    archiver=compiler.with_name('llvm-ar.exe')
    command[0]=str(compiler)
    object_path=out/NATIVE_PLATFORM[0]
    dependency=out/'native-platform.d'
    command[command.index('-o')+1]=str(object_path)
    command[command.index('-c')+1]=str(ROOT/'native/driver/radv_ps5_platform_native.c')
    if '-MF' in command:command[command.index('-MF')+1]=str(dependency)
    else:command+=['-MMD','-MF',str(dependency)]
    command+=['-I'+str(ROOT/'native/driver'),'-I'+str(mesa/'src/amd/vulkan/winsys/ps5'),'-DPS5_AI_MOSS_TRIAL_10G=1']
    env=dict(os.environ,PATH=str(workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    source_inputs=[record(path)for path in sorted((ROOT/'native/driver').iterdir())if path.is_file()]
    # Get the actual include graph first so header changes cannot escape the receipt.
    scan=list(command);scan[scan.index('-c')]='-M'
    result=subprocess.run(scan,cwd=row['directory'],env=env,capture_output=True,timeout=120)
    (out/'headers.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
    text=dependency.read_text().replace('\\\n',' ')
    _,separator,tail=text.partition(': ')
    if not separator:raise ValueError('Native compiler dependency graph is unavailable')
    headers=[]
    for name in tail.split():
        path=Path(name)
        if not path.is_absolute():path=Path(row['directory'])/path
        headers.append(path.resolve())
    headers=sorted(set(headers))
    header_inputs=[record(path)for path in headers]
    before=[record(donor),record(database),record(compiler),record(archiver),record(args.composition_manifest)]
    result=subprocess.run(command,cwd=row['directory'],env=env,capture_output=True,timeout=120)
    (out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
    if header_inputs!=[record(path)for path in headers] or source_inputs!=[record(Path(row['path']))for row in source_inputs]:
        raise ValueError('Native platform source/header changed during compilation')
    phase('archiving_native_platform')
    archive=out/'libvulkan_radeon.qwen-native.a'
    shutil.copyfile(donor,archive)
    base=hashes(read_archive(donor))
    archive_command=[str(archiver),'r',str(archive),str(object_path)]
    result=subprocess.run(archive_command,env=env,capture_output=True,timeout=600)
    (out/'archive.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Native platform archive construction failed')
    phase('verifying_all_member_occurrences')
    after=hashes(read_archive(archive))
    if base.keys()!=after.keys() or {key for key in base if base[key]!=after[key]}!={NATIVE_PLATFORM}:
        raise ValueError('Native platform replacement changed unrelated members')
    if after[NATIVE_PLATFORM]!=sha(object_path):raise ValueError('Native platform object digest mismatch')
    if before!=[record(donor),record(database),record(compiler),record(archiver),record(args.composition_manifest)]:
        raise ValueError('Native platform build input changed')
    receipt=dict(schema='ps5-qwen-native-platform-build-v1',selected_driver=selected,
        composition_archive_sha256=original['archive_sha256'],archive_path=str(archive),archive_sha256=sha(archive),
        modified_members=[list(NATIVE_PLATFORM)],unmodified_members_preserved=703,
        native_source=source_inputs,native_headers=header_inputs,inputs_before_after=before,
        compile_command=command,archive_command=archive_command,frontend_qualification='host-only; console execution disabled',
        other_application_log_fallback=False,persistent_caches_disabled_required=True,
        console_access=False,GPU_executed=False,deployment_allowed=False,CI=False)
    (out/'manifest.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    status.write_text(json.dumps(dict(phase='completed',console_access=False,accepted_manifest_published=True))+'\n')
    print(json.dumps(dict(native_platform_build='passed',archive_sha256=receipt['archive_sha256'],
                         native_members_preserved=703,console_access=False)),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','driver-root','driver-manifest','composition-manifest','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();existed=out.exists()
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    selected=validate_driver(args.driver_root,args.driver_manifest,lock['ps5_vulkan_inference'])
    try:build(args,selected,lock)
    except BaseException as error:
        if not existed and out.is_dir():
            (out/'manifest.private.json').unlink(missing_ok=True)
            (out/'operation-status.private.json').write_text(json.dumps(dict(phase='failed',error_type=type(error).__name__,
                accepted_manifest_published=False,console_access=False))+'\n')
        raise
if __name__=='__main__':main()
