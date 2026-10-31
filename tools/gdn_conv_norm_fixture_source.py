# SPDX-License-Identifier: MIT
"""Construct a full-shape F64 oracle for convolution, normalization and GDN state."""
from build_speculative_batch_probe import once
CONV=r'''
    const unsigned channels=width*(2*qheads+heads);
    auto*history=tensor(tokens+3,channels,sequences,1);auto*weights=tensor(4,channels,1,1);
    auto*convolved=ggml_ssm_conv(f.context,history,weights);auto*activated=ggml_silu(f.context,convolved);
    auto view=[&](unsigned h,size_t offset){return ggml_view_4d(f.context,activated,width,h,tokens,sequences,width*4,channels*4,channels*tokens*4,offset);};
    const float epsilon=1e-6f,normal_scale=1.0f/std::sqrt(float(width));
    auto*q=ggml_scale(f.context,ggml_rms_norm(f.context,view(qheads,0),epsilon/width),normal_scale);
    auto*k=ggml_scale(f.context,ggml_rms_norm(f.context,view(qheads,width*qheads*4),epsilon/width),normal_scale);
    auto*v=view(heads,width*qheads*8);
    f.eligible=tokens==1&&sequences==1&&heads==48&&qheads==16;
    f.raw_history=history;f.raw_weights=weights;
'''
VALUES=r'''
    auto hs=values(history,11+salt*23,37),ws=values(weights,3+salt*19,113);
    for(unsigned c=0;c<2*width*qheads;++c)for(unsigned j=0;j<4;++j){if(salt==1)ws[c*4+j]=0;else if(salt==2)ws[c*4+j]*=1e-6f;}
    f.original_history=hs;f.original_weights=ws;
    std::vector<double>act(size_t(tokens)*channels),qs(size_t(tokens)*qheads*width),ks(qs.size()),vs(size_t(tokens)*heads*width);
    for(unsigned t=0;t<tokens;++t)for(unsigned c=0;c<channels;++c){double sum=0;for(unsigned j=0;j<4;++j)sum+=double(hs[c*(tokens+3)+t+j])*ws[c*4+j];act[t*channels+c]=sum/(1.0+std::exp(-sum));}
    for(unsigned t=0;t<tokens;++t)for(unsigned h=0;h<qheads;++h){double sq=0,sk=0;
        for(unsigned j=0;j<width;++j){const auto q=act[t*channels+h*width+j],k=act[t*channels+(qheads+h)*width+j];sq+=q*q;sk+=k*k;}
        const double rq=1/std::sqrt(sq/width+double(epsilon/width)),rk=1/std::sqrt(sk/width+double(epsilon/width));
        for(unsigned j=0;j<width;++j){qs[(t*qheads+h)*width+j]=act[t*channels+h*width+j]*rq*normal_scale;ks[(t*qheads+h)*width+j]=act[t*channels+(qheads+h)*width+j]*rk*normal_scale;}
    }
    for(unsigned t=0;t<tokens;++t)for(unsigned j=0;j<width*heads;++j)vs[t*width*heads+j]=act[t*channels+2*width*qheads+j];
'''
def transform(text):
 text=text.replace('qwen_app_gdn_trial_','qwen_app_conv_norm_trial_').replace('namespace gdn_fixture','namespace gdn_conv_norm_fixture').replace('GDN_columns','GDN_conv_norm')
 text=once(text,'    double maximum=0;','    bool eligible=true;ggml_tensor*raw_history=nullptr,*raw_weights=nullptr;std::vector<float>original_history,original_weights;\n    double maximum=0;')
 text=once(text,'unsigned snapshots,bool vector_gate,void(*checkpoint)(),','unsigned snapshots,bool vector_gate,unsigned salt,void(*checkpoint)(),')
 text=once(text,'    auto*q=tensor(width,qheads,tokens,1);auto*k=tensor(width,qheads,tokens,1);\n    auto*v=tensor(width,heads,tokens,sequences);',CONV)
 text=once(text,'    auto qs=values(q,1,97),ks=values(k,2,113),vs=values(v,3,67);',VALUES)
 text=once(text,'    upload(q,qs);upload(k,ks);upload(v,vs);upload(g,gs);upload(beta,bs);upload(state,ss);',
     '    upload(history,hs);upload(weights,ws);upload(g,gs);upload(beta,bs);upload(state,ss);')
 text=once(text,'        std::array<float,128> canary{};',
     '        for(auto pair:{std::make_pair(raw_history,&original_history),std::make_pair(raw_weights,&original_weights)}){std::vector<float>observed(pair.second->size());ggml_backend_tensor_get(pair.first,observed.data(),0,observed.size()*4);if(std::memcmp(observed.data(),pair.second->data(),observed.size()*4))throw std::runtime_error("Convolution source history or original weight bytes changed");}\n        std::array<float,128> canary{};')
 text=once(text,'        if(!selected)throw std::runtime_error("GDN candidate pipeline did not execute");',
     '        if((eligible&&!selected)||(!eligible&&selected))throw std::runtime_error("Convolution normalization selected-path/fallback coverage differs");')
 text=once(text,'{"candidate_pipeline_selections",selected}', '{"candidate_pipeline_selections",selected},{"eligible_fused_shape",eligible},{"original_source_history_and_weights_exact",true}')
 text=once(text,'        p.mem_size=32*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(32,false);',
     '        p.mem_size=96*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(64,false);')
 text=once(text,'for(auto&g:graphs)g=ggml_new_graph_custom(context,32,false);','for(auto&g:graphs)g=ggml_new_graph_custom(context,64,false);')
 old='''    for(bool vector_gate:{false,true})for(unsigned tokens:{1u,32u})for(unsigned snapshots:{1u,2u})
        cases.push_back(one(vector_gate?4:48,vector_gate?2:16,tokens,vector_gate?2:1,
                            snapshots,vector_gate,checkpoint,stage,admit,deadline,graphs));
    if(graphs!=288)throw std::runtime_error("GDN fixture omitted a declared graph");'''
 new='''    for(unsigned salt=0;salt<4;++salt)cases.push_back(one(48,16,salt==3?2:1,1,salt==3?3:2,false,salt,checkpoint,stage,admit,deadline,graphs));
    if(graphs!=144)throw std::runtime_error("Convolution normalization fixture omitted a declared graph");'''
 text=once(text,old,new)
 # Separate backend timing from the retained positive completion observation.
 text=once(text,'    double maximum=0;','    double maximum=0,last_backend_us=0,last_checkpoint_us=0;')
 text=once(text,'        ggml_backend_synchronize(backend);checkpoint();++executions;\n        const auto elapsed=std::chrono::duration<double,std::micro>(Clock::now()-start).count();',
     '        ggml_backend_synchronize(backend);const auto computed=Clock::now();checkpoint();const auto checked=Clock::now();++executions;\n        last_backend_us=std::chrono::duration<double,std::micro>(computed-start).count();last_checkpoint_us=std::chrono::duration<double,std::micro>(checked-computed).count();\n        const auto elapsed=std::chrono::duration<double,std::micro>(checked-start).count();')
 text=once(text,'            std::array<double,8> times{};for(auto&time:times)time=compute(arm);check(arm);',
     '            std::array<double,8> times{},backend_times{},completion_times{};for(unsigned sample=0;sample<8;++sample){times[sample]=compute(arm);backend_times[sample]=last_backend_us;completion_times[sample]=last_checkpoint_us;}check(arm);')
 text=once(text,'{{"candidate",arm==1},{"samples_us",times},',
     '{{"candidate",arm==1},{"samples_us",times},{"backend_samples_us",backend_times},{"completion_samples_us",completion_times},')
 return '#include <cstring>\n#include <utility>\n'+text
