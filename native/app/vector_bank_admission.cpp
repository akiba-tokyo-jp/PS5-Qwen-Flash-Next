// SPDX-License-Identifier: MIT
#include "vector_bank_admission.h"
#include "vectored_source_batch.h"
#include "batch_io_journal.h"
#include "padded_bank_bridge.h"
#include "padded_bank_layout.h"
#include "padded_bank.h"
#include "indexed_vector.h"
#include "direct_integrity.h"
#include "device_buffer_budget.h"
#include "mapped_source_bridge.h"
#include "mapped_source.h"
#include "system_memory.h"
#include "native_gpu.h"
#include "profile_clock.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "llama.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <fcntl.h>
#include <mutex>
#include <sys/stat.h>
#include <sys/uio.h>
#include <unistd.h>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
void qwen_native_halt(const char *);
void qwen_native_driver_checkpoint();
}
namespace qwen_app { namespace {
using Json=nlohmann::json;
constexpr std::array<std::int32_t,10> selected{{52,0,26,0,50,2,52,13,25,42}};
constexpr std::array<unsigned,2> slots{{0,52}};
using Identity=std::array<std::uint64_t,10>;
void check(bool ok,const char *message){if(!ok)throw std::runtime_error(message);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();}
Identity identity(int fd) {
    struct stat s{};check(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_ino&&s.st_size>0,"Vector bank source identity refused");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
std::string digest(const void *data,std::size_t size) {
    sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char *>(data),size);unsigned char raw[32];sha256_final(&h,raw);
    std::string result;for(auto value:raw){result+="0123456789abcdef"[value>>4];result+="0123456789abcdef"[value&15];}return result;
}
struct Fixture {
    const Json &policy;Json batches=Json::array();
    const bool compact;
    BatchIOJournal events;
    explicit Fixture(const Json &p):policy(p),compact(p.value("journal_style",std::string())=="batch-memory-events-v1"){}
    std::array<int,2> fds{{-1,-1}};std::array<Identity,2> source{};
    std::array<ggml_tensor *,3> banks{},inputs{},ids{};
    std::array<std::array<ggml_tensor *,3>,13> outputs{};
    std::array<std::array<ggml_cgraph *,3>,13> graphs{};
    std::array<std::array<std::vector<float>,3>,13> references;
    std::array<unsigned char *,3> mapped{};std::array<std::size_t,3> alignments{};
    ggml_backend_t backend=nullptr;std::mutex journal;
    VectoredSourceBatch *reader=nullptr;std::thread::id producer;
    std::uint64_t next_id=0,started=0;std::atomic<unsigned> scalar{0},vector{0};
    unsigned GPU_graphs=0,exact_matrices=0;std::uint64_t non_BF16_inputs=0;double maximum_error=0;
    void bounded() {check(now()-started<120000000000ull,"Vector bank finite deadline exceeded; backing retained");}
    static std::int64_t read_at(void *opaque,const VectoredRead &r) {
        auto &f=*static_cast<Fixture *>(opaque);
        {std::lock_guard<std::mutex> lock(f.journal);(void)admit_native_system_memory();
         if(!f.compact){const auto text="vector_bank_IO_before id="+std::to_string(r.id)+" bytes="+std::to_string(r.bytes());qwen_native_stage(text.c_str());}}
        const auto begin=now();
        if(f.compact)f.events.begin(r.id,r.offset,r.bytes(),begin);
        ssize_t got;
        if(r.count==1){got=pread(r.fd,r.destinations[0].data,r.destinations[0].bytes,r.offset);}
        else{struct iovec v[3];for(unsigned i=0;i<3;++i){v[i].iov_base=r.destinations[i].data;v[i].iov_len=r.destinations[i].bytes;}
             got=preadv(r.fd,v,3,r.offset);}
        const auto end=now();
        if(r.count==1)++f.scalar;else ++f.vector;
        if(f.compact)f.events.returned(r.id,got,end);
        else{std::lock_guard<std::mutex> lock(f.journal);
         const auto text="vector_bank_IO_returned id="+std::to_string(r.id)+" result="+std::to_string(got)+" read_ns="+std::to_string(now()-begin);qwen_native_stage(text.c_str());}
        return got;
    }
    void declare_events(unsigned group,unsigned mode) {
        const auto &items=policy.at("groups").at(group).at("matrices");
        std::array<BatchIOPlan,6> plans{};const unsigned count=mode?2:6;
        std::string text="vector_bank_IO_batch_plan group="+std::to_string(group)+" mode="+std::to_string(mode)+" events=";
        for(unsigned i=0;i<count;++i) {
            plans[i]={next_id+1+i,items.at(i).at("offset").get<std::uint64_t>(),(mode?3u:1u)*padded_bank_stride};
            if(i)text+=",";
            text+=std::to_string(plans[i].id)+":"+std::to_string(plans[i].offset)+":"+std::to_string(plans[i].bytes);
        }
        events.prepare(plans.data(),count);check(text.size()<=1024,"Declared compact I/O plan exceeds its durable journal");
        qwen_native_stage(text.c_str());events.admit_durable();
    }
    BatchIOSnapshot persist_returned_events() {
        const auto snapshot=events.snapshot();
        std::string text="vector_bank_IO_batch_returned count="+std::to_string(snapshot.count)+
            " uncertain="+std::to_string(snapshot.uncertain)+" events=";
        for(unsigned i=0;i<snapshot.count;++i) {
            const auto &e=snapshot.events[i];if(i)text+=",";
            text+=std::to_string(e.plan.id)+":"+std::to_string(e.plan.offset)+":"+std::to_string(e.plan.bytes)+":"+
                std::to_string(e.begun)+":"+std::to_string(e.returned)+":"+std::to_string(e.result)+":"+
                std::to_string(e.begin_ns)+":"+std::to_string(e.end_ns);
        }
        check(text.size()<=1024,"Returned compact I/O events exceed their durable journal");qwen_native_stage(text.c_str());
        return snapshot;
    }
    void read_group(const Json &group,unsigned mode) {
        const auto p=group.at("pack").get<unsigned>();check(identity(fds[p])==source[p],"Vector source changed before delivery");
        const auto &items=group.at("matrices");
        for(unsigned wave=0;wave<(mode?1u:3u);++wave) {
            std::array<VectoredRead,2> requests{};
            for(unsigned e=0;e<2;++e) {
                auto &r=requests[e];r.fd=fds[p];r.device=source[p][0];r.inode=source[p][1];r.file_bytes=source[p][5];
                r.id=++next_id;r.count=mode?3:1;r.offset=items.at(mode?e:wave*2+e).at("offset");
                for(unsigned j=0;j<r.count;++j) {
                    const unsigned role=mode?j:wave;
                    r.destinations[j]={mapped[role]+slots[e]*padded_bank_stride,std::uint32_t(padded_bank_stride)};
                }
            }
            reader->read(requests.data(),2);
        }
        check(identity(fds[p])==source[p],"Vector source changed after returned delivery");
    }
    void exact_and_compute(unsigned group_index,const Json &group) {
        const auto &items=group.at("matrices");
        for(unsigned role=0;role<3;++role) {
            const unsigned columns=role==2?640:2560,rows=role==2?2560:640;
            std::vector<float> input(std::size_t(columns)*10),actual(std::size_t(rows)*10);
            std::vector<double> expected(actual.size());
            for(unsigned v=0;v<10;++v)for(unsigned col=0;col<columns;++col) {
                const auto value=float(int(col%13)-6)/12288.0f;input[std::size_t(v)*columns+col]=value;
                if(ggml_bf16_to_fp32(ggml_fp32_to_bf16(value))!=value)++non_BF16_inputs;
            }
            // Recreate views per returned group; their offsets are immutable during the graph.
            for(unsigned e=0;e<2;++e) {
                const auto &item=items.at(role*2+e);const auto residue=item.at("residue").get<unsigned>();
                const auto *base=mapped[role]+slots[e]*padded_bank_stride;
                check(digest(base,padded_bank_stride)==item.at("envelope_sha256")&&
                    digest(base+residue,bank_expert_bytes)==item.at("raw_sha256"),"Vector bank original BF16 bytes differ");
                ++exact_matrices;
                // Slot-boundary canaries surround both real read envelopes.
                if(slots[e])for(unsigned j=0;j<bank_read_alignment;++j)
                    check(base[-int(j)-1]==0xa7,"Vector bank preceding canary differs");
                for(unsigned j=0;j<bank_read_alignment;++j)
                    check(base[padded_bank_stride+j]==0xa7,"Vector bank following canary differs");
                for(unsigned row=0;row<rows;++row) {
                    double sum=0;for(unsigned col=0;col<columns;++col) {
                        std::uint16_t bits;std::memcpy(&bits,base+residue+(std::size_t(row)*columns+col)*2,2);
                        std::uint32_t wide=std::uint32_t(bits)<<16;float weight;std::memcpy(&weight,&wide,4);
                        check(std::isfinite(weight),"Vector bank reference BF16 is nonfinite");sum+=double(weight)*input[col];
                    }
                    for(unsigned v=0;v<10;++v)if(selected[v]==int(slots[e]))expected[std::size_t(v)*rows+row]=sum;
                }
            }
            ggml_backend_tensor_set(inputs[role],input.data(),0,input.size()*4);
            bounded();(void)admit_native_system_memory();
            const auto before=gpu_path_stats();
            check(ggml_backend_graph_compute(backend,graphs[group_index][role])==GGML_STATUS_SUCCESS,"Vector bank GPU completion refused; backing retained");
            ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();++GPU_graphs;
            const auto after=gpu_path_stats();check(after.bf16_vector-before.bf16_vector==1&&after.bf16_matrix==before.bf16_matrix,"Vector bank indexed path changed");
            ggml_backend_tensor_get(outputs[group_index][role],actual.data(),0,actual.size()*4);
            for(std::size_t i=0;i<actual.size();++i) {
                const auto error=std::abs(double(actual[i])-expected[i]);
                check(std::isfinite(actual[i])&&error<=1e-5+1e-5*std::abs(expected[i]),"Vector bank F64 reference differs");
                maximum_error=std::max(maximum_error,error);
            }
            auto &reference=references[group_index][role];
            if(reference.empty())reference=actual;
            else check(reference.size()==actual.size()&&!std::memcmp(reference.data(),actual.data(),actual.size()*4),"Scalar/vector F32 GPU outputs differ in bits");
            for(unsigned e=0;e<2;++e) {
                const auto *base=mapped[role]+slots[e]*padded_bank_stride;
                if(slots[e])for(unsigned j=0;j<bank_read_alignment;++j)check(base[-int(j)-1]==0xa7,"Post-GPU vector bank preceding canary differs");
                for(unsigned j=0;j<bank_read_alignment;++j)check(base[padded_bank_stride+j]==0xa7,"Post-GPU vector bank following canary differs");
            }
        }
    }
    void run() {
        check(std::this_thread::get_id()==producer,"Vector bank requires the original GPU producer");
        qwen_native_stage("vector_bank_three_owned_aligned_bank_leases_admitted");
        // Mutate no bank until every real owner and aligned destination has
        // passed. Unselected expert planes are zero; adjacent pages are canaries.
        for(unsigned role=0;role<3;++role) {
            std::memset(mapped[role],0,padded_bank_tensor_bytes);
            for(unsigned e=0;e<2;++e) {
                auto *base=mapped[role]+slots[e]*padded_bank_stride;
                if(slots[e])std::memset(base-bank_read_alignment,0xa7,bank_read_alignment);
                std::memset(base+padded_bank_stride,0xa7,bank_read_alignment);
            }
        }
        reader=new VectoredSourceBatch(read_at,this);reader->start();
        for(unsigned round=0;round<8;++round)for(unsigned shifted=0;shifted<3;++shifted)for(unsigned order=0;order<2;++order)
            delivery(round,(round+shifted)%3,(round+order)%2,true);
        for(unsigned g=3;g<13;++g)for(unsigned mode=0;mode<2;++mode)delivery(0,g,mode,false);
        reader->stop_completed();delete reader;reader=nullptr;
    }
    void delivery(unsigned round,unsigned group,unsigned mode,bool timed) {
        bounded();(void)admit_native_system_memory();const auto &g=policy.at("groups").at(group);
        const auto &items=g.at("matrices");
        for(unsigned role=0;role<3;++role) {
            // Only completed previous graphs may release these regions for I/O.
            for(unsigned e=0;e<2;++e)std::memset(mapped[role]+slots[e]*padded_bank_stride,0,padded_bank_stride);
            const auto residue0=items.at(role*2).at("residue").get<unsigned>(),residue1=items.at(role*2+1).at("residue").get<unsigned>();
            check(residue0==residue1,"One indexed tensor requires equal expert residues");
        }
        const auto begin=now();if(compact)declare_events(group,mode);
        const auto source_begin=now();
        try{read_group(g,mode);}catch(...) {
            if(compact) {
                if(!reader->completion_known())events.retain_uncertain();
                (void)persist_returned_events();
            }
            throw;
        }
        const auto source_end=now();BatchIOSnapshot snapshot;
        if(compact){snapshot=persist_returned_events();events.finish_after_durable_return();}
        const auto wall=now()-begin;
        check(wall>0,"Vector bank delivery clock refused");
        exact_and_compute(group,g);
        Json batch={{"round",round},{"group",group},{"mode",mode},{"timed",timed},{"delivery_wall_ns",wall},
            {"physical_bytes",6*padded_bank_stride},{"copies",0}};
        if(compact) {
            check(source_end>=source_begin&&source_begin>=begin,"Compact delivery clock regressed");
            batch["source_critical_ns"]=source_end-source_begin;batch["batch_safety_records"]=2;
            batch["source_begin_ns"]=source_begin;batch["source_end_ns"]=source_end;
            batch["io_events"]=Json::array();
            for(unsigned i=0;i<snapshot.count;++i) {
                const auto &e=snapshot.events[i];
                batch["io_events"].push_back({e.plan.id,e.plan.offset,e.plan.bytes,e.begun,e.returned,e.result,e.begin_ns,e.end_ns});
            }
        }
        batches.push_back(std::move(batch));
        qwen_native_stage("vector_bank_batch_exact_GPU_fences_completed");
    }
};
struct Lease {Fixture *fixture;unsigned role;};
int hold_bank(void *data,std::size_t bytes,std::uint64_t flags,std::size_t alignment,void *opaque) {
    const auto lease=*static_cast<Lease *>(opaque);auto &f=*lease.fixture;const auto role=lease.role;
    check(bytes==padded_bank_tensor_bytes&&(flags&7)==7&&reinterpret_cast<std::uintptr_t>(data)%16384==0,"Vector bank real owned mapping refused");
    f.mapped[role]=static_cast<unsigned char *>(data);f.alignments[role]=alignment;
    if(role)check(alignment==f.alignments[0],"Nested vector bank descriptor alignments differ");
    else configure_padded_index_layout(true,alignment);
    for(const auto residue:original_bank_residues)(void)padded_bank_slot(52,residue,bytes,alignment);
    if(role<2){Lease next{&f,role+1};check(ggml_app_vk_probe_owned_bank(f.banks[role+1],hold_bank,&next)==0,"Nested vector bank lease refused");}
    else f.run();
    return 0;
}
} // namespace
Json admit_vector_bank(const Json &policy,const std::string &journal) {
    require_vector_bank_policy(policy,false);const auto &p=policy.at("native_vector_bank_validation");
    for(const auto *name:{"GGML_VK_BOUNDED_STAGING","GGML_VK_DISABLE_ASYNC","GGML_VK_SERIALIZE_SUBMISSIONS","GGML_VK_MAX_NODES_PER_SUBMIT"})
        check(!setenv(name,"1",1),"Vector bank requires the qualified serialized Vulkan policy");
    auto *f=new Fixture(p);f->producer=std::this_thread::get_id();f->started=now();
    for(unsigned i=0;i<2;++i) {
        const auto &pack=p.at("packs").at(i);const auto path=pack.at("path").get<std::string>();
        verify_native_startup_file_direct(path,pack.at("bytes"),pack.at("sha256"),30);
        f->fds[i]=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
        check(f->fds[i]>=0&&(fcntl(f->fds[i],F_GETFL)&O_DIRECT),"Vector bank Direct descriptor refused");
        f->source[i]=identity(f->fds[i]);check(f->source[i][5]==pack.at("bytes"),"Vector bank pack size differs");
    }
    std::vector<SourceFile> sources;
    for(unsigned i=0;i<2;++i)sources.push_back({p.at("packs").at(i).at("path"),f->source[i][5],f->source[i]});
    // Retain the existing source-owner and device-ledger prerequisites. Its
    // 8 MiB CPU window/preflight is charged once and outside both timed arms.
    start_native_model_sources(std::move(sources));
    (void)admit_native_startup_memory();qwen_native_gpu_initialize(journal.c_str());qwen_native_driver_begin();
    llama_backend_init();enforce_native_model_compute_limits();
    f->backend=ggml_backend_vk_init(0);check(f->backend,"Vector bank backend unavailable");
    ggml_init_params params{};params.no_alloc=true;params.mem_size=ggml_tensor_overhead()*90+39*ggml_graph_overhead_custom(16,false);
    auto *ctx=ggml_init(params);check(ctx,"Vector bank metadata allocation refused");
    // GGML allocates root tensors in creation order. Keep the three page-sized
    // bank extents consecutive, ahead of smaller inputs and outputs, so each
    // root retains its 16 KiB Direct-I/O alignment without extra padding/copies.
    for(unsigned role=0;role<3;++role) {
        const unsigned k=role==2?640:2560,n=role==2?2560:640;
        auto *bank=ggml_new_tensor_3d(ctx,GGML_TYPE_BF16,k,n,padded_bank_physical_slots);
        bank->nb[2]=padded_bank_stride;bank->nb[3]=padded_bank_stride*padded_bank_physical_slots;f->banks[role]=bank;
        ggml_set_input(bank);
    }
    for(unsigned role=0;role<3;++role) {
        const unsigned k=role==2?640:2560,n=role==2?2560:640;auto *bank=f->banks[role];
        f->inputs[role]=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,k,10,1);f->ids[role]=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,1);
        ggml_set_input(f->inputs[role]);ggml_set_input(f->ids[role]);
        for(unsigned group=0;group<13;++group) {
            const auto &items=p.at("groups").at(group).at("matrices");
            const auto residue=items.at(role*2).at("residue").get<unsigned>();
            check(residue==items.at(role*2+1).at("residue"),"Vector graph expert residues differ");
            auto *view=ggml_view_3d(ctx,bank,k,n,padded_bank_active_slots,k*2,padded_bank_stride,residue);
            f->outputs[group][role]=ggml_mul_mat_id(ctx,view,f->inputs[role],f->ids[role]);ggml_set_output(f->outputs[group][role]);
            auto *graph=ggml_new_graph_custom(ctx,16,false);ggml_build_forward_expand(graph,f->outputs[group][role]);f->graphs[group][role]=graph;
        }
    }
    auto *buffer=ggml_backend_alloc_ctx_tensors(ctx,f->backend);check(buffer,"Vector bank real GPU allocation refused");
    check(ggml_backend_buffer_get_size(buffer)<=536870912,"Vector bank allocated payload exceeds the unchanged cache cap");
    ggml_backend_synchronize(f->backend);qwen_native_driver_checkpoint();
    for(unsigned role=0;role<3;++role)ggml_backend_tensor_set(f->ids[role],selected.data(),0,sizeof(selected));
    configure_bf16_indexed_vector(true);set_bf16_indexed_vector_scope(true);
    Lease first{f,0};check(ggml_app_vk_probe_owned_bank(f->banks[0],hold_bank,&first)==0,"All three vector bank leases did not return");
    set_bf16_indexed_vector_scope(false);configure_bf16_indexed_vector(false);configure_padded_index_layout(false);
    for(unsigned i=0;i<2;++i){check(identity(f->fds[i])==f->source[i],"Vector pack changed before close");check(!close(f->fds[i]),"Vector pack close refused");f->fds[i]=-1;}
    ggml_backend_synchronize(f->backend);qwen_native_driver_checkpoint();
    ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_backend_free(f->backend);qwen_native_driver_checkpoint();
    const auto ledger=native_model_device_stats();check(!ledger.live,"Vector bank device buffers remain live");
    stop_native_model_sources();
    check(f->GPU_graphs==204&&f->exact_matrices==408&&f->scalar==204&&f->vector==68&&f->non_BF16_inputs>0,"Vector bank finite cohort is incomplete");
    Json result={{"schema",f->compact?"ps5-qwen-vector-bank-result-compact-v2":"ps5-qwen-vector-bank-result-v1"},{"batches",f->batches},{"original_matrix_deliveries",f->exact_matrices},
        {"GPU_graphs",f->GPU_graphs},{"scalar_read_calls",f->scalar.load()},{"vector_read_calls",f->vector.load()},
        {"maximum_absolute_error",f->maximum_error},{"F64_reference_passed",true},{"F32_inputs_non_BF16_exact",true},
        {"non_BF16_exact_input_values",f->non_BF16_inputs},{"same_F32_outputs_bit_exact",true},
        {"all_30_residues_passed",true},{"real_bank_slots",{0,52}},{"selected_IDs",selected},{"canaries_intact",true},
        {"all_IO_returned_and_closed",true},{"all_workers_joined",true},{"all_three_strong_bank_leases_returned",true},
        {"device_ledger_peak_bytes",ledger.peak},{"device_ledger_live_bytes",ledger.live},{"model_loaded",false},{"copy_bytes",0}};
    delete f;return result;
}
}
