#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a source-bound paired IQ2 carrier for the existing Q2_0 plane ABI."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from build_iq2_paired_down import table
from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load, need, save

PLANE = 460800
PAYLOAD = 422400
HEADER = 64
TABLES = 2560
MAGIC = (0x32495751, 0x4e574f44, 0x31524950, 0x53585832)


def carrier(payload, tables):
    need(len(payload) == PAYLOAD and len(tables) == TABLES, 'One complete paired IQ2 plane/codebook required')
    header = struct.pack('<H4III', 0x7e00, *MAGIC, 1, PAYLOAD)
    out = header + bytes(HEADER - len(header)) + payload + tables
    need(len(out) <= PLANE and (HEADER + PAYLOAD) % 4 == 0, 'The original plane must contain all encoded bytes/tables')
    return out + bytes(PLANE - len(out))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cache', 'encoded-layer', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    encoded = load(a.encoded_layer)
    need(encoded['completed'] and encoded['complete_layer'] and encoded['role'] == 'down' and
         encoded['paired_original_rows'] and encoded['encoded_row_shape'] == [1280, 1280] and
         encoded['codec'] == 'IQ2_XXS' and encoded['encoded_Experts'] == 512 and
         record(encoded['pack']['path']) == encoded['pack'], 'Complete original-BF16 paired Down encoding required')
    common = a.cache / ('upstream/llama.cpp-' + REVISION) / 'ggml/src/ggml-common.h'
    text = common.read_text()
    grid = table(text, 'uint64_t', 'iq2xxs_grid', 256)
    signs = table(text, 'uint8_t', 'ksigns_iq2xs', 128)
    tables = struct.pack('<256Q128I', *grid, *signs)
    need(len(tables) == TABLES, 'Exact pinned codebook buffer geometry required')
    a.out.mkdir(parents=True, exist_ok=False)
    output = a.out / 'paired-IQ2-Q2_0-carrier.bin'
    planes = []
    with Path(encoded['pack']['path']).open('rb') as source, output.open('xb') as target:
        for i in range(512):
            payload = source.read(PAYLOAD)
            need(hashlib.sha256(payload).hexdigest() == encoded['Experts'][i]['encoded_SHA256'], 'A complete encoded Expert changed')
            raw = carrier(payload, tables)
            target.write(raw)
            planes.append(hashlib.sha256(raw).hexdigest())
        need(not source.read(1), 'The complete original IQ2 pack must end exactly')
    # Independently read back complete carrier extents and inverse-extract both
    # payload and tables. This never quantizes or executes the model again.
    with output.open('rb') as stream, Path(encoded['pack']['path']).open('rb') as original:
        for i in range(512):
            raw = stream.read(PLANE)
            need(hashlib.sha256(raw).hexdigest() == planes[i] and raw[HEADER:HEADER+PAYLOAD] == original.read(PAYLOAD) and
                 raw[HEADER+PAYLOAD:HEADER+PAYLOAD+TABLES] == tables and
                 struct.unpack_from('<H4III', raw) == (0x7e00, *MAGIC, 1, PAYLOAD) and
                 not any(raw[26:HEADER]) and not any(raw[HEADER+PAYLOAD+TABLES:]), 'Complete independent carrier inverse differs')
        need(not stream.read(1), 'The complete carrier must end exactly')
    save(a.out / 'result.private.json', dict(completed=True, encoded_layer=record(a.encoded_layer), pack=record(output),
        pinned_codebook_source=record(common), codebook_SHA256=hashlib.sha256(tables).hexdigest(),
        role='down', layer=encoded['layer'], planes=512, plane_bytes=PLANE, IQ2_payload_bytes_per_plane=PAYLOAD,
        IQ2_payload_offset=HEADER, codebook_offset=HEADER+PAYLOAD, plane_SHA256=planes,
        original_encoded_bytes_preserved=True, all_complete_carriers_independently_inverse_verified=True,
        Q2_0_carrier_type_is_not_the_encoded_weight_format=True, encoded_format='paired-row IQ2_XXS',
        compressed_cache_or_IO_saving_claimed=False, native_model_integration_and_GPU_qualified=False,
        PS5_operations=0, model_inference=False))
    print(json.dumps(dict(completed=True, layer=encoded['layer'], carriers=512, GPU_qualified=False, PS5_operations=0)))


if __name__ == '__main__':
    main()
