#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one isolated post-context OS-reserve experiment with a coherent ABI."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess

from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from resident_OS_reserve_scope import SCOPE, entry, implementation, source_header, system_header
from shader_storage import record

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'workspace', 'cache', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    prior = json.loads(a.parent.read_text())
    frozen = list({row['path']: row for row in prior['inputs_before'] + [prior['artifact']]}.values())
    for row in frozen:
        if record(row['path']) != row:
            raise ValueError('Exact native input changed: ' + row['path'])
    a.out.mkdir(parents=True, exist_ok=False)
    view = a.out / 'app-view'
    view.mkdir()
    (a.out / 'tmp').mkdir()
    main_recipe = prior['compile_commands'][0].copy()
    folders = [Path(main_recipe[i+1]) for i, token in enumerate(main_recipe[:-1]) if token == '-I']
    original_view = next(folder for folder in folders if (folder / 'resident_CPU_metadata_scope.h').is_file())
    for path in sorted(original_view.glob('*.h')):
        (view / path.name).write_bytes(path.read_bytes())
        frozen.append(record(path))
    private_header = next(row for row in prior['resident_phase_source']['inputs']
        if Path(row['path']).name == 'resident-mapped-source.private.h')
    if not (view / 'resident-mapped-source.private.h').exists():
        (view / 'resident-mapped-source.private.h').write_bytes(Path(private_header['path']).read_bytes())
        frozen.append(record(private_header['path']))
    declarations = view / 'resident_CPU_metadata_scope.h'
    declarations.write_text(declarations.read_text() + '''
extern "C" bool qwen_app_resident_GPU_OS_reserve_active();
extern "C" void qwen_app_activate_resident_GPU_OS_reserve();
''', newline='\n')
    for name, transform in (('system_memory.h', system_header), ('resident_phase_vm.h', source_header)):
        path = view / name
        path.write_text(transform(path.read_text()), newline='\n')
    recipes = [row['command'].copy() for row in prior['CPU_metadata_scope']['changed_sources']
        if row['object_path'] in prior['link_command'] and 'resident-comparison' not in Path(row['source']['path']).name]
    recipes.append(main_recipe)
    commands = []
    replacements = {}
    compiled = []
    for index, recipe in enumerate(recipes):
        original = Path(recipe[recipe.index('-c') + 1])
        text = original.read_text()
        is_main = recipe == main_recipe
        if original.name == 'system_memory.cpp':
            text = implementation(text)
        if is_main:
            text = entry(text)
        generated = view / ('resident-comparison-OS-reserve.private.cpp' if is_main else original.name)
        generated.write_text(text, newline='\n')
        old = recipe[recipe.index('-o') + 1]
        obj = a.out / (str(index) + '-' + generated.stem + '.o')
        recipe[recipe.index('-c') + 1] = str(generated)
        recipe[recipe.index('-o') + 1] = str(obj)
        recipe[1:1] = ['-I', str(view)]
        recipe += ['-I', str(original.parent)]
        commands.append(recipe)
        replacements[old] = str(obj)
        compiled.append(dict(original=record(original), source=record(generated), object_path=str(obj), command=recipe))
        frozen.append(record(original))
    if sum(Path(row['source']['path']).name == 'system_memory.cpp' for row in compiled) != 1:
        raise ValueError('One actual coherent native system-memory implementation required')
    link = [replacements.get(x, x) for x in prior['link_command']]
    if any(prior['link_command'].count(old) != 1 for old in replacements):
        raise ValueError('Every replaced app object must have exactly one actual link owner')
    image = a.out / 'qwen-native.pie.elf'
    link[link.index('-o') + 1] = str(image)
    link = [('-Map=' + str(a.out / 'native-link.private.map')) if x.startswith('-Map=') else x for x in link]
    frozen += [record(x) for x in (a.parent, Path(__file__), ROOT / 'tools/resident_OS_reserve_scope.py', *sorted(view.iterdir()))]
    env = dict(os.environ, TMP=str(a.out / 'tmp'), TEMP=str(a.out / 'tmp'))
    for index, command in enumerate(commands + [link]):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=600, env=env)
        (a.out / f'{index}.private.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(OS_reserve_compiled_or_linked=index+1, total=len(commands)+1)), flush=True)
    for row in frozen:
        if record(row['path']) != row:
            raise ValueError('Fresh OS-reserve input changed')
    receipt = copy.deepcopy(prior)
    receipt.update(artifact=record(image), link_command=link, compile_commands=[commands[-1]],
        source_parent=record(a.parent), inputs_before=frozen + [record(path) for path in replacements.values()],
        post_context_OS_reserve=dict(scope=SCOPE, all_actual_app_dependencies_recompiled=True,
            original_engine_and_driver_objects_unchanged=True, original_setup_floor_pages=1154,
            selected_post_context_floor_pages=1104, native_qualification_pending=True),
        lossless_driver_table_geometry=audit_linked_storage(image, prior['lossless_driver_tables']))
    receipt['CPU_metadata_scope']['changed_sources'] = compiled
    receipt['resident_context_reuse']['entry'] = compiled[-1]['source']
    phase = next(row for row in compiled if 'mapped-source-original-window' in Path(row['source']['path']).name)
    receipt['resident_phase_source'].update(generated_source=phase['source'], object=record(phase['object_path']), command=phase['command'])
    path = a.out / 'receipt.private.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    receipt['real_module_import_audit'] = audit(a.workspace, a.cache, a.out)
    if receipt['real_module_import_audit']['missing']:
        raise ValueError('Native imports missing')
    receipt['native_dispatch_audit'] = dispatch(a.workspace,
        a.workspace / 'driver-work/PS5-Vulkan-Inference-qwen-872cc126', image, a.out / 'dispatch')
    if not receipt['native_dispatch_audit']['passed']:
        raise ValueError('Native dispatch failed')
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(OS_reserve_experiment_built=True, setup_GPU_floor_unchanged=True, PS5_operations=0)), flush=True)


if __name__ == '__main__':
    main()
