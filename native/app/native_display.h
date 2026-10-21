// SPDX-License-Identifier: MIT
#pragma once
#include "monitor.h"
#include <memory>

namespace qwen_app {
// Display backing remains process-owned through ordinary OS title close. It
// never frees registered or uncertain scan-out resources from a destructor.
class NativeDisplay {
public:
    NativeDisplay();
    ~NativeDisplay();
    NativeDisplay(const NativeDisplay &) = delete;
    NativeDisplay & operator=(const NativeDisplay &) = delete;
    void start(MonitorSnapshot initial);
    void publish(const MonitorSnapshot & snapshot);
    bool failed() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace qwen_app
