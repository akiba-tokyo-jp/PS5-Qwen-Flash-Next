// SPDX-License-Identifier: MIT
#include "calibrated_iq2_fixture.h"
#include "calibrated_iq2_assets.h"
#include "direct_integrity.h"
#include "system_memory.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "ggml-quants.h"
#include <ps5platform/heap.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
void need(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
double us(Clock::time_point start){return std::chrono::duration<double,std::micro>(Clock::now()-start).count();}
std::string sha(const void*data,std::size_t bytes){
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,static_cast<const unsigned char*>(data),bytes);
    unsigned char digest[32];sha256_final(&hash,digest);std::string out;
    for(auto value:digest){out+="0123456789abcdef"[value>>4];out+="0123456789abcdef"[value&15];}return out;
}
float input(unsigned column,unsigned token){return float(int((column+3*token)%13)-6)/1009.0f;}
struct Pack {
    int fd=-1;void*scratch=nullptr;struct stat original{};
    std::uint64_t reads=0,physical=0;void(*stage)(const char*);
    explicit Pack(void(*s)(const char*)):stage(s){
        qwen_app::verify_native_startup_file_direct(iq2_pack_path,iq2_pack_bytes,iq2_pack_sha256,60);
        fd=open(iq2_pack_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
        need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&!fstat(fd,&original)&&S_ISREG(original.st_mode)&&
             std::uint64_t(original.st_size)==iq2_pack_bytes,"Exact Direct IQ2 fixture pack required");
        need(!posix_memalign(&scratch,16384,4u<<20)&&scratch&&ps5_heap_owns(scratch),"Tracked4MiB IQ2 scratch required");
    }
    bool stable()const{
        struct stat after{};return !fstat(fd,&after)&&original.st_dev==after.st_dev&&original.st_ino==after.st_ino&&
            original.st_mode==after.st_mode&&original.st_uid==after.st_uid&&original.st_gid==after.st_gid&&
            original.st_size==after.st_size&&original.st_mtim.tv_sec==after.st_mtim.tv_sec&&
            original.st_mtim.tv_nsec==after.st_mtim.tv_nsec&&original.st_ctim.tv_sec==after.st_ctim.tv_sec&&
            original.st_ctim.tv_nsec==after.st_ctim.tv_nsec;
    }
    const void*read(unsigned matrix,unsigned format){
        need(matrix<9&&format<2,"IQ2 component selector invalid");
        const auto&part=iq2_matrices[matrix].encoded[format];const auto bytes=(part.bytes+16383)&~std::uint64_t(16383);
        need(part.offset%16384==0&&part.offset+bytes<=iq2_pack_bytes&&bytes<=4u<<20,
             "IQ2 component extent invalid");
        (void)qwen_app::admit_native_system_memory();stage("IQ2_component_Direct_read_before_native_call");
        const auto actual=pread(fd,scratch,bytes,off_t(part.offset));++reads;physical+=bytes;
        stage("IQ2_component_Direct_read_returned");need(actual==ssize_t(bytes)&&stable(),"IQ2 source read or identity failed; retain owner");
        return scratch;
    }
    void verify(unsigned matrix,unsigned format){
        const auto&part=iq2_matrices[matrix].encoded[format];need(sha(scratch,part.bytes)==part.sha256,"IQ2 component payload differs");
    }
    void close_completed(){need(stable()&&close(fd)==0,"IQ2 source retirement failed");fd=-1;free(scratch);scratch=nullptr;}
};
struct Fixture {
    ggml_backend_t backend=nullptr;ggml_context*ctx=nullptr;ggml_backend_buffer_t buffer=nullptr;
    std::array<ggml_tensor*,2> weights{},outputs{};std::array<ggml_cgraph*,2> graphs{};
    ggml_tensor *x=nullptr,*ids=nullptr,*canary=nullptr;
    std::array<std::vector<double>,2> expected;
    unsigned group,width;bool supported=true,valid=true;
    std::uint64_t completed=0,mismatches=0;double maximum_error=0;
    void(*checkpoint)();void(*stage)(const char*);Clock::time_point deadline;
    Fixture(unsigned g,unsigned w,Pack&pack,void(*c)(),void(*s)(const char*),Clock::time_point end):
        group(g),width(w),checkpoint(c),stage(s),deadline(end){
        backend=ggml_backend_vk_init(0);need(backend,"Native IQ2 Vulkan backend unavailable");
        ggml_init_params params{};params.no_alloc=true;params.mem_size=64*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(32,false);
        ctx=ggml_init(params);need(ctx,"IQ2 component CPU metadata unavailable");
        x=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,2560,1,width);ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,2,width);
        canary=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);ggml_set_input(x);ggml_set_input(ids);ggml_set_input(canary);ggml_set_output(canary);
        for(unsigned format=0;format<2;++format){
            weights[format]=ggml_new_tensor_3d(ctx,format?GGML_TYPE_IQ2_XXS:GGML_TYPE_Q2_K,2560,640,10);
            outputs[format]=ggml_mul_mat_id(ctx,weights[format],x,ids);ggml_set_output(outputs[format]);
            supported=supported&&ggml_backend_supports_op(backend,outputs[format]);
            graphs[format]=ggml_new_graph_custom(ctx,32,false);ggml_build_forward_expand(graphs[format],outputs[format]);
        }
        // An unsupported operator has no submitted graph or device tensor
        // allocation. It is a known negative, not an uncertain GPU completion.
        if(!supported)return;
        buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer,"Bounded IQ2 component device allocation failed");
        const auto device=ggml_backend_buft_get_device(ggml_backend_buffer_get_type(buffer));
        need(device&&ggml_backend_dev_type(device)==GGML_BACKEND_DEVICE_TYPE_IGPU,"The actual integrated Vulkan result buffer is required");
        std::array<float,128>guard;guard.fill(42.125f);ggml_backend_tensor_set(canary,guard.data(),0,sizeof(guard));
        constexpr unsigned positions[3]={0,4,9};std::vector<std::int32_t>selected(2*width);
        for(unsigned token=0;token<width;++token)for(unsigned slot=0;slot<2;++slot)selected[2*token+slot]=positions[(slot+token)%3];
        ggml_backend_tensor_set(ids,selected.data(),0,selected.size()*4);
        std::vector<float>values(2560*width);for(unsigned token=0;token<width;++token)for(unsigned col=0;col<2560;++col)
            values[token*2560+col]=input(col,token);
        ggml_backend_tensor_set(x,values.data(),0,values.size()*4);ggml_backend_synchronize(backend);checkpoint();
        for(unsigned format=0;format<2;++format){
            std::vector<double>sums(3*640*13,0);std::array<float,2560>decoded{};
            for(unsigned expert=0;expert<3;++expert){
                const auto matrix=group*3+expert;const auto*raw=static_cast<const unsigned char*>(pack.read(matrix,format));pack.verify(matrix,format);
                for(unsigned row=0;row<640;++row){
                    if(format)dequantize_row_iq2_xxs(reinterpret_cast<const block_iq2_xxs*>(raw+row*660),decoded.data(),2560);
                    else dequantize_row_q2_K(reinterpret_cast<const block_q2_K*>(raw+row*840),decoded.data(),2560);
                    for(unsigned col=0;col<2560;++col){need(std::isfinite(decoded[col]),"Decoded IQ2 reference is nonfinite");
                        sums[(expert*640+row)*13+col%13]+=double(decoded[col]);}
                }
            }
            expected[format].resize(640*2*width);
            for(unsigned token=0;token<width;++token)for(unsigned slot=0;slot<2;++slot)for(unsigned row=0;row<640;++row){
                double value=0;for(unsigned residue=0;residue<13;++residue)
                    value+=sums[(((slot+token)%3)*640+row)*13+residue]*double(input(residue,token));
                expected[format][(token*2+slot)*640+row]=value;
            }
        }
    }
    double load(Pack&pack,unsigned format){
        constexpr unsigned positions[3]={0,4,9};double elapsed=0;
        for(unsigned i=0;i<3;++i){const auto matrix=group*3+i;const auto begin=Clock::now();const auto*raw=pack.read(matrix,format);
            ggml_backend_tensor_set(weights[format],raw,positions[i]*weights[format]->nb[2],iq2_matrices[matrix].encoded[format].bytes);
            ggml_backend_synchronize(backend);checkpoint();elapsed+=us(begin);pack.verify(matrix,format);}
        return elapsed;
    }
    double compute(unsigned format){
        need(completed<12&&Clock::now()<deadline,"IQ2 finite graph/deadline bound reached before submission");
        (void)qwen_app::admit_native_system_memory();stage("IQ2_component_graph_before_native_call");const auto begin=Clock::now();
        need(ggml_backend_graph_compute(backend,graphs[format])==GGML_STATUS_SUCCESS,"IQ2 graph completion unknown; retain all owners");
        ggml_backend_synchronize(backend);checkpoint();++completed;const auto elapsed=us(begin);
        stage("IQ2_component_graph_positively_completed");need(std::isfinite(elapsed)&&elapsed>0,"IQ2 component clock invalid");return elapsed;
    }
    bool verify(unsigned format){
        std::vector<float>actual(expected[format].size());ggml_backend_tensor_get(outputs[format],actual.data(),0,actual.size()*4);
        for(std::size_t i=0;i<actual.size();++i){const double error=std::abs(double(actual[i])-expected[format][i]);
            if(!std::isfinite(actual[i])||error>1e-5+2e-4*std::abs(expected[format][i])){valid=false;++mismatches;}
            if(std::isfinite(error))maximum_error=std::max(maximum_error,error);}
        std::array<float,128>guard;ggml_backend_tensor_get(canary,guard.data(),0,sizeof(guard));
        if(!std::all_of(guard.begin(),guard.end(),[](float v){return v==42.125f;})){valid=false;++mismatches;}
        return valid;
    }
    Json measure(Pack&pack){
        Json arms=Json::array();
        if(supported){
            for(unsigned i=0;i<4&&valid;++i){load(pack,i%2);compute(i%2);verify(i%2);}
            for(unsigned arm=0;arm<4&&valid;++arm){const unsigned format=arm==1||arm==2?1:0;Json samples=Json::array();
                for(unsigned i=0;i<2&&valid;++i){const auto delivery=load(pack,format),kernel=compute(format);verify(format);
                    samples.push_back({{"delivery_us",delivery},{"compute_us",kernel},{"delivery_and_compute_us",delivery+kernel}});}
                arms.push_back({{"format",format?"IQ2_XXS":"Q2_K"},{"samples",samples}});
            }
            // A returned numerical negative still has positive GPU completion.
            // Retire it normally; never issue further candidate graphs.
            ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);buffer=nullptr;
        }
        ggml_free(ctx);ctx=nullptr;ggml_backend_free(backend);backend=nullptr;checkpoint();
        return {{"group",group},{"layer",iq2_matrices[group*3].layer},{"width",width},{"columns",2560},{"rows",640},
            {"selected_Experts",2},{"unique_original_Experts",3},{"supported",supported},{"all_outputs_and_canaries_passed",supported&&valid},
            {"reference","F64 of each separately decoded format"},{"maximum_absolute_GPU_reference_error",maximum_error},
            {"mismatches",mismatches},{"arms",arms},{"GPU_graphs",completed},{"backends_positively_retired",true}};
    }
};
}
namespace qwen_app {
nlohmann::json run_calibrated_iq2_fixture(void(*checkpoint)(),void(*stage)(const char*)){
    need(checkpoint&&stage&&getenv("GGML_VK_DISABLE_MMVQ")&&std::strcmp(getenv("GGML_VK_DISABLE_MMVQ"),"1")==0,
         "Explicit original F32 activation policy required before backend creation");
    Pack pack(stage);const auto deadline=Clock::now()+std::chrono::seconds(240);Json cases=Json::array();bool valid=true;
    std::uint64_t graphs=0;
    for(unsigned group=0;group<3&&valid;++group)for(unsigned width:{1u,2u}){
        Fixture fixture(group,width,pack,checkpoint,stage,deadline);auto row=fixture.measure(pack);
        valid=valid&&row.at("all_outputs_and_canaries_passed").get<bool>();graphs+=row.at("GPU_graphs").get<std::uint64_t>();cases.push_back(row);
        if(!valid)break;
    }
    const auto reads=pack.reads,bytes=pack.physical;pack.close_completed();
    return {{"schema","ps5-qwen-calibrated-IQ2-component-v1"},{"completed",true},{"cases",cases},{"GPU_graphs",graphs},
        {"all_outputs_reference_valid",valid},{"all_backends_positively_retired",true},{"source_descriptor_and_scratch_retired",true},
        {"complete_pack_SHA256_verified",true},{"Direct_reads",reads},{"physical_read_bytes",bytes},
        {"real_weight_calibration",true},{"component_inputs","Synthetic periodic F32 vectors, not model inference"},
        {"component_fixture_not_model_speed",true},{"model_loads",0},{"activation_quantization_disabled",true},
        {"prefill_width30_qualified",false},{"timed_digest_work",false},{"automatic_retries",0}};
}
}
