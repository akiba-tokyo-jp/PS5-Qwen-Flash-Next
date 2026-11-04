#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Encode the 144 current shared projections from authenticated original BF16."""
import argparse
import collections
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import types

from build_performance_quantizer import record

ROOT = Path(__file__).resolve().parents[1]
REVISION = '0a1ef309cdbb9f2024f58a38fb4c42352c5db569'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'cache', 'reference', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    up = args.cache / ('upstream/llama.cpp-' + REVISION)
    package = types.ModuleType('gguf')
    package.__path__ = [str(up / 'gguf-py/gguf')]
    sys.modules['gguf'] = package
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import Q4_0, Q8_0
    import numpy as np

    reference = load(args.reference)
    assert record(reference['library']['path']) == reference['library']
    dll_directory = os.add_dll_directory(str(args.workspace / 'toolchain/msys-clang64/clang64/bin'))
    library = ctypes.CDLL(reference['library']['path'])
    quantize = library.ggml_quantize_chunk
    quantize.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p]
    quantize.restype = ctypes.c_size_t
    encoder = args.out / 'independent-q4.dll'
    compiler = args.workspace / 'toolchain/msys-clang64/clang64/bin/clang.exe'
    command = [str(compiler), '-std=c11', '-O3', '-shared', str(ROOT / 'tools/expert_q4_quantize.c'), '-o', str(encoder)]
    run = subprocess.run(command, capture_output=True, timeout=120)
    (args.out / 'encoder-build.private.log').write_bytes(run.stdout + run.stderr)
    assert run.returncode == 0, run.stderr.decode(errors='replace')[-3000:]
    independent_library = ctypes.CDLL(str(encoder))
    independent = independent_library.qwen_quantize_bf16_q4_0
    independent.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
    independent.restype = ctypes.c_int

    current_path = args.cache / 'Post-top2-output-Q4-32100/model-receipt.json'
    current = load(current_path)
    assert record(current_path)['sha256'] == '46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426'
    shared = load(args.cache / 'resident-shared-Q8-10450/model-receipt.json')
    known = {row['name']: row for row in shared['resident_Q8_overlay']['tensors']}
    chosen = [t for t in current['tensors'] if re.fullmatch(r'blk\.(?:[0-9]|[1-3][0-9]|4[0-7])\.ffn_(?:gate|up|down)_shexp\.weight', t['name'])]
    assert len(chosen) == 144 and all(t['type'] == 'Q8_0' for t in chosen)
    assert sum(t['bytes'] for t in chosen) == 250675200
    original_receipt = load(args.cache / 'converted-bf16-002/model-receipt.json')
    assert original_receipt['original_shards_verified'] and not original_receipt['learned_inference_performed']
    assert original_receipt['upstream_revision'] == REVISION
    original_files = {r['path']: r for r in original_receipt['files']}
    by_file = collections.defaultdict(list)
    for row in chosen:
        by_file[row['file']].append(row)
    candidate = copy.deepcopy(current)
    candidate_tensors = {r['name']: r for r in candidate['tensors']}
    pack_path = args.out / 'shared-q4.bin'
    changes = []
    headers = []
    with pack_path.open('xb') as output, (args.cache / 'resident-shared-Q8-10450/resident-shared-Q8.bin').open('rb') as control:
        for filename, tensors in by_file.items():
            source = args.cache / 'converted-bf16-002' / filename
            before = source.stat()
            assert before.st_size == original_files[filename]['bytes']
            reader = GGUFReader(source, 'r')
            originals = {t.name: t for t in reader.tensors}
            assert reader.byte_order == 'I' and reader.data_offset <= 32 << 20
            with source.open('rb') as stream:
                header = bytearray(stream.read(reader.data_offset))
            for target in tensors:
                tensor = originals[target['name']]
                assert tensor.tensor_type == Type.BF16 and list(tensor.shape) == target['shape']
                original = np.ascontiguousarray(tensor.data).view(np.uint16).reshape(-1)
                assert original.nbytes == known[target['name']]['original_bytes']
                assert sha(original.tobytes()) == known[target['name']]['parent_payload_sha256']
                values = (original.astype(np.uint32) << 16).view(np.float32)
                assert np.isfinite(values).all() and values.size == 2560 * 640
                encoded = np.empty(values.size // 32 * 18, dtype=np.uint8)
                width = target['shape'][0]
                count = quantize(int(Type.Q4_0), values.ctypes.data, encoded.ctypes.data, 0, values.size // width, width, None)
                assert count == encoded.nbytes
                checked = np.empty_like(encoded)
                assert independent(original.ctypes.data, checked.ctypes.data, original.size) == 0
                assert np.array_equal(encoded, checked), 'Pinned and independent Q4 encoders differ'
                control.seek(known[target['name']]['pack_offset'])
                control_raw = control.read(target['bytes'])
                assert len(control_raw) == target['bytes'] and sha(control_raw) == target['payload_sha256']
                decoded = Q4_0.dequantize(encoded.reshape(-1, 18)).reshape(-1).astype(np.float64)
                decoded_control = Q8_0.dequantize(np.frombuffer(control_raw, dtype=np.uint8).reshape(-1, 34)).reshape(-1).astype(np.float64)
                original_values = values.astype(np.float64)
                norm = float(np.dot(original_values, original_values))
                error = float(np.square(decoded - original_values).sum())
                control_error = float(np.square(decoded_control - original_values).sum())
                output.write(bytes((-output.tell()) % 16384))
                offset = output.tell()
                output.write(encoded.tobytes())
                row = dict(name=target['name'], file=filename, shape=target['shape'], type='Q4_0',
                           bytes=count, pack_offset=offset, payload_sha256=sha(encoded.tobytes()),
                           control_type='Q8_0', control_bytes=target['bytes'], control_payload_sha256=target['payload_sha256'],
                           original_BF16_payload_sha256=sha(original.tobytes()),
                           whole_weight_NRMSE=(error / norm) ** .5 if norm else 0.,
                           control_whole_weight_NRMSE=(control_error / norm) ** .5 if norm else 0.)
                changes.append(row)
                candidate_tensors[target['name']].update(type='Q4_0', bytes=count, payload_sha256=row['payload_sha256'])
            cursor = int(reader.data_offset)
            for row in candidate['tensors']:
                if row['file'] != filename:
                    continue
                original = originals[row['name']]
                field = int(original.field.offset) + 8 + len(row['name'].encode())
                assert len(original.shape) == len(row['shape'])
                field += 4 + 8 * len(row['shape'])
                struct.pack_into('<IQ', header, field, int(Type[row['type']]), cursor - reader.data_offset)
                row['offset'] = cursor
                cursor += row['bytes']
                assert cursor % 32 == 0
            assert cursor <= original_files[filename]['bytes']
            path = args.out / filename
            path.write_bytes(header)
            headers.append(dict(file=filename, **record(path)))
            after = source.stat()
            assert (before.st_size, before.st_ino, before.st_mtime_ns) == (after.st_size, after.st_ino, after.st_mtime_ns)
            del reader, originals
            print(json.dumps(dict(candidate='shared-Q4', encoded=len(changes), total=144)), flush=True)
        output.flush()
        os.fsync(output.fileno())
    assert len(changes) == 144 and sum(r['bytes'] for r in changes) == 132710400
    delta = dict(schema='ps5-qwen-shared-Q4-source-delta-v1', control=record(current_path),
                 target='shared-Q4', tensors=changes, headers=headers, pack=record(pack_path),
                 preserve_parent_precision_overlay=True, unchanged_parent_parts=current['precision_overlay']['parts'],
                 saved_payload_bytes=117964800, original_BF16_sources_modified=False,
                 all_144_original_and_control_payload_hashes_verified=True,
                 all_144_pinned_and_independent_encoder_bytes_equal=True,
                 maximum_whole_weight_NRMSE=max(r['whole_weight_NRMSE'] for r in changes),
                 host_model_inference=False, native_inference=False, production_adopted=False,
                 native_source_integration_complete=False, native_quality_and_speed_verification_pending=True,
                 reference=reference['library'], independent_encoder=record(encoder), encoder_command=command)
    (args.out / 'candidate-model.private.json').write_text(json.dumps(candidate, separators=(',', ':')) + '\n', encoding='utf-8')
    (args.out / 'source-delta.private.json').write_text(json.dumps(delta, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: delta[k] for k in ('target', 'saved_payload_bytes', 'maximum_whole_weight_NRMSE',
                                          'all_144_pinned_and_independent_encoder_bytes_equal', 'production_adopted')}), flush=True)
    library.ggml_quantize_free()
    dll_directory.close()


if __name__ == '__main__':
    main()
