#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resume a positively timed-out host conversion, retaining audited split work.

No console access or learned inference is implemented. A read-only checkpoint
binds the completed original SHA pass to unchanged file identities. A fresh
attempt may retain structurally complete splits, but every final tensor still
undergoes the original independent audit and every output receives a new hash.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from qwen_flash_next import LOCK, ROOT, json_write, safe_name, writer_lease
from convert_model import converter_sources, digest
from resumable_gguf import identity

ORIGINAL_TOOLS = ("convert_model.py", "bounded_conversion.py", "audit_conversion.py",
                  "qwen_flash_next.py", "fetch_engine.py", "prepare_model.py")
from resume_provenance import RESUME_TOOLS, validate_adapter


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest(path))


def process_library(cache):
    sys.path.insert(0, str(cache / "host-io-tools/psutil-7.1.3"))
    import psutil
    if psutil.__version__ != "7.1.3": raise ValueError("The host process inspector differs")
    return psutil


def tool_hashes(names): return {name: digest(ROOT / "tools" / name) for name in names}


def direct_worker_command(arguments):
    # Windows venv redirectors can outlive subprocess.run's tracked launcher.
    # Launch the actual interpreter directly with this environment's exact
    # import paths, so a host timeout terminates the tracked writer itself.
    executable = Path(sys._base_executable).resolve()
    bootstrap = ("import runpy,sys;sys.path[:]=%r;sys.prefix=%r;sys.exec_prefix=%r;sys.argv=%r;"
        "runpy.run_path(sys.argv[0],run_name='__main__')") % (sys.path, sys.prefix, sys.exec_prefix, arguments)
    return [str(executable), "-B", "-c", bootstrap]


def checkpoint(args):
    cache, previous = args.cache.resolve(), args.previous.resolve()
    if previous.parent != cache: raise ValueError("The previous output must belong to the exact model cache")
    preparation = cache / "model-preparation-005.private.json"
    state, prep = read(previous / "conversion-status.private.json"), read(preparation)
    if (state["phase"] != "converting_BF16" or state["pid"] != 29608 or
            prep["phase"] != "conversion_started" or prep["pid"] != 29608):
        raise ValueError("The known original SHA-completed live conversion is required")
    frozen = read(cache / "model-data-continuation-002/intent.private.json")
    tools = tool_hashes(ORIGINAL_TOOLS)
    for name, sha in tools.items():
        rows = [row for row in frozen["sources"] if Path(row["path"]).resolve() == ROOT / "tools" / name]
        if len(rows) != 1 or rows[0]["sha256"] != sha: raise ValueError("An original preparation source changed")
    psutil = process_library(cache)
    processes = []
    for pid, expected in ((29608, 1792643805.733826), (15500, 1792662619.3382335), (32632, 1792662619.1998374)):
        process = psutil.Process(pid)
        if abs(process.create_time() - expected) > .001: raise ValueError("An original process identity changed")
        processes.append(dict(pid=pid, created_epoch=process.create_time(), command=process.cmdline()))
    stdout = cache / "model-preparation-005.stdout.private.log"
    lines = stdout.read_text(encoding="utf-8").splitlines()
    manifest = read(cache / "metadata/checkpoint.json")
    if manifest["revision"] != LOCK["model"]["revision"] or manifest["quantization"] or len(manifest["files"]) != 131:
        raise ValueError("The complete original BF16 source manifest differs")
    completed = [line for line in lines if line.startswith("Original shard verified: ")]
    if completed != [f"Original shard verified: {i}/131" for i in range(1, 132)]:
        raise ValueError("The original process did not journal every completed source SHA")
    boundary_ns = int(datetime.fromisoformat(prep["updated_at"]).timestamp() * 1_000_000_000)
    sources = []
    for row in manifest["files"]:
        path = cache / "model" / safe_name(row["name"])
        info = identity(path)
        if path.is_symlink() or info["bytes"] != row["bytes"] or info["modified_ns"] > boundary_ns:
            raise ValueError("A source changed after the original verification began")
        sources.append(dict(name=row["name"], expected_sha256=row["sha256"], identity=info))
    metadata = [record(cache / "metadata/checkpoint.json")]
    metadata += [record(p) for p in sorted((cache / "model").iterdir()) if p.is_file() and p.suffix != ".safetensors"]
    value = dict(schema="ps5-qwen-source-verification-checkpoint-v1", captured_at_UTC=datetime.now(timezone.utc).isoformat(),
        cache=str(cache), previous=str(previous), original_model_revision=manifest["revision"],
        original_verification_reused=True, fresh_original_payload_rehash=False,
        source_modification_bound_UTC=prep["updated_at"], original_processes=processes,
        original_preparation=prep, original_conversion=state, completed_original_SHA_journal=record(stdout),
        preparation_tool_sources=tools, metadata=metadata, sources=sources,
        console_access=False, learned_inference_performed=False)
    with args.checkpoint.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2) + "\n"); output.flush(); os.fsync(output.fileno())
    print(json.dumps(dict(checkpoint_written=True, original_SHA_verified_files=len(sources), fresh_payload_rehash=False, console_access=False)))


def read_only_leases(paths, leases):
    if os.name != "nt": raise ValueError("This source-preservation lease has only been qualified on Windows")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    for path in paths:
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
        if handle is None or handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), "An original source read-only lease was refused")
        leases.callback(kernel.CloseHandle, handle)


def validate_checkpoint(args, leases):
    cache, previous = args.cache.resolve(), args.previous.resolve()
    value = read(args.checkpoint)
    if (value["schema"] != "ps5-qwen-source-verification-checkpoint-v1" or
            Path(value["cache"]).resolve() != cache or Path(value["previous"]).resolve() != previous or
            value["preparation_tool_sources"] != tool_hashes(ORIGINAL_TOOLS) or
            value.get("original_verification_reused") is not True or value.get("fresh_original_payload_rehash") is not False):
        raise ValueError("The exact unchanged original verification checkpoint is required")
    if leases is not None:
        read_only_leases([cache / "model" / row["name"] for row in value["sources"]] +
            [Path(row["path"]) for row in value["metadata"]], leases)
    for row in value["sources"]:
        path = cache / "model" / safe_name(row["name"])
        if path.is_symlink() or identity(path) != row["identity"]:
            raise ValueError("An original verified source identity changed")
    if value["metadata"] != [record(row["path"]) for row in value["metadata"]]:
        raise ValueError("Pinned original metadata changed")
    journal = value["completed_original_SHA_journal"]
    if record(journal["path"]) != journal:
        raise ValueError("The completed original SHA journal changed")
    manifest = read(cache / "metadata/checkpoint.json")
    expected = {row["name"]: (row["sha256"], row["bytes"]) for row in manifest["files"]}
    supplied = {row["name"]: (row["expected_sha256"], row["identity"]["bytes"]) for row in value["sources"]}
    if (manifest["revision"] != LOCK["model"]["revision"] or manifest["quantization"] or
            len(expected) != 131 or len(value["sources"]) != 131 or expected != supplied):
        raise ValueError("The complete original SHA-verified source set differs")
    return value


def worker(args):
    from audit_conversion import inputs, expected_plan
    from bounded_conversion import wrap_transforms, CHUNK_BYTES
    from resumable_gguf import install, MAX_NEW_PAYLOAD_BYTES
    cache, out = args.cache.resolve(), args.out.resolve()
    gguf, _, model_class, manifest, config, sources_before = inputs(cache)
    plan, _, _ = expected_plan(cache)
    import numpy
    import convert_hf_to_gguf
    from gguf.gguf_writer import WriterState
    architecture = convert_hf_to_gguf.get_model_architecture(config, convert_hf_to_gguf.ModelType.TEXT)
    if convert_hf_to_gguf.get_model_class(architecture, mmproj=False) is not model_class:
        raise ValueError("The pinned text converter selected another architecture")
    original = model_class.modify_tensors
    wrapped, cursors, copies = wrap_transforms(original, plan, manifest, cache / "model", gguf, numpy)
    def progress(value):
        json_write(args.attempt / "resume-writer-progress.private.json", dict(updated_at_UTC=datetime.now(timezone.utc).isoformat(), **value))
        print(json.dumps(value), flush=True)
    outcome, restore = install(gguf.GGUFWriter, WriterState, args.previous, out, progress)
    model_class.modify_tensors = wrapped
    try:
        upstream = cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
        sys.argv = [str(upstream / "convert_hf_to_gguf.py"), str(cache / "model"), "--outtype", "bf16",
                    "--outfile", str(out / "qwen-flash-next-bf16.gguf"), "--split-max-size", "4G"]
        convert_hf_to_gguf.main()
        retained, written = set(outcome["retained_tensors"]), set(outcome["written_tensors"])
        if retained & written or retained | written != set(plan["tensors"]) or set(cursors) != set(copies):
            raise ValueError("The complete original planned tensor partition differs")
        if any(cursor.next != (0 if name in retained else len(cursor.parts)) for name, cursor in cursors.items()):
            raise ValueError("A retained or newly streamed original BF16 copy differs")
        provenance = dict(schema="ps5-qwen-resumed-copy-adapter-v1", pinned_sources_modified=False,
            chunk_limit_bytes=CHUNK_BYTES, maximum_source_read_bytes=max(c.maximum_read_bytes for c in cursors.values()),
            complete_planned_copy_partition=True, original_copy_tensors=len(copies),
            original_copy_BF16_bytes=sum(plan["tensors"][name]["bytes"] for name in copies),
            maximum_new_payload_bytes=MAX_NEW_PAYLOAD_BYTES,
            retained_copy_tensors=sum(name in retained for name in copies),
            written_copy_tensors=sum(name in written for name in copies),
            retained_copy_BF16_bytes=sum(plan["tensors"][name]["bytes"] for name in copies if name in retained),
            written_copy_BF16_bytes=sum(plan["tensors"][name]["bytes"] for name in copies if name in written),
            preparation_tool_sources=tool_hashes(ORIGINAL_TOOLS), resume_tool_sources=tool_hashes(RESUME_TOOLS),
            checkpoint=record(args.checkpoint),
            independent_payload_audit_required=True, console_access=False, learned_inference_performed=False)
    finally:
        model_class.modify_tensors = original; restore()
        for cursor in cursors.values(): cursor.close()
    if converter_sources(cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip"), upstream) != sources_before:
        raise ValueError("Pinned converter sources changed")
    json_write(args.attempt / "retention.private.json", outcome)
    provenance["retention_record"] = record(args.attempt / "retention.private.json")
    json_write(args.attempt / "resumed-copy-receipt.private.json", provenance)


def run(args):
    cache, previous, out = args.cache.resolve(), args.previous.resolve(), args.out.resolve()
    psutil = process_library(cache)
    state = read(previous / "conversion-status.private.json")
    continuation = read(cache / "model-data-continuation-002/status.private.json")
    if (state["phase"] != "failed" or state["error_type"] != "TimeoutExpired" or
            read(cache / "model-preparation-005.private.json")["phase"] != "failed" or
            continuation["phase"] != "failed_retained_for_review" or previous.joinpath("model-receipt.json").exists()):
        raise ValueError("Only the positively failed original timeout and stopped data continuation may resume")
    checkpoint_value = validate_checkpoint(args, None)
    for process in checkpoint_value["original_processes"]:
        if psutil.pid_exists(process["pid"]) and abs(psutil.Process(process["pid"]).create_time() - process["created_epoch"]) < .001:
            raise ValueError("An original conversion process is still alive")
    if psutil.pid_exists(29964) and abs(psutil.Process(29964).create_time() - 1792670927.8299885) < .001:
        raise ValueError("The previous data-only continuation is still alive")
    attempt = args.attempt.resolve()
    if (out.parent != cache or previous.parent != cache or attempt.parent != cache or
            len({out, previous, attempt}) != 3 or args.checkpoint.resolve().parent != cache):
        raise ValueError("Distinct original/new cache directories are required")
    args.attempt.mkdir(parents=True, exist_ok=False); out.mkdir(exist_ok=False)
    started = time.monotonic(); frozen = tool_hashes((*ORIGINAL_TOOLS, *RESUME_TOOLS)); writer_completed = False
    def status(phase, **fields):
        value = dict(schema="ps5-qwen-conversion-status-v1", phase=phase,
            pid=os.getpid(), updated_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
            console_access=False, learned_inference_performed=False, **fields)
        json_write(args.attempt / "status.private.json", value)
        if writer_completed or phase == "failed": json_write(out / "conversion-status.private.json", value)
    try:
        with writer_lease(cache / "model-preparation.lock.private"), writer_lease(cache / "model-download.lock.private"), ExitStack() as leases:
            validate_checkpoint(args, leases)
            # The destination must contain only writer outputs during conversion.
            # Keep status outside it until the writer has classified every split.
            arguments = [str(Path(__file__).resolve()), "worker", "--cache", str(cache),
                "--previous", str(previous), "--out", str(out), "--checkpoint", str(args.checkpoint.resolve()),
                "--attempt", str(args.attempt.resolve())]
            command = direct_worker_command(arguments)
            json_write(args.attempt / "intent.private.json", dict(command=command, pid=os.getpid(), frozen_sources=frozen,
                previous_failure=state, checkpoint=record(args.checkpoint), conversion_timeout_seconds=14400,
                audit_timeout_seconds=86400, hashing_timeout_seconds=43200, automatic_retries=0,
                direct_worker_interpreter=record(command[0]), original_source_read_leases_held=True,
                console_access=False, learned_inference_performed=False))
            status("resuming_BF16", timeout_seconds=14400, progress=str(args.attempt / "resume-writer-progress.private.json"))
            with (args.attempt / "conversion.private.log").open("x", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=14400,
                    env=dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"))
            if result.returncode: raise RuntimeError("The one-attempt resumed writer failed")
            writer_completed = True
            status("planning_complete_payload_audit")
            adapter = read(args.attempt / "resumed-copy-receipt.private.json")
            validate_adapter(adapter, {name: frozen[name] for name in ORIGINAL_TOOLS},
                {name: frozen[name] for name in RESUME_TOOLS})
            files = sorted(out.glob("*.gguf"))
            read_only_leases(files, leases)
            output_identities = {path.name: identity(path) for path in files}
            from audit_conversion import audit_conversion, inputs
            _, _, _, manifest, _, sources = inputs(cache)
            audit = audit_conversion(cache, out, files, status, 86400)
            outputs = []; deadline = time.monotonic() + 43200
            for index, path in enumerate(files):
                status("hashing_converted_files", verified=index, total=len(files))
                outputs.append(dict(path=path.name, bytes=path.stat().st_size, sha256=digest(path, deadline)))
            validate_checkpoint(args, None)
            if output_identities != {path.name: identity(path) for path in files}:
                raise ValueError("A converted output changed during its complete audit or final hash pass")
            if frozen != tool_hashes((*ORIGINAL_TOOLS, *RESUME_TOOLS)):
                raise ValueError("A resumed preparation source changed")
            if sources != converter_sources(cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip"),
                    cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])):
                raise ValueError("The original converter source identity changed")
            receipt = dict(schema="ps5-qwen-bf16-conversion-v2", original_revision=manifest["revision"],
                upstream_revision=LOCK["llama_cpp"]["revision"], outtype="bf16", original_shards_verified=True,
                files=outputs, converter_sources=sources, conversion_audit=audit, conversion_adapter=adapter,
                preparation_tool_sources={name: frozen[name] for name in ORIGINAL_TOOLS},
                resume_tool_sources={name: frozen[name] for name in RESUME_TOOLS},
                original_source_verification=checkpoint_value, console_access=False, learned_inference_performed=False)
            json_write(out / "model-receipt.json", receipt)
            status("completed", verified=len(files), total=len(files), receipt="model-receipt.json")
    except BaseException as error:
        if (out / "model-receipt.json").exists():
            (out / "model-receipt.json").rename(out / "model-receipt.not-admitted.private.json")
        status("failed", error_type=type(error).__name__, receipt_published=False)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("checkpoint", "run", "worker"))
    for name in ("cache", "previous", "checkpoint"): parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--out", type=Path); parser.add_argument("--attempt", type=Path)
    args = parser.parse_args()
    if args.command != "checkpoint" and (args.out is None or args.attempt is None): parser.error("out and attempt are required")
    globals()[args.command](args)


if __name__ == "__main__": main()
