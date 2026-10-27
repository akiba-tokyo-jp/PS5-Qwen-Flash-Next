#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Convert the verified native PIE to a local development SELF, without deployment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct

from driver_inputs import sha, validate_driver
from native_driver import validate_native_platform
from audit_native_imports import audit
from build_model_io import validate_overrides

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--driver-root", type=Path, required=True)
    p.add_argument("--driver-manifest", type=Path, required=True)
    p.add_argument("--native-build", type=Path,
                   help="Native build directory; defaults to cache/build/application-native")
    p.add_argument("--out", type=Path, required=True, help="Fresh local package directory")
    a = p.parse_args()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text(encoding="utf-8"))
    selected = validate_driver(a.driver_root, a.driver_manifest, lock["ps5_vulkan_inference"])
    native_build = a.native_build.resolve() if a.native_build else a.cache / "build/application-native"
    link_receipt = native_build / "receipt.private.json"
    linked = json.loads(link_receipt.read_text(encoding="utf-8"))
    if linked.get("link_returncode") != 0 or not linked.get("input_hashes_stable") or linked["driver"] != selected:
        raise ValueError("A successful matching native link receipt is required")
    if linked.get("bounded_model_source_link_map_passed") is not True:
        raise ValueError("Every bounded source-reader override must be proven in the final link map")
    io_manifest = linked["bounded_model_source_manifest"]
    if record(Path(io_manifest["path"])) != io_manifest or validate_overrides(
        Path(io_manifest["path"]), Path(linked["engine_receipt"]["path"])) != linked["bounded_model_source_overrides"]:
        raise ValueError("The source-reader integration changed after the native link")
    shader_resources=linked.get('lossless_shader_storage')
    if shader_resources:
        from external_shader_storage import validate_shader_resources
        resource_manifest=linked.get('shader_resource_manifest')
        if not resource_manifest or record(Path(resource_manifest['path']))!=resource_manifest:
            raise ValueError('The exact linked shader resource manifest is required before packaging')
        if validate_shader_resources(resource_manifest['path'],io_manifest['path'],linked['engine_receipt']['path'])!=shader_resources:
            raise ValueError('The shader resource integration changed after the native link')
        if linked.get('lossless_shader_storage_link_map_passed')is not True:
            raise ValueError('Actual shader resource link-map admission is required')
    if linked.get('native_platform'):
        platform=validate_native_platform(linked['native_platform']['manifest_path'],selected,lock['native_platform_base'])
        if platform!=linked['native_platform']:raise ValueError('Linked native platform provenance changed')
    image = Path(linked["artifact"]["path"])
    driver_tables=linked.get('lossless_driver_tables')
    if driver_tables:
        from driver_table_storage import validate as validate_driver_tables
        manifest=linked.get('driver_table_manifest')
        if not manifest or record(Path(manifest['path']))!=manifest or linked.get('lossless_driver_tables_link_map_passed')is not True:
            raise ValueError('The exact linked driver-table manifest and symbols are required')
        if validate_driver_tables(manifest['path'],driver_tables['source_archive']['path'])!=driver_tables:
            raise ValueError('Cold driver table inputs changed after link')
        from driver_table_storage import audit_linked_storage
        if audit_linked_storage(image,driver_tables)!=linked.get('lossless_driver_table_geometry'):
            raise ValueError('Actual native driver table geometry was not qualified')
    if sha(image) != linked["artifact"]["sha256"]:
        raise ValueError("Native PIE differs from the link receipt")
    dispatch = linked.get("native_dispatch_audit", {})
    if (dispatch.get("schema") != "ps5-qwen-native-dispatch-audit-v1" or
        dispatch.get("passed") is not True or dispatch.get("image_sha256") != sha(image) or
        len(dispatch.get("required_physical_callbacks", [])) != 6):
        raise ValueError("The actual native Vulkan callback-table audit is required before packaging")
    imported = audit(a.workspace, a.cache, native_build)
    if imported["missing"]:
        raise ValueError("Real module import audit failed: " + ", ".join(imported["missing"]))
    if linked.get("mmap_public_provider_required") is not True or imported["resolved"].get("mmap") != "libkernel.sprx":
        raise ValueError("The native file mapper must import the actual public libkernel mmap provider")
    if a.out.exists():
        raise ValueError("Package output must be a fresh directory")
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    llvm = a.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    native = a.driver_root / "tooling/native"
    sources = [native / name for name in ("native_app_builder.cpp", "elf_object.cpp", "sce_module_writer.cpp", "self_container.cpp")]
    headers = list(sorted(native.glob("*.hpp")))
    tool_identity = hashlib.sha256(b"".join(path.read_bytes() for path in sources + headers)).hexdigest()
    tool_dir = a.cache / "build/native-format-tool" / tool_identity[:20]
    tool_dir.mkdir(parents=True, exist_ok=True)
    tool = tool_dir / "ps5-native-tool.exe"
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    compile_command = [str(host / "clang++.exe"), "-std=c++20", "-O2", *map(str, sources), "-lz", "-o", str(tool)]
    if not tool.exists():
        result = subprocess.run(compile_command, env=env, capture_output=True)
        (tool_dir / "compile.private.log").write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    a.out.mkdir(parents=True)
    external_shader_file=None
    if shader_resources and shader_resources.get('storage_kind')=='external_file':
        pool=shader_resources['pool'];directory=a.out/'resources';directory.mkdir()
        name='shader-storage-'+pool['sha256']+'.bin';snapshot=directory/name
        shutil.copyfile(pool['path'],snapshot)
        saved=record(snapshot)
        if saved['bytes']!=pool['bytes']or saved['sha256']!=pool['sha256']:
            raise ValueError('External shader resource snapshot changed its complete original bytes')
        external_shader_file=dict(local=saved,filename=name,native_path='/app0/qwen-runtime/'+name,
            input_window_bytes=shader_resources['external_file_input_window_bytes'],
            original_SPIRV_resource=True,persistent_compiled_cache=False)
    native_platform_snapshot=None
    if linked.get('native_platform'):
        origin=Path(linked['native_platform']['manifest_path'])
        native_platform_snapshot=a.out/'native-platform.receipt.private.json'
        shutil.copyfile(origin,native_platform_snapshot)
        if sha(native_platform_snapshot)!=linked['native_platform']['manifest_sha256']:
            raise ValueError('Native platform manifest changed while snapshotting')
    engine_origin = Path(linked["engine_receipt"]["path"])
    if sha(engine_origin) != linked["engine_receipt"]["sha256"]:
        raise ValueError("Engine build receipt changed after the native link")
    engine_snapshot = a.out / "engine-build.receipt.private.json"
    shutil.copyfile(engine_origin, engine_snapshot)
    if sha(engine_snapshot) != linked["engine_receipt"]["sha256"]:
        raise ValueError("Engine build receipt changed while snapshotting")
    # Keep an immutable ledger in every package. A later build may replace the
    # working link receipt; retaining only its path/digest would lose provenance.
    link_snapshot = a.out / "native-link.receipt.private.json"
    shutil.copyfile(link_receipt, link_snapshot)
    if sha(link_snapshot) != sha(link_receipt):
        raise ValueError("Native link receipt changed while snapshotting")
    if json.loads(link_snapshot.read_text(encoding="utf-8")) != linked:
        raise ValueError("Native link receipt differs from the qualified build")
    original = a.out / "source.pie.elf"
    shutil.copyfile(image, original)
    if sha(original) != linked["artifact"]["sha256"]:
        raise ValueError("Native PIE changed while snapshotting the package input")
    pie = a.out / "application.pie.elf"
    converted, executable, extracted = (a.out / name for name in ("eboot.elf", "eboot.bin", "roundtrip.elf"))
    # Use exactly the import stubs which participated in this native link.
    # Weak convenience stubs include names absent from the actual title ABI.
    # They may help a host link, but cannot establish a native import provider.
    imports = [Path(row["path"]) for row in linked["inputs_before"]
               if row["path"].endswith(".so") and not Path(row["path"]).name.endswith("_stub_weak.so")]
    for path in imports:
        expected = next(row["sha256"] for row in linked["inputs_before"] if Path(row["path"]) == path)
        if sha(path) != expected: raise ValueError("Native runtime import stub changed")
    commands = [
        ("strip_debug", [str(llvm / "llvm-objcopy.exe"), "--strip-debug", str(original), str(pie)]),
        ("convert", [str(tool), "link", "--in", str(pie), "--out", str(converted),
                     *[value for path in imports for value in ("--stub", str(path))]]),
        ("self", [str(tool), "self", "--sign", "--in", str(converted), "--out", str(executable)]),
        ("inspect", [str(tool), "self", "--inspect", "--file", str(executable)]),
        ("extract", [str(tool), "self", "--extract", "--file", str(executable), "--out", str(extracted)]),
    ]
    receipt = {"schema": "ps5-qwen-local-self-v1", "driver": selected, "native_link_receipt": record(link_snapshot),
               "lossless_driver_tables":driver_tables,
               "linked_driver":linked.get('linked_driver',selected),
               "engine_build_receipt": record(engine_snapshot),
               "native_link_receipt_origin": record(link_receipt),
               "native_pie": record(image), "format_tool": record(tool), "format_tool_sources": [record(path) for path in sources + headers],
               "format_tool_compile": compile_command, "console_access": False, "installed": False,
               "model_loaded": False, "release_qualified": False, "steps": []}
    if native_platform_snapshot:receipt['native_platform_build_receipt']=record(native_platform_snapshot)
    if external_shader_file:receipt['external_shader_file']=external_shader_file
    for name, command in commands:
        result = subprocess.run(command, env=env, capture_output=True)
        (a.out / (name + ".private.log")).write_bytes(result.stdout + result.stderr)
        receipt["steps"].append({"name": name, "returncode": result.returncode, "command": command})
        (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if result.returncode: raise SystemExit(result.stderr.decode("utf-8", "replace"))
        if name == "inspect" and b"integrity: valid" not in result.stdout:
            raise ValueError("SELF integrity inspection did not confirm success")
        print(name + " passed", flush=True)
    # SELF wrapping normalizes ELF header fields; compare with the wrapper's
    # documented normalized form rather than claiming an identical raw header.
    if not extracted.exists() or extracted.stat().st_size < 64:
        raise ValueError("SELF extraction is incomplete")
    expected = bytearray(converted.read_bytes())
    expected[18:20] = struct.pack("<H", 0x3e)
    if expected[7] in (0, 3): expected[7] = 9
    if struct.unpack_from("<H", expected, 16)[0] == 0: struct.pack_into("<H", expected, 16, 2)
    recovered = extracted.read_bytes()
    phoff = struct.unpack_from("<Q", expected, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", expected, 54)
    if recovered[:phoff + phsize * phcount] != expected[:phoff + phsize * phcount]:
        raise ValueError("SELF roundtrip header verification failed")
    checked_segments = 0
    for index in range(phcount):
        kind, _, offset, _, _, size = struct.unpack_from("<IIQQQQ", expected, phoff + index * phsize)
        if kind not in (1, 2, 0x61000000) or not size: continue
        if recovered[offset:offset + size] != expected[offset:offset + size]:
            raise ValueError("SELF roundtrip segment verification failed")
        checked_segments += 1
    receipt.update(converted_elf=record(converted), SELF=record(executable), extracted_elf=record(extracted),
                   integrity_verified=True, real_module_import_audit=imported,
                   roundtrip_segments_verified=checked_segments)
    if driver_tables:
        from driver_table_storage import audit_converted_storage
        receipt['converted_driver_table_audit']=audit_converted_storage(image,converted,driver_tables)
    (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"local_SELF_created": True, "sha256": sha(executable), "console_access": False}))


if __name__ == "__main__":
    main()
