# Direct PFS lifetime prototype

Status: **host cross-build only; not qualified for native use or production**.
No direct-PFS supervisor, native APR resolve, hardware Kraken request or model
benchmark from this prototype has executed on PS5.

The preceding classic-PFS-through-nullfs route could read its control bytes but
APR rejected its file ID. The proposed changed test mounts an owned filesystem
directly at the authenticated native sandbox path. This separates the forwarding
layer from the actual PFS handler. It does not assume either route will be fast.

## Ownership and handshake

`apr_direct_control.h` defines one locked 64-byte file with a version magic,
32-character case nonce, native PID and stage. It lives outside the PFS volume.
Every transition uses `flock`, whole-record I/O and durable writes.

1. Native creates an exclusive empty directory and control file, then publishes
   READY. A supervisor claim and an unclaimed timeout take the same lock.
2. The supervisor verifies boot, services, candidate hashes, the one native PID,
   sandbox path, and that its credential object is not shared with the parent
   or protected services. It claims BUSY before any image operation.
3. The supervisor owns an exclusive 64 MiB-capacity image. It uses original OS
   filesystem APIs, preserves the generated key, and mounts directly at the
   sandbox path. The filename must fit the actual mount-name field.
4. The control bytes are written/fsynced under a temporary name and atomically
   published. MOUNTED releases native access. Native records the actual
   filesystem type, verifies all bytes, and tries APR identity/size only.
5. Native closes its ordinary input descriptor and publishes NATIVE_CLOSED.
   No APR read or GPU request is submitted by this prerequisite probe.
6. The supervisor ordinarily unmounts and verifies the original parent fsid
   before deleting the image/directory. It restores its auth and parent owner,
   then publishes DETACHED. Native return follows acknowledgement.

No forced unmount, process kill, kernel reset, registration change or source
weight change is part of this prototype. Cleanup never unlinks a possibly
mounted backing image. Poll loops have both a clock deadline and a count bound.
Unexpected kernel blocking still cannot be converted into a guaranteed ordinary
completion by these user-space controls. Failed detach retains ownership
evidence and is not a successful test.

## Current execution boundary

The first candidate's OS launch returned `0x80020008` before native entry.
The direct supervisor was never called. The original program and five settings
were restored and whole-file checked, including the existing title alias.

Read-only new-boot discovery had reported the old compatibility runtime absent.
The launcher previously did not check this prerequisite. It now contains the
same read-only readiness query as the qualified compatibility loader and refuses
before calling LaunchApp unless the result is positive. This correction is
cross-built, not natively verified.

The exact pre-existing compatibility binary was subsequently requested once.
Completion collection then lost communication; no ready END was obtained.
Independent management/FTP checks also failed. Do not repeat that initialization
on this boot. Runtime readiness, direct PFS acceptance and hardware Kraken remain
unperformed/unconfirmed as appropriate; no speedup is assigned to this code.

## Required qualification before adoption

- Recover and inspect the pending initializer journal and current boot/owners.
- Verify an actual positive runtime result before native admission.
- Exercise ordinary success and controlled failure paths with positive native
  and supervisor completion, restored owners, and no retained mount/image.
- Record actual PFS type and APR identity/size. A rejected identity is a measured
  rejection of that exact format/context, not proof of absent hardware.
- Only with a genuine ID, qualify bounded read/completion ABI and compare
  1/2/4-request delivery. Hardware Kraken separately needs a genuine supported
  compressed source; the CPU entropy envelope is not one.
- Adopt only repeatable matched model improvements. This branch does not change
  the default inference engine, driver, precision, caches or deployed binary.

Original filesystem layouts reference ps5-sd-tool ef5df270 and garlic-worker
e0cbe2d3. Classic creation uses five arguments; PPR creation uses the observed
four-argument offset/capacity ABI. A selectable PPR code branch is not evidence
that a PPR control or hardware decoder has run.
