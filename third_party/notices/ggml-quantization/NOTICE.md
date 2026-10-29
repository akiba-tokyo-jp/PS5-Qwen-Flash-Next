# ggml quantization attribution

The Q2_K reference routines in `tools/expert_q2k_quantize.c` are extracted from
`ggml/src/ggml-quants.c` at llama.cpp commit
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`: `nearest_int`,
`make_qkx2_quants` and `quantize_row_q2_K_ref`.
The retained [MIT license](LICENSE) and copyright apply to those routines.
The local wrapper accepts original BF16 input and uses the same FP16 block ABI.
The Q2_0 wrapper independently implements the corresponding pinned block format.

Upstream: https://github.com/ggml-org/llama.cpp/tree/0a1ef309cdbb9f2024f58a38fb4c42352c5db569
