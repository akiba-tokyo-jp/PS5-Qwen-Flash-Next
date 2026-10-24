# Plan-bound model file permissions

The first full-model native attempt rejected the transferred model files before
backend initialization: the FTP server created regular files with mode 0777,
while native identity admission rejects group/world write permissions. The
candidate's raw SELF and receipt checks had passed. No model load or GPU
initialization occurred. The exact owner was closed through the ordinary OS
path; its failed result and source/stage evidence remain retained.

`tools/build_model_file_seal.py` now builds a separate CPU controller from the
qualified credential-preserving CRT and actual runtime modules. Its generated
header contains exactly the original plan's 76 filenames/sizes and the complete
receipt. The runtime accepts only its fixed operation argument and fresh log
nonce. It reads no model payload and makes no ownership, deletion, mapping,
title or GPU calls.

Before any permission change, every file must be a regular root-owned file of
the exact size, with mode 0777 or already 0644. The parent must remain a root-owned
0755 directory. Each file is reopened without following symlinks; descriptor
identity is compared before changing only its mode to 0644. Post-change and final
checks require unchanged file/device/inode/size/owner/mtime, no group/world write,
and unchanged directory permissions. The controller retains a bounded per-file
completion log. A failure never triggers an automatic replay.

Seven host checks passed: successful complete sealing, rejection of a foreign
owner, unexpected mode, wrong size, changed identity and failed `fchmod`, and
acceptance of already-sealed files without another change. All 14 dynamic imports
resolved through the qualified real runtime providers, including `fchmod`.

The physical operation passed all 77 file records. Independent FTP metadata
confirmed mode 0644, the owner marker and full receipt readback matched, and fresh
CPU guards before/after confirmed the same boot/services and no native owner.
The original model bytes and conversion receipt were retained. These metadata
results do not replace the native full-payload SHA pass before model loading.
