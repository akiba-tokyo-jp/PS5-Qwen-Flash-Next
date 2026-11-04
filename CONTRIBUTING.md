# Contributing

Start with the [documentation guide](docs/README.md),
[current status](docs/project-status.md) and [architecture](docs/architecture.md).

## Scope changes

Describe concrete behavior and separate implementation, measurement and adoption.
Experimental providers do not become selected by being committed. Preserve
numerical, identity, memory, ownership and completion contracts.

Write documentation, comments, program messages and commit/PR descriptions in
English. Preserve identifiers and legal notices. Do not include model weights,
SDKs, native binaries, credentials, private captures or machine-specific manifests.

## Host checks

Python 3.11+ runs these initial checks without a console:

```powershell
python -B -m unittest discover -s tests -p test_development_policy.py -v
python -B -m unittest discover -s tests -p test_driver_inputs.py -v
```

Run checks relevant to a change. Other tests/builders may require the selected
Windows compiler, pinned sources or private retained artifacts; not every test
is portable Python-only. Report what actually ran and missing prerequisites.
Compilation, API stubs and host simulations are not PS5 performance evidence.
GitHub Actions workflows are not enabled.

## Native work

A source contribution does not authorize console use. Native operations require
the operator's scope and current observations. Preserve one IO owner, ordinary
close and positive worker/source/device retirement. Do not replay consumed
initialization, launch or cache-window bindings. The latest close/restoration
is unresolved; do not automatically resume it.

Never bypass a completion gate or lower a reserve simply to make a test run.
Distinguish hardware limits from application policies; price a changed policy
under its measured scope. Pin the driver source/profile and keep persistent
caches off until separately qualified.

## Performance claims

Report cold/retained/exact-prefix separately with
`(generated_tokens - 1) * 1000 / decode_ms`. Disclose precision, routing, input,
output count and control. Keep TTFT, prefill and whole-time results separate.
Exclude qualification observers from timing. Do not combine unmatched gains or
infer broad quality from a few tasks. See [performance](docs/performance.md).

Reuse completed evidence and advance distinct untested scopes efficiently.
Repeating an unchanged negative is not a refinement. Report incomplete work as
incomplete, including an unresolved ordinary close.

## Pull requests

Lead with the problem and final behavior. Include relevant validation, limits
and adoption status. Keep raw logs/data/native artifacts outside Git and identify
source/profile provenance. Public source preparation does not qualify a binary
release or change console state.
