// SPDX-License-Identifier: MIT
#include "model_mapping.h"
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace qwen_app {
namespace {
class NativeMappingOps final : public ModelMappingOps {
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
        return reinterpret_cast<std::uintptr_t>(mmap(nullptr, bytes, PROT_READ, MAP_SHARED, fd, 0));
    }
    bool close_file(int fd) override { return close(fd) == 0; }
    bool unmap(std::uintptr_t at, std::uint64_t bytes) override {
        return munmap(reinterpret_cast<void *>(at), bytes) == 0;
    }
};
}
ModelMappingReport admit_native_model_mapping(const std::vector<ModelMappingFile> & files,
        const std::function<void(const std::string &)> & stage) {
    NativeMappingOps ops;
    return admit_model_mapping(files, ops, stage);
}
}
