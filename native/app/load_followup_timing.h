// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <chrono>
#include <cstdint>
#include <stdexcept>
namespace qwen_load {
enum Cpu {epoch_begin,epoch_complete,checkpoint,stage,logit_access,sampler,finite_scan,full_validation,token_render,token_persistence,publication,model_process,work_guard,request_run,cpu_count};
struct Stat {std::uint64_t calls=0,inclusive=0,exclusive=0;};
inline std::array<Stat,cpu_count>cpu{};
inline bool enabled=false;
inline std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
// All instrumented application/queue calls belong to the one admitted producer.
struct CpuSpan;
inline CpuSpan*active=nullptr;
struct CpuSpan {
 unsigned category;bool used;std::uint64_t began=0,children=0;CpuSpan*parent=nullptr;
 explicit CpuSpan(unsigned c):category(c),used(enabled){if(used){began=now();parent=active;active=this;}}
 void end(){if(!used)return;const auto elapsed=now()-began;if(active!=this||children>elapsed)throw std::runtime_error("CPU timing nesting differs");active=parent;if(parent)parent->children+=elapsed;auto&s=cpu[category];++s.calls;s.inclusive+=elapsed;s.exclusive+=elapsed-children;used=false;}
 ~CpuSpan(){end();}
};
inline std::array<std::uint64_t,cpu_count*3>snapshot(){std::array<std::uint64_t,cpu_count*3>v{};for(unsigned i=0;i<cpu_count;++i){v[i*3]=cpu[i].calls;v[i*3+1]=cpu[i].inclusive;v[i*3+2]=cpu[i].exclusive;}return v;}
}
