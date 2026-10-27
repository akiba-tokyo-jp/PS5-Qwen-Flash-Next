#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded application-only libc parameter experiment; never edit driver inputs."""
import hashlib
import struct

OLD = ('    write_u64(result.data, result.heap_size, std::numeric_limits<std::uint64_t>::max());\n'
       '    write_u32(result.data, result.heap_extended, 1);')


def specialize(source, heap_bytes):
    if type(heap_bytes) is not int or not 2 << 20 <= heap_bytes <= 64 << 20 or heap_bytes % (2 << 20):
        raise ValueError('Experimental libc heap must be 2..64 MiB in 2 MiB steps')
    if source.count(OLD) != 1:
        raise ValueError('Original driver parameter constructor changed')
    return source.replace(OLD, f'    write_u64(result.data, result.heap_size, {heap_bytes}ULL);\n'
                          '    write_u32(result.data, result.heap_extended, 0);')


def parameter_block(heap_bytes, extended):
    sizes = (0xa8, 0x38, 0x10, 0x78, 0xc0, 0x38)
    counts = (0x10000000e, 0, 0, 2, 3, 1)
    data = bytearray(sum(sizes) + 16)
    at = 0
    for size, count in zip(sizes, counts):
        struct.pack_into('<QQ', data, at, size, count)
        at += size
    struct.pack_into('<QI', data, at, heap_bytes, extended)
    return bytes(data)


def verify_data_only(control, candidate, heap_bytes):
    """Require the complete converted ELF to differ only in these two scalars."""
    old = parameter_block((1 << 64) - 1, 1)
    new = parameter_block(heap_bytes, 0)
    if control.count(old) != 1:
        raise ValueError('Unique original process parameter block required')
    at = control.index(old)
    expected = bytearray(control[:at] + new + control[at + len(old):])
    # The original converter recomputes two build-ID note payloads from SHA1
    # of the complete output with both payloads zero. Verify that exact rule;
    # no executable or other data difference is permitted.
    notes = []
    for name, size, count in ((b'GNU\0', 0x14, 16), (b'SIE\0', 8, 8)):
        prefix = struct.pack('<III', 4, size, 3) + name
        if control.count(prefix) != 1:
            raise ValueError('Unique original converter build-ID notes required')
        offset = control.index(prefix) + 16
        notes.append((offset, count))
        expected[offset:offset + count] = bytes(count)
    digest = hashlib.sha1(expected).digest()
    for offset, count in notes:
        expected[offset:offset + count] = digest[:count]
    if candidate != expected:
        raise ValueError('Converted ELF changed outside the explicit libc parameter scalars')
    return dict(whole_ELF_data_only_difference_passed=True, heap_bytes=heap_bytes,
                extended_allocation=False, changed_scalar_bytes=12,
                original_converter_build_ID_recomputation_verified=True,
                executable_code_and_original_driver_objects_unchanged=True)
