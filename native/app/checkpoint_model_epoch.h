// SPDX-License-Identifier: MIT
#pragma once
namespace qwen_app {
// Match LlamaEngine's existing GpuBoundary protocol for standalone checkpoint
// calls made after a sampled token has completed its original frontend epoch.
class CheckpointModelEpoch {
    void(*complete_)();void(*retain_)();bool completed_=false;
public:
    CheckpointModelEpoch(void(*begin)(),void(*complete)(),void(*retain)()):complete_(complete),retain_(retain){if(begin)begin();}
    void complete(){if(complete_)complete_();completed_=true;}
    ~CheckpointModelEpoch(){if(!completed_&&retain_)retain_();}
};
}
