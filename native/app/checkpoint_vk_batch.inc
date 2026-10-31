// SPDX-License-Identifier: MIT
// Appended to the selected Vulkan implementation, with its original shaders.
extern "C" bool qwen_checkpoint_vk_copy_batch(ggml_tensor*const*source,ggml_tensor*const*target,size_t count){
    if(!count||count>256)return false;
    struct Span {vk_buffer src,dst;size_t from,to,size;};
    std::array<Span,256>spans{};
    for(size_t i=0;i<count;++i){auto*s=source[i];auto*d=target[i];
        if(!s||!d||!s->buffer||!d->buffer||!ggml_backend_buffer_is_vk(s->buffer)||!ggml_backend_buffer_is_vk(d->buffer)||
           s->type!=d->type||!ggml_are_same_shape(s,d)||!ggml_is_contiguous(s)||!ggml_is_contiguous(d))return false;
        auto*sc=static_cast<ggml_backend_vk_buffer_context*>(s->buffer->context);
        auto*dc=static_cast<ggml_backend_vk_buffer_context*>(d->buffer->context);
        auto&x=spans[i];x.src=sc->dev_buffer;x.dst=dc->dev_buffer;
        const auto so=vk_tensor_offset(s),to=vk_tensor_offset(d);
        if(s->view_offs>SIZE_MAX-so||d->view_offs>SIZE_MAX-to)return false;
        x.from=so+s->view_offs;x.to=to+d->view_offs;x.size=ggml_nbytes(s);
        if(!x.src||!x.dst||!x.size||x.from%4||x.to%4||x.size%4||x.src->device!=x.dst->device||
           (i&&x.src->device!=spans[0].src->device)||x.from>x.src->size||x.size>x.src->size-x.from||
           x.to>x.dst->size||x.size>x.dst->size-x.to)return false;
    }
    // Reject all dependencies and overlapping destinations before submission.
    for(size_t i=0;i<count;++i)for(size_t j=0;j<count;++j){
        if(spans[i].src->buffer==spans[j].dst->buffer)return false;
        if(i<j&&spans[i].dst->buffer==spans[j].dst->buffer&&
           spans[i].to<spans[j].to+spans[j].size&&spans[j].to<spans[i].to+spans[i].size)return false;
    }
    auto device=spans[0].src->device;
    std::lock_guard<std::recursive_mutex>lock(device->mutex);
    vk_context ctx=ggml_vk_create_temporary_context(device->transfer_queue->cmd_pool);
    ggml_vk_ctx_begin(device,ctx);
    for(size_t i=0;i<count;++i){auto&x=spans[i];ggml_vk_buffer_copy_async(ctx,x.dst,x.to,x.src,x.from,x.size);}
    ggml_vk_ctx_end(ctx);ggml_vk_submit(ctx,device->fence);
    VK_CHECK(device->device.waitForFences({device->fence},true,UINT64_MAX),"checkpoint batch waitForFences",device);
    device->device.resetFences({device->fence});ggml_vk_queue_command_pools_cleanup(device);
    return true;
}
