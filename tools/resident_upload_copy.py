#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the original fenced Vulkan copy path for resident-load destinations."""


def generate(source):
    begin=source.index('void ggml_vk_buffer_write_2d(vk_buffer& dst,')
    end=source.index('\nbool ggml_vk_buffer_read_2d_async(',begin)
    body=source[begin:end]
    old='    // Buffer is already mapped\n    if(dst->memory_property_flags & vk::MemoryPropertyFlagBits::eHostVisible) {'
    new='''    const bool resident_copy=&qwen_app_resident_GPU_load_copy&&qwen_app_resident_GPU_load_copy();
    // Keep CPU writes away from large resident mappings in this load-only scope.
    if((dst->memory_property_flags & vk::MemoryPropertyFlagBits::eHostVisible)&&!resident_copy) {'''
    if body.count(old)!=1:raise ValueError('Unique original synchronous mapped write required')
    body=body.replace(old,new)
    old='''        bool ret = ggml_vk_buffer_write_2d_async(subctx, dst, offset, src, spitch, dpitch, width, height, true);
        GGML_ASSERT(ret);'''
    new='''        if(resident_copy) {
            if(!src||!width||!height||width>ggml_app_transfer_limit/height||
               offset>dst->size||height-1>(SIZE_MAX-width)/std::max<size_t>(dpitch,1)||
               height-1>(SIZE_MAX-width)/std::max<size_t>(spitch,1)||
               (height-1)*spitch+width>UINTPTR_MAX-reinterpret_cast<uintptr_t>(src)||
               (height-1)*dpitch+width>dst->size-offset)
                throw std::length_error("Resident GPU upload exceeds its exact bounded destination");
            const size_t staging_bytes=width*height;
            ggml_vk_ensure_sync_staging_buffer(dst->device,staging_bytes);
            const auto staging=dst->device->sync_staging;
            std::vector<vk::BufferCopy> copies;
            copies.reserve(height);
            for(size_t row=0;row<height;++row) {
                memcpy(static_cast<uint8_t *>(staging->ptr)+row*width,static_cast<const uint8_t *>(src)+row*spitch,width);
                copies.emplace_back(row*width,offset+row*dpitch,width);
            }
            ggml_vk_sync_buffers(nullptr,subctx);
            subctx->s->buffer->buf.copyBuffer(staging->buffer,dst->buffer,copies);
        }else {
            bool ret = ggml_vk_buffer_write_2d_async(subctx, dst, offset, src, spitch, dpitch, width, height, true);
            GGML_ASSERT(ret);
        }'''
    if body.count(old)!=1:raise ValueError('Unique original synchronous staging frontier required')
    body=body.replace(old,new)
    old='        ggml_vk_queue_command_pools_cleanup(dst->device);'
    if body.count(old)!=1:raise ValueError('Unique original positive fence cleanup required')
    body=body.replace(old,old+'\n        if(resident_copy){++resident_upload_calls;resident_upload_bytes+=width*height;qwen_app_resident_GPU_upload_completed(width*height);}')
    declaration='''#include <atomic>
extern "C" bool qwen_app_resident_GPU_load_copy() __attribute__((weak));
extern "C" void qwen_app_resident_GPU_upload_completed(uint64_t);
static std::atomic<uint64_t> resident_upload_calls{0},resident_upload_bytes{0};
extern "C" void qwen_app_resident_GPU_load_copy_counters(uint64_t *calls,uint64_t *bytes){
    if(calls)*calls=resident_upload_calls.load();if(bytes)*bytes=resident_upload_bytes.load();
}
'''
    return declaration+source[:begin]+body+source[end:]
