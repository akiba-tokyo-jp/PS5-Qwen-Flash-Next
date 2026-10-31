// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Validate both directions without changing eviction history or slot ownership.
// Request state and GPU completion are checked by the original caller.
template<class LRU>
std::uint64_t validate_retained_weight_cache(const LRU& lru, unsigned layers,
                                           unsigned selected) {
    if (layers != 48 || lru.n_slots != int(selected) || lru.n_expert != 512 ||
        lru.slot_map.size() != 49 || lru.key_of.size() != selected ||
        lru.prev.size() != selected || lru.next.size() != selected ||
        lru.is_protected.size() != selected || lru.seen.size() != 512)
        throw std::runtime_error("Retained weight cache geometry changed");
    unsigned maps = 0;
    for (unsigned layer = 0; layer < 49; ++layer) {
        const auto* map = lru.slot_map[layer];
        if (!map) continue;
        ++maps;
        for (unsigned expert = 0; expert < 512; ++expert) {
            const int slot = map[expert];
            if (slot < -1 || slot >= int(selected) ||
                (slot >= 0 && lru.key_of[slot] != int(layer * 512 + expert)))
                throw std::runtime_error("Retained weight lookup lost its owner");
        }
    }
    if (maps != 48) throw std::runtime_error("Retained cache lost a trunk map");
    std::uint64_t occupied = 0;
    for (unsigned slot = 0; slot < selected; ++slot) {
        const int key = lru.key_of[slot];
        if (key == -1) continue;
        if (key < 0 || key >= 49 * 512 || !lru.slot_map[key / 512] ||
            lru.slot_map[key / 512][key % 512] != int(slot))
            throw std::runtime_error("Retained weight slot lost its lookup");
        ++occupied;
    }
    return occupied;
}
}
