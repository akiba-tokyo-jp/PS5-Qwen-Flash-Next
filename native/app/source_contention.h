// SPDX-License-Identifier: MIT
#pragma once
#include "mapped_source.h"
#include <memory>

namespace qwen_app {
// Owned for the entire native source lifetime. Unknown reads never unwind this
// observer or release its thread, metadata or the source window it observes.
class SourceContentionMonitor {
public:
    SourceContentionMonitor();
    ~SourceContentionMonitor();
    void start();
    bool active() const;
    std::int64_t read_at(int, void *, std::size_t, std::uint64_t);
    void begin_pair(unsigned, unsigned, unsigned, const std::array<SourceReadRequest, 2> &,
                    const std::array<std::uint64_t, 2> &, const CompletedSourcePair &);
    void complete_pair(const std::array<std::int64_t, 2> &);
    std::string finish_completed();
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
std::string run_native_completed_source_trace();
}
