# AMPR and Kraken candidate validation — 2026-11-01

The current AMPR path is not executable in the observed payload context: all
three existing paths return `-1 / EOPNOTSUPP(45)` before an APR file ID is
created. Kraken preserves the sampled Q2 weights exactly and reduces the
materialized host envelope by 4.2553%. Neither candidate has demonstrated a
PS5 model speedup, so production is unchanged.

## Scope and evidence

Two fresh CPU-only native helpers completed positively and their PIDs retired.
No APR reads, GPU work, model/title launch, module loading, driver integration,
restart or CI run occurred. Native `IO_submits=0` log fields refer to APR
submissions; ordinary `pread`/write operations did capture the weight samples.
The console firmware was `0x12400009`. Private evidence cases are `60010`
(symbols), `60030` (paths and samples), `60110` (host codec comparison), `60120`
(persisted envelope) and `60130` (final readback and corrected interpretation).
Aggregates are in [the machine-readable report](AMPR-Kraken-validation-20261101.json).

### AMPR: symbols exist; the tested backend cannot resolve the files

All six `sceKernelApr*` functions were found through SDK `dlsym`, including
resolve, size/stat, submit, submit-and-result and wait. The six tested
`sceAmpr*` command-writer symbols were unresolved in that search scope.

Own-module handle lookup returned `-1 / EINVAL(22)` even for the kernel
libraries. That lookup is inconclusive, not evidence that those modules or
the APR kernel functions are absent. The first private parser incorrectly
excluded the SDK lookup from its completeness flag. Raw evidence is retained;
`tools/analyze_ampr_kraken.py` and the final report correct this interpretation.

The next helper called the resolver once per independently existing path:

| Path role | Return | errno | Output canaries |
| --- | ---: | ---: | --- |
| Current program, canonical installed path | -1 | 45 | Intact |
| Program through the title-system alias | -1 | 45 | Intact |
| Current immutable Q2 Expert bundle | -1 | 45 | Intact |

No valid ID was produced, so `GetFileSize` and read/completion submissions were
not attempted. This closes the proposed 1/2/4-read batch benchmark as
**not executable through the observed context and storage paths**. It does not
prove hardware absence or identify whether title permissions, filesystem/PFS
integration, firmware support or another backend requirement causes the refusal.
A valid native file ID is the prerequisite, not a relaxed memory threshold.
Repeating the same refused resolution would add no evidence.

### Kraken: actual current weights, lossless host experiment

Sixteen Expert triplets were captured from sixteen spaced parts of the current
66-part sealed bundle. Each source identity matched before/after direct reads.
The helper used one aligned 64 KiB window. Host downloads matched every native
padded SHA256 and the exact 24,641,536-byte EOF. No quantization or model
conversion occurred. This is a dispersed sample, not a whole-model result.

Each triplet contains 1,536,000 useful bytes and occupies a 1,540,096-byte aligned
record. Independent 64/128/256 KiB codec blocks were compared with Huffman arrays
off/on on four samples. Without Huffman arrays all tested blocks fell back to
raw storage: zero physical-size reduction. All three Huffman pilot settings
reached the same aligned size. The first two tied settings were expanded to
all sixteen samples, avoiding a redundant third full comparison.

| Codec block | Samples | Original aligned bytes | Compressed payload bytes | Envelope aligned bytes | Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64 KiB, Huffman | 16 | 24,641,536 | 23,443,777 | 23,592,960 | 4.2553% |
| 128 KiB, Huffman | 16 | 24,641,536 | 23,439,991 | 23,592,960 | 4.2553% |

All in-memory round trips were byte-exact. The 128 KiB result was also written
to a 23,592,960-byte file and reopened by a separate process. Header/index/range,
padding, EOF and all sixteen decoded payloads matched. Its SHA256 is recorded
in the JSON report. The envelope has a 32-byte record header, 24-byte block
index entries and one final 16 KiB alignment per Expert. It is an experimental
host envelope, **not a PFS package or a qualified AMPR/hardware input format**.

One Expert would still be read as one contiguous record. The proposed I/O
command count is unchanged; internal codec blocks must not become separate
SSD requests. The 128 KiB design needs 12 decode calls per Expert versus 24
for 64 KiB. Actual kernel/NVMe request counts were not measured.

Managed host decode totals were 154.0739 ms and 147.7875 ms respectively.
These are host CPU measurements, not PS5 CPU/hardware decode performance.
The measured quantity is stored size; neither PS5 SSD-wait reduction nor model
tokens/s improvement was measured. Even free decoding gives only a 4.4444%
ideal bandwidth-only improvement for these sampled records; request latency,
unaffected work and decompression reduce that benefit. This is not a whole-model
speed prediction. A different encoder may produce different ratios.

## Adoption decisions and next implementation boundary

| Candidate | Disposition | Evidence needed to reopen/adopt |
| --- | --- | --- |
| AMPR read + completion batch | Current execution path unavailable; no production change | A changed, documented context/backend that resolves a current weight file to a valid native ID; then one exact bounded read, followed by matched 1/2/4-read + completion timings |
| Kraken independent chunks | Host lossless format/size check passed; production not qualified | An actual accessible PS5 decoder and exact output on these same chunks, then read + decode + delivery timings and matched normal inference showing improvement |

There is no arbitrary minimum percentage for adoption. Both candidates must
improve matched end-to-end measurements beyond the current control variation,
preserve exact decoded weight bytes, and retain positive completion and ordinary
close. Size reduction alone does not establish faster inference. The current
interface limitation blocks hardware Kraken timing; it is not reported as a
successful hardware test or a measured lack of benefit.

Implementation belongs primarily in this LLM repository:

- `native/app/completion_source_io.h`: a future APR source backend would replace
  the reader operation while preserving `submit`, first-positive `take(false)`,
  buffer ownership, `release` and `stop_completed`. One final event for a whole
  batch can delay earlier consumers; compare per-read visibility separately
  from submission count. Do not feed emulator command structs to native APR.
- `tools/KrakenChunkBench.cs`: `Main` builds independent codec blocks and the
  experimental envelope; `Verify` reads persisted records and checks exact
  decoded bytes. A production converter would add an immutable index and a
  qualified decoder behind the existing staging-buffer path.
- `native/qwen_flash_next/ampr_capability_probe.c` and
  `ampr_path_sample_probe.c`: prerequisite observations, not inference backends.
  `tools/build_ampr_capability_probe.py` produces fresh, bound CPU-only helpers;
  `tools/analyze_ampr_kraken.py` prevents symbol/host-result overclaims.

A Vulkan driver modification does not fix APR path resolution. Keep the current
driver/profile and cache policy. Only a later demonstrated direct-to-GPU path
would justify separately scoped driver memory/coherency/synchronization work;
the first usable APR comparison should retain the existing staging and copy.

## Source provenance

- [drakmor/ampr_emu, cfa85df: APR kernel bridge](https://github.com/drakmor/ampr_emu/blob/cfa85df379f6eeeb165d7badf9b648e266fe77b7/src/ampr_emu_apr_kernel_bridge.cpp)
  and [native command packing](https://github.com/drakmor/ampr_emu/blob/cfa85df379f6eeeb165d7badf9b648e266fe77b7/src/ampr_emu_command_packing.cpp): API signatures and future encoding reference; software emulation is not native hardware evidence.
- [AnyPS5, ba627802: GuestAprRead](https://github.com/boykopovar/AnyPS5/blob/ba627802e2210187d417deb64c8f2fed8e33011f/core/libs/tests/GuestAprRead.cpp): independent API-call signatures, not a native command-layout guarantee.
- [LibProsperoPKG, 748eabf: EncodeBlock](https://github.com/SvenGDK/LibProsperoPKG/blob/748eabf1b7d17819528cabf367d8e27109d8fce3/src/LibProsperoPkg/PFS/Compression/Oodle/OodleKrakenEncoder.cs#L183)
  and [DecodeBlock](https://github.com/SvenGDK/LibProsperoPKG/blob/748eabf1b7d17819528cabf367d8e27109d8fce3/src/LibProsperoPkg/PFS/Compression/Oodle/KrakenDecoder.cs#L78): the actual host codec.
  Seven codec sources and LICENSE/NOTICE were fetched; every Git blob was
  verified. No keys, package resources or proprietary codec DLL were fetched.
  Upstream notices remain in the host cache; no codec binary is committed.

## Final state

The installed program and five current settings passed final whole-file SHA256,
size and EOF readback. Program SHA256 remains
`56c29e9c871f5b068181675353c9098a4ff3513c29b00bb5dc4c1840897c0126`.
All five new remote helper/log/sample artifacts were archived and deleted;
directory absence and zero native owners were verified. Production weights,
program and driver were not modified. The existing driver remains
`872cc1264ad8ba5d6b888b092968fa5858a38c58 / cumulative-idle`, caches disabled.
Four focused host interpretation tests pass; manual native and codec builds pass.
