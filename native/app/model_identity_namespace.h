// SPDX-License-Identifier: MIT
#pragma once
#include "mapped_source.h"

namespace qwen_app {
// Null mounts can expose a distinct filesystem device ID. Bind exactly one
// source/application device pair; all nine remaining identity fields stay exact.
class ModelIdentityNamespace {
public:
    ModelIdentityNamespace(const SourceIdentity & expected_directory,
            const SourceIdentity & directory, const SourceIdentity & expected_receipt,
            const SourceIdentity & receipt, bool allow_app0_device_translation)
        : source_device_(expected_directory[0]), application_device_(directory[0]) {
        if (!source_device_ || !application_device_ ||
            (source_device_ != application_device_ && !allow_app0_device_translation) ||
            !matches(directory, expected_directory) || !matches(receipt, expected_receipt))
            throw std::runtime_error("The original-model mount namespace is not admitted");
    }
    bool matches(const SourceIdentity & actual, const SourceIdentity & expected) const {
        if (actual[0] != application_device_ || expected[0] != source_device_) return false;
        for (std::size_t i = 1; i < actual.size(); ++i) if (actual[i] != expected[i]) return false;
        return true;
    }
    std::uint64_t source_device() const { return source_device_; }
    std::uint64_t application_device() const { return application_device_; }
private:
    std::uint64_t source_device_, application_device_;
};
}
