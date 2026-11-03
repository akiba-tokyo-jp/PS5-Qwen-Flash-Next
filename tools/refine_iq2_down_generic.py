#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refine the two indexed generic resources selected by the completed native trace."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('matmul_id_quant_f32_fp32', 'matmul_id_subgroup_quant_f32_fp32')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'parent', 'native', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    parent, native = load(a.parent), load(a.native)
    need(parent['completed'] and parent['packed_half_dequant_refinement'] and len(parent['shaders']) == 13 and
         native['completed'] and not native['native_passed'] and native['ordinary_exit_observed'] and
         native['current_seven_restored_and_native_hashed'], 'The completed immutable parent and returned native negative are required')
    recipes = load(parent['recipes']['path'])
    directory = Path(recipes['source']['path']).parent
    a.out.mkdir(parents=True, exist_ok=False)
    overlay = a.out / 'shaders'
    overlay.mkdir()
    for path in directory.glob('*.glsl'):
        shutil.copyfile(path, overlay / path.name)
    shutil.copyfile(directory / 'mul_mm.comp', overlay / 'mul_mm.comp')
    shutil.copyfile(ROOT / 'native/app/iq2_down_carrier.glsl', overlay / 'iq2_down_carrier.glsl')
    shader = overlay / 'mul_mm.comp'
    shader.write_text(once(shader.read_text(), '#include "types.glsl"',
        '#include "types.glsl"\n#include "iq2_down_carrier.glsl"'), newline='\n')
    funcs = overlay / 'mul_mm_funcs.glsl'
    text = funcs.read_text()
    start = text.index('    } else if (MmTypeA == GGML_TYPE_Q2_0) {')
    end = text.index('    } else if (MmTypeA == GGML_TYPE_Q2_K) {', start)
    text = text[:start] + '''    } else if (MmTypeA == GGML_TYPE_Q2_0) {
        const uint idx = pos_a + col * p.stride_a / mm_load_vec_a() + row;
        const uint k_pair = row * mm_load_vec_a() / 2;
        const uint value = idx * 4u;
        store_a(col, k_pair, FLOAT_TYPEV2(iq2_down_decode(value), iq2_down_decode(value + 1u)));
        store_a(col, k_pair + 1, FLOAT_TYPEV2(iq2_down_decode(value + 2u), iq2_down_decode(value + 3u)));
''' + text[end:]
    funcs.write_text(text, newline='\n')
    # Packed row-map words already bound both coordinates to sixteen bits.
    # Keep those exact values in 32-bit shared registers for the software check.
    for filename in ('mul_mm.comp','mul_mm_funcs.glsl','mul_mm_id_funcs.glsl'):
        path=overlay/filename
        path.write_text(path.read_text().replace('u16vec2','uvec2'),newline='\n')
    emitter = Path(recipes['emitter']['path'])
    need(record(emitter) == recipes['emitter'], 'The exact pinned recipe emitter changed')
    text = once(emitter.read_text(),
        '    if(name.find("q2_0")==std::string::npos||name.find("tq2_0")!=std::string::npos)return;',
        '    if(name!="matmul_id_quant_f32_fp32"&&name!="matmul_id_subgroup_quant_f32_fp32")return;')
    source, exe = a.out / 'generator.private.cpp', a.out / 'generator.exe'
    source.write_text(text, newline='\n')
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    shaderc = a.workspace / 'toolchain/shaderc-clang64/clang64/bin'
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''), TMP=str(a.out), TEMP=str(a.out))
    commands = []
    def run(command, label):
        command = list(map(str, command)); commands.append(command)
        r = subprocess.run(command, capture_output=True, timeout=120, env=env)
        (a.out / (label + '.private.log')).write_bytes(r.stdout + r.stderr)
        need(r.returncode == 0, r.stderr.decode(errors='replace')[-4000:])
        return r.stdout.decode()
    run([host/'clang++.exe', '-std=c++17', '-O2', source, '-o', exe], 'generator')
    manifest = run([exe, '--output-dir', a.out], 'recipes')
    added = []
    for line in manifest.splitlines():
        name, filename, fp16, coop, coop2, *defines = line.split('\t')
        need(name in NAMES and fp16 == coop == coop2 == '0', 'Only the two observed F32 indexed generic recipes are required')
        flags = dict(x.split('=', 1) for x in defines)
        output = a.out / (name + '.spv')
        run([shaderc/'glslc.exe', '-fshader-stage=compute', '--target-env=vulkan1.2', '-O',
             overlay/filename, '-o', output, *['-D'+k+'='+v for k,v in sorted(flags.items())]], name+'-compile')
        run([host/'spirv-val.exe', '--target-env', 'vulkan1.2', output], name+'-validate')
        added.append(dict(name=name, artifact=record(output), recipe=dict(name=name, source=record(directory/filename),
            fp16=False, coopmat=False, coopmat2=False, defines=flags)))
    need({r['name'] for r in added} == set(NAMES), 'Both new resources must complete')
    result = dict(parent)
    result.update(ancestor=record(a.parent), shaders=parent['shaders']+added, commands=commands,
        generic_indexed_refinement=True, packed_half_dequant_refinement=False, reused_shader_resources=13,
        native_selection_evidence=record(a.native), changed_sources=[record(shader),record(funcs)],
        carrier_decoder=record(ROOT/'native/app/iq2_down_carrier.glsl'),
        only_Q2_0_branch_changed=True, other_quantization_branches_unchanged=True,
        packed_row_map_coordinates_preserved_in_u32=True,
        software_model_shader_qualified=False, native_model_shader_qualified=False)
    save(a.out/'result.private.json', result)
    print(dict(completed=True, new_resources=2, reused_resources=13, PS5_operations=0))


if __name__ == '__main__':
    main()
