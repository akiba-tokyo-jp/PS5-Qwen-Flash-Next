// SPDX-License-Identifier: MIT
// Execute the actual model matvec SPIR-V with its original descriptor/push ABI.
#include "model_shader_desktop_API.private.h"
#include "iq2_paired_down.h"
#include <array>
Json model_case(API&a,VkPipeline pipeline,VkPipelineLayout layout,VkDescriptorSetLayout descriptors,
                const Json&c,bool indexed,bool half_input){
    auto weights=read(c.at("weights").at("path"));const auto inputs=read(c.at("inputs").at("path"));
    const auto ids=read(c.at("ids").at("path")),expected=read(c.at("expected").at("path"));
    const unsigned selected=c.at("selected"),values=selected*2560u;
    need(c.at("width")==1&&selected==2&&weights.size()==4608000&&inputs.size()==selected*640*4&&
         ids.size()==selected*4&&expected.size()==values*8,"Exact original width-one component operands required");
    std::vector<std::uint32_t>indices(selected);std::memcpy(indices.data(),ids.data(),ids.size());
    std::vector<float>input(selected*640);std::memcpy(input.data(),inputs.data(),inputs.size());
    std::vector<std::uint16_t>half(input.size());
    if(half_input)for(unsigned i=0;i<input.size();++i){const auto rounded=static_cast<_Float16>(input[i]);
        std::memcpy(half.data()+i,&rounded,2);input[i]=float(rounded);}
    auto packed=weights;
    if(!indexed){packed.resize(selected*460800u);for(unsigned i=0;i<selected;++i){need(indices[i]<10,"Bounded original Expert required");
        std::memcpy(packed.data()+i*460800u,weights.data()+indices[i]*460800u,460800u);}}
    const float zero=0;std::vector<float>output(values+128,42.125f);
    std::vector<Buffer>buffers{allocate(a,packed.size(),packed.data()),
        allocate(a,half_input?half.size()*2:inputs.size(),half_input?static_cast<const void*>(half.data()):inputs.data()),
        allocate(a,output.size()*4,output.data()),allocate(a,4,&zero),allocate(a,4,&zero),allocate(a,ids.size(),ids.data())};
    VkDescriptorPoolSize size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,6};VkDescriptorPoolCreateInfo pool_info{};
    pool_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;pool_info.maxSets=1;pool_info.poolSizeCount=1;pool_info.pPoolSizes=&size;
    VkDescriptorPool pool{};ok(a.vkCreateDescriptorPool(a.device,&pool_info,nullptr,&pool),"Model descriptor pool failed");
    VkDescriptorSetAllocateInfo allocate_set{};allocate_set.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    allocate_set.descriptorPool=pool;allocate_set.descriptorSetCount=1;allocate_set.pSetLayouts=&descriptors;
    VkDescriptorSet set{};ok(a.vkAllocateDescriptorSets(a.device,&allocate_set,&set),"Model descriptor set failed");
    VkDescriptorBufferInfo bi[6]{};VkWriteDescriptorSet writes[6]{};
    for(unsigned i=0;i<6;++i){bi[i]={buffers[i].buffer,i==2?256u:0u,buffers[i].bytes-(i==2?256u:0u)};
        writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=set;writes[i].dstBinding=i;
        writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[i].pBufferInfo=&bi[i];}
    a.vkUpdateDescriptorSets(a.device,6,writes,0,nullptr);
    std::array<std::uint32_t,13>push{640,640,640,2560,1638400,640,2560,0,0,selected,selected,1,1};
    unsigned push_bytes=52;if(indexed){push={640,640,640,2560,1638400,selected*640,selected*2560,0,selected,selected,0,selected,0};push_bytes=48;}
    VkCommandPoolCreateInfo cp{};cp.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;cp.queueFamilyIndex=a.family;
    VkCommandPool commands{};ok(a.vkCreateCommandPool(a.device,&cp,nullptr,&commands),"Model command pool failed");
    VkCommandBufferAllocateInfo ca{};ca.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;ca.commandPool=commands;
    ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;VkCommandBuffer command{};
    ok(a.vkAllocateCommandBuffers(a.device,&ca,&command),"Model command allocation failed");
    VkCommandBufferBeginInfo begin{};begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    ok(a.vkBeginCommandBuffer(command,&begin),"Model command begin failed");
    VkMemoryBarrier before{};before.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;
    before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
    a.vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
    a.vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
    a.vkCmdPushConstants(command,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,push_bytes,push.data());
    for(unsigned row:{0u,1248u,2496u})a.vkCmdDispatchBase(command,row,0,0,64,selected,1);
    VkMemoryBarrier after{};after.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;
    after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);
    ok(a.vkEndCommandBuffer(command),"Model command end failed");VkFenceCreateInfo fi{};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    VkFence fence{};ok(a.vkCreateFence(a.device,&fi,nullptr,&fence),"Model fence failed");VkSubmitInfo submit{};
    submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.commandBufferCount=1;submit.pCommandBuffers=&command;
    ok(a.vkQueueSubmit(a.queue,1,&submit,fence),"Model submit failed");
    if(a.vkWaitForFences(a.device,1,&fence,VK_TRUE,30000000000ull)!=VK_SUCCESS){
        std::cerr<<"Software model-shader completion unknown; retain owners, no resubmission\n"<<std::flush;for(;;)Sleep(1000);}
    a.vkDestroyFence(a.device,fence,nullptr);std::memcpy(output.data(),buffers[2].mapped,output.size()*4);
    bool canaries=true;unsigned mismatches=0,compared=0;double maximum=0;
    for(unsigned i=0;i<output.size();++i){const bool inside=i>=64&&i<64+values;const unsigned logical=inside?i-64:0,row=logical%2560;
        const bool touched=inside&&(row<64||(row>=1248&&row<1312)||row>=2496);
        if(!touched){canaries=canaries&&output[i]==42.125f;continue;}
        double reference=0;
        if(!half_input)std::memcpy(&reference,expected.data()+logical*8,8);
        else{const unsigned expert=logical/2560;const auto*carrier=weights.data()+indices[expert]*460800u;
            std::uint64_t grid[256];std::uint8_t signs[128];std::memcpy(grid,carrier+422464,2048);
            for(unsigned s=0;s<128;++s)signs[s]=std::uint8_t(qwen_app::PairedIQ2Down::u32(carrier+424512+s*4));
            for(unsigned col=0;col<640;++col)reference+=double(qwen_app::PairedIQ2Down::decode(carrier+64,row,col,grid,signs))*input[expert*640+col];}
        const double error=std::abs(double(output[i])-reference);maximum=std::max(maximum,error);++compared;
        if(!std::isfinite(output[i])||error>1e-5+2e-4*std::abs(reference))++mismatches;
    }
    a.vkDestroyCommandPool(a.device,commands,nullptr);a.vkDestroyDescriptorPool(a.device,pool,nullptr);
    for(auto&buffer:buffers)release(a,buffer);
    return {{"layer",c.at("layer")},{"half_input",half_input},{"indexed",indexed},{"compared_values",compared},
        {"distinct_row_tiles",3},{"mismatches",mismatches},{"maximum_absolute_F64_error",maximum},
        {"canaries_exact",canaries},{"positive_fence",true},{"all_case_resources_retired",true},
        {"passed",canaries&&!mismatches}};
}
int main(int argc,char**argv){try{
    need(argc==3,"Manifest and output required");const auto raw=read(argv[1]);const auto manifest=Json::parse(raw);
    API a(true);
    const auto loader=GetModuleHandleA("vulkan-1.dll");need(loader,"The existing Vulkan loader is required");
    const auto get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(GetProcAddress(loader,"vkGetInstanceProcAddr"));
    const auto properties2=reinterpret_cast<PFN_vkGetPhysicalDeviceProperties2>(get(a.instance,"vkGetPhysicalDeviceProperties2"));
    need(properties2,"Actual subgroup properties are required");
    VkPhysicalDeviceSubgroupProperties subgroup{};subgroup.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_PROPERTIES;
    VkPhysicalDeviceProperties2 properties{};properties.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;properties.pNext=&subgroup;
    properties2(a.physical,&properties);
    need(subgroup.subgroupSize&&!(subgroup.subgroupSize&(subgroup.subgroupSize-1))&&
        (subgroup.supportedOperations&VK_SUBGROUP_FEATURE_ARITHMETIC_BIT),"The actual arithmetic subgroup is required");
    Json result={{"completed",false},{"software_SPIRV_reference",true},{"physical_GPU_execution",false},
        {"actual_subgroup_size",subgroup.subgroupSize},
        {"desktop_GPU",a.properties.deviceName},{"cases",Json::array()},{"PS5_operations",0}};
    VkDescriptorSetLayoutBinding bindings[6]{};for(unsigned i=0;i<6;++i){bindings[i].binding=i;bindings[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[i].descriptorCount=1;bindings[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
    VkDescriptorSetLayoutCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;di.bindingCount=6;di.pBindings=bindings;
    VkDescriptorSetLayout descriptors{};ok(a.vkCreateDescriptorSetLayout(a.device,&di,nullptr,&descriptors),"Model descriptor layout failed");
    VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT,0,52};VkPipelineLayoutCreateInfo li{};li.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    li.setLayoutCount=1;li.pSetLayouts=&descriptors;li.pushConstantRangeCount=1;li.pPushConstantRanges=&range;
    VkPipelineLayout layout{};ok(a.vkCreatePipelineLayout(a.device,&li,nullptr,&layout),"Model pipeline layout failed");
    for(const auto&shader:manifest.at("shaders")){
        const auto binary=read(shader.at("artifact").at("path"));std::vector<std::uint32_t>words(binary.size()/4);std::memcpy(words.data(),binary.data(),binary.size());
        VkShaderModuleCreateInfo si{};si.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;si.codeSize=binary.size();si.pCode=words.data();
        VkShaderModule module{};ok(a.vkCreateShaderModule(a.device,&si,nullptr,&module),"Model shader module failed");
        VkSpecializationMapEntry entries[]={{0,0,4},{1,4,4},{2,8,4}};
        const bool no_shared=shader.at("name").get<std::string>().find("_no_shmem")!=std::string::npos;
        std::uint32_t constants[]={no_shared?subgroup.subgroupSize:32u,1,1};
        VkSpecializationInfo special{3,entries,sizeof(constants),constants};VkComputePipelineCreateInfo pi{};
        pi.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;pi.flags=VK_PIPELINE_CREATE_DISPATCH_BASE_BIT;pi.layout=layout;
        pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;
        pi.stage.module=module;pi.stage.pName="main";pi.stage.pSpecializationInfo=&special;
        VkPipeline pipeline{};ok(a.vkCreateComputePipelines(a.device,VK_NULL_HANDLE,1,&pi,nullptr,&pipeline),"Model compute pipeline failed");
        for(const auto&c:manifest.at("cases")){auto row=model_case(a,pipeline,layout,descriptors,c,shader.at("indexed"),shader.at("half_input"));
            row["shader"]=shader.at("name");result["cases"].push_back(row);save(argv[2],result);need(row.at("passed"),"Actual model shader differs from the independent reference");}
        a.vkDestroyPipeline(a.device,pipeline,nullptr);a.vkDestroyShaderModule(a.device,module,nullptr);
    }
    a.vkDestroyPipelineLayout(a.device,layout,nullptr);a.vkDestroyDescriptorSetLayout(a.device,descriptors,nullptr);a.close();
    result["completed"]=true;result["all_GPU_resources_positively_retired"]=true;save(argv[2],result);return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
