// SPDX-License-Identifier: MIT
// Execute the real mapping ownership policy with deterministic file/VM failures.
#include "model_mapping.h"
#include <iostream>

using namespace qwen_app;
static void check(bool value) { if (!value) throw std::runtime_error("CPU mapping contract failed"); }
struct FakeOps final : ModelMappingOps {
    std::vector<std::uint64_t> sizes;
    unsigned opens = 0, maps = 0, closes = 0, unmaps = 0;
    int fail_map = -1, fail_close = -1, fail_unmap = -1;
    bool wrong_size = false, overlap = false, unaligned = false;
    std::uint64_t page = 16384;
    std::uint64_t page_size() override { return page; }
    int open_readonly(const std::string &) override { return 100 + opens++; }
    bool regular_file_size(int fd, std::uint64_t & bytes) override {
        bytes = sizes.at(fd - 100) + (wrong_size ? 1 : 0); return true;
    }
    std::uintptr_t map_readonly(int fd, std::uint64_t bytes) override {
        check(bytes == sizes.at(fd - 100));
        const auto index = maps++;
        if (static_cast<int>(index) == fail_map) return std::numeric_limits<std::uintptr_t>::max();
        return (1ull << 42) + (overlap ? 0 : (std::uint64_t(index) << 40)) + (unaligned ? 1 : 0);
    }
    bool close_file(int) override { return static_cast<int>(closes++) != fail_close; }
    bool unmap(std::uintptr_t, std::uint64_t) override { return static_cast<int>(unmaps++) != fail_unmap; }
};
int main() {
    try {
        const std::vector<ModelMappingFile> files{{"part-0.gguf", 4ull << 30}, {"part-1.gguf", (4ull << 30) + 17}};
        auto fake = [&] { FakeOps ops; for (const auto & file : files) ops.sizes.push_back(file.bytes); return ops; };
        auto reject = [&](const auto & selected, FakeOps & ops) {
            bool refused = false; try { admit_model_mapping(selected, ops); } catch (const std::exception &) { refused = true; }
            check(refused);
        };
        auto positive = fake();
        const auto report = admit_model_mapping(files, positive);
        check(report.files == 2 && report.unmapped == 2 && report.bytes == (8ull << 30) + 17);
        check(positive.opens == 2 && positive.maps == 2 && positive.closes == 2 && positive.unmaps == 2);
        auto map_failure = fake(); map_failure.fail_map = 1; reject(files, map_failure);
        check(map_failure.maps == 2 && map_failure.closes == 2 && map_failure.unmaps == 0);
        auto close_failure = fake(); close_failure.fail_close = 0; reject(files, close_failure);
        check(close_failure.maps == 1 && close_failure.closes == 1 && close_failure.unmaps == 0);
        auto unmap_failure = fake(); unmap_failure.fail_unmap = 0; reject(files, unmap_failure);
        check(unmap_failure.unmaps == 1 && unmap_failure.maps == 2);
        auto partial_unmap_failure = fake(); partial_unmap_failure.fail_unmap = 1; reject(files, partial_unmap_failure);
        check(partial_unmap_failure.unmaps == 2);
        auto changed = fake(); changed.wrong_size = true; reject(files, changed);
        check(changed.maps == 0 && changed.closes == 1 && changed.unmaps == 0);
        auto overlapping = fake(); overlapping.overlap = true; reject(files, overlapping);
        check(overlapping.maps == 2 && overlapping.unmaps == 0);
        auto unaligned = fake(); unaligned.unaligned = true; reject(files, unaligned);
        check(unaligned.maps == 1 && unaligned.unmaps == 0);
        for (const auto & invalid : std::vector<std::vector<ModelMappingFile>>{
                 {}, {{"same.gguf", 1}, {"same.gguf", 1}}, {{"zero.gguf", 0}},
                 {{"large.gguf", (512ull << 30) + 1}},
                 {{"first.gguf", 512ull << 30}, {"second.gguf", 1}}}) {
            auto ops = fake(); reject(invalid, ops); check(ops.opens == 0 && ops.maps == 0);
        }
        auto invalid_page = fake(); invalid_page.page = 16385; reject(files, invalid_page);
        check(invalid_page.opens == 0);
        auto stage_failure = fake(); bool refused = false;
        try { admit_model_mapping(files, stage_failure, [](const std::string & text) {
            if (text.find("model_mapping_completed") == 0) throw std::runtime_error("durable observation failed");
        }); } catch (const std::exception &) { refused = true; }
        check(refused && stage_failure.maps == 1 && stage_failure.unmaps == 0);
        std::cout << "CPU mapping byte accounting, rounded ranges, completed cleanup and no-retry failure retention passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
