#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Convert only the installed model's remaining resident BF16 tensors to Q8_0."""
import argparse
import collections
import copy
import hashlib
import json
import struct
import sys
import types
import zipfile
from pathlib import Path

from expert_q4 import LOCK, record, require, write_json
from resident_all_q8 import PARENT_SHA256, EXPECTED_Q8_BYTES, selection, stored_shape


class Parts:
    """Keep each independently sealed source below the existing512 MiB limit."""
    def __init__(self, out):
        self.out, self.parts, self.stream = out, [], None

    def allocate(self, count):
        require(0 < count <= 512 << 20, 'One payload must fit a bounded part')
        if self.stream is None or ((self.stream.tell() + 16383) // 16384 * 16384 + count > 512 << 20):
            if self.stream:
                self.stream.close()
            path = self.out / f'resident-all-Q8.part{len(self.parts)}.bin'
            self.parts.append(path)
            self.stream = path.open('xb')
        self.stream.write(bytes((-self.stream.tell()) % 16384))
        return len(self.parts) - 1, self.stream.tell()

    def close(self):
        if self.stream:
            self.stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cache', 'parent', 'original', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    parent_record = record(args.parent)
    require(parent_record['sha256'] == PARENT_SHA256, 'Exact installed shared-Q8 parent required')
    parent = json.loads(args.parent.read_text())
    chosen = selection(parent)
    revision = LOCK['llama_cpp']['revision']
    upstream = args.cache / 'upstream' / ('llama.cpp-' + revision)
    archive = args.cache / ('llama-' + revision + '.zip')
    require(record(archive)['sha256'] == LOCK['llama_cpp']['archive_sha256'], 'Pinned quantizer archive required')
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if '/gguf-py/gguf/' in name and name.endswith('.py'):
                require((upstream / 'gguf-py' / name.split('/gguf-py/', 1)[1]).read_bytes() == bundle.read(name), 'Pinned GGUF module changed')
    package = types.ModuleType('gguf')
    package.__path__ = [str(upstream / 'gguf-py/gguf')]
    sys.modules['gguf'] = package
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import Q8_0
    import numpy as np

    args.out.mkdir(parents=True, exist_ok=False)
    candidate = copy.deepcopy(parent)
    # These audit-only inherited values remain bound by the complete parent
    # digest and the compiled parent receipt. Do not duplicate them in metadata.
    candidate.pop('original_BF16_receipt')
    candidate.pop('resident_Q8_overlay')
    changes, headers = [], []
    tensors = {t['name']: t for t in candidate['tensors']}
    grouped = collections.defaultdict(list)
    for tensor in chosen:
        grouped[tensor['file']].append(tensor)
    parts = Parts(args.out)
    try:
        for filename, rows in grouped.items():
            path = args.original / filename
            identity = path.stat()
            reader = GGUFReader(path, 'r')
            originals = {t.name: t for t in reader.tensors}
            with path.open('rb') as source:
                header = bytearray(source.read(reader.data_offset))
                for tensor in rows:
                    original = originals[tensor['name']]
                    require(original.tensor_type == Type.BF16 and list(original.shape) == tensor['shape'] and int(original.n_bytes) == tensor['bytes'], 'Original BF16 tensor geometry changed')
                    count = tensor['bytes'] // 64 * 34
                    part, offset = parts.allocate(count)
                    source.seek(original.data_offset)
                    old_hash, new_hash = hashlib.sha256(), hashlib.sha256()
                    left, squared, norm, maximum = tensor['bytes'], 0., 0., 0.
                    while left:
                        raw = source.read(min(1 << 20, left))
                        require(len(raw) > 0 and len(raw) % 64 == 0, 'Complete bounded BF16 blocks required')
                        left -= len(raw)
                        old_hash.update(raw)
                        values = (np.frombuffer(raw, dtype='<u2').astype('<u4') << 16).view('<f4').reshape(-1, 32)
                        require(np.isfinite(values).all(), 'Nonfinite original weight')
                        quantized = Q8_0.quantize_blocks(values)
                        data = quantized.tobytes()
                        parts.stream.write(data)
                        new_hash.update(data)
                        decoded = quantized[:, :2].copy().view('<f2').astype('<f4') * quantized[:, 2:].copy().view(np.int8).astype('<f4')
                        require(np.isfinite(decoded).all(), 'Q8 scales must decode to finite weights')
                        difference = decoded.astype(np.float64) - values
                        maximum = max(maximum, float(np.max(np.abs(difference))))
                        squared += float(np.sum(difference ** 2))
                        norm += float(np.sum(values.astype(np.float64) ** 2))
                    require(old_hash.hexdigest() == tensor['payload_sha256'], 'Original BF16 payload differs from the installed parent')
                    require(parts.stream.tell() == offset + count, 'Complete Q8 tensor length differs')
                    target = tensors[tensor['name']]
                    target.update(type='Q8_0', shape=stored_shape(tensor), bytes=count, payload_sha256=new_hash.hexdigest())
                    changes.append(dict(name=tensor['name'], part=part, pack_offset=offset, original_bytes=tensor['bytes'], bytes=count,
                                        parent_payload_sha256=tensor['payload_sha256'], payload_sha256=new_hash.hexdigest(),
                                        maximum_absolute_weight_error=maximum, relative_weight_RMSE=(squared / norm) ** .5 if norm else 0.))
            # Rebuild all tensor descriptors from the effective installed types,
            # including unchanged Q2 experts and already converted shared Q8.
            cursor = reader.data_offset
            for tensor in candidate['tensors']:
                if tensor['file'] != filename:
                    continue
                original = originals[tensor['name']]
                field = int(original.field.offset) + 8 + len(tensor['name'].encode())
                require(len(tensor['shape']) == len(original.shape), 'Tensor rank must remain fixed')
                struct.pack_into('<I', header, field, len(tensor['shape']))
                struct.pack_into('<' + 'Q' * len(tensor['shape']), header, field + 4, *tensor['shape'])
                field += 4 + 8 * len(tensor['shape'])
                struct.pack_into('<IQ', header, field, int(Type[tensor['type']]), cursor - reader.data_offset)
                tensor['offset'] = cursor
                cursor += tensor['bytes']
                require(cursor % 32 == 0, 'Unaligned compact GGUF tensor')
            old_file = next(f for f in parent['files'] if f['path'] == filename)
            require(cursor <= old_file['bytes'], 'Compacted data exceeds its immutable parent range')
            part, offset = parts.allocate(len(header))
            parts.stream.write(header)
            headers.append(dict(file=filename, part=part, pack_offset=offset, bytes=len(header), sha256=hashlib.sha256(header).hexdigest()))
            after = path.stat()
            require((identity.st_size, identity.st_mtime_ns, identity.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino), 'Original source changed during conversion')
            del originals, reader
            print(json.dumps(dict(resident_Q8_tensors=len(changes), total=len(chosen), PS5_operations=0)), flush=True)
    finally:
        parts.close()
    total_old = sum(c['original_bytes'] for c in changes)
    total_new = sum(c['bytes'] for c in changes)
    require(total_new == EXPECTED_Q8_BYTES, 'Complete resident Q8 payload size differs')
    candidate['schema'] = 'ps5-qwen-all-resident-Q8-overlay-v1'
    candidate['non_Expert_except_output_and_shared_payload_bytes_preserved'] = False
    candidate['resident_all_Q8_overlay'] = dict(schema='ps5-qwen-all-resident-Q8-overlay-v1', parent={k:v for k,v in parent_record.items() if k != 'path'},
        tensors=changes, headers=headers, parts=[record(path) for path in parts.parts], saved_resident_payload_bytes=total_old-total_new,
        pinned_quantizer_revision=revision, original_Expert_payloads_preserved=True, F32_activation_input_required=True,
        KV_precision_preserved=True, logical_file_lengths_preserved=True, tensor_offsets_compacted=True,
        narrow_convolution_BF16_preserved=True)
    target = args.out / 'model-receipt.json'
    target.write_text(json.dumps(candidate, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    require(target.stat().st_size <= 1 << 20, 'Keep the original1 MiB native receipt limit')
    write_json(args.out / 'receipt.private.json', dict(completed=True, parent=parent_record, candidate=record(target),
        parts=[record(path) for path in parts.parts], selected_tensors=len(changes), original_BF16_bytes=total_old,
        Q8_bytes=total_new, saved_resident_payload_bytes=total_old-total_new, serialized_headers=len(headers),
        Expert_payloads_unchanged=True, mapped_embeddings_and_lazy_PLE_and_MTP_unchanged=True,
        native_GPU_verification_completed=False, production_adopted=False, PS5_operations=0))
    print(json.dumps(dict(resident_Q8_prepared=True, selected_tensors=len(changes), saved_bytes=total_old-total_new, parts=len(parts.parts))))


if __name__ == '__main__':
    main()
