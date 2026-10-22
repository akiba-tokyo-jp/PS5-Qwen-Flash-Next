#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check original resident metadata using the exact pinned GGML buffer planner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()


def record(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "plan", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(); cache=args.cache.resolve(); workspace=args.workspace.resolve()
    out=args.out.resolve()
    if not out.is_relative_to(cache): raise ValueError("A fresh host-only data-disk output is required")
    lock=json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())["llama_cpp"]
    upstream=cache / "upstream" / ("llama.cpp-" + lock["revision"])
    archive=cache / ("llama-" + lock["revision"] + ".zip")
    if archive.stat().st_size!=lock["archive_bytes"] or sha(archive)!=lock["archive_sha256"]:
        raise ValueError("The exact pinned source archive is required")
    relative="ggml/src/ggml-backend.cpp"; source=upstream / relative
    with zipfile.ZipFile(archive) as bundle:
        raw=bundle.read("llama.cpp-" + lock["revision"] + "/" + relative)
    if source.read_bytes()!=raw: raise ValueError("The actual allocator source differs from the pinned original")
    text=raw.decode(); start=text.index("struct ggml_backend_buft_alloc_buffer_n_plan_item {")
    stop=text.index("// default implementation of alloc_buffer_n",start)
    actual=text[start:stop]
    if actual.count("static ggml_backend_buft_alloc_buffer_n_plan_t ")!=1:
        raise ValueError("The pinned planner extraction boundary changed")
    # Check that the backend's value used by admission is the reduced batching
    # target, and that no force-max environment override is added by the client.
    backend=upstream / "ggml/src/ggml-vulkan/ggml-vulkan.cpp"; vulkan=backend.read_text()
    required=("return ctx->device->suballocation_block_size;",
        "device->suballocation_block_size = std::min(device->suballocation_block_size, device->max_memory_allocation_size);")
    if any(value not in vulkan for value in required): raise ValueError("The source batching/limit contract changed")
    app=ROOT / "native/app/native_main.cpp"; app_text=app.read_text()
    if ('setenv("GGML_VK_SUBALLOCATION_BLOCK_SIZE","2147483648",1)' not in app_text or
            "GGML_VK_FORCE_MAX_ALLOCATION_SIZE" in app_text or "GGML_VK_FORCE_MAX_BUFFER_SIZE" in app_text):
        raise ValueError("The client must request a batching target without overriding physical limits")
    plan=args.plan.resolve()
    if not plan.is_relative_to(cache) or not 0<plan.stat().st_size<=1<<20:
        raise ValueError("The complete bounded host tensor plan is required")
    test=ROOT / "tests/model_buffer_plan.cpp"; compiler=workspace / "toolchain/msys-clang64/clang64/bin/clang++.exe"
    before=[record(path) for path in (source,backend,app,plan,test,compiler)]
    out.mkdir(parents=True,exist_ok=False); include=out / "actual-buffer-plan.inc"; include.write_text(actual,newline="\n")
    executable=out / "model-buffer-plan.exe"
    command=[str(compiler),"-std=c++17","-O0","-Wall","-Wextra","-Werror","-I",str(out),
        "-I",str(upstream / "vendor"),str(test),"-o",str(executable)]
    env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get("PATH",""))
    for name,cmd in (("compile",command),("actual-pinned-planner",[str(executable),str(plan)])):
        result=subprocess.run(cmd,capture_output=True,env=env,timeout=120)
        (out / (name + ".private.log")).write_bytes(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError("The actual pinned buffer planner check failed")
    if before!=[record(path) for path in (source,backend,app,plan,test,compiler)]:
        raise ValueError("A checked buffer planning input changed")
    result=json.loads(result.stdout)
    result.update(schema="ps5-qwen-pinned-buffer-planner-check-v1",inputs=before,
        actual_planner=record(include),executable=record(executable),upstream_revision=lock["revision"],
        check_modified_upstream_tree=False,source_inputs_stable=True)
    with (out / "receipt.private.json").open("x") as stream: json.dump(result,stream,indent=2);stream.write("\n")
    print(json.dumps({key:result[key] for key in ("pinned_allocator_plan_cases","device_tensor_count",
        "largest_tensor_bytes","requested_batch_target_bytes","console_access","physical_memory_admitted")}))


if __name__=="__main__": main()
