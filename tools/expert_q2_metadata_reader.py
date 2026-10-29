#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive an isolated complete-prefix metadata reader for sealed composites."""
from build_speculative_batch_probe import once


def metadata_source(text):
    text=once(text,'#include "direct_metadata.h"','#include "expert_q2_metadata_window.h"\n#include <map>')
    text=once(text,'qwen_app::DirectMetadataStats totals;',
              'qwen_app::DirectMetadataStats totals;\nstd::map<std::string,std::uint64_t> composite_prefixes;')
    text=once(text,'qwen_app::DirectMetadataWindow &window;', 'qwen_app::ExpertQ2MetadataWindow &window;')
    marker='std::uint64_t native_metadata_logical_bytes(int fd,std::uint64_t physical_bytes) {'
    text=once(text,marker,'''void register_expert_q2_composite_metadata(const std::string &path,
        const std::array<std::uint64_t,10>&key,std::uint64_t logical,std::uint64_t header){
    if(!enabled.load()||busy.load()||accepted.size()>=256||path.size()>1024||
       path.rfind("/app0/expert-q2-",0)!=0||path.find('\\0')!=std::string::npos||
       !key[5]||key[5]>logical||logical>(512ull<<30)||!header||header>metadata_direct_limit||
       header>key[5]||header>=logical)
        throw std::runtime_error("A sealed complete composite header is required");
    for(const auto&item:accepted)if(item.path==path||item.identity==key)
        throw std::runtime_error("Duplicate composite metadata source admission");
    if(!composite_prefixes.emplace(path,header).second)
        throw std::runtime_error("Duplicate composite prefix admission");
    accepted.push_back({path,logical,key});
}
'''+marker)
    text=once(text,'qwen_app::DirectMetadataWindow window(ops,buffer,file->bytes);',
        'qwen_app::ExpertQ2MetadataWindow window(ops,buffer,file->bytes,file->identity[5],'
        'composite_prefixes.count(path)?composite_prefixes.at(path):0);')
    return text


def metadata_entry(text):
    text=once(text,'using Json = nlohmann::json;',
        'namespace qwen_app {void register_expert_q2_composite_metadata(const std::string&,const std::array<std::uint64_t,10>&,std::uint64_t,std::uint64_t);}\n'
        'using Json = nlohmann::json;')
    marker='''            if(direct_metadata)qwen_app::register_native_direct_metadata(
                model_file(startup.model_receipt,file.at("path").get<std::string>()),file_identities.back(),file_bytes);'''
    return once(text,marker,'''            if(direct_metadata){
                const auto path=model_file(startup.model_receipt,file.at("path").get<std::string>());
                const auto plan=std::find_if(qwen_app::expert_q2_pending_segments.begin(),qwen_app::expert_q2_pending_segments.end(),
                    [&](const auto&p){return p.path==path;});
                if(plan==qwen_app::expert_q2_pending_segments.end())
                    qwen_app::register_native_direct_metadata(path,file_identities.back(),file_bytes);
                else{
                    const auto header=qwen_app::receipt_integer(file,"header_bytes");
                    if(plan->segments.empty()||plan->segments.front().logical_offset||plan->segments.front().physical_offset||
                       plan->segments.front().bytes<header||!split_integrity||
                       split_integrity->physical.at(plan->segments.front().physical).identity!=split_integrity->prior.files.at(file_index-1))
                        throw std::runtime_error("The complete verified header must occupy the first physical prefix");
                    qwen_app::register_expert_q2_composite_metadata(path,file_identities.back(),file_bytes,header);
                }
            }''')
