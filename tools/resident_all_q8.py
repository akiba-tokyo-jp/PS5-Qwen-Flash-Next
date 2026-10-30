# SPDX-License-Identifier: MIT
"""Precision and placement rules for the remaining resident BF16 weights."""
import re

PARENT_SHA256 = '7ba7bbf919eba43a365f570930558b9405b60ad66f9e3cdeea104ce5557377fb'
CONV = 'blk.1.ple_conv1d.weight'
EXPECTED_COUNT = 544
EXPECTED_BF16_BYTES = 6749552640
EXPECTED_Q8_BYTES = EXPECTED_BF16_BYTES // 64 * 34


def placement(name):
    layer = re.match(r'^blk\.(\d+)\.', name)
    if layer and int(layer[1]) >= 48:
        return 'skipped_mtp'
    if name == 'per_layer_token_embd.weight':
        return 'lazy_ple'
    if name == 'token_embd.weight':
        return 'mapped_embeddings'
    if '.ffn_' in name and '_exps.weight' in name:
        return 'mapped_experts'
    return 'device_weights'


def selected(tensor):
    return tensor['type'] == 'BF16' and tensor['name'] != CONV and placement(tensor['name']) == 'device_weights'


def stored_shape(tensor):
    shape = tensor['shape']
    if shape[0] % 32 == 0:
        return shape.copy()
    raise ValueError('The narrow PLE convolution must retain its original BF16 layout')


def selection(receipt):
    tensors = [t for t in receipt['tensors'] if selected(t)]
    if len(tensors) != EXPECTED_COUNT or sum(t['bytes'] for t in tensors) != EXPECTED_BF16_BYTES:
        raise ValueError('The installed resident BF16 selection changed')
    for tensor in tensors:
        stored_shape(tensor)
    return tensors
