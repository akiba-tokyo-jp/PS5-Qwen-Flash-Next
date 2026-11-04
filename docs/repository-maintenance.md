# Repository and branch maintenance

Publication preparation date: **2026-11-05**.

## Maintained branches

| Branch | Purpose |
| --- | --- |
| `main` | Maintained source, public documentation and recorded validation baseline |
| `perf/strata-validation-20261105` | Resume the incomplete Strata follow-up after the original close/restoration is resolved |

The selected R1/P1 evidence and incomplete Strata results are recorded on main.
Merging source history does not adopt an experimental provider, qualify a
binary release, change execution flags or resolve console state.

## Cleanup and retained history

The pre-cleanup inventory contains 85 remote and 87 local branches. All refs
were backed up to a verified local Git bundle before any ref deletion. Merged
work remains reachable through main. Ten historical heads outside the integrated
validation history are retained as `archive/20261105/<previous-branch-name>` tags,
including two local-only heads. The [inventory](archive/branch-inventory-20261105.json)
records exact commits and preservation actions.

Completed/duplicate work branches are removed after the latest source and
publication documentation are integrated. The incomplete Strata branch is
advanced to the same documentation baseline, so it does not retain an obsolete
README. These are ordinary fast-forward/merge operations, not rewritten history.
No unique head is discarded and no release tag is repurposed.

Cleanup is complete: 83 remote work branches were removed, leaving two.
86 local work refs were removed, including the temporary publication branch.
Both maintained branches share the updated documentation baseline. The archive
tags are present on the remote, and the local worktree is clean. Repository
visibility was not changed by this cleanup.

Archive tags are historical controls, not recommended configurations. To inspect
one, list them with `git tag --list "archive/20261105/*"`, then use
`git show <tag>` or create a new branch from that tag. Existing immutable report
links and commits remain valid.

## Future changes

Keep main's README/status accurate. Use a focused branch for a new experiment;
keep its eligibility, numerical, performance and adoption decisions distinct.
After integration, remove obsolete work branches while retaining any unique
historical head. Do not delete a branch used by an active PR or worktree.

Do not change repository visibility, enable CI or publish binaries as an
incidental cleanup step. Those are separate actions. Public-facing documentation
should use placeholders for local paths and point to dated evidence without
presenting private artifact locations as runnable instructions.

## Publication preparation verification

The two documented host-check groups pass seven tests. The five documented
CLI entry points parse their help without executing downloads/builds. Maintained
Markdown passes local-link checks (153 links at preparation time); dependency
pins match the lock file and JSON parses. No native console operation or CI run
is part of this cleanup.

The current tracked tree contains no model/native binary or private capture
files. A scoped pattern scan of 4,913 reachable Git blobs/commits/tags
(77,646,459 bytes) finds no private-key markers, GitHub token patterns or AWS
access-key patterns. This records the checks actually performed, not a general
secret-free guarantee. Historical receipts still contain local artifact paths;
maintained guides use placeholders and explain their scope.
