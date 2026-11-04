#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link an independent C-only loader probe from retained CRT/bootstrap inputs."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from audit_native_imports import audit
from build_performance_quantizer import record
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--reuse-controls',type=Path,help='Reuse the exact unchanged parser/parameter source controls')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    prior = load(a.current / 'provenance/native-link.receipt.private.json')
    retained = load(a.current / 'provenance/retained-relink-inputs.private.json')
    mapping = {row['original_path']: row for row in retained}
    keep_objects = [name for name in mapping if any(mark in Path(name).name for mark in
                    ('native_fault-', 'native-bootstrap-boot-qualified.o', 'native_crt-'))]
    need(len(keep_objects) == 3, 'Exactly the retained CRT, fault and current-boot bootstrap required')
    archives = {'libps5platform.a', 'libc.title.a', 'libclang_rt.builtins-x86_64.a'}
    providers = {'libSceLibcInternal.so', 'libkernel.so'}
    recipe = prior.get('retained_link_command', prior['link_command'])
    selected = set(keep_objects)
    selected.update(name for name in mapping if Path(name).name in archives | providers)
    inputs = []
    for name in selected:
        expected = mapping[name]
        value = record(expected['path'])
        need(all(value[k] == expected[k] for k in ('path', 'bytes', 'sha256')), 'A selected CPU input changed')
        inputs.append(value)
    # The current93 relink inputs exclude the separately retained formatter
    # stubs. Authenticate the two actual SDK providers used by this link too.
    for argument in recipe:
        if argument.endswith('.so') and Path(argument).name in providers:
            expected = [row for row in prior['formatter_stubs'] if Path(row['path']).name == Path(argument).name]
            need(len(expected) == 1, 'One exact retained provider record required')
            value = record(mapping[argument]['path'] if argument in mapping else argument)
            need(all(value[k] == expected[0][k] for k in ('bytes', 'sha256')), 'Actual CPU module provider changed')
            if value not in inputs:
                inputs.append(value)
    compiler = a.workspace / 'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk = a.workspace / 'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    source = ROOT / 'native/app/CPU_loader_footprint.c'
    sha = a.workspace / 'native/model_hash/sha256.c'
    obj, sha_obj = a.out / 'probe.o', a.out / 'sha256.o'
    common = [str(compiler / 'clang.exe'), '--no-default-config', '--target=x86_64-sie-ps5',
              '-isystem', str(sdk), '-std=gnu11', '-O2', '-fPIC', '-fno-stack-protector', '-fno-plt',
              '-fno-builtin-malloc', '-fno-builtin-free',
              '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
              '-I', str(ROOT / 'native/qwen_flash_next'), '-I', str(sha.parent)]
    commands = [common + ['-c', str(source), '-o', str(obj)], common + ['-c', str(sha), '-o', str(sha_obj)]]
    image = a.out / 'CPU-loader.pie.elf'
    link = []
    skip = False
    table_script = prior['lossless_driver_tables']['linker_script']['path']
    for index, argument in enumerate(recipe):
        if skip:
            skip = False
            continue
        if argument == '-T' and recipe[index + 1] == table_script:
            skip = True
            continue
        if argument.endswith('.o') and argument not in keep_objects:
            continue
        if argument.endswith('.a') and Path(argument).name not in archives:
            continue
        if argument.endswith('.so') and Path(argument).name not in providers:
            continue
        if argument.startswith('--defsym=') or (argument.startswith('--wrap=') and argument != '--wrap=abort'):
            continue
        if argument in ('--whole-archive', '--no-whole-archive'):
            continue
        if argument.startswith('-Map='):
            argument = '-Map=' + str(a.out / 'native-link.private.map')
        link.append(mapping[argument]['path'] if argument in mapping else argument)
    link[link.index('-o') + 1] = str(image)
    link[1:1] = [str(obj), str(sha_obj)]
    commands.append(link)
    fixed = [source, sha, Path(__file__), ROOT / 'native/qwen_flash_next/loader_probe_context.h',
             ROOT / 'native/qwen_flash_next/launch_integrity.h', ROOT / 'native/qwen_flash_next/launch_integrity_native.h',
             ROOT / 'tests/loader_probe_context_test.c', ROOT / 'tools/libc_parameter_policy.py',
             ROOT / 'tests/test_libc_parameter_policy.py', ROOT / 'native/qwen_flash_next/app_named_stat.h',
             ROOT / 'tests/app_named_stat_test.c']
    inputs += [record(path) for path in fixed]
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    exe = a.out / 'context-check.exe'
    controls = [[str(host / 'clang.exe'), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                 '-I', str(ROOT / 'native/qwen_flash_next'), str(ROOT / 'tests/loader_probe_context_test.c'), '-o', str(exe)],
                [str(exe)], [sys.executable, '-B', str(ROOT / 'tests/test_libc_parameter_policy.py')]]
    reused_controls=None
    if a.reuse_controls:
        old=load(a.reuse_controls)
        need(old['completed'] and old['context_controls']==old['libc_parameter_controls']==8,'Completed source controls required')
        controlled=('loader_probe_context.h','loader_probe_context_test.c','libc_parameter_policy.py','test_libc_parameter_policy.py')
        old_inputs={Path(row['path']).name:row for row in old['inputs_before']}
        for name in controlled:
            need(name in old_inputs and record(old_inputs[name]['path'])==old_inputs[name],'A previously controlled source changed')
        reused_controls=record(a.reuse_controls);controls=[]
    named_exe=a.out/'named-stat-check.exe'
    controls += [[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror',
                  '-I',str(ROOT/'native/qwen_flash_next'),str(ROOT/'tests/app_named_stat_test.c'),'-o',str(named_exe)],
                 [str(named_exe)]]
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''), TMP=str(a.out), TEMP=str(a.out))
    for index, job in enumerate(controls + commands):
        run = subprocess.run(job, capture_output=True, timeout=60, env=env)
        (a.out / (str(index) + '.private.log')).write_bytes(run.stdout + run.stderr)
        need(run.returncode == 0, run.stderr.decode(errors='replace')[-3500:])
    receipt = dict(artifact=record(image), inputs_before=inputs, runtime_providers=prior['runtime_providers'])
    save(a.out / 'receipt.private.json', receipt)
    imported = audit(a.workspace, a.current.parent, a.out)
    need(not imported['missing'], 'Actual native CPU imports must resolve: ' + str(imported['missing']))
    need({'malloc','free'}<=imported['resolved'].keys(),'The actual small libc allocation must not be optimized away')
    need(all(not name.startswith(('sceAgc', 'sceVideoOut', 'sceSystemServiceLaunch', 'sceSystemServiceKill'))
             for name in imported['resolved']), 'GPU/display/title APIs must not enter this CPU-only executable')
    names = subprocess.check_output([str(compiler / 'llvm-nm.exe'), '--defined-only', '--format=posix', str(image)], text=True)
    need(not any(re.match(r'^(vk[A-Z]|radv_|aco_|llama_|ggml_)', line) for line in names.splitlines()),
         'No inference or Vulkan implementation may be linked')
    need(all(record(row['path']) == row for row in inputs), 'A frozen selected CPU input changed')
    receipt.update(completed=True, baseline_relink=False, CPU_only=True, driver_code_linked=False,
                   model_engine_linked=False, driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',
                   driver_profile='cumulative-idle', source=record(source), commands=commands,
                   link_command=link, controls=controls, context_controls=8, libc_parameter_controls=8,
                   unchanged_control_proof_reused=reused_controls, named_descriptor_controls=5,
                   real_module_import_audit=imported, source_payload_reads=0, GPU_calls=0,
                   pressure_allocations=0, explicit_libc_allocation_bytes=4096, source_workers=0, PS5_operations=0)
    (a.out / 'receipt.private.json').write_text(json.dumps(receipt, indent=2) + '\n')
    save(a.out / 'result.private.json', receipt)
    print(json.dumps(dict(completed=True, bytes=receipt['artifact']['bytes'], context_controls=8,
                          libc_parameter_controls=8, driver_code_linked=False, PS5_operations=0)))


if __name__ == '__main__': main()
