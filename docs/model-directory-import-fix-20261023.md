# Model-directory controller import correction

The independent content audit and all 76 final GGUF hashes completed. The v2
model receipt covers 359,246,956,672 container bytes and has SHA256
`d2a0705e0e8d8d5999cf2e6bd9519ccb0654837abcf1ab47d0295030a8bb5495`.
These host results do not qualify physical full-model inference.

The first data continuation passed the actual native host receipt gate, then
failed while checking its newly linked CPU directory controller. Its real owner
marker caused a `memcmp` import absent from the qualified reference object;
the reference source's short comparison had been inlined. The synthetic short
marker check had therefore missed a marker-length-dependent compiler behavior.
No CPU observer, directory controller, data transfer or title was executed.
Both dependent waiting controllers positively ended before source changes.

The controller now compares exact marker bytes using local volatile byte reads,
preventing synthesized comparison imports for different marker lengths. The
expected marker has static read-only storage, avoiding a synthesized stack-copy
import with the maximum marker. Exact lengths, EOF, owner, mode, regular-file,
symlink, canary and close checks are unchanged. No import allowance was expanded.

The host/native check now uses a 4,096-byte synthetic marker. All 37 in-memory
checks passed, including a mismatch at the final byte and high-bit bytes, and the
actual PS5 ABI object remains a subset of the qualified import set. Eleven Python
build/staging admission and fault-injection tests passed. Synthetic artifacts
remain host-only. The unchanged final application candidate is not rebuilt.

A new finite continuation can invoke the existing data operator with a fresh
data batch, then the existing single physical case and all ordinary restoration
steps. Completed content checks and container hashes are reused. Prior failure
records and artifacts are retained; no uncertain physical operation is retried.
The actual plan-bound controller link must still pass before its first CPU
execution. Fresh session, storage, owner and independent native SHA gates remain
mandatory. Committed deployment, execution, release and CI controls stay disabled.
