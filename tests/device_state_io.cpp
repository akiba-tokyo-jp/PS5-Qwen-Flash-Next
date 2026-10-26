// SPDX-License-Identifier: MIT
// Exercise the pinned actual state-copy classes with a checked metadata backend.
// These stubs perform byte copies only, never model arithmetic or GPU execution.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
void check(bool v){if(!v)throw std::runtime_error("Actual device-state I/O control failed");}
unsigned allocations=0,copies=0,live_buffers=0,live_contexts=0;
}
#define GGML_ASSERT(x) check(bool(x))
#define GGML_ABORT(...) std::abort()
#define LLAMA_LOG_INFO(...) ((void)0)
enum ggml_type {GGML_TYPE_F32};
struct buffer_type {unsigned id;};using ggml_backend_buffer_type_t=buffer_type *;
struct buffer {ggml_backend_buffer_type_t type;std::vector<std::uint8_t> bytes;};
struct ggml_tensor {
    ggml_type type=GGML_TYPE_F32;int64_t ne[4]={0,1,1,1};
    struct buffer *buffer=nullptr;std::uint8_t *data=nullptr;
    ggml_tensor *view_src=nullptr;size_t view_offs=0;
};
struct ggml_context {std::vector<ggml_tensor *> tensors;};
struct ggml_init_params {size_t mem_size;void *mem_buffer;bool no_alloc;};
struct ContextDelete {void operator()(ggml_context *p)const{if(p){for(auto *t:p->tensors)delete t;delete p;--live_contexts;}}};
struct BufferDelete {void operator()(buffer *p)const{if(p){delete p;--live_buffers;}}};
using ggml_context_ptr=std::unique_ptr<ggml_context,ContextDelete>;
using ggml_backend_buffer_ptr=std::unique_ptr<buffer,BufferDelete>;
size_t ggml_tensor_overhead(){return sizeof(ggml_tensor);}
ggml_context *ggml_init(ggml_init_params p){check(p.mem_size&&p.no_alloc&&!p.mem_buffer);++live_contexts;return new ggml_context;}
void ggml_free(ggml_context *p){ContextDelete{}(p);}
size_t ggml_nbytes(const ggml_tensor *t){return t->ne[0]*t->ne[1]*t->ne[2]*t->ne[3]*4;}
size_t ggml_element_size(const ggml_tensor *){return 4;}
ggml_tensor *ggml_new_tensor_1d(ggml_context *ctx,ggml_type type,int64_t n){check(ctx&&n>=0);auto *t=new ggml_tensor;t->type=type;t->ne[0]=n;ctx->tensors.push_back(t);return t;}
ggml_tensor *ggml_view_1d(ggml_context *ctx,ggml_tensor *source,int64_t n,size_t offset){
    check(offset<=ggml_nbytes(source)&&n>=0&&size_t(n)*4<=ggml_nbytes(source)-offset);
    auto *t=ggml_new_tensor_1d(ctx,source->type,n);t->view_src=source;t->view_offs=offset;return t;
}
ggml_backend_buffer_type_t ggml_backend_buffer_get_type(buffer *p){check(p);return p->type;}
const char *ggml_backend_buft_name(ggml_backend_buffer_type_t type){return type->id==1?"mock-device-one":"mock-device-two";}
void ggml_backend_view_init(ggml_tensor *t){check(t->view_src&&t->view_src->buffer&&t->view_src->data);t->buffer=t->view_src->buffer;t->data=t->view_src->data+t->view_offs;}
struct ggml_tallocr {buffer *buf;size_t offset;};
ggml_tallocr ggml_tallocr_new(buffer *buf){check(buf);return {buf,0};}
void ggml_tallocr_alloc(ggml_tallocr *allocator,ggml_tensor *t){
    const auto offset=(allocator->offset+15)&~size_t(15),bytes=ggml_nbytes(t);
    check(offset<=allocator->buf->bytes.size()&&bytes<=allocator->buf->bytes.size()-offset);
    t->buffer=allocator->buf;t->data=allocator->buf->bytes.data()+offset;allocator->offset=offset+bytes;
}
buffer *ggml_backend_alloc_ctx_tensors_from_buft(ggml_context *ctx,ggml_backend_buffer_type_t type){
    size_t bytes=0;for(auto *t:ctx->tensors)if(!t->view_src)bytes=((bytes+15)&~size_t(15))+ggml_nbytes(t);
    check(bytes);auto *buf=new buffer{type,std::vector<std::uint8_t>(bytes)};++allocations;++live_buffers;
    auto allocator=ggml_tallocr_new(buf);for(auto *t:ctx->tensors){if(t->view_src)ggml_backend_view_init(t);else ggml_tallocr_alloc(&allocator,t);}return buf;
}
bool ggml_are_same_shape(const ggml_tensor *a,const ggml_tensor *b){return std::equal(a->ne,a->ne+4,b->ne);}
void ggml_backend_tensor_copy(const ggml_tensor *src,ggml_tensor *dst){check(src->data&&dst->data&&ggml_nbytes(src)==ggml_nbytes(dst));std::memmove(dst->data,src->data,ggml_nbytes(src));++copies;}
#include "actual_device_state_io.inc"
namespace {
struct Original {
    buffer_type type{1};ggml_context_ptr ctx;ggml_backend_buffer_ptr buf;ggml_tensor *tensor;
    explicit Original(unsigned id=1):type{id},ctx(ggml_init({4096,nullptr,true})){tensor=ggml_new_tensor_1d(ctx.get(),GGML_TYPE_F32,1024);buf.reset(ggml_backend_alloc_ctx_tensors_from_buft(ctx.get(),&type));}
    void fill(unsigned seed){for(size_t i=0;i<buf->bytes.size();++i)buf->bytes[i]=static_cast<std::uint8_t>(i*37+(i>>7)*13+seed);}
};
struct Slice {ggml_tensor *tensor;size_t offset,bytes;};
std::vector<std::uint8_t> concatenate(const std::vector<Slice> &slices){std::vector<std::uint8_t> bytes;for(auto s:slices)bytes.insert(bytes.end(),s.tensor->data+s.offset,s.tensor->data+s.offset+s.bytes);return bytes;}
void save(llama_memory_buffers &storage,std::uint8_t *metadata,const std::vector<Slice> &slices) {
    llama_io_write_device writer(metadata,16,storage);const std::uint32_t values[4]={0xaf143cd8,0,29,53};
    writer.write(values,8);for(auto s:slices)writer.write_tensor(s.tensor,s.offset,s.bytes);writer.write(values+2,8);check(writer.n_bytes()==16);
}
void restore(const llama_memory_buffers &storage,const std::uint8_t *metadata,const std::vector<Slice> &slices,bool discard=false) {
    llama_io_read_device reader(metadata,16,storage);std::uint32_t values[4]{};reader.read(values,8);
    for(auto s:slices)reader.read_tensor(s.tensor,s.offset,s.bytes);reader.read(values+2,8);
    check(values[0]==0xaf143cd8&&values[1]==0&&values[2]==29&&values[3]==53&&reader.n_bytes()==16);if(discard)reader.discard();
}
}
int main() {
    const auto initial_buffers=live_buffers,initial_contexts=live_contexts;unsigned cases=0,refused=0;
    {
        Original a;std::uint8_t metadata[16]{};llama_memory_buffers storage;
        std::vector<Slice> save_ranges{{a.tensor,0,512},{a.tensor,512,256}};
        std::vector<Slice> same{{a.tensor,0,512},{a.tensor,512,256}},rechunk{{a.tensor,0,256},{a.tensor,256,512}},three{{a.tensor,0,256},{a.tensor,256,256},{a.tensor,512,256}};
        for(const auto &read_ranges:{same,rechunk,three}) {
            a.fill(17);const auto original=a.buf->bytes;save(storage,metadata,save_ranges);a.fill(91);const auto modified=a.buf->bytes;
            restore(storage,metadata,read_ranges);check(concatenate(read_ranges)==std::vector<std::uint8_t>(original.begin(),original.begin()+768));++cases;
            check(std::equal(a.buf->bytes.begin()+768,a.buf->bytes.end(),modified.begin()+768));
        }
        auto *held=storage.begin()->second.buf.get();const auto allocated=allocations;
        a.fill(32);save(storage,metadata,save_ranges);check(storage.begin()->second.buf.get()==held&&allocations==allocated);++cases;
        a.fill(62);save(storage,metadata,rechunk);check(storage.begin()->second.buf.get()==held&&allocations==allocated);a.fill(72);restore(storage,metadata,same);++cases;
        a.fill(19);save(storage,metadata,save_ranges);a.fill(87);const auto unchanged=a.buf->bytes;restore(storage,metadata,three,true);check(a.buf->bytes==unchanged);++cases;
        {llama_io_write_device writer(metadata,16,storage);try{writer.write(metadata,17);}catch(...){++refused;}}
        {llama_io_read_device reader(metadata,16,storage);try{std::uint8_t target[17];reader.read(target,17);}catch(...){reader.discard();++refused;}}
        std::vector<Slice> larger{{a.tensor,0,1024}};const auto before=allocations;save(storage,metadata,larger);check(allocations==before+1);++cases;
    }
    check(live_buffers==initial_buffers&&live_contexts==initial_contexts);
    {
        Original a(1),b(2);a.fill(3);b.fill(5);const auto old_a=a.buf->bytes,old_b=b.buf->bytes;
        std::uint8_t metadata[16]{};llama_memory_buffers storage;std::vector<Slice> slices{{a.tensor,256,512},{b.tensor,128,512}};
        save(storage,metadata,slices);check(storage.size()==2);a.fill(9);b.fill(10);restore(storage,metadata,slices);
        check(!std::memcmp(a.tensor->data+256,old_a.data()+256,512)&&!std::memcmp(b.tensor->data+128,old_b.data()+128,512));++cases;
    }
    check(live_buffers==initial_buffers&&live_contexts==initial_contexts&&refused==2);
    std::printf("{\"actual_device_IO_cases\":%u,\"metadata_bounds_refused\":%u,\"unequal_chunking_and_discard\":true,\"same_size_reuse_and_resize\":true,\"buffer_types_independent\":true,\"byte_copies\":%u,\"all_stub_owners_returned\":true,\"GPU_calls\":0,\"model_arithmetic\":false}\n",cases,refused,copies);
}
