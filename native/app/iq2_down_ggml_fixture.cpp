// SPDX-License-Identifier: MIT
// The published carrier operands are exercised through the selected GGML ABI.
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <nlohmann/json.hpp>
static nlohmann::json qwen_paired_down_prepare_CPU();
#include "paired_down_native_support.h"
#include "shader_assets.h"
#include "iq2_down_resource_checks.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "native_failure_journal.h"
#include <cmath>

static NativeJson qwen_paired_down_prepare_CPU(){
    native_guard(31);qwen_native_stage("IQ2_Down_shader_CPU_admission_before_GPU");
    qwen_app::install_native_assertion_journal();
    for(const auto*name:{"GGML_VK_BOUNDED_STAGING","GGML_VK_DISABLE_ASYNC",
        "GGML_VK_SERIALIZE_SUBMISSIONS","GGML_VK_MAX_NODES_PER_SUBMIT",
        "GGML_VK_DISABLE_INTEGER_DOT_PRODUCT","GGML_VK_DISABLE_COOPMAT","GGML_VK_DISABLE_COOPMAT2"}){
        native_require(!setenv(name,"1",1)&&!std::strcmp(getenv(name),"1"),
            "The successful production GGML environment must be applied before backend initialization");
    }
    qwen_app::initialize_native_shader_file(iq2_shader_file_path,iq2_shader_file_bytes,iq2_shader_file_SHA256);
    qwen_app::initialize_native_shader_assets();
    unsigned verified=0;
    for(const auto&resource:iq2_resource_checks){
        std::size_t bytes=0;void*lease=nullptr;
        const void*code=qwen_app_prepare_shader_code(resource.data,resource.bytes,&bytes,&lease);
        native_require(code==resource.data&&bytes==resource.bytes&&lease,
            "Every replacement shader requires its original CPU lease and whole SHA256");
        qwen_app_complete_shader_code(lease);++verified;
    }
    const auto stats=qwen_app::native_shader_asset_stats();
    native_require(stats.initialized&&!stats.failed&&!stats.active_lease&&stats.assets==1527&&
        stats.lookup_entries==382&&stats.CPU_verified_lookups==382&&
        stats.registry_sha256==iq2_original_registry_SHA256&&stats.external_file.verified&&
        !stats.external_file.failed&&!stats.external_file.read_pending&&verified==13,
        "Original registry, fresh shader file and all thirteen replacement leases must be admitted before GPU");
    native_guard(31);qwen_native_stage("IQ2_Down_shader_CPU_admission_completed_GPU_not_started");
    return {{"completed",true},{"GPU_calls",0},{"initialized",true},{"active_lease",false},
        {"original_assets",stats.assets},{"original_lookups_verified",stats.CPU_verified_lookups},
        {"replacement_resources_verified",verified},{"shader_file_verified",true},
        {"original_registry_SHA256",stats.registry_sha256},{"original_all_asset_decode_replayed",false},
        {"successful_GGML_environment_verified",7},{"native_assertion_journal_installed",true}};
}

static VkInstance fixture_instance=VK_NULL_HANDLE;
static std::uintptr_t fixture_device=0;
static PFN_vkCreateInstance fixture_create_instance=nullptr;
static ggml_backend_t fixture_backend=nullptr;
extern "C" PFN_vkVoidFunction __real_vkGetInstanceProcAddr(VkInstance,const char*);
extern "C" void __real_qwen_native_driver_register_device(std::uintptr_t);
static VkResult VKAPI_CALL fixture_create(const VkInstanceCreateInfo*info,const VkAllocationCallbacks*allocator,VkInstance*instance){
    native_require(fixture_create_instance&&!fixture_instance,"Only one original GGML instance is admitted");
    const auto result=fixture_create_instance(info,allocator,instance);
    if(result==VK_SUCCESS){native_require(instance&&*instance,"Actual GGML instance handle required");fixture_instance=*instance;}
    return result;
}
extern "C" PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance instance,const char*name){
    const auto operation=__real_vkGetInstanceProcAddr(instance,name);
    if(name&&!std::strcmp(name,"vkCreateInstance")&&operation){
        fixture_create_instance=reinterpret_cast<PFN_vkCreateInstance>(operation);
        return reinterpret_cast<PFN_vkVoidFunction>(fixture_create);
    }
    return operation;
}
extern "C" void __wrap_qwen_native_driver_register_device(std::uintptr_t device){
    native_require(device&&!fixture_device,"Exactly one actual GGML device is admitted");
    fixture_device=device;__real_qwen_native_driver_register_device(device);
}

static NativeJson fixture_case(const NativeJson&c){
    const unsigned width=c.at("width"),selected=c.at("selected"),planes=c.at("planes");
    native_require((width==1||width==2||width==30||width==32)&&planes==10&&selected==(width<=2?2u:10u),
        "Exact published Down shape required");
    const auto weights=native_read(c.at("weights").at("path"));
    const auto inputs=native_read(c.at("inputs").at("path"));
    const auto ids=native_read(c.at("ids").at("path"));
    const auto reference=native_read(c.at("expected").at("path"));
    const std::size_t values=std::size_t(width)*selected*2560;
    native_require(weights.size()==460800u*planes&&inputs.size()==std::size_t(width)*selected*640*4&&
        ids.size()==std::size_t(width)*selected*4&&reference.size()==values*8,"Published complete operand extents required");
    native_guard(31);
    ggml_init_params params{};params.no_alloc=true;
    params.mem_size=32*ggml_tensor_overhead()+ggml_graph_overhead_custom(32,false);
    auto*ctx=ggml_init(params);native_require(ctx,"Bounded GGML CPU metadata required");
    auto*gate=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_K,2560,640,11);
    auto*up=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_K,2560,640,11);
    auto*bank=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_0,640,2560,11);
    native_require(bank->nb[2]==460800,"Original Q2_0 cache plane ABI required");
    auto*view=ggml_view_3d(ctx,bank,640,2560,10,bank->nb[1],bank->nb[2],bank->nb[2]);
    auto*x=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,640,selected,width);
    auto*indices=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,selected,width);
    auto*guard=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);
    auto*y=ggml_mul_mat_id(ctx,view,x,indices);
    ggml_set_input(x);ggml_set_input(indices);ggml_set_output(y);ggml_set_output(guard);
    ggml_set_name(gate,"fixture.moe_cache.Gate");ggml_set_name(up,"fixture.moe_cache.Up");
    ggml_set_name(bank,"fixture.moe_cache.Down");ggml_set_name(view,"fixture.nonzero.Down.view");
    native_require(ggml_backend_supports_op(fixture_backend,y),"Actual GGML carrier operator unsupported");
    auto*graph=ggml_new_graph_custom(ctx,32,false);ggml_build_forward_expand(graph,y);
    auto*buffer=ggml_backend_alloc_ctx_tensors(ctx,fixture_backend);
    native_require(buffer,"Bounded actual GGML device allocation required");
    auto*device=ggml_backend_buft_get_device(ggml_backend_buffer_get_type(buffer));
    native_require(device&&ggml_backend_dev_type(device)==GGML_BACKEND_DEVICE_TYPE_IGPU,
        "The selected integrated Vulkan backend is required");
    native_require(view->view_src==bank&&view->view_offs==460800&&view->nb[2]==460800&&
        std::uintptr_t(bank->data)>std::uintptr_t(up->data)&&std::uintptr_t(up->data)>std::uintptr_t(gate->data),
        "Actual Gate/Up prefix and nonzero Down view must be allocated in order");
    std::vector<unsigned char>prefix(460800,0xa5),observed_prefix(prefix.size());
    std::array<float,128>canary;canary.fill(42.125f);
    ggml_backend_tensor_set(bank,prefix.data(),0,prefix.size());
    ggml_backend_tensor_set(view,weights.data(),0,weights.size());
    ggml_backend_tensor_set(x,inputs.data(),0,inputs.size());
    ggml_backend_tensor_set(indices,ids.data(),0,ids.size());
    ggml_backend_tensor_set(guard,canary.data(),0,sizeof(canary));
    ggml_backend_synchronize(fixture_backend);qwen_native_driver_checkpoint();
    native_guard(31);qwen_native_stage("IQ2_Down_GGML_graph_before_native_call");
    native_require(ggml_backend_graph_compute(fixture_backend,graph)==GGML_STATUS_SUCCESS,
        "Unknown GGML graph completion retains all owners");
    ggml_backend_synchronize(fixture_backend);qwen_native_driver_checkpoint();
    qwen_native_stage("IQ2_Down_GGML_graph_positively_completed");
    std::vector<float>actual(values);ggml_backend_tensor_get(y,actual.data(),0,values*4);
    ggml_backend_tensor_get(guard,canary.data(),0,sizeof(canary));
    ggml_backend_tensor_get(bank,observed_prefix.data(),0,observed_prefix.size());
    std::uint64_t mismatches=0;double maximum=0;
    for(std::size_t i=0;i<values;++i){double expected;std::memcpy(&expected,reference.data()+8*i,8);
        const double error=std::abs(double(actual[i])-expected);
        if(!std::isfinite(actual[i])||error>1e-5+2e-4*std::abs(expected))++mismatches;
        if(std::isfinite(error))maximum=std::max(maximum,error);
    }
    const bool canaries=observed_prefix==prefix&&std::all_of(canary.begin(),canary.end(),[](float f){return f==42.125f;});
    const auto bank_offset=std::uintptr_t(bank->data)-std::uintptr_t(gate->data);
    ggml_backend_synchronize(fixture_backend);qwen_native_driver_checkpoint();
    ggml_backend_buffer_free(buffer);ggml_free(ctx);
    return {{"layer",c.at("layer")},{"width",width},{"selected",selected},{"output_values",values},
        {"GGML_graphs",1},{"positive_fence",true},{"all_case_resources_retired",true},
        {"actual_Gate_Up_prefix_bytes",bank_offset},{"actual_Down_view_offset",460800},
        {"carrier_plane_bytes",460800},{"canaries_exact",canaries},{"mismatches",mismatches},
        {"all_outputs_passed",mismatches==0&&canaries},{"maximum_absolute_F64_reference_error",maximum},
        {"PS5_speed_claimed",false}};
}

int qwen_paired_down_component(int argc,char**argv){
    native_require(argc==3,"One finite GGML carrier component required");
    const auto cases=NativeJson::parse(paired_cases_json);
    native_require(cases.at("cases").size()==12,"Twelve original layer/width cases required");
    native_require(!setenv("GGML_VK_DISABLE_MMVQ","1",1)&&!setenv("GGML_VK_DISABLE_F16","1",1),
        "Explicit original F32 activation and shader arithmetic profile required");
    native_component_prepare();
#if IQ2_DOWN_GPU_RESOURCE_TRACE
    qwen_iq2_down_begin_GPU_resource_trace();
#endif
    fixture_backend=ggml_backend_vk_init(0);
    native_require(fixture_backend&&fixture_instance&&fixture_device,"Captured actual live GGML owner required");
    NativeJson result={{"completed",false},{"native_PS5",true},{"model_loads",0},
        {"GGML_carrier_ABI",true},{"cases",NativeJson::array()},{"all_outputs_passed",true},
        {"unknown_completion",false},{"all_GPU_resources_positively_retired",false},
        {"all_case_resources_positively_retired",false},{"whole_model_speed_qualified",false},
        {"GGML_backend_free_calls",0},{"persistent_pipeline_cache",false}};
    result["completed_GGML_case_prefix"]=iq2_completed_GGML_prefix;
    unsigned case_index=0;
    for(const auto&c:cases.at("cases")){
        if(case_index++<iq2_completed_GGML_prefix)continue;
        const auto row=fixture_case(c);result["cases"].push_back(row);native_save(argv[2],result);
        if(!row.at("all_outputs_passed").get<bool>()){result["all_outputs_passed"]=false;break;}
    }
    // Keep the actual GGML backend, its device, instance and internal backing
    // alive through the final producer completion and ordinary process close.
    qwen_native_driver_complete();const auto epoch=native_completed_epoch();
    native_component_retain(fixture_device,reinterpret_cast<std::uintptr_t>(fixture_instance),epoch);
    result["completed"]=true;result["all_case_resources_positively_retired"]=true;
    result["retained_completed_device"]=native_retained_receipt();
    result["retained_GGML_backend"]=reinterpret_cast<std::uintptr_t>(fixture_backend);
    native_retained_result=result;native_save(argv[2],result);
    return result.at("all_outputs_passed").get<bool>()?0:2;
}
