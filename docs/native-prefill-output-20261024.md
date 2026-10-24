# Keep the final-layer cache eligible during single-token prefill

The strict source-copy guard identified `blk.47.ffn_gate_exps.weight`, consumed by
`ffn_moe_gate-47` / MUL_MAT_ID, as the attempted complete 1,677,721,600-byte source
copy. This was the final layer during the first prompt token. Both complete
stable logs had no worker initialization; native context/cache admission had
already passed. Ordinary close and the complete original restoration/readmission
sequence remain separate from generation success.

The adapter submitted one token at a time but requested output logits only for
the last prompt token. In Qwen4exp, the graph crops the last layer to `n_outputs`
rows before its final FFN. A zero-output batch therefore has zero rows in that
FFN. The expert cache rejects a zero-token lookup, and the ordinary scheduler
tries to copy an original expert tensor even though its output is empty.

The actual GGML row-cropping operation and the actual cache eligibility method
reproduce this boundary without weights or model inference: zero output rows
return no cache slot map, while one row retains the 53-slot/top-10 cache. The
real adapter regression accepts the corrected one-output batches and rejects
the previous implementation. Sampling, synchronization, checkpoints and failure
retention continue to pass. The PS5 adapter translation unit also compiles.

The adapter now requests one output for every single-token prompt batch. It
still samples only from the final prompt token's logits. All original layers,
experts and precision are retained. This performs otherwise-unused intermediate
logit work; it avoids the zero-output graph/cache fallback and keeps one graph
output shape throughout prefill and decode. No memory limit is enlarged and the
whole-source-copy rejection remains enabled. Engine overlays and driver remain
unchanged; only the application adapter object changes.

This establishes the metadata/control-flow cause and its focused regression,
not completed physical model inference. The distinct artifact must still pass
actual prefill/decode, two external requests, real native frame review, positive
resource retirement, ordinary close and all original restoration/readmission gates.
