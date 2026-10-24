# PS5 source I/O workarounds

The current PS5 reproduces a same-file cross-region read conflict without GPU
work. Two completed parallel 3,293,184-byte reads across approximately 1 GiB
file-offset regions cost about 49 ms per pair; serial costs about 10 ms.
Independent opens do not help. Distinct-file parallel controls cost about 7 ms.
The loaded-native trace reproduces the corresponding slow subset at about
70 ms, with the other same-region pairs at about 3 ms. See
[the investigation](source-contention-investigation-20261024.md) for scope,
controls and the distinction between measured waiting and inferred kernel state.

## Primary-source search

The search checked PS5-specific implementations rather than transferring Linux
AIO, CUDA/HIP or generic NVMe advice directly. Exact public searches for
`BfsIpInd`, `BfsClSs1` and `BfsPWtFr` did not locate a documented fix for this
read pattern. Absence from these searches does not prove no other work exists.
The reviewed sources below provide relevant design constraints, not proof that
their remedies fix this project's BFS conflict.

| Primary implementation | Relevant behavior | Applicability here |
| --- | --- | --- |
| [BFpilot performance design](https://github.com/ItsBlurf/BFpilot/blob/93acd4b9486ba7d11208a26ff2db7dbb7386666f/docs/PERFORMANCE_STABILITY.md) and [copy code](https://github.com/ItsBlurf/BFpilot/blob/93acd4b9486ba7d11208a26ff2db7dbb7386666f/src/transfer.c#L749) | One sequential reader overlaps a writer through bounded aligned slots; filesystem identity and fatal I/O boundaries are checked. The design excludes indiscriminate directory writers and global sendfile/F_NOCACHE changes. | Supports overlapping different stages while limiting one source stream. It is not a demonstration of two same-file random readers or a measured repair for this conflict. |
| [ShadowMountPlus LVD/BFS contract](https://github.com/drakmor/ShadowMountPlus/blob/0794096dbfd5855d5b757e4708703671400bc9cf/include/sm_mount_defs.h#L61) | Type-5 LVD can batch exactly 64 KiB, aligned requests to a regular image on internal BFS, subject to provider guards. Other requests use the normal vnode path. | A real PS5-specific alternative path, but it operates on mounted disk images. Setting an ordinary pread size to 64 KiB does not activate it. It requires new image, mount, memory and lifecycle qualification; it is not the first candidate. |
| [zftpd v1.4.0 release](https://github.com/seregonwar/zftpd/releases/tag/v1.4.0) and [file I/O source](https://github.com/seregonwar/zftpd/blob/8f089a86208f55df326d0811c9e9505d87808df9/src/pal_fileio.c) | Filesystem-specific sendfile exclusions and a copy pipeline with one reader. Its copy-only source cache hints are explicitly separate from sendfile. The release also serializes PFS file creation. | These are different operations: network sends, sequential copies and O_CREAT metadata. Their cache hints, peak rates and creation-lock fix do not establish a cure for read-only BFS random pread. |

All citations are pinned to reviewed source revisions where available. No code
from these projects was copied into the source reader. These developer reports
are implementation evidence, not Sony documentation or a cross-firmware guarantee.
The BFpilot and zftpd paths differ in cache policy, so they do not justify
changing this application's qualified O_DIRECT path by analogy.

## Owner-supplied references

[CAPCOM's CEDEC2018 presentation](https://www.docswell.com/s/CAPCOM_RandD/598YPM-cedec2018)
targets PS4/Xbox One (slide 3). Slides 94..98 separate loading from decompression
and reuse decoded blocks; slides 33..44 compare synchronization costs and explain
the CPU cost of spinning on longer jobs. Useful transfers are stage overlap,
reuse within an existing budget, and measurement of handoff separately from work.
Their core layout, 256 KiB block size, 24-entry cache and game-specific hit rate
are not PS5/Qwen admission constants. Here, handoff is small while pread waiting
dominates. No spin-wait replacement, extra payload cache or compression is
introduced. The existing expert cache and read/consumer pipeline already provide
the corresponding layers; the new candidate concerns which reads may overlap.

The [official PS5 hardware support hub](https://www.playstation.com/ja-jp/support/hardware/ps5/)
links [M.2 requirements](https://www.playstation.com/ja-jp/support/hardware/ps5-install-m2-ssd/).
Sony specifies recommended sequential performance and states that PS5 does not
support HMB. These are relevant when qualifying an expansion drive, not a
guarantee for random model reads or an explanation of this internal BFS test.
The public pages do not document BFS indirect mapping locks or a parallel-pread
fix. No hardware purchase, drive migration, firmware update or recovery action
has been initiated from these references.

## Candidate order

1. **Preserve the admitted one-read pipeline now.** It already avoids concurrent
   same-file region changes, and overlaps the read with synchronous producer
   consumption. Keep the 8 MiB window, reserve predicates and positive completion
   ownership unchanged. This is the currently qualified workaround, not a new
   performance claim.
2. **Qualify selective parallel scheduling next.** Treat file identity and full
   aligned byte ranges as scheduling inputs. Serialize unqualified combinations,
   especially same-file different-region reads. Measure selected same-region and
   distinct-file combinations in a finite diagnostic before changing production.
   The 32 native trace pairs show why a universal depth of two is inappropriate:
   25 benefit but seven incur a large penalty. Do not infer a whole-model gain
   from the isolated per-pair improvement or from a theoretical recombination.
3. **Consider lossless smaller-file layout only if scheduling is insufficient.**
   Distinct-inode controls remove the observed conflict, so smaller immutable
   source files are a plausible physical-layout remedy. Hard links, dup and
   independent opens retain the inode and do not supply that separation. A
   layout candidate must preserve all BF16/F32 bytes, tensors, experts and PLE,
   validate exact offset translation across file boundaries, and provide a new
   integrity/transport receipt. No model rewrite or additional transfer has been
   started for this investigation.
4. **Defer new kernel/storage paths.** LVD image batching, AIO, read-ahead hints,
   cache flags and alternate media need their own applicability evidence.
   Higher queue depth does not remove a shared filesystem conflict by itself.
   An unqualified mount/cache change would add variables before the smaller
   application scheduling candidate has been measured.

The next scheduling gate must cover both full aligned ranges, near-boundary
reads, unknown file identity, same-inode aliases, failed admission and unknown
completion. There is no qualified production rule equivalent to comparing only
`offset >> 30`. Keep production `NativeReads::read_pair` rejected and maximum
outstanding reads at one until a distinct candidate passes its complete native
numeric/output, frame, retirement, ordinary-close and original-restoration plan.
No additional title launch is needed to document the completed cause finding.

The driver stays at `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`,
with persistent shader/pipeline caches disabled. A CPU-only reproducer is no
reason to alter the Vulkan driver during this isolation. These changes require
neither quantization nor reduced model components.
