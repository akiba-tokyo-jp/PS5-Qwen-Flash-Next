# Physical CPU hash timing and model verification budget

On 2026-10-22, the reserved physical PS5 completed the bounded synthetic CPU hash
probe at application source `7875481b73a51ab04ce9d67917d8136b6db5b139`.
It reused the exact compiled SHA256 provider from the qualified native application.
Fresh CPU observations before and after passed with the same boot/services,
no native title and unchanged shared reservation. The probe modified no original
SELF or app directory. Three CPU helper submissions completed; no title launch,
model load, Vulkan initialization or GPU work occurred.

| Measurement | Result |
| --- | ---: |
| Synthetic buffer | 1 MiB |
| Independently digest-checked passes | 512 |
| Verified synthetic bytes | 536,870,912 |
| Native measured interval | 3.056937667 s |
| CPU hash rate | 167.4878770107418 MiB/s |
| Compute-only projection for 359,235,922,432 payload bytes | 2,045.4857919772546 s |

The projection is approximately 34.09 minutes before disk I/O. It shows that the
earlier fixed 30-minute whole-model deadline is inadequate for planning at the
observed rate. It is not a measured full-model file time, an integrity result,
TTFT or tokens/s. Cached synthetic RAM throughput does not qualify disk reads.

The next native model preflight uses a distinct v2 policy with a fixed two-hour
whole-model deadline, bound to this completed CPU probe. This is an initial
finite budget with I/O margin, not a measured full-file bound. Each split uses
only the remaining global allowance. Legacy v1/30-minute policies are rejected;
display, model loading, Vulkan and full inference remain rejected in this mode.
Previously preserved application binaries are not silently switched to this
updated policy.

Structured native progress now records file index/count, current and total byte
counts, elapsed time and the fixed deadline. A separate completed-file marker
follows a matched SHA256. The host parser distinguishes hashed bytes from
matched digests and still requires final native integrity/mapping reports.
It accepts only complete newline-terminated records with consistent monotonic
counters; a partially captured tail is not a completed observation.

Host checks passed: 17 actual-source timer/digest cases, all 14 probe imports
resolved through the actual qualified runtime exports, 172 negative execution
policy cases, nine progress-parser cases and the full 130-case Python suite.
The revised PS5 main object compiled. Its added C++ formatting symbol resolves
through the exact qualified static libc++ archive; it has not been linked into
a new application, packaged or executed for model preflight. Earlier failed
host build/overly narrow symbol-check records remain preserved.

Probe ELF SHA256:
`cbd7964f9b46e9e817bce99a53228058a0183d12cda901755fb4c3d13f2f181b`.
Probe source SHA256:
`7566190c19311f756c798f0c3252c27bd4583b408396ab8dd02b484f687ffa76`.
Exact native SHA object:
`5899071fb7022390f3e1d98d331dcd05439678ba622ad2308243260ed60929c8`.
Raw captures, private identities and runtime binaries remain outside Git.
