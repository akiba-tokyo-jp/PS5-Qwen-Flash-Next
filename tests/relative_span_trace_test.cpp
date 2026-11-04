// SPDX-License-Identifier: MIT
#include "relative_span_predictor.h"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace qwen_app;
static void need(bool b){if(!b)throw std::runtime_error("Native relative-span trace control failed");}
int main(int argc,char**argv){
    need(argc==2);std::ifstream in(argv[1],std::ios::binary);
    std::vector<unsigned char>raw((std::istreambuf_iterator<char>(in)),{});
    need(raw.size()>16384&&!std::memcmp(raw.data(),"QWENIO1\0",8));
    std::uint64_t count=0;std::memcpy(&count,raw.data()+24,8);need(raw.size()==16384+count*sizeof(ObservedReadRow));
    std::map<std::uint64_t,std::vector<ObservedReadRow>>producers;
    for(std::uint64_t i=0;i<count;++i){ObservedReadRow r;std::memcpy(&r,raw.data()+16384+i*sizeof(r),sizeof(r));need(r.ordinal==i);producers[r.thread].push_back(r);}
    ObservedReadRow original{};
    for(const auto&[id,rows]:producers){(void)id;for(const auto&r:rows)if(completed_relative_span(r)){original=r;break;}if(original.requested)break;}
    need(bool(completed_relative_span(original)));
    for(unsigned fault=0;fault<8;++fault){
        auto r=original;
        switch(fault){case 0:--r.returned;break;case 1:++r.offset;break;case 2:r.requested=16384;break;
        case 3:r.before[2]=r.after[2]=1<<20;break;case 4:++r.after[1];break;case 5:r.flags_after^=1;break;
        case 6:r.before_valid=0;break;case 7:r.before[2]=r.after[2]=UINT64_MAX;break;}
        need(!completed_relative_span(r));RelativeSpanPredictor predictor;need(!predictor.complete(r)&&!predictor.histories());
    }
    std::uint64_t eligible=0,predictions=0,hits=0,unused=0,predicted_bytes=0,hit_bytes=0,peak=0,largest=0;
    for(auto&[id,rows]:producers){
        (void)id;RelativeSpanPredictor predictor;unsigned submitted=0;std::optional<RelativeSpan>pending;
        std::sort(rows.begin(),rows.end(),[](const auto&a,const auto&b){return std::tie(a.begin_ns,a.ordinal)<std::tie(b.begin_ns,b.ordinal);});
        std::uint64_t last=0;
        for(const auto&r:rows){
            need(r.begin_ns>last&&r.end_ns>=r.begin_ns);last=r.end_ns;
            const auto key=completed_relative_span(r);eligible+=bool(key);
            if(pending){if(key&&*key==*pending){++hits;hit_bytes+=r.requested;}else ++unused;pending.reset();}
            const auto target=predictor.complete(r);peak=std::max(peak,std::uint64_t(predictor.transition_entries()));
            need(predictor.histories()<=64&&predictor.transition_entries()<=1024);
            if(target&&submitted<6){pending=target;++submitted;++predictions;predicted_bytes+=target->bytes;largest=std::max(largest,target->bytes);}
        }
        if(pending)++unused;
    }
    need(predictions==hits+unused);
    std::cout<<"{\"original_calls\":"<<count<<",\"eligible_calls\":"<<eligible<<",\"original_producers\":"<<producers.size()
        <<",\"predictions\":"<<predictions<<",\"hits\":"<<hits<<",\"unused\":"<<unused<<",\"predicted_bytes\":"<<predicted_bytes
        <<",\"hit_bytes\":"<<hit_bytes<<",\"live_table_entries_peak\":"<<peak<<",\"largest_prediction_bytes\":"<<largest<<"}\n";
}
