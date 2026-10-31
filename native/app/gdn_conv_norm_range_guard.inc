// SPDX-License-Identifier: MIT
// Protect every member during both generic pulling passes, as upstream QSA
// protects interior nodes. A start-only check cannot see roots already pulled.
static std::vector<bool>qwen_conv_norm_protected_ranges(ggml_backend_vk_context*ctx,ggml_cgraph*graph){
    std::vector<bool>protected_nodes(graph->n_nodes,false);static std::atomic<bool>noted{false};
    for(int first=0;first<graph->n_nodes;++first){
        if(graph->nodes[first]->op!=GGML_OP_SSM_CONV)continue;
        auto*conv=graph->nodes[first];auto*x=conv->src[0];auto*w=conv->src[1];
        if(x&&w&&x->ne[0]==4&&x->ne[1]==10240&&!noted.exchange(true)){
            std::string note="Qwen_GDN_planner_metadata channels="+std::to_string(x->ne[1])+" input_type="+std::to_string(x->type)+" weight_type="+std::to_string(w->type)+" input_sequences="+std::to_string(x->ne[2])+" window=";
            for(int j=0;j<13&&first+j<graph->n_nodes;++j){auto*n=graph->nodes[first+j];note+=ggml_op_name(n->op);note+='[';
                for(unsigned d=0;d<4;++d)note+=std::to_string(n->ne[d])+',';note+="];";}
            ggml_app_phase(note.c_str());
        }
        const auto match=qwen_conv_norm_match(ctx,graph,first,true);
        if(!match.extra)continue;
        for(int j=0;j<=match.extra;++j)protected_nodes[first+j]=true;
    }
    return protected_nodes;
}
