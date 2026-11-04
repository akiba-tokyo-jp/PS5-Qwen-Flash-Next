// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_service {
enum class TokenDurability { per_token, request_end };
struct TokenLedgerPolicy {
    TokenDurability durability=TokenDurability::per_token;
    std::uint64_t max_records=32, max_bytes=128u<<10;
    std::size_t max_record_bytes=4096;
};

// Sink owns the descriptor. Request-end durability requires an explicit finish
// before reporting request success; an interrupted request can lose its tail.
template<class Sink> class BoundedTokenWriter {
    Sink& sink_;
    TokenLedgerPolicy policy_;
    std::uint64_t records_=0, bytes_=0, syncs_=0;
    bool dirty_=false, failed_=false, finished_=false;
    void require_writable() const {
        if(failed_||finished_) throw std::runtime_error("Token ledger is no longer writable");
    }
public:
    explicit BoundedTokenWriter(Sink& sink, TokenLedgerPolicy policy={}):sink_(sink),policy_(policy) {
        if(!policy.max_records||!policy.max_bytes||!policy.max_record_bytes||
                policy.max_record_bytes>policy.max_bytes||
                (policy.durability!=TokenDurability::per_token&&policy.durability!=TokenDurability::request_end))
            throw std::invalid_argument("Positive bounded token ledger policy required");
    }
    void append(const char* data,std::size_t length) {
        require_writable();
        if(!data||!length||records_>=policy_.max_records||length>policy_.max_record_bytes||
                length>policy_.max_bytes-bytes_)
            throw std::runtime_error("Token ledger bounds exceeded");
        try {
            std::size_t done=0;
            while(done<length) {
                const auto wrote=sink_.write(data+done,length-done);
                if(wrote<0&&sink_.interrupted()) continue;
                if(wrote<=0||static_cast<std::uint64_t>(wrote)>length-done)
                    throw std::runtime_error("Token ledger write did not complete");
                done+=static_cast<std::size_t>(wrote);dirty_=true;
            }
            if(policy_.durability==TokenDurability::per_token) flush();
            ++records_;bytes_+=length;
        } catch(...) {failed_=true;throw;}
    }
    void flush() {
        require_writable();
        if(dirty_) {
            try {
                if(!sink_.sync()) throw std::runtime_error("Token ledger synchronization failed");
                ++syncs_;dirty_=false;
            } catch(...) {failed_=true;throw;}
        }
    }
    void finish() {require_writable();flush();finished_=true;}
    std::uint64_t records() const {return records_;}
    std::uint64_t bytes() const {return bytes_;}
    std::uint64_t syncs() const {return syncs_;}
    bool dirty() const {return dirty_;}
    bool failed() const {return failed_;}
};
}
