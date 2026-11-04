// SPDX-License-Identifier: MIT
#pragma once
#include "model_pread_observation.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <list>
#include <map>
#include <optional>
#include <tuple>

namespace qwen_app {
struct RelativeSpan {
    std::array<std::uint64_t,12> identity{};
    std::int64_t flags=-1;
    std::uint64_t bytes=0,offset=0;
    bool operator==(const RelativeSpan&o)const noexcept{
        return identity==o.identity&&flags==o.flags&&bytes==o.bytes&&offset==o.offset;
    }
};
inline std::optional<RelativeSpan> completed_relative_span(const ObservedReadRow&r){
    if(!r.candidate||!r.before_valid||!r.after_valid||!r.identity_equal||r.before!=r.after||
       r.flags_before<0||r.flags_before!=r.flags_after||r.requested<(256u<<10)||r.requested>(8u<<20)||
       r.requested%16384||r.offset%16384||r.returned!=std::int64_t(r.requested)||r.before[2]<(64u<<20)||
       r.before[2]>std::uint64_t(std::numeric_limits<std::int64_t>::max())||r.offset>r.before[2]||r.requested>r.before[2]-r.offset)return {};
    return RelativeSpan{r.before,r.flags_before,r.requested,r.offset};
}

// Native port of the completed relative-offset screen. Each producer retains
// at most64 full-identity histories and512 entries in each transition table.
// It chooses only from completed reads and never submits an I/O operation.
class RelativeSpanPredictor {
    using Namespace=std::tuple<std::array<std::uint64_t,12>,std::int64_t,std::uint64_t>;
    using Context=std::tuple<Namespace,std::int64_t,std::int64_t>;
    class Table {
        struct Entry{std::int64_t target;unsigned count;std::list<Context>::iterator age;};
        std::list<Context> age_;
        std::map<Context,Entry> entries_;
    public:
        void remember(const Context&key,std::int64_t target){
            auto found=entries_.find(key);unsigned count=1;
            if(found!=entries_.end()){
                if(found->second.target==target)count=std::min(255u,found->second.count+1);
                age_.erase(found->second.age);entries_.erase(found);
            }
            age_.push_back(key);entries_.emplace(key,Entry{target,count,std::prev(age_.end())});
            if(entries_.size()>512){entries_.erase(age_.front());age_.pop_front();}
        }
        std::optional<std::int64_t>lookup(const Context&key,unsigned minimum){
            auto found=entries_.find(key);if(found==entries_.end())return {};
            age_.splice(age_.end(),age_,found->second.age);
            return found->second.count>=minimum?std::optional<std::int64_t>(found->second.target):std::nullopt;
        }
        std::size_t size()const noexcept{return entries_.size();}
    };
    struct History {std::uint64_t offset;std::array<std::int64_t,2>deltas{};unsigned count=0;std::list<Namespace>::iterator age;};
    std::array<Table,2>tables_;
    std::map<Namespace,History>histories_;
    std::list<Namespace>age_;
public:
    RelativeSpanPredictor()=default;
    RelativeSpanPredictor(const RelativeSpanPredictor&)=delete;
    RelativeSpanPredictor&operator=(const RelativeSpanPredictor&)=delete;
    std::optional<RelativeSpan>complete(const ObservedReadRow&r){
        const auto span=completed_relative_span(r);
        if(!span){histories_.clear();age_.clear();return {};}
        const Namespace ns{span->identity,span->flags,span->bytes};
        const auto found=histories_.find(ns);std::array<std::int64_t,2>deltas{};unsigned count=0;
        if(found!=histories_.end()){
            const auto&old=found->second;
            const auto delta=std::int64_t(span->offset)-std::int64_t(old.offset);
            if(old.count)tables_[0].remember({ns,old.deltas[old.count-1],0},delta);
            if(old.count==2)tables_[1].remember({ns,old.deltas[0],old.deltas[1]},delta);
            if(old.count){deltas={old.deltas[old.count-1],delta};count=2;}
            else {deltas[0]=delta;count=1;}
            age_.erase(old.age);histories_.erase(found);
        }
        age_.push_back(ns);histories_.emplace(ns,History{span->offset,deltas,count,std::prev(age_.end())});
        if(histories_.size()>64){histories_.erase(age_.front());age_.pop_front();}
        std::optional<std::int64_t>prediction;
        if(count==2)prediction=tables_[1].lookup({ns,deltas[0],deltas[1]},1);
        if(!prediction&&count)prediction=tables_[0].lookup({ns,deltas[count-1],0},2);
        if(!prediction)return {};
        const auto offset=std::int64_t(span->offset);
        if((*prediction>0&&offset>std::numeric_limits<std::int64_t>::max()-*prediction)||
           (*prediction<0&&offset< -*prediction))return {};
        const auto target=offset+*prediction;
        if(target<0||std::uint64_t(target)>span->identity[2]-span->bytes)return {};
        auto output=*span;output.offset=std::uint64_t(target);return output;
    }
    std::size_t transition_entries()const noexcept{return tables_[0].size()+tables_[1].size();}
    std::size_t histories()const noexcept{return histories_.size();}
};
}
