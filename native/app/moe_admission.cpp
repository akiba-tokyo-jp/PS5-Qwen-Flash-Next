// SPDX-License-Identifier: MIT
#include "moe_admission.h"
#include "model_integrity.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "indexed_vector.h"
#include "indexed_vector_admission.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace qwen_app {
std::array<IndexedVectorCase,4> admit_indexed_vectors(void (*checkpoint)(),void (*stage)(const char *)) {
    if (!checkpoint || !stage) throw std::invalid_argument("Positive fixture completion hooks are required");
    std::array<IndexedVectorCase,4> reports{};
    constexpr std::array<std::int32_t,10> selected{{9,0,5,0,8,1,9,3,7,2}};
    for (unsigned index=0;index<reports.size();++index) {
        auto & report=reports[index];
        report.columns=index<2?2560:640;report.rows=index<2?640:2560;report.input_vectors=index%2?10:1;
        const auto k=report.columns,n=report.rows,v=report.input_vectors;
        std::vector<std::uint16_t> weights(std::size_t(k)*n*10);
        std::vector<float> inputs(std::size_t(k)*v),actual(std::size_t(n)*10);
        std::vector<double> expected(actual.size());
        for(unsigned e=0;e<10;++e)for(unsigned row=0;row<n;++row)for(unsigned col=0;col<k;++col) {
            const float value=float(int((col*3+row*5+e*7)%17)-8)/128;
            const auto bf=ggml_fp32_to_bf16(value);
            std::memcpy(&weights[(std::size_t(e)*n+row)*k+col],&bf,2);
        }
        const auto reference=[&](bool non_dyadic){
            std::fill(expected.begin(),expected.end(),0.0);
            for(unsigned slot=0;slot<v;++slot)for(unsigned col=0;col<k;++col) {
                const float value=indexed_fixture_input(col,slot,non_dyadic);
                inputs[std::size_t(slot)*k+col]=value;
                if(non_dyadic&&ggml_bf16_to_fp32(ggml_fp32_to_bf16(value))!=value)
                    ++report.non_dyadic_F32_inputs;
            }
            for(unsigned slot=0;slot<10;++slot)for(unsigned row=0;row<n;++row)for(unsigned col=0;col<k;++col) {
                const double weight=double(int((col*3+row*5+unsigned(selected[slot])*7)%17)-8)/128;
                expected[std::size_t(slot)*n+row]+=weight*inputs[std::size_t(slot%v)*k+col];
            }
        };
        reference(false);
        stage("indexed_vector_fixture_CPU_reference_completed_GPU_not_submitted");
        auto * backend=ggml_backend_vk_init(0);
        if(!backend)throw std::runtime_error("Indexed-vector fixture backend unavailable");
        ggml_init_params params{};
        params.mem_size=ggml_tensor_overhead()*8+ggml_graph_overhead_custom(16,false);params.no_alloc=true;
        auto * context=ggml_init(params);
        if(!context)throw std::runtime_error("Indexed-vector fixture metadata unavailable");
        auto * a=ggml_new_tensor_3d(context,GGML_TYPE_BF16,k,n,10);
        auto * b=ggml_new_tensor_3d(context,GGML_TYPE_F32,k,v,1);
        auto * ids=ggml_new_tensor_2d(context,GGML_TYPE_I32,10,1);
        auto * output=ggml_mul_mat_id(context,a,b,ids);
        ggml_set_input(a);ggml_set_input(b);ggml_set_input(ids);ggml_set_output(output);
        auto * graph=ggml_new_graph_custom(context,16,false);ggml_build_forward_expand(graph,output);
        if(!bf16_indexed_vector_layout(output))throw std::runtime_error("Fixture layout did not reach the candidate predicate");
        auto * buffer=ggml_backend_alloc_ctx_tensors(context,backend);
        if(!buffer)throw std::runtime_error("Indexed-vector fixture allocation failed");
        const auto * bytes=reinterpret_cast<const unsigned char *>(weights.data());
        const auto size=weights.size()*2;
        for(std::size_t offset=0;offset<size;offset+=8u<<20)
            ggml_backend_tensor_set(a,bytes+offset,offset,std::min<std::size_t>(8u<<20,size-offset));
        ggml_backend_tensor_set(b,inputs.data(),0,inputs.size()*4);
        ggml_backend_tensor_set(ids,selected.data(),0,sizeof(selected));
        const auto validate=[&]{
            ggml_backend_tensor_get(output,actual.data(),0,actual.size()*4);
            for(std::size_t i=0;i<actual.size();++i) {
                const auto error=std::abs(double(actual[i])-expected[i]);
                if(!std::isfinite(actual[i]) || error>1e-6)
                    throw std::runtime_error("Indexed-vector fixture numerical refusal; backing retained");
                report.max_absolute_error=std::max(report.max_absolute_error,error);
            }
        };
        for(unsigned strategy=0;strategy<2;++strategy) {
            configure_bf16_indexed_vector(strategy==1);set_bf16_indexed_vector_scope(true);
            if(!ggml_backend_dev_supports_op(ggml_backend_get_device(backend),output))
                throw std::runtime_error("Indexed-vector fixture operation unsupported");
            const auto before=gpu_path_stats();
            for(unsigned repeat=0;repeat<3;++repeat) {
                stage("indexed_vector_fixture_before_finite_graph");
                const auto started=std::chrono::steady_clock::now();
                if(ggml_backend_graph_compute(backend,graph)!=GGML_STATUS_SUCCESS)
                    throw std::runtime_error("Indexed-vector fixture compute failed; backing retained");
                ggml_backend_synchronize(backend);checkpoint();
                const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
                if(repeat==0)report.first_ms[strategy]=ms;else report.warm_ms[strategy]+=ms/2;
                validate();
                stage("indexed_vector_fixture_numerics_and_positive_completion_passed");
            }
            const auto after=gpu_path_stats();
            if((strategy==0 && (after.bf16_matrix-before.bf16_matrix!=3 || after.bf16_vector!=before.bf16_vector)) ||
               (strategy==1 && (after.bf16_vector-before.bf16_vector!=3 || after.bf16_matrix!=before.bf16_matrix)))
                throw std::runtime_error("Indexed-vector fixture did not execute the selected strategy");
            set_bf16_indexed_vector_scope(false);
        }
        // Keep the original timed comparisons on identical dyadic inputs.
        // This additional graph independently qualifies unrounded F32 inputs.
        reference(true);
        if(!report.non_dyadic_F32_inputs)
            throw std::runtime_error("The vector fixture requires non-BF16-exact F32 activations");
        ggml_backend_tensor_set(b,inputs.data(),0,inputs.size()*4);
        configure_bf16_indexed_vector(true);set_bf16_indexed_vector_scope(true);
        const auto before_non_dyadic=gpu_path_stats();
        stage("indexed_vector_non_dyadic_before_finite_graph");
        if(ggml_backend_graph_compute(backend,graph)!=GGML_STATUS_SUCCESS)
            throw std::runtime_error("Non-dyadic indexed-vector compute failed; backing retained");
        ggml_backend_synchronize(backend);checkpoint();validate();
        const auto after_non_dyadic=gpu_path_stats();
        if(after_non_dyadic.bf16_vector-before_non_dyadic.bf16_vector!=1 ||
           after_non_dyadic.bf16_matrix!=before_non_dyadic.bf16_matrix)
            throw std::runtime_error("Non-dyadic indexed-vector strategy was not executed");
        stage("indexed_vector_non_dyadic_numerics_and_positive_completion_passed");
        set_bf16_indexed_vector_scope(false);
        configure_bf16_indexed_vector(false);
        ggml_backend_buffer_free(buffer);ggml_free(context);ggml_backend_free(backend);checkpoint();
        report.passed=true;
    }
    return reports;
}

std::vector<std::uint16_t> load_original_moe_fixture(const std::string & path) {
    verify_model_file(path, moe_fixture_bytes, moe_fixture_sha256, {}, 30);
    std::ifstream file(path, std::ios::binary);
    std::vector<std::uint16_t> bits(moe_fixture_bytes / 2);
    if (!file.read(reinterpret_cast<char *>(bits.data()), moe_fixture_bytes) || file.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("Original MoE fixture size changed after verification");
    for (auto word : bits)
        if ((word & 0x7f80u) == 0x7f80u) throw std::runtime_error("Nonfinite original MoE fixture is not admitted");
    return bits;
}

MoeAdmission admit_original_moe(const std::vector<std::uint16_t> & bits, void (*stage)(const char *)) {
    if (bits.size() != moe_fixture_bytes / 2)
        throw std::invalid_argument("The exact all-expert BF16 diagnostic is required");
    for (auto word : bits)
        if ((word & 0x7f80u) == 0x7f80u) throw std::invalid_argument("Nonfinite MoE input is not admitted");
    MoeAdmission report;
    const auto started = std::chrono::steady_clock::now();
    std::array<float, moe_columns> input{};
    for (unsigned k = 0; k < moe_columns; ++k) input[k] = float(int(k % 7) - 3) * 0.5f;
    for (unsigned slot = 0; slot < moe_selected; ++slot) {
        const auto expert = moe_expert_ids[slot];
        if (expert < 0 || expert >= std::int32_t(moe_experts)) throw std::logic_error("Invalid diagnostic expert ID");
        for (unsigned row = 0; row < moe_rows; ++row) for (unsigned k = 0; k < moe_columns; ++k) {
            const auto word = bits[(std::size_t(expert) * moe_rows + row) * moe_columns + k];
            ggml_bf16_t value;
            static_assert(sizeof(value) == 2, "Original BF16 must remain 16 bits");
            std::memcpy(&value, &word, 2);
            report.expected[slot * moe_rows + row] += double(ggml_bf16_to_fp32(value)) * input[k];
        }
    }
    if (stage) stage("MoE_CPU_double_references_completed_before_compute_backend");
    auto * backend = ggml_backend_vk_init(0);
    if (!backend) throw std::runtime_error("Vulkan MoE admission backend is unavailable");
    report.backend = ggml_backend_name(backend);
    ggml_init_params params{};
    params.mem_size = ggml_tensor_overhead() * 8 + ggml_graph_overhead_custom(16, false);
    params.no_alloc = true;
    auto * context = ggml_init(params);
    if (!context) throw std::runtime_error("MoE admission CPU metadata allocation failed");
    auto * weights = ggml_new_tensor_3d(context, GGML_TYPE_BF16, moe_columns, moe_rows, moe_experts);
    auto * vector = ggml_new_tensor_3d(context, GGML_TYPE_F32, moe_columns, 1, 1);
    auto * ids = ggml_new_tensor_2d(context, GGML_TYPE_I32, moe_selected, 1);
    auto * output = ggml_mul_mat_id(context, weights, vector, ids);
    ggml_set_input(weights); ggml_set_input(vector); ggml_set_input(ids); ggml_set_output(output);
    auto * graph = ggml_new_graph_custom(context, 16, false);
    ggml_build_forward_expand(graph, output);
    if (!ggml_backend_dev_supports_op(ggml_backend_get_device(backend), output))
        throw std::runtime_error("Original BF16 MUL_MAT_ID is unsupported before allocation");
    if (stage) stage("MoE_indexed_operation_supported_before_device_allocation");
    auto * buffer = ggml_backend_alloc_ctx_tensors(context, backend);
    if (!buffer) throw std::runtime_error("MoE admission device allocation failed");
    constexpr std::size_t upload_chunk = 8u << 20;
    const auto * bytes = reinterpret_cast<const unsigned char *>(bits.data());
    for (std::size_t offset = 0; offset < moe_fixture_bytes; offset += upload_chunk)
        ggml_backend_tensor_set(weights, bytes + offset, offset, std::min<std::size_t>(upload_chunk, moe_fixture_bytes - offset));
    ggml_backend_tensor_set(vector, input.data(), 0, sizeof(input));
    ggml_backend_tensor_set(ids, moe_expert_ids.data(), 0, sizeof(moe_expert_ids));
    if (stage) stage("MoE_all512_experts_and_top10_IDs_uploaded_before_single_graph_compute");
    if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS)
        throw std::runtime_error("MoE admission compute failed; backing retained");
    ggml_backend_synchronize(backend);
    if (stage) stage("MoE_synchronized_before_readback");
    ggml_backend_tensor_get(output, report.actual.data(), 0, sizeof(report.actual));
    report.metric.values = report.actual.size();
    double error_squares = 0, reference_squares = 0;
    for (unsigned i = 0; i < report.actual.size(); ++i) {
        const auto error = std::abs(double(report.actual[i]) - report.expected[i]);
        report.metric.finite = report.metric.finite && std::isfinite(report.actual[i]) && std::isfinite(report.expected[i]);
        if (!std::isfinite(error) || error > 1e-5 + 1e-5 * std::abs(report.expected[i])) report.metric.passed = false;
        if (std::isfinite(error)) report.metric.max_absolute_error = std::max(report.metric.max_absolute_error, error);
        error_squares += error * error; reference_squares += report.expected[i] * report.expected[i];
    }
    report.metric.normalized_rmse = reference_squares > 0 ? std::sqrt(error_squares / reference_squares)
        : error_squares == 0 ? 0 : INFINITY;
    report.passed = report.metric.passed = report.metric.passed && report.metric.finite &&
        std::isfinite(report.metric.normalized_rmse) && report.metric.normalized_rmse <= 0.01;
    report.elapsed_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    if (report.passed) {
        if (stage) stage("MoE_all_numerical_gates_passed_before_release");
        ggml_backend_buffer_free(buffer); ggml_free(context); ggml_backend_free(backend);
        if (stage) stage("MoE_completed_resources_deferred_for_positive_retirement");
    } else if (stage) stage("MoE_numerical_failure_backing_retained");
    return report;
}
}
