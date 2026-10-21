#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually cross-build the pinned Qwen engine with the owner's current driver.

This builds static libraries only. It does not start CI, deploy a title, or
perform learned inference on the host. Build receipts are local-only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--driver-root", type=Path, required=True)
    p.add_argument("--driver-manifest", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--configure-only", action="store_true")
    a = p.parse_args()
    if not 1 <= a.jobs <= 12:
        p.error("jobs must be between 1 and 12")
    workspace, driver, cache = a.workspace.resolve(), a.driver_root.resolve(), a.cache.resolve()
    source = cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    if not (source / "src/models/qwen4exp.cpp").is_file():
        raise ValueError("Pinned upstream source is missing")
    source_receipt = json.loads((cache / "upstream/source-receipt.json").read_text())
    archive_source = cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip")
    if (source_receipt["revision"] != LOCK["llama_cpp"]["revision"]
            or source_receipt["archive_sha256"] != LOCK["llama_cpp"]["archive_sha256"]
            or sha(archive_source) != LOCK["llama_cpp"]["archive_sha256"]):
        raise ValueError("Upstream source archive identity mismatch")
    patches = []
    for patch in sorted((ROOT / "patches/llama").glob("*.patch")):
        check = subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, capture_output=True)
        if check.returncode == 0:
            subprocess.run(["git", "apply", str(patch)], cwd=source, check=True)
        else:
            reverse = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source, capture_output=True)
            if reverse.returncode:
                raise ValueError("Upstream patch does not apply cleanly: " + patch.name)
        patches.append({"name": patch.name, "sha256": sha(patch)})
    overlay_source = ROOT / "native/app/expert_policy.h"
    overlay_target = source / "src/llama-app-expert-policy.h"
    overlay_receipt = cache / "upstream/application-overlay.private.json"
    expected_previous = json.loads(overlay_receipt.read_text())["sha256"] if overlay_receipt.exists() else None
    overlay_hash = sha(overlay_source)
    if overlay_target.exists() and sha(overlay_target) not in (overlay_hash, expected_previous):
        raise ValueError("Existing expert policy overlay has unrecognized local changes")
    overlay_target.write_bytes(overlay_source.read_bytes())
    overlay_receipt.write_text(json.dumps({"source": "native/app/expert_policy.h", "sha256": overlay_hash}) + "\n")
    profile = json.loads(a.driver_manifest.read_text())
    archive = a.driver_manifest.resolve().parent / "libvulkan_radeon.experimental.a"
    if profile.get("profile") != "cumulative-idle" or sha(archive) != profile["archive_sha256"]:
        raise ValueError("Current selected driver profile does not match its receipt")
    revision = subprocess.check_output(["git", "-C", str(driver), "rev-parse", "HEAD"], text=True).strip()
    if revision != LOCK["ps5_vulkan_inference"]["revision"]:
        raise ValueError("Driver source revision differs from the selected dependency lock")
    if sha(archive) != LOCK["ps5_vulkan_inference"]["archive_sha256"]:
        raise ValueError("Driver archive differs from the selected dependency lock")
    sdk = workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    llvm = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    host = workspace / "toolchain/msys-clang64/clang64/bin"
    cmake = workspace / "toolchain/pydeps/cmake/data/bin/cmake.exe"
    ninja = workspace / "toolchain/pydeps/bin/ninja.exe"
    glslc = workspace / "toolchain/shaderc-clang64/clang64/bin/glslc.exe"
    include = workspace / "toolchain/Vulkan-Headers/include"
    out = cache / "build/llama-ps5"
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PS5_PAYLOAD_SDK=str(sdk), PS5_LLVM_BIN=str(llvm))
    env["PATH"] = os.pathsep.join(map(str, (host, llvm, cmake.parent, ninja.parent))) + os.pathsep + env.get("PATH", "")
    spirv = workspace / "toolchain/shaderc-clang64/clang64/share/cmake/SPIRV-Headers"
    spirv_header = workspace / "toolchain/shaderc-clang64/clang64/include/spirv/unified1/spirv.hpp"
    if not (spirv / "SPIRV-HeadersConfig.cmake").is_file() or not spirv_header.is_file():
        raise ValueError("The installed SPIRV-Headers package and headers are required")
    command = [str(cmake), "-S", str(source), "-B", str(out), "-G", "Ninja",
               "-DCMAKE_TOOLCHAIN_FILE=" + str(ROOT / "cmake/ps5.cmake"),
               "-DCMAKE_MAKE_PROGRAM=" + str(ninja), "-DCMAKE_BUILD_TYPE=Release",
               "-DBUILD_SHARED_LIBS=OFF", "-DGGML_BACKEND_DL=OFF", "-DGGML_NATIVE=OFF",
               "-DGGML_CPU_ALL_VARIANTS=OFF", "-DGGML_OPENMP=OFF", "-DGGML_CCACHE=OFF",
               "-DGGML_AVX=ON", "-DGGML_AVX2=ON", "-DGGML_FMA=ON", "-DGGML_F16C=ON",
               "-DGGML_BMI2=ON", "-DGGML_AVX512=OFF", "-DGGML_VULKAN=ON",
               "-DVulkan_INCLUDE_DIR=" + str(include), "-DVulkan_LIBRARY=" + str(archive),
               "-DVulkan_GLSLC_EXECUTABLE=" + str(glslc), "-DSPIRV-Headers_DIR=" + str(spirv),
               "-DHOST_C_COMPILER=" + str(host / "clang.exe"),
               "-DHOST_CXX_COMPILER=" + str(host / "clang++.exe"),
               "-DLLAMA_BUILD_COMMON=OFF", "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF",
               "-DLLAMA_BUILD_TOOLS=OFF", "-DLLAMA_BUILD_SERVER=OFF", "-DLLAMA_OPENSSL=OFF"]
    receipt = {"schema": "ps5-qwen-static-build-v1", "upstream_revision": LOCK["llama_cpp"]["revision"],
               "driver_repository": "akiba-tokyo-jp/PS5-Vulkan-Inference", "driver_revision": revision,
               "driver_profile": profile["profile"], "driver_archive_sha256": sha(archive),
               "persistent_caches_disabled_required": True, "CI": False, "console_executed": False,
               "learned_host_inference": False, "spirv_header_sha256": sha(spirv_header),
               "upstream_patches": patches,
               "application_overlay_sha256": overlay_hash,
               "configure_command": command}
    for name, cmd in [("configure", command), ("compile", [str(cmake), "--build", str(out), "--target", "llama", "--parallel", str(a.jobs)])]:
        if name == "compile" and a.configure_only:
            break
        with (out / (name + ".private.log")).open("w", encoding="utf-8") as stream:
            result = subprocess.run(cmd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        receipt[name + "_returncode"] = result.returncode
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            print((out / (name + ".private.log")).read_text(encoding="utf-8", errors="replace")[-11000:])
            raise SystemExit(result.returncode)
        print(name + " succeeded", flush=True)
    if not a.configure_only:
        paths = ["src/libllama.a", "ggml/src/libggml.a", "ggml/src/libggml-base.a",
                 "ggml/src/libggml-cpu.a", "ggml/src/ggml-vulkan/libggml-vulkan.a"]
        receipt["artifacts"] = [{"path": str(out / name), "bytes": (out / name).stat().st_size, "sha256": sha(out / name)} for name in paths]
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"out": str(out), "driver_revision": revision, "profile": profile["profile"], "console_executed": False}))


if __name__ == "__main__":
    main()
