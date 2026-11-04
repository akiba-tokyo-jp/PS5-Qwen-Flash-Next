#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove owned, relocation-free read-only pages from ELF LOAD coverage."""
import hashlib
import struct

PAGE = 16384


def headers(raw):
    if raw[:7] != b'\x7fELF\x02\x01\x01' or struct.unpack_from('<H', raw, 18)[0] != 62:
        raise ValueError('An x86-64 little-endian ELF is required')
    offset = struct.unpack_from('<Q', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 54)
    if offset != 64 or stride != 56 or not 0 < count < 32:
        raise ValueError('Unsupported program-header geometry')
    return offset, [struct.unpack_from('<IIQQQQQQ', raw, offset + i * stride) for i in range(count)]


def externalize(raw, begin, size, expected):
    offset, rows = headers(raw)
    if begin % PAGE or not size or size % PAGE or not isinstance(expected, bytes) or len(expected) != size:
        raise ValueError('Exact full owned pages and payload bytes are required')
    end = begin + size
    matches = [(i, h) for i, h in enumerate(rows) if h[0] == 1 and h[3] <= begin and end <= h[3] + h[5]]
    if len(matches) != 1:
        raise ValueError('One file-backed LOAD must contain the complete payload')
    index, selected = matches[0]
    if selected[1] != 4 or selected[5] != selected[6] or selected[7] not in (PAGE, 65536):
        raise ValueError('Only an original read-only, non-executable LOAD may be split')
    cut = selected[2] + begin - selected[3]
    if cut % PAGE or raw[cut:cut + size] != expected:
        raise ValueError('The actual loaded payload or file alignment differs')
    shoff = struct.unpack_from('<Q', raw, 40)[0]
    stride, count, strings_index = struct.unpack_from('<HHH', raw, 58)
    if stride != 64 or not count or strings_index >= count:
        raise ValueError('Complete section metadata is required')
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, shoff + i * stride) for i in range(count)]
    tab = sections[strings_index]
    strings = raw[tab[4]:tab[4] + tab[5]]
    owners = []
    for section in sections:
        if section[1] in (4, 9):
            if section[1] != 4 or section[9] != 24 or section[5] % 24:
                raise ValueError('Unsupported relocation geometry')
            for at in range(section[4], section[4] + section[5], 24):
                location = struct.unpack_from('<Q', raw, at)[0]
                if location < end and begin < location + 8:
                    raise ValueError('A relocation writes inside the external payload')
        if section[2] & 2 and section[5] and section[3] < end and begin < section[3] + section[5]:
            name = strings[section[0]:strings.index(0, section[0])].decode()
            if section[1] != 1 or section[2] != 2 or name not in ('.rodata', '.qwen_external_rodata') or not (
                    section[3] <= begin and end <= section[3] + section[5]):
                raise ValueError('The cut intersects another allocated section')
            owners.append(name)
    if len(owners) != 1:
        raise ValueError('One exclusive read-only section is required')
    replacement = []
    prefix = begin - selected[3]
    suffix = selected[3] + selected[5] - end
    if prefix:
        replacement.append((*selected[:5], prefix, prefix, selected[7]))
    if suffix:
        replacement.append((1, 4, cut + size, end, end, suffix, suffix, PAGE))
    updated = rows[:index] + replacement + rows[index + 1:]
    first_data = min(h[2] for h in rows if h[0] == 1)
    old_table_end = offset + len(rows) * 56
    new_table_end = offset + len(updated) * 56
    if new_table_end > first_data or any(raw[old_table_end:new_table_end]):
        raise ValueError('No unused header space for the additional LOAD')
    changed = bytearray(raw)
    struct.pack_into('<H', changed, 56, len(updated))
    changed[offset:max(old_table_end, new_table_end)] = b'\0' * (max(old_table_end, new_table_end) - offset)
    for i, row in enumerate(updated):
        struct.pack_into('<IIQQQQQQ', changed, offset + i * 56, *row)
    allowed = set(range(56, 58)) | set(range(offset, max(old_table_end, new_table_end)))
    if any(a != b and i not in allowed for i, (a, b) in enumerate(zip(raw, changed))):
        raise ValueError('Unexpected bytes changed outside the program-header table')
    # Every original LOAD byte is either preserved at its original VA or is
    # exactly the externally restored byte. This also checks both edge pages.
    for h in rows:
        if h[0] != 1:
            continue
        restored = bytearray(h[5])
        coverage = bytearray(h[5])
        for new in updated:
            if new[0] != 1:
                continue
            lo, hi = max(h[3], new[3]), min(h[3] + h[5], new[3] + new[5])
            if lo < hi:
                at = new[2] + lo - new[3]
                restored[lo-h[3]:hi-h[3]] = changed[at:at+hi-lo]
                coverage[lo-h[3]:hi-h[3]] = b'\1' * (hi-lo)
        if h == selected:
            restored[prefix:prefix+size] = expected
            coverage[prefix:prefix+size] = b'\1' * size
        if not all(coverage) or restored != raw[h[2]:h[2]+h[5]]:
            raise ValueError('Loaded bytes do not reconstruct the original ELF')
    return bytes(changed), dict(begin=begin, bytes=size, sha256=hashlib.sha256(expected).hexdigest(),
        original_LOADs=rows, transformed_LOADs=updated, original_section=owners[0],
        relocation_locations_in_cut=0, original_loaded_bytes_reconstructed_exactly=True,
        executable_bytes_and_relocations_unchanged=True, only_program_headers_changed=True)


def verify_repacked(original, repacked, begin, payload):
    """Verify all LOAD bytes after section removal/file-offset repacking."""
    _, old = headers(original); _, new = headers(repacked)
    end = begin + len(payload)
    for row in new:
        if row[0] == 1 and row[3] < end and begin < row[3] + row[6]:
            raise ValueError('The external range remains covered by a LOAD')
    for row in old:
        if row[0] != 1:
            continue
        for at in range(0, row[5], PAGE):
            address = row[3] + at
            count = min(PAGE, row[5] - at)
            expected = original[row[2]+at:row[2]+at+count]
            if begin <= address and address + count <= end:
                actual = payload[address-begin:address-begin+count]
            else:
                matches = [h for h in new if h[0] == 1 and h[1] == row[1] and
                           h[3] <= address and address+count <= h[3]+h[5]]
                if len(matches) != 1:
                    raise ValueError('An original loaded page or protection is missing')
                h = matches[0]; offset = h[2]+address-h[3]
                actual = repacked[offset:offset+count]
            if expected != actual:
                raise ValueError('Repacked original page bytes differ')
    return dict(loaded_bytes_and_protection_equal_after_external_restore=True,
                external_range_has_no_LOAD_coverage=True)
