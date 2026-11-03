#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bound a CPU-only application's libc heap in the qualified writer's layout."""
import struct


def bind_heap(raw, heap_bytes):
    if heap_bytes != 8 << 20:
        raise ValueError('Only the explicit8MiB CPU-only experiment is admitted')
    if raw[:6] != b'\x7fELF\x02\x01' or len(raw) < 64:
        raise ValueError('A complete little-endian ELF64 is required')
    phoff = struct.unpack_from('<Q', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 54)
    if stride != 56 or not count or phoff + count * stride > len(raw):
        raise ValueError('Complete native program headers required')
    headers = [struct.unpack_from('<IIQQQQQQ', raw, phoff + i * stride) for i in range(count)]
    matches = [h for h in headers if h[0] == 0x61000001]
    if len(matches) != 1:
        raise ValueError('One native process parameter block required')
    _, _, offset, address, _, size, _, _ = matches[0]
    total = 0x60 + 0x260 + 16
    if size != 0x60 or offset + total > len(raw) or raw[offset + 8:offset + 12] != b'ORBI':
        raise ValueError('Qualified process parameter geometry required')
    if struct.unpack_from('<Q', raw, offset)[0] != 0x60:
        raise ValueError('Qualified process parameter size required')
    if not any(h[0] == 1 and h[2] <= offset and offset + total <= h[2] + h[5] for h in headers):
        raise ValueError('Every parameter byte must be inside one actual LOAD segment')
    blocks, blocks_address = offset + 0x60, address + 0x60
    cursor = 0
    for block_size, block_count in zip((0xa8, 0x38, 0x10, 0x78, 0xc0, 0x38),
                                       (0x10000000e, 0, 0, 2, 3, 1)):
        if struct.unpack_from('<QQ', raw, blocks + cursor) != (block_size, block_count):
            raise ValueError('Qualified libc/thread parameter blocks required')
        cursor += block_size
    for target, value in ((address + 0x38, blocks_address),
                          (blocks_address + 0x10, blocks_address + 0x260),
                          (blocks_address + 0x20, blocks_address + 0x268)):
        if raw.count(struct.pack('<QQQ', target, 8, value)) != 1:
            raise ValueError('Exact relative parameter pointer required')
    heap_offset = blocks + cursor
    if struct.unpack_from('<QI', raw, heap_offset) != (0xffffffffffffffff, 1):
        raise ValueError('Only the original unlimited heap with extension1 may change')
    output = bytearray(raw)
    struct.pack_into('<Q', output, heap_offset, heap_bytes)
    return bytes(output), dict(heap_size_file_offset=heap_offset, original_heap_size=0xffffffffffffffff,
                              selected_heap_size=heap_bytes, extended_allocation_flag=1,
                              changed_parameter_bytes=8, all_other_file_bytes_unchanged=True,
                              actual_memory_reduction_measured=False)
