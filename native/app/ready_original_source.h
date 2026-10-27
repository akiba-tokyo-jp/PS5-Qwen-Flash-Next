// SPDX-License-Identifier: MIT
#pragma once
#include "split_bank_allocation.h"
#include "mapped_source.h"
#include "vectored_source_batch.h"
#include "batch_io_journal.h"
#include <atomic>
#include <nlohmann/json.hpp>
namespace qwen_app {
struct ReadyOriginalFile {std::string path;std::uint64_t bytes;SourceIdentity identity;};
struct ReadyOriginalMatrix {unsigned source=0,residue=0;std::uint64_t offset=0;std::string raw,envelope;};
struct ReadyOriginalPlan {
    unsigned layer=0;std::string sha256;
    std::array<std::int32_t,10> experts{};
    std::array<unsigned,10> slots{};
    std::vector<ReadyOriginalFile> files;
    // Role-major, original-ordinal order, never routing/group execution order.
    std::array<ReadyOriginalMatrix,30> matrices;
};
ReadyOriginalPlan parse_ready_original_plan(const std::string &,const std::string &sha256);
// Returns null unless the manual build explicitly embeds the original-source
// manifest. Production and ordinary numerical builds keep this feature absent.
const ReadyOriginalPlan *compiled_ready_original_plan();
class ReadyOriginalSource {
public:
    using Verify=bool (*)(const ReadyOriginalMatrix &,const void *,void *);
    using Stage=void (*)(const char *);
private:
    const ReadyOriginalPlan &plan_;SplitBankBackings banks_;SourceReadOps &ops_;
    Verify verify_;void *opaque_;Stage stage_;
    struct Handle {unsigned source=0;int fd=-1;std::uint64_t use=0;};
    std::array<Handle,8> handles_{};std::uint64_t clock_=0,operation_=0,id_=0;
    VectoredSourceBatch *reader_=nullptr;BatchIOJournal *journal_=nullptr;
    nlohmann::json reads_=nlohmann::json::array();
    unsigned next_group_=0,calls_=0,pairs_=0,live_handles_=0,peak_handles_=0,opens_=0,closes_=0;bool failed_=false,closed_=false;
    std::atomic<bool> cancelled_{false};
    std::chrono::steady_clock::time_point deadline_;
    int descriptor(unsigned,int excluded=-1);
    static std::int64_t read(void *,const VectoredRead &);
    void fill_group(ReadyExpertWave &,unsigned);
public:
    ReadyOriginalSource(const ReadyOriginalPlan &,const SplitBankBackings &,SourceReadOps &,Verify,void *,Stage,
        std::chrono::steady_clock::time_point);
    ~ReadyOriginalSource(){if(closed_&&!failed_){delete reader_;delete journal_;}}
    ReadyOriginalSource(const ReadyOriginalSource&)=delete;
    ReadyOriginalSource&operator=(const ReadyOriginalSource&)=delete;
    static void fill(ReadyExpertWave &,unsigned,void *);
    // Cooperative stop between batches only. Never cancel an opaque read,
    // close a pending descriptor or release a failed GPU/backing owner.
    void stop_new_work(){cancelled_.store(true,std::memory_order_release);}
    nlohmann::json completed_report()const;
};
}
