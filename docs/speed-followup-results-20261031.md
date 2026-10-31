# Speed follow-up results

The specification and its bounded native comparisons are implemented. Cases12420,12460 and12500 complete16+3+3 requests, preserve all original physical/kernel/heap/device limits, positively retire all model/source/GPU owners, and normally close/exactly restore the3066 control. Native/API/display qualification selects SELF5564792a,20089335bytes. Production placement is the final pending step in the adoption JSON until its native verification completes.

| Condition, same30-token prompt and22 output tokens | Installed12220 | Qualified12500 | Whole-time change |
| --- | ---: | ---: | ---: |
| Expert cold, model already loaded |4.377562 tok/s;11.452933s|4.382934 tok/s;11.494214s|+0.360%|
| Independent request/KV reset, Expert weights retained |4.177872 tok/s;7.486257s|4.894846 tok/s;6.581032s|−12.092%|
| Exact prefix plus causal reuse |6.300317 tok/s;3.871905s|6.579934 tok/s;3.459633s|−10.648%|

These are distinct reuse conditions. The installed comparison is sequential rather than ABBA. Cold inference has no demonstrated improvement. Ordinary physical reads fall6719→5279 and3.402154→2.980954GB per complete request; source wait falls3.481921→2.638469s. These totals include prefill and EOS, not just accepted decode. Every normal output token and byte matches the counting reference. Unlike-cache/width F32 maximum differences remain disclosed in the JSON; complete finite vocabulary does not imply exact cross-policy logits or broad reasoning quality.

| Specification | Result | Selection |
| --- | --- | --- |
| S1 previous accepted-decode protection | Fixed normal-route replay:2148→1785 misses at cap1536. Four different-input fixed-route replay:11108→11155. Native four-input aggregate reduction is confounded by JSON24→18 tokens; equal-output warm tasks are0.244% slower. | Only the measured compiled-identical-prompt normal composition is selected. Arbitrary-prompt acceleration is unqualified. |
| S2 owned BF16 row cache | Exact320/5120-byte rows;491520 payload/525344 allocated bytes,16-byte alignment. Corrected warm reverse comparison saves684 physical calls and1.495% whole time. Full-row SHA256, routes, tokens and bytes match. | Retained within the measured normal composition. The standalone2% target was not met and no separate2% gain is claimed. |
| S3 six-attempt causal budget | Matched12460/12500: same providers/model/driver/output; six accepts in both, one rejected seventh attempt removed. Tail449.911→207.131ms; final request3.731697→3.459633s,7.291% shorter;134 calls/66600960 bytes avoided. | Select cap6 in the bounded normal program; preserve state restoration and width-one EOS fallback. |
| S4 actual four-lane timing | Queue-to-start about14.5µs versus about1.44ms in the read function; busy-period average API inflight about3.26/4. Token snapshots separate physical prefill/decode/EOS calls and bytes in the headless cohort. | Bounded counters implemented. Raw SSD NAND time and pure GPU time remain unmeasured. |

The composed normal result is the adoption unit; this experiment does not independently attribute its12.092% gain to S1 or S2. Neither a shorter answer nor overlapping read durations are treated as equal-work throughput or exclusive SSD time.

Initial12360 returned a harness error after19 positively reset requests because the inherited96-entry VM record array did not cover24 requests. Its failed terminal and pre-close unknown whole-owner retirement remain preserved. Normal OS close and exact restoration succeeded. The corrected16-request B/C/B/A case prices88 entries for at most81 samples and completes. It does not replay the consumed case. Aligned owned storage, exact selected-reader bytes/leases/reset/canaries, short-read and consumer/admission failure draining, all-protected fallback, and the actual3072-slot planner across13200 captured-route observations pass focused host checks. This host aging check is not sustained native-service qualification.

Exact source/relink digests, precision, driver872cc126/cumulative-idle, linked native archiveb57fe26e and shared-profile archive67fe76cc are recorded in [adoption evidence](speed-followup-adoption-20261031.json). Persistent caches remain disabled; Expert Q2, resident Q8, original small PLE convolution BF16 and F32 activation/KV remain unchanged. No CI, agents, reboot, forced signal or GPU reset was used. See the [specification](speed-followup-spec-20261031.md) and [corrected detailed analysis](speed-followup-headless-corrected-20261031.json).
