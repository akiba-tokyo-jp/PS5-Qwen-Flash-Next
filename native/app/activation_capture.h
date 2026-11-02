// SPDX-License-Identifier: MIT
#pragma once
#include "ggml-backend.h"
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>

namespace qwen_app {
// Calibration only. A completed matmul still owns its inputs when the
// synchronous scheduler callback runs, before later graph nodes can reuse them.
class ActivationCapture {
public:
    static constexpr std::size_t alignment=16384,scratch_bytes=4u<<20,limit_bytes=256u<<20;
    using Get=void(*)(const ggml_tensor*,void*,std::size_t,std::size_t);
    using Write=void(*)(const void*,std::size_t);
private:
    struct Layer {
        std::array<std::int32_t,320> ids{};
        unsigned tokens=0;
        bool ranked=false,up=false,down=false;
    };
    std::array<Layer,48> layers_{};
    unsigned char *scratch_=nullptr;
    Get get_=nullptr;Write write_=nullptr;
    bool active_=false,failed_=false;
    std::uint64_t evaluations_=0,records_=0,bytes_=alignment,readback_=0;
    const char *error_="";
    void need(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
    void get(const ggml_tensor*t,void*out,std::size_t offset,std::size_t bytes){
        need(t&&t->data&&(t->buffer||(t->view_src&&t->view_src->buffer))&&
             offset<=ggml_nbytes(t)&&bytes<=ggml_nbytes(t)-offset,"Calibration tensor read bounds differ");
        get_(t,out,offset,bytes);readback_+=bytes;
    }
    static int named(const char*name,const char*prefix){
        const auto size=std::strlen(prefix);if(std::strncmp(name,prefix,size))return -1;
        unsigned layer=0;char tail=0;
        return std::sscanf(name+size,"%u%c",&layer,&tail)==1&&layer<48?int(layer):-1;
    }
    void ranked(ggml_tensor*t,unsigned layer){
        auto&state=layers_[layer];
        need(!state.ranked&&t->type==GGML_TYPE_I32&&t->op==GGML_OP_ARGSORT&&t->ne[0]==512&&
            t->ne[1]>0&&t->ne[1]<=32&&t->ne[2]==1&&t->ne[3]==1&&t->nb[0]==4,
            "Calibration requires the complete original argsort rows");
        state.tokens=unsigned(t->ne[1]);
        for(unsigned token=0;token<state.tokens;++token){
            get(t,state.ids.data()+10*token,token*t->nb[1],10*sizeof(std::int32_t));
            for(unsigned slot=0;slot<10;++slot)
                need(state.ids[10*token+slot]>=0&&state.ids[10*token+slot]<512,"Calibration original Expert ID invalid");
        }
        state.ranked=true;
    }
    void operand(ggml_tensor*t,unsigned layer,unsigned role){
        auto&state=layers_[layer];const auto*x=t->src[1];const auto*slots=t->src[2];
        need(t->op==GGML_OP_MUL_MAT_ID&&x&&slots&&state.ranked,"Calibration needs actual indexed matmul operands and original IDs");
        const unsigned k=role?640:2560;
        need(x->type==GGML_TYPE_F32&&x->ne[0]==k&&x->nb[0]==4&&x->ne[1]>0&&x->ne[1]<=10&&
            x->ne[2]==state.tokens&&x->ne[3]==1&&slots->type==GGML_TYPE_I32&&slots->ne[0]>0&&slots->ne[0]<=10&&
            slots->ne[1]==state.tokens&&slots->ne[2]==1&&slots->ne[3]==1&&slots->nb[0]==4,
            "Calibration activation or slot geometry differs");
        const unsigned selected=unsigned(slots->ne[0]),xslots=unsigned(x->ne[1]);
        need((xslots==1||xslots==selected)&&(!role||xslots==selected)&&
             !(role?state.down:state.up),"Calibration selection order or duplicate projection differs");
        const std::size_t payload=std::size_t(k)*xslots*state.tokens*4;
        const std::size_t padded=(payload+alignment-1)&~(alignment-1);
        need(alignment+padded<=scratch_bytes&&bytes_+alignment+padded<=limit_bytes,"Calibration bounded stream is full");
        std::memset(scratch_,0,alignment+padded);std::memcpy(scratch_,"QACTREC1",8);
        const auto put=[&](std::size_t at,const auto&value){std::memcpy(scratch_+at,&value,sizeof(value));};
        put(8,evaluations_);put(16,role);put(20,layer);put(24,k);put(28,state.tokens);put(32,xslots);put(36,selected);
        const std::uint64_t size=payload,rounded=padded;put(40,size);put(48,rounded);
        const std::uint32_t type=t->src[0]?std::uint32_t(t->src[0]->type):UINT32_MAX;put(56,type);
        for(unsigned token=0;token<state.tokens;++token){
            std::memcpy(scratch_+64+4*selected*token,state.ids.data()+10*token,4*selected);
            get(slots,scratch_+1344+4*selected*token,token*slots->nb[1],4*selected);
            for(unsigned slot=0;slot<xslots;++slot){
                auto*out=scratch_+alignment+(std::size_t(token)*xslots+slot)*k*4;
                get(x,out,token*x->nb[2]+slot*x->nb[1],k*4);
                for(unsigned column=0;column<k;++column){float value;std::memcpy(&value,out+column*4,4);
                    need(std::isfinite(value),"Calibration activation contains nonfinite values");}
            }
        }
        write_(scratch_,alignment+padded);bytes_+=alignment+padded;++records_;
        if(role)state.down=true;else state.up=true;
    }
public:
    void initialize(void*scratch,Get get,Write write){
        need(!scratch_&&scratch&&get&&write,"One fresh calibration sink required");
        scratch_=static_cast<unsigned char*>(scratch);get_=get;write_=write;
    }
    void request(unsigned ordinal){active_=ordinal==0&&!failed_;}
    bool active()const{return active_&&!failed_;}
    void fail(const char*message)noexcept{failed_=true;active_=false;if(!*error_)error_=message;}
    void begin_compute(){
        need(active(),"Calibration compute is inactive");++evaluations_;
        need(evaluations_<=33,"Calibration evaluation limit exceeded");
        for(auto&layer:layers_)layer=Layer{};
    }
    void end_compute()noexcept{
        if(failed_)return;
        for(const auto&layer:layers_)if(!layer.ranked||!layer.up||!layer.down){fail("Calibration graph did not expose all48 complete layers");break;}
    }
    bool evaluate(ggml_tensor*t,bool ask)noexcept{
        if(!t)return !ask;
        const int rank=named(t->name,"ffn_moe_argsort-"),up=named(t->name,"ffn_moe_up-"),down=named(t->name,"ffn_moe_down-");
        if(ask)return active()&&(rank>=0||up>=0||down>=0);
        // Diagnostic failures never return false from a completed callback:
        // false would truncate the real scheduler split and affect inference.
        if(!active())return true;
        try{if(rank>=0)ranked(t,unsigned(rank));else if(up>=0)operand(t,unsigned(up),0);else if(down>=0)operand(t,unsigned(down),1);}
        catch(...){fail("Calibration operand, readback or synchronous stream failed");}
        return true;
    }
    bool failed()const{return failed_;}
    const char*error()const{return error_;}
    std::uint64_t evaluations()const{return evaluations_;}
    std::uint64_t records()const{return records_;}
    std::uint64_t bytes()const{return bytes_;}
    std::uint64_t readback_bytes()const{return readback_;}
};
}
