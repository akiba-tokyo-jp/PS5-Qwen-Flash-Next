// SPDX-License-Identifier: MIT
struct QwenConvNormMatch {int extra=0,q=-1,k=-1;uint32_t writes=0;float epsilon=0,scale=0;};
static bool qwen_conv_norm_view(const ggml_tensor*t,const ggml_tensor*root,size_t offset){
    if(!t||t->type!=GGML_TYPE_F32||t->ne[0]!=128||t->ne[1]!=16||t->ne[2]!=1||t->ne[3]!=1||t->nb[0]!=4||t->nb[1]!=512)return false;
    size_t accumulated=0;unsigned steps=0;while(t->view_src){if(++steps>8||t->view_offs>SIZE_MAX-accumulated)return false;accumulated+=t->view_offs;t=t->view_src;}
    return t==root&&accumulated==offset;
}
static QwenConvNormMatch qwen_conv_norm_match(const ggml_backend_vk_context*ctx,const ggml_cgraph*graph,int first){
    QwenConvNormMatch out;
    if(!qwen_conv_norm_enabled.load(std::memory_order_relaxed)||first+7>=graph->n_nodes)return out;
    auto*conv=graph->nodes[first];auto*x=conv->src[0];auto*w=conv->src[1];auto*y=graph->nodes[first+1];
    if(conv->op!=GGML_OP_SSM_CONV||!x||!w||x->type!=GGML_TYPE_F32||w->type!=GGML_TYPE_F32||conv->type!=GGML_TYPE_F32||
       x->ne[0]!=4||x->ne[1]!=10240||x->ne[2]!=1||x->ne[3]!=1||x->nb[0]!=4||w->ne[0]!=4||w->ne[1]!=10240||
       w->ne[2]!=1||w->ne[3]!=1||w->nb[0]!=4||y->op!=GGML_OP_UNARY||ggml_get_unary_op(y)!=GGML_UNARY_OP_SILU||
       y->src[0]!=conv||y->type!=GGML_TYPE_F32||!ggml_is_contiguous(y)||ggml_nelements(y)!=10240)return out;
    auto*program=qwen_conv_norm_find(ctx->device);const auto&limits=ctx->device->properties.limits;
    if(!program||!program->pipeline||limits.maxComputeWorkGroupInvocations<128||limits.maxComputeWorkGroupSize[0]<128||
       limits.maxComputeSharedMemorySize<512||limits.maxPerStageDescriptorStorageBuffers<5||limits.maxPushConstantsSize<sizeof(QwenConvNormPC))return out;
    int rms[2]={-1,-1},scaled[2]={-1,-1};std::array<int,13>indices{},outputs{};std::array<ggml_op,13>ops{};
    int output_count=0;outputs[output_count++]=first+1;
    for(int j=0;j<13&&first+j<graph->n_nodes;++j){auto*node=graph->nodes[first+j];indices[j]=first+j;ops[j]=node->op;
        if(j<2)continue;
        if(ggml_op_is_empty(node->op)){outputs[output_count++]=first+j;}
        else if(node->op==GGML_OP_RMS_NORM){
            const int arm=qwen_conv_norm_view(node->src[0],y,0)?0:qwen_conv_norm_view(node->src[0],y,8192)?1:-1;
            if(arm<0||rms[arm]>=0||node->type!=GGML_TYPE_F32||!ggml_is_contiguous(node))return {};
            const float eps=ggml_get_op_params_f32(node,0);if(!std::isfinite(eps)||eps<=0)return {};
            if(rms[1-arm]>=0&&eps!=out.epsilon)return {};out.epsilon=eps;rms[arm]=first+j;
        }else if(node->op==GGML_OP_SCALE){
            const int arm=rms[0]>=0&&node->src[0]==graph->nodes[rms[0]]?0:rms[1]>=0&&node->src[0]==graph->nodes[rms[1]]?1:-1;
            if(arm<0||scaled[arm]>=0||node->type!=GGML_TYPE_F32||!ggml_is_contiguous(node)||!ggml_are_same_shape(node,node->src[0]))return {};
            const float scale=ggml_get_op_params_f32(node,0);
            if(!std::isfinite(scale)||scale!=1.0f/std::sqrt(128.0f)||ggml_get_op_params_f32(node,1)!=0)return {};
            if(scaled[1-arm]>=0&&scale!=out.scale)return {};out.scale=scale;scaled[arm]=first+j;outputs[output_count++]=first+j;
        }else return {};
        if(scaled[0]>=0&&scaled[1]>=0){
            if(!ggml_can_fuse_subgraph_ext(graph,indices.data(),j+1,ops.data(),outputs.data(),output_count))return {};
            out.extra=j;out.q=scaled[0];out.k=scaled[1];out.writes=(1u<<1)|(1u<<(out.q-first))|(1u<<(out.k-first));return out;
        }
    }return {};
}
static void qwen_conv_norm_dispatch(ggml_backend_vk_context*ctx,vk_context&subctx,const ggml_cgraph*graph,int first,const QwenConvNormMatch&m){
    auto*x=graph->nodes[first]->src[0];auto*w=graph->nodes[first]->src[1];auto*y=graph->nodes[first+1];auto*q=graph->nodes[m.q];auto*k=graph->nodes[m.k];
    auto*program=qwen_conv_norm_find(ctx->device);GGML_ASSERT(program&&program->pipeline&&ctx->num_additional_fused_ops==uint32_t(m.extra));
    QwenConvNormPC pc{uint32_t(get_misalign_bytes(ctx,x)/4),uint32_t(get_misalign_bytes(ctx,w)/4),uint32_t(get_misalign_bytes(ctx,y)/4),
        uint32_t(get_misalign_bytes(ctx,q)/4),uint32_t(get_misalign_bytes(ctx,k)/4),uint32_t(x->nb[1]/4),uint32_t(w->nb[1]/4),m.epsilon,m.scale};
    ggml_pipeline_request_descriptor_sets(ctx,program->pipeline,1);
    const auto xb=ggml_vk_tensor_subbuffer(ctx,x,true),wb=ggml_vk_tensor_subbuffer(ctx,w,true),yb=ggml_vk_tensor_subbuffer(ctx,y,true),
        qb=ggml_vk_tensor_subbuffer(ctx,q,true),kb=ggml_vk_tensor_subbuffer(ctx,k,true);
    ggml_vk_dispatch_pipeline(ctx,subctx,program->pipeline,{xb,wb,yb,qb,kb},pc,{10240,1,1});++qwen_conv_norm_executions;
}
