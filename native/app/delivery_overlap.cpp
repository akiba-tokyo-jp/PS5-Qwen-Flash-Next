// SPDX-License-Identifier: MIT
#include "delivery_overlap_plan.h"
#include "ggml-backend.h"
#include "ggml-impl.h"
#include "native_gpu.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <thread>
namespace {
qwen_app::DeliveryOverlapPlan plan;
std::array<ggml_tensor*,1024>early{},remaining{};
std::array<std::uint64_t,10>counts{};
ggml_cgraph*pending=nullptr;ggml_tensor**original=nullptr;int original_count=0;std::uint64_t original_uid=0;
ggml_backend_t owner=nullptr;bool enabled=false,retired=false;
std::thread::id producer;
std::uint64_t graph_epoch=0,used_graph_epoch=UINT64_MAX;ggml_tensor*declared_shared=nullptr;int declared_layer=-1;
std::array<std::uint64_t,4>graph_counts{};
char alias_writer[64]{},alias_reader[64]{},alias_input[64]{};
bool pure(ggml_op op){switch(op){
    case GGML_OP_NONE:case GGML_OP_MUL_MAT:case GGML_OP_ADD:case GGML_OP_MUL:case GGML_OP_DIV:case GGML_OP_SCALE:
    case GGML_OP_UNARY:case GGML_OP_GLU:case GGML_OP_CONT:case GGML_OP_VIEW:case GGML_OP_RESHAPE:case GGML_OP_PERMUTE:case GGML_OP_TRANSPOSE:return true;
    default:return false;}}
qwen_app::OverlapRange range(const ggml_tensor*t){
    if(!t||!t->data)return {};
    const auto*root=t;while(root->view_src)root=root->view_src;
    auto buffer=t->buffer?t->buffer:root->buffer;
    if(!buffer)throw std::runtime_error("Allocated overlap tensor buffer identity required");
    // Device buffers share vk_ptr_base=0x1000. Those addresses are offsets in
    // distinct objects, while host buffers use their actual CPU address space.
    const auto space=ggml_backend_buffer_is_host(buffer)?0:reinterpret_cast<std::uintptr_t>(buffer);
    return {reinterpret_cast<std::uintptr_t>(t->data),ggml_nbytes(t),space};
}
int index(ggml_cgraph*g,const ggml_tensor*t){for(int i=0;t&&i<g->n_nodes;++i)if(g->nodes[i]==t)return i;return -1;}
}
extern "C" void qwen_app_overlap_select(bool value){if(pending)throw std::runtime_error("Overlap graph remains live");if(enabled!=value)++graph_epoch;enabled=value;producer=std::this_thread::get_id();}
extern "C" void qwen_app_overlap_stats(std::uint64_t*out){if(pending)throw std::runtime_error("Overlap snapshot precedes retirement");std::copy(counts.begin(),counts.end(),out);}
extern "C" void qwen_app_overlap_begin(ggml_backend_t backend,ggml_cgraph*g,int layer,bool has_misses){
    used_graph_epoch=graph_epoch;if(!enabled)return;if(pending||producer!=std::this_thread::get_id())throw std::runtime_error("Overlap producer or graph differs");++counts[0];
    if(!has_misses){++counts[1];return;}if(!g||g->n_nodes<=0||g->n_nodes>1024){++counts[2];return;}
    char endpoint_name[64];std::snprintf(endpoint_name,sizeof(endpoint_name),"ffn_shexp_gated-%d",layer);int endpoint=-1;
    static_assert(GGML_MAX_SRC<=16,"Bounded dependency metadata required");
    for(int i=0;i<g->n_nodes;++i){auto*t=g->nodes[i];auto&n=plan.nodes[i];n={};n.output=range(t);n.pure=pure(t->op);n.writes=t->op!=GGML_OP_NONE&&t->op!=GGML_OP_VIEW&&t->op!=GGML_OP_RESHAPE&&t->op!=GGML_OP_TRANSPOSE&&t->op!=GGML_OP_PERMUTE;n.inplace=ggml_op_can_inplace(t->op);
        if(!std::strcmp(t->name,endpoint_name))endpoint=i;
        for(unsigned j=0;j<GGML_MAX_SRC;++j)if(t->src[j]){n.inputs[j]=index(g,t->src[j]);if(n.inputs[j]<0)n.external[j]=range(t->src[j]);}
    }
    const auto result=plan.inspect(unsigned(g->n_nodes),endpoint);if(result!=qwen_app::DeliveryOverlapPlan::Decision::ready){
        ++counts[2+unsigned(result)];
        if(result==qwen_app::DeliveryOverlapPlan::Decision::live_input_alias&&!alias_writer[0]){
            for(int i=0;i<g->n_nodes&&!alias_writer[0];++i)if(!plan.selected[i])
                for(int j=0;j<g->n_nodes&&!alias_writer[0];++j)if(plan.selected[j]&&plan.nodes[j].writes)
                    for(unsigned k=0;k<GGML_MAX_SRC;++k)if(qwen_app::overlaps(plan.nodes[j].output,plan.nodes[i].external[k])){
                        std::snprintf(alias_writer,sizeof(alias_writer),"%s",g->nodes[j]->name);
                        std::snprintf(alias_reader,sizeof(alias_reader),"%s",g->nodes[i]->name);
                        std::snprintf(alias_input,sizeof(alias_input),"%s",g->nodes[i]->src[k]->name);break;}
        }return;}
    unsigned n_early=0,n_remaining=0;for(int i=0;i<g->n_nodes;++i)if(plan.selected[i])early[n_early++]=g->nodes[i];else remaining[n_remaining++]=g->nodes[i];
    if(!n_early||!n_remaining){++counts[2];return;}
    pending=g;original=g->nodes;original_count=g->n_nodes;original_uid=g->uid;owner=backend;retired=false;
    auto view=*g;view.nodes=early.data();view.n_nodes=int(n_early);view.uid=0;
    if(ggml_backend_graph_compute_async(backend,&view)!=GGML_STATUS_SUCCESS)throw std::runtime_error("Independent shared graph submission failed; retain graph");
    ++counts[8];counts[9]+=n_early;g->nodes=remaining.data();g->n_nodes=int(n_remaining);g->uid=0;
}
extern "C" void qwen_app_overlap_stream_boundary(ggml_backend_t backend){if(!pending)ggml_backend_synchronize(backend);else if(owner!=backend)throw std::runtime_error("Overlap cache backend differs");}
extern "C" void qwen_app_overlap_before_scatter(){if(pending&&!retired){ggml_backend_synchronize(owner);qwen_native_driver_checkpoint();retired=true;}}
extern "C" void qwen_app_overlap_after_split(ggml_backend_t backend,ggml_cgraph*g){
    if(!pending)return;if(g!=pending||backend!=owner)throw std::runtime_error("Overlap split changed before completion");
    ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();retired=true;
    g->nodes=original;g->n_nodes=original_count;g->uid=original_uid;pending=nullptr;original=nullptr;owner=nullptr;
}

extern "C" bool qwen_app_overlap_graph_can_reuse(){const bool reuse=used_graph_epoch==graph_epoch;if(!reuse)++graph_counts[3];return reuse;}
extern "C" void qwen_app_overlap_graph_set(ggml_tensor*t,int layer){
    if(!enabled)return;++graph_counts[0];if(!t||declared_shared||declared_layer!=-1)throw std::runtime_error("One declared shared graph branch required");declared_shared=t;declared_layer=layer;
}
extern "C" ggml_tensor*qwen_app_overlap_graph_take(int layer){
    if(!enabled)return nullptr;++graph_counts[1];if(!declared_shared||declared_layer!=layer)throw std::runtime_error("Declared shared graph layer differs");auto*t=declared_shared;declared_shared=nullptr;declared_layer=-1;return t;
}
extern "C" void qwen_app_overlap_graph_cleared(){if(enabled)++graph_counts[2];if(declared_shared||declared_layer!=-1)throw std::runtime_error("Shared graph declaration did not reach the cache split");}
extern "C" void qwen_app_overlap_graph_stats(std::uint64_t*out){std::copy(graph_counts.begin(),graph_counts.end(),out);}
extern "C" const char*qwen_app_overlap_alias_name(unsigned which){return which==0?alias_writer:(which==1?alias_reader:alias_input);}
