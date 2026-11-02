#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind restored, byte-identical live inputs through a read-only data provider."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from build_performance_quantizer import record
from driver_table_storage import sections
from native_dispatch import ELF
from start_success_route import load,need,save


def authenticated(row):
    need(record(row['path'])==row,'Private evidence or retained input changed')
    return load(row['path'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--input',action='append',type=Path,required=True)
    args=parser.parse_args()
    need(len(args.input)==3,'Exactly three positively finalized live inputs required')
    args.out.mkdir(parents=True,exist_ok=False)
    state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['unknown_completion'],
         'Positive native completion and selected application restoration required')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    owners=[r for r in retained if Path(r['original_path']).name=='owner.o']
    need(len(owners)==1,'One actual selected owner required')
    owner={k:owners[0][k] for k in ('path','bytes','sha256')}
    need(record(owner['path'])==owner,'Actual owner changed')
    raw=Path(owner['path']).read_bytes();table=sections(raw)
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    relocations=subprocess.check_output([str(llvm/'llvm-readobj.exe'),'--relocs',owner['path']],text=True)
    old_symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',owner['path']],text=True)
    rows=[];boot=None
    for path in args.input:
        restored=load(path);symbol=restored['identity_provider_symbol']
        need(re.fullmatch(r'Q2_(bundle|extra|current)_expected_identity',symbol),'Unexpected identity provider')
        need(restored in state['restored_required_bundle_inputs'],'Input not in positively closed active state')
        case=authenticated(restored['native_copy_case']);report=authenticated(restored['native_report'])
        final=authenticated(restored['finalization']);bundle=authenticated(case['required_bundle_restore']['bundle_plan'])
        proof=authenticated(case['required_bundle_restore']['current_model_proof'])
        terminal=load(Path(restored['native_copy_case']['path']).parent/'result.private.json')
        need(terminal['completed'] and terminal['required_bundle_restored'] and terminal['ordinary_exit_observed'] and
             terminal['current_original_restored'] and terminal['current_seven_file_native_hashes_pass'],
             'Full native copy, ordinary close and exact restoration required')
        need(final['completed'] and final['operation']=='finalize-bundle' and final['helper_exited'] and final['helper_files_removed'],
             'Positive root metadata finalization required')
        need(report['completed'] and report['run_id']==case['run_id'] and report['full_original_SHA256_and_EOF_readback'] and
             report['tracked_CPU_heap_free_returned'] and report['all_started_input_calls_returned'] and report['source_payloads_unchanged'],
             'Complete original bytes and positive CPU allocation retirement required')
        need(restored['full_native_original_SHA256_and_EOF_preserved'] and restored['payload_writes']==0 and
             restored['sha256']==bundle['expected_SHA256'] and restored['bytes']==bundle['output_bytes'] and
             restored['path']==bundle['output'] and symbol==bundle['identity_provider_symbol'],
             'Exact original live input, digest and geometry required')
        need({k:bundle['owner'][k] for k in owner}==owner,'Restore plan belongs to another owner')
        identity=restored['identity']
        need(len(identity)==10 and identity[0]==proof['canonical_directory'][0] and identity[1]>0 and
             identity[2:6]==[0o100444,0,0,restored['bytes']] and all(type(v) is int and 0<=v<2**64 for v in identity),
             'Fresh canonical read-only input identity required')
        need(proof['current_boot']==state['current_boot'] and (boot is None or boot==proof['current_boot']),
             'All three restored inputs must belong to this boot')
        boot=proof['current_boot']
        old=[s for s in table if s['name']=='.rodata.'+symbol]
        need(len(old)==1 and list(struct.unpack('<10Q',old[0]['data']))==bundle['old_identity'],
             'Original weak metadata was not reconstructed exactly')
        need(re.search(r'^'+symbol+r' V 0 50$',old_symbols,re.M) is not None and
             len(re.findall(r'R_X86_64_REX_GOTPCRELX '+symbol+r' ',relocations))==1,
             'Actual owner must use one symbolic weak read-only identity provider')
        rows.append(dict(symbol=symbol,identity=identity,restored_input=record(path),original_SHA256=restored['sha256']))
    need({r['symbol'] for r in rows}=={'Q2_'+k+'_expected_identity' for k in ('bundle','extra','current')},
         'One distinct provider for each required legacy input is required')
    source=args.out/'required-input-identities.c';obj=args.out/'required-input-identities.o'
    source.write_text('/* Generated from positively closed, whole-hash verified native inputs. */\n'
        '#include <stdint.h>\n'+''.join('const uint64_t '+r['symbol']+'[10]={'+
        ','.join(str(v)+'ULL' for v in r['identity'])+'};\n' for r in sorted(rows,key=lambda r:r['symbol'])),
        encoding='utf-8',newline='\n')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    command=[str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5',
             '-isystem',str(sdk/'target/include'),'-std=c11','-fPIC','-O2','-fdata-sections',
             '-c',str(source),'-o',str(obj)]
    result=subprocess.run(command,capture_output=True,timeout=60,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--format=posix',str(obj)],text=True)
    need({line.split()[0] for line in symbols.splitlines()}=={r['symbol'] for r in rows} and
         all(line.split()[1]=='R' and line.split()[3]=='50' for line in symbols.splitlines()),
         'Only three strong read-only 80-byte definitions are permitted')
    elf=ELF(obj)
    for row in rows:
        need(elf.symbol_data(row['symbol'])==struct.pack('<10Q',*row['identity']),'Compiled identity bytes differ')
    need(not any(s['bytes'] for s in sections(obj.read_bytes()) if s['flags']&4) and not elf.relocations,
         'The metadata provider must contain no instructions, imports or relocations')
    need(record(owner['path'])==owner,'Selected owner changed during metadata compilation')
    report=dict(completed=True,owner=owner,source=record(source),artifact=record(obj),inputs=rows,current_boot=boot,
        command=command,strong_readonly_identity_definitions=3,executable_bytes=0,imports=0,relocations=0,
        original_owner_unchanged=True,model_arithmetic_changes=0,weight_byte_changes=0,PS5_operations=0,
        native_model_admitted=False,native_speed_or_quality_measured=False,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('owner','source','artifact','inputs','command','current_boot')}))


if __name__=='__main__':main()
