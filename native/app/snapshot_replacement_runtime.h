// SPDX-License-Identifier: MIT
#pragma once
#include "snapshot_replacement_budget.h"
#include "snapshot_layout_witness.h"
#include "llama-memory.h"
#include "llama.h"
namespace qwen_app {
// Default-off build-time integration. This sidecar does not change the engine
// or llama_context object layout or relax the native allocator limits.
inline SnapshotReplacementBudget snapshot_replacement_budget;
inline std::uint64_t snapshot_witness_sections=0;
inline std::uint64_t begin_snapshot_replacement(llama_context*context,
    ggml_backend_buffer_type_t buft,std::uint64_t bytes,std::uint64_t live,std::uint64_t cap){
    const auto memory=llama_get_memory(context);
    if(!memory)throw std::runtime_error("Actual original state memory is required");
    SnapshotLayoutWitness witness(buft);
    memory->state_write(witness,0,LLAMA_STATE_SEQ_FLAGS_NONE);
    witness.require_exact_payload(bytes);snapshot_witness_sections=witness.tensor_sections();
    return snapshot_replacement_budget.begin(context,bytes,live,cap);
}
}
