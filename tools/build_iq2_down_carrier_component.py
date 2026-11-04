#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Change only paired-Down operand storage and reuse its actual numerical references."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from build_iq2_down_carrier import carrier, PAYLOAD, PLANE, HEADER, TABLES
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'component', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--resume', action='store_true', help='Reuse unchanged carrier bytes after an unsubmitted host shader compile failure')
    a = p.parse_args()
    old = load(a.component)
    need(old['completed'] and old['buffer_tables'] and old['all14745600_decoded_F32_values_byte_exact'] and
         record(old['GPU_cases']['path']) == old['GPU_cases'], 'The exact previously qualified paired operands are required')
    cases = copy.deepcopy(load(old['GPU_cases']['path']))
    need(cases['completed'] and cases['buffer_tables'] and len(cases['cases']) == 12 and
         record(cases['tables']['path']) == cases['tables'], 'The complete original12 shape/reference cases are required')
    tables = Path(cases['tables']['path']).read_bytes()
    need(len(tables) == TABLES, 'Exact pinned buffer codebooks required')
    a.out.mkdir(parents=True, exist_ok=a.resume)
    need(not (a.out/'result.private.json').exists(), 'A completed component build must not be repeated')
    converted = {}
    for row in cases['cases']:
        original = row['weights']
        if original['sha256'] not in converted:
            need(record(original['path']) == original, 'The complete original weight sample changed')
            raw = Path(original['path']).read_bytes()
            need(len(raw) == 10 * PAYLOAD, 'All original10 selected Expert planes required')
            path = a.out / ('carriers-' + original['sha256'][:24] + '.bin')
            encoded = b''.join(carrier(raw[i*PAYLOAD:(i+1)*PAYLOAD], tables) for i in range(10))
            if path.exists():
                need(a.resume and path.read_bytes() == encoded, 'Only byte-identical already prepared operands may be reused')
            else:
                path.write_bytes(encoded)
            # Independent inverse of every plane preserves all original bytes.
            for i in range(10):
                plane = encoded[i*PLANE:(i+1)*PLANE]
                need(plane[HEADER:HEADER+PAYLOAD] == raw[i*PAYLOAD:(i+1)*PAYLOAD] and
                     plane[HEADER+PAYLOAD:HEADER+PAYLOAD+TABLES] == tables,
                     'The independent complete carrier inverse differs')
            converted[original['sha256']] = record(path)
        row['weights'] = converted[original['sha256']]
    source = (ROOT / 'native/app/iq2_paired_down.comp').read_text()
    begin, end = source.index('#if defined(QWEN_DOWN_BUFFER_TABLES)'), source.index('#ifndef QWEN_DOWN_WORKGROUP')
    source = source[:begin] + '#include "iq2_down_carrier.glsl"\n' + source[end:]
    source = once(source, 'layout(set=0,binding=0,std430) readonly buffer Weights {uint words[];} weights;\n', '')
    begin, end = source.index('uint byte_at('), source.index('\nvoid main()')
    source = source[:begin] + '''float decode(uint plane,uint row,uint column){
    if(!iq2_down_header(plane))return uintBitsToFloat(0x7fc00000u);
    return iq2_down_decode(plane*IQ2_DOWN_VALUES+row*640u+column);
}
''' + source[end:]
    source = once(source, 'weights.words.length()<geometry.planes*105600u',
                   'iq2_down_carrier.words.length()<geometry.planes*115200u')
    shader = a.out / 'iq2_down_carrier_component.comp'
    shader.write_text(source, newline='\n')
    commands, profiles = [], []
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    env = dict(os.environ, PATH=str(host)+os.pathsep+os.environ.get('PATH', ''), TMP=str(a.out), TEMP=str(a.out))
    def run(command, name):
        command = list(map(str, command))
        commands.append(command)
        result = subprocess.run(command, capture_output=True, timeout=240, env=env)
        (a.out / (name + '.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode, (result.stdout+result.stderr).decode(errors='replace')[-4000:])
    for width in (64, 128):
        output = a.out / ('carrier-' + str(width) + '.spv')
        run([a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslangValidator.exe', '-V', '--target-env', 'vulkan1.2',
             '-S', 'comp', '-DQWEN_DOWN_WORKGROUP='+str(width), '-I'+str(ROOT/'native/app'), shader, '-o', output], 'shader-'+str(width))
        run([host/'spirv-val.exe', '--target-env', 'vulkan1.2', output], 'validate-'+str(width))
        profiles.append(dict(workgroup=width, artifact=record(output)))
    cases.update(buffer_tables=False, paired_down_carrier=True, carrier_plane_bytes=PLANE, shader=profiles,
                 source=record(shader), original_component=record(a.component))
    target = a.out / 'GPU-cases.private.json'
    save(target, cases)
    save(a.out / 'result.private.json', dict(completed=True, paired_down_carrier=True, source=record(shader),
        decoder=record(ROOT/'native/app/iq2_down_carrier.glsl'), GPU_cases=record(target),
        original_component=record(a.component), original_IQ2_operands_and_F64_references_preserved=True,
        all_complete_carriers_independently_inverse_verified=True, source_hashes_changed_without_reencoding=len(converted),
        commands=commands, native_GPU_execution=False, GPU_qualified=False, model_inference=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, new_shader_profiles=2, changed_operand_packs=len(converted), PS5_operations=0)))


if __name__ == '__main__':
    main()
