// SPDX-License-Identifier: MIT
#include "model_mapping.h"
#include "virtual_source.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>

namespace qwen_app {
namespace {
class NativeMappingOps final : public ModelMappingOps {
    int error_ = 0;
    std::uint64_t page_size() override {
        const auto bytes = sysconf(_SC_PAGESIZE);
        return bytes > 0 ? static_cast<std::uint64_t>(bytes) : 0;
    }
    int open_readonly(const std::string & path) override { return open(path.c_str(), O_RDONLY | O_NOFOLLOW); }
    bool regular_file_size(int fd, std::uint64_t & bytes) override {
        static_assert(sizeof(off_t) == 8, "Original model files require 64-bit offsets");
        struct stat metadata{};
        if (fstat(fd, &metadata) || !S_ISREG(metadata.st_mode) || metadata.st_size <= 0) return false;
        bytes = static_cast<std::uint64_t>(metadata.st_size); return true;
    }
    std::uintptr_t map_readonly(int fd, std::uint64_t bytes) override {
        static_assert(sizeof(std::size_t) == 8, "Complete model mappings require 64-bit lengths");
        (void) fd;
        return reserve_native_virtual_source(bytes);
    }
    bool close_file(int fd) override { return close(fd) == 0; }
    bool unmap(std::uintptr_t at, std::uint64_t bytes) override {
        release_native_virtual_source(at, bytes); return true;
    }
    int last_error() const override { return error_; }
};
}
ModelMappingReport admit_native_model_mapping(const std::vector<ModelMappingFile> & files,
        const std::function<void(const std::string &)> & stage) {
    if (stage) stage("source_virtual_small_probe_started bytes=16384 file_mmap_calls=0 GPU_not_started=1");
    const auto probe = reserve_native_virtual_source(16384);
    release_native_virtual_source(probe,16384);
    if (stage) stage("source_virtual_small_probe_completed bytes=16384 file_mmap_calls=0 GPU_not_started=1");
    NativeMappingOps ops;
    return admit_model_mapping(files, ops, stage);
}
}
