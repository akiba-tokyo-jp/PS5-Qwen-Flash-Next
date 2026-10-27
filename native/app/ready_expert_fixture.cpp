// SPDX-License-Identifier: MIT
#include "ready_expert_fixture.h"
#include "ready_expert_native.h"
#include "split_bank_admission.h"
#include "split_bank_route.h"
#include "indexed_vector.h"
#include "system_memory.h"
#include "native_gpu.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
}
namespace qwen_app {namespace {
using Json=nlohmann::json;
using Identity=std::array<std::uint64_t,10>;
void check(bool good,const char *message){if(!good)throw std::runtime_error(message);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
Identity identity(int fd) {
    struct stat s{};check(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&!fstat(fd,&s)&&S_ISREG(s.st_mode)&&
        s.st_ino&&s.st_size==split_bank_pack_bytes&&!(s.st_mode&0022),"Ready fixture requires its sealed original Direct descriptor");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
std::string digest(const void *data,std::size_t bytes) {
    sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char *>(data),bytes);
    unsigned char raw[32];sha256_final(&h,raw);std::string out;
    for(const auto b:raw){out+="0123456789abcdef"[b>>4];out+="0123456789abcdef"[b&15];}return out;
}
float weight(const unsigned char *p,std::size_t index) {
    std::uint16_t half;std::memcpy(&half,p+index*2,2);const auto wide=std::uint32_t(half)<<16;
    float f;std::memcpy(&f,&wide,4);check(std::isfinite(f),"Ready original BF16 weight is nonfinite");return f;
}
struct Run {
    ggml_backend_t backend;int fd;Identity source;SplitBankBackings banks;SplitBankRoots roots;
    std::array<ReadyFixtureMatrix,6> matrices;
    ggml_context *context=nullptr;ReadyExpertNativeGraphs graphs;ReadyExpertExecution execution;ReadyExpertWave *wave=nullptr;
    std::array<ReadyExpertGraphInputs,2> inputs{};ggml_tensor *output=nullptr,*activation=nullptr,*contributions=nullptr;
    std::array<std::array<unsigned char *,3>,2> bases{};
    std::vector<float> x,actual,actual_contributions;std::array<std::array<float,5>,2> weights{};
    Json reads=Json::array(),submissions=Json::array();
    std::uint64_t operation=0,prior,plan;unsigned returned_reads=0;
    std::chrono::steady_clock::time_point deadline=std::chrono::steady_clock::now()+std::chrono::seconds(60);
    Run(ggml_backend_t b,int f,const SplitBankBackings &bs,const SplitBankRoots &rs,
        const std::array<ReadyFixtureMatrix,6>&ms,std::uint64_t p,std::uint64_t sequence):
        backend(b),fd(f),source(identity(f)),banks(bs),roots(rs),matrices(ms),prior(p),plan(sequence){}
    void bounded(){check(std::chrono::steady_clock::now()<deadline,"Ready numerical finite deadline exceeded; owners retained");}
    void verify(unsigned group,unsigned role) {
        const auto &m=matrices[role*2+group];auto *base=bases[group][role];
        check(digest(base,padded_bank_stride)==m.envelope&&digest(base+m.residue,bank_expert_bytes)==m.raw,
            "Ready original envelope or BF16 matrix differs");
        const bool before=group!=0,after=group==0;
        for(unsigned j=0;j<bank_read_alignment;++j) {
            if(before)check(base[-int(j)-1]==0xa7,"Ready preceding canary differs");
            if(after)check(base[padded_bank_stride+j]==0xa7,"Ready following canary differs");
        }
    }
    void prepare() {
        const auto owners=validate_split_bank_backings(banks);
        std::array<std::int32_t,10> selected{};std::array<unsigned,10> slots{};
        for(unsigned i=0;i<10;++i){selected[i]=i%2?257:0;slots[i]=i%2?52:0;}
        wave=new ReadyExpertWave(selected,slots,owners,0,1,plan,prior);
        ggml_init_params params{};params.no_alloc=true;
        params.mem_size=ggml_tensor_overhead()*600+8*ggml_graph_overhead_custom(256,false);
        context=ggml_init(params);check(context,"Ready graph metadata allocation refused");
        activation=ggml_new_tensor_2d(context,GGML_TYPE_F32,2560,1);ggml_set_input(activation);
        contributions=ggml_new_tensor_2d(context,GGML_TYPE_F32,2560,10);ggml_set_input(contributions);
        output=ggml_new_tensor_2d(context,GGML_TYPE_F32,2560,1);ggml_set_output(output);
        for(unsigned group=0;group<2;++group) {
            auto &a=inputs[group];a.activation=activation;a.contributions=contributions;a.count=5;
            std::array<ggml_tensor *,3> views{};
            for(unsigned role=0;role<3;++role) {
                const auto &m=matrices[role*2+group];const auto slot=split_padded_slot(group?52:0,m.residue,banks[group][role].descriptor_alignment);
                bases[group][role]=static_cast<unsigned char *>(banks[group][role].destination)+slot.envelope.aligned_write_offset;
                const unsigned k=role==2?640:2560,n=role==2?2560:640;
                views[role]=ggml_view_3d(context,roots[group][role],k,n,split_bank_active[group],k*2,padded_bank_stride,m.residue);
            }
            a.gate=views[0];a.up=views[1];a.down=views[2];
            a.slots=ggml_new_tensor_2d(context,GGML_TYPE_I32,5,1);ggml_set_input(a.slots);
            a.weights=ggml_new_tensor_2d(context,GGML_TYPE_F32,1,5);ggml_set_input(a.weights);
            for(unsigned i=0;i<5;++i){a.original_ordinals[i]=i*2+group;weights[group][i]=float(a.original_ordinals[i]+1)/256.0f;}
        }
        graphs.prepare(context,backend,inputs,output,prior,qwen_native_stage,qwen_native_driver_checkpoint);graphs.allocate_workspace();
        // Check the actual graph nodes after backend buffer assignment. A host
        // metadata graph or a matrix fallback does not qualify this route.
        for(const auto phase:{ReadyGraphPhase::complete_serial,ReadyGraphPhase::first_group,ReadyGraphPhase::second_group}) {
            auto *g=graphs.graph(phase);unsigned indexed=0;
            for(int i=0;i<ggml_graph_n_nodes(g);++i) {
                const auto *t=ggml_graph_node(g,i);
                if(t->op==GGML_OP_MUL_MAT_ID){++indexed;check(split_bank_indexed_vector_layout(t,banks[0][0].descriptor_alignment),"Ready partial indexed route is not eligible");}
            }
            check(indexed==(phase==ReadyGraphPhase::complete_serial?6u:3u),"Ready graph indexed projection count differs");
        }
        x.resize(2560);actual.resize(2560);actual_contributions.resize(25600);
        for(unsigned i=0;i<2560;++i)x[i]=float(int(i%13)-6)/3.0f;
        ggml_backend_tensor_set(activation,x.data(),0,x.size()*4);
        std::vector<float> poison(25600,std::numeric_limits<float>::quiet_NaN());
        ggml_backend_tensor_set(contributions,poison.data(),0,poison.size()*4);
        ggml_backend_tensor_set(output,poison.data(),0,actual.size()*4);
        for(unsigned group=0;group<2;++group) {
            std::array<std::int32_t,5> slots{};slots.fill(group?26:0);
            ggml_backend_tensor_set(inputs[group].slots,slots.data(),0,sizeof(slots));
            ggml_backend_tensor_set(inputs[group].weights,weights[group].data(),0,sizeof(weights[group]));
        }
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
    }
    static void fill(ReadyExpertWave &wave,unsigned group,void *opaque) {
        auto &r=*static_cast<Run *>(opaque);
        for(unsigned role=0;role<3;++role) {
            r.bounded();
            // First-use shader loading can call the mutable admission gate on
            // the GPU producer. The source thread therefore observes the same
            // operational predicate without touching that shared gate state.
            check(qualified_system_headroom(observe_native_system_memory())>=(256u<<20),"Ready source cannot retain original Flexible/kernel reserves");
            const auto &m=r.matrices[role*2+group];
            check(identity(r.fd)==r.source,"Ready source changed before read");
            wave.begin_role_read(group?52:0,role,++r.operation);
            const auto label="ready_numerical_read_before plan="+std::to_string(r.plan)+" group="+std::to_string(group)+
                " role="+std::to_string(role)+" offset="+std::to_string(m.offset)+" bytes="+std::to_string(padded_bank_stride);
            qwen_native_stage(label.c_str());const auto start=now();
            const auto got=pread(r.fd,r.bases[group][role],padded_bank_stride,m.offset);const auto end=now();
            qwen_native_stage("ready_numerical_Direct_read_returned");
            check(got==static_cast<ssize_t>(padded_bank_stride)&&identity(r.fd)==r.source,"Ready Direct read returned incomplete bytes or identity");
            r.verify(group,role);wave.complete_role_read(r.plan,r.operation,bank_expert_bytes,true,true);++r.returned_reads;
            r.reads.push_back({{"group",group},{"role",role},{"offset",m.offset},{"bytes",padded_bank_stride},
                {"begin_ns",start},{"end_ns",end},{"original_raw_sha256",m.raw},{"original_envelope_sha256",m.envelope}});
        }
    }
    static bool dispatch(ReadyGraphPhase phase,std::uint64_t epoch,const std::array<bool,10>&selected,void *opaque) {
        auto &r=*static_cast<Run *>(opaque);
        const auto label="ready_numerical_dispatch_before plan="+std::to_string(r.plan)+" phase="+std::to_string(static_cast<unsigned>(phase))+" epoch="+std::to_string(epoch);
        qwen_native_stage(label.c_str());const auto start=now();const auto op=r.graphs.operations();
        const bool complete=op.dispatch_and_complete(phase,epoch,selected,op.opaque);const auto end=now();
        r.submissions.push_back({{"phase",static_cast<unsigned>(phase)},{"epoch",epoch},{"begin_ns",start},{"end_ns",end},
            {"positive_synchronized_driver_completion",complete}});return complete;
    }
    std::vector<double> reference() {
        std::array<std::vector<double>,2> values;
        for(unsigned group=0;group<2;++group) {
            std::vector<double> activated(640);values[group].resize(2560);
            for(unsigned row=0;row<640;++row) {
                double gate=0,up=0;
                for(unsigned col=0;col<2560;++col) {
                    gate+=double(weight(bases[group][0]+matrices[group].residue,std::size_t(row)*2560+col))*x[col];
                    up+=double(weight(bases[group][1]+matrices[2+group].residue,std::size_t(row)*2560+col))*x[col];
                }
                activated[row]=(gate/(1+std::exp(-gate)))*up;
            }
            for(unsigned row=0;row<2560;++row)for(unsigned col=0;col<640;++col)
                values[group][row]+=double(weight(bases[group][2]+matrices[4+group].residue,std::size_t(row)*640+col))*activated[col];
        }
        std::vector<double> ref(2560);
        for(unsigned i=0;i<10;++i)for(unsigned row=0;row<2560;++row)ref[row]+=values[i%2][row]*double(weights[i%2][i/2]);
        return ref;
    }
};
} // namespace
Json run_ready_expert_fixture(ggml_backend_t backend,int fd,const SplitBankBackings &banks,const SplitBankRoots &roots,
        const std::array<ReadyFixtureMatrix,6>&matrices,std::uint64_t prior) {
    check(prior==12,"Ready numerical fixture requires twelve positively completed backing graphs");
    const std::array<ReadyExecutionMode,6> modes{{ReadyExecutionMode::one_graph_serial,ReadyExecutionMode::split_serial,
        ReadyExecutionMode::split_overlap,ReadyExecutionMode::split_overlap,ReadyExecutionMode::split_serial,ReadyExecutionMode::one_graph_serial}};
    Json cases=Json::array();std::vector<float> control,control_contributions;std::vector<double> ref;
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(120);
    std::uint64_t read_calls=0,graph_calls=0;
    for(unsigned i=0;i<modes.size();++i) {
        // Explicit heap owners survive all exceptions. No joinable-thread,
        // native graph, source or shared-bank owner unwinds on unknown work.
        check(std::chrono::steady_clock::now()<deadline,"Ready numerical cohort deadline exceeded before new work");
        auto *r=new Run(backend,fd,banks,roots,matrices,prior,i+1);r->deadline=std::min(r->deadline,deadline);r->prepare();
        const auto paths=gpu_path_stats();const auto start=now();
        r->execution.run(*r->wave,modes[i],Run::fill,r,{Run::dispatch,r},prior,r->deadline);
        const auto end=now();const auto completed=gpu_path_stats();
        check(completed.bf16_vector==paths.bf16_vector+6&&completed.bf16_matrix==paths.bf16_matrix,
            "Ready partial graph did not use exactly six original BF16 vector projections");
        ggml_backend_tensor_get(r->output,r->actual.data(),0,r->actual.size()*4);
        ggml_backend_tensor_get(r->contributions,r->actual_contributions.data(),0,r->actual_contributions.size()*4);
        if(!i){control=r->actual;control_contributions=r->actual_contributions;ref=r->reference();}r->bounded();
        check(std::any_of(ref.begin(),ref.end(),[](double v){return std::isfinite(v)&&std::abs(v)>1e-4;}),"Ready original reference has no material nonzero output");
        for(const auto value:r->actual_contributions)check(std::isfinite(value),"Ready original contribution remains unwritten or nonfinite");
        double maximum=0,normalized=0;
        for(unsigned row=0;row<2560;++row) {
            const auto error=std::abs(double(r->actual[row])-ref[row]),tolerance=1e-5+1e-5*std::abs(ref[row]);
            check(std::isfinite(r->actual[row])&&error<=tolerance,"Ready complete FFN F64 reference differs");
            maximum=std::max(maximum,error);normalized=std::max(normalized,error/tolerance);
        }
        check(!std::memcmp(control.data(),r->actual.data(),control.size()*4),"Ready serial/split original-order F32 outputs differ in bits");
        check(!std::memcmp(control_contributions.data(),r->actual_contributions.data(),control_contributions.size()*4),"Ready serial/split F32 contributions differ in bits");
        for(unsigned group=0;group<2;++group)for(unsigned role=0;role<3;++role)r->verify(group,role);
        const auto s=r->wave->snapshot();const auto e=r->execution.snapshot();const auto source=r->execution.source_snapshot();
        check(r->returned_reads==6&&s.unique_experts==2&&s.role_returns==6&&s.retired&&source.joined&&e.completed,
            "Ready finite numerical cohort lacks returned source or graph completion");
        cases.push_back({{"mode",static_cast<unsigned>(modes[i])},{"plan_epoch",i+1},{"prior_completed_GPU_epoch",prior},
            {"last_completed_GPU_epoch",e.last_completed_GPU_epoch},{"read_calls",r->returned_reads},{"GPU_graphs",e.completed_graphs},
            {"source_to_output_ns",end-start},{"reads",r->reads},{"submissions",r->submissions},
            {"output_F32_sha256",digest(r->actual.data(),r->actual.size()*4)},
            {"contribution_F32_sha256",digest(r->actual_contributions.data(),r->actual_contributions.size()*4)},{"maximum_absolute_error",maximum},
            {"maximum_normalized_error",normalized},{"F64_reference_passed",true},{"same_F32_outputs_bit_exact",true},
            {"all_original_envelopes_and_canaries_intact",true},{"source_joined",true},{"wave_retired",true}});
        read_calls+=r->returned_reads;graph_calls+=e.completed_graphs;prior=e.last_completed_GPU_epoch;
        r->graphs.close_completed(r->execution,*r->wave);ggml_free(r->context);delete r->wave;delete r;
    }
    check(read_calls==36&&graph_calls==14,"Ready numerical cohort counts differ");
    return {{"schema","ps5-qwen-ready-numerical-result-v1"},{"cases",cases},{"unique_original_experts",2},
        {"original_contributions",10},{"source_IO_depth",1},{"source_coordinator_workers",1},{"Direct_read_calls",read_calls},
        {"GPU_graphs",graph_calls},{"initial_positive_graph_epoch",12},{"final_positive_graph_epoch",prior},
        {"reference_absolute_tolerance",1e-5},{"reference_relative_tolerance",1e-5},{"representative_speed_test",false},
        {"physical_GPU_timestamp_overlap_qualified",false},{"model_speed_qualified",false},{"production_adopted",false}};
}
}
