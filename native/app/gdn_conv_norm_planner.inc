// SPDX-License-Identifier: MIT
// Use the same pre-allocation dependency API as upstream TOPK_MOE fusion.
// Preserve potential spans even while dispatch is disabled for a control arm;
// graph reuse must not lose either ordering or external-input lifetimes.
static bool qwen_conv_norm_preserve_plan(ggml_backend_vk_context*ctx,ggml_cgraph*graph,
    ggml_backend_graph_optimize_params*params,std::vector<ggml_tensor*>&order,
    std::vector<bool>&used,std::set<ggml_tensor*>&scheduled,int&first){
    ++qwen_conv_norm_planner_counts[0];
    if(graph->nodes[first]->op!=GGML_OP_SSM_CONV)return false;
    ++qwen_conv_norm_planner_counts[1];
    const auto match=qwen_conv_norm_match(ctx,graph,first,true);
    if(!match.extra)return false;
    ++qwen_conv_norm_planner_counts[2];
    for(int j=0;j<=match.extra;++j)if(used[first+j])return false;
    auto*last=graph->nodes[first+match.extra];std::set<ggml_tensor*>seen;
    for(int j=0;j<=match.extra;++j){auto*node=graph->nodes[first+j];
        for(unsigned s=0;s<GGML_MAX_SRC;++s)if(auto*src=node->src[s]){
            if(seen.insert(src).second){params->add_alloc_dep(params->user_data,src,last);++qwen_conv_norm_planner_counts[3];}
        }
        seen.insert(node);
    }
    for(int j=0;j<=match.extra;++j){auto*node=graph->nodes[first+j];order.push_back(node);scheduled.insert(node);used[first+j]=true;}
    while(first<graph->n_nodes&&used[first])++first;
    ++qwen_conv_norm_planner_counts[4];return true;
}
