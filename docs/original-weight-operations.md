# Bounded original-weight operation admission

`operator-validation` implements a distinct no-display diagnostic before full
model load. It uses an unchanged 81,920-byte BF16 slice from the pinned original
checkpoint: expert 0, gate rows 0 through 15, 2,560 columns. Its complete
3,355,443,368-byte source shard was independently hashed before extracting the
slice. The native policy pins the model revision, source-shard SHA256, slice
SHA256, selected driver/archive/profile and preceding successful combined SELF.
This diagnostic does not prune the complete model or claim model generation.

The application hashes and checks the finite BF16 input before GPU initialization.
One fixed graph performs BF16 2560x16/F32-vector multiplication, F32 RMS
normalization of the 2,560-element input and F32 SiLU on that normalized input.
All three outputs require device support before graph allocation. CPU scalar
double references are computed on the PS5. Every output must pass the fixed
`1e-5 + 1e-5 * abs(reference)` gate, finite checks and normalized RMSE at most 1%.
The historical shared driver's failed LLM reference result is not replaced by
this component test.

Readbacks complete before numerical checks. Successful resources enter deferred
retirement, followed by positive device idle and matching worker epochs through
the existing native frontend. Failed or unknown results retain backing and are
never retried. Complete RMS/SiLU readbacks and the 16 matvec outputs are saved as
bounded metadata for independent host verification. The passive service rejects
generation because no model is loaded; tokens/s remains unavailable.

Host tests use synthetic constant BF16 data and API stubs. They exercise all
graph shapes/readbacks, unsupported operations, backend/allocation/compute/readback
failures, wrong or nonfinite inputs, numerical failure and release ordering.
The actual implementation compiles for PS5. Startup isolation and the fixed
fixture path pass; the native policy rejects 159 malformed/out-of-scope cases
including full-inference attempts. Host checks are not physical operation
admission.

The distinct candidate subsequently passed on the physical PS5, including all
5,136 readbacks, fixed numeric limits, positive completion/retirement, ordinary
close and complete original restoration/readmission. See
[the physical result](native-original-operations-20261022.md) and its JSON.
This does not qualify full-model inference.

Before execution, require the exact native link, actual-module imports, SELF
roundtrips, six callback targets, all three BF16 and the actual F32 RMS/SiLU
SPIR-V modules. Preserve the original title, take fresh unchanged CPU guards and
bind the private policy/source slice into a single ordinary launch. Finish by
ordinary close, exact original restoration, numerical readmission, normal
shutdown, fresh CPU guards and a final full readback. Committed execution and
deployment flags remain disabled.

The first host link for this diagnostic reached its 600-second deadline while
the data disk was also verifying the original checkpoint. No console operation
occurred for that failed build. Its local receipt and timeout log are preserved.
The host linker now has a separate bounded worker count and explicit deadline:
`--link-threads 1 --link-timeout-seconds 1800` for this rebuild. These options
do not change console waits, numerical limits, native sources or execution gates.
