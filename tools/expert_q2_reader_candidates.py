#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive independent Q2 metadata-hint and bounded composite-pair candidates."""
import re
from build_speculative_batch_probe import once
from expert_q4 import require

def candidate_header(text):
    require('class ResidentMappedSourceReader {'in text and 'composite_pair('in text,'Actual resident composite reader required')
    range_decl='    struct Range { std::uintptr_t at; std::uint64_t bytes, offset; std::size_t file, owner; };'
    require(text.count(range_decl)==1,'One original immutable Range definition required')
    text=once(text,range_decl,'')
    text,count=re.subn(r'std::find_if\(ranges_\.begin\(\),\s*ranges_\.end\(\),','candidate_range(',text)
    require(count==11,'Exact actual point-range lookup sites required')
    text='#include <atomic>\n'+text
    text=once(text,'namespace qwen_app {','namespace qwen_app {\ninline std::atomic<unsigned> Q2_reader_candidate_mode{0};')
    helper='''
    struct Range { std::uintptr_t at; std::uint64_t bytes, offset; std::size_t file, owner; };
    mutable std::atomic<std::size_t> range_hint_{SIZE_MAX};
    mutable std::atomic<std::uint64_t> range_lookups_{0},range_hint_hits_{0};
    std::uint64_t composite_parallel_pairs_=0;
    template<class Predicate>std::vector<Range>::const_iterator candidate_range(Predicate matches)const {
        range_lookups_.fetch_add(1,std::memory_order_relaxed);
        if(Q2_reader_candidate_mode.load(std::memory_order_relaxed)==1){
            const auto index=range_hint_.load(std::memory_order_relaxed);
            if(index<ranges_.size()&&matches(ranges_[index])){
                range_hint_hits_.fetch_add(1,std::memory_order_relaxed);return ranges_.cbegin()+index;
            }
        }
        const auto result=std::find_if(ranges_.cbegin(),ranges_.cend(),matches);
        if(result!=ranges_.cend())range_hint_.store(std::size_t(result-ranges_.cbegin()),std::memory_order_relaxed);
        return result;
    }
'''
    text=once(text,'class ResidentMappedSourceReader {','class ResidentMappedSourceReader {'+helper)
    text=once(text,'public:\n','''public:
    std::array<std::uint64_t,3> candidate_stats()const {
        return {range_hint_hits_.load(std::memory_order_relaxed),range_lookups_.load(std::memory_order_relaxed),composite_parallel_pairs_};
    }
''')
    text=once(text,'        ranges_ = std::move(kept); ++stats_.retired_ranges;',
        '        range_hint_.store(SIZE_MAX,std::memory_order_relaxed);\n        ranges_ = std::move(kept); ++stats_.retired_ranges;')
    marker='    std::array<const void*,2> composite_pair(const std::array<std::uintptr_t,2>&addresses,std::size_t bytes){'
    require(text.count(marker)==1,'One original composite gather required')
    text=text.replace(marker,parallel_gather()+marker+'\n        if(Q2_reader_candidate_mode.load(std::memory_order_relaxed)==2)return candidate_composite_pair(addresses,bytes);',1)
    return text

def parallel_gather():
    return '''    std::array<const void*,2> candidate_composite_pair(const std::array<std::uintptr_t,2>&addresses,std::size_t bytes){
        if(busy_)fail("A composite pair overlaps an active lease");
        struct Plan{std::size_t file=0,skip=0,destination=0,saved=0,count=0;std::uint64_t expected=0;};
        const auto half=model_read_window/2;std::array<std::size_t,2>done{};
        std::array<std::array<unsigned char,model_read_alignment>,2>prefix{};
        std::array<const void*,2>windows{static_cast<unsigned char*>(scratch_),static_cast<unsigned char*>(scratch_)+half};
        busy_=true;pending_windows_=2;bool used_parallel=false;
        try{
            while(done[0]<bytes||done[1]<bytes){
                std::array<Plan,2>plans{};std::array<SourceReadRequest,2>requests{};std::array<bool,2>active{};
                for(unsigned i=0;i<2;++i){if(done[i]==bytes)continue;active[i]=true;const auto at=addresses[i]+done[i];
                    const auto range=candidate_range([&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
                    if(range==ranges_.end())fail("A composite pair lost its admitted range");
                    const auto offset=range->offset+at-range->at;
                    if(offset>=files_[range->file].bytes)fail("A composite pair escaped its physical file");
                    const auto aligned=offset&~std::uint64_t(model_read_alignment-1);auto&p=plans[i];
                    p.file=range->file;p.skip=std::size_t(offset-aligned);p.destination=done[i]&~std::size_t(model_read_alignment-1);p.saved=done[i]-p.destination;
                    p.count=std::min({bytes-done[i],std::size_t(range->bytes-(at-range->at)),std::size_t(files_[p.file].bytes-offset),half-done[i],half-p.destination-p.skip});
                    const auto requested=std::size_t(rounded(p.skip+p.count));
                    if(!p.count||p.destination+requested>half||ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin)
                        fail("A composite gather escaped its fixed window or reserves");
                    auto*target=static_cast<unsigned char*>(scratch_)+i*half;
                    if(p.saved)std::memcpy(prefix[i].data(),target+p.destination,p.saved);
                    requests[i]={handle(p.file),target+p.destination,requested,aligned};p.expected=std::min<std::uint64_t>(requested,files_[p.file].bytes-aligned);
                }
                std::array<std::int64_t,2>got{};
                const bool parallel=active[0]&&active[1]&&source_schedule_parallel(files_[plans[0].file].identity,requests[0].offset,requests[0].bytes,
                    files_[plans[1].file].identity,requests[1].offset,requests[1].bytes);
                {ProfileScope timing(stats_.read_ns);
                    if(parallel)got=ops_.read_pair(requests);
                    else for(unsigned i=0;i<2;++i)if(active[i])got[i]=ops_.read_at(requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset);
                }
                if(parallel){++composite_parallel_pairs_;++stats_.parallel_batches;used_parallel=true;}
                for(unsigned i=0;i<2;++i)if(active[i]){const auto&p=plans[i];
                    if(got[i]!=std::int64_t(p.expected)||p.expected<p.skip+p.count||ops_.identity(requests[i].fd)!=files_[p.file].identity)
                        fail("A composite gather did not return stable complete bytes");
                    auto*target=static_cast<unsigned char*>(scratch_)+i*half;
                    std::memmove(target+done[i],target+p.destination+p.skip,p.count);
                    if(p.saved)std::memcpy(target+p.destination,prefix[i].data(),p.saved);
                    ++stats_.physical_read_calls;stats_.physical_read_bytes+=p.expected;
                    stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,requests[i].bytes);done[i]+=p.count;
                }
            }
        }catch(...){failed_=true;throw;}
        stats_.bytes+=bytes*2;stats_.chunks+=2;if(!used_parallel)++stats_.selected_serial_batches;
        consumer_started_=ProfileClock::now();return windows;
    }
'''
