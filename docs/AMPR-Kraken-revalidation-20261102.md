# AMPR and Kraken revalidation — 2026-11-02

The CPU entropy-chunk comparator completed on PS5 and was slower. AMPR read
submission and hardware Kraken timing remain unqualified. Communication was
lost during post-restoration readback; this campaign is **not complete**.
No candidate was adopted into the inference engine. CI and GPU calls: zero.

## Actual PS5 results

| Candidate | Observation | Disposition |
| --- | --- | --- |
| CPU decoding of captured Q2 entropy chunks | Exact output, 4.2553% fewer bytes, unchanged request count, approximately 97% greater total delivery latency | Measured ineffective; not adopted |
| Owned classic PFS | Original OS APIs created/mounted a 64 MiB image; complete 16 KiB control read matched | Filesystem prerequisite demonstrated, not hardware qualification |
| Root APR on owned PFS | -1/EOPNOTSUPP(45), intact outputs, no file ID | Measured rejection in this context |
| Native APR through owned readonly PFS view | Complete 16 KiB control matched; -1/ENOTTY(25), intact outputs | Measured rejection; nullfs forwarding and the underlying PFS handler are not isolated |
| AMPR read/completion and 1/2/4-read comparison | No genuine accepted native ID; no read submitted | Execution unavailable in the current session |
| Hardware Kraken on a compatible compressed source | No hardware request submitted | Execution unavailable in the current session |
| Native model comparison and deployment | No qualified faster candidate | Unperformed; no acceleration change |

## CPU delivery comparison

Sixteen real Q2 Expert samples contain 192 entropy-only blocks, each at most
128 KiB. The custom QKRK001 envelope is **not** a hardware-mountable PFS image.
The pinned GPL adapter supports this entropy coding, not arbitrary LZ Kraken
streams, and does not load a proprietary PC decoder.

Each Expert uses an ABBA sequence of raw/compressed/compressed/raw whole-Expert
reads with aligned reused buffers and O_DIRECT. Input identity and original
SHA checks precede timing; all decoded bytes match. Device cache state is
unspecified. These are neither cold-SSD measurements nor model tokens/s.

| Sum over 32 timed deliveries | Original padded | CPU entropy chunks |
| --- | ---: | ---: |
| Bytes | 49,283,072 | 47,185,920 |
| Requests | 32 | 32 |
| Read | 76.947130 ms | 74.607321 ms |
| Decode | 0 ms | 77.047451 ms |
| Total | 76.984256 ms | 151.654772 ms |

The 2.34 ms lower read sum does not offset 77.05 ms decoding. This CPU path is
rejected as measured ineffective. If every other cost were unchanged and
hardware decoding were free, the sampled byte reduction would imply only
about 1.044x bandwidth-bound read speed. That idealized bound is not a hardware
measurement or a prediction for the entire model.

The first host monitor watched an incorrectly constructed log name. The actual
positive END and helper absence were recovered without resubmission. The CPU
fixture and probe artifacts were removed. The corrected public builder checks
its declared log path and was rebuilt successfully for the PS5 target.

## Filesystem corrections

The full stable inventory had 1112 entries. The initial substring classifier
mistook tmpfs for PFS; it was corrected without replaying the inventory. The
owned classic fixture subsequently mounted as pfs/type164. Its mount name was
shortened from 94 to 78 bytes to fit the measured 88-byte target field.

A lower submount was not visible through the normal title alias. A bounded
native wait and authenticated helper attached one readonly owned view directly
inside the current sandbox. The first attach failed EPERM. The measured
filesystem role, limited to the helper's own process, and a root-owned empty
target allowed attachment. Helper auth and runtime-parent ownership were
restored. Native reads then matched all bytes; APR still rejected file-ID
creation. No synthetic ID was submitted.

Native END, ordinary return, PID absence and ordinary view unmount returning
zero were recorded. PID absence does not establish that asynchronous sandbox
teardown fully retired. Lifetime coordination must be redesigned before
another such trial. A teardown interaction is an unproven hypothesis for the
later communication failure. These diagnostics are not linked into production
and are not qualified for automatic filesystem experiments.

Direct compatible PPR or readonly compressed-PFS control tests remain
unperformed. Earlier PPR/long-name errors do not prove hardware absence.
Changing the command emitter cannot repair a missing genuine file ID.

## Hardware Kraken boundary

The acquired original Zlib module's symbols identify Initialize, Finalize,
Inflate, WaitForDone and GetResult. Public bindings describe zlib inflation
with at most 64 KiB output. No direct Kraken API was identified by this
comparison; other modules or compressed-PFS routes are not ruled out. No
invalid Kraken stream was submitted to zlib as a substitute.

Decoded system copies fail embedded whole-ELF verification and remain static
analysis observations. None was installed or executed. Console calls used the
original OS filesystem module through its loader.

## Interrupted restoration and remaining work

The original SELF was checked in its rollback location, and both restoring
rename operations were acknowledged. Source reconstruction locates the timeout
after those operations, inside the six-file whole-readback loop. Post-restore
verification and final remote cleanup are incomplete.

The separate base PFS fixture/backing image remains owned. Never delete its
backing while possibly mounted. Pending artifact identities remain private.
HTTP and FTP became unavailable; ICMP had no reply from the expected console.
Windows' success exit code for a local unreachable message is not reachability.
Discovery found one standby PS5 at another address, without an identity match;
no wake or launch packet was sent. Freeze, standby and network failure are not
distinguished by these observations. Reboot is unavailable.

First recover a positively identified channel, establish current boot and
ownership, finish original-file/settings checks and retire owned mounts through
ordinary APIs before removing backing files. Do not repeat consumed launches
or recovery probes. Then qualify changed direct PFS/PPR and compressed-source
prerequisites, bounded completion, matched I/O, and matched model throughput.
Hardware/model work is unperformed, not a measured ineffective result.

## Sources and provenance

- [AMPR ABI/encoding, cfa85df](https://github.com/drakmor/ampr_emu/tree/cfa85df379f6eeeb165d7badf9b648e266fe77b7).
- [ps5-sd-tool filesystem APIs, ef5df270](https://github.com/c0w-ar/ps5-sd-tool/tree/ef5df2706b1b1fda7395c0db24a0b0ab86f97799), [garlic-worker, e0cbe2d3](https://github.com/earthonion/garlic-worker/tree/e0cbe2d3d1127e21b3cb61bc286ba59ae8f96233).
- [powzix/ooz entropy decoder, 0503806](https://github.com/powzix/ooz/blob/05038060aa68f9187ae9923b2388ca8db40e58d1/kraken.cpp), blob a4983d6de308f92c4a7f71f8d0f87bb2bdc3cdd2; GPL notice retained.
- [Zlib bindings, SharpProspero 5dfdb4b](https://github.com/SvenGDK/SharpProspero/blob/5dfdb4b0b166e83dc9ae275001afb695f12c7174/src/SharpProspero/Interop/Compression/Zlib.cs), [OpenOrbis header 0a1aaf9](https://github.com/OpenOrbis/OpenOrbis-PS4-Toolchain/blob/0a1aaf9dd4a92695538bdeb09fb056d06dd11725/include/orbis/Zlib.h).
- [Compressed-image candidate, LibProsperoPKG 748eabf](https://github.com/SvenGDK/LibProsperoPKG/tree/748eabf1b7d17819528cabf367d8e27109d8fce3/src/LibProsperoPkg/PFS).

Production source remains 2b683814c9b6ed18c13352963c0a989f9e4d0b15. Driver
872cc1264ad8ba5d6b888b092968fa5858a38c58, cumulative-idle, is unchanged;
persistent caches remain disabled. No driver relink occurred. The companion
JSON lists evidence case IDs. Proprietary bytes, disassembly, library hashes,
endpoints and credentials remain outside commits.
