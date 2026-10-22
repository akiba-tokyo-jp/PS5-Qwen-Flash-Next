// SPDX-License-Identifier: MIT
#pragma once
#include <chrono>
#include <cstdint>
#include <functional>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace qwen_app {
struct ModelMappingFile { std::string path; std::uint64_t bytes; };
struct ModelMappingReport { std::uint64_t bytes = 0; unsigned files = 0, unmapped = 0; };
struct ModelMappingOps {
    virtual ~ModelMappingOps() = default;
    virtual std::uint64_t page_size() = 0;
    virtual int open_readonly(const std::string &) = 0;
    virtual bool regular_file_size(int, std::uint64_t &) = 0;
    virtual std::uintptr_t map_readonly(int, std::uint64_t) = 0;
    virtual bool close_file(int) = 0;
    virtual bool unmap(std::uintptr_t, std::uint64_t) = 0;
};

// Metadata-only mapping admission: no reads through mapped pointers, prefetch,
// writable/fixed mappings, backend setup or GPU requests. Failed/unknown calls
// retain remaining mappings for ordinary OS title close, without retry.
inline ModelMappingReport admit_model_mapping(const std::vector<ModelMappingFile> & files,
        ModelMappingOps & ops, const std::function<void(const std::string &)> & stage = {}) {
    if (files.empty() || files.size() > 256) throw std::invalid_argument("Bounded model mapping files are required");
    ModelMappingReport report;
    std::unordered_set<std::string> names;
    for (const auto & file : files) {
        if (file.path.empty() || file.path.size() > 1024 || file.path.find('\0') != std::string::npos ||
            !names.insert(file.path).second || !file.bytes || file.bytes > (512ull << 30) - report.bytes)
            throw std::invalid_argument("Invalid complete model mapping footprint");
        report.bytes += file.bytes;
    }
    const auto page = ops.page_size();
    if (page < 4096 || page > (1u << 20) || (page & (page - 1)))
        throw std::runtime_error("Native CPU mapping page size is not admitted");
    struct Range { std::uintptr_t at; std::uint64_t bytes, span; };
    std::vector<Range> mapped;
    mapped.reserve(files.size());
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(60);
    auto observe = [&](const char * phase) {
        if (std::chrono::steady_clock::now() > deadline)
            throw std::runtime_error("CPU model mapping deadline expired; backing retained");
        if (stage) stage(std::string(phase) + " mapped_files=" + std::to_string(report.files) +
                         " unmapped_files=" + std::to_string(report.unmapped) + " GPU_not_started=1 model_loaded=0");
    };
    for (const auto & file : files) {
        observe("model_mapping_before_open");
        const auto fd = ops.open_readonly(file.path);
        if (fd < 0) throw std::runtime_error("Original model mapping file could not be opened");
        std::uint64_t bytes = 0;
        if (!ops.regular_file_size(fd, bytes) || bytes != file.bytes) {
            (void) ops.close_file(fd);
            throw std::runtime_error("Original model mapping file identity or size is not admitted");
        }
        const auto at = ops.map_readonly(fd, bytes);
        const auto span = (bytes + page - 1) & ~(page - 1);
        if (at == std::numeric_limits<std::uintptr_t>::max()) {
            (void) ops.close_file(fd);
            throw std::runtime_error("Original model address space could not be mapped; earlier mappings retained");
        }
        if (!at || (at & (page - 1)) || at >= (1ull << 47) || span > (1ull << 47) - at)
            throw std::runtime_error("CPU model mapping returned an unadmitted range; backing retained");
        for (const auto & previous : mapped)
            if (at < previous.at + previous.span && previous.at < at + span)
                throw std::runtime_error("CPU model mapping ranges overlap; backing retained");
        mapped.push_back({at, bytes, span}); ++report.files;
        if (!ops.close_file(fd))
            throw std::runtime_error("CPU model file close was uncertain; backing retained");
        observe("model_mapping_completed");
    }
    observe("complete_model_address_space_mapped_before_unmap");
    for (auto it = mapped.rbegin(); it != mapped.rend(); ++it) {
        observe("model_mapping_before_completed_unmap");
        if (!ops.unmap(it->at, it->bytes))
            throw std::runtime_error("CPU model unmap failed; remaining backing retained without retry");
        ++report.unmapped;
    }
    observe("model_mapping_all_completed_ranges_unmapped");
    return report;
}

ModelMappingReport admit_native_model_mapping(const std::vector<ModelMappingFile> &,
    const std::function<void(const std::string &)> & stage = {});
}
