#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace delimited experiment case numbers without changing artifact hashes."""
import re

DIGEST = re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])')


def replace_case_ids(text, mapping):
    if not isinstance(text, str) or not isinstance(mapping, dict) or not mapping:
        raise ValueError('Text and an explicit nonempty case mapping are required')
    converted = {}
    for key, value in mapping.items():
        source, target = str(key), str(value)
        if not all(re.fullmatch(r'[1-9][0-9]{0,9}', x) and int(x) < 2**31 for x in (source, target)):
            raise ValueError('Positive bounded decimal case identifiers are required')
        converted[source] = target
    pattern = r'(?<![0-9A-Za-z])(?:' + '|'.join(map(re.escape, converted)) + r')(?![0-9A-Za-z])'
    result = re.sub(pattern, lambda match: converted[match.group()], text)
    if DIGEST.findall(result) != DIGEST.findall(text):
        raise ValueError('Artifact or credential digests must never change during case rebinding')
    return result
