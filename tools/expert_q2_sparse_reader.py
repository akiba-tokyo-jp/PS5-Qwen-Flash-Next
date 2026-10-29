#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive isolated composite-source views without editing the selected reader."""
from expert_q4 import require

def reader_header(text):
    require('ExpertQ2SourceSegment'not in text,'An unchanged original reader is required')
    text='#include "expert_q2_sparse.h"\n'+text
    text=text.replace('std::vector<LogicalSourceFile> logical = {})',
        'std::vector<LogicalSourceFile> logical = {}, std::vector<ExpertQ2SourceSegments> composites = {})',1)
    text=text.replace('owner_(std::this_thread::get_id()) {',
        'owner_(std::this_thread::get_id()),composites_(std::move(composites)) {',1)
    marker='            if (bytes != file.bytes) throw std::invalid_argument("Split sources do not preserve the original logical size");'
    require(text.count(marker)==1,'The original physical/logical length guard changed')
    text=text.replace(marker,'''            const bool composite=std::any_of(composites_.begin(),composites_.end(),[&](const auto&p){return p.path==file.path;});
            if((!composite&&bytes!=file.bytes)||(composite&&bytes>file.bytes))
                throw std::invalid_argument("Only a complete composite plan may reduce stored physical bytes");''',1)
    marker='        if (std::find(used.begin(), used.end(), false) != used.end())'
    require(text.count(marker)==1,'The original complete physical coverage check changed')
    text=text.replace(marker,'''        std::vector<std::string> composite_paths;
        std::size_t segment_count=0;
        for(const auto&plan:composites_){
            const auto file=std::find_if(logical.begin(),logical.end(),[&](const auto&f){return f.path==plan.path;});
            if(file==logical.end()||plan.segments.empty()||
               std::find(composite_paths.begin(),composite_paths.end(),plan.path)!=composite_paths.end())
                throw std::invalid_argument("One complete composite plan per admitted logical file is required");
            composite_paths.push_back(plan.path);std::uint64_t covered=0;
            for(const auto&segment:plan.segments){
                if(segment.logical_offset!=covered||!segment.bytes||segment.physical>=files_.size()||
                   segment.physical_offset>=files_[segment.physical].bytes||
                   segment.bytes>files_[segment.physical].bytes-segment.physical_offset||
                   covered>file->bytes||segment.bytes>file->bytes-covered||++segment_count>8192)
                    throw std::invalid_argument("Composite ranges must partition exact immutable physical bytes");
                used[segment.physical]=true;covered+=segment.bytes;
            }
            if(covered!=file->bytes)throw std::invalid_argument("Composite logical coverage is incomplete");
        }
'''+marker,1)
    begin=text.index('        if (match->parts.size() > 8192 - ranges_.size())')
    end=text.index('        ++stats_.mappings;',begin)
    text=text[:begin]+'''        const auto composite=std::find_if(composites_.begin(),composites_.end(),[&](const auto&row){return row.path==match->path;});
        const auto owner=std::size_t(stats_.mappings);
        if(composite!=composites_.end()){
            if(composite->segments.size()>8192-ranges_.size())fail("Composite mapping metadata exceeds its bound");
            for(const auto&segment:composite->segments){
                const auto padding=segment.logical_offset+segment.bytes==bytes?span-bytes:0;
                ranges_.push_back({at+segment.logical_offset,segment.bytes+padding,segment.physical_offset,segment.physical,owner});
            }
        }else{
            if(match->parts.size()>8192-ranges_.size())fail("Engine mapping metadata exceeds its bound");
            std::uint64_t offset=0;
            for(const auto part:match->parts){ranges_.push_back({at+offset,rounded(files_[part].bytes),0,part,owner});offset+=files_[part].bytes;}
        }
'''+text[end:]
    text=text.replace('files_[range->file].bytes - offset)), copied);',
        'std::min(files_[range->file].bytes-offset,range->bytes-(at-range->at)))), copied);',1)
    if 'pair_crosses_part(files, offsets, bytes)'in text:
        # Existing parallel windows remain unchanged when each request stays
        # within one physical range. Composite boundaries need a bounded gather:
        # logical and physical alignment residues need not agree after aliasing.
        text=text.replace('pair_crosses_part(files, offsets, bytes)',
            '(pair_crosses_part(files,offsets,bytes)||pair_crosses_ranges(addresses,bytes))')
        marker='    bool pair_crosses_part('
        require(text.count(marker)==1,'One original paired-read boundary helper required')
        text=text.replace(marker,'''    bool pair_crosses_ranges(const std::array<std::uintptr_t,2>&addresses,std::size_t bytes) const {
        for(const auto at:addresses){
            const auto range=std::find_if(ranges_.begin(),ranges_.end(),[&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
            if(range==ranges_.end()||bytes>range->bytes-(at-range->at))return true;
        }
        return false;
    }
    std::array<const void*,2> composite_pair(const std::array<std::uintptr_t,2>&addresses,std::size_t bytes){
        if(busy_)fail("A composite pair overlaps an active lease");
        std::array<const void*,2>windows{};
        std::array<unsigned char,model_read_alignment>prefix{};
        const auto half=model_read_window/2;
        busy_=true;pending_windows_=2;
        try{
            for(unsigned i=0;i<2;++i){
                auto*target=static_cast<unsigned char*>(scratch_)+i*half;
                std::size_t done=0;
                while(done<bytes){
                    const auto at=addresses[i]+done;
                    const auto range=std::find_if(ranges_.begin(),ranges_.end(),[&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
                    if(range==ranges_.end())fail("A composite pair lost its admitted range");
                    const auto offset=range->offset+at-range->at;
                    if(offset>=files_[range->file].bytes)fail("A composite pair escaped its physical file");
                    const auto aligned=offset&~std::uint64_t(model_read_alignment-1);
                    const auto skip=std::size_t(offset-aligned);
                    const auto destination=done&~std::size_t(model_read_alignment-1);
                    const auto saved=done-destination;
                    const auto count=std::min({std::size_t(bytes-done),std::size_t(range->bytes-(at-range->at)),
                        std::size_t(files_[range->file].bytes-offset),half-done,half-destination-skip});
                    const auto requested=std::size_t(rounded(skip+count));
                    if(!count||destination+requested>half||
                       ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin)
                        fail("A composite gather escaped its fixed window or reserves");
                    if(saved)std::memcpy(prefix.data(),target+destination,saved);
                    const int fd=handle(range->file);std::int64_t got;
                    {ProfileScope timing(stats_.read_ns);got=ops_.read_at(fd,target+destination,requested,aligned);}
                    const auto expected=std::min<std::uint64_t>(requested,files_[range->file].bytes-aligned);
                    if(got!=std::int64_t(expected)||expected<skip+count||ops_.identity(fd)!=files_[range->file].identity)
                        fail("A composite gather did not return stable complete bytes");
                    std::memmove(target+done,target+destination+skip,count);
                    if(saved)std::memcpy(target+destination,prefix.data(),saved);
                    ++stats_.physical_read_calls;stats_.physical_read_bytes+=expected;
                    stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,requested);done+=count;
                }
                windows[i]=target;
            }
        }catch(...){failed_=true;throw;}
        stats_.bytes+=bytes*2;stats_.chunks+=2;++stats_.selected_serial_batches;
        consumer_started_=ProfileClock::now();return windows;
    }
'''+marker,1)
        marker='''        if (busy_) fail("A crossing source pair overlaps an active lease");'''
        require(text.count(marker)==1,'One original crossing-pair owner required')
        text=text.replace(marker,'        if(!composites_.empty())return composite_pair(addresses,bytes);\n'+marker,1)
    text=text.replace('    std::thread::id owner_;','    std::thread::id owner_;\n    std::vector<ExpertQ2SourceSegments> composites_;',1)
    return text

def reader_source(text):
    selected='ResidentMappedSourceReader'if 'std::unique_ptr<qwen_app::ResidentMappedSourceReader> reader;'in text else'MappedSourceReader'
    marker='std::unique_ptr<qwen_app::'+selected+'> reader;'
    require(text.count(marker)==1,'The actual qualified reader owner is required')
    text=text.replace(marker,marker+'\nstd::vector<qwen_app::ExpertQ2SourceSegments> expert_q2_segments;',1)
    marker='namespace qwen_app {'
    text=text.replace(marker,marker+'''
void configure_expert_q2_source_segments(std::vector<ExpertQ2SourceSegments> plan){
    if(reader||window||active.load()||!expert_q2_segments.empty()||plan.empty())
        throw std::runtime_error("Composite sources require one fresh owner before source startup");
    expert_q2_segments=std::move(plan);
}
''',1)
    marker='std::move(files), ops, window, std::move(logical))'
    require(text.count(marker)==1,'One exact original source-reader construction is required')
    return text.replace(marker,'std::move(files),ops,window,std::move(logical),std::move(expert_q2_segments))',1)
