# Original-precision SSD delivery results

The initial gates in the [validation plan](ssd-io-validation-plan-20261025.md)
have been evaluated. No candidate qualifies for production adoption. Four
CPU-only PS5 cohorts completed exact original-byte checks, returned reads,
worker/buffer retirement, fresh same-boot idle checks and a full unchanged
production SELF readback. There were no title launches, GPU calls, model-file
changes, driver changes or CI runs. These are delivery measurements, not new
Flash-Next generation rates. See the [allowlisted evidence](ssd-io-validation-results-20261025.json).

The installed fastest SELF and the preserved original rollback remain in place.
Original BF16/F32 weights, F32 KV, all experts/PLE, 512 MiB source parts, the
53-slot cache, 8 MiB source window, pinned `872cc126` cumulative-idle driver,
disabled persistent caches and every production guard remain unchanged.

## Compared mechanisms

Throughput ratios below use paired round totals of identical original bytes.
`1.00x` is the corresponding uncompressed control; larger is faster. None is
a measured tokens/s ratio. Medians of individual durations need not divide
to the median paired ratio.

| Candidate | Control / scope | PS5 paired delivery ratio | Disposition |
| --- | --- | ---: | --- |
| Exponent LZ4HC, serial reconstruction | Serial raw, nine matrices, six rotated rounds, case 2255 | 0.777x | Reject this serial path. |
| Four exponent shards, serial reconstruction | Same serial raw/control | 0.780x | Independent chunks alone do not solve restoration cost. |
| Four shards, three decoder workers plus caller | Serial raw, nine matrices, eight rotated rounds, case 2258 | 0.883x | Restoration fell to 1.515 ms median but complete delivery remained slower. |
| Uncompressed completion-driven refill | Pair-wave raw, three groups of three matrices, eight rotated rounds, case 2267 | 1.039x | Small signal; one of eight rounds lost and the initial gate failed. |
| Compressed read/restore overlap | Uncompressed continuous schedule, same case 2267 | 0.918x | Reject this CPU implementation. |
| Uncompressed completion-driven refill, second cohort | Pair-wave raw, same groups, six rotated rounds, case 2269 | 1.038x | Again one round lost; not adopted. |
| Packed 4 MiB reads plus output copies | Raw pair-wave, same original expert bytes, case 2269 | 0.875x | Larger reads did not repay copies in this fixture. |
| Packed continuous reads plus output copies | Raw continuous schedule, same case 2269 | 0.934x | Reject this gather/copy variant. |
| Router reuse | Original router metadata, cache geometry and saved-route evidence | Unmeasured | Capacity/design screen only; no speculative reads enabled. |

The exploratory gate was specified before these executions: paired median over
1.05x and every round faster, with a matched uncompressed schedule for overlapped
compression and packing. It is a filter for these small fixtures, not a universal
minimum gain or a significance test. The roughly 4% refill signal merits retaining
the prototype; it does not justify replacing the installed application. No complete
native inference comparison was attempted after these gates failed.

## Lossless codec and parallel delivery

Twenty-seven original 3,276,800-byte matrices cover gate/up/down, layers
0/23/47 and experts 0/257/511. All variants restore exactly. Median encoded
fractions were 1.00394 for raw LZ4, 0.99205 for raw LZ4HC, 0.82377 for exponent
LZ4, 0.74721 for exponent LZ4HC, 0.74973 for four exponent shards, and 0.68111
for host-only exponent Zstd. Zstd has no native integration or PS5 speed result.

The independently written format separates the eight exponent bits from
sign/mantissa bits. LZ4 reconstructs original bits before use; it changes no
floating-point value, router choice or model precision. The native serial
comparison used nine complete expert-257 matrices, original SHA256, aligned
Direct reads, stable descriptor identity, complete sample-pack SHA256/EOF and
Latin-rotated orders. Parallel restoration uses three fixed workers plus the
caller, each with disjoint input, scratch and output slices.

Read time alone improved, while restoration consumed more than the saving.
In the overlapped cohort, summed restoration rose to 7.074 ms median per
three-matrix batch versus 4.988 ms in its pair-wave mode. This is consistent
with CPU/memory/scheduling contention during overlap; it does not identify a
particular proprietary SSD, cache or memory-controller cause.

The final host checks include all 65,536 BF16 patterns, malformed/alias/bounds
refusals, 338 controls, 32 repeated maximum-size parallel round trips, and
refusal plus completed worker joins for a damaged shard. Seven focused Python
evidence tests include missing completion, wrong identity/size, failed release,
incomplete original SHA checks and packed-copy faults. No CI was used.

## Continuous reads and packing scope

`CompletionSourceIO` holds exactly two read leases. Continuous mode releases
only a completed, consumed buffer and immediately submits the next known
matrix while the other read can remain active. No predicted expert, third
read or arbitrary GPU mapping is involved. Pair-wave control uses the same
workers, source bytes, destination pool and journal but waits for the wave.
Host ownership controls prove refill while another read is pending, held-buffer
reuse refusal, invalid-request refusal and drain/join after a known error.

Every three-matrix group represents one original layer/expert's gate/up/down
bytes. The packing screen compares three direct 3.125 MiB matrix reads with
two 4 MiB reads and one 1.375 MiB tail, followed by copies into destinations.
Both read 9.375 MiB in three calls. Complete output SHA256 is checked after
the timed batch and before destination reuse. Only a small immutable sidecar
was made; no full model or second expert corpus was repacked.

This is a favorable contiguous-destination CPU screen. It does not measure
filesystem seek reduction across the full original model, actual Vulkan bank
leases, split-boundary frequency or a different indexed layout. The production
path already delivers approximately 97% of payload directly into owned coherent
banks; packing that reintroduces copies must repay them. The prototype's two
I/O workers, three decoder workers and completion journal are also distinct
from the production source worker/observer. These differences limit projection
of the small refill signal to full inference.

## Memory refusal and smaller comparison

The initial nine-destination comparison requested a separately counted 40 MiB
Direct CPU allocation: 8 MiB I/O/scratch plus 32 MiB destinations. Its conservative
preallocation gate required the original kernel floor plus one page per proposed
allocation page: 3,714 pages. It returned a failed terminal before any allocation
or payload read. The case was preserved and was never replayed. An unchanged,
allocation-free metadata observer then completed with fresh idle sessions; its
later free count was 2,673, not a reconstructed count at the earlier refusal.

A distinct three-destination cohort reduced destination storage to 10 MiB while
keeping the full original matrices. Total Direct storage was 18 MiB, with the
same original 1,154-page kernel floor, 1,152 extra pages and a 2,306-page
preallocation target. The final packing case observed 2,691 pages before its
positive allocation/map. The original 264 MiB Flexible floor and every per-read
kernel check remained. All four successful cohorts positively unmapped/released
their allocations. This extra CPU-fixture destination pool is not presented as
part of the production 8 MiB scratch or as admitted Vulkan memory.

## Router reuse: corrected capacity finding

The actual GGUF metadata contains 49 router matrices, each **F32**, shape
`[2560, 512]`, 5,242,880 bytes; ten experts are selected per token. This includes
the MTP router: `load_mtp=false` leaves the 48 text-layer routers in scope for
current inference. F32 is already the original stored type.
`streaming_model_params` offloads dense tensors and
overrides only expert tensors, so the current model does not require the
additional BF16-to-F32 router copy used by the upstream design. Individual
runtime router mappings still need an ownership check before any direct reuse.

It would be incorrect to reject all router reuse by automatically charging
another 256,901,120 bytes here. However, the literal upstream 128 MiB staging
reserve exceeds the 83,820,544 bytes left at the previously measured CPU peak.
Its 256-slot victim margin also cannot fit 53 global slots. Four-layer deferral
with top-10 routes and two speculative slots would hold 52 slots before that
margin. This blocks that literal configuration, not a smaller forecast.

A plausible smaller design reuses original resident F32 routers, keeps a
one-layer lead and at most two speculative slots within the existing 53, and
uses only idle existing read capacity. Ten current decode experts plus two
reservations fit the slot count. This arithmetic does not prove prediction
accuracy, startup admission, actual buffer ownership or a speed gain. Predictions
must control transfer only and must publish a slot only after all three original
matrices are complete. The actual router remains authoritative.

The Qwen4Exp graph combines hyper-connections and PLE. Its actual FFN input is
the result of `build_hc_mix` after `build_hc_combine`, not simply an arbitrary
previous-layer attention output. The saved expert-ID traces contain no such
earlier hidden vectors. Therefore those traces cannot validate router reuse;
the rejected previous-token predictor was not rerun or relabeled as router reuse.
No forecast kernel, hidden-state capture or speculative transfer was implemented
or physically qualified by this screen.

## Source locations and next admissible gates

| Mechanism | Source / function | Next gate before production integration |
| --- | --- | --- |
| BF16 exact storage | `native/app/bf16_lossless.h`: `qwen_bf16_prepare`, `qwen_bf16_decode_shard`, `qwen_bf16_decode` | A materially different decoder or GPU reassembly needs a new measured delivery win. Current CPU variants are rejected. |
| Parallel reconstruction | `native/app/bf16_decode_queue.h`: `BF16DecodeQueue::decode` | Keep disjoint shard ownership and positive completion. More threads alone are not justified by these results. |
| Completion refill | `native/app/completion_source_io.h`: `submit`, `take`, `release`; `native/qwen_flash_next/completion_probe_cpp.cpp`: `completion_probe_batch` | Reproduce under exact production request shapes and low-cost observation; then lease/descriptor integration in `MappedSourceReader::try_owned_bank_reads` and the cache's `copy` loop. Preserve coalescing and split fallbacks. |
| Packing | `completion_probe_batch`, packed modes 4/5 | A different layout must first beat direct-bank reads including gather cost. Do not create a complete 241.6 GB sidecar for this losing variant. |
| Router tap / reuse, proposed only | Pinned llama.cpp `src/models/qwen4exp.cpp`: graph construction around `build_hc_combine` / `build_hc_mix`, `graph::build_layer_ffn`; `src/llama-moe-cache.cpp`: real route callback and slot planner | First collect bounded actual early-input/router predictions without speculative I/O, score useful missing experts, added graph cost and lead time. This needs a separately qualified artifact and complete numerical/retirement gates. |
| Slot adoption, proposed only | `patches/native-model-io/0002-llama-moe-cache.patch`, `native/app/expert_policy.h`, `native/app/mapped_source.h`, `mapped_source_bridge.h` | Protect actual selections, reserve two slots without enlarging the pool, require all-role completion masks and owned bank leases; demand reads always take precedence. |

The last two rows remain future implementation prerequisites, not measured
optimizations. Only a demonstrated beneficial candidate may proceed to a new
full-model comparison with identical requests, output/token/route checks, decode
and TTFT, actual native frames, positive retirement and full final executable
readback. The current production artifact is retained.

## Pinned primary sources and licenses

- [ZipMoE compressor and bit-plane design](https://github.com/npnothard/ZipMoE-ICML26/blob/1d0a56af1bb08d4c26ff850f557e2db439ef93b5/csrc/tensor_engine/compressors.cpp),
  [GPU restoration](https://github.com/npnothard/ZipMoE-ICML26/blob/1d0a56af1bb08d4c26ff850f557e2db439ef93b5/csrc/kernels/tensor_recover.cu),
  [prefetch scheduler](https://github.com/npnothard/ZipMoE-ICML26/blob/1d0a56af1bb08d4c26ff850f557e2db439ef93b5/csrc/prefetch/task_scheduler.cpp).
  Used as design references; no Academic Non-Commercial source was imported.
- [LZ4 v1.10.0](https://github.com/lz4/lz4/tree/ebb370ca83af193212df4dcbadcc5d87bc0de2f0/lib):
  only the BSD-2-Clause library and its original notices are vendored.
  `native/thirdparty/lz4/UPSTREAM.json` pins complete file digests.
- [Slotstream decode lookahead](https://github.com/carloslfu/slotstream/blob/7578fb21e57ec362d19f5050922e0f583914935d/Sources/Slotstream/DecodeLookahead.swift),
  [prefetch and adoption](https://github.com/carloslfu/slotstream/blob/7578fb21e57ec362d19f5050922e0f583914935d/Sources/Slotstream/ExpertPrefetch.swift),
  [documented qualification limits](https://github.com/carloslfu/slotstream/blob/7578fb21e57ec362d19f5050922e0f583914935d/docs/EXPERT-LOOKAHEAD.md).
  Its different memory target, quantized model and draft-token workload supply
  no PS5 original-precision speed estimate.
- [Pinned Qwen4Exp graph](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/models/qwen4exp.cpp),
  `build_layer_ffn` and FFN hyper-connection input construction. Existing
  production patches and qualified driver integration are unchanged.

Manual host commands are `tools/check_bf16_lossless.py`,
`tools/check_completion_source_io.py` and the two focused Python evidence test
modules. Build products and immutable native source/header/link/session receipts
stay on the private data disk. Console fixtures require fresh generated private
contexts and the normal guarded operator; they are not general launch commands.
