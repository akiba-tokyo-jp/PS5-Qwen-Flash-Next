// SPDX-License-Identifier: MIT
#include "router_shadow_graph.h"
#include "router_shadow_observer.h"
#include <iostream>
namespace {void check(bool ok){if(!ok)throw std::runtime_error("Router shadow observation differs");}}
int main() {
    unsigned records=0,refused=0,graphs=0;
    for(unsigned width=1;width<=4;++width) {
        qwen_app::RouterShadowObserver o(23);std::array<std::int32_t,40> early{},actual{};
        for(unsigned t=0;t<width;++t)for(unsigned i=0;i<10;++i){early[10*t+i]=i;actual[10*t+i]=i+1;}
        for(unsigned i=1;i<=96;++i){o.begin_process(i<=48?1:2,i<=48?i:i-48,width);o.early(23,early.data(),width,10);o.demand(23,actual.data(),width,20);o.complete_process(true);}
        check(o.size()==96&&o.record(95).process==48&&o.record(95).request==2&&o.record(95).predicted[0][0]==0&&o.record(95).actual[0][0]==1);records+=o.size();
        try{o.begin_process(3,1,width);}catch(const std::invalid_argument &){++refused;}
        auto *ctx=ggml_init({1u<<20,nullptr,true});check(ctx);
        auto *router=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,512);auto *hidden=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,width);
        auto *ids=qwen_app::build_router_shadow(ctx,hidden,router);auto *graph=ggml_new_graph(ctx);ggml_build_forward_expand(graph,ids);
        check(ids->type==GGML_TYPE_I32&&ids->ne[0]==10&&ids->ne[1]==width&&ids->nb[1]==512*4);
        unsigned multiply=0;
        for(int i=0;i<ggml_graph_n_nodes(graph);++i){auto *t=ggml_graph_node(graph,i);if(t->op==GGML_OP_MUL_MAT){check(t->src[0]==router&&t->src[1]==hidden&&t->type==GGML_TYPE_F32);++multiply;}}
        check(multiply==1);++graphs;
        router->type=GGML_TYPE_BF16;try{qwen_app::build_router_shadow(ctx,hidden,router);}catch(const std::invalid_argument &){++refused;}
        ggml_free(ctx);
    }
    for(unsigned mode=0;mode<9;++mode) {
        qwen_app::RouterShadowObserver o(23);std::array<std::int32_t,40> ids{};for(unsigned i=0;i<10;++i)ids[i]=i;
        o.begin_process(1,1,1);bool failed=false;
        try {
            if(mode==0)o.demand(23,ids.data(),1,20);
            else if(mode==1)o.early(22,ids.data(),1,10);
            else if(mode==2){ids[1]=ids[0];o.early(23,ids.data(),1,10);}
            else if(mode==3){ids[0]=512;o.early(23,ids.data(),1,10);}
            else if(mode==4)o.complete_process(true);
            else {o.early(23,ids.data(),1,10);
                if(mode==5)o.complete_process(true);
                else if(mode==6)o.demand(23,ids.data(),1,9);
                else if(mode==7)o.early(23,ids.data(),1,11);
                else{o.demand(23,ids.data(),1,20);o.complete_process(false);}
            }
        }catch(const std::runtime_error &){failed=true;}
        check(failed&&o.failed());++refused;
    }
    std::cout<<"{\"bounded_complete_records\":"<<records<<",\"actual_GGML_shadow_graphs\":"<<graphs
        <<",\"refusals\":"<<refused<<",\"fixed_observer_bytes\":"<<sizeof(qwen_app::RouterShadowObserver)
        <<",\"hidden_states_or_model_weights_read\":false,\"GPU_execution\":false}"<<std::endl;
}
