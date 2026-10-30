# Obsolete console versions retired

The owner authorized deleting old versions after implementation. Cleanup10200
supersedes the previous requirement to keep every old executable and setting
backup on the PS5. It changes retention, not the selected inference program.

The scope is108 obsolete `eboot.before-*`, `eboot.after-*` and
`eboot.pending-*` programs plus1,346 backups of the five application settings.
Their removed raw file lengths total3,101,941,517 bytes (3.102 GB;2.889 GiB).
Only explicitly inventoried regular files are removed. Each deletion has a
durable intent, a positive server acknowledgement and an absence check. Final
directory inventories must equal their original inventories minus these files.
No recursive directory deletion is used.

The selected SELF remains18,299,623 bytes with SHA256
`5487e687dbc13a5f6a7655faf52d91752f3d029ba13938762b133b99e6a3a7a5`.
Its complete raw bytes and all five current settings are checked before and
after removal. The existing CPU-only directory controller restores the original
runtime/web ownership after setting retirement. All model assets, driver files,
licenses, existing host packages and historical evidence are outside the scope.
The normal title, gateway and models stay inactive; no GPU calls, application
launches, reboot or CI are needed.

All12 formerly qualified production programs still have exact, unchanged host
archives. Obsolete experimental console copies can be removed without creating
another duplicate archive of each one. Existing complete captures and interrupted
read evidence are retained privately. Historical placement10160's verification
of13 programs and five settings remains true at that earlier point; it is not
a claim that those rollback files still exist on the console. The separately
qualified shared-prefix executable9980 is also retired; its source and test
evidence remain available.

The [current retention record](obsolete-version-cleanup-20261030.json) records
actual removed raw file lengths. Their sum is a logical file-size reduction,
not a measured increase in filesystem free space and not reclaimed inference
or kernel memory. Inference throughput is unchanged by this cleanup.

`performance_production.py` and `qualified_control` accept the exact current
SELF with this completed retirement record and matching private context. They
reject missing cleanup, altered current SELF, incomplete protected-file checks,
missing host recovery or unrestored ownership. Numerical qualification, driver,
memory, owner and completion requirements are unchanged. Historical controls
continue to use their original preservation requirements.

Manual checks pass23 tests across current performance admission, passive
observation, historical routing/width16 and optimized I/O controls. The older
I/O suite now binds its own historical schema instead of the moving current
installation. `git diff --check` passes. No CI is run.

For future replacements, preserve the immediate control during qualification.
Once the replacement is positively qualified and its installed bytes/settings
verified, retire its obsolete console copies under the owner's authorization.
Use existing host recovery artifacts instead of repeatedly copying them back
to the console. Build/model data and private evidence remain outside Git.
