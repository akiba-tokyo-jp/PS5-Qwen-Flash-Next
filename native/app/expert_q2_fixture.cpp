// SPDX-License-Identifier: MIT
#include "expert_q2_fixture.h"
#include "expert_q2_fixture_assets.h"
#include "expert_q2_geometry.h"
#include "direct_integrity.h"
#include "system_memory.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
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
using Json=nlohmann::json;
using Clock=std::chrono::steady_clock;
std::uint64_t graphs=0;
void check(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
double elapsed(Clock::time_point start){return std::chrono::duration<double,std::micro>(Clock::now()-start).count();}
std::string hash(const void*data,std::size_t bytes){
    sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char*>(data),bytes);
    unsigned char digest[32];sha256_final(&h,digest);std::string out;
    for(auto x:digest){out+="0123456789abcdef"[x>>4];out+="0123456789abcdef"[x&15];}return out;
}
using Identity=std::array<std::uint64_t,10>;
Identity identity(int fd){
    struct stat s{};check(fstat(fd,&s)==0&&S_ISREG(s.st_mode)&&s.st_size==q2_fixture_pack_bytes,"Q2 sample identity differs");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
float bf16(const unsigned char*p){std::uint16_t raw;std::memcpy(&raw,p,2);const std::uint32_t bits=std::uint32_t(raw)<<16;float value;std::memcpy(&value,&bits,4);return value;}
float q2(const unsigned char*p,std::size_t index){
    const auto block=index/64,within=index%64;ggml_fp16_t scale;
    std::memcpy(&scale,p+block*18,2);
    const int value=int((p[block*18+2+within/4]>>(2*(within%4)))&3)-1;
    return ggml_fp16_to_fp32(scale)*float(value);
}
float x_value(unsigned column,unsigned token,unsigned selection){return float(int((column+3*token+5*selection)%13)-6)/1009.0f;}
struct Pack {
    int fd=-1;void*scratch=nullptr;Identity original{};
    std::uint64_t reads=0,physical_bytes=0;
    void(*stage)(const char*);
    explicit Pack(void(*s)(const char*)):stage(s){
        qwen_app::verify_native_startup_file_direct(q2_fixture_pack_path,q2_fixture_pack_bytes,q2_fixture_pack_sha256,60);
        fd=open(q2_fixture_pack_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
        check(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Q2 sample Direct descriptor unavailable");original=identity(fd);
        check(!posix_memalign(&scratch,16384,4u<<20)&&scratch&&ps5_heap_owns(scratch),"Q2 sample tracked Direct window unavailable");
    }
    const unsigned char*read(const Q2FixtureMatrix&m,unsigned format){
        (void)qwen_app::admit_native_system_memory();
        const auto offset=format?m.q2_offset:m.bf16_offset;
        const auto payload=format?460800u:3276800u;
        const auto bytes=(payload+16383)&~std::size_t(16383);
        check(offset%16384==0&&offset+bytes<=q2_fixture_pack_bytes,"Q2 sample read bounds differ");
        stage("expert_q2_read_before_native_call");const auto got=pread(fd,scratch,bytes,static_cast<off_t>(offset));
        stage("expert_q2_read_native_call_returned");++reads;physical_bytes+=bytes;
        check(got==static_cast<ssize_t>(bytes)&&identity(fd)==original,"Q2 sample read or identity failed; backing retained");
        return static_cast<const unsigned char*>(scratch);
    }
    void verify(const Q2FixtureMatrix&m,unsigned format){
        check(hash(scratch,format?460800:3276800)==(format?m.q2_sha256:m.bf16_sha256),"Q2 sample payload digest differs");
    }
    void close_completed(){check(identity(fd)==original&&close(fd)==0,"Q2 sample descriptor retirement failed");fd=-1;free(scratch);scratch=nullptr;}
};
struct Fixture {
    ggml_backend_t backend=nullptr;ggml_context*ctx=nullptr;ggml_backend_buffer_t buffer=nullptr;
    std::array<ggml_cgraph*,2> graph{};std::array<ggml_tensor*,2> weights{},outputs{};
    ggml_tensor *input=nullptr,*ids=nullptr,*canary=nullptr;
    std::array<std::vector<double>,2> expected;
    std::array<unsigned,3> matrices{};std::vector<std::int32_t> selected;
    unsigned columns,rows,width,input_experts;
    void(*checkpoint)();void(*stage)(const char*);Clock::time_point deadline;
    double maximum_error=0;
    Fixture(unsigned group,unsigned w,Pack&pack,void(*c)(),void(*s)(const char*),Clock::time_point d):
        width(w),checkpoint(c),stage(s),deadline(d){
        for(unsigned i=0;i<3;++i)matrices[i]=q2_fixture_groups[group][i];
        const auto&m=q2_fixture_matrices[matrices[0]];columns=m.columns;rows=m.rows;input_experts=columns==640?10:1;
        backend=ggml_backend_vk_init(0);check(backend,"Q2 fixture backend unavailable");
        ggml_init_params p{};p.no_alloc=true;p.mem_size=64*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(32,false);
        ctx=ggml_init(p);check(ctx,"Q2 fixture CPU metadata unavailable");
        input=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,columns,input_experts,width);
        ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,width);
        canary=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);ggml_set_input(canary);ggml_set_output(canary);
        for(unsigned format=0;format<2;++format){
            weights[format]=ggml_new_tensor_3d(ctx,format?GGML_TYPE_Q2_0:GGML_TYPE_BF16,columns,rows,10);
            graph[format]=ggml_new_graph_custom(ctx,32,false);
            outputs[format]=ggml_mul_mat_id(ctx,weights[format],input,ids);ggml_set_output(outputs[format]);
            ggml_build_forward_expand(graph[format],outputs[format]);
        }
        buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);check(buffer,"Q2 fixture device allocation failed");
        std::array<float,128> guard;guard.fill(42.125f);ggml_backend_tensor_set(canary,guard.data(),0,sizeof(guard));
        const unsigned positions[3]={0,4,9};selected.resize(10*width);
        for(unsigned v=0;v<width;++v)for(unsigned e=0;e<10;++e)selected[v*10+e]=positions[(e+v)%3];
        ggml_backend_tensor_set(ids,selected.data(),0,selected.size()*4);
        std::vector<float>x(std::size_t(columns)*input_experts*width);
        for(unsigned v=0;v<width;++v)for(unsigned e=0;e<input_experts;++e)for(unsigned col=0;col<columns;++col)
            x[(std::size_t(v)*input_experts+e)*columns+col]=x_value(col,v,e);
        ggml_backend_tensor_set(input,x.data(),0,x.size()*4);ggml_backend_synchronize(backend);checkpoint();
        // Group exact decoded weights by the deterministic 13-column input
        // period. This retains an independent F64 dot-product reference while
        // avoiding redundant complete weight scans for every selected ID.
        for(unsigned format=0;format<2;++format){
            std::vector<double>sums(std::size_t(3)*rows*13,0.0);
            for(unsigned expert=0;expert<3;++expert){
                const auto&source=q2_fixture_matrices[matrices[expert]];const auto*raw=pack.read(source,format);pack.verify(source,format);
                for(unsigned row=0;row<rows;++row)for(unsigned col=0;col<columns;++col){
                    const auto at=std::size_t(row)*columns+col;
                    const float weight=format?q2(raw,at):bf16(raw+2*at);
                    check(std::isfinite(weight),"Q2 fixture decoded weight is nonfinite");
                    sums[(std::size_t(expert)*rows+row)*13+col%13]+=double(weight);
                }
            }
            expected[format].resize(std::size_t(rows)*10*width);
            for(unsigned v=0;v<width;++v)for(unsigned e=0;e<10;++e)for(unsigned row=0;row<rows;++row){
                double sum=0;const unsigned which=(e+v)%3;
                for(unsigned residue=0;residue<13;++residue)sum+=sums[(std::size_t(which)*rows+row)*13+residue]*double(x_value(residue,v,input_experts==1?0:e));
                expected[format][(std::size_t(v)*10+e)*rows+row]=sum;
            }
        }
    }
    double load(Pack&pack,unsigned format){
        const unsigned slots[3]={0,4,9};double total=0;
        for(unsigned i=0;i<3;++i){
            const auto&m=q2_fixture_matrices[matrices[i]];const auto begin=Clock::now();const auto*raw=pack.read(m,format);
            const auto bytes=format?460800u:3276800u;
            ggml_backend_tensor_set(weights[format],raw,slots[i]*weights[format]->nb[2],bytes);
            ggml_backend_synchronize(backend);checkpoint();total+=elapsed(begin);
            pack.verify(m,format); // Complete payload verification is outside timed delivery.
        }
        return total;
    }
    double compute(unsigned format){
        check(Clock::now()<deadline&&graphs<400,"Q2 fixture finite graph/deadline bound exhausted");
        (void)qwen_app::admit_native_system_memory();stage("expert_q2_graph_before_native_call");const auto begin=Clock::now();
        check(ggml_backend_graph_compute(backend,graph[format])==GGML_STATUS_SUCCESS,"Q2 fixture GPU completion failed; owner retained");
        ggml_backend_synchronize(backend);checkpoint();++graphs;const auto us=elapsed(begin);
        stage("expert_q2_graph_positive_completion");check(std::isfinite(us)&&us>0,"Q2 fixture clock did not advance");return us;
    }
    void verify(unsigned format){
        std::vector<float>actual(expected[format].size());ggml_backend_tensor_get(outputs[format],actual.data(),0,actual.size()*4);
        for(std::size_t i=0;i<actual.size();++i){
            const auto difference=std::abs(double(actual[i])-expected[format][i]);
            if(!std::isfinite(actual[i])||difference>1e-5+2e-4*std::abs(expected[format][i]))
                throw std::runtime_error("Expert fixture GPU/F64 mismatch "+Json({{"format",format?"Q2_0":"BF16"},
                    {"columns",columns},{"rows",rows},{"width",width},{"output_index",i},
                    {"actual",actual[i]},{"reference",expected[format][i]},{"absolute_error",difference},
                    {"completed_graphs",graphs}}).dump());
            maximum_error=std::max(maximum_error,difference);
        }
        std::array<float,128>guard;ggml_backend_tensor_get(canary,guard.data(),0,sizeof(guard));
        check(std::all_of(guard.begin(),guard.end(),[](float x){return x==42.125f;}),"Q2 fixture device canary changed");
    }
    Json measure(Pack&pack,unsigned group){
        for(unsigned i=0;i<4;++i){load(pack,i%2);compute(i%2);verify(i%2);}
        Json arms=Json::array();
        for(unsigned arm=0;arm<4;++arm){const unsigned format=arm==1||arm==2?1:0;Json samples=Json::array();
            for(unsigned i=0;i<2;++i){const auto delivery=load(pack,format),kernel=compute(format);verify(format);
                samples.push_back({{"delivery_us",delivery},{"compute_us",kernel},{"delivery_and_compute_us",delivery+kernel}});}
            arms.push_back({{"format",format?"Q2_0":"BF16"},{"samples",samples}});
        }
        ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);buffer=nullptr;
        ggml_free(ctx);ctx=nullptr;ggml_backend_free(backend);backend=nullptr;checkpoint();
        return {{"group",group},{"width",width},{"columns",columns},{"rows",rows},{"selected_Experts",10},{"unique_original_Experts",3},
            {"arms",arms},{"reference","F64_of_each_format"},{"maximum_absolute_GPU_reference_error",maximum_error},
            {"GPU_graphs",12},{"all_outputs_and_canaries_passed",true},{"backends_positively_retired",true}};
    }
};
}
namespace qwen_app {
nlohmann::json run_expert_q2_fixture(void(*checkpoint)(),void(*stage)(const char*)){
    check(checkpoint&&stage&&!graphs,"One fresh Q2 Expert fixture required");
    Pack pack(stage);const auto deadline=Clock::now()+std::chrono::seconds(240);Json cases=Json::array();
    for(unsigned group=0;group<9;++group)for(unsigned width:{1u,2u,4u}){
        Fixture fixture(group,width,pack,checkpoint,stage,deadline);cases.push_back(fixture.measure(pack,group));
    }
    const auto reads=pack.reads,bytes=pack.physical_bytes;pack.close_completed();
    return {{"schema","ps5-qwen-expert-q2-fixture-result-v1"},{"completed",true},{"cases",cases},{"GPU_graphs",graphs},
        {"maximum_GPU_graphs",400},{"model_loaded",false},{"component_fixture_not_model_speed",true},
        {"all_outputs_reference_valid",true},{"all_backends_positively_retired",true},{"Direct_reads",reads},{"physical_read_bytes",bytes},
        {"complete_pack_SHA256_verified",true},{"source_descriptor_and_scratch_retired",true},
        {"quantized_activations",false},{"timed_digest_work",false},{"automatic_retries",0}};
}
}
