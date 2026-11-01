# SPDX-License-Identifier: MIT
"""Generate a five-lease, four-worker no-copy streaming alternative."""
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def transform():
    s=(ROOT/'native/app/streaming_read_pool.h').read_text()
    s=once(s,'#include <algorithm>','#include <algorithm>\n#include <cstdlib>\nextern "C" bool qwen_post_ring_enabled();')
    s=once(s,'enum class State {idle,queued,reading,ready};','enum class State {idle,queued,reading,ready,consuming};')
    s=once(s,'std::array<Slot,4>slots_{};','std::array<Slot,5>slots_{};\n    void* spare_=nullptr;')
    s=once(s,'void worker(unsigned lane)noexcept{','void worker(unsigned)noexcept{')
    s=once(s,'changed_.wait(lock,[&]{return stop_||slots_[lane].state==State::queued;});if(stop_)return;\n            auto&s=slots_[lane];',
        'changed_.wait(lock,[&]{return stop_||std::any_of(slots_.begin(),slots_.end(),[](const Slot&s){return s.state==State::queued;});});if(stop_)return;\n            auto&s=*std::find_if(slots_.begin(),slots_.end(),[](const Slot&s){return s.state==State::queued;});')
    s=once(s,'pending_=true;maximum_=0;',
        '''const unsigned capacity=qwen_post_ring_enabled()?5:4;
        if(capacity==5&&!spare_&&(posix_memalign(&spare_,16384,2u<<20)||!spare_))throw std::runtime_error("Owned spare ring lease unavailable");
        const std::array<void*,5>ring={leases[0],leases[1],leases[2],leases[3],spare_};
        pending_=true;maximum_=0;''')
    s=once(s,'s.request.target=leases[lane];','s.request.target=ring[lane];')
    s=once(s,'unsigned lane=4;for(unsigned i=0;i<4;++i)if(slots_[i].state==State::ready&&(lane==4||slots_[i].order<slots_[lane].order))lane=i;',
        'unsigned lane=5;for(unsigned i=0;i<capacity;++i)if(slots_[i].state==State::ready&&(lane==5||slots_[i].order<slots_[lane].order))lane=i;')
    s=once(s,'            delivery_[5]+=now_ns()-s.ready_ns;',
        '''            delivery_[5]+=now_ns()-s.ready_ns;
            s.state=State::consuming;
            if(capacity==5&&!failure&&!error&&got==std::int64_t(request.bytes)&&next<count){
                for(unsigned idle=0;idle<5;++idle)if(slots_[idle].state==State::idle){queue(idle);break;}
            }''')
    s=once(s,'for(unsigned i=0;i<started_;++i)if(threads_[i].joinable())threads_[i].join();}',
        'for(unsigned i=0;i<started_;++i)if(threads_[i].joinable())threads_[i].join();std::free(spare_);spare_=nullptr;}')
    return s
