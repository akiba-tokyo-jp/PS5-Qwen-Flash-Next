#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Graft completed original-BF16 IQ2 Up or uniform Gate/Up packs onto the selected model."""
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
from iq2_up_model_scope import require_gate_input_qualification


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
        need(old['name'] == new['name'] and old['shape'] == new['shape'], 'Only selected tensor type/extent may change')
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


def selected_header(old, parent, retained, name, base_headers=None):
    matches=[h for h in old['precision_overlay']['headers'] if h['file']==name]
    source_parts=retained
    if not matches:
        shared=parent['resident_all_Q8_overlay']
        matches=[h for h in shared['headers'] if h['file']==name]
        source_parts=shared['parts']
    need(len(matches)<=1,'A selected header must be unique')
    if matches:
        original=matches[0];part=source_parts[original['part']]
        with Path(part['path']).open('rb') as source:
            source.seek(original['pack_offset']);raw=source.read(original['bytes'])
        need(hashlib.sha256(raw).hexdigest()==original['sha256'],'The complete selected header SHA differs')
    else:
        if base_headers is None:
            need(record(old['layout']['path'])==old['layout'],'The selected base layout changed')
            base_headers=load(old['layout']['path'])['headers']
            need(record(base_headers['path'])==base_headers,'The selected complete base header pack changed')
        file=next(f for f in old['files'] if f['path']==name);expected=file['parts'][0]
        need(expected['offset']==0 and expected['bytes']==file['header_bytes'],
             'The unchanged base header must have its own exact digest')
        with Path(base_headers['path']).open('rb') as source:
            source.seek(file['header_pack_offset']);raw=source.read(file['header_bytes'])
        need(hashlib.sha256(raw).hexdigest()==expected['sha256'],'The unchanged complete base header differs')
    return raw,base_headers


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'cache', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--encoded-layer', type=Path, action='append', required=True)
    p.add_argument('--completed-encoding-root',type=Path,
        help='Reuse immutable completed coordinator receipts; defer payload rehash to native sealing')
    p.add_argument('--Gate-encoding-root',type=Path,
        help='Add all48 completed Gate encodings after the complete Up prefix')
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
    completed_receipts=[]
    paths=list(a.encoded_layer)
    if a.Gate_encoding_root:
        need(a.completed_encoding_root is not None,'Combined Gate/Up requires immutable original encoding receipts')
        paths += [a.Gate_encoding_root/('gate-'+str(layer).zfill(2))/'result.private.json' for layer in range(48)]
    Gate_input_identity=None
    for path in paths:
        r = load(path)
        role=r['role'];root=a.Gate_encoding_root if role=='gate' else a.completed_encoding_root
        need(r['completed'] and r['complete_layer'] and role in ('up','gate') and r['encoded_Experts'] == 512 and
             r['codec'] == 'IQ2_XXS' and r['logical_shape'] == [2560, 640, 512] and
             r['encoded_row_shape'] == [2560, 640] and not r['paired_original_rows'] and
             not r['host_model_inference'] and r['source_tensor'] == 'blk.' + str(r['layer']) + '.ffn_'+role+'_exps.weight' and
             r['original_BF16_source']['path'].replace('\\', '/').startswith(str(a.cache).replace('\\', '/') + '/converted-bf16-002/'),
             'Only complete directly encoded original-BF16 Up/Gate layers are permitted')
        if role=='gate':
            need(root is not None and r['importance_input_role']=='up','Gate requires the completed identity-qualified encoding stream')
            require_gate_input_qualification(r['Gate_input_identity'])
            if Gate_input_identity is None:Gate_input_identity=r['Gate_input_identity']
            need(r['Gate_input_identity']==Gate_input_identity,'One exact Gate/Up input proof is required')
        if root:
            marker=root/(role+'-'+str(r['layer']).zfill(2)+'.complete.private.json')
            completed=load(marker);pack=Path(r['pack']['path'])
            need(path.resolve()==(root/(role+'-'+str(r['layer']).zfill(2))/'result.private.json').resolve() and
                 completed['job']['layer']==r['layer'] and completed['job']['role']==role and
                 completed['result']==record(path) and completed['pack']==r['pack'] and
                 pack.stat().st_size==216268800 and pack.stat().st_mtime_ns<=marker.stat().st_mtime_ns,
                 'An immutable completed whole-layer encoder receipt and unchanged extent are required')
            completed_receipts.append(record(marker))
        else:
            need(record(r['pack']['path']) == r['pack'] and r['pack']['bytes'] == 216268800,
                 'The complete independently decoded IQ2 layer pack changed')
        encoded.append((path, r))
    encoded.sort(key=lambda item:(item[1]['role']!='up',item[1]['layer']))
    jobs=[(r['role'],r['layer']) for _,r in encoded]
    layers = [r['layer'] for _, r in encoded if r['role']=='up']
    Gate_layers=[r['layer'] for _,r in encoded if r['role']=='gate']
    need(len(jobs)==len(set(jobs)) and all(0<=n<48 for _,n in jobs) and layers,'Unique trunk Up/Gate layers required')
    need(not Gate_layers or Gate_layers==layers==list(range(48)),
         'Only the complete uniform48+48 Gate/Up layout may extend the Up prefix')
    need(all(r['importance'] == encoded[0][1]['importance'] and r['reference_library'] == encoded[0][1]['reference_library']
             for _, r in encoded), 'One actual prefill-only calibration and pinned codec required')
    a.out.mkdir(parents=True, exist_ok=False)
    candidate = copy.deepcopy(old)
    detail = candidate['precision_overlay']
    before = {t['name']: t for t in old['tensors']}
    tensors = {t['name']: t for t in candidate['tensors']}
    retained = copy.deepcopy(detail['parts'])
    for r in retained:
        if a.completed_encoding_root:
            need(Path(r['path']).stat().st_size==r['bytes'],'A selected retained precision extent changed')
        else:
            need(record(r['path']) == r, 'A selected retained precision part changed')
    parts = retained.copy()
    changed_files = set()
    for path, r in encoded:
        name = r['source_tensor']
        original, target = before[name], tensors[name]
        need(original['type'] == 'Q2_K' and original['shape'] == [2560, 640, 512] and original['bytes'] == 275251200,
             'The original selected Up/Gate geometry changed')
        index = len(parts)
        parts.append(r['pack'])
        target.update(type='IQ2_XXS', bytes=r['pack']['bytes'], payload_sha256=r['pack']['sha256'])
        detail['tensors'].append(dict(name=name, part=index, pack_offset=0, bytes=target['bytes'],
            original_bytes=original['bytes'], parent_payload_sha256=original['payload_sha256'],
            payload_sha256=target['payload_sha256'], type='IQ2_XXS',
            original_BF16_encoding=record(path), original_BF16_direct_quantization=True))
        changed_files.add(original['file'])
    header_path = a.out / ('IQ2-Gate-Up-headers.bin' if Gate_layers else 'IQ2-Up-headers.bin')
    header_index = len(parts)
    rebuilt = []
    base_headers=None
    with header_path.open('xb') as stream:
        for name in sorted(changed_files):
            raw,base_headers=selected_header(old,parent,retained,name,base_headers)
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
    detail.update(mode='dense-Q4-and-IQ2-Gate-Up' if Gate_layers else 'dense-Q4-and-IQ2-Up', parts=parts,
                  saved_payload_bytes=detail['saved_payload_bytes'] + len(jobs) * (275251200 - 216268800),
                  IQ2_Up_layers=sorted(layers), prefill_only_importance=encoded[0][1]['importance'],
                  current_Q2_requantization=False, original_selected_cache_slots=3712,
                  old_bundle_payloads_compatible=False)
    if Gate_layers:detail.update(IQ2_Gate_layers=Gate_layers,Gate_input_identity=Gate_input_identity)
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
        IQ2_Gate_layers=Gate_layers,Gate_payload_saved_bytes=len(Gate_layers)*58982400,Gate_input_identity=Gate_input_identity,
        all_changed_headers_independently_parsed=True, old_bundle_payloads_must_be_rebuilt_or_disabled=True,
        completed_encoding_receipts=completed_receipts,
        selected_base_header_pack=base_headers,
        selected_parent_shared_Q8_headers_preserved=True,
        host_payload_rehash_deferred_to_native_sealing=bool(a.completed_encoding_root),
        complete_native_SHA256_EOF_sealing_required_before_model_admission=True,
        other_payload_types_and_shapes_preserved=True, PS5_operations=0,
        native_source_publication_and_model_quality_and_rate_qualified=False))
    print(json.dumps(dict(completed=True, IQ2_Up_layers=sorted(layers), new_parts=len(parts)-len(retained),
                          PS5_operations=0, native_qualified=False)))


if __name__ == '__main__':
    main()
