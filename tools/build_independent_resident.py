#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build isolated retained-context comparisons from exact compiled objects."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from resident_independent_scopes import (bound_reference, release_completed_upload_entry,
    release_completed_upload_source, separate_combined)
from shader_storage import record

ROOT = Path(__file__).resolve().parents[1]


def freeze_compiled_inputs(prior):
    """Do not reinterpret historical source aliases as present compiler inputs.

    The old receipt and its complete generated source/object set are retained.
    A Git checkout can change line endings, and merged generators can supersede
    historical aliases. Neither changes an already compiled object. Explicitly
    disclose those historical aliases; require every generated source, object,
    archive, compiler, SDK input and actual private header to remain exact.
    """
    rows = {}
    for row in prior['inputs_before'] + [prior['artifact']]:
        previous = rows.setdefault(row['path'], row)
        if previous != row:
            raise ValueError('Ambiguous historical input identity')
    historical = []
    current = []
    allowed_tools = {'build_main_SELF.py', 'build_resident_comparison.py',
        'resident_shader_integrity.py', 'resident_combined_comparison.py'}
    for path, row in rows.items():
        actual = record(path)
        if actual == row:
            current.append(actual)
            continue
        source = Path(path)
        if not source.is_relative_to(ROOT):
            raise ValueError('Actual compiled input changed: ' + path)
        normalized = source.read_bytes().replace(b'\r\n', b'\n')
        endings = hashlib.sha256(normalized).hexdigest() == row['sha256']
        alias = source.parent == ROOT / 'tools' and source.name in allowed_tools
        mapped_alias = source.parent == ROOT / 'native/app' and source.name in ('mapped_source.cpp', 'mapped_source.h')
        if not (endings or alias or mapped_alias):
            raise ValueError('Unqualified compiled dependency change: ' + path)
        historical.append(dict(historical_capture=row, present_alias=actual,
            reason='line_endings_only' if endings else 'superseded_generator_or_original_source_alias',
            historical_receipt_unmodified=True, not_used_instead_of_actual_generated_source=True))
        current.append(actual)
    # Every old application object was compiled from the complete captured view.
    app = prior['CPU_metadata_scope']['changed_sources']
    for compiled in app:
        for key in ('source',):
            if record(compiled[key]['path']) != compiled[key]:
                raise ValueError('Actual compiled app view changed')
        if str(Path(compiled['object_path'])) in prior['link_command']:
            path = str(Path(compiled['object_path']))
            if path not in rows or record(path) != rows[path]:
                raise ValueError('Actual linked application object not captured')
    for token in prior['link_command']:
        if token.endswith(('.o', '.obj', '.a')):
            if token not in rows or record(token) != rows[token]:
                raise ValueError('Actual linked object/archive not captured: ' + token)
    return current, historical


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('parent', 'workspace', 'cache', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--kind', choices=('predictive', 'prefix', 'refill'), required=True)
    p.add_argument('--reuse-buffer-receipt', type=Path)
    a = p.parse_args()
    prior = json.loads(a.parent.read_text())
    frozen, historical = freeze_compiled_inputs(prior)
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / 'tmp').mkdir()
    command = prior['compile_commands'][0].copy()
    original = Path(command[command.index('-c') + 1])
    text = original.read_text()
    if a.kind != 'refill':
        text = separate_combined(text, a.kind)
    text = release_completed_upload_entry(bound_reference(text))
    generated = a.out / 'resident-comparison-independent.private.cpp'
    generated.write_text(text, newline='\n')
    obj = a.out / 'resident-comparison-independent.o'
    old_entry = command[command.index('-o') + 1]
    command[command.index('-c') + 1] = str(generated)
    command[command.index('-o') + 1] = str(obj)
    command += ['-I', str(original.parent), '-MMD', '-MF', str(a.out / 'entry.private.d')]
    upload = next(row for row in prior['bounded_model_source_overrides']['objects']
        if row['source'] == 'ggml/src/ggml-vulkan/ggml-vulkan-buffers.cpp')
    recipe = upload['command'].copy()
    original_upload = Path(recipe[recipe.index('-c') + 1])
    upload_source = release_completed_upload_source(original_upload.read_text())
    commands = []
    buffer = a.out / 'vulkan-completed-upload.private.cpp'
    buffer.write_text(upload_source, newline='\n')
    buffer_obj = a.out / 'vulkan-completed-upload.o'
    if a.reuse_buffer_receipt:
        reused = json.loads(a.reuse_buffer_receipt.read_text())['independent_resident_scope']['upload']
        for key in ('source', 'object'):
            if record(reused[key]['path']) != reused[key]:
                raise ValueError('Changed actual reusable upload dependency')
        if record(buffer)['sha256'] != reused['source']['sha256']:
            raise ValueError('Reusable upload source differs')
        buffer_obj = Path(reused['object']['path'])
        buffer_command = reused['command']
        frozen += [record(a.reuse_buffer_receipt), reused['source'], reused['object']]
    else:
        recipe[recipe.index('-c') + 1] = str(buffer)
        recipe[recipe.index('-o') + 1] = str(buffer_obj)
        recipe += ['-I', str(original_upload.parent)]
        commands.append(recipe)
        buffer_command = recipe
    commands.append(command)
    replacements = {old_entry: str(obj), upload['object']['path']: str(buffer_obj)}
    if any(prior['link_command'].count(old) != 1 for old in replacements):
        raise ValueError('Unique original entry and buffer objects required')
    link = [replacements.get(x, x) for x in prior['link_command']]
    image = a.out / 'qwen-native.pie.elf'
    link[link.index('-o') + 1] = str(image)
    link = [('-Map=' + str(a.out / 'native-link.private.map')) if x.startswith('-Map=') else x for x in link]
    commands.append(link)
    frozen += [record(x) for x in (a.parent, Path(__file__), ROOT / 'tools/resident_independent_scopes.py',
        original, original_upload, generated, buffer)]
    for index, recipe in enumerate(commands):
        result = subprocess.run(recipe, cwd=ROOT, capture_output=True, timeout=600,
            env=dict(os.environ, TMP=str(a.out / 'tmp'), TEMP=str(a.out / 'tmp')))
        (a.out / f'{index}.private.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(compiled_or_linked=index + 1, total=len(commands), kind=a.kind)), flush=True)
    for row in frozen:
        if record(row['path']) != row:
            raise ValueError('Fresh build input changed: ' + row['path'])
    receipt = copy.deepcopy(prior)
    replacement = next(row for row in receipt['bounded_model_source_overrides']['objects']
        if row['source'] == upload['source'])
    replacement.update(object=record(buffer_obj), actual_source=record(buffer), command=buffer_command)
    if a.reuse_buffer_receipt:
        replacement['actual_source'] = reused['source']
    receipt.update(artifact=record(image), link_command=link, compile_commands=[command],
        source_parent=record(a.parent), inputs_before=frozen + [record(obj), record(buffer_obj)],
        historical_input_aliases=historical, input_hashes_stable=True, link_returncode=0,
        independent_resident_scope=dict(kind=a.kind, model_precision_changed=False,
            original_context_tokens=256, original_prefill=4, full_vocabulary_reference_rows=23,
            original_maximum_output_tokens=32, C2_required_before_prefix=False,
            original_GPU_floor_unchanged=True, generated=record(generated),
            upload=dict(source=replacement['actual_source'], object=record(buffer_obj), command=buffer_command),
            changed_native_objects=2, historical_parent_unmodified=True),
        lossless_driver_table_geometry=audit_linked_storage(image, prior['lossless_driver_tables']))
    receipt['resident_context_reuse']['entry'] = record(generated)
    path = a.out / 'receipt.private.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    receipt['real_module_import_audit'] = audit(a.workspace, a.cache, a.out)
    if receipt['real_module_import_audit']['missing']:
        raise ValueError('Native imports missing')
    receipt['native_dispatch_audit'] = dispatch(a.workspace,
        a.workspace / 'driver-work/PS5-Vulkan-Inference-qwen-872cc126', image, a.out / 'dispatch')
    if not receipt['native_dispatch_audit']['passed']:
        raise ValueError('Native callback dispatch failed')
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(independent_scope_linked=True, kind=a.kind, PS5_operations=0)), flush=True)


if __name__ == '__main__':
    main()
