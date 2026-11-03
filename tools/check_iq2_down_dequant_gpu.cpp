// SPDX-License-Identifier: MIT
// Verify packed-half output for every value in complete, nonzero carrier views.
#include "model_shader_desktop_API.private.h"
#include "iq2_paired_down.h"
#include <array>

static Json check(API&a,VkPipeline pipeline,VkPipelineLayout layout,VkDescriptorSetLayout descriptors,const Json&c){
    const auto weights=read(c.at("weights").at("path"));
    constexpr std::size_t prefix=12288000,tail=16384,values=16384000,guard=128;
    need(weights.size()==4608000&&a.properties.limits.maxStorageBufferRange>=2*values,"Complete ten-plane extent required");
    std::vector<unsigned char>input(prefix+weights.size()+tail,0xa5);
    std::memcpy(input.data()+prefix,weights.data(),weights.size());
    std::vector<std::uint16_t>output(values+2*guard,0x5a5a);
    std::vector<Buffer>buffers{allocate(a,input.size(),input.data()),allocate(a,output.size()*2,output.data())};
    VkDescriptorPoolSize size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,2};VkDescriptorPoolCreateInfo pi{};
    pi.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;pi.maxSets=1;pi.poolSizeCount=1;pi.pPoolSizes=&size;
    VkDescriptorPool pool{};ok(a.vkCreateDescriptorPool(a.device,&pi,nullptr,&pool),"Dequant descriptor pool failed");
    VkDescriptorSetAllocateInfo ai{};ai.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    ai.descriptorPool=pool;ai.descriptorSetCount=1;ai.pSetLayouts=&descriptors;
    VkDescriptorSet set{};ok(a.vkAllocateDescriptorSets(a.device,&ai,&set),"Dequant descriptor set failed");
    VkDescriptorBufferInfo bi[]={{buffers[0].buffer,prefix,weights.size()},{buffers[1].buffer,2*guard,2*values}};
    VkWriteDescriptorSet writes[2]{};
    for(unsigned i=0;i<2;++i){writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=set;
        writes[i].dstBinding=i;writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[i].pBufferInfo=&bi[i];}
    a.vkUpdateDescriptorSets(a.device,2,writes,0,nullptr);
    VkCommandPoolCreateInfo cp{};cp.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;cp.queueFamilyIndex=a.family;
    VkCommandPool commands{};ok(a.vkCreateCommandPool(a.device,&cp,nullptr,&commands),"Dequant command pool failed");
    VkCommandBufferAllocateInfo ca{};ca.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;ca.commandPool=commands;
    ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;VkCommandBuffer command{};
    ok(a.vkAllocateCommandBuffers(a.device,&ca,&command),"Dequant command allocation failed");
    VkCommandBufferBeginInfo begin{};begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    ok(a.vkBeginCommandBuffer(command,&begin),"Dequant command begin failed");
    VkMemoryBarrier before{};before.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;
    before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
    a.vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
    a.vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
    const std::array<std::uint32_t,5>push{2560,640,640,640,values};
    a.vkCmdPushConstants(command,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(push),push.data());
    a.vkCmdDispatchBase(command,0,0,0,(values+1023)/1024,1,1);
    VkMemoryBarrier after{};after.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;
    after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);
    ok(a.vkEndCommandBuffer(command),"Dequant command end failed");VkFenceCreateInfo fi{};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    VkFence fence{};ok(a.vkCreateFence(a.device,&fi,nullptr,&fence),"Dequant fence failed");VkSubmitInfo submit{};
    submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.commandBufferCount=1;submit.pCommandBuffers=&command;
    ok(a.vkQueueSubmit(a.queue,1,&submit,fence),"Dequant submit failed");
    if(a.vkWaitForFences(a.device,1,&fence,VK_TRUE,120000000000ull)!=VK_SUCCESS){
        std::cerr<<"Software dequant completion unknown; retain owners\n"<<std::flush;for(;;)Sleep(1000);}
    std::memcpy(output.data(),buffers[1].mapped,output.size()*2);
    bool canaries=!std::memcmp(buffers[0].mapped,input.data(),input.size());
    for(std::size_t i=0;i<guard;++i)canaries=canaries&&output[i]==0x5a5a&&output[guard+values+i]==0x5a5a;
    std::uint64_t mismatches=0;
    for(unsigned plane=0;plane<10;++plane){
        const auto*carrier=weights.data()+plane*460800u;
        std::uint64_t grid[256];std::uint8_t signs[128];std::memcpy(grid,carrier+422464,2048);
        for(unsigned s=0;s<128;++s)signs[s]=std::uint8_t(qwen_app::PairedIQ2Down::u32(carrier+424512+s*4));
        for(unsigned i=0;i<1638400;++i){
            const _Float16 rounded=static_cast<_Float16>(qwen_app::PairedIQ2Down::decode(carrier+64,i/640,i%640,grid,signs));
            std::uint16_t expected;std::memcpy(&expected,&rounded,2);
            if(output[guard+plane*1638400+i]!=expected)++mismatches;
        }
    }
    a.vkDestroyFence(a.device,fence,nullptr);a.vkDestroyCommandPool(a.device,commands,nullptr);
    a.vkDestroyDescriptorPool(a.device,pool,nullptr);for(auto&b:buffers)release(a,b);
    return {{"layer",c.at("layer")},{"values",values},{"mismatches",mismatches},{"FP16_storage_bits_exact",!mismatches},
        {"descriptor_prefix_bytes",prefix},{"canaries_exact",canaries},{"positive_fence",true},{"all_case_resources_retired",true},
        {"passed",!mismatches&&canaries}};
}

int main(int argc,char**argv){try{
    need(argc==3,"Manifest and output required");const auto manifest=Json::parse(read(argv[1]));API a(true);
    VkDescriptorSetLayoutBinding bindings[2]{};for(unsigned i=0;i<2;++i){bindings[i].binding=i;
        bindings[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;bindings[i].descriptorCount=1;bindings[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
    VkDescriptorSetLayoutCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;di.bindingCount=2;di.pBindings=bindings;
    VkDescriptorSetLayout descriptors{};ok(a.vkCreateDescriptorSetLayout(a.device,&di,nullptr,&descriptors),"Dequant descriptor layout failed");
    VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT,0,20};VkPipelineLayoutCreateInfo li{};
    li.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;li.setLayoutCount=1;li.pSetLayouts=&descriptors;li.pushConstantRangeCount=1;li.pPushConstantRanges=&range;
    VkPipelineLayout layout{};ok(a.vkCreatePipelineLayout(a.device,&li,nullptr,&layout),"Dequant pipeline layout failed");
    const auto raw=read(manifest.at("shader").at("path"));std::vector<std::uint32_t>words(raw.size()/4);std::memcpy(words.data(),raw.data(),raw.size());
    VkShaderModuleCreateInfo si{};si.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;si.codeSize=raw.size();si.pCode=words.data();
    VkShaderModule module{};ok(a.vkCreateShaderModule(a.device,&si,nullptr,&module),"Dequant module failed");
    VkComputePipelineCreateInfo pi{};pi.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;pi.layout=layout;pi.flags=VK_PIPELINE_CREATE_DISPATCH_BASE_BIT;
    pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pi.stage.module=module;pi.stage.pName="main";
    VkPipeline pipeline{};ok(a.vkCreateComputePipelines(a.device,VK_NULL_HANDLE,1,&pi,nullptr,&pipeline),"Dequant pipeline failed");
    Json result={{"completed",false},{"software_only",true},{"PS5_operations",0},{"cases",Json::array()}};
    for(const auto&c:manifest.at("cases")){auto row=check(a,pipeline,layout,descriptors,c);result["cases"].push_back(row);save(argv[2],result);need(row.at("passed"),"Packed-half dequant differs from the independent decoder");}
    a.vkDestroyPipeline(a.device,pipeline,nullptr);a.vkDestroyShaderModule(a.device,module,nullptr);
    a.vkDestroyPipelineLayout(a.device,layout,nullptr);a.vkDestroyDescriptorSetLayout(a.device,descriptors,nullptr);a.close();
    result["completed"]=true;result["all_GPU_resources_positively_retired"]=true;save(argv[2],result);return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
