// SPDX-License-Identifier: MIT
static bool qwen_gate_up_match(const ggml_cgraph*g,int first){
    if(!qwen_gate_up_enabled.load()||first+2>=g->n_nodes)return false;
    auto*a=g->nodes[first];auto*b=g->nodes[first+1];auto*y=g->nodes[first+2];
    if(a->op!=GGML_OP_MUL_MAT_ID||b->op!=GGML_OP_MUL_MAT_ID||y->op!=GGML_OP_GLU||ggml_get_glu_op(y)!=GGML_GLU_OP_SWIGLU||
       a->src[1]!=b->src[1]||a->src[2]!=b->src[2]||!((y->src[0]==a&&y->src[1]==b)||(y->src[0]==b&&y->src[1]==a)))return false;
    const auto*w=a->src[0];const auto*v=b->src[0];const auto*x=a->src[1];const auto*ids=a->src[2];
    if(!w||!v||!x||!ids||w->type!=GGML_TYPE_Q2_K||v->type!=GGML_TYPE_Q2_K||!ggml_are_same_shape(w,v)||
       w->ne[0]!=2560||w->ne[1]!=640||w->ne[2]<3||w->ne[2]>3073||w->ne[3]!=1||!ggml_is_contiguous(w)||!ggml_is_contiguous(v)||
       x->type!=GGML_TYPE_F32||x->ne[0]!=2560||x->ne[1]!=1||(x->ne[2]!=1&&x->ne[2]!=2)||x->ne[3]!=1||!ggml_is_contiguous(x)||
       ids->type!=GGML_TYPE_I32||ids->ne[0]!=6||ids->ne[1]!=x->ne[2]||ids->ne[2]!=1||ids->ne[3]!=1||!ggml_is_contiguous(ids)||
       y->type!=GGML_TYPE_F32||y->ne[0]!=640||y->ne[1]!=6||y->ne[2]!=x->ne[2]||y->ne[3]!=1||!ggml_is_contiguous(y))return false;
    return ggml_can_fuse_subgraph(g,first,{GGML_OP_MUL_MAT_ID,GGML_OP_MUL_MAT_ID,GGML_OP_GLU},{first+2});
}
static void qwen_gate_up_dispatch(ggml_backend_vk_context*ctx,vk_context&subctx,const ggml_cgraph*g,int first){
    auto*y=g->nodes[first+2];auto*gate=y->src[0]->src[0];auto*up=y->src[1]->src[0];auto*x=y->src[0]->src[1];auto*ids=y->src[0]->src[2];
    auto*program=qwen_gate_up_find(ctx->device);GGML_ASSERT(program&&program->pipeline&&qwen_gate_up_match(g,first));
    QwenGateUpPC pc{uint32_t(get_misalign_bytes(ctx,gate)/4),uint32_t(get_misalign_bytes(ctx,up)/4),uint32_t(get_misalign_bytes(ctx,x)/4),uint32_t(get_misalign_bytes(ctx,ids)/4),uint32_t(get_misalign_bytes(ctx,y)/4),uint32_t(gate->nb[2]/4),uint32_t(up->nb[2]/4),uint32_t(gate->nb[1]/4),uint32_t(up->nb[1]/4),uint32_t(x->nb[2]/4),uint32_t(ids->nb[1]/4),uint32_t(y->nb[2]/4),uint32_t(gate->ne[2]),6,uint32_t(x->ne[2])};
    ggml_pipeline_request_descriptor_sets(ctx,program->pipeline,1);
    ggml_vk_dispatch_pipeline(ctx,subctx,program->pipeline,{ggml_vk_tensor_subbuffer(ctx,gate,true),ggml_vk_tensor_subbuffer(ctx,up,true),ggml_vk_tensor_subbuffer(ctx,x,true),ggml_vk_tensor_subbuffer(ctx,ids,true),ggml_vk_tensor_subbuffer(ctx,y,true)},pc,{640*128,6,uint32_t(x->ne[2])});++qwen_gate_up_executions;
}
