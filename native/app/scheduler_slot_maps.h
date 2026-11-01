// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace qwen_app {
class SchedulerSlotMaps;
inline SchedulerSlotMaps * scheduler_slot_map_owner = nullptr;
inline std::atomic<bool> scheduler_slot_map_reuse{false};
// Publications, uploads, reuses, pre-allocation bindings, sent/saved bytes,
// allocations, allocated bytes, callback checks, source comparisons.
inline std::array<std::uint64_t, 10> scheduler_slot_map_counts{};

class SchedulerSlotMaps {
    static constexpr std::size_t experts = 512, guard = 64, stride = experts + 2 * guard;
    static constexpr std::int32_t sentinel = 0x13579bdf;
    ggml_backend_t backend_;
    std::size_t capacity_;
    ggml_context * context_ = nullptr;
    ggml_backend_buffer_t buffer_ = nullptr;
    ggml_tensor * storage_ = nullptr;
    std::vector<ggml_tensor *> maps_;
    std::vector<const ggml_tensor *> sources_;
    std::vector<std::array<std::int32_t, experts>> sent_;
    std::vector<bool> valid_;

    static void need(bool value, const char * message) {
        if (!value) throw std::runtime_error(message);
    }
    static bool geometry(const ggml_tensor * tensor) {
        return tensor && tensor->type == GGML_TYPE_I32 &&
            ggml_nelements(tensor) == experts && ggml_is_contiguous(tensor) &&
            !tensor->view_src && !tensor->view_offs;
    }
public:
    SchedulerSlotMaps(ggml_backend_t backend,
                     std::vector<const ggml_tensor *> sources, std::size_t capacity):
        backend_(backend), capacity_(capacity), maps_(sources.size()),
        sources_(std::move(sources)), sent_(maps_.size()), valid_(maps_.size(), false) {
        need(!scheduler_slot_map_owner && backend && !maps_.empty() &&
             maps_.size() <= 64 && capacity && capacity <= INT32_MAX,
             "One serialized bounded scheduler slot-map owner required");
        for (auto * source : sources_) need(!source || (geometry(source) && source->data),
                                           "Complete owned CPU slot-map source required");
        ggml_init_params params{};
        params.no_alloc = true;
        params.mem_size = (maps_.size() + 1) * ggml_tensor_overhead() + 256;
        context_ = ggml_init(params);
        need(context_ != nullptr, "Scheduler slot-map metadata allocation failed");
        storage_ = ggml_new_tensor_1d(context_, GGML_TYPE_I32, maps_.size() * stride);
        for (std::size_t layer = 0; layer < maps_.size(); ++layer)
            maps_[layer] = ggml_view_1d(context_, storage_, experts,
                                      (layer * stride + guard) * sizeof(std::int32_t));
        buffer_ = ggml_backend_alloc_ctx_tensors(context_, backend_);
        if (!buffer_) {
            ggml_free(context_); context_ = nullptr;
            throw std::runtime_error("Scheduler slot-map device allocation failed");
        }
        std::vector<std::int32_t> initial(maps_.size() * stride, sentinel);
        for (std::size_t layer = 0; layer < maps_.size(); ++layer)
            std::fill_n(initial.begin() + layer * stride + guard, experts, -1);
        ggml_backend_tensor_set(storage_, initial.data(), 0, initial.size() * sizeof(std::int32_t));
        ++scheduler_slot_map_counts[6];
        scheduler_slot_map_counts[7] += ggml_backend_buffer_get_size(buffer_);
        scheduler_slot_map_owner = this;
    }
    SchedulerSlotMaps(const SchedulerSlotMaps &) = delete;
    SchedulerSlotMaps & operator=(const SchedulerSlotMaps &) = delete;
    ~SchedulerSlotMaps() {
        if (scheduler_slot_map_owner == this) scheduler_slot_map_owner = nullptr;
        if (buffer_) ggml_backend_buffer_free(buffer_);
        if (context_) ggml_free(context_);
    }
    bool bind_before_allocation(ggml_backend_t backend, const ggml_tensor * source,
                                ggml_tensor * destination, int copy) {
        const auto found = std::find(sources_.begin(), sources_.end(), source);
        if (found == sources_.end()) return false;
        need(backend == backend_ && copy == 0 && geometry(source) && geometry(destination),
             "Scheduler slot-map backend/copy/layout contract differs");
        need(!destination->buffer && !destination->data,
             "Scheduler slot maps must bind before any allocation");
        const auto layer = std::size_t(found - sources_.begin());
        // The public allocation API initializes the backend descriptor now.
        // The graph allocator and all descendant views see this storage first.
        need(ggml_backend_tensor_alloc(buffer_, destination, maps_[layer]->data) == GGML_STATUS_SUCCESS,
             "Scheduler slot-map tensor initialization failed");
        ++scheduler_slot_map_counts[3];
        return true;
    }
    bool publish(ggml_backend_t backend, unsigned layer, const ggml_tensor * source,
                 ggml_tensor * destination) {
        if (layer >= sources_.size() || sources_[layer] != source) return false;
        ++scheduler_slot_map_counts[8];
        need(backend == backend_ && geometry(source) && geometry(destination) &&
             destination->buffer == buffer_ && destination->data == maps_[layer]->data,
             "Scheduler slot-map storage changed after graph allocation");
        const auto * values = static_cast<const std::int32_t *>(source->data);
        for (std::size_t i = 0; i < experts; ++i)
            need(values[i] >= -1 && (values[i] < 0 || std::size_t(values[i]) < capacity_),
                 "Scheduler slot map contains an unowned Expert slot");
        ++scheduler_slot_map_counts[0]; ++scheduler_slot_map_counts[9];
        const bool same = valid_[layer] && !std::memcmp(values, sent_[layer].data(), experts * sizeof(*values));
        if (!scheduler_slot_map_reuse.load(std::memory_order_relaxed) || !same) {
            ggml_backend_tensor_set_async(backend_, destination, values, 0, experts * sizeof(*values));
            std::memcpy(sent_[layer].data(), values, experts * sizeof(*values)); valid_[layer] = true;
            ++scheduler_slot_map_counts[1]; scheduler_slot_map_counts[4] += experts * sizeof(*values);
        } else {
            ++scheduler_slot_map_counts[2]; scheduler_slot_map_counts[5] += experts * sizeof(*values);
        }
        // No address, buffer, view or descriptor is changed by publication.
        return true;
    }
    void verify_completed() const {
        // The caller must first prove backend completion.
        std::vector<std::int32_t> actual(maps_.size() * stride);
        ggml_backend_tensor_get(storage_, actual.data(), 0, actual.size() * sizeof(std::int32_t));
        for (std::size_t layer = 0; layer < maps_.size(); ++layer) {
            for (std::size_t i = 0; i < guard; ++i)
                need(actual[layer * stride + i] == sentinel &&
                     actual[layer * stride + guard + experts + i] == sentinel,
                     "Scheduler slot-map guard differs");
            for (std::size_t i = 0; i < experts; ++i)
                need(actual[layer * stride + guard + i] == (valid_[layer] ? sent_[layer][i] : -1),
                     "Scheduler slot-map GPU bytes differ from the published CPU map");
        }
    }
};
inline void bind_scheduler_slot_map(ggml_backend_t backend, const ggml_tensor * source,
                                    ggml_tensor * destination, int copy) {
    if (scheduler_slot_map_owner)
        scheduler_slot_map_owner->bind_before_allocation(backend, source, destination, copy);
}
}
