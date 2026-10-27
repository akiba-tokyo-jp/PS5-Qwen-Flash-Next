#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare current-boot CPU headers from complete evidence; never execute."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
from kernel_vm_preflight import session_boot, load_qualified_session

ROLES = (('elfldr', 'elfldr.elf'), ('ftpsrv', 'ftpsrv.elf'),
         ('pldmgr', 'pldmgr.elf'), ('shsrv', 'shsrv.elf'),
         ('websrv', 'websrv.elf'), ('syscore', 'SceSysCore.elf'),
         ('shellcore', 'SceShellCore'), ('compat', 'payload'))


def current_processes(session, runtime):
    boot = session_boot(session)
    if (not isinstance(boot, list) or len(boot) != 2 or
            any(type(v) is not int for v in boot) or boot[0] <= 0 or not 0 <= boot[1] < 1000000):
        raise ValueError('Invalid complete CPU boot identity')
    if (runtime.get('state') != 'unchanged_runtime_ready' or runtime.get('boot') != boot or
            runtime.get('kernel_loaded') is not True or type(runtime.get('runtime_pid')) is not int or
            runtime['runtime_pid'] <= 0 or type(runtime.get('ELF_requests')) is not int or
            runtime['ELF_requests'] != 1 or type(runtime.get('automatic_retries')) is not int or runtime['automatic_retries'] != 0):
        raise ValueError('The positive same-boot compatibility runtime is required')
    candidates = [*session['services'], session['parent'], session['shellcore']]
    compat = [p for p in session['compat_candidates'] if p.get('name') == 'payload' and p.get('self') is False]
    if len(candidates) != 7 or len(compat) != 1 or compat[0].get('pid') != runtime['runtime_pid']:
        raise ValueError('Exact current services and compatibility owner are required')
    candidates += compat
    result = []
    for label, name in ROLES:
        found = [p for p in candidates if p.get('name') == name]
        if len(found) != 1:
            raise ValueError('Missing or duplicate actual process identity')
        item = found[0]
        for key in ('pid', 'ppid', 'uid', 'start_sec', 'start_usec'):
            if type(item.get(key)) is not int or item[key] < 0:
                raise ValueError('Exact unsigned process metadata is required')
        if not 0 < item['pid'] <= 0x7fffffff or item['ppid'] > 0x7fffffff or item['uid'] != 0:
            raise ValueError('Qualified management process credentials differ')
        if not 0 <= item['start_usec'] < 1000000 or (item['start_sec'], item['start_usec']) < tuple(boot):
            raise ValueError('Process start differs from the current boot')
        result.append(dict(label=label, name=name, **{k: item[k] for k in ('pid', 'ppid', 'uid', 'start_sec', 'start_usec')}))
    if len({p['pid'] for p in result}) != 8:
        raise ValueError('Current process identities alias')
    services = {p['name']: p for p in result}
    if (services['payload']['ppid'] != services['websrv.elf']['pid'] or
            services['SceShellCore']['ppid'] != services['SceSysCore.elf']['pid']):
        raise ValueError('Current process ancestry differs')
    return result


def headers(session, runtime, nonce):
    if not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('A fresh CPU control nonce is required')
    rows = current_processes(session, runtime)
    boot = session['boot']
    observer = '#pragma once\n#define OBSERVER_NONCE ' + json.dumps(nonce) + '\n'
    observer += '#define OBSERVER_LOG_PATH ' + json.dumps('/data/ai/moss-kernel-observer-' + nonce + '.log') + '\n'
    observer += f'#define BOOT_SEC {boot[0]}LL\n#define BOOT_USEC {boot[1]}LL\n'
    observer += 'struct expected_process{const char *label;int pid;const char *name;int ppid;unsigned uid;int64_t sec,usec;};\n'
    observer += 'static const struct expected_process expected_processes[]={\n'
    guard = '#pragma once\n#define CLOSE_NONCE ' + json.dumps(nonce) + '\n'
    guard += f'#define BOOT_SEC INT64_C({boot[0]})\n#define BOOT_USEC INT64_C({boot[1]})\n'
    guard += 'struct expected_process {const char *name;int pid,ppid;unsigned uid;int64_t sec,usec;};\n'
    guard += 'static const struct expected_process expected_processes[]={\n'
    for p in rows:
        identity = f'{p["pid"]},{json.dumps(p["name"])},{p["ppid"]},{p["uid"]}U,{p["start_sec"]}LL,{p["start_usec"]}LL'
        observer += '{' + json.dumps(p['label']) + ',' + identity + '},\n'
        guard += '{' + json.dumps(p['name']) + f',{p["pid"]},{p["ppid"]},{p["uid"]}U,{p["start_sec"]}LL,{p["start_usec"]}LL' + '},\n'
    return {'observer_context.h': observer + '};\n', 'close_context.h': guard + '};\n'}


def launcher_header(session,runtime,template):
    rows=current_processes(session,runtime)
    if not isinstance(template,str)or not 0<len(template)<=16384 or '\0'in template:
        raise ValueError('A bounded qualified ordinary-launcher identity template is required')
    compat=rows[-1]
    replacements=dict(BOOT_SEC=str(session['boot'][0])+'LL',BOOT_USEC=str(session['boot'][1])+'LL',
        COMPATIBILITY_PID=str(compat['pid']),COMPATIBILITY_START_SEC=str(compat['start_sec'])+'LL',
        COMPATIBILITY_START_USEC=str(compat['start_usec'])+'LL')
    for key,value in replacements.items():
        template,count=re.subn(r'^#define '+key+r' .*$',lambda _: '#define '+key+' '+value,template,flags=re.M)
        if count!=1:raise ValueError('One exact ordinary-launch identity macro is required: '+key)
    pattern=r'(static const struct expected_service expected_services\[\]=\{)\n(.*?)\n\};'
    found=list(re.finditer(pattern,template,re.S))
    if len(found)!=1 or re.findall(r'\{"([^"\n]+)"',found[0][2])!=[name for _,name in ROLES]:
        raise ValueError('The qualified launcher must retain all eight original service guards')
    body='\n'.join('{'+json.dumps(p['name'])+f',{p["pid"]},{p["ppid"]},{p["uid"]}U,{p["start_sec"]}LL,{p["start_usec"]}LL'+'},'for p in rows)
    return re.sub(pattern,lambda m:m[1]+'\n'+body+'\n};',template,flags=re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--launcher-template',type=Path,help='Qualified session_context.h; only actual boot/process identity data is rebound')
    args = parser.parse_args()
    inputs = []
    values = []
    session, session_raw = load_qualified_session(args.session)
    for path, raw in ((args.session, session_raw), (args.runtime, args.runtime.read_bytes())):
        inputs.append(dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        values.append(json.loads(raw))
    nonce = secrets.token_hex(16)
    generated = headers(*values, nonce)
    if args.launcher_template:
        raw=args.launcher_template.read_bytes()
        generated['launcher_session_context.h']=launcher_header(*values,raw.decode('utf-8'))
        inputs.append(dict(path=str(args.launcher_template.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    args.out.mkdir(parents=True, exist_ok=False)
    for name, text in generated.items():
        with (args.out / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    result = dict(schema='ps5-qwen-current-CPU-headers-v1', inputs=inputs,
                  nonce=nonce, expected_boot=values[0]['boot'], expected_processes=current_processes(*values),
                  old_owner_reused=False, source_guard_relaxed=False,
                  native_admission_granted=False, console_operations=0, CI_runs=0)
    with (args.out / 'receipt.private.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(current_boot_CPU_headers_prepared=True, process_identities=8,
                         native_admission_granted=False, console_operations=0)))


if __name__ == '__main__':
    main()
