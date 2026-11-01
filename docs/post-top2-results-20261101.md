# Post-Top2 optimization results

Completed: all17 planned candidate stages are disposed; normal45100 is qualified and production45200 is installed. Both complete programs and both five-setting sets passed native whole-SHA256/identity/EOF verification before and after placement. The immediate5b control is preserved. The app, gateway and models are inactive. The actual current-control admission and13 invalid-adoption refusals pass.

The17 stages in `speed-opportunities-20261101.md` are explicitly disposed below. D1-D3 were scoped as initial capability/feasibility/cost slices. Their completion does not claim a full indirect backend, stateful MTP service or full-model shared-basis conversion. No unchanged failed launch was repeated. Host inference, CI, reboot, forced reset and persistent shader/pipeline caches were not used.

## Qualified normal application

| Condition | Previous normal30200 decode | New normal45100 decode | New TTFT | New whole request |
|---|---:|---:|---:|---:|
| Cold weights |5.537 tok/s|6.587 tok/s|6.076 s|9.388 s|
| Retained weights, empty request state |6.539 tok/s|8.203 tok/s|0.586 s|3.287 s|
| Exact prefix replay |7.873 tok/s|9.451 tok/s|0.062 s|2.458 s|

These are22-output-token measurements with30 prompt tokens. Normal30200 and45100 are sequential complete product configurations, not an interleaved causal A/B test. Matched component evidence is separate; stage percentage gains must not be added. The retained whole request is16.697% shorter and decode25.458% higher in this sequential comparison. Prefix replay is a different cache condition and still answers the final number as7 instead of8; it is not correct-answer throughput. Cold/retained counting answers pass. General quality, arbitrary-prompt speed and sustained service are not established.

The application emits three actual API responses and two positively completed1920x1080 VideoOut frames. Both original frames were visually inspected:8.20 and9.45 tok/s, CPU/GPU identity, synchronized UTC clock and memory are readable. Unavailable utilization counters remain `--`.

## Stage decisions

| ID | Technology | Native evidence cases | Decision |
|---|---|---|---|
|N1|GPU greedy and full vocabulary handling|31500,33400,33900,42900|tested-not-adopted|
|N2|Submission node256/divisor40|35100,35900,36700,37300,38300|adopted; production verified|
|N3|Output Q4 projection|31600,34700,35400|adopted; production verified|
|N4|Static/adaptive prefill Expert budgets|32500,34500,39900|tested-not-adopted|
|N5|Observed startup and reuse of sealed read-only pack|32600,36900|adopted; production verified|
|R1|New Top2 Gate/Up kernel|30700,39300|tested-not-adopted|
|R2|History proposal cap8/12|31600,34000,35400|tested-not-adopted|
|R3|Two-token GDN|33800|tested-not-adopted|
|R4|Held-out current-distribution phase placement|39700|tested-not-adopted|
|R5|Owned zero-extra-copy ring|36300|tested-not-adopted|
|C1|GPU selection with node256 and complete logit evidence|38900,42900|tested-not-adopted|
|C2|Cap12 plus two-token GDN plus Top2 Gate/Up|40300,41100|tested-not-adopted|
|C3|Adaptive prefill plus phase placement plus owned ring|39900|tested-not-adopted|
|C4|Release obsolete synchronized scheduler before replacement|40700,42900|adopted; production verified|
|D1|GPU-generated indirect hit-path capability|selected-driver source screen|selected-driver-capability-failure|
|D2|Matched trained MTP auxiliary first slice|40900,41900,42500,43300,43800,44100|first-slice-tested-not-adopted|
|D3|One-layer/rank shared basis and residual|39096,41300|first-slice-completed-not-selected|

The complete measured scope and disposition of each row is in `post-top2-adoption-20261101.json`. Earlier failures and refusals remain in `post-top2-worklog-20261101.json` under `candidate_attempt_history`; they are not timing samples or physical-impossibility claims.

## Selected changes and concrete implementation

- `tools/build_post_top2_submission.py`: `PostScopedNodeCap` scopes the actual selected Vulkan provider's `ggml_backend_vk_graph_compute` to256 nodes and restores the app's original1-node setting afterward. The original flop divisor40, shader math, true dependencies and completion rules remain. Cases35100/35900/37300 have14 complete requests, four fixed semantic tasks and exact full F32/routes/tokens. Actual final normal maximum is163 nodes, with44,091 candidate submissions. Divisor10 is negative and excluded.
- `tools/build_post_top2_output_model.py`, `tools/build_post_top2_output.py`, `native/app/output_plain_segments.h`: output Q8_0 becomes Q4_0,675430400 to357580800 bytes.108 existing resident Q4 matrices are unchanged; the selected total is109. Cases31600/34700/35400 bracket four same-cap Q4 replays; every Q4 replay is faster than every Q8 group, with0.46125% mean shorter whole time. Four fixed semantic tasks pass. Cross-format full-vocabulary KL and broad quality preservation are unmeasured.
- `tools/build_post_top2_startup.py` and `tools/build_post_top2_pack_seal_reuse.py`: require two quiet admitted startup observations rather than a fixed five-second wait; bound the wait and retain physical/OS checks. The measured settle interval drops5.006610326 to0.100198499 s. Reuse the prior native whole-pack SHA seal only after fresh read-only named-inode/descriptor/EOF admission. Final normal actually reuses one seal; a fresh whole-pack hash is explicitly not claimed. Startup savings are not advertised as decode speed.
- `tools/reuse_post_top2_scheduler_lifetime.py` and `tools/build_post_top2_normal.py`: after existing synchronization, release the obsolete `llama_context::sched_new` scheduler and reserve graph before constructing their replacements. Case42900 shows167837696 bytes of simultaneous obsolete metadata eliminated. Its GPU-greedy experiment becomes runnable but remains slower. This is a same-cache memory improvement; no standalone speed gain or160MiB final-normal reduction is claimed.
- `tools/build_post_top2_normal.py`: composes the actual normal API/display entry and1024-triplet sealed-pack owner from36820 with the exact selected37220 GPU object and34620 output plan. It keeps3712 active slots/3713 physical planes, F32 KV/recurrent state, BF16 PLE convolution, CPU512MiB and original physical completion rules. `tools/finalize_post_top2.py`, `tools/post_top2_production.py` and the `tools/prepare_first_case.py::qualified_control` branch admit this exact new composition without weakening the preceding production validator.

## Important negative results and limits

N1/C1 actually execute22 GPU selections per timed candidate and preserve exact complete rows, but whole time grows4.62039%. Even fully hiding the measured26.5ms observer plus0.873ms full-logit transfer cannot offset either114.6/177.5ms observed delay. Fully deferred CPU validation is therefore screened by a measured upper bound, not falsely reported as implemented.

R1's180-graph fixture is faster, but the full model's816 actual dispatches per timed request produce0.05274% longer whole time. R3's216 actual two-token GDN selections give only0.26195% whole-time reduction within variation. C2 executes both kernels in two14-request cohorts, but one paired whole-time result regresses in each and mean gains remain smaller than A/A spread. Kernel-only or decoder-only eligibility flags do not override the whole-time criterion.

N4, R4 and C3 complete their changed prefill/held-out placement/ring scopes; the combination is8.72095% slower. More cache slots are not separately replayed against a trace with no eviction; the same3712-slot lifetime improvement dominates increasing transient allocations for this workload.

D1: pinned `driver/ps5vk_compute.c::ps5vk_CmdDispatchIndirect` reads arguments on CPU at recording time and explicitly refuses GPU-written arguments in the same command. The planned GPU-generated indirect path requires driver/backend changes. This is a selected-driver limitation, not a PS5 hardware impossibility. See `post-top2-indirect-feasibility-20261101.json`.

D2: trained layer48 actually executes with a shared loaded model,10240-element HC state,1088-node auxiliary graph, no auxiliary rollback and target-verified proposals. The original `n_ubatch > n_keep_tail` assertion came from the hybrid recurrent rollback splitter, not PLE. An already mapped624.125MiB heap hit the512MiB software shader guard; explicit672MiB repricing enables completion. Case44100 completes14 requests/four semantic tasks with exact independent matched MTP full-row SHA/tokens/routes. Timed candidates make10 MTP calls each; total12 proposals accept10/reject2, including history proposals. Auxiliary work costs0.694-1.382 s in retained requests; whole time grows26.33546% and decode drops22.15224%. No unverified draft token is emitted. This stateless first slice is not selected; stateful/prewarmed alternatives were not tested and are not declared impossible.

D3: the declared one-layer/rank first slice completes180 native F64/canary graphs. Shared rank32 Q8 basis/factors plus TQ1 residual reduce triplet bytes22.1667%, but GPU backend graph wall time is1.567-2.053 times original, with substantial weight approximation. Full-model cold-I/O tradeoffs, answer quality and speed remain unmeasured; a full-model regression is not inferred from this fixture.

## Memory and provenance

Final normal peaks: CPU503382016 bytes, post-load GPU ledger6167724032 bytes and actual workspace8388608 bytes. The6199160832-byte post-load ledger excludes preloaded resident model weights and separate staging; it is not total physical memory. Expert cache remains5703659520 bytes. Output payload savings are not silently converted to additional cache slots.

Application relink source: `97de33bab429618475d250c9e0bc4a71f06469ed`; SELF `2d66ba58810a7c0502564fb7c9181f25e8c2355f34925934f54f43bf20c4ecb9`; selected GPU object `b05d8e998a60f36b6eb40624a601d740022d921bae399eb332cd3c9ed9ce57d9`; model receipt `46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426`.

Driver: `akiba-tokyo-jp/PS5-Vulkan-Inference`, revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, archive `67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9`. Exact native source/header/object hashes and complete artifact fingerprints are retained in the linked receipt and adoption JSON.
