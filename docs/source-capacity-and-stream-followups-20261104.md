# Source capacity and inference IO follow-ups, 2026-11-04

The primary metric remains `(generated_tokens-1)*1000/decode_ms`, reported
separately for cold, retained and exact-prefix requests. All remaining IQ2
model experiments are complete as of2026-11-05. None is adopted; production
remains R1+P1.

## Final model results

| Profile | Cold tok/s (change) | Retained tok/s (change) | Exact-prefix tok/s (change) |
| --- | ---: | ---: | ---: |
| Recorded P1 control65400 | 10.479220 | 12.093470 | 13.390932 |
| Up minimum stream | 8.971814 (-14.385%) | 11.445104 (-5.361%) | 13.227152 (-1.223%) |
| Gate-Up minimum stream | 9.005970 (-14.059%) | 11.877638 (-1.785%) | 12.632911 (-5.661%) |
| Down full-plane | 5.725340 (-45.365%) | 9.042587 (-25.228%) | 11.262401 (-15.895%) |
| Down source-prefix | 5.661682 (-45.972%) | 9.035292 (-25.288%) | 11.097403 (-17.127%) |
| Down minimum stream | 6.390577 (-39.017%) | 10.984585 (-9.169%) | 12.224860 (-8.708%) |

These are single screens, not matched means. The original Up/Gate-Up
MMVQ-off/on profiles below were also slower. Every completed model case has
exact22 token IDs/output bytes, ordinary close and exact P1 restoration.
All three minimum-stream IO comparisons pass69 complete vocabulary F32 hashes
and ordered routes against the same quantized model, with1043/1068/1044
streamed groups for Up/Gate-Up/Down. These observed IO timings are not used for
the observer-free rates above. The completed Gate-Up plain observation and both
prebuilt Down models were reused without replay or recompilation.

Final evidence is in65564/Gate-Up/first-screen.private.json and65567/Down's
full-plane-screen.private.json, source-prefix-screen.private.json and
stream-followups/Down/first-screen.private.json. All previously pending
profiles are resolved. No new IQ2 adoption, heldout quality claim or additional
decode gain follows. Further improvements remain possible outside these
tested configurations.

## Final artifact retirement, 2026-11-05

PS5 cleanup65572 removes five unselected IQ2 namespaces:444 source files,
32,192,794,023 logical bytes, plus three closed fixture/prototype inputs totaling
74,416,128 bytes. Positive receipts preserve every completed deletion. A host
alias-check error after the first40 files is corrected without replaying those
deletions or the three completed component deletions. The final native helper
confirms all five roots absent in both physical and alias namespaces, hashes
the selected seven files, exits and removes its own files. Cleanup performs no
title launch, GPU work, mount change or runtime initialization.

PC cleanups65573/65575 remove 7,152 unselected trial binary files
(71,543,433,510 logical bytes). This sum is not an allocated-space claim;
hardlinks can share storage. All947 canonical rebuild inputs and current-file
hashes remain unchanged. Authenticated original BF16 source identities remain
unchanged without another full-source hash pass. The additional133 trial copies pass complete current-content SHA256
verification and have no canonical path/file-identity dependency before deletion.
Source text, logs and receipts remain as evidence. The active runtime and selected source namespaces, including
their existing placeholders, are preserved. No unselected shared input remains
pending. All owners are retired; the console is idle with R1+P1 restored and no
unknown completion.

## Archived checkpoints

The following observations retain their original scope. Their active-owner,
queued-build and pending-rate statements are historical and superseded above.

Checkpoint65568: Gate-Up minimum streaming passes the actual native IO
comparison: all69 full-vocabulary F32 hashes, ordered routes, tokens and output
bytes match the SAME quantized model's plain path.1068 streamed groups execute.
Both observations close ordinarily and restore the exact selected P1 files.
The completed plain observation is reused; only its previously unlaunched
stream counterpart runs. The observer-free timed model builds and its first
native speed case is active.
Down full-plane65559 and source-prefix65561 both build PC-only and will be
reused by the already queued65567 successor. Two positive and12 invalid
prebuilt-profile controls prevent unnecessary recompilation or scope mixing.

After the plain model, the old Down and original-complement pools finish their
remaining188/1234 windows with zero resident pages. All five old pools are
exhausted and remain unchanged. The next stream preflight refuses before any
publication or launch below7374 pages. Cleanup65560 removes two exact inactive
staging images (54067200 bytes), preserving current-seven hashes; free pages
remain3300. This removal alone supplies no RAM or inference gain.

The completed plain model supplies a materially different source-read owner:
all13685 source windows complete, device live bytes reach zero, and ordinary
exit/current-file restoration pass. New eligibility is bound to that EXACT
latest model, compiled SELF, recipe, sealed input set and positive closure.
A persistent per-model ledger refuses duplicate case keys, reset prefixes,
pending helpers, no-read fixtures and incomplete owners. Low free pages or a
refused launch cannot create another owner. Physical ranges may overlap an
earlier owner's inputs after an actual new model read; this fact is explicit,
and old pool cursors are not reset. This narrows the earlier blanket no-rescan
rule to the actual completed read owner. It does not claim exact per-range
read attribution or permit arbitrary cache epochs.

The native cache body remains byte-exact:64MiB readonly maps,8MiB sync extents,
128 calls/20 seconds, unchanged1154 cache floor, positive identity/canary/unmap/
descriptor retirement and no mapped data touches. Model admission stays7374.
Host65562 binds the actual positive read owner and rejects eight invalid owners
and four invalid ledger states. First native65563 processes23/3805 eligible
windows with127 sync calls:5856 resident pages become zero, free3090->8945.
Every source/FD/mapping/helper completes positively; original ledgers remain
intact. No exclusive global RAM attribution or inference gain is claimed.
Continuation65565 also rejects six invalid archived observations, preventing
the successful plain case from being rerun. Remaining cases can use only a
different actual completed model owner or the unscanned suffix of the SAME
owner, retaining its exact prefix through the new registry.

Checkpoint65557: new source-seal65554 completes all101 files with whole
physical/alias SHA256 and EOF, unchanged518 selected parents and unchanged
parent directory snapshots. Its helper exits and its files are removed. The
original65355 publication points to this new positive native result; its
original zero-operation refusal remains intact. The four actually consumed
cache windows bind to the sealed identities and appear in the queued65537
Gate-Up config before both source owners clear.188/192 Down windows remain.
The existing coordinator starts the Gate-Up phase, followed by Down; no new
coordinator, upload or completed model comparison is started again. Inference
rates for those remaining profiles are still pending.

Checkpoint65556 (2026-11-05 JST): all101 Down files are positively transferred,
including all48 carriers. The original seven successful stores are preserved;
the disconnected partial is restarted once and no completed payload is sent
again. The original whole-source sealer exits positively as a returned refusal
before any metadata operation:1196 free pages versus its unchanged1201 floor.
Its result and helper retirement are retained; that submission is never replayed.

Read-only native metadata65545 observes exact root-owned0777 staging files.
These acquire0644 permissions only after whole physical/alias SHA256 and EOF
sealing. Corrected cache helper65546 checks all48 identities but scans zero
windows at1113<1154. Compact diagnostic markers65549 reduce the helper journal
from469857 to9777 bytes, preserving the actual read/returned state, per-file
completion counts, SHA/EOF, identity, clock and admission bodies. It still
scans zero windows at1117<1154. Both helpers exit and remove their own files;
neither supplies a RAM or inference gain. No unchanged refused scope is retried.

Cleanup65551 removes the exact57327616-byte archived Down fixture input after
positive ordinary fixture exit. Cleanup65552 removes20 whole-hashed console
report copies from five positively closed cases. PC originals and archives
remain retained; both aliases disappear, the runtime directory owner is
restored and the current seven files pass native hashes. Neither cleanup
changes a selected or pending model source or a snapshotted parent directory.

In that changed state,65553 retires four previously unscanned Down windows,
235929600 bytes, using29 sync calls:14400 resident pages become zero and free
pages increase2613->17013. All canaries, identities, readonly mappings, file
descriptors and the helper retire positively. Source writes and mapped data
touches are zero. The existing1154 cache floor,1201 source-sealer floor and
7374 model floor are unchanged.188 of192 Down windows remain unscanned.

New source-seal scope65554 now runs the exact original101-file context with
the original262KiB window,97-page margin and additive OS admission. Its
submission is separate from the original zero-operation refusal; total source
sealer submissions are two, with no payload retransmission. Only the same
helper is collected after the existing350/180-second quiet intervals.
After positive sealing, the controller must bind the four consumed windows
to the sealed inode/ownership/size/mtime and whole hashes, explicitly allowing
the expected0777->0644 and ctime transition. Host controls65555 pass two
positive and eight changed-source negative cases. This cache prefix is handed
to the already queued65537 successor before source ownership clears. These
are readiness/source results, not additional inference-speed measurements.

Checkpoint65538: the minimum-request Up stream passes actual native IO
equivalence. All69 F32 vocabulary rows (248320 columns), ordered routes,
tokens and output bytes match the SAME quantized model's plain path. There
are1043 actual streamed groups; both cases close and exactly restore P1.
The separate observer-free first screen is:

| Condition | Recorded P1 control tok/s | Up minimum-stream tok/s | Change |
| --- | ---: | ---: | ---: |
| cold | 10.479220 | 8.971814 | -14.384711% |
| retained | 12.093470 | 11.445104 | -5.361290% |
| exact-prefix | 13.390932 | 13.227152 | -1.223067% |

This improves the earlier unadopted Up implementation but remains slower
than selected P1 in every condition. It is not replayed or adopted. These
are single screens, not matched means; no physical-byte reduction is claimed.

Gate-Up's plain observed package is built but its native preflight refused
at5111<7374 pages, before staging/launch. The added Gate/Up source-cache pools
are exhausted and their final returned free6497 is below admission. The
independent, prepared Down source placement therefore runs first. Its new
source-cache pool will be available after positive whole-source sealing.
Gate-Up's minimum-stream observed package65535 is prepared PC-only, with no
additional native model/codec replay.

The successful original complement also retains1234 UNscanned windows:
PC65536 reconstructs the current582-file/6076-window geometry exactly and
preserves all three original read scopes and22 completed complement scopes
(4842 windows). Five new invalid handoffs/pools refuse;65538 confirms the main
pipeline dispatches the unscanned suffix after an exhausted primary pool.
These controls perform zero PS5 operations. No consumed range is re-entered.
The same existing native bodies keep64MiB readonly mappings,8MiB sync extents,
128 calls/20 seconds, no source writes and unchanged7374-page model admission.

Coordinator65537 waits only on PC receipts until the owned Down publication
positively seals and clears its IO owners. It then runs the remaining
Gate-Up profile and Down screens. Completed cache prefixes pass between
roles; duplicate pool keys refuse and the Down fallback ledger excludes its
primary pool. No source upload or completed native case is resubmitted.

Checkpoint65531: all124 Gate files, including all48 large layer files, are
placed and positively sealed through whole physical/alias SHA256, EOF and
parent identities. No completed source payload was retransmitted. The first
full Gate-Up MMVQ-off/on screens complete all three requests with exact22
tokens and bytes, ordinary close and exact seven-file P1 restoration:

| Condition | Recorded P1 control tok/s | Gate-Up MMVQ-off tok/s | Change |
| --- | ---: | ---: | ---: |
| cold | 10.479220 | 7.986276 | -23.789400% |
| retained | 12.093470 | 9.982410 | -17.456196% |
| exact-prefix | 13.390932 | 11.722984 | -12.455800% |

The independent MMVQ-on screen is8.009480/10.003726/11.633629 tok/s, changes
-23.567978/-17.279941/-13.123080 percent in the same three conditions.

This is one screen per arm, not matched means or a speedup qualification.
The clearly slower version is not replayed or adopted. Its first host-only
startup preflight had stopped before any publication/launch because pretty
JSON occupied1063907 bytes. Compact serialization preserves every field and
value while fitting1010366 bytes under the UNCHANGED1048576-byte native bound;
actual PC startup preparation passes in65526.

The built MMVQ-on variant subsequently refused BEFORE staging/launch at5565
free pages versus the unchanged7374-page admission. Coordinator65530 resumes
only unscanned Gate source-cache windows after the first completed window.
The next21 windows retire positively (5856 resident pages, no source writes,
all mappings/FDs retired), with10403 free pages returned and170/192 windows
remaining. Only this changed state admits a new startup attempt. The existing
MMVQ-on build and completed MMVQ-off screen are retained. Main Down screens
now use the same finite readiness-only continuation as stream follow-ups;
unknown completion never permits a retry. Stream native IO and all remaining
rates are still pending. Production remains R1+P1.

Supervisor65530 stopped after spawning the second startup child because its
exclusive owner-log filename was reused. The SAME startup child completed
one accepted launch (app32792). Collector69318 used `--collect`, completed
the existing three-request case and ordinarily restored all seven files;
no publication or title launch was repeated. Supervisor65531 now uses
distinct per-phase owner receipts and checks absence before dispatch. It
continues the Up/Gate-Up streaming follow-ups and then Down under one owner.

The Gate source writer stopped during file7 with `550 No space left on
device`. Its first six positive whole stores remain reusable. No native sealer,
title or GPU operation had started. The exact146735104-byte partial file was
positively removed once in65500. Unrelated project models were preserved.

The first unused-chunk cleanup65509 refused before any data write and retired
normally. Read-only diagnosis65510 found that each512MiB BF16 chunk occupies
an additional64KiB of allocation metadata; all630 protected files were present.
Corrected65511 reclaimed52 chunks outside all current and prepared source maps,
including inode-alias exclusion. It verified zero remaining size/allocation,
positive close, unchanged protected stat identities and preserved directory
entries. Authenticated complete PC originals remain retained. Logical release
is27917287424 bytes; verified allocated release is27920695296 bytes.

The65513 coordinator preserves all six original receipts and resumes only the
uncompleted suffix. Reclaimed bytes alone cover the remaining20444524558 bytes
for both Gate and Down plus1GiB. Each positive suffix store gets a durable
receipt. The existing262KiB native sealer is submitted once after all stores;
whole physical/alias SHA256, EOF and unchanged parent identities remain required.
The source transport is unchanged. Byte progress is local host logging.

The inference follow-up reuses the original four source leases and8MiB scratch.
It enables format-checked streaming and skips positively delivered Experts in
the generic loop. The initially prepared Up/Gate wrapper requested537600 bytes
while uploading422400 IQ2 bytes. The unsubmitted wrapper is now superseded:
65517/65518 use the owner's smaller accepted460800-byte request, leaving38400
unused requested bytes instead of115200. The original type-agnostic owner,
cache, weights and scratch remain unchanged. This overfetch is
explicit, and no reduction in physical source bytes is claimed. Down requests
already have accepted sizes. The original owner SHA256 remains
`f87f931a6a537cf32f8e1d92678182cdbc8db5c9f624cdec84b009ed4e86b02e`.
Its range, EOF, overlap, identity and positive-completion guards are preserved.

Observed Up packages65514/65519 compile, link and package against the actual
selected PS5 ABI. All three compiled stream providers pass source admission;
eight new invalid model/cache/observer/slot combinations refuse. These are
PC results, with zero native/codec test replays. Native equivalence and speed
remain pending.

The minimum-request host controls separately exercise both layouts, all four
group sizes, exact destination canaries,24/28 negative boundaries and a newly
accepted460800-byte logical suffix. Physical read extents still round to16KiB
and must fit the backing file; insufficient physical padding still refuses
before any callback. Gate reuses the completed Up control
matrix. Four new malformed minimum-size/accounting/source bindings refuse.
The original larger-request prototypes were never executed on PS5; changing
them before the first native comparison avoids extra model runs and transfers.
Supplement65523 tests those two bounds separately at four aligned source
offsets: eight new positives and ten new EOF/range negatives across both
layouts, with exact destination canaries. The old wrapper matrix and native
graphs are not repeated; the runtime wrapper, cache and native builds stay
unchanged. These are PC boundary controls, not native IO/speed evidence.

Existing65384 single-pair data also supports prioritizing this IO refinement.
Retained decode increases1736.4743->2244.0216ms, while whole-request producer
wait increases443.7894->951.3900ms. Exact-prefix decode increases
1568.2254->1694.6523ms while producer wait increases151.2013->267.0175ms.
The source interval covers the whole request and is nested, so these numbers
do not establish decode-only causality or replace the primary tok/s metric.

After the two original Gate screens, the same coordinator compares plain and
streamed Up, then Gate-Up. It subsequently places Down and runs its full-plane,
prefix and streamed profiles. The additional IO comparison uses the same
quantized model on both sides:69 complete vocabulary-row hashes, ordered routes,
tokens, bytes and ordinary restoration must match, and actual stream groups
must execute. Only then can an observer-free speed screen run. Clearly slower
screens are not repeated. Promising candidates receive fresh ABBA and the
existing heldout quality tasks before adoption is considered.
An ordinarily closed counting/finite negative is recorded without timing and
the next independent profile proceeds. Unknown owner completion still stops
the sequence; it never authorizes another native operation.

Completed Up cases65407/65388 were collected35.297/34.851 seconds after their
launch helpers, with nine observations each. Remaining model cases use the
existing35-second host-quiet option before initial collection. This reduces
repeated observation traffic during the finite workload without changing its
metric, source, arithmetic, readiness or positive-close requirements. A first
screen against the older control remains provisional; any adoption needs a
fresh matched control using the same observation policy on both sides.

Every changed native scope keeps fresh7374-page admission, positive owner
completion and exact P1 restoration. Cache retirement uses only unscanned
windows, recorded in a shared ledger, including the five remaining final-four
Up windows after the exact11-window65371/65375 prefix. Its16384-page target is optional headroom,
not a new model launch threshold. The driver remains
`872cc1264ad8ba5d6b888b092968fa5858a38c58` / `cumulative-idle`, with persistent
shader/pipeline caches disabled. Initialization63121 remains consumed; no
reboot or recovery is required or requested.
