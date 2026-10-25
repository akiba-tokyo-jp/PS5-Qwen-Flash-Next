# Adopted original-precision inference profile

The selected configuration is
[`config/qualified-performance.json`](../config/qualified-performance.json).
It selects the qualified decode-only BF16 indexed-vector route and owned
padded-bank reads, with ordinary staged/coalesced fallback. Non-temporal copies
remain disabled after their measured regression. Quantization, KV precision,
53 active slots, the 512 MiB cache, 8 MiB source window and driver stay unchanged.

This profile is bound to the exact qualified SELF and driver archive. Both
complete same-SELF arms passed physical inference, actual native frame review,
source/GPU/model retirement, ordinary close, exact original restoration, fresh
original numerical admission, original shutdown and final idle/full readback.
See [the sanitized evidence](native-owned-bank-success-20261025.json) and
[results](gpu-optimization-results-20261025.md). These are short deterministic
requests; broader quality, context and sustained unattended service are separate.

The offline helper applies only the four known performance switches to an
already prepared private case, preserving every other binding and gate:

```powershell
python tools/qualified_performance.py --policy <fresh-private-policy> `
  --profile config/qualified-performance.json --package <exact-package-receipt> `
  --out <new-private-policy-path>
```

Omitting `--out` verifies that a policy already selects the profile. The measured
selected policy passed that verification value-for-value in parsed JSON.
The helper refuses a different SELF/driver, changed precision/cache policy or
incompatible execution/prefill/source scope. It never launches, deploys, creates
an execution admission, modifies an existing input or contacts a console.
Keep each fresh case's ownership, complete original preservation, source/data,
memory and ordinary restoration checks. Never replay a consumed case or run ID.

The committed general execution/deployment controls remain disabled. Selecting
an optimization profile does not automatically start an unattended service.
At completion the exact original title was restored and normally closed; no
native owner, gateway or loaded model remains.
