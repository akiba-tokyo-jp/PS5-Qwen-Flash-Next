// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
namespace qwen_service {
inline unsigned mode=0;
inline std::uint64_t stage_pairs=0,stage_writes=0,stage_syncs=0;
inline char pending_stage[96]{};
inline bool ledger(){return mode&1;}
inline bool pair_stages(){return mode&2;}
}
