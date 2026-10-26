#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Freeze native fixture code from host-checked pinned state-copy classes."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REV='0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
def record(p):return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def validate(path,cache):
    m=json.loads(path.read_text())
    if m.get('schema')!='ps5-qwen-device-state-fixture-inputs-v1'or m.get('upstream_revision')!=REV:raise ValueError('Exact device-state fixture inputs required')
    for row in m['inputs']+[m['generated']]:
        if record(Path(row['path']))!=row:raise ValueError('Device-state fixture input changed')
    proof=json.loads(Path(m['host_proof']['path']).read_text())
    if record(Path(m['host_proof']['path']))!=m['host_proof']or proof['controls']['actual_device_IO_cases']!=8 or proof['controls']['metadata_bounds_refused']!=2 or not proof['controls']['all_stub_owners_returned']:
        raise ValueError('Complete state-copy host gates required')
    source=cache/('upstream/llama.cpp-'+REV)/'src/llama-context.cpp';s=source.read_text()
    body=s[s.index('class llama_io_write_device :'):s.index('size_t llama_context::state_get_size()')]
    expected='// Generated from pinned llama.cpp MIT state-copy code; engine symbols remain unchanged.\nnamespace qwen_device_state_fixture {\n'+body+'}\n'
    if Path(m['generated']['path']).read_text()!=expected:raise ValueError('Native state-copy extraction differs')
    return m
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','host-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);proof=json.loads(a.host_proof.read_text())
    for row in proof['inputs']:
        if record(Path(row['path']))!=row:raise ValueError('Host state-copy input changed')
    source=a.cache/('upstream/llama.cpp-'+REV)/'src/llama-context.cpp';s=source.read_text()
    body=s[s.index('class llama_io_write_device :'):s.index('size_t llama_context::state_get_size()')]
    generated=a.out/'native_device_state_io.inc'
    generated.write_text('// Generated from pinned llama.cpp MIT state-copy code; engine symbols remain unchanged.\nnamespace qwen_device_state_fixture {\n'+body+'}\n',newline='\n')
    result=dict(schema='ps5-qwen-device-state-fixture-inputs-v1',upstream_revision=REV,host_proof=record(a.host_proof),generated=record(generated),
        inputs=proof['inputs']+[record(a.host_proof),record(Path(__file__))],PS5_operations=0,CI_runs=0)
    path=a.out/'manifest.private.json';path.write_text(json.dumps(result,indent=2)+'\n');validate(path,a.cache)
    print(json.dumps(dict(native_fixture_inputs_prepared=True,engine_symbols_unchanged=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
