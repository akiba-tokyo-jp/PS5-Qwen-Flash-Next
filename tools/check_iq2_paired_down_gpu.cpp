// SPDX-License-Identifier: MIT
// A finite desktop Vulkan component check. It never communicates with a PS5.
#define VK_NO_PROTOTYPES
#define NOMINMAX
#include <vulkan/vulkan.h>
#include <windows.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
using Json=nlohmann::json;
void need(bool value,const char*message){if(!value)throw std::runtime_error(message);}
void ok(VkResult value,const char*message){if(value!=VK_SUCCESS)throw std::runtime_error(std::string(message)+" VkResult="+std::to_string(int(value)));}
std::vector<unsigned char>read(const std::string&path){
    std::ifstream stream(path,std::ios::binary|std::ios::ate);need(bool(stream),"Component file unavailable");const auto bytes=stream.tellg();
    need(bytes>0&&bytes<=64*1024*1024,"Bounded component file required");std::vector<unsigned char>data(static_cast<std::size_t>(bytes));
    stream.seekg(0);stream.read(reinterpret_cast<char*>(data.data()),data.size());need(bool(stream),"Full component file read required");return data;
}
void save(const std::string&path,const Json&value){std::ofstream out(path,std::ios::binary);out<<value.dump(2)<<'\n';out.flush();need(bool(out),"GPU result write failed");}
#define DEVICE_API(X) \
    X(vkDestroyDevice) X(vkGetDeviceQueue) X(vkCreateBuffer) X(vkDestroyBuffer) X(vkGetBufferMemoryRequirements) \
    X(vkAllocateMemory) X(vkFreeMemory) X(vkBindBufferMemory) X(vkMapMemory) X(vkUnmapMemory) \
    X(vkCreateDescriptorSetLayout) X(vkDestroyDescriptorSetLayout) X(vkCreatePipelineLayout) X(vkDestroyPipelineLayout) \
    X(vkCreateShaderModule) X(vkDestroyShaderModule) X(vkCreateComputePipelines) X(vkDestroyPipeline) \
    X(vkCreateDescriptorPool) X(vkDestroyDescriptorPool) X(vkAllocateDescriptorSets) X(vkUpdateDescriptorSets) \
    X(vkCreateCommandPool) X(vkDestroyCommandPool) X(vkAllocateCommandBuffers) X(vkBeginCommandBuffer) X(vkEndCommandBuffer) \
    X(vkCmdPipelineBarrier) X(vkCmdBindPipeline) X(vkCmdBindDescriptorSets) X(vkCmdPushConstants) X(vkCmdDispatch) X(vkCmdDispatchBase) \
    X(vkCreateFence) X(vkDestroyFence) X(vkQueueSubmit) X(vkWaitForFences)
struct API {
    VkInstance instance{};VkDevice device{};VkPhysicalDevice physical{};VkQueue queue{};unsigned family=0;
    VkPhysicalDeviceMemoryProperties memory{};VkPhysicalDeviceProperties properties{};
    PFN_vkDestroyInstance destroy_instance{};
#define FIELD(name) PFN_##name name{};
    DEVICE_API(FIELD)
#undef FIELD
    explicit API(bool software){
        auto library=LoadLibraryA("vulkan-1.dll");need(library,"Desktop Vulkan loader unavailable");
        const auto get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(GetProcAddress(library,"vkGetInstanceProcAddr"));need(get,"Desktop Vulkan entry unavailable");
        const auto create=reinterpret_cast<PFN_vkCreateInstance>(get(VK_NULL_HANDLE,"vkCreateInstance"));need(create,"Vulkan create entry unavailable");
        VkApplicationInfo app{};app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO;app.pApplicationName="Qwen paired Down component";app.apiVersion=VK_API_VERSION_1_2;
        VkInstanceCreateInfo info{};info.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;info.pApplicationInfo=&app;ok(create(&info,nullptr,&instance),"Desktop instance creation failed");
#define INSTANCE(type,name) const auto name=reinterpret_cast<PFN_##type>(get(instance,#type));need(name,"Desktop Vulkan instance API unavailable")
        INSTANCE(vkEnumeratePhysicalDevices,enumerate);INSTANCE(vkGetPhysicalDeviceProperties,properties_of);
        INSTANCE(vkGetPhysicalDeviceQueueFamilyProperties,queues);INSTANCE(vkGetPhysicalDeviceMemoryProperties,memory_of);
        INSTANCE(vkCreateDevice,create_device);INSTANCE(vkGetDeviceProcAddr,get_device);
#undef INSTANCE
        destroy_instance=reinterpret_cast<PFN_vkDestroyInstance>(get(instance,"vkDestroyInstance"));
        unsigned count=0;ok(enumerate(instance,&count,nullptr),"Device enumeration failed");need(count&&count<=32,"Bounded desktop GPU inventory required");
        std::vector<VkPhysicalDevice>devices(count);ok(enumerate(instance,&count,devices.data()),"Complete device enumeration failed");
        for(auto candidate:devices){
            VkPhysicalDeviceProperties p{};properties_of(candidate,&p);
            const bool type=software?p.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU:
                (p.deviceType==VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU||p.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU);
            if(!type||p.apiVersion<VK_API_VERSION_1_2)continue;
            unsigned n=0;queues(candidate,&n,nullptr);std::vector<VkQueueFamilyProperties>q(n);queues(candidate,&n,q.data());
            for(unsigned i=0;i<n;++i)if(q[i].queueCount&&(q[i].queueFlags&VK_QUEUE_COMPUTE_BIT)){physical=candidate;family=i;properties=p;break;}
            if(physical)break;
        }
        need(physical&&properties.limits.maxComputeWorkGroupInvocations>=128&&properties.limits.maxComputeWorkGroupSize[0]>=128&&
            properties.limits.maxComputeWorkGroupCount[0]>=2560&&properties.limits.maxStorageBufferRange>=8u*1024*1024,
            "The explicitly selected desktop backend and bounded component limits are required");
        const float priority=1;VkDeviceQueueCreateInfo qi{};qi.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkDeviceCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;
        ok(create_device(physical,&di,nullptr,&device),"Desktop compute device creation failed");
#define LOAD(name) name=reinterpret_cast<PFN_##name>(get_device(device,#name));need(name,"Desktop Vulkan device API unavailable");
        DEVICE_API(LOAD)
#undef LOAD
        memory_of(physical,&memory);vkGetDeviceQueue(device,family,0,&queue);
    }
    void close(){vkDestroyDevice(device,nullptr);device=VK_NULL_HANDLE;destroy_instance(instance,nullptr);instance=VK_NULL_HANDLE;}
};
struct Buffer {VkBuffer buffer{};VkDeviceMemory memory{};void*mapped=nullptr;VkDeviceSize bytes=0;};
Buffer allocate(API&a,VkDeviceSize bytes,const void*data){
    Buffer b;b.bytes=bytes;VkBufferCreateInfo info{};info.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;info.size=bytes;info.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;info.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    ok(a.vkCreateBuffer(a.device,&info,nullptr,&b.buffer),"Component buffer allocation failed");VkMemoryRequirements req{};a.vkGetBufferMemoryRequirements(a.device,b.buffer,&req);
    unsigned index=a.memory.memoryTypeCount;
    for(unsigned i=0;i<a.memory.memoryTypeCount;++i)if((req.memoryTypeBits&(1u<<i))&&
        (a.memory.memoryTypes[i].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){index=i;break;}
    need(index<a.memory.memoryTypeCount&&req.size<=32u*1024*1024,"Bounded coherent host-visible component storage required");
    VkMemoryAllocateInfo mi{};mi.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;mi.allocationSize=req.size;mi.memoryTypeIndex=index;
    ok(a.vkAllocateMemory(a.device,&mi,nullptr,&b.memory),"Component device memory allocation failed");ok(a.vkBindBufferMemory(a.device,b.buffer,b.memory,0),"Component bind failed");
    ok(a.vkMapMemory(a.device,b.memory,0,VK_WHOLE_SIZE,0,&b.mapped),"Component map failed");std::memcpy(b.mapped,data,bytes);return b;
}
void release(API&a,Buffer&b){a.vkUnmapMemory(a.device,b.memory);a.vkDestroyBuffer(a.device,b.buffer,nullptr);a.vkFreeMemory(a.device,b.memory,nullptr);b={};}
Json check(API&a,VkPipeline pipeline,VkPipelineLayout layout,VkDescriptorSetLayout descriptors,const Json&c,const std::string&result,unsigned workgroup,Json&progress){
    const auto weights=read(c.at("weights").at("path")),inputs=read(c.at("inputs").at("path")),ids=read(c.at("ids").at("path")),expected=read(c.at("expected").at("path"));
    const unsigned width=c.at("width"),selected=c.at("selected"),planes=c.at("planes");
    const unsigned values=width*selected*2560;need(width&&width<=32&&selected&&selected<=10&&planes==10&&weights.size()==422400u*planes&&
        inputs.size()==width*selected*640u*4&&ids.size()==width*selected*4u&&expected.size()==values*8u,"Exact paired Down case geometry required");
    std::vector<float>output(values+128,42.125f);std::vector<Buffer>buffers{allocate(a,weights.size(),weights.data()),allocate(a,inputs.size(),inputs.data()),allocate(a,ids.size(),ids.data()),allocate(a,output.size()*4,output.data())};
    if(progress.at("buffer_tables").get<bool>()){
        const auto tables=read(progress.at("table_path"));need(tables.size()==2560,"Exact readonly IQ2 codebook buffer required");buffers.push_back(allocate(a,tables.size(),tables.data()));
    }
    const auto bindings=unsigned(buffers.size());VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,bindings};VkDescriptorPoolCreateInfo pool_info{};pool_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;pool_info.maxSets=1;pool_info.poolSizeCount=1;pool_info.pPoolSizes=&pool_size;
    VkDescriptorPool pool{};ok(a.vkCreateDescriptorPool(a.device,&pool_info,nullptr,&pool),"Descriptor pool failed");
    VkDescriptorSetAllocateInfo set_info{};set_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;set_info.descriptorPool=pool;set_info.descriptorSetCount=1;set_info.pSetLayouts=&descriptors;
    VkDescriptorSet set{};ok(a.vkAllocateDescriptorSets(a.device,&set_info,&set),"Descriptor allocation failed");
    VkDescriptorBufferInfo ranges[5]{};VkWriteDescriptorSet writes[5]{};
    for(unsigned i=0;i<bindings;++i){ranges[i]={buffers[i].buffer,0,buffers[i].bytes};writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=set;writes[i].dstBinding=i;writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[i].pBufferInfo=&ranges[i];}
    a.vkUpdateDescriptorSets(a.device,bindings,writes,0,nullptr);
    VkCommandPoolCreateInfo ci{};ci.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;ci.flags=VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;ci.queueFamilyIndex=a.family;
    VkCommandPool command_pool{};ok(a.vkCreateCommandPool(a.device,&ci,nullptr,&command_pool),"Command pool failed");
    const bool software=progress.at("software_SPIRV_reference");const unsigned tile_rows=software?64:2560;
    unsigned dispatches=0;double wall=0;
    for(unsigned row_base=0;row_base<2560;row_base+=tile_rows){
    VkCommandBufferAllocateInfo ai{};ai.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;ai.commandPool=command_pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
    VkCommandBuffer command{};ok(a.vkAllocateCommandBuffers(a.device,&ai,&command),"Command allocation failed");
    VkCommandBufferBeginInfo bi{};bi.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;ok(a.vkBeginCommandBuffer(command,&bi),"Command begin failed");
    VkMemoryBarrier before{};before.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
    a.vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);a.vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
    const unsigned geometry[4]={width,selected,planes,64};a.vkCmdPushConstants(command,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(geometry),geometry);
    if(software)a.vkCmdDispatchBase(command,row_base,0,0,std::min(tile_rows,2560-row_base),selected,width);
    else a.vkCmdDispatch(command,2560,selected,width);
    VkMemoryBarrier after{};after.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    a.vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);ok(a.vkEndCommandBuffer(command),"Command end failed");
    VkFenceCreateInfo fi{};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;VkFence fence{};ok(a.vkCreateFence(a.device,&fi,nullptr,&fence),"Fence creation failed");
    VkSubmitInfo submit{};submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.commandBufferCount=1;submit.pCommandBuffers=&command;
    const auto started=std::chrono::steady_clock::now();const auto submitted=a.vkQueueSubmit(a.queue,1,&submit,fence);
    const auto waited=submitted==VK_SUCCESS?a.vkWaitForFences(a.device,1,&fence,VK_TRUE,30000000000ull):submitted;
    if(waited!=VK_SUCCESS){
        progress["unknown_completion"]=true;progress["VkResult"]=waited;progress["owner_retained"]=true;save(result,progress);
        std::cerr<<"Desktop GPU completion unknown; resources retained, no resubmission\n"<<std::flush;for(;;)Sleep(1000);
    }
    wall+=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-started).count();++dispatches;
    a.vkDestroyFence(a.device,fence,nullptr);
    progress["positive_reference_dispatches"]=progress.value("positive_reference_dispatches",0u)+1;
    progress["last_positive_row_base"]=row_base;save(result,progress);
    }
    std::memcpy(output.data(),buffers[3].mapped,output.size()*4);bool valid=true;std::uint64_t mismatches=0;double maximum=0;
    for(unsigned i=0;i<values;++i){double reference;std::memcpy(&reference,expected.data()+8u*i,8);const double error=std::abs(double(output[64+i])-reference);
        if(!std::isfinite(output[64+i])||error>1e-5+2e-4*std::abs(reference)){valid=false;++mismatches;}maximum=std::max(maximum,error);}
    const bool canaries=std::all_of(output.begin(),output.begin()+64,[](float x){return x==42.125f;})&&std::all_of(output.end()-64,output.end(),[](float x){return x==42.125f;});
    a.vkDestroyCommandPool(a.device,command_pool,nullptr);a.vkDestroyDescriptorPool(a.device,pool,nullptr);for(auto&b:buffers)release(a,b);
    return {{"layer",c.at("layer")},{"width",width},{"selected",selected},{"workgroup",workgroup},{"output_values",values},{"all_outputs_passed",valid&&canaries},
        {"mismatches",mismatches},{"canaries_exact",canaries},{"maximum_absolute_F64_reference_error",maximum},{"positive_fence",true},{"all_case_resources_retired",true},
        {"desktop_dispatch_and_fence_wall_us",wall},{"Vulkan_dispatches",dispatches},{"PS5_speed_claimed",false}};
}
int main(int argc,char**argv){try{
    need(argc>=3&&argc<=5,"One exact case manifest and result path required");bool first_only=false,software=false;
    for(int i=3;i<argc;++i){const std::string flag=argv[i];need(flag=="--first-case-only"||flag=="--software-reference","Only explicit finite backend flags are admitted");
        if(flag=="--first-case-only")first_only=true;else software=true;}
    const auto raw=read(argv[1]);const auto cases=Json::parse(raw);
    need(cases.at("completed")==true&&cases.at("cases").size()==12&&cases.at("shader").size()==2,"Exact finite compiled component cases required");
    API a(software);Json result={{"completed",false},{"desktop_GPU",a.properties.deviceName},{"software_SPIRV_reference",software},{"physical_GPU_execution",!software},
        {"vendor_ID",a.properties.vendorID},{"device_ID",a.properties.deviceID},
        {"API_version",a.properties.apiVersion},{"driver_version",a.properties.driverVersion},{"cases",Json::array()},{"PS5_operations",0},{"whole_model_speed_qualified",false},{"persistent_pipeline_cache",false}};
    result["buffer_tables"]=cases.value("buffer_tables",false);if(result["buffer_tables"].get<bool>())result["table_path"]=cases.at("tables").at("path");
    const unsigned binding_count=result["buffer_tables"].get<bool>()?5:4;
    VkDescriptorSetLayoutBinding bindings[5]{};for(unsigned i=0;i<binding_count;++i){bindings[i].binding=i;bindings[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;bindings[i].descriptorCount=1;bindings[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
    VkDescriptorSetLayoutCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;di.bindingCount=binding_count;di.pBindings=bindings;
    VkDescriptorSetLayout descriptors{};ok(a.vkCreateDescriptorSetLayout(a.device,&di,nullptr,&descriptors),"Descriptor layout failed");
    VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT,0,16};VkPipelineLayoutCreateInfo li{};li.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;li.setLayoutCount=1;li.pSetLayouts=&descriptors;li.pushConstantRangeCount=1;li.pPushConstantRanges=&range;
    VkPipelineLayout layout{};ok(a.vkCreatePipelineLayout(a.device,&li,nullptr,&layout),"Pipeline layout failed");bool valid=true;
    for(const auto&shader:cases.at("shader")){
        const auto binary=read(shader.at("artifact").at("path"));need(binary.size()%4==0,"Aligned SPIRV required");std::vector<std::uint32_t>words(binary.size()/4);std::memcpy(words.data(),binary.data(),binary.size());
        VkShaderModuleCreateInfo si{};si.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;si.codeSize=binary.size();si.pCode=words.data();VkShaderModule module{};
        ok(a.vkCreateShaderModule(a.device,&si,nullptr,&module),"Shader module failed");VkComputePipelineCreateInfo pi{};pi.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;pi.layout=layout;
        pi.flags=VK_PIPELINE_CREATE_DISPATCH_BASE_BIT;pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pi.stage.module=module;pi.stage.pName="main";VkPipeline pipeline{};
        ok(a.vkCreateComputePipelines(a.device,VK_NULL_HANDLE,1,&pi,nullptr,&pipeline),"Paired Down compute pipeline failed");
        for(const auto&c:cases.at("cases")){auto row=check(a,pipeline,layout,descriptors,c,argv[2],shader.at("workgroup"),result);valid=valid&&row.at("all_outputs_passed").get<bool>();result["cases"].push_back(row);save(argv[2],result);std::cout<<row.dump()<<'\n'<<std::flush;if(!valid||first_only)break;}
        a.vkDestroyPipeline(a.device,pipeline,nullptr);a.vkDestroyShaderModule(a.device,module,nullptr);if(!valid||first_only)break;
    }
    a.vkDestroyPipelineLayout(a.device,layout,nullptr);a.vkDestroyDescriptorSetLayout(a.device,descriptors,nullptr);a.close();
    result["completed"]=true;result["all_outputs_passed"]=valid;result["all_GPU_resources_positively_retired"]=true;result["unknown_completion"]=false;save(argv[2],result);
    return valid?0:2;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
