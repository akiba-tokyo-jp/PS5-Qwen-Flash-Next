// SPDX-License-Identifier: MIT
// The common desktop Vulkan ownership helpers are supplied by the build tool.
std::vector<int> expected_order(const std::vector<float>&scores,unsigned columns,unsigned rows,bool descending){
    std::vector<int> answer(columns*rows);
    for(unsigned row=0;row<rows;++row){
        std::vector<int> indices(columns);for(unsigned i=0;i<columns;++i)indices[i]=int(i);
        for(unsigned k=2;k<=columns;k*=2)for(unsigned j=k/2;j;j/=2)for(unsigned i=0;i<columns;++i){
            unsigned other=i^j;if(other<=i)continue;
            unsigned a=(i&k)==0?i:other,b=(i&k)==0?other:i;
            if(scores[row*columns+indices[a]]>scores[row*columns+indices[b]])std::swap(indices[a],indices[b]);
        }
        for(unsigned i=0;i<columns;++i)answer[row*columns+(descending?columns-i-1:i)]=indices[i];
    }return answer;
}
Json rank_case(API&a,VkShaderModule module,VkPipelineLayout layout,VkDescriptorSetLayout descriptors,
               unsigned columns,unsigned rows,unsigned pattern,bool descending,bool fused,const std::string&path,Json&progress){
    const unsigned values=columns*rows,guard=64;const std::uint32_t sentinel=0x4b2b2b2b;
    std::vector<float> raw(values),coefficient(values),weighted(values);
    for(unsigned r=0;r<rows;++r)for(unsigned i=0;i<columns;++i){
        unsigned at=r*columns+i;
        raw[at]=pattern==0?float(int((i*73+r*37)%997)-499)/256.f:
                pattern==1?float(int(i%17)-8):pattern==2?(i%2?0.f:-0.f):float(i<24?100:int(i%97));
        coefficient[at]=pattern==1||pattern==2?1.f:(i%3==0?1.03125f:i%3==1?.999875f:1.f);
        weighted[at]=columns==512&&rows<=2?raw[at]*coefficient[at]:raw[at];
    }
    std::vector<std::uint32_t> arena(values+2*guard,sentinel);
    std::memcpy(arena.data()+guard,coefficient.data(),values*4);
    auto input=allocate(a,values*4,fused?raw.data():weighted.data());auto output=allocate(a,arena.size()*4,arena.data());
    VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,3};VkDescriptorPoolCreateInfo pool_info{};
    pool_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;pool_info.maxSets=1;pool_info.poolSizeCount=1;pool_info.pPoolSizes=&pool_size;
    VkDescriptorPool pool{};ok(a.vkCreateDescriptorPool(a.device,&pool_info,nullptr,&pool),"Rank descriptor pool failed");
    VkDescriptorSetAllocateInfo alloc{};alloc.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;alloc.descriptorPool=pool;alloc.descriptorSetCount=1;alloc.pSetLayouts=&descriptors;
    VkDescriptorSet set{};ok(a.vkAllocateDescriptorSets(a.device,&alloc,&set),"Rank descriptors failed");
    VkDescriptorBufferInfo ranges[3]={{input.buffer,0,input.bytes},{output.buffer,guard*4,values*4},{output.buffer,guard*4,values*4}};
    VkWriteDescriptorSet writes[3]{};for(unsigned i=0;i<3;++i){writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=set;writes[i].dstBinding=i;
        writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[i].pBufferInfo=&ranges[i];}
    a.vkUpdateDescriptorSets(a.device,3,writes,0,nullptr);
    unsigned log2=0;while((1u<<log2)<columns)++log2;
    const unsigned specialization[2]={columns,log2};VkSpecializationMapEntry entries[2]={{0,0,4},{1,4,4}};
    VkSpecializationInfo spec{2,entries,sizeof(specialization),specialization};
    VkComputePipelineCreateInfo pi{};pi.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;pi.layout=layout;
    pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pi.stage.module=module;pi.stage.pName="main";pi.stage.pSpecializationInfo=&spec;
    VkPipeline pipeline{};ok(a.vkCreateComputePipelines(a.device,VK_NULL_HANDLE,1,&pi,nullptr,&pipeline),"Rank pipeline failed");
    VkCommandPoolCreateInfo ci{};ci.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;ci.flags=VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;ci.queueFamilyIndex=a.family;
    VkCommandPool commands{};ok(a.vkCreateCommandPool(a.device,&ci,nullptr,&commands),"Rank command pool failed");
    VkCommandBufferAllocateInfo ai{};ai.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;ai.commandPool=commands;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
    VkCommandBuffer command{};ok(a.vkAllocateCommandBuffers(a.device,&ai,&command),"Rank command allocation failed");
    VkCommandBufferBeginInfo bi{};bi.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    ok(a.vkBeginCommandBuffer(command,&bi),"Rank command begin failed");
    VkMemoryBarrier before{};before.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
    a.vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);a.vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
    const unsigned push[9]={columns,columns,log2,rows,descending?1u:0u,0,log2,0,log2};
    a.vkCmdPushConstants(command,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(push),push);a.vkCmdDispatch(command,1,rows,1);
    VkMemoryBarrier after{};after.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);
    ok(a.vkEndCommandBuffer(command),"Rank command end failed");
    VkFenceCreateInfo fi{};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;VkFence fence{};ok(a.vkCreateFence(a.device,&fi,nullptr,&fence),"Rank fence failed");
    VkSubmitInfo submit{};submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.commandBufferCount=1;submit.pCommandBuffers=&command;
    auto status=a.vkQueueSubmit(a.queue,1,&submit,fence);if(status==VK_SUCCESS)status=a.vkWaitForFences(a.device,1,&fence,VK_TRUE,30000000000ull);
    if(status!=VK_SUCCESS){progress["unknown_completion"]=true;progress["owner_retained"]=true;save(path,progress);for(;;)Sleep(1000);}
    const auto expected=expected_order(weighted,columns,rows,descending);const auto actual=static_cast<const int*>(output.mapped)+guard;
    const bool exact=std::equal(expected.begin(),expected.end(),actual);
    auto bits=static_cast<const std::uint32_t*>(output.mapped);
    bool canaries=true;for(unsigned i=0;i<guard;++i)canaries=canaries&&bits[i]==sentinel&&bits[guard+values+i]==sentinel;
    const bool input_exact=std::memcmp(input.mapped,fused?raw.data():weighted.data(),values*4)==0;
    a.vkDestroyFence(a.device,fence,nullptr);a.vkDestroyCommandPool(a.device,commands,nullptr);a.vkDestroyPipeline(a.device,pipeline,nullptr);
    a.vkDestroyDescriptorPool(a.device,pool,nullptr);release(a,input);release(a,output);
    return {{"columns",columns},{"rows",rows},{"pattern",pattern},{"descending",descending},{"fused",fused},
        {"all_ordered_indices_exact",exact},{"canaries_exact",canaries},{"input_exact",input_exact},{"positive_fence",true},{"case_resources_retired",true}};
}
int main(int argc,char**argv){try{
    need(argc==4,"Original and fused shader paths plus result required");API a(true);
    VkDescriptorSetLayoutBinding bindings[3]{};for(unsigned i=0;i<3;++i)bindings[i]={i,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
    VkDescriptorSetLayoutCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;di.bindingCount=3;di.pBindings=bindings;
    VkDescriptorSetLayout descriptors{};ok(a.vkCreateDescriptorSetLayout(a.device,&di,nullptr,&descriptors),"Rank descriptor layout failed");
    VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT,0,36};VkPipelineLayoutCreateInfo li{};li.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    li.setLayoutCount=1;li.pSetLayouts=&descriptors;li.pushConstantRangeCount=1;li.pPushConstantRanges=&range;
    VkPipelineLayout layout{};ok(a.vkCreatePipelineLayout(a.device,&li,nullptr,&layout),"Rank pipeline layout failed");
    Json progress={{"completed",false},{"software_backend",a.properties.deviceName},{"cases",Json::array()},{"PS5_operations",0},{"unknown_completion",false},
        {"maximum_physical_lanes",a.properties.limits.maxComputeWorkGroupInvocations}};
    for(unsigned variant=0;variant<2;++variant){
        const auto binary=read(argv[1+variant]);std::vector<std::uint32_t> words(binary.size()/4);need(binary.size()%4==0,"Aligned SPIRV required");std::memcpy(words.data(),binary.data(),binary.size());
        VkShaderModuleCreateInfo si{};si.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;si.codeSize=binary.size();si.pCode=words.data();VkShaderModule module{};
        ok(a.vkCreateShaderModule(a.device,&si,nullptr,&module),"Rank shader module failed");
        const auto geometries=variant?std::vector<std::pair<unsigned,unsigned>>{{512,1},{512,2},{512,30},{32,1},{128,2},{1024,1}}:
            std::vector<std::pair<unsigned,unsigned>>{{32,1},{128,2}};
        for(auto geometry:geometries)
            for(unsigned pattern=0;pattern<4;++pattern)for(unsigned order=0;order<2;++order){
                auto row=rank_case(a,module,layout,descriptors,geometry.first,geometry.second,pattern,order,variant,argv[3],progress);
                progress["cases"].push_back(row);save(argv[3],progress);
                need(row["all_ordered_indices_exact"]&&row["canaries_exact"]&&row["input_exact"],"Original bitonic order or alias canary mismatch");
            }
        a.vkDestroyShaderModule(a.device,module,nullptr);
    }
    a.vkDestroyPipelineLayout(a.device,layout,nullptr);a.vkDestroyDescriptorSetLayout(a.device,descriptors,nullptr);a.close();
    progress["completed"]=true;progress["all_resources_positively_retired"]=true;progress["positive_fences"]=progress["cases"].size();save(argv[3],progress);
    std::cout<<"All64 original/fused full-sort cases passed\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
