#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile seven isolated model-I/O overrides without changing active sources.

Reuses the exact existing native engine compile recipes and archives. The final
application link must prove that the seven original archive members were omitted.
This tool performs no console access, model reads, driver build or deployment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINES = {
    "src/llama-mmap.cpp": "130601ff8c2b6e16668b70a1dca07cc09ae84328d91bbd5bd259aea5658103e7",
    "src/llama-moe-cache.cpp": "d0b19ef2e921ec16ed04e751d32cbc7682973e915f0df85b6cadc8800e0af6cd",
    "ggml/src/ggml-vulkan/ggml-vulkan-buffers.cpp": "83b8c27432046448597c3cdc034332fb0117354f2b705a0e61b601bf6556ba99",
    "ggml/src/ggml-vulkan/ggml-vulkan.cpp": "f9bb02f59483c252d71ba8c6af7528f17d893f1cf32261d9d5d3c618ca126502",
    "ggml/src/ggml-cpu/ggml-cpu.cpp": "ccf382d3fbf126b5ddb5850a0a970656fb24e00587da4003419439277c91cd01",
    "ggml/src/ggml-cpu/ops.cpp": "b565fea101889b8b73011ad26c5cafc242e3d10b0eb65d3aba4b53808d0f2e71",
    "ggml/src/ggml-backend.cpp": "79ade6b83b3d042e43e035fa81d2c672211a552af9af38e410a047e4ba2723a0"}

def source_archive(source):
    if source.startswith("src/"): return "libllama.a"
    if "/ggml-cpu/" in source: return "libggml-cpu.a"
    if source == "ggml/src/ggml-backend.cpp": return "libggml-base.a"
    return "libggml-vulkan.a"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def validate_overrides(path, base_receipt):
    data = json.loads(Path(path).read_text())
    if data.get("schema") != "ps5-qwen-model-io-overrides-v1" or data.get("state") != "compiled_not_console_admitted":
        raise ValueError("Complete isolated model-I/O override compilation is required")
    if data["base_engine_receipt"] != record(base_receipt):
        raise ValueError("The original native engine receipt changed")
    if data["bridge"] != record(ROOT / "native/app/mapped_source_bridge.h"):
        raise ValueError("The source-reader bridge changed")
    if data.get("logical_bridge") != record(ROOT / "native/app/logical_source_bridge.h"):
        raise ValueError("The logical source size bridge changed")
    if data.get("indexed_vector_policy") != record(ROOT / "native/app/indexed_vector.h"):
        raise ValueError("The indexed-vector policy or measurement bridge changed")
    if data.get("mapped_copy_policy") != record(ROOT / "native/app/mapped_copy.h"):
        raise ValueError("The bounded mapped-copy policy changed")
    if data.get("padded_bank_bridge") != record(ROOT / "native/app/padded_bank_bridge.h"):
        raise ValueError("The owned padded-layout dispatch bridge changed")
    if data.get("padded_cache_policy") != record(ROOT / "native/app/padded_cache_bridge.h") or data.get("padded_bank_layout") != record(ROOT / "native/app/padded_bank.h"):
        raise ValueError("The qualified padded-cache ABI or layout changed")
    if data.get("padded_cache_geometry") != record(ROOT / "native/app/padded_cache_geometry.h"):
        raise ValueError("The selected padded-cache geometry changed")
    patches = [record(p) for p in sorted((ROOT / "patches/native-model-io").glob("*.patch"))]
    if data["patches"] != patches or len(patches) != 7 or set(data["sources"]) != set(BASELINES):
        raise ValueError("The exact seven model-I/O overrides are required")
    artifacts = {Path(row["path"]).name: row for row in json.loads(Path(base_receipt).read_text())["artifacts"]}
    if len(data["objects"]) != 7 or {row["source"] for row in data["objects"]} != set(BASELINES):
        raise ValueError("Seven complete replacement objects are required")
    for row in data["objects"]:
        source = row["source"]
        expected_archive = source_archive(source)
        if row["archive"] != artifacts[expected_archive] or row["member"] != Path(source).name + ".o":
            raise ValueError("A source override does not match its original archive member")
        if row["object"] != record(row["object"]["path"]):
            raise ValueError("A compiled source override changed")
        if data["sources"][source]["original_sha256"] != BASELINES[source]:
            raise ValueError("An unrecognized engine source was used")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    source = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    base = a.cache / "build/llama-ps5/receipt.private.json"
    original = json.loads(base.read_text())
    if original.get("compile_returncode") != 0 or original["upstream_revision"] != lock["llama_cpp"]["revision"]:
        raise ValueError("The qualified original engine build is required")
    recipes_path = base.parent / "compile_commands.json"
    recipes = json.loads(recipes_path.read_text())
    artifacts = {Path(item["path"]).name: item for item in original["artifacts"]}
    isolated = out / "source"
    receipt = dict(schema="ps5-qwen-model-io-overrides-v1", base_engine_receipt=record(base),
        original_compile_recipes=record(recipes_path), bridge=record(ROOT / "native/app/mapped_source_bridge.h"),
        logical_bridge=record(ROOT / "native/app/logical_source_bridge.h"),
        indexed_vector_policy=record(ROOT / "native/app/indexed_vector.h"),
        mapped_copy_policy=record(ROOT / "native/app/mapped_copy.h"),
        padded_bank_bridge=record(ROOT / "native/app/padded_bank_bridge.h"),
        padded_cache_policy=record(ROOT / "native/app/padded_cache_bridge.h"),
        padded_bank_layout=record(ROOT / "native/app/padded_bank.h"),
        padded_cache_geometry=record(ROOT / "native/app/padded_cache_geometry.h"),
        patches=[record(p) for p in sorted((ROOT / "patches/native-model-io").glob("*.patch"))],
        sources={}, objects=[], steps=[], console_access=False, model_loaded=False, learned_host_inference=False)
    if len(receipt["patches"]) != 7:
        raise ValueError("The seven reviewed source patches are required")
    for name, digest in BASELINES.items():
        current = source / name
        if sha(current) != digest:
            raise ValueError("The exact original engine source changed: " + name)
        target = isolated / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(current.read_bytes().replace(b"\r\n", b"\n"))
        receipt["sources"][name] = dict(original_sha256=digest, normalized_sha256=sha(target))
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    environment = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""),
        GIT_CEILING_DIRECTORIES=str(out))
    def run(label, command, cwd, timeout=240):
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, timeout=timeout, shell=False)
        (out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        receipt["steps"].append(dict(name=label, returncode=result.returncode))
        if result.returncode:
            raise RuntimeError(label + ": " + result.stderr.decode("utf-8", "replace")[-5000:])
        print(label + " passed", flush=True)
    try:
        for index, patch in enumerate(receipt["patches"]):
            run("patch_check_" + str(index), ["git", "apply", "--check", patch["path"]], isolated)
            run("patch_apply_" + str(index), ["git", "apply", patch["path"]], isolated)
        for index, name in enumerate(BASELINES):
            rows = [r for r in recipes if Path(r["file"]).resolve() == (source / name).resolve()]
            if len(rows) != 1:
                raise ValueError("One exact original compile recipe is required: " + name)
            row = rows[0]
            command = row["command"]
            compiler = a.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe"
            if Path(command.split(" ", 1)[0].strip('"')).resolve() != compiler.resolve() or "--target=x86_64-sie-ps5" not in command:
                raise ValueError("The original recipe must use the selected PS5 C++ compiler")
            original_path = str((source / name).resolve())
            if command.count(original_path) != 1:
                raise ValueError("The original source argument is not uniquely identified")
            patched = isolated / name
            command = command.replace(original_path, subprocess.list2cmdline([str(patched)]))
            obj = out / (Path(name).name + ".o")
            command, count = re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',
                lambda _: "-o " + subprocess.list2cmdline([str(obj)]), command)
            if count != 1 or re.search(r"\s-(?:MF|MT|MD)\b", command):
                raise ValueError("The isolated compile output is not uniquely bounded")
            command += " -I" + subprocess.list2cmdline([str(ROOT / "native/app")])
            command += " -I" + subprocess.list2cmdline([str((source / name).parent)])
            receipt["sources"][name]["patched_sha256"] = sha(patched)
            run("compile_" + str(index), command, Path(row["directory"]))
            archive = artifacts[source_archive(name)]
            receipt["objects"].append(dict(source=name, object=record(obj), archive=archive,
                member=Path(row["output"]).name, command=command))
        if any(sha(source / name) != digest for name, digest in BASELINES.items()):
            raise ValueError("Active engine sources changed during isolated compilation")
        receipt["state"] = "compiled_not_console_admitted"
    except BaseException as error:
        receipt["state"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        (out / "manifest.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    validate_overrides(out / "manifest.private.json", base)


if __name__ == "__main__":
    main()
