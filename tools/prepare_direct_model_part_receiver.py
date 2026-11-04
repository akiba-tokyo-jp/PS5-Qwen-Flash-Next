#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify only the larger finite byte ceiling of the isolated model-part receiver."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from direct_self_staging import qualification
from start_success_route import need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'original-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--resume', action='store_true', help='Continue an unsubmitted host compilation after a fixture-only warning fix')
    a = p.parse_args()
    prior = qualification(a.original_proof)
    original = ROOT / 'native/qwen_flash_next/direct_stage_receive.h'
    source = original.read_text()
    need(source.count('(32ull<<20)') == 1, 'One original finite byte ceiling required')
    changed = source.replace('(32ull<<20)', '(512ull<<20)', 1)
    a.out.mkdir(parents=True, exist_ok=a.resume)
    need(not (a.out/'result.private.json').exists(), 'A completed boundary qualification is never replayed')
    receiver = a.out / 'direct_model_part_receive.h'
    receiver.write_text(changed, newline='\n')
    mocked = changed
    for name in ('sys/socket.h', 'netinet/in.h', 'sys/time.h'):
        mocked = once(mocked, '#include <' + name + '>\n', '')
    mocked = once(mocked, 'static _Alignas(16384) unsigned char direct_stage_window[16384];',
                  'static unsigned char *direct_stage_window;')
    (a.out / 'direct_stage_under_test.h').write_text(mocked, newline='\n')
    fixture = ROOT / 'tests/direct_stage_receive_test.c'
    test = fixture.read_text()
    test = once(test, '#define DIRECT_STAGE_BYTES 17003u',
                'static uint64_t configured_bytes;\n#define DIRECT_STAGE_BYTES configured_bytes')
    test = once(test, 'payload[DIRECT_STAGE_BYTES],wire[128+DIRECT_STAGE_BYTES]', 'wire[128+17003u]')
    test = once(test, 'bytes==DIRECT_STAGE_BYTES&&stored_size==32768', '(uint64_t)bytes==DIRECT_STAGE_BYTES&&stored_size==32768')
    test = once(test, 'static int lstat(const char *path,struct stat *s){',
                'static unsigned boundary_checks;\nstatic int lstat(const char *path,struct stat *s){++boundary_checks;')
    begin = test.index('int main(void){')
    test = test[:begin] + '''int main(void){
    const uint64_t sizes[]={0,32ull<<20,(32ull<<20)+1,512ull<<20,(512ull<<20)+1,UINT64_MAX,235929600};
    unsigned admitted=0,refused=0;CHECK(sizeof(wire)==128+17003u);
    for(unsigned i=0;i<sizeof(sizes)/sizeof(sizes[0]);++i){
        configured_bytes=sizes[i];fault=EXISTS;now_ns=0;boundary_checks=opens=live_objects=acks=write_calls=0;
        int operations=0;CHECK(!case_receive_direct_stage(&operations));
        const unsigned allowed=configured_bytes>0&&configured_bytes<=(512ull<<20);
        CHECK(boundary_checks==allowed&&!opens&&!live_objects&&!operations&&!acks&&!write_calls);
        if(allowed)++admitted;else ++refused;
    }
    printf("{\\"completed\\":true,\\"new_byte_boundary_cases\\":7,\\"admitted_to_original_existing_file_guard\\":%u,\\"refused_before_file_access\\":%u,\\"OS_objects\\":0,\\"PS5_operations\\":0}\\n",admitted,refused);
    return 0;
}
'''
    path = a.out / 'boundary-test.c'
    path.write_text(test, newline='\n')
    sha = a.workspace / 'native/model_hash/sha256.c'
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    exe = a.out / 'boundary-test.exe'
    command = list(map(str, [host/'clang.exe', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', a.out,
                            '-I', sha.parent, path, sha, '-o', exe]))
    env = dict(os.environ, PATH=str(host)+os.pathsep+os.environ.get('PATH', ''))
    result = subprocess.run(command, capture_output=True, timeout=120, env=env)
    (a.out / 'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(not result.returncode, result.stderr.decode(errors='replace')[-3500:])
    result = subprocess.run([str(exe)], capture_output=True, timeout=10, env=env)
    (a.out / 'boundaries.private.log').write_bytes(result.stdout+result.stderr)
    need(not result.returncode, result.stderr.decode(errors='replace')[-2000:])
    tested = json.loads(result.stdout)
    need(tested['new_byte_boundary_cases'] == 7 and tested['admitted_to_original_existing_file_guard'] == 4 and
         tested['refused_before_file_access'] == 3 and tested['OS_objects'] == 0, 'Every distinct changed boundary must pass')
    save(a.out / 'result.private.json', dict(completed=True, receiver=record(receiver), original_receiver=record(original),
        original_qualification=prior, only_finite_payload_ceiling_changed=True, maximum_model_part_bytes=512<<20,
        original_180_second_deadline_and_16KiB_window_unchanged=True, old14_transport_and10_endpoint_controls_replayed=0,
        new_boundary_controls=tested, inputs=[record(fixture), record(sha), record(path), record(__file__)], command=command,
        native_large_model_part_qualified=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, new_boundary_controls=7, old_controls_replayed=0, PS5_operations=0)))


if __name__ == '__main__':
    main()
