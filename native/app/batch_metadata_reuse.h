// SPDX-License-Identifier: MIT
#pragma once
#include "llama-batch.h"
#include <array>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Experimental metadata-only prototype. Not linked into the production engine.
// Keep one already initialized single-sequence batch for each admitted width.
// A healthy completed consumer is required before the caller mutates any batch.
class BatchMetadataReuse {
    std::array<llama_batch_ext, 3> batches_;
    std::uint64_t epoch_;
    bool pending_ = false;
    bool failed_ = false;
    static unsigned slot(std::uint32_t count) {
        if (count == 1) return 0;
        if (count == 2) return 1;
        if (count == 4) return 2;
        throw std::invalid_argument("Batch reuse requires width one, two or four");
    }
public:
    BatchMetadataReuse(std::uint64_t epoch, llama_token vocabulary)
        : batches_{{llama_batch_ext(4, 2560, 2560, 1, nullptr, vocabulary, 1),
                    llama_batch_ext(4, 2560, 2560, 1, nullptr, vocabulary, 1),
                    llama_batch_ext(4, 2560, 2560, 1, nullptr, vocabulary, 1)}}, epoch_(epoch) {
        if (!epoch || vocabulary <= 0) throw std::invalid_argument("Batch owner and vocabulary are required");
        for (const auto width : {1u, 2u, 4u}) {
            auto & batch = batches_[slot(width)];
            for (unsigned i = 0; i < width; ++i) {
                if (batch.add_token(0) != static_cast<int>(i) || !batch.set_output(i, true))
                    throw std::runtime_error("Batch metadata initialization failed");
            }
        }
    }
    BatchMetadataReuse(const BatchMetadataReuse &) = delete;
    BatchMetadataReuse & operator=(const BatchMetadataReuse &) = delete;
    llama_batch_ext & prepare(std::uint64_t epoch, const llama_token * ids,
                             std::uint32_t count, llama_pos position, std::uint32_t context) {
        if (failed_ || pending_ || epoch != epoch_ || !ids || position < 0 ||
            std::uint64_t(position) + count > context || context > 256)
            throw std::invalid_argument("Batch metadata has no healthy completed owner");
        auto & batch = batches_[slot(count)];
        // Validate the entire update before changing a previously completed batch.
        for (unsigned i = 0; i < count; ++i)
            if (ids[i] < 0 || ids[i] >= batch.n_vocab)
                throw std::invalid_argument("Batch token is outside the original vocabulary");
        for (unsigned i = 0; i < count; ++i) {
            const llama_pos pos = position + static_cast<llama_pos>(i);
            if (!batch.set_token_id(i, ids[i]) || !batch.set_token_pos(i, &pos)) {
                failed_ = true;
                throw std::runtime_error("Batch metadata update failed");
            }
        }
        pending_ = true;
        return batch;
    }
    void completed(std::uint64_t epoch) {
        if (failed_ || !pending_ || epoch != epoch_)
            throw std::invalid_argument("Batch metadata completion has no matching owner");
        pending_ = false;
    }
    void quarantine() noexcept { failed_ = true; }
};
}
