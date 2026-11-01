// SPDX-License-Identifier: MIT
// Included after the pinned Vulkan common header in the scoped GPU provider.
#include "frontier_options.h"
#include "command_cache_key.h"
#include <unordered_map>
namespace {
thread_local bool frontier_command_eligible=false;
struct FrontierCommandScope {
    bool previous;
    explicit FrontierCommandScope(bool eligible):previous(frontier_command_eligible){frontier_command_eligible=eligible;}
    ~FrontierCommandScope(){frontier_command_eligible=previous;}
};
struct FrontierTape {vk::DescriptorPool descriptors;vk::CommandBuffer command;};
struct FrontierTapes {
    vk::Device device;vk::CommandPool pool;std::uint64_t generation=0;
    std::unordered_map<std::string,FrontierTape> entries;
};
std::unordered_map<ggml_backend_vk_context*,FrontierTapes> frontier_tapes;
std::uint64_t frontier_command_stats[8]{};
template<class T>std::uint64_t frontier_handle(T value){
    static_assert(sizeof(value)<=sizeof(std::uint64_t),"Native Vulkan handle width");
    std::uint64_t bits=0;std::memcpy(&bits,&value,sizeof(value));return bits;
}
void frontier_clear_tapes(ggml_backend_vk_context *ctx) {
    auto it=frontier_tapes.find(ctx);if(it==frontier_tapes.end())return;
    // Caller has completed the original synchronize/fence path. Never evict
    // or reset a tape from a recording/dispatch or a pending submission.
    GGML_ASSERT(!ctx->submit_pending&&ctx->compute_ctx.expired());
    auto &cache=it->second;
    if(cache.pool)cache.device.destroyCommandPool(cache.pool);
    for(auto &item:cache.entries)cache.device.destroyDescriptorPool(item.second.descriptors);
    frontier_tapes.erase(it);++frontier_command_stats[6];
}
void frontier_retire_stale_tapes(ggml_backend_vk_context *ctx) {
    auto it=frontier_tapes.find(ctx);if(it==frontier_tapes.end())return;
    if(it->second.generation!=ctx->device->buffer_destroy_count.load(std::memory_order_acquire))frontier_clear_tapes(ctx);
}
}
extern "C" void qwen_frontier_command_stats(std::uint64_t*out){for(unsigned i=0;i<8;++i)out[i]=frontier_command_stats[i];}
template<typename T>inline void qwen_frontier_dispatch_pipeline(ggml_backend_vk_context *ctx,vk_context &subctx,vk_pipeline &pipeline,
    std::initializer_list<vk::DescriptorBufferInfo>const& infos,const T& pc,std::array<std::uint32_t,3> elements) {
    if(!(qwen_frontier::mode.load(std::memory_order_relaxed)&16)||!frontier_command_eligible){ggml_vk_dispatch_pipeline(ctx,subctx,pipeline,infos,pc,elements);return;}
    ++frontier_command_stats[0];
    const auto generation=ctx->device->buffer_destroy_count.load(std::memory_order_acquire);
    auto &cache=frontier_tapes[ctx];
    if(cache.pool&&cache.generation!=generation){++frontier_command_stats[3];ggml_vk_dispatch_pipeline(ctx,subctx,pipeline,infos,pc,elements);return;}
    const std::array<std::uint32_t,3> groups={CEIL_DIV(elements[0],pipeline->wg_denoms[0]),CEIL_DIV(elements[1],pipeline->wg_denoms[1]),CEIL_DIV(elements[2],pipeline->wg_denoms[2])};
    for(unsigned i=0;i<3;++i)GGML_ASSERT(groups[i]<=ctx->device->properties.limits.maxComputeWorkGroupCount[i]);
    GGML_ASSERT(infos.size()==pipeline->parameter_count&&infos.size()<=MAX_PARAMETER_COUNT&&pipeline->push_constant_size==push_constant_size(pc));
    std::vector<qwen_frontier::CommandBinding> bindings;bindings.reserve(infos.size());
    for(const auto &b:infos)bindings.push_back({frontier_handle(static_cast<VkBuffer>(b.buffer)),b.offset,b.range});
    auto key=qwen_frontier::command_key(reinterpret_cast<std::uintptr_t>(ctx),generation,frontier_handle(static_cast<VkPipeline>(pipeline->pipeline)),frontier_handle(static_cast<VkPipelineLayout>(pipeline->layout)),subctx->p->q->queue_family_index,groups,bindings,push_constant_data(pc),push_constant_size(pc));
    auto found=cache.entries.find(key);
    // This finite first slice never evicts an in-flight secondary. Full caches
    // retain the existing path; stale caches retire only at positive completion.
    constexpr std::size_t max_entries=256;
    if(found==cache.entries.end()&&cache.entries.size()>=max_entries){++frontier_command_stats[3];ggml_vk_dispatch_pipeline(ctx,subctx,pipeline,infos,pc,elements);return;}
    GGML_ASSERT(ctx->descriptor_set_idx<ctx->descriptor_sets.size());++ctx->descriptor_set_idx;
    if(found==cache.entries.end()) {
        if(!cache.pool){cache.device=ctx->device->device;cache.generation=generation;cache.pool=cache.device.createCommandPool({{},subctx->p->q->queue_family_index});}
        FrontierTape tape{};
        const vk::DescriptorPoolSize size(vk::DescriptorType::eStorageBuffer,MAX_PARAMETER_COUNT);
        tape.descriptors=cache.device.createDescriptorPool({{},1,size});
        const auto descriptor=cache.device.allocateDescriptorSets({tape.descriptors,ctx->device->dsl})[0];
        cache.device.updateDescriptorSets({vk::WriteDescriptorSet{descriptor,0,0,pipeline->parameter_count,vk::DescriptorType::eStorageBuffer,nullptr,infos.begin()}},{});
        tape.command=cache.device.allocateCommandBuffers({cache.pool,vk::CommandBufferLevel::eSecondary,1})[0];
        const vk::CommandBufferInheritanceInfo inheritance{};
        tape.command.begin({vk::CommandBufferUsageFlagBits::eSimultaneousUse,&inheritance});
        tape.command.pushConstants(pipeline->layout,vk::ShaderStageFlagBits::eCompute,0,push_constant_size(pc),push_constant_data(pc));
        tape.command.bindPipeline(vk::PipelineBindPoint::eCompute,pipeline->pipeline);
        tape.command.bindDescriptorSets(vk::PipelineBindPoint::eCompute,pipeline->layout,0,{descriptor},{});
        tape.command.dispatch(groups[0],groups[1],groups[2]);tape.command.end();
        found=cache.entries.emplace(std::move(key),tape).first;++frontier_command_stats[1];
        frontier_command_stats[4]=std::max<std::uint64_t>(frontier_command_stats[4],cache.entries.size());
    } else ++frontier_command_stats[2];
    {ggml_vk_debug_label label(subctx,pipeline->name,groups[0],groups[1],groups[2]);subctx->s->buffer->buf.executeCommands({found->second.command});}
    ++frontier_command_stats[5];
}
#define ggml_vk_dispatch_pipeline qwen_frontier_dispatch_pipeline
