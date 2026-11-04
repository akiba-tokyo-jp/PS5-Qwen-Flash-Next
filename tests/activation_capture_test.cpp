// SPDX-License-Identifier: MIT
#include "activation_capture.h"
#include <cassert>
#include <vector>

extern "C" size_t ggml_nbytes(const ggml_tensor*t){return std::size_t(t->ne[3]-1)*t->nb[3]+
    std::size_t(t->ne[2]-1)*t->nb[2]+std::size_t(t->ne[1]-1)*t->nb[1]+std::size_t(t->ne[0])*t->nb[0];}
namespace {
std::vector<unsigned char> sink;
bool fail_get=false;
void get(const ggml_tensor*t,void*out,std::size_t offset,std::size_t bytes){
    if(fail_get)throw std::runtime_error("Injected returned readback failure");
    assert(offset+bytes<=ggml_nbytes(t));std::memcpy(out,static_cast<unsigned char*>(t->data)+offset,bytes);
}
void write(const void*data,std::size_t bytes){const auto*p=static_cast<const unsigned char*>(data);sink.assign(p,p+bytes);}
ggml_tensor tensor(ggml_type type,void*data,unsigned k,unsigned slots,unsigned tokens,unsigned gap=0){
    ggml_tensor t{};t.type=type;t.data=data;t.buffer=reinterpret_cast<ggml_backend_buffer_t>(1);
    t.ne[0]=k;t.ne[1]=slots;t.ne[2]=tokens;t.ne[3]=1;t.nb[0]=4;t.nb[1]=4*k+gap;
    t.nb[2]=t.nb[1]*slots+gap;t.nb[3]=t.nb[2]*tokens;return t;
}
template<class T>T field(unsigned offset){T out;std::memcpy(&out,sink.data()+offset,sizeof(out));return out;}
}
int main(){
    using qwen_app::ActivationCapture;
    std::vector<unsigned char> scratch(ActivationCapture::scratch_bytes);
    std::vector<std::int32_t> ranks(2*512),slots_data{77,88,99,111};
    for(unsigned t=0;t<2;++t)for(unsigned i=0;i<512;++i)ranks[t*512+i]=int((i+9*t)%512);
    auto rank=tensor(GGML_TYPE_I32,ranks.data(),512,2,1);rank.op=GGML_OP_ARGSORT;
    auto slots=tensor(GGML_TYPE_I32,slots_data.data(),2,2,1);
    std::vector<unsigned char> xdata(24000),ddata(16000);
    auto x=tensor(GGML_TYPE_F32,xdata.data(),2560,1,2,16);
    auto d=tensor(GGML_TYPE_F32,ddata.data(),640,2,2,16);
    for(unsigned t=0;t<2;++t)for(unsigned s=0;s<2;++s)for(unsigned k=0;k<640;++k){
        const float v=float(t*10000+s*1000+k);std::memcpy(ddata.data()+t*d.nb[2]+s*d.nb[1]+k*4,&v,4);
    }
    auto up=tensor(GGML_TYPE_F32,nullptr,640,2,2);up.op=GGML_OP_MUL_MAT_ID;up.src[1]=&x;up.src[2]=&slots;
    auto down=up;down.src[1]=&d;
    ActivationCapture capture;capture.initialize(scratch.data(),get,write);capture.request(0);capture.begin_compute();
    for(unsigned layer=0;layer<48;++layer){
        std::snprintf(rank.name,sizeof(rank.name),"ffn_moe_argsort-%u",layer);
        std::snprintf(up.name,sizeof(up.name),"ffn_moe_up-%u",layer);
        std::snprintf(down.name,sizeof(down.name),"ffn_moe_down-%u",layer);
        assert(capture.evaluate(&rank,true));assert(capture.evaluate(&rank,false));
        assert(capture.evaluate(&up,true));assert(capture.evaluate(&up,false));
        assert(field<unsigned>(24)==2560&&field<unsigned>(32)==1&&field<unsigned>(36)==2);
        assert(field<int>(64)==0&&field<int>(68)==1&&field<int>(72)==9&&field<int>(1344)==77);
        assert(capture.evaluate(&down,true));assert(capture.evaluate(&down,false));
        assert(field<unsigned>(24)==640&&field<unsigned>(32)==2&&field<unsigned>(20)==layer);
        assert(field<float>(16384+4*(640*3+639))==11639.0f);
    }
    capture.end_compute();assert(!capture.failed()&&capture.records()==96&&capture.evaluations()==1);
    capture.request(1);assert(!capture.evaluate(&up,true));assert(capture.evaluate(&up,false));
    // Returned diagnostic failures must not truncate a scheduler split.
    ActivationCapture broken;broken.initialize(scratch.data(),get,write);broken.request(0);broken.begin_compute();
    fail_get=true;assert(broken.evaluate(&rank,false));assert(broken.failed());assert(broken.evaluate(&down,false));
    assert(!broken.evaluate(&down,true));fail_get=false;
    ActivationCapture missing;missing.initialize(scratch.data(),get,write);missing.request(0);missing.begin_compute();
    missing.end_compute();assert(missing.failed()&&missing.evaluate(&up,false));
    return 0;
}
