#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create a distinct reader type with a load-only submission cap; no ABI patch."""
import re


def generate(source):
    begin=source.index('class MappedSourceReader {')
    end=source.index('\n// The native provider allocates exactly one aligned window.',begin)
    body=source[begin:end]
    body=re.sub(r'\bMappedSourceReader\b','ResidentMappedSourceReader',body)
    anchor='class ResidentMappedSourceReader {\npublic:'
    if body.count(anchor)!=1:raise ValueError('Unique reader class boundary required')
    body=body.replace(anchor,'''class ResidentMappedSourceReader {
    std::size_t resident_load_limit_=model_read_window;
public:
    void set_resident_load_limit(std::size_t bytes) {
        require_completed_window();
        if(bytes!=(1u<<20)&&bytes!=model_read_window)throw std::invalid_argument("Unsupported resident load window");
        resident_load_limit_=bytes;
    }''')
    anchor='copied = std::min(wanted, model_read_window - skip);'
    if body.count(anchor)!=1:raise ValueError('Unique original single-window source boundary required')
    body=body.replace(anchor,'copied = std::min(wanted, resident_load_limit_ - skip);')
    return '// SPDX-License-Identifier: MIT\n#pragma once\n#include "mapped_source.h"\nnamespace qwen_app {\n'+body+'\n}\n'
