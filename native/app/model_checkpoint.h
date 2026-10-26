// SPDX-License-Identifier: MIT
#pragma once
#include "llama.h"
#include <cstdint>
#include <functional>
#include <thread>
#include <vector>
namespace qwen_app {
struct CheckpointApplicationState {
    std::uint64_t request_epoch=0;
    llama_pos position=0;
    llama_token pending=LLAMA_TOKEN_NULL;
    bool ready=false;
    std::vector<llama_token> prompt;
};
// Owns bounded CPU metadata only. Tensor snapshots remain owned and charged to
// the same admitted llama_context until that context positively retires.
class ModelCheckpoint {
public:
    using Stage=std::function<void(const char *)>;
    using Admit=std::function<void(std::uint64_t)>;
    using Complete=std::function<void()>;
    ModelCheckpoint(llama_model *,llama_context *);
    ~ModelCheckpoint();
    ModelCheckpoint(const ModelCheckpoint &)=delete;
    ModelCheckpoint &operator=(const ModelCheckpoint &)=delete;
    void capture(const CheckpointApplicationState &,const float *logits,std::size_t count,
        const Admit &,const Stage &,const Complete &);
    const CheckpointApplicationState &restore(std::uint64_t epoch,const Stage &,const Complete &);
    bool matches_complete_prompt(const std::vector<llama_token> &)const;
    void rebind_complete_prompt(std::uint64_t epoch,const std::vector<llama_token> &);
    const std::vector<float> &logits()const;
    void discard();
    bool saved()const;
    bool quarantined()const;
    std::uint64_t payload_bytes()const;
    std::size_t metadata_bytes()const;
private:
    struct Payload;
    enum class Status {empty,saved,capturing,restoring,quarantined};
    llama_model *model_;llama_context *context_;std::thread::id owner_;
    Payload *data_;Status status_=Status::empty;
    void owner()const;
};
}
