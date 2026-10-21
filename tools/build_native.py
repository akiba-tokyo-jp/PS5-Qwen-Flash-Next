#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually link the real Qwen application with its pinned PS5 driver.

Produces an intermediate native PIE and local provenance only. No model load,
SELF packaging, installation, console access or CI occurs. Runtime execution
and numerical/memory admission remain separate checks.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from driver_inputs import sha, validate_driver

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    path = Path(path).resolve()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--driver-root", type=Path, required=True)
    parser.add_argument("--driver-manifest", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--runtime-imports", type=Path, required=True,
                        help="Local source-generated SceAgc import stubs; never copied to the repository")
    parser.add_argument("--jobs", type=int, default=4)
    a = parser.parse_args()
    if not 1 <= a.jobs <= 8:
        parser.error("jobs must be between 1 and 8")
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    selected = validate_driver(a.driver_root, a.driver_manifest, lock["ps5_vulkan_inference"])
    workspace, cache = a.workspace.resolve(), a.cache.resolve()
    engine = cache / "build/llama-ps5"
    receipt_path = engine / "receipt.private.json"
    built = json.loads(receipt_path.read_text())
    if (built.get("compile_returncode") != 0 or built.get("upstream_revision") != lock["llama_cpp"]["revision"] or
            built.get("driver_inputs") != selected or built.get("application_overlay_sha256") != sha(ROOT / "native/app/expert_policy.h")):
        raise ValueError("Rebuild the engine with the exact selected driver and application overlay first")
    expected_patches = [{"name": p.name, "sha256": sha(p)} for p in sorted((ROOT / "patches/llama").glob("*.patch"))]
    if built["upstream_patches"] != expected_patches:
        raise ValueError("Engine receipt does not match current application patches")
    for artifact in built["artifacts"]:
        if sha(artifact["path"]) != artifact["sha256"]:
            raise ValueError("Engine archive changed after its build receipt")
    out = cache / "build/application-native"
    objects = out / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    source = cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    llvm = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    library = sdk / "target/lib"
    includes = [ROOT / "native/app", source / "include", source / "ggml/include", source / "common",
                source / "src", source / "vendor", source / "vendor/nlohmann", source / "vendor/cpp-httplib"]
    flags = ["--no-default-config", "--target=x86_64-sie-ps5", "-fno-stack-protector", "-fno-plt",
             "-femulated-tls", "-fdenormal-fp-math=ieee", "-fPIC", "-std=c++17", "-O1", "-DNDEBUG",
             "-fvisibility-nodllstorageclass=default", "-fexceptions", "-fcxx-exceptions", "-frtti",
             "-nostdinc++", "-isystem", str(sdk / "target/include/c++/v1"), "-isystem", str(sdk / "target/include")]
    flags += [value for path in includes for value in ("-I", str(path))]
    files = [ROOT / "native/app" / name for name in ("session.cpp", "llama_engine.cpp", "http_app.cpp", "native_main.cpp",
                                                   "vulkan_bridge.cpp", "native_socket.cpp", "monitor_raster.cpp",
                                                   "native_display.cpp", "startup.cpp", "gpu_admission.cpp", "native_fault.cpp", "native_memory.cpp")]
    files += [source / "common/jinja" / name for name in ("lexer.cpp", "parser.cpp", "runtime.cpp", "value.cpp", "string.cpp")]
    files += [source / "common/json.cpp", source / "common/unicode.cpp", source / "src/unicode.cpp",
              source / "src/unicode-data.cpp", source / "vendor/cpp-httplib/httplib.cpp",
              a.driver_root / "tooling/native/app_crt.cpp"]
    # Fingerprint header changes as well as translation units and compiler flags.
    header_paths = [path for directory in (ROOT / "native/app", source / "common/jinja", source / "vendor/cpp-httplib")
                    for path in sorted(directory.glob("*.h"))]
    header_inputs = [record(path) for path in header_paths]
    headers = b"".join(path.read_bytes() for path in header_paths)
    compiler_hash = sha(llvm / "clang++.exe")
    source_inputs = [record(path) for path in files]
    env = os.environ.copy()
    env["PATH"] = str(workspace / "toolchain/msys-clang64/clang64/bin") + os.pathsep + env.get("PATH", "")

    def compile_one(path):
        local_flags = flags + (["-I", str(workspace / "toolchain/Vulkan-Headers/include")] if path.name == "vulkan_bridge.cpp" else [])
        identity = hashlib.sha256((str(path) + json.dumps(local_flags) + compiler_hash).encode() + path.read_bytes() + headers).hexdigest()
        obj = objects / (path.stem + "-" + identity[:20] + ".o")
        command = [str(llvm / "clang++.exe"), *local_flags, "-c", str(path), "-o", str(obj)]
        if not obj.exists():
            result = subprocess.run(command, env=env, capture_output=True)
            (objects / (obj.stem + ".private.log")).write_bytes(result.stdout + result.stderr)
            if result.returncode:
                obj.unlink(missing_ok=True)
                raise RuntimeError(result.stderr.decode("utf-8", "replace"))
        print("compiled " + path.name, flush=True)
        return obj, command

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        compiled = list(pool.map(compile_one, files))
    if source_inputs != [record(path) for path in files] or header_inputs != [record(path) for path in header_paths]:
        raise ValueError("An application source changed during compilation")
    # Keep deterministic source/link order and all static constructor sections.
    elf = out / "qwen-native.pie.elf"
    driver_archive = Path(selected["archive_path"])
    engine_archives = [Path(row["path"]) for row in built["artifacts"]]
    static_runtime = [library / name for name in ("libc++.a", "libc++abi.a", "libunwind.a", "libps5platform.a", "libc.a")]
    builtins = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/lib/clang/23/lib/linux/libclang_rt.builtins-x86_64.a"
    imports = [a.runtime_imports / "libSceAgc.so", a.runtime_imports / "libSceAgcDriver.so"]
    imports += [library / name for name in ("libc_stub_weak.so", "libSceLibcInternal.so", "libkernel.so",
                                           "libkernel_stub_weak.so", "libSceNet.so", "libSceVideoOut.so", "libSceSystemService.so")]
    command = [str(llvm / "ld.lld.exe"), "-m", "elf_x86_64", "-pie", "-e", "_start", "-T", str(ROOT / "cmake/native-unwind.ld"),
               "-L", str(a.driver_root / "tooling/native"), "-L", str(library), "--eh-frame-hdr", "-z", "max-page-size=0x4000", "--hash-style=gnu",
               "--exclude-libs=ALL", "-Map=" + str(out / "native-link.private.map"), "-o", str(elf)]
    # The public SDK supplies a real pipe-backed memstream implementation. Its
    # flush/close wrappers publish the caller-owned buffer; preserve both hooks.
    command += ["--defsym=open_memstream=ps5_open_memstream", "--wrap=fclose", "--wrap=fflush"]
    command += ["--wrap=abort"]
    command += ["--defsym=mprotect=qwen_native_mprotect"]
    # SDK dlfcn wrappers test these optional payload-loader hooks for null.
    # This statically linked native title has no payload dynamic loader. Preserve
    # the normal absent-weak-symbol semantics without inventing native imports.
    command += ["--defsym=" + name + "=0" for name in
                ("__dlopen", "__dlsym", "__dlfunc", "__dlclose", "__dlerror", "__dladdr")]
    # Native module imports must exist in public provider metadata. Bind the
    # SDK's documented compatibility implementations rather than importing
    # unavailable FreeBSD locale, TLS and POSIX routines from a weak stub.
    compatibility = ("__cxa_thread_atexit_impl", "qsort_r", "mkstemps", "openlog", "popen", "pclose", "__xuname",
        "__assert", "__memset_chk", "localtime_r", "gmtime_r", "newlocale", "freelocale", "strtod_l", "strtof_l", "dladdr",
        "utimensat", "futimens", "localeconv_l", "strtoll_l", "strtoull_l", "strtold_l", "snprintf_l", "sscanf_l", "asprintf_l",
        "strcoll_l", "strxfrm_l", "strftime_l", "wcscoll_l", "wcsxfrm_l", "btowc_l", "wctob_l", "iswctype_l", "mbrlen_l",
        "mbrtowc_l", "mbsrtowcs_l", "mbsnrtowcs_l", "wcrtomb_l", "wcsnrtombs_l", "mbtowc_l", "___mb_cur_max_l",
        "___runetype_l", "___tolower_l", "___toupper_l", "__runes_for_locale", "catopen", "catgets", "catclose", "backtrace",
        "backtrace_symbols_fd", "getaddrinfo", "freeaddrinfo", "if_nameindex", "if_freenameindex", "opendir", "fdopendir",
        "readdir", "rewinddir", "dirfd", "closedir", "nl_langinfo", "nl_langinfo_l", "getpwuid_r", "posix_fallocate",
        "access", "openat", "unlinkat", "fchmodat", "fstatat", "mkdirat", "renameat", "memfd_create",
        "arc4random", "arc4random_buf", "arc4random_uniform", "clock_nanosleep")
    command += ["--defsym=" + name + "=ps5_" + name for name in compatibility]
    command += ["--wrap=" + name for name in ("malloc", "calloc", "realloc", "free", "posix_memalign",
                "aligned_alloc", "memalign", "malloc_usable_size", "reallocf", "reallocarray", "getline", "getdelim")]
    command += ["--version-script", str(ROOT / "cmake/native-symbols.map")]
    # The pinned linker script explicitly KEEP's every initializer array.
    # Discard unreachable payload-only SDK routines and their private imports.
    command += ["--gc-sections"]
    command += [str(obj) for obj, _ in compiled]
    # Prefer actual native libc/kernel exports. The payload SDK's libc archive
    # contains optional payload-loader/kernel helpers unsuitable for a title.
    public_imports = [path for path in imports if not path.name.endswith("_stub_weak.so")]
    weak_imports = [path for path in imports if path.name.endswith("_stub_weak.so")]
    command += ["--as-needed", *map(str, public_imports)]
    command += ["--start-group", *map(str, engine_archives), str(driver_archive), *map(str, static_runtime), str(builtins), "--end-group"]
    command += [*map(str, weak_imports)]
    inputs = [*(obj for obj, _ in compiled), *engine_archives, driver_archive, *static_runtime, builtins, *imports,
              ROOT / "cmake/native-unwind.ld", ROOT / "cmake/native-symbols.map",
              a.driver_root / "tooling/native/ps5-pie.ld", receipt_path]
    before = [record(path) for path in inputs]
    receipt = {"schema": "ps5-qwen-native-link-v1", "driver": selected, "engine_receipt": record(receipt_path),
               "compiler": record(llvm / "clang++.exe"), "linker": record(llvm / "ld.lld.exe"),
               "application_sources": source_inputs, "application_headers": header_inputs,
               "console_access": False, "model_loaded": False, "learned_host_inference": False,
               "SELF_packaged": False, "CI": False, "compile_commands": [cmd for _, cmd in compiled],
               "link_command": command, "inputs_before": before}
    result = subprocess.run(command, env=env, capture_output=True)
    (out / "link.private.log").write_bytes(result.stdout + result.stderr)
    receipt["link_returncode"] = result.returncode
    (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if result.returncode:
        raise SystemExit(result.stderr.decode("utf-8", "replace")[-14000:])
    after = [record(path) for path in inputs]
    if before != after:
        raise ValueError("A native link input changed during the build")
    symbols = subprocess.check_output([str(llvm / "llvm-nm.exe"), "--defined-only", str(elf)], text=True)
    for name in ("_start", "main", "catchReturnFromMain", "qwen_native_halt", "llama_app_mmap_prefetch_disabled", "llama_app_expert_policy_enabled", "llama_app_expert_counters", "vkGetInstanceProcAddr"):
        if not re.search(r"\b" + re.escape(name) + r"$", symbols, re.M):
            raise ValueError("Required native integration symbol is absent: " + name)
    sections = subprocess.check_output([str(llvm / "llvm-readelf.exe"), "--wide", "--sections", str(elf)], text=True)
    initializers = re.search(r"\]\s+\.init_array\s+\S+\s+\S+\s+\S+\s+([0-9a-fA-F]+)", sections)
    if not initializers or not int(initializers[1], 16):
        raise ValueError("Native static constructors were lost")
    dynamic = subprocess.check_output([str(llvm / "llvm-readelf.exe"), "--dynamic", str(elf)], text=True)
    providers = re.findall(r"Shared library: \[([^\]]+)\]", dynamic)
    expected_providers = {"libSceAgc.prx", "libSceAgcDriver.prx", "libSceLibcInternal.sprx",
                          "libkernel.sprx", "libSceNet.sprx", "libSceVideoOut.sprx", "libSceSystemService.sprx"}
    required_providers = expected_providers - {"libSceNet.sprx"}
    if not required_providers.issubset(providers) or set(providers) - expected_providers:
        raise ValueError("Unexpected native runtime provider set")
    receipt.update(inputs_after=after, input_hashes_stable=True, artifact=record(elf),
                   initializer_slots=int(initializers[1], 16) // 8,
                   runtime_providers=providers,
                   required_engine_and_driver_symbols_present=True)
    (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"native_link": "passed", "driver_revision": selected["source_revision"],
                      "profile": selected["profile"], "artifact_sha256": sha(elf), "console_access": False}))


if __name__ == "__main__":
    main()
