# SPDX-License-Identifier: MIT
"""Transform only pinned device state writers/readers; preserve their ABI."""
from build_speculative_batch_probe import once
API=r'''
struct qwen_checkpoint_fixture_state {llama_memory_buffers buffers;};
extern "C" void*qwen_checkpoint_fixture_create(){return new qwen_checkpoint_fixture_state;}
extern "C" void qwen_checkpoint_fixture_free(void*p){delete static_cast<qwen_checkpoint_fixture_state*>(p);}
extern "C" void qwen_checkpoint_fixture_save(void*p,ggml_tensor*const*t,const size_t*offset,const size_t*size,size_t count){
    auto&s=*static_cast<qwen_checkpoint_fixture_state*>(p);uint8_t metadata=0;
    llama_io_write_device writer(&metadata,0,s.buffers);
    for(size_t i=0;i<count;++i)writer.write_tensor(t[i],offset[i],size[i]);
}
extern "C" void qwen_checkpoint_fixture_restore(void*p,ggml_tensor*const*t,const size_t*offset,const size_t*size,size_t count){
    auto&s=*static_cast<qwen_checkpoint_fixture_state*>(p);uint8_t metadata=0;
    llama_io_read_device reader(&metadata,0,s.buffers);
    for(size_t i=0;i<count;++i)reader.read_tensor(t[i],offset[i],size[i]);
}
'''
def transform(text,fixture_api=False):
 text=once(text,'class llama_io_write_device : public llama_io_write_i {','#include "checkpoint_device_trial.h"\nclass llama_io_write_device : public llama_io_write_i {')
 text=once(text,'    ~llama_io_write_device() {\n        llama_memory_buffers mbufs_new;',
     '    ~llama_io_write_device() {\n        if(qwen_checkpoint_trial::reuse_descriptors(winfos,mbufs))return;\n        llama_memory_buffers mbufs_new;')
 text=once(text,'                if (!mbuf_cur.buf || mbuf_cur.total_size != mbuf.total_size) {',
     '                if (!mbuf_cur.buf || (mbuf_cur.total_size != mbuf.total_size && !qwen_checkpoint_trial::fits(mbuf_cur.buf.get(),mbuf.cpy))) {')
 text=once(text,'            for (size_t i = 0; i < mbuf_cur.org.size(); ++i) {\n                ggml_backend_tensor_copy(mbuf_cur.org[i], mbuf_cur.cpy[i]);\n            }',
     '            qwen_checkpoint_trial::copy(mbuf_cur.org,mbuf_cur.cpy);')
 text=once(text,'                    for (size_t i = 0; i < mbuf_cur.org.size(); ++i) {\n                        ggml_backend_tensor_copy(mbuf_cur.cpy[i], mbuf.org[i]);\n                    }',
     '                    qwen_checkpoint_trial::copy(mbuf_cur.cpy,mbuf.org);')
 if fixture_api:
  start=text.index('class llama_io_read_device :');end=text.index('\n};',start)+3;text=text[:end]+API+text[end:]
 return text
