// SPDX-License-Identifier: MIT
#include "ready_original_source.h"
#include "model_integrity.h"
#include <algorithm>
#include <limits>
namespace qwen_app {namespace {
void check(bool good,const char *message){if(!good)throw std::runtime_error(message);}
bool hash(const std::string &s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
std::uint64_t ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
}
ReadyOriginalPlan parse_ready_original_plan(const std::string &text,const std::string &sha) {
    check(text.size()<=65536&&hash(sha)&&sha256_metadata_bytes(text)==sha,"Bounded SHA256-bound original-source manifest required");
    const auto p=nlohmann::json::parse(text);ReadyOriginalPlan out;out.sha256=sha;
    check(p.is_object()&&p.size()==8&&p.at("schema")=="ps5-qwen-ready-original-plan-v1"&&
        p.at("layer").is_number_unsigned()&&p.at("layer")<48u&&p.at("lineage").is_object(),"Exact original-source plan required");
    out.layer=p.at("layer");const auto &files=p.at("files"),&experts=p.at("experts"),&slots=p.at("slots"),&matrices=p.at("matrices");
    const auto &lineage=p.at("lineage"),&origin=p.at("origin");
    check(lineage.is_object()&&lineage.size()==5&&lineage.at("original_revision")=="de4b8e4d43b917e7706784d8bb445c9af86a3540"&&
        lineage.at("original_BF16_preserved")==true&&hash(lineage.at("original_receipt_sha256"))&&
        hash(lineage.at("native_layout_seal_sha256"))&&hash(lineage.at("headers_sha256"))&&origin.is_object()&&origin.size()==5&&
        origin.at("native_route_record").is_number_unsigned()&&origin.at("native_route_record")<4096u&&origin.at("actual_recorded_selection")==true&&
        origin.at("fixture_activation_and_weights_are_deterministic")==true&&origin.at("model_hidden_state_not_captured")==true&&
        hash(origin.at("native_routes_sha256")),"Exact original lineage and completed route provenance required");
    check(files.is_array()&&!files.empty()&&files.size()<=30&&experts.is_array()&&experts.size()==10&&
        slots.is_array()&&slots.size()==10&&matrices.is_array()&&matrices.size()==30,"Exact ten-expert source geometry required");
    for(unsigned i=0;i<10;++i) {
        check(experts[i].is_number_unsigned()&&experts[i]<512u&&slots[i].is_number_unsigned()&&
            slots[i]==(i%2?48+i/2:i/2),"Original IDs and fixed interleaved 5/5 bank slots required");
        out.experts[i]=experts[i];out.slots[i]=slots[i];
        for(unsigned j=0;j<i;++j)check(out.experts[j]!=out.experts[i],"Representative fixture requires ten distinct original experts");
    }
    for(const auto &f:files) {
        check(f.is_object()&&f.size()==4&&f.at("bytes").is_number_unsigned()&&f.at("bytes")>0u&&f.at("bytes")<=(512u<<20),"Original physical part exceeds its scope");
        ReadyOriginalFile file;file.path=f.at("path");file.bytes=f.at("bytes");
        check(file.path.rfind("/data/",0)==0&&file.path.size()<1024&&file.path.find("..") ==std::string::npos&&
            file.path.find('\0')==std::string::npos&&file.path.find('\\')==std::string::npos,"Exact native model-part path required");
        const auto &identity=f.at("identity");check(identity.is_array()&&identity.size()==10,"Complete sealed source identity required");
        for(unsigned j=0;j<10;++j){check(identity[j].is_number_unsigned(),"Unsigned sealed source identity required");file.identity[j]=identity[j];}
        check(file.identity[0]&&file.identity[1]&&file.identity[5]==file.bytes&&
            (file.identity[2]&0170000)==0100000&&!(file.identity[2]&0022)&&hash(f.at("sha256")),"Sealed physical file identity differs");
        for(const auto &prior:out.files)check(prior.path!=file.path&&prior.identity!=file.identity,"Original source parts cannot alias");
        out.files.push_back(std::move(file));
    }
    std::array<bool,30> used{};
    for(unsigned i=0;i<30;++i) {
        const auto &m=matrices[i];auto &a=out.matrices[i];const unsigned role=i/10;
        check(m.is_object()&&m.size()==5&&m.at("source").is_number_unsigned()&&m.at("source")<out.files.size()&&
            m.at("offset").is_number_unsigned()&&m.at("residue").is_number_unsigned(),"Exact original matrix source required");
        a.source=m.at("source");a.offset=m.at("offset");a.residue=m.at("residue");a.raw=m.at("raw");a.envelope=m.at("envelope");
        const auto &file=out.files[a.source];used[a.source]=true;
        check(a.offset%bank_read_alignment==0&&a.offset<=file.bytes&&padded_bank_stride<=file.bytes-a.offset&&
            a.residue>0&&a.residue<bank_read_alignment&&a.residue%32==0&&hash(a.raw)&&hash(a.envelope),"Original matrix envelope/hash exceeds its part");
        if(i%10)check(a.residue==out.matrices[role*10].residue,"A role requires its original common Expert residue");
        for(unsigned j=0;j<i;++j)check(a.source!=out.matrices[j].source||a.offset!=out.matrices[j].offset,
            "Distinct original Expert roles cannot reuse one source envelope");
    }
    for(unsigned i=0;i<out.files.size();++i)check(used[i],"Unused original source part refused");
    return out;
}
#ifdef QWEN_READY_ORIGINAL_PLAN
#include "ready_original_plan.inc"
const ReadyOriginalPlan *compiled_ready_original_plan() {
    static const auto *plan=new ReadyOriginalPlan(parse_ready_original_plan(ready_original_manifest,ready_original_manifest_sha256));return plan;
}
#else
const ReadyOriginalPlan *compiled_ready_original_plan(){return nullptr;}
#endif
ReadyOriginalSource::ReadyOriginalSource(const ReadyOriginalPlan &p,const SplitBankBackings &banks,SourceReadOps &ops,
        Verify verify,void *opaque,Stage stage,std::chrono::steady_clock::time_point deadline):
    plan_(p),banks_(banks),ops_(ops),verify_(verify),opaque_(opaque),stage_(stage),deadline_(deadline) {
    check(verify_&&stage_&&deadline_>std::chrono::steady_clock::now(),"Original source requires bounded exact-byte and durable-plan callbacks");
    (void)validate_split_bank_backings(banks_);
}
int ReadyOriginalSource::descriptor(unsigned source,int excluded) {
    for(auto &h:handles_)if(h.fd>=0&&h.source==source){h.use=++clock_;return h.fd;}
    Handle *chosen=nullptr;
    for(auto &h:handles_)if((h.fd<0||h.fd!=excluded)&&(!chosen||h.fd<0||(chosen->fd>=0&&h.use<chosen->use))){chosen=&h;if(h.fd<0)break;}
    check(chosen,"Original source has no unpinned descriptor slot");
    if(chosen->fd>=0){check(ops_.close_file(chosen->fd),"Original source descriptor close is unknown");chosen->fd=-1;--live_handles_;++closes_;}
    const auto &file=plan_.files.at(source);chosen->fd=ops_.open_direct(file.path);
    check(chosen->fd>=0&&ops_.identity(chosen->fd)==file.identity,"Original physical part changed before read");
    ++live_handles_;++opens_;peak_handles_=std::max(peak_handles_,live_handles_);
    chosen->source=source;chosen->use=++clock_;return chosen->fd;
}
std::int64_t ReadyOriginalSource::read(void *opaque,const VectoredRead &r) {
    auto &s=*static_cast<ReadyOriginalSource *>(opaque);
    s.journal_->begin(r.id,r.offset,r.bytes(),ns());
    const auto got=s.ops_.read_at(r.fd,r.destinations[0].data,r.destinations[0].bytes,r.offset);
    s.journal_->returned(r.id,got,ns());return got;
}
void ReadyOriginalSource::fill(ReadyExpertWave &wave,unsigned group,void *opaque) {
    check(opaque,"Original source callback owner required");auto &s=*static_cast<ReadyOriginalSource *>(opaque);
    try{s.fill_group(wave,group);}catch(...){s.failed_=true;throw;}
}
void ReadyOriginalSource::fill_group(ReadyExpertWave &wave,unsigned group) {
    check(!failed_&&!closed_&&!cancelled_.load(std::memory_order_acquire)&&group==next_group_&&group<2,"Original source group order or ownership differs");
    if(!group){journal_=new BatchIOJournal;reader_=new VectoredSourceBatch(read,this);reader_->start();}
    for(unsigned role=0;role<3;++role)for(unsigned first=0;first<5;) {
        check(!cancelled_.load(std::memory_order_acquire)&&std::chrono::steady_clock::now()<deadline_&&ops_.system_headroom()>=(256u<<20),"Original source cannot retain stop/deadline/memory admission");
        const auto ordinal=first*2+group;unsigned count=1;
        const auto &m=plan_.matrices[role*10+ordinal];
        if(first<4) {
            const auto &next=plan_.matrices[role*10+ordinal+2];
            if(source_schedule_parallel(plan_.files[m.source].identity,m.offset,padded_bank_stride,
                plan_.files[next.source].identity,next.offset,padded_bank_stride))count=2;
        }
        std::array<VectoredRead,2> requests{};std::array<BatchIOPlan,2> plans{};
        for(unsigned j=0;j<count;++j) {
            const auto at=ordinal+j*2;const auto &matrix=plan_.matrices[role*10+at];const auto &file=plan_.files[matrix.source];
            const auto slot=split_padded_slot(plan_.slots[at],matrix.residue,banks_[group][role].descriptor_alignment);
            auto &r=requests[j];r.fd=descriptor(matrix.source,j?requests[0].fd:-1);r.device=file.identity[0];r.inode=file.identity[1];
            r.file_bytes=file.bytes;r.offset=matrix.offset;r.id=++id_;r.count=1;
            r.destinations[0]={static_cast<unsigned char *>(banks_[group][role].destination)+slot.envelope.aligned_write_offset,std::uint32_t(padded_bank_stride)};
            plans[j]={r.id,r.offset,r.bytes()};
        }
        ++operation_;if(count==2)wave.begin_role_read_pair(plan_.slots[ordinal],plan_.slots[ordinal+2],role,operation_);
        else wave.begin_role_read(plan_.slots[ordinal],role,operation_);
        journal_->prepare(plans.data(),count);
        std::string text="ready_original_batch_before plan="+std::to_string(wave.snapshot().plan_epoch)+" operation="+std::to_string(operation_)+" group="+std::to_string(group)+" role="+std::to_string(role)+" calls="+std::to_string(count)+" events=";
        for(unsigned j=0;j<count;++j)text+=std::to_string(plans[j].id)+":"+std::to_string(plans[j].offset)+":"+std::to_string(plans[j].bytes)+",";
        stage_(text.c_str());journal_->admit_durable();reader_->read(requests.data(),count);
        const auto events=journal_->snapshot();check(events.all_returned()&&reader_->completion_known(),"Original source pair completion is unknown");
        for(unsigned j=0;j<count;++j) {
            const auto at=ordinal+j*2;const auto &matrix=plan_.matrices[role*10+at];const auto &r=requests[j];const auto &event=events.events[j];
            check(event.result==static_cast<std::int64_t>(padded_bank_stride)&&ops_.identity(r.fd)==plan_.files[matrix.source].identity&&
                verify_(matrix,r.destinations[0].data,opaque_),"Original Expert bytes or identity differ after returned read");
            reads_.push_back({{"id",r.id},{"ordinal",at},{"group",group},{"role",role},{"source",matrix.source},{"offset",r.offset},
                {"bytes",padded_bank_stride},{"begin_ns",event.begin_ns},{"end_ns",event.end_ns},{"batch",operation_},{"batch_calls",count},
                {"original_raw_sha256",matrix.raw},{"original_envelope_sha256",matrix.envelope}});
        }
        stage_("ready_original_batch_all_calls_and_byte_proofs_returned");journal_->finish_after_durable_return();
        wave.complete_role_read(wave.snapshot().plan_epoch,operation_,count*bank_expert_bytes,true,true);
        calls_+=count;pairs_+=count==2;first+=count;
    }
    if(group) {
        reader_->stop_completed();
        for(auto &h:handles_)if(h.fd>=0){check(ops_.identity(h.fd)==plan_.files[h.source].identity&&ops_.close_file(h.fd),"Original source final identity or close differs");h.fd=-1;--live_handles_;++closes_;}
        closed_=true;
    }
    ++next_group_;
}
nlohmann::json ReadyOriginalSource::completed_report()const {
    check(closed_&&!failed_&&!cancelled_.load(std::memory_order_acquire)&&next_group_==2&&calls_==30&&reads_.size()==30&&!live_handles_&&opens_==closes_,"Original source lacks complete reads and joined inner worker");
    return {{"reads",reads_},{"Direct_read_calls",calls_},{"two_call_batches",pairs_},{"maximum_descriptor_cache",8},
        {"peak_open_descriptors",peak_handles_},{"descriptor_opens",opens_},{"descriptor_closes",closes_},
        {"inner_reader_joined",true},{"all_descriptors_closed",true},{"model_source_plan_sha256",plan_.sha256}};
}
}
