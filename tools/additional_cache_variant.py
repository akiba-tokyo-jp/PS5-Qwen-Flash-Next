#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create exact VFS overlays for an independent 128/134-slot experiment."""
import json
import re
from pathlib import Path
from build_speculative_batch_probe import once

RAW_134=3*135*3293184


def geometry(text):
    text=once(text,'(active_slots!=53&&active_slots!=128)',
        '(active_slots!=53&&active_slots!=128&&active_slots!=134)')
    text=once(text,'postload&&selected_padded_cache_geometry().active_slots==128&&actual>',
        'postload&&(selected_padded_cache_geometry().active_slots==128||selected_padded_cache_geometry().active_slots==134)&&actual>')
    marker='inline std::atomic<std::size_t> selected_padded_cache_slots{53};'
    text=once(text,marker,marker+'''
inline std::atomic<std::size_t> requested_additional_cache_slots{128};
inline void request_additional_cache_slots(unsigned slots){
    if(slots!=128&&slots!=134)throw std::invalid_argument("Only the isolated 128/134 cache scopes are supported");
    requested_additional_cache_slots.store(slots,std::memory_order_relaxed);
}
inline unsigned additional_cache_slots(){return unsigned(requested_additional_cache_slots.load(std::memory_order_relaxed));}
''')
    text=once(text,'compare_exchange_strong(expected,128)','compare_exchange_strong(expected,additional_cache_slots())')
    return text+'\nstatic_assert(qwen_app::PaddedCacheGeometry{134}.cache_bytes()=='+str(RAW_134)+',"Exact 135-plane original-precision cache required");\n'


def large_policy(text):
    text=once(text,'const auto &scope=policy.at("native_large_cache_scope");',
        '''const auto &scope=policy.at("native_large_cache_scope");
    const auto slots=scope.at("active_slots").get<unsigned>();
    request_additional_cache_slots(slots);''')
    text=text.replace('PaddedCacheGeometry{128}', 'PaddedCacheGeometry{additional_cache_slots()}')
    text=text.replace('{"schema","ps5-qwen-cache-128-experiment-v1"}',
        '{"schema",std::string("ps5-qwen-cache-")+std::to_string(slots)+"-experiment-v1"}')
    text=text.replace('{"active_slots",128},{"physical_planes",129}',
        '{"active_slots",additional_cache_slots()},{"physical_planes",additional_cache_slots()+1}')
    text=text.replace('r.at("active_slots")!=128||r.at("physical_planes")!=129',
        'r.at("active_slots")!=additional_cache_slots()||r.at("physical_planes")!=additional_cache_slots()+1')
    return text


def transform(path,text):
    name=Path(path).name
    if name=='padded_cache_geometry.h':return geometry(text)
    if name=='large_cache_policy.h':return large_policy(text)
    if name=='resident_additional_policy.h':
        text='#include "padded_cache_geometry.h"\n'+text
        text=text.replace('(slots!=53&&slots!=128)','(slots!=53&&slots!=128&&slots!=134)')
        text=text.replace('(slots==53?536870912ull:1274462208ull)','PaddedCacheGeometry{slots}.cache_bytes()')
        return text.replace('!=(slots==128)','!=(slots!=53)')
    if name=='resident_cache_reset.h':
        return text.replace('(lru.n_slots!=53&&lru.n_slots!=128)',
            '(lru.n_slots!=53&&lru.n_slots!=128&&lru.n_slots!=134)')
    if name=='resident_refill_policy.h':
        return '''// SPDX-License-Identifier: MIT
#pragma once
#include "resident_additional_policy.h"
namespace qwen_app {
inline void require_resident_refill_policy(const nlohmann::json&policy){
 const auto slots=policy.at("native_padded_expert_cache").at("active_slots").get<unsigned>();
 if(slots!=128&&slots!=134)throw std::runtime_error("Only the matched 128/134 cache experiment is supported");
 auto expected=resident_additional_scope("cache",slots);expected["schema"]="ps5-qwen-additional-cache-comparison-v1";
 if(policy.at("native_resident_comparison")!=expected)throw std::runtime_error("Exact three-request cache-only comparison required");
 auto original=policy;original["native_resident_comparison"]=resident_additional_scope("cache",slots);
 require_resident_additional_policy(original,"cache");
}
}
'''
    if name=='padded_bank_layout.cpp':
        return once(text,'    if(selected_padded_cache_geometry().active_slots==128)',
            '''    if(selected_padded_cache_geometry().active_slots==134)
        return {{133,0,64,0,132,1,133,53,96,111}};
    if(selected_padded_cache_geometry().active_slots==128)''')
    # These are cache geometry predicates, never transfer staging caps or source
    # residues. The original source bodies, OS prices and queue limits remain.
    if ('mapped-source'in name or 'mapped_source'in name or name.endswith('.private.h')):
        text=re.sub(r'(geometry\.active_slots\s*!=\s*128)(?!\d)',r'\1&&geometry.active_slots!=134',text)
        text=text.replace('qwen_app::selected_padded_cache_geometry().active_slots!=128)',
            'qwen_app::selected_padded_cache_geometry().active_slots!=128&&qwen_app::selected_padded_cache_geometry().active_slots!=134)')
    if name.endswith(('.cpp','.cxx')):
        text=text.replace('{"active_slots",128},{"physical_planes",129}',
            '{"active_slots",qwen_app::selected_padded_cache_geometry().active_slots},{"physical_planes",qwen_app::selected_padded_cache_geometry().physical_slots()}')
        if name=='resident-comparison-cache128-postload.private.cpp':
            text=once(text,'const unsigned request_count=5;','const unsigned request_count=3;')
            text=once(text,'const bool refill=ordinal==2||ordinal==3;','const bool refill=true;')
            text=once(text,'{"kind","refill"}','{"kind","additional-cache"}')
    return text


def write_overlay(rows,out):
    import hashlib
    out=Path(out);out.mkdir(parents=True,exist_ok=False);roots=[];changes=[]
    paths={str(Path(row['path'])) for row in rows if Path(row['path']).suffix in('.h','.cpp','.cxx')}
    for value in sorted(paths):
        path=Path(value)
        if not path.is_file():raise ValueError('Captured cache source is missing: '+value)
        text=path.read_text();changed=transform(path,text)
        if changed==text:continue
        target=out/(hashlib.sha256(value.encode()).hexdigest()[:16]+'-'+path.name)
        target.write_text(changed,newline='\n')
        roots.append({'type':'file','name':path.resolve().as_posix(),'external-contents':target.resolve().as_posix()})
        changes.append(dict(original=value,replacement=str(target)))
    if not any(Path(r['original']).name=='padded_cache_geometry.h'for r in changes):
        raise ValueError('An actual compiled geometry header must be overlaid')
    overlay=out/'overlay.private.json';overlay.write_text(json.dumps({'version':0,'case-sensitive':'false',
        'use-external-names':False,'roots':roots},indent=2)+'\n',newline='\n')
    return overlay,changes
