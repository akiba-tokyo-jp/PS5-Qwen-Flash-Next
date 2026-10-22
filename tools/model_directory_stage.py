#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-attempt directory sequencing after separate original-plan/CPU admission.

This module has no CLI, console address, controller launcher or admission bypass.
The caller must validate the complete original plan, exact controller build,
fresh unchanged CPU session and shared reservation before supplying callbacks.
Every uncertain mutation is retained; neither failure nor reinvocation retries it.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import time
from model_transport import REMOTE_ROOT, exclusive_json

MARKER = ".qwen-transfer-owner.json"


def controller_result(raw, mode, marker_bytes):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 65536:
        raise ValueError("A bounded completed CPU controller log is required")
    lines = raw.decode("ascii").splitlines()
    begin = f"BEGIN mode={mode} uid=1 euid=0 GPU_calls=0 title_launches=0"
    end = (f"END success=1 mode={mode} parent_ownership_restored=" +
           ("0" if mode == "prepare" else "1") + " GPU_calls=0 title_launches=0")
    expected = [begin]
    if mode == "finalize":
        row = ("MODEL_DIRECTORY uid=0 gid=0 mode=0755 marker_bytes=" + str(marker_bytes) +
               " no_symlinks=1 marker_verified=1")
        expected += [row, row]
    expected.append(end)
    if mode not in {"prepare", "finalize"} or lines != expected:
        raise ValueError("The exact positive CPU directory result is required")


def prepare_directory_once(connection, manifest, out, *, guard, control):
    """Use one admitted CPU controller and publish proof only after finalization.

    control(mode, out) must invoke the exact separately admitted artifact once,
    with its mode-specific exclusive remote log and immutable execution record.
    guard() must retain the admitted context/reservation and idle services while
    checking the pre-existing task-owner marker, including before each mutation.
    """
    if (manifest.get("schema") != "ps5-qwen-model-directory-controller-v1" or
            manifest.get("remote_root") != REMOTE_ROOT or
            manifest.get("allowed_actions") != ["prepare", "finalize", "verify"] or
            manifest.get("input_hashes_stable") is not True or
            manifest.get("imports_subset_of_qualified_controller") is not True or
            manifest.get("console_access") is not False or
            type(manifest.get("title_launches")) is not int or manifest["title_launches"] != 0 or
            type(manifest.get("GPU_calls")) is not int or manifest["GPU_calls"] != 0):
        raise ValueError("A separately admitted CPU-only directory controller is required")
    nonce = manifest["owner_nonce"]
    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("The original model plan nonce is required")
    marker = manifest["marker"]; path = Path(marker["path"])
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or not 0 < path.stat().st_size <= 4096:
        raise ValueError("A bounded regular exact owner marker is required")
    with path.open("rb") as stream: raw = stream.read(4097)
    if len(raw) != marker["bytes"] or hashlib.sha256(raw).hexdigest() != marker["sha256"]:
        raise ValueError("The original model directory marker changed")
    value = json.loads(raw)
    if (value.get("schema") != "ps5-qwen-model-directory-owner-v1" or value.get("nonce") != nonce or
            not re.fullmatch(r"[0-9a-f]{64}", value.get("original_receipt_sha256", ""))):
        raise ValueError("The exact original-receipt owner marker is required")
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); phase = "initial_admission"
    parent_restored = False
    def boundary():
        if time.monotonic() - started > 180:
            raise TimeoutError("Directory preparation deadline expired at a completed boundary")
        guard()
    def run_control(mode):
        nonlocal parent_restored
        boundary()
        exclusive_json(out / (mode + ".intent.private.json"), dict(mode=mode,
            artifact=manifest["artifact"], automatic_retries=0, title_launches=0, GPU_calls=0))
        log = control(mode, out / ("control-" + mode))
        with (out / (mode + ".private.log")).open("xb") as stream: stream.write(log)
        controller_result(log, mode, len(raw))
        if mode == "finalize": parent_restored = True
        boundary()
    try:
        boundary(); connection.absent(REMOTE_ROOT)
        exclusive_json(out / "intent.private.json", dict(remote_root=REMOTE_ROOT,
            manifest=manifest, maximum_marker_bytes=4096, timeout_seconds=180,
            automatic_retries=0, title_launches=0, GPU_calls=0))
        phase = "parent_prepare"; run_control("prepare")
        phase = "mkdir"; boundary(); connection.absent(REMOTE_ROOT)
        exclusive_json(out / "mkdir.intent.private.json", dict(remote_root=REMOTE_ROOT, automatic_retries=0))
        with connection.ftp() as ftp:
            if ftp.mkd(REMOTE_ROOT) != REMOTE_ROOT:
                raise ValueError("The new directory result does not match its exact path")
            if connection.directory_metadata(ftp):
                raise ValueError("The newly created model directory is not empty")
        exclusive_json(out / "mkdir.complete.private.json", dict(new_directory_created=True))
        phase = "marker_upload"; boundary(); connection.absent(REMOTE_ROOT + "/" + MARKER)
        exclusive_json(out / "marker.intent.private.json", dict(marker=marker, automatic_retries=0))
        with connection.ftp() as ftp:
            response = ftp.storbinary("STOR " + REMOTE_ROOT + "/" + MARKER, io.BytesIO(raw), 4096)
            if not response.startswith("226 ") or ftp.size(REMOTE_ROOT + "/" + MARKER) != len(raw):
                raise ValueError("The bounded marker upload lacks positive completion and size")
        if connection.model_get(REMOTE_ROOT + "/" + MARKER, 4096) != raw:
            raise ValueError("The complete new marker readback differs")
        exclusive_json(out / "marker.complete.private.json", dict(full_readback_verified=True, marker=marker))
        phase = "parent_finalize"; run_control("finalize")
        phase = "final_readback"; boundary()
        if connection.model_get(REMOTE_ROOT + "/" + MARKER, 4096) != raw:
            raise ValueError("The finalized model marker changed")
        with connection.ftp() as ftp:
            if connection.directory_metadata(ftp) != [dict(name=MARKER, mode="-rw-r--r--")]:
                raise ValueError("The finalized model directory must contain only its exact readable marker")
        boundary()
        proof = dict(schema="ps5-qwen-model-directory-preparation-v1", remote_root=REMOTE_ROOT,
            directory_created=True, directory_uid=0, directory_mode="0755",
            parent_ownership_restored=True, symlinks_rejected=True,
            marker_full_readback_verified=True, owner_nonce=nonce, marker=marker,
            plan_sha256=manifest["plan_sha256"], title_launches=0, GPU_calls=0,
            automatic_retries=0, elapsed_seconds=time.monotonic() - started)
        exclusive_json(out / "complete.private.json", proof)
        return proof
    except BaseException as error:
        exclusive_json(out / "failure.private.json", dict(error_type=type(error).__name__,
            phase=phase, parent_ownership_restored=parent_restored, automatic_retries=0,
            unresolved_attempt_requires_review=True, remote_partials_retained=True,
            title_launches=0, GPU_calls=0))
        raise
