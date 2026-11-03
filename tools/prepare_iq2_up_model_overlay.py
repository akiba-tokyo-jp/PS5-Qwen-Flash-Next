#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Graft completed original-BF16 IQ2 Up packs onto the exact selected model."""
import argparse
import ast
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import types

from audit_shared_q8_headers import parse
from build_performance_quantizer import record
from resident_all_q8 import placement
from start_success_route import load, need, save
from prepare_shared_q4 import REVISION


def literal(header, name):
    rows = re.findall(r'inline constexpr const char\*' + re.escape(name) + r'=(.*);', header)
    need(len(rows) == 1, 'One exact selected metadata literal required')
    return ast.literal_eval(rows[0])


def rewrite_header(raw, before, after, kinds):
    """Match complete serialized descriptors before changing their type/offset."""
    parsed = parse(raw)
    need(len(parsed) == len(before) == len(after), 'Every original descriptor must be preserved')
    out = bytearray(raw)
    cursor = len(raw)
    for old, new, serialized in zip(before, after, parsed):
        need(serialized == (old['name'], old['shape'], kinds[old['type']], old['offset'] - len(raw)),
             'The selected complete GGUF header differs from its receipt')
        need(old['name'] == new['name'] and old['shape'] == new['shape'], 'Only Up type/extent may change')
        name = old['name'].encode()
        prefix = struct.pack('<Q', len(name)) + name + struct.pack('<I', len(old['shape']))
        prefix += struct.pack('<' + 'Q' * len(old['shape']), *old['shape'])
        descriptor = prefix + struct.pack('<IQ', kinds[old['type']], old['offset'] - len(raw))
        need(raw.count(descriptor) == 1, 'One complete immutable tensor descriptor required')
        at = raw.index(descriptor) + len(prefix)
        struct.pack_into('<IQ', out, at, kinds[new['type']], cursor - len(raw))
        new['offset'] = cursor
        cursor += new['bytes']
        need(cursor % 32 == 0, 'Every compact tensor must retain the original GGUF alignment')
    expected = [(t['name'], t['shape'], kinds[t['type']], t['offset'] - len(raw)) for t in after]
    need(parse(out) == expected, 'Independent complete serialized header readback failed')
    return bytes(out), cursor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'cache', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--encoded-layer', type=Path, action='append', required=True)
    a = p.parse_args()
    selected = load(a.current / 'provenance/selected-entry-build.private.json')
    policy = load(selected['application_policy']['path'])
    directory = Path(policy['source']['path']).parent
    header = directory / 'precision-plan.private.h'
    text = header.read_text()
    old_raw = literal(text, 'precision_candidate_raw')
    parent_raw = literal(text, 'precision_parent_raw')
    old, parent = json.loads(old_raw), json.loads(parent_raw)
    need(hashlib.sha256(old_raw.encode()).hexdigest() == literal(text, 'precision_candidate_sha256') and
         hashlib.sha256(parent_raw.encode()).hexdigest() == literal(text, 'precision_parent_sha256'),
         'Exact selected embedded metadata digests required')
    need(old['precision_candidate'] == 'dense-Q4' and len(old['precision_overlay']['tensors']) == 109,
         'Only the selected complete109-tensor overlay may be extended')
    package = types.ModuleType('gguf')
    package.__path__ = [str(a.cache / ('upstream/llama.cpp-' + REVISION) / 'gguf-py/gguf')]
    sys.modules['gguf'] = package
    from gguf.constants import GGMLQuantizationType as Type
    kinds = {v.name: int(v) for v in Type}
    encoded = []
    for path in a.encoded_layer:
        r = load(path)
        need(r['completed'] and r['complete_layer'] and r['role'] == 'up' and r['encoded_Experts'] == 512 and
             r['codec'] == 'IQ2_XXS' and r['logical_shape'] == [2560, 640, 512] and
             r['encoded_row_shape'] == [2560, 640] and not r['paired_original_rows'] and
             not r['host_model_inference'] and r['source_tensor'] == 'blk.' + str(r['layer']) + '.ffn_up_exps.weight' and
             r['original_BF16_source']['path'].replace('\\', '/').startswith(str(a.cache).replace('\\', '/') + '/converted-bf16-002/'),
             'Only complete directly encoded original-BF16 Up layers are permitted')
        need(record(r['pack']['path']) == r['pack'] and r['pack']['bytes'] == 216268800,
             'The complete independently decoded IQ2 layer pack changed')
        encoded.append((path, r))
    layers = [r['layer'] for _, r in encoded]
    need(len(layers) == len(set(layers)) and all(0 <= n < 48 for n in layers), 'Unique trunk Up layers required')
    need(all(r['importance'] == encoded[0][1]['importance'] and r['reference_library'] == encoded[0][1]['reference_library']
             for _, r in encoded), 'One actual prefill-only calibration and pinned codec required')
    a.out.mkdir(parents=True, exist_ok=False)
    candidate = copy.deepcopy(old)
    detail = candidate['precision_overlay']
    before = {t['name']: t for t in old['tensors']}
    tensors = {t['name']: t for t in candidate['tensors']}
    retained = copy.deepcopy(detail['parts'])
    for r in retained:
        need(record(r['path']) == r, 'A selected retained precision part changed')
    parts = retained.copy()
    changed_files = set()
    for path, r in encoded:
        name = 'blk.' + str(r['layer']) + '.ffn_up_exps.weight'
        original, target = before[name], tensors[name]
        need(original['type'] == 'Q2_K' and original['shape'] == [2560, 640, 512] and original['bytes'] == 275251200,
             'The original selected Up geometry changed')
        index = len(parts)
        parts.append(r['pack'])
        target.update(type='IQ2_XXS', bytes=r['pack']['bytes'], payload_sha256=r['pack']['sha256'])
        detail['tensors'].append(dict(name=name, part=index, pack_offset=0, bytes=target['bytes'],
            original_bytes=original['bytes'], parent_payload_sha256=original['payload_sha256'],
            payload_sha256=target['payload_sha256'], type='IQ2_XXS',
            original_BF16_encoding=record(path), original_BF16_direct_quantization=True))
        changed_files.add(original['file'])
    header_path = a.out / 'IQ2-Up-headers.bin'
    header_index = len(parts)
    rebuilt = []
    with header_path.open('xb') as stream:
        for name in sorted(changed_files):
            matches = [h for h in old['precision_overlay']['headers'] if h['file'] == name]
            need(len(matches) == 1, 'The selected complete original header must be present')
            original = matches[0]
            part = retained[original['part']]
            with Path(part['path']).open('rb') as source:
                source.seek(original['pack_offset'])
                raw = source.read(original['bytes'])
            need(hashlib.sha256(raw).hexdigest() == original['sha256'], 'The complete original header SHA differs')
            left = [t for t in old['tensors'] if t['file'] == name]
            right = [t for t in candidate['tensors'] if t['file'] == name]
            raw, end = rewrite_header(raw, left, right, kinds)
            limit = next(f['bytes'] for f in old['files'] if f['path'] == name)
            need(end <= limit, 'The changed compact metadata exceeds the original logical file')
            stream.write(bytes((-stream.tell()) % 16384))
            at = stream.tell()
            stream.write(raw)
            rebuilt.append(dict(file=name, part=header_index, pack_offset=at, bytes=len(raw),
                                sha256=hashlib.sha256(raw).hexdigest()))
    parts.append(record(header_path))
    detail['headers'] = [h for h in detail['headers'] if h['file'] not in changed_files] + rebuilt
    detail.update(mode='dense-Q4-and-IQ2-Up', parts=parts,
                  saved_payload_bytes=detail['saved_payload_bytes'] + len(layers) * (275251200 - 216268800),
                  IQ2_Up_layers=sorted(layers), prefill_only_importance=encoded[0][1]['importance'],
                  current_Q2_requantization=False, original_selected_cache_slots=3712,
                  old_bundle_payloads_compatible=False)
    candidate['precision_candidate'] = detail['mode']
    output = a.out / 'model-receipt.json'
    output.write_text(json.dumps(candidate, separators=(',', ':')) + '\n', newline='\n')
    need(output.stat().st_size <= 1 << 20, 'Original native metadata bound must be retained')
    footprint = collections.Counter()
    for t in candidate['tensors']:
        footprint[placement(t['name'])] += t['bytes']
    save(a.out / 'result.private.json', dict(completed=True, selected_header=record(header),
        selected_model_sha256=hashlib.sha256(old_raw.encode()).hexdigest(),
        parent_model_sha256=hashlib.sha256(parent_raw.encode()).hexdigest(), candidate=record(output),
        encoded_layers=[record(path) for path, _ in encoded], IQ2_Up_layers=sorted(layers),
        selected_tensors=len(detail['tensors']), retained_precision_parts=retained,
        new_parts=parts[len(retained):], footprint=dict(footprint),
        Up_payload_saved_bytes=len(layers) * 58982400,
        all_changed_headers_independently_parsed=True, old_bundle_payloads_must_be_rebuilt_or_disabled=True,
        other_payload_types_and_shapes_preserved=True, PS5_operations=0,
        native_source_publication_and_model_quality_and_rate_qualified=False))
    print(json.dumps(dict(completed=True, IQ2_Up_layers=sorted(layers), new_parts=len(parts)-len(retained),
                          PS5_operations=0, native_qualified=False)))


if __name__ == '__main__':
    main()
