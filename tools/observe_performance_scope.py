#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe a fresh performance scope without initializing runtime or a title."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time


def record(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'cache', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--success-route', action='store_true',
                        help='Also observe mount-before-initialization prerequisites; never initialize')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'tmp').mkdir()
    source = args.workspace / 'driver-work/PS5-Vulkan-Inference/.local/discover_current_boot.c'
    frozen = args.out / 'discovery.private.c'
    body = source.read_text()
    startup = Path(__file__).resolve().parents[1] / 'native/qwen_flash_next/performance_bootstrap_observer.h'
    if args.success_route:
        # Includes follow the original declarations, before main. All added
        # observations execute inside the same two existing boot/process phases.
        body = body.replace('int main(int argc,char **argv) {',
                            '#include ' + json.dumps(startup.as_posix()) + '\nint main(int argc,char **argv) {', 1)
        anchor = '    for(unsigned phase=1;phase<=2;phase++) {'
        assert body.count(anchor) == 1
        body = body.replace(anchor, anchor + '\n        if(qwen_success_route_prerequisites(out,phase)){failure=1;break;}', 1)
    frozen.write_text(body, encoding='utf-8', newline='\n')
    sdk = args.workspace / 'toolchain/ps5-payload-sdk'
    tool = args.workspace / 'toolchain/fast/llvm-mingw-20261006-ucrt-x86_64/bin'
    archived = Path('D:/PS5-AI/archives/c-drive-cleanup-20261019/build/gpu_probe')
    crt = archived / 'credential-preserving-crt'
    artifact = args.out / 'performance-scope.elf'
    obj = args.out / 'discovery.o'
    commands = [
        [str(tool / 'clang.exe'), '--no-default-config', '--target=x86_64-sie-ps5',
         '-isystem', str(sdk / 'target/include'), '-I', str(archived / 'sd-pid807-signal-state/overlay'),
         '-I', str(args.workspace / 'vendor/ShadowMountPlus/include'), '-D_BSD_SOURCE',
         '-std=gnu11', '-fno-stack-protector', '-fno-plt', '-femulated-tls', '-fPIC',
         '-O2', '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror',
         '-c', str(frozen), '-o', str(obj)],
        [str(tool / 'ld.lld.exe'), '-m', 'elf_x86_64', '-pie', '-T', str(sdk / 'ldscripts/elf_x86_64.x'),
         '--eh-frame-hdr', '--gc-sections', '-z', 'max-page-size=0x4000', '--hash-style=gnu',
         '-L', str(sdk / 'target/lib'), '-o', str(artifact), str(obj),
         str(crt / 'crt1-credential-preserving.o'), str(crt / 'patch-syscall-only.o'),
         '-lc', '-lkernel_web', '-lSceLibcInternal', '--as-needed', '-lSceSystemService', '-lSceAppInstUtil'],
    ]
    inputs = [record(p) for p in (source, frozen, crt / 'crt1-credential-preserving.o', crt / 'patch-syscall-only.o')]
    if args.success_route:
        inputs.append(record(startup))
    environment = dict(os.environ, TMP=str(args.out / 'tmp'), TEMP=str(args.out / 'tmp'))
    for index, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, timeout=90, env=environment)
        (args.out / f'build-{index}.private.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-3000:])
    imports = subprocess.check_output([str(tool / 'llvm-nm.exe'), '--undefined-only', str(obj)], text=True)
    if re.search(r'\b(?:kill|ptrace|nmount|unmount|kernel_set\w*|sceSystemServiceLaunchApp|sceAgc\w*)\b', imports):
        raise RuntimeError('Read-only observer has a forbidden import')
    save(args.out / 'build.private.json', dict(artifact=record(artifact), inputs=inputs, commands=commands,
                                             imports=imports, initializer_requests=0, title_launches=0, GPU_calls=0))
    if not args.execute:
        print(json.dumps(dict(observer_built=True, console_executions=0)), flush=True)
        return
    spec = importlib.util.spec_from_file_location('lan', 'D:/PS5-AI/moss/tools/live_moss_root_v1.py')
    lan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lan)

    def processes():
        with lan.OPENER.open('http://' + lan.HOST + ':8084/processes_list', timeout=8) as response:
            return json.loads(response.read((1 << 20) + 1))['processes']

    before = processes()
    if any(row['name'] == 'eboot.bin' for row in before):
        raise RuntimeError('A native title already owns the console')
    save(args.out / 'management-before.private.json', before)
    prefix = '/data/ai/moss-reval-discovery-' + secrets.token_hex(16)
    raw = lan.execute_once(artifact, record(artifact)['sha256'], prefix + '.log',
                           prefix + '.elf', prefix + '.log', args.out / 'execution', 45)
    if not re.search(rb'\nEND success=[01] GPU_calls=0 state_changes=0\n$', raw):
        raise RuntimeError('Observer terminal state is unknown; retain all files and never resubmit')
    pid = int(re.search(rb'BEGIN pid=(\d+)', raw)[1])
    deadline = time.monotonic() + 10
    while any(int(r['pid']) == pid for r in processes()):
        assert time.monotonic() < deadline, 'Observer retirement is unknown; never resubmit'
        time.sleep(.2)
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST, 2121, timeout=20)
        ftp.login()
        assert ftp.sendcmd('SELF') == '226 SELF transfer mode disabled'
        for path in (prefix + '.elf', prefix + '.log'):
            assert ftp.sendcmd('DELE ' + path).startswith(('226 ', '250 '))
    for path in (prefix + '.elf', prefix + '.log'):
        lan.absent(path)
    save(args.out / 'retirement.private.json', dict(helper_exited=True, helper_files_removed=True,
                                                  observation_success=raw.endswith(b'END success=1 GPU_calls=0 state_changes=0\n')))
    if not raw.endswith(b'END success=1 GPU_calls=0 state_changes=0\n'):
        raise RuntimeError('Read-only observation did not complete positively')
    lines = raw.decode().splitlines()

    def rows(kind):
        return [dict(re.findall(r'(\w+)=([^ ]+)', line)) for line in lines if line.startswith(kind + ' ')]

    boot = rows('BOOT')
    assert len(boot) == 2 and all(r['rc'] == '0' and r['bytes'] == '16' for r in boot)
    boot_value = [int(boot[0]['sec']), int(boot[0]['usec'])]
    assert all([int(r['sec']), int(r['usec'])] == boot_value for r in boot)
    native = rows('PROCESS')
    first = [{k: v for k, v in r.items() if k != 'phase'} for r in native if r['phase'] == '1']
    last = [{k: v for k, v in r.items() if k != 'phase'} for r in native if r['phase'] == '2']
    assert first == last and not any(r['name'] == 'eboot.bin' for r in first)
    runtime = rows('RUNTIME')
    assert len(runtime) == 1 and runtime[0]['query_only'] == '1'
    startup_rows = rows('SUCCESS_ROUTE')
    if args.success_route:
        assert len(startup_rows) == 2
        first_startup = {k: v for k, v in startup_rows[0].items() if k not in ('phase', 'free_pages')}
        last_startup = {k: v for k, v in startup_rows[1].items() if k not in ('phase', 'free_pages')}
        assert first_startup == last_startup and first_startup['source_directory'] == '1'
    result = dict(completed=True, boot=boot_value, processes=first, runtime_loaded=runtime[0]['loaded'] == '1',
                  native_owners=0, helper_exited=True, helper_files_removed=True, initializer_requests=0,
                  title_launches=0, GPU_calls=0, raw=record(args.out / 'execution/console.private.log'))
    if args.success_route:
        result['success_route_prerequisites'] = startup_rows
    save(args.out / 'result.private.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('boot', 'processes', 'raw')}), flush=True)


if __name__ == '__main__':
    main()
