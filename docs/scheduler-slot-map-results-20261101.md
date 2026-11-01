# Scheduler-owned input storage and identical-map publication

The replacement passes an actual 48-graph CPU/Vulkan scheduler fixture, 14 matched
model requests and 12 normal/API requests in original/candidate/candidate/original
order. The measured winner is installed and admitted as production59800;
current-only SSD cleanup59840 and final native verification59860 are complete.
Generation speed is selected as the endpoint. All cases are consumed; a new
launch requires a fresh binding. Native/gateway/model are currently inactive.

| Normal condition | Original mean tok/s | Candidate mean tok/s | Change |
| --- | ---: | ---: | ---: |
| Cold generation |9.531683|9.622700|+0.954889%|
| Retained weights |11.273628|11.366228|+0.821386%|
| Exact-prefix repeat |12.334864|12.500280|+1.341043%|

Both retained and prefix whole-time/decode savings exceed the original normal
control A/A spread in both pairs. Initial TTFT increases 172.346 ms on average;
cold whole-request time also regresses. Do not claim every metric improves.
The generation-priority choice keeps this startup cost explicit. These fixed
22-token requests do not qualify sustained service or broad reasoning quality.

The 14-request matched model comparison has complete F32/routes/tokens equality,
identical source demand and four fixed semantic tasks. Its two retained whole
savings are 24.902865/13.945849 ms versus 4.539938 ms A/A spread, 0.860487% mean.
Nonempty submissions fall from 4423 to 3820. The internal control also owns dedicated
maps, so the independent original-normal ABBA remains essential. All 12 normal
outputs, actual ordered Expert routes and source bytes/calls are exact across
the four normal processes. Normal full vocabulary is finite and its configured
continuation comparisons pass; cross-program complete normal F32 row hashes
were not recorded and are not claimed. Eight actual native frames were viewed.

## Implementation and provenance

`native/app/scheduler_slot_maps.h` registers cache-owned guarded storage through
`ggml_backend_tensor_alloc` before scheduler graph allocation. The GGML input-copy
creation path in `ggml_backend_sched_split_graph` invokes this binding; allocation
and descendant-view initialization first see the final storage. The real
`llama_moe_cache::impl::copy` retains authoritative selected-ID download and
synchronization, cache planning and required weight loads. Its `publish` compares
all 512 I32 values and omits identical uploads without modifying a live tensor's
buffer, data, view or descriptor. One producer and cache lifetime are preserved.

The builder reconstructs the exact frozen 632a72dc backend source from pinned
llama.cpp 0a1ef309 and the existing source-reader patch, then changes input-copy
creation only. The model builder reuses the qualified scheduler provider; the
normal builder retains the actual original normal entry and other providers.
Compiled source is 2b683814c9b6ed18c13352963c0a989f9e4d0b15, normal build 59100,
SELF 56c29e9c871f5b068181675353c9098a4ff3513c29b00bb5dc4c1840897c0126.
Driver 872cc126/cumulative-idle, Mesa 1ba9874f, actual cold-table archive a325dcd4
and GPU math provider c26fadf2 remain unchanged. Persistent caches stay disabled.

Requested/reported map storage is 125440 bytes; actual measured additional device
peak is 2097152 bytes, not an assumed 128 KiB. CPU heap peak remains 503382016 bytes;
the candidate device peak 6169821184 remains below the 6199160832 cap. Precision,
3712/3713 cache geometry, source layout, all memory/OS/owner/completion controls
and all selected previous optimizations remain unchanged. SSD reads are unchanged.

## Current-boot recovery and verification corrections

The existing compatibility runtime and only the existing registered title's
missing volatile nullfs alias were restored without reboot, registration changes
or system-volume remounts. A CPU namespace refusal then identified a five-second
directory mtime/ctime difference. Native 58300 verifies 11 whole SHA256/identity/EOF
files, 518 complete unchanged source identities and two stable directory snapshots.
`model_directory_readmission.py` rebinds only those directory timestamp fields;
device/inode/mode/owner/length, recipe, certificate and part identities remain
exact. The cause is not proven to be cleanup. Other boots require fresh proof.

The old partial-bundle counter does not measure the selected broad T1 triplet
provider. Normal collection now requires positive actual T1 indices 0/1/2 and
T3 indices 7/8 while retaining graph reuse and every original numerical, source,
ownership and completion gate. A transient management-read timeout resumed only
the unexecuted preparation step. One CPU log collection used the wrong host path;
the positive result was collected from its immutable compiled path without
re-executing the helper. Neither event is a model/GPU hang or a speed result.

The old 57500 copy-callback rebinding remains rejected and was never replayed.
Its failure is not reclassified as successful GPU completion or a proven driver
fault. All new GPU lifetimes positively retire and ordinarily close before exact
control restoration. No reboot, force signal, manual GPU release/reset, CI or
agent delegation was used. Raw private evidence remains on the host data disk.

## Production placement and console retention

Placement59800 verifies both the original and candidate programs and five
settings each by complete native SHA256/identity/EOF before and after the
rename. The selected59400 program/settings are current. The old9824 program
and configuration remain archived on the host; no console rollback copy remains.

Cleanup59840 removes653 closed trial artifacts plus10 completed cleanup/readback
helpers and logs:663 files,244886177 logical bytes. Every file is durably archived
before deletion, and absence is verified. UID1 mode0600 diagnostic logs require
the existing `read_owned_logs.c` owner-UID behavior: PS5's root-effective helper
has no DAC override. Only the cleanup helper's effective UID is temporarily
changed; exact closed targets are made archivable and runtime ownership is
restored. Current protected files, model directories and other processes'
credentials are unchanged. The initial access refusals are preserved; acknowledged
deletions and consumed native helpers are not replayed.

Final59860 verifies11 whole files (current program, five settings and five source
certificates),518 unchanged source identities and stable snapshots in both
namespaces. Its process is observed absent before its own archived ELF/log are
removed. No extra model/GPU launch is used for cleanup or placement. One current
program and five settings remain. All current native/model/source owners are
retired, ordinary closes pass, and23 invalid installation/owner/profile states
are refused while the actual installed control is admitted. Private repository
visibility and disabled GitHub Actions are verified before publication.
