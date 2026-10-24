#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a host-only native driver candidate without replacing its allocator.

Only the two exact selected-profile members are copied. This does not integrate
the application's frontend lifecycle or authorize packaging/deployment/execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from driver_inputs import sha, validate_driver

ROOT = Path(__file__).resolve().parents[1]
PROFILE_MEMBERS = {("radv_shader.c.o", 0), ("winsys_ps5_radv_ps5_winsys.c.o", 0)}
NATIVE_PLATFORM = ("radv_ps5_platform_native.o", 0)
GENERIC_PLATFORM = ("winsys_ps5_radv_ps5_platform.c.o", 0)
NATIVE_COMPATIBILITY = {("radv_device.c.o", 0), ("radv_device_memory.c.o", 0),
                        ("radv_physical_device.c.o", 0)}


def read_archive(path):
    """Index ordinary ELF archives, retaining duplicate-member identities."""
    result, occurrences, names = {}, {}, b""
    with Path(path).open("rb") as stream:
        length = stream.seek(0, 2)
        stream.seek(0)
        if stream.read(8) != b"!<arch>\n":
            raise ValueError("An ordinary archive is required")
        while stream.tell() < length:
            header = stream.read(60)
            if len(header) != 60 or header[58:] != b"`\n":
                raise ValueError("Invalid archive header")
            name = header[:16].decode("ascii").strip()
            try:
                size = int(header[48:58])
            except ValueError as error:
                raise ValueError("Invalid archive member size") from error
            offset = stream.tell()
            end = offset + size
            if size < 0 or end + size % 2 > length:
                raise ValueError("Truncated archive member")
            if name == "//":
                if size > 1 << 20:
                    raise ValueError("Archive name table is too large")
                names = stream.read(size)
            elif name not in {"/", "/SYM64/"}:
                if name.startswith("#1/"):
                    count = int(name[3:])
                    if count <= 0 or count > min(size, 4096):
                        raise ValueError("Invalid BSD archive name")
                    name = stream.read(count).rstrip(b"\0").decode("utf-8")
                    offset += count
                elif name.startswith("/"):
                    index = int(name[1:])
                    if index < 0 or index >= len(names):
                        raise ValueError("Invalid archive name offset")
                    tail = names[index:]
                    stop = tail.find(b"/\n")
                    if stop < 0:
                        raise ValueError("Unterminated archive name")
                    name = tail[:stop].decode("utf-8")
                else:
                    name = name.removesuffix("/")
                if not name or any(c in name for c in "/\\:\0\r\n"):
                    raise ValueError("Archive members must use plain basenames")
                stream.seek(offset)
                if stream.read(4) != b"\x7fELF" or end - offset < 4:
                    raise ValueError("Non-ELF archive member")
                stream.seek(offset)
                digest = hashlib.sha256()
                remaining = end - offset
                while remaining:
                    block = stream.read(min(remaining, 1 << 20))
                    if not block:
                        raise ValueError("Truncated ELF member")
                    digest.update(block)
                    remaining -= len(block)
                occurrence = occurrences.get(name, 0)
                occurrences[name] = occurrence + 1
                result[(name, occurrence)] = {"sha256": digest.hexdigest(), "offset": offset,
                                               "bytes": end - offset}
            stream.seek(end + size % 2)
    return result


def hashes(index):
    return {key: row["sha256"] for key, row in index.items()}


def check_plan(base, reference, selected):
    if not (len(base) == len(reference) == len(selected) == 704):
        raise ValueError("Expected exactly 704 ELF member occurrences")
    if selected.keys() != reference.keys() or {
            key for key in selected if selected[key] != reference[key]} != PROFILE_MEMBERS:
        raise ValueError("Selected profile must change exactly the two pinned driver members")
    if base.keys() - reference.keys() != {NATIVE_PLATFORM} or reference.keys() - base.keys() != {GENERIC_PLATFORM}:
        raise ValueError("Native platform member identity differs")
    if {key for key in base.keys() & reference.keys() if base[key] != reference[key]} != NATIVE_COMPATIBILITY:
        raise ValueError("Native compatibility member set differs")
    if any(base[key] != reference[key] for key in PROFILE_MEMBERS):
        raise ValueError("Native base profile members are not pristine")


def verify_composition(before, after, selected):
    if before.keys() != after.keys():
        raise ValueError("Composition changed member occurrence identities")
    changed = {key for key in before if before[key] != after[key]}
    if changed != PROFILE_MEMBERS or any(after[key] != selected[key] for key in PROFILE_MEMBERS):
        raise ValueError("Composition must preserve all 702 native members and copy exact selected members")


def _compose(native_base, reference, selected, native_lock, llvm_ar, out, timeout_seconds=600):
    if not 1 <= timeout_seconds <= 1800:
        raise ValueError("Invalid host archiver deadline")
    native_base, reference, out = Path(native_base).resolve(), Path(reference).resolve(), Path(out).resolve()
    paths = [native_base, reference, Path(selected["archive_path"])]
    before_digests = [sha(path) for path in paths]
    if before_digests[:2] != [native_lock["base_archive_sha256"], native_lock["reference_archive_sha256"]]:
        raise ValueError("Native base or original reference digest mismatch")
    if before_digests[2] != selected["archive_sha256"] or selected["profile"] != "cumulative-idle":
        raise ValueError("Selected driver profile digest mismatch")
    print("Native base, reference and selected profile digests matched", flush=True)
    base, ref, donor = [read_archive(path) for path in paths]
    check_plan(hashes(base), hashes(ref), hashes(donor))
    print("704-member plan admitted; 702 native member occurrences will be preserved", flush=True)
    out.mkdir(parents=True, exist_ok=False)
    archive = out / "libvulkan_radeon.native-candidate.a"
    shutil.copyfile(native_base, archive)
    objects = []
    with paths[2].open("rb") as stream:
        for key in sorted(PROFILE_MEMBERS):
            entry = donor[key]
            stream.seek(entry["offset"])
            content = stream.read(entry["bytes"])
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError("Selected donor changed during composition")
            path = out / key[0]
            path.write_bytes(content)
            objects.append(path)
    command = [str(llvm_ar), "r", str(archive), *map(str, objects)]
    status = out / "operation-status.private.json"
    status.write_text(json.dumps({"phase": "archiving", "timeout_seconds": timeout_seconds,
                                 "console_access": False, "accepted_manifest_published": False}) + "\n")
    try:
        process = subprocess.run(command, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        (out / "archive.private.log").write_bytes((error.stdout or b"") + (error.stderr or b""))
        status.write_text(json.dumps({"phase": "failed", "error_type": "TimeoutExpired",
                                     "console_access": False, "accepted_manifest_published": False}) + "\n")
        raise
    (out / "archive.private.log").write_bytes(process.stdout + process.stderr)
    if process.returncode:
        status.write_text(json.dumps({"phase": "failed", "returncode": process.returncode,
                                     "console_access": False, "accepted_manifest_published": False}) + "\n")
        raise RuntimeError("Native candidate archiving failed; see the private log")
    status.write_text(json.dumps({"phase": "verifying_composition", "console_access": False,
                                 "accepted_manifest_published": False}) + "\n")
    after = read_archive(archive)
    verify_composition(hashes(base), hashes(after), hashes(donor))
    if before_digests != [sha(path) for path in paths]:
        raise ValueError("A composition input changed during archiving")
    receipt = {"schema": "ps5-qwen-native-driver-candidate-v1", "selected_driver": selected,
               "base_archive_sha256": before_digests[0], "reference_archive_sha256": before_digests[1],
               "archive_path": str(archive), "archive_sha256": sha(archive),
               "changed_members": [list(key) for key in sorted(PROFILE_MEMBERS)],
               "native_members_preserved": 702, "native_frontend_integrated": False,
               "native_compatibility_members": [list(key) for key in sorted(NATIVE_COMPATIBILITY | {NATIVE_PLATFORM})],
               "members": [{"name": key[0], "occurrence": key[1], "sha256": row["sha256"]}
                           for key, row in after.items()],
               "archiver_sha256": sha(llvm_ar), "command": command, "inputs_stable": True,
               "console_access": False, "GPU_executed": False, "CI": False,
               "deployment_allowed": False, "application_linked": False}
    with (out / "manifest.private.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    status.write_text(json.dumps({"phase": "completed", "console_access": False,
                                 "accepted_manifest_published": True}) + "\n")
    return receipt


def compose(native_base, reference, selected, native_lock, llvm_ar, out, timeout_seconds=600):
    out = Path(out).resolve()
    existed = out.exists()
    try:
        return _compose(native_base, reference, selected, native_lock, llvm_ar, out, timeout_seconds)
    except BaseException as error:
        # Never mutate an existing output belonging to an earlier attempt.
        if not existed and out.is_dir():
            (out / "manifest.private.json").unlink(missing_ok=True)
            (out / "operation-status.private.json").write_text(json.dumps({
                "phase": "failed", "error_type": type(error).__name__,
                "console_access": False, "accepted_manifest_published": False}) + "\n")
        raise


def validate_native_platform(manifest_path, selected, native_lock):
    manifest_path=Path(manifest_path).resolve()
    value=json.loads(manifest_path.read_text())
    if (value.get('schema')!='ps5-qwen-native-platform-build-v1' or value.get('selected_driver')!=selected or
        value.get('composition_archive_sha256')!=native_lock['selected_composition_sha256'] or
        value.get('modified_members')!=[list(NATIVE_PLATFORM)] or value.get('unmodified_members_preserved')!=703 or
        value.get('other_application_log_fallback') is not False or value.get('deployment_allowed') is not False or
        value.get('console_access') is not False or value.get('GPU_executed') is not False or
        value.get('persistent_caches_disabled_required') is not True or value.get('CI') is not False):
        raise ValueError('Native platform manifest does not match the host-only integration contract')
    current=sorted(path.resolve()for path in (ROOT/'native/driver').iterdir()if path.is_file())
    recorded=sorted(Path(row['path']).resolve()for row in value['native_source'])
    if recorded!=current:raise ValueError('Native platform source set changed')
    for row in value['native_source']+value['native_headers']+value['inputs_before_after']:
        if sha(row['path'])!=row['sha256']:raise ValueError('Native platform source, header or build input changed')
    archive=Path(value['archive_path'])
    if sha(archive)!=value['archive_sha256']:raise ValueError('Native platform archive digest mismatch')
    inputs=value['inputs_before_after']
    if not inputs or inputs[0]['sha256']!=native_lock['selected_composition_sha256']:
        raise ValueError('Native platform composition donor is not pinned')
    before=hashes(read_archive(inputs[0]['path']));after=hashes(read_archive(archive))
    if len(before)!=704 or before.keys()!=after.keys() or {key for key in before if before[key]!=after[key]}!={NATIVE_PLATFORM}:
        raise ValueError('Native platform changed an unrelated member occurrence')
    native_object=manifest_path.parent/NATIVE_PLATFORM[0]
    if after[NATIVE_PLATFORM]!=sha(native_object):raise ValueError('Native platform object does not match the archive')
    return {'manifest_path':str(manifest_path),'manifest_sha256':sha(manifest_path),
            'archive_path':str(archive),'archive_sha256':value['archive_sha256'],
            'selected_shared_driver':selected,'source_inputs':value['native_source'],
            'unmodified_native_members_preserved':703,'console_qualified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-base", "reference", "driver-root", "driver-manifest", "llvm-ar", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--archiver-timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    selected = validate_driver(args.driver_root, args.driver_manifest, lock["ps5_vulkan_inference"])
    receipt = compose(args.native_base, args.reference, selected, lock["native_platform_base"],
                      args.llvm_ar, args.out, args.archiver_timeout_seconds)
    print(json.dumps({key: receipt[key] for key in ("archive_sha256", "native_members_preserved",
                       "native_frontend_integrated", "application_linked", "console_access")}))


if __name__ == "__main__":
    main()
