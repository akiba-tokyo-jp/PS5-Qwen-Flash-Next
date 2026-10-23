# Disjoint native source addresses

The fresh-boot full SHA passed before a returned reservation rejection. See
[the complete sequence and recovery](native-full-model-progress-20261024.md).
The rejected fourth source span was 102,400,507,904 bytes. No backend, model or
GPU initialization was reached. Every attempted memory call returned.

A separate native CPU telemetry artifact measured `RLIMIT_AS` soft/hard values
of 9,223,372,036,854,775,807 and `RLIMIT_DATA` soft/hard values of 34,359,738,368.
Neither limit was changed. The Direct heap's virtual reservation was
137,438,953,472 through 154,618,822,656. The automatic allocator's chosen source
addresses were not recorded in the failed artifact, so an exact hole/limit
mechanism is not established by its returned error alone.

The replacement keeps source keys in [512,896) GiB, separate from the pinned
native driver's entire [256,512) GiB placement interval, its low shader window,
and the [128,144) GiB Direct heap. It uses fixed plus no-overwrite reservation
flags `0x90`, checks the exact returned address and verifies zero protection
across the whole span. An occupied interval is rejected without a search or
retry. Eighty bounded metadata entries support all 76 model files and temporary
probes. Completed releases return their exact owned intervals to first-fit reuse;
failed/unknown reservation, protection or release poisons the book and retains
its records for ordinary OS close. There is no physical allocation or file mmap.

The native artifact is 58,674,983 bytes at SHA256
`22e59575461767ba02a70de0379f75229a47c8277b7eda1e3a7023a6920c24d2`.
Its actual runtime imports and six-segment SELF roundtrip passed. On the PS5,
the 16 KiB probe returned exactly 549,755,813,888, verified zero protection,
completed release and saved its terminal result. Raw kernel free pages were
1,719 before and after. GPU calls were zero and no model was loaded. The exact
owner then normally closed and fresh complete CPU guards passed.

Host checks exercised actual native code with controlled APIs, four retained
failure cases, no speculative release, every real model span, overlap/exhaustion,
fragmentation and complete address reuse. All 76 spans fit the disjoint interval.
The original CPU kernels, engine overlays, model data and pinned driver archive
were unchanged. A post-source-release kernel/Flexible/CPU guard now precedes
backend initialization in the full-model path.

This tiny physical result does not qualify a 102 GB reservation, all simultaneous
source spans, resident memory, model loading or generation. The next case must
complete those native gates and every final restoration/readmission requirement.
Its SHA reuse is limited to this same boot and the positively unchanged sealed
model/receipt identities; old-boot sessions and integrity remain invalid.
