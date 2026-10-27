// SPDX-License-Identifier: MIT
#include "ready_expert_native.h"
#include "device_buffer_budget.h"
#include "native_gpu.h"
#include "system_memory.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include <ps5platform/kernel.h>
namespace qwen_app {
namespace {
unsigned index(ReadyGraphPhase phase) {
    switch(phase) {
    case ReadyGraphPhase::complete_serial:return 0;
    case ReadyGraphPhase::first_group:return 1;
    case ReadyGraphPhase::second_group:return 2;
    case ReadyGraphPhase::original_reduction:return 3;
    }
    throw std::invalid_argument("Unknown ready-expert graph phase");
}
}
void ReadyExpertNativeGraphs::producer()const {
    if(std::this_thread::get_id()!=producer_)throw std::logic_error("Native ready graphs require the sole original GPU producer");
}
void ReadyExpertNativeGraphs::prepare(ggml_context *ctx,ggml_backend_t backend,
        const std::array<ReadyExpertGraphInputs,2>&groups,ggml_tensor *output,
        std::uint64_t prior,void (*stage)(const char *),void (*checkpoint)()) {
    producer();
    if(prepared_||failed_||closed_||!ctx||!backend||!ggml_backend_is_vk(backend)||!stage||!checkpoint||!prior||prior>std::numeric_limits<std::uint64_t>::max()-3)
        throw std::invalid_argument("Fresh native ready graphs and exact completion operations required");
    try {
        graphs_[0]=build_serial_ready_expert_graph(ctx,groups,output);
        graphs_[1]=build_ready_expert_graph(ctx,groups[0]);graphs_[2]=build_ready_expert_graph(ctx,groups[1]);
        graphs_[3]=build_ready_expert_reduction(ctx,groups[0].contributions,output);
        selected_[0].fill(true);selected_[3].fill(true);
        for(unsigned group=0;group<2;++group)for(unsigned i=0;i<groups[group].count;++i)
            selected_[group+1][groups[group].original_ordinals[i]]=true;
        context_=ctx;backend_=backend;stage_=stage;checkpoint_=checkpoint;last_epoch_=prior;prepared_=true;
    }catch(...){failed_=true;throw;}
}
void ReadyExpertNativeGraphs::allocate_workspace() {
    producer();
    if(!prepared_||failed_||closed_||workspace_||next_||complete_control_)
        throw std::logic_error("One healthy ready workspace allocation is required before source work");
    try {
        const auto type=ggml_backend_get_default_buffer_type(backend_);
        if(!type)throw std::runtime_error("Native ready workspace requires the actual Vulkan buffer type");
        const auto planned=ggml_backend_alloc_ctx_tensors_from_buft_size(context_,type);
        constexpr std::uint64_t cap=16u<<20,reserve=512u<<20;
        if(!planned||planned>cap)throw std::length_error("Native ready graph workspace exceeds its 16 MiB scope");
        const auto stats=native_model_device_stats();
        if(stats.live>model_postload_device_budget-cap)throw std::length_error("Native ready workspace lacks aggregate ledger capacity");
        const auto memory=admit_native_system_memory();
        std::int64_t physical=0;std::size_t available=0;const auto pool=sceKernelGetDirectMemorySize();
        if(qualified_system_headroom(memory)<(256u<<20)||pool<=0||
           sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available)<0||available<cap+reserve)
            throw std::runtime_error("Native ready workspace cannot retain original system and Direct reserves");
        stage_("ready_expert_workspace_priced_before_allocation");checkpoint_();
        workspace_=ggml_backend_alloc_ctx_tensors(context_,backend_);
        if(!workspace_||!ggml_backend_buffer_get_size(workspace_)||ggml_backend_buffer_get_size(workspace_)>cap)
            throw std::runtime_error("Native ready workspace allocation refused; owners retained");
        ggml_backend_synchronize(backend_);checkpoint_();
    }catch(...){failed_=true;qwen_native_driver_retain();throw;}
}
ggml_cgraph *ReadyExpertNativeGraphs::graph(ReadyGraphPhase phase)const {
    producer();if(!prepared_||failed_||closed_)throw std::logic_error("Native ready graphs are not healthy and prepared");
    return graphs_[index(phase)];
}
ReadyExecutionOps ReadyExpertNativeGraphs::operations() {
    producer();if(!prepared_||failed_||closed_||!workspace_)throw std::logic_error("Native ready execution requires its actual allocated workspace");
    return {dispatch,this};
}
bool ReadyExpertNativeGraphs::dispatch(ReadyGraphPhase phase,std::uint64_t epoch,const std::array<bool,10> &selected,void *opaque) {
    if(!opaque)throw std::invalid_argument("Native ready graph owner required");
    auto &self=*static_cast<ReadyExpertNativeGraphs *>(opaque);
    try {
        self.producer();
        const auto at=index(phase);
        if(!self.prepared_||self.failed_||self.closed_||!self.workspace_||self.complete_control_||epoch!=self.last_epoch_+1||
           selected!=self.selected_[at]||(self.next_==0?at>1:at!=self.next_))
            throw std::logic_error("Native ready graph order, selected contributions or completed epoch differs");
        // The source coordinator owns the mutable backpressure gate while it
        // runs. The GPU producer uses only the pure fresh predicate here.
        if(qualified_system_headroom(observe_native_system_memory())<(256u<<20))
            throw std::runtime_error("Native ready graph cannot retain the original Flexible reserve");
        constexpr const char *plans[]={"ready_expert_before_complete_serial_graph","ready_expert_before_first_group_graph",
            "ready_expert_before_second_group_graph","ready_expert_before_original_reduction_graph"};
        self.stage_(plans[at]);
        if(ggml_backend_graph_compute(self.backend_,self.graphs_[at])!=GGML_STATUS_SUCCESS)
            throw std::runtime_error("Native ready graph compute failed; all backing retained");
        ggml_backend_synchronize(self.backend_);self.checkpoint_();
        self.stage_("ready_expert_graph_synchronized_driver_completion_returned");
        self.last_epoch_=epoch;self.complete_control_=at==0;self.next_=at+1;return true;
    }catch(...){self.failed_=true;qwen_native_driver_retain();throw;}
}
void ReadyExpertNativeGraphs::close_completed(ReadyExpertExecution &execution,const ReadyExpertWave &wave) {
    producer();const auto e=execution.snapshot();const auto s=wave.snapshot();const auto source=execution.source_snapshot();
    if(!prepared_||failed_||closed_||!workspace_||(!complete_control_&&next_!=4)||
       !e.completed||e.failed||e.owners_must_be_retained||e.last_completed_GPU_epoch!=last_epoch_||
       e.completed_graphs!=(complete_control_?1u:3u)||!s.retired||s.failed||s.IO_pending||s.GPU_pending||
       !s.reduction_complete||!source.joined||source.failed)
        throw std::logic_error("Native ready workspace retirement requires matching completed source, graphs and original reduction");
    try {
        ggml_backend_synchronize(backend_);checkpoint_();ggml_backend_buffer_free(workspace_);workspace_=nullptr;checkpoint_();closed_=true;
    }catch(...){failed_=true;qwen_native_driver_retain();throw;}
}
}
