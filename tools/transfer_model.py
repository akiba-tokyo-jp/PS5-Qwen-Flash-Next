#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate private data-only admissions, then stream the complete original model.

Default behavior is offline validation. Execution requires an explicit private
admission, fresh unchanged CPU evidence and an owned prepared model directory.
No title launch, model evaluation, GPU initialization or remote deletion occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from model_transfer_batch import run_batch, validate_plan
from model_transport import REMOTE_ROOT
from plan_model_transfer import preparation_gate
from ps5_model_connection import PS5ModelConnection

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()


def bounded_json(path, limit=1 << 20):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or not 0 < path.stat().st_size <= limit:
        raise ValueError("A bounded regular local metadata file is required")
    with path.open("rb") as stream: raw = stream.read(limit + 1)
    if not 0 < len(raw) <= limit: raise ValueError("Local metadata exceeded its read bound")
    return json.loads(raw)


def record_bytes(record, cache, limit=1 << 20):
    original = Path(record["path"])
    if original.is_symlink(): raise ValueError("Symlinked admission evidence is not accepted")
    path = original.resolve()
    if not path.is_relative_to(cache) or not stat.S_ISREG(path.stat().st_mode) or not 0 < path.stat().st_size <= limit:
        raise ValueError("Admitted evidence must be a bounded regular data-disk file")
    with path.open("rb") as stream: raw = stream.read(limit + 1)
    if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError("Admitted local evidence changed")
    return raw


def require_admission(admission, plan_sha):
    if (admission.get("schema") != "ps5-qwen-model-data-transfer-admission-v1" or
            admission.get("model_data_transfer_enabled") is not True or
            admission.get("GPU_execution_enabled") is not False or
            admission.get("model_loading_enabled") is not False or
            admission.get("plan_sha256") != plan_sha or admission.get("remote_root") != REMOTE_ROOT):
        raise ValueError("An exact private data-only transfer admission is required")


def validate_original_plan(workspace, cache, plan_path):
    """Shared original-model gate; it grants no remote operation by itself."""
    if plan_path.is_symlink(): raise ValueError("A regular admitted transfer plan is required")
    plan_path = plan_path.resolve()
    if not plan_path.is_relative_to(cache): raise ValueError("The original transfer plan must remain on the data disk")
    plan = bounded_json(plan_path)
    receipt_bytes = record_bytes(plan["receipt_copy"], cache)
    original_bytes = record_bytes(plan["original_receipt"], cache)
    if original_bytes != receipt_bytes: raise ValueError("The original receipt copy differs")
    receipt = json.loads(receipt_bytes)
    directory = Path(plan["source_directory"]).resolve()
    if not directory.is_relative_to(cache): raise ValueError("Original model sources must remain on the data disk")
    if (Path(plan["original_receipt"]["path"]).resolve() != directory / "model-receipt.json" or
            Path(plan["receipt_copy"]["path"]).resolve() != plan_path.parent / "model-receipt.private.json"):
        raise ValueError("The original receipt and frozen plan copy paths differ")
    preparation_gate(receipt, bounded_json(directory / "conversion-status.private.json"))
    validate_plan(plan, receipt_bytes)
    lock = bounded_json(ROOT / "native/qwen_flash_next/dependencies.lock.json")
    upstream = cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    compiler = workspace / "toolchain/msys-clang64/clang64/bin/clang++.exe"
    expected = [ROOT / "tools/model_transfer_receipt.cpp", ROOT / "native/app/model_receipt.h",
                ROOT / "native/app/memory_admission.h", upstream / "vendor/nlohmann/json.hpp", compiler]
    recorded = plan["validator_inputs"]
    if [Path(row["path"]).resolve() for row in recorded] != [path.resolve() for path in expected]:
        raise ValueError("Native receipt validator source/toolchain provenance differs")
    for row in recorded:
        if sha(row["path"]) != row["sha256"]: raise ValueError("A native receipt validator input changed")
    executable = plan_path.parent / "model-transfer-receipt.exe"
    if Path(plan["validator"]["path"]).resolve() != executable or sha(executable) != plan["validator"]["sha256"]:
        raise ValueError("The exact host-built native receipt validator is required")
    env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get("PATH", ""))
    result = subprocess.run([str(executable), plan["receipt_copy"]["path"]], capture_output=True, env=env, timeout=30)
    if result.returncode: raise ValueError("The actual native original-model receipt gate rejected execution")
    native = json.loads(result.stdout)
    if native != plan["native_receipt_gate"]: raise ValueError("The actual native receipt result changed")
    return dict(plan=plan, receipt_bytes=receipt_bytes)


def validate_console_evidence(admission, workspace, cache, reservation):
    """Shared unchanged-CPU/restoration gate; directory and bulk scopes differ."""
    context_raw = record_bytes(admission["completed_context"], cache)
    context = json.loads(context_raw)
    if (context.get("original_restored") is not True or context.get("original_numerical_re_admission") != "passed" or
            context.get("complete_original_SELF_readback_after_shutdown") is not True or
            context.get("console_reserved") is not True or context.get("native_running") is not False or
            context.get("gateway_running") is not False or context.get("model_loaded") is not False):
        raise ValueError("Complete original restoration/readmission and the existing reservation are required")
    baseline = bounded_json(context["final_session"])
    fresh = json.loads(record_bytes(admission["fresh_session"], cache))
    observed = json.loads(record_bytes(admission["fresh_CPU_admission"], cache))
    interval = json.loads(record_bytes(admission["fresh_host_interval"], cache))
    manifest = json.loads(record_bytes(admission["fresh_CPU_manifest"], cache))
    log = record_bytes(admission["fresh_CPU_log"], cache)
    reference_source = cache / "build/display-metadata-observer-016/observer.c"
    sources = [row for row in manifest["frozen_inputs"] if Path(row["path"]).name == "observer.c"]
    nonce = manifest["nonce"]
    if (len(sources) != 1 or sha(sources[0]["path"]) != sources[0]["sha256"] or
            sources[0]["sha256"] != sha(reference_source)):
        raise ValueError("The unchanged reviewed metadata-only CPU observer is required")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce) or not any(
            line.startswith(b"END success=1 log_healthy=1 ") and ("nonce=" + nonce).encode() in line for line in log.splitlines()):
        raise ValueError("A complete fresh-nonce CPU observation is required")
    if (fresh["boot"] != baseline["boot"] or fresh["services"] != baseline["services"] or
            fresh["double_snapshot_equal"] is not True or fresh["native_eboot_count"] != 0 or fresh["runningBigApp"] != -1 or
            observed["state"] != "fresh_CPU_metadata_admitted" or observed["GPU_calls"] != 0 or
            Path(observed["session"]).resolve() != Path(admission["fresh_session"]["path"]).resolve()):
        raise ValueError("Fresh unchanged CPU boot/service/process guards are required")
    age = time.time_ns() // 1000000 - interval["host_after_epoch_ms"]
    if (not 0 <= age <= 300000 or not 0 <= interval["host_elapsed_ms"] <= 8000 or
            interval["host_after_epoch_ms"] < interval["host_before_epoch_ms"]):
        raise ValueError("The initial CPU observation must be fresh and bounded")
    reservation_path = reservation.resolve()
    if not reservation_path.is_relative_to(workspace / "driver-work") or reservation_path.name != "active-context.private.json":
        raise ValueError("The existing shared driver reservation path is required")
    pointer_raw = reservation_path.read_bytes()
    if Path(json.loads(pointer_raw)["context"]).resolve() != Path(admission["completed_context"]["path"]).resolve():
        raise ValueError("This task no longer owns the console reservation")
    return dict(context_raw=context_raw, context_path=Path(admission["completed_context"]["path"]),
        reservation_path=reservation_path, pointer_raw=pointer_raw, session=fresh)


def validate_local(args):
    cache = args.cache.resolve(); workspace = args.workspace.resolve()
    admission = bounded_json(args.admission)
    require_admission(admission, sha(args.plan))
    original = validate_original_plan(workspace, cache, args.plan)
    state = validate_console_evidence(admission, workspace, cache, args.reservation)
    plan = original["plan"]
    prepared = json.loads(record_bytes(admission["directory_preparation"], cache))
    exact = dict(remote_root=REMOTE_ROOT, directory_created=True, directory_uid=0, directory_mode="0755",
                 parent_ownership_restored=True, symlinks_rejected=True, marker_full_readback_verified=True,
                 owner_nonce=plan["nonce"], title_launches=0, GPU_calls=0)
    if any(type(prepared.get(key)) is not type(value) or prepared[key] != value for key, value in exact.items()):
        raise ValueError("The exact owned model directory preparation is required")
    marker_bytes = record_bytes(prepared["marker"], cache, 4096)
    marker = json.loads(marker_bytes)
    if (marker.get("schema") != "ps5-qwen-model-directory-owner-v1" or marker.get("nonce") != plan["nonce"] or
            marker.get("original_receipt_sha256") != plan["original_receipt"]["sha256"]):
        raise ValueError("The model directory owner differs from this original plan")
    # The context remains immutable throughout data transfer. Progress lives in
    # the separate batch directory; it is not a new GPU/runtime admission.
    connection_data = bounded_json(args.connection, 4096)
    return dict(**original, **state, marker_bytes=marker_bytes, host=connection_data["host"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "plan", "admission", "connection", "reservation", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--execute", action="store_true", help="Run only after all private data-only admissions pass")
    p.add_argument("--resume", action="store_true", help="Reuse only positively completed records; uncertain writes remain rejected")
    a = p.parse_args()
    state = validate_local(a)
    out = a.out.resolve(); cache = a.cache.resolve()
    sources = Path(state["plan"]["source_directory"]).resolve()
    if not out.is_relative_to(cache) or out.is_relative_to(sources) or sources.is_relative_to(out):
        raise ValueError("A separate data-disk transfer evidence directory is required")
    if not a.execute:
        print(json.dumps(dict(local_data_transfer_admissions="passed", console_access=False,
            transfer_started=False, model_loaded=False)))
        return
    connection = PS5ModelConnection(state["host"])
    marker_path = REMOTE_ROOT + "/.qwen-transfer-owner.json"
    def unchanged(path, original):
        with path.open("rb") as stream: return stream.read(len(original) + 1) == original
    def guard():
        if not unchanged(state["reservation_path"], state["pointer_raw"]) or not unchanged(state["context_path"], state["context_raw"]):
            raise ValueError("The shared reservation or original-restoration context changed")
        connection.idle_guard(state["session"]["services"])
        if connection.model_get(marker_path, 4096) != state["marker_bytes"]:
            raise ValueError("The owned destination marker changed")
    guard()
    allowed = {".qwen-transfer-owner.json"}
    if a.resume:
        for row in state["plan"]["files"]:
            name = row["original"]["path"]
            if (out / "files" / (name + ".complete.private.json")).exists(): allowed.add(name)
    with connection.ftp() as ftp:
        if any(row["name"] not in allowed for row in connection.directory_metadata(ftp)):
            raise ValueError("An unknown destination entry or unresolved partial requires review")
    result = run_batch(state["plan"], state["receipt_bytes"], connection, out,
        cache / "model-transfer.writer.lock", guard=guard, resume=a.resume)
    print(json.dumps(result))


if __name__ == "__main__": main()
