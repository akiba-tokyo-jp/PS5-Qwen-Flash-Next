# Physical PS5 comparison of 512 / 256 / 128 MiB files

The representative region did not become faster with smaller physical files.
Parallel pair means were **6.807 / 6.869 / 6.896 ms** for 512 / 256 / 128 MiB.
Keep **512 MiB as the provisional layout candidate**. This establishes neither
a PS5-wide optimum nor an inference tokens/s improvement. The complete model
has not been physically split or run with any of these layouts.

See the [allowlisted measurements](source-layout-size-comparison-20261025.json)
and the [earlier original-versus-512 control](source-split512-cpu-20261025.md).
The earlier result's 1.439x ratio combined physical splitting and parallel reads;
it did not establish that 512 MiB was the best file size.

## Matched physical results

Each table entry contains 96 exact-byte pair reads, sixteen per round over six
rounds. Every mode occupied every sequence position once. Lower time is better.
P95 uses linear interpolation between ordered observations.

| Physical file size | Serial mean | Parallel mean | Parallel P95 | Parallel maximum | Parallel mean versus 512 MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 512 MiB | 8.960 ms | 6.807 ms | 7.611 ms | 7.983 ms | Control |
| 256 MiB | 9.017 ms | 6.869 ms | 7.625 ms | 8.247 ms | 0.91% longer |
| 128 MiB | 8.967 ms | 6.896 ms | 7.599 ms | 10.713 ms | 1.30% longer |

The 256 MiB parallel round mean beat the corresponding 512 MiB mean in one of
six rounds; 128 MiB did so in two. All three serial means were also close.
The 128 MiB P95 was slightly lower while its maximum was higher. These small
differences do not qualify a general speed ranking or a sustained tail guarantee.

The engineering selection rule was recorded before timing: replace the
provisional 512 MiB candidate only for at least 5% lower parallel mean, at least
five of six faster round means, and no worse parallel P95. Neither smaller size
passed. This is a practical selection screen, not a statistical significance
test. The smaller file count of a prospective 512 MiB layout remains a management
consideration; this test did not measure whole-layout descriptor churn.

## Fixed data and execution conditions

- The physical PS5 used the application's actual C++ paired-read executor.
- Each pair read the same two original model ranges at 1016 / 1032 MiB, with a
  16 KiB stride across sixteen positions. Every read returned 3,293,184 bytes.
- Split-file relative offsets were 504 / 8 MiB, 248 / 8 MiB and 120 / 8 MiB.
  There was no cross-file boundary inside an individual timed read.
- One 8 MiB Direct window, at most two outstanding reads and seven pre-opened
  source descriptors were used. The existing eight-descriptor bound remained.
  File size does not imply allocating that much memory.
- All **576 pairs** passed SHA256 of every returned byte against the same
  original bytes. Hashing ran outside the timed read interval.
- Existing two 512 MiB files were fully streamed back and verified afresh.
  Only two 256 MiB and two 128 MiB files were added: **768 MiB total**. All six
  files passed complete raw transfer SHA256 before timing. Originals were retained.
- Mode order was cyclically rotated over six rounds. No cache purge, filesystem
  hint, model change, extra payload buffer or automatic read retry was used.

The helper retained the original kernel/Flexible admission, exact boot/service
identity checks, positive read completion and worker join, and 45-second
completed-boundary diagnostic limit. An unknown read retains its backing.
Fresh idle CPU observations before and after the run passed. The worker joined,
all source descriptors closed and the Direct window was positively released.
The finite host parent returned zero and every frozen input remained unchanged.

No title was launched, model loaded, GPU operation performed or original model /
application file written. The console remains idle with its original executable.
The GPU reservation remains held. No driver relink was needed for this CPU-only
test; selected driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
explicit `cumulative-idle` profile and disabled persistent shader / pipeline
cache policy remain unchanged. General execution/release and CI remain disabled.

## Implementation and limits

The diagnostic now accepts compile-time bounds of three to eight source
descriptors and one to six rounds, with optional cyclic mode ordering. Its
defaults retain the earlier three-descriptor, three-round order. Actual PS5
compilation passed with the default configuration and with this six-mode case;
greater than eight descriptors or six rounds failed compile-time controls.
All native runtime imports passed provider validation. The bounded publication
transport passed 36 host fault controls across the three size namespaces.

These observations cover one selected pair of original regions, repeated
overlapping ranges, pre-opened descriptors and one console/filesystem state.
They do not cover whole-route locality, descriptor replacement cost, reads
crossing a split boundary, cold-storage behavior or native inference. Do not
translate the approximately 1% differences into tokens/s. A broader production
layout decision still needs representative route and boundary costs, followed
by separate native inference qualification.
