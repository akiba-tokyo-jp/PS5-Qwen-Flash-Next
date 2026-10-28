// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <mutex>
#include <streambuf>
#include <nlohmann/json.hpp>
// Existing upstream logger flags, not a new driver or timestamp implementation.
extern bool vk_perf_logger_enabled;
extern bool vk_perf_logger_concurrent;
extern std::uint32_t vk_perf_logger_frequency;
namespace qwen_app {
class BoundedGpuProfile final:public std::streambuf {
    struct Entry{std::array<char,192>name{};std::uint64_t count=0;double us=0;};
    std::array<Entry,256> entries_{};
    std::array<char,768> line_{};
    unsigned used_=0,line_bytes_=0,blocks_=0;
    bool failed_=false,active_=false;
    std::streambuf*original_=nullptr;
    std::mutex mutex_;
    void line(){
        line_[line_bytes_]=0;
        if(std::strstr(line_.data(),"Vulkan Timings:")){++blocks_;line_bytes_=0;return;}
        char*colon=std::strstr(line_.data(),": ");
        char*equal=std::strstr(line_.data()," us = ");
        if(colon&&equal){
            const auto name_bytes=std::size_t(colon-line_.data());
            unsigned long long count=0;double mean=0,total=0;
            if(name_bytes>=192||std::sscanf(colon+2,"%llu x %lf us = %lf us",&count,&mean,&total)!=3||
               !count||!std::isfinite(total)||total<0){failed_=true;line_bytes_=0;return;}
            *colon=0;unsigned at=0;for(;at<used_;++at)if(!std::strcmp(entries_[at].name.data(),line_.data()))break;
            if(at==entries_.size()){failed_=true;line_bytes_=0;return;}
            if(at==used_){std::memcpy(entries_[at].name.data(),line_.data(),name_bytes+1);++used_;}
            entries_[at].count+=count;entries_[at].us+=total;
        }else if(line_bytes_&&original_&&!std::strstr(line_.data(),"Total time:")&&line_[0]!='-'){
            original_->sputn(line_.data(),line_bytes_);original_->sputn("\n",1);}
        line_bytes_=0;
    }
protected:
    std::streamsize xsputn(const char*s,std::streamsize n)override{
        std::lock_guard<std::mutex>lock(mutex_);
        for(std::streamsize i=0;i<n;++i){if(s[i]=='\n')line();
            else if(line_bytes_+1<line_.size())line_[line_bytes_++]=s[i];else failed_=true;}
        return n;
    }
    int_type overflow(int_type ch)override{
        if(traits_type::eq_int_type(ch,traits_type::eof()))return traits_type::not_eof(ch);
        const auto c=traits_type::to_char_type(ch);xsputn(&c,1);return ch;
    }
public:
    void start(){if(active_)throw std::runtime_error("One bounded GPU profile is permitted");
        original_=std::cerr.rdbuf(this);active_=true;vk_perf_logger_enabled=true;
        vk_perf_logger_concurrent=false;vk_perf_logger_frequency=1;}
    void clear_completed_scope(){std::lock_guard<std::mutex>lock(mutex_);
        if(!active_)throw std::runtime_error("A live capture requires a completed preceding scope");
        for(unsigned i=0;i<used_;++i)entries_[i]={};used_=line_bytes_=blocks_=0;failed_=false;}
    nlohmann::json finish(){
        if(!active_)throw std::runtime_error("A started GPU profile is required");
        vk_perf_logger_enabled=false;std::cerr.flush();std::cerr.rdbuf(original_);active_=false;
        if(line_bytes_)line();nlohmann::json rows=nlohmann::json::array();
        for(unsigned i=0;i<used_;++i){const auto&e=entries_[i];rows.push_back({{"name",e.name.data()},{"calls",e.count},{"GPU_microseconds",e.us}});}
        return {{"complete",!failed_&&blocks_>0&&used_>0},{"blocks",blocks_},{"rows",rows},
            {"storage_bytes",sizeof(*this)},{"logger","existing ggml-vulkan timestamp logger"},
            {"timestamps_are_instrumented_not_unmodified_request_timings",true},{"normal_timed_arms_profile_enabled",false}};
    }
    ~BoundedGpuProfile(){if(active_){vk_perf_logger_enabled=false;std::cerr.rdbuf(original_);}}
};
}
