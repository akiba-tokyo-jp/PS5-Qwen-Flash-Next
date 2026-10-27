// SPDX-License-Identifier: MIT
#include "completed_expert_routes.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <cstring>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

extern "C" void __real_ggml_backend_tensor_get_async(ggml_backend_t,const ggml_tensor *,void *,size_t,size_t);
extern "C" void __real_ggml_backend_synchronize(ggml_backend_t);

namespace {
struct Observer {
    std::vector<qwen_app::CompletedExpertRoute> rows;
    std::size_t used=0;
    std::thread::id producer=std::this_thread::get_id();
    ggml_backend_t backend=nullptr;
    const std::int32_t * ids=nullptr;
    unsigned layer=0,tokens=0;
    bool get_returned=false,failed=false;
    Observer():rows(qwen_app::expert_route_capacity){}
};
std::unique_ptr<Observer> observer;
std::mutex observer_mutex;
bool capture_quarantined=false;
[[noreturn]] void fail(const char * message) {
    capture_quarantined=true;
    if(observer)observer->failed=true;
    throw qwen_app::ExpertRouteCaptureError(message);
}
void healthy() {
    if(capture_quarantined||!observer||observer->failed||observer->producer!=std::this_thread::get_id())
        fail("Completed expert-route observer is quarantined or has another producer");
}
int route_layer(const ggml_tensor * tensor) {
    if(!tensor)return -1;
    constexpr char prefix[]="ffn_moe_topk-";
    const char * name=ggml_get_name(tensor);
    if(std::strncmp(name,prefix,sizeof(prefix)-1))return -1;
    const char * p=name+sizeof(prefix)-1;
    if(*p<'0'||*p>'9')return -1;
    unsigned layer=unsigned(*p++-'0');
    if(*p>='0'&&*p<='9')layer=layer*10+unsigned(*p++-'0');
    if(!*p)return -1; // The original top-k tensor is not the cache's flattened input.
    if((std::strcmp(p," (reshaped)")&&std::strcmp(p," (cont) (reshaped)"))||layer>=qwen_app::expert_route_layers)
        fail("Selected expert tensor has an unexpected layer identity");
    return int(layer);
}
}

namespace qwen_app {
void begin_completed_expert_routes() {
    std::lock_guard<std::mutex> lock(observer_mutex);
    if(capture_quarantined||observer)fail("Completed expert-route capture cannot replace a live or failed owner");
    observer=std::make_unique<Observer>();
}
bool completed_expert_routes_pending() {
    std::lock_guard<std::mutex> lock(observer_mutex);
    return capture_quarantined||(observer&&(observer->ids||observer->failed));
}
std::uint32_t completed_expert_route_cursor() {
    std::lock_guard<std::mutex> lock(observer_mutex);healthy();
    if(observer->ids||observer->used%expert_route_layers)fail("Route comparison requires a completed whole process");
    return std::uint32_t(observer->used);
}
void compare_completed_expert_route_ranges(std::uint32_t first,std::uint32_t second,std::uint32_t count) {
    std::lock_guard<std::mutex> lock(observer_mutex);healthy();
    if(observer->ids||observer->used%expert_route_layers||first%expert_route_layers||second%expert_route_layers||count%expert_route_layers||
       first>observer->used||second>observer->used||count>observer->used-first||count>observer->used-second)
        fail("Route comparison exceeds its completed owned process ranges");
    for(std::uint32_t i=0;i<count;++i) {
        const auto &a=observer->rows[first+i];const auto &b=observer->rows[second+i];
        if(a.layer!=b.layer||a.tokens!=b.tokens)fail("Restored expert-route geometry differs");
        for(unsigned j=0;j<10*a.tokens;++j)if(a.ids[j]!=b.ids[j])fail("Restored original expert selections differ");
    }
}
void quarantine_completed_expert_routes() {
    std::lock_guard<std::mutex> lock(observer_mutex);
    capture_quarantined=true;if(observer)observer->failed=true;
}
SingleTokenExpertRoutes last_completed_single_token_routes() {
    std::lock_guard<std::mutex> lock(observer_mutex);healthy();
    if(observer->ids||observer->used<48||observer->used%48)fail("Online cost requires a completed whole-token route");
    SingleTokenExpertRoutes result{};
    for(unsigned l=0;l<48;++l) {
        const auto &row=observer->rows[observer->used-48+l];
        if(row.layer!=l||row.tokens!=1)fail("Online cost cannot substitute batched routes for ordinary observations");
        std::copy_n(row.ids.begin(),10,result.begin()+l*10);
    }
    return result;
}
std::vector<CompletedExpertRoute> finish_completed_expert_routes(std::uint64_t calls) {
    std::lock_guard<std::mutex> lock(observer_mutex);
    healthy();
    if(!calls||calls>expert_route_capacity/expert_route_layers||observer->ids||
       observer->used!=calls*expert_route_layers)
        fail("Completed expert routes do not cover every original model layer");
    // Retained evidence owns only its completed rows. Do not carry the full
    // capture capacity into the next request or retain per-row JSON objects.
    std::vector<CompletedExpertRoute> result(observer->rows.begin(),observer->rows.begin()+observer->used);
    observer.reset();return result;
}
}

extern "C" void __wrap_ggml_backend_tensor_get_async(ggml_backend_t backend,
        const ggml_tensor * tensor,void * target,size_t offset,size_t bytes) {
    bool capture=false;
    {
        std::lock_guard<std::mutex> lock(observer_mutex);
        try {
        if(observer&&!capture_quarantined) {
            const int layer=route_layer(tensor);
            if(layer>=0) {
                healthy();
                const auto * unflattened=tensor->src[0];
                const auto tokens=tensor->ne[0]/10;
                if(observer->ids||!backend||!target||offset||tensor->type!=GGML_TYPE_I32||tensor->op!=GGML_OP_RESHAPE||
                   tensor->ne[0]%10||tokens<1||tokens>4||tensor->ne[1]!=1||tensor->ne[2]!=1||tensor->ne[3]!=1||
                   !unflattened||unflattened->ne[0]!=10||unflattened->ne[1]!=tokens||unflattened->ne[2]!=1||unflattened->ne[3]!=1||
                   !ggml_is_contiguous(tensor)||bytes!=std::size_t(tensor->ne[0])*sizeof(std::int32_t)||
                   observer->used>=qwen_app::expert_route_capacity||unsigned(layer)!=observer->used%qwen_app::expert_route_layers)
                    fail("Selected expert metadata exceeds its bounded original cache contract");
                observer->backend=backend;observer->ids=static_cast<const std::int32_t *>(target);
                observer->layer=unsigned(layer);observer->tokens=unsigned(tokens);observer->get_returned=false;
                capture=true;
            }
        }
        }catch(const qwen_app::ExpertRouteCaptureError&){capture=false;}
    }
    try {
        __real_ggml_backend_tensor_get_async(backend,tensor,target,offset,bytes);
        if(capture){std::lock_guard<std::mutex> lock(observer_mutex);if(observer&&!capture_quarantined)observer->get_returned=true;}
    }catch(...){std::lock_guard<std::mutex> lock(observer_mutex);if(observer){observer->failed=true;capture_quarantined=true;}throw;}
}

extern "C" void __wrap_ggml_backend_synchronize(ggml_backend_t backend) {
    // Always preserve the original synchronization, including when capture is
    // disabled or a provider performs an internal synchronization during GET.
    try {__real_ggml_backend_synchronize(backend);}
    catch(...){std::lock_guard<std::mutex> lock(observer_mutex);if(observer){observer->failed=true;capture_quarantined=true;}throw;}
    std::lock_guard<std::mutex> lock(observer_mutex);
    if(capture_quarantined||!observer||!observer->ids||!observer->get_returned||observer->backend!=backend)return;
    if(observer->producer!=std::this_thread::get_id())return;
    try {
    healthy();
    auto & row=observer->rows[observer->used];row.layer=std::uint8_t(observer->layer);row.tokens=std::uint8_t(observer->tokens);
    for(unsigned i=0;i<10*observer->tokens;++i){
        const auto id=observer->ids[i];
        if(id<0||id>=512)fail("A synchronized selected expert ID exceeds the original vocabulary");
        row.ids[i]=std::uint16_t(id);
    }
    ++observer->used;observer->ids=nullptr;observer->backend=nullptr;observer->get_returned=false;
    }catch(const qwen_app::ExpertRouteCaptureError&){return;}
}
