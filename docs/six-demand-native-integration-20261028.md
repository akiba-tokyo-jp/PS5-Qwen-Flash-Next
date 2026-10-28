# Actual-model six-demand delivery

This default-off implementation connects the positive six-demand source fixture
to the original model's expert delivery loop. It preserves BF16 weights, F32
arithmetic and KV state, all original expert selections, and the qualified
53-slot padded cache.

`tools/refill_model_io.py` overlays the actual `llama-moe-cache.cpp` delivery
frontier. It selects two isolated cache misses across the original three expert
roles, retains the existing coalesced groups, and skips only positively delivered
entries in the ordinary per-role loop. `native/app/owned_mapped_backend.cpp`
obtains the three existing coherent shared bank leases.
`MappedSourceReader::try_owned_bank_batch` in `native/app/mapped_source.h`
validates six disjoint source/target envelopes, identities, residues, slots and
ownership before I/O. Split, coalesced and EOF cases return to the existing path
before issuing a read. `PairedSourceIO::read_batch` keeps one persistent worker
and the existing producer, with at most two reads in flight; it refills either
lane as each read completes. Exact completion and accounting precede reuse.

The manual host controls passed:

- The same worker completed six deliveries, then the original pair and consumer
  pipeline. Invalid and known short reads were refused.
- All 30 original residues completed 180 exact reads, including last-slot guards,
  three pre-I/O fallback cases, eight negative controls and source conservation.

Native parent build 3881 compiled the actual modified MoE object and linked the
ten returned unchanged app dependency objects from build 3864. Provenance 3919
binds the actual seven model-I/O objects. The bounded five-request entry in
build 3922 uses warmup, ordinary, six-demand, six-demand, ordinary, fresh contexts
and caches, exact output bytes/tokens, all 23 F32 logit rows, complete expert
routes, batch/read/byte accounting, and positive final source/device retirement.

The primary checkout's provenance bridge 3991 and SELF 4151 passed the original
package/import/dispatch/segment checks. The later build 4250 restores the original
eight MiB load reads; SELF 4251 is SHA256
`c4c82a111d3f319aac37dc6519bfc96ad94d8bfd31f9cf9f5ce4f3dadbbb7464`.
The driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, linked archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent caches and CI remain disabled.

The earlier native source fixture's median ratio was 1.0319375546 across
60 batches/360 reads, with nine of ten reverse pairs faster. Actual-model
qualification and production selection require the five-request physical
comparison. Source-fixture timing does not establish a model tokens/s gain.

The subsequent retained-context entry is built and case 4940 was executed.
The original model loaded, then the before-context predicate observed 1,182
free kernel pages against the selected 1,197-page requirement. No request or
six-demand model batch ran. Ordinary OS close and exact fastest/settings
restoration passed. This is current execution unavailability, rather than
missing integration, physical impossibility or a measured model regression.
See `retained-context-results-20261028.md` for the complete terminal decisions.
