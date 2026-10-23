#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-writer transfer sequencing with retained uncertain outcomes.

The caller supplies admitted original metadata and fresh reservation/session/
directory guards. This engine does not grant those admissions or launch a title.
"""
import hashlib
import io
import json
from pathlib import Path
import secrets
import re
import stat
import time
from model_transport import (REMOTE_ROOT, atomic_progress, exclusive_json,
                             positive_FTP_completion, source_identity, upload_file_once, validate_file, writer_lease)
from storage_capacity import require_storage


def small_json(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("A regular recorded transfer metadata file is required")
    with path.open("rb") as stream: raw = stream.read((1 << 20) + 1)
    if not 0 < len(raw) <= 1 << 20: raise ValueError("Recorded transfer metadata exceeded its bound")
    return json.loads(raw)


def positive_rename_record(value, original, destination, out):
    if value.get("FTP_250") is True:
        return True
    if value.get("FTP_2xx_rename") is not True or value.get("remote_partial_absent") is not True:
        return False
    if positive_FTP_completion(value.get("FTP_rename_reply")):
        return True
    row = value.get("reviewed_publication")
    if not isinstance(row, dict): return False
    path = Path(row["path"])
    if path.is_symlink() or path.resolve().parent != Path(out).resolve(): return False
    if path.stat().st_size != row["bytes"] or path.stat().st_size > 1 << 20: return False
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["sha256"]: return False
    proof = json.loads(raw)
    required = dict(schema="ps5-qwen-reviewed-model-file-publication-v1", original=original,
        destination=destination, source_stream_SHA_verified=True, source_identity_stable=True,
        FTP_226=True, FTP_2xx_rename=True, exact_rename_reply_not_recorded=True,
        destination_size_verified=True, partial_absent=True, remote_regular_world_readable=True,
        uncertain_rename_repeated=False, title_launches=0, GPU_calls=0)
    return all(type(proof.get(k)) is type(v) and proof[k] == v for k, v in required.items())


def validate_plan(plan, receipt_bytes):
    if (plan.get("schema") != "ps5-qwen-model-transfer-plan-v1" or plan.get("remote_root") != REMOTE_ROOT or
            plan.get("maximum_upload_connections") != 1 or plan.get("console_access") is not False or
            plan.get("remote_payload_SHA_verified") is not False or plan.get("input_hashes_stable") is not True):
        raise ValueError("An admitted offline original-model transfer plan is required")
    if not isinstance(plan.get("nonce"), str) or not re.fullmatch(r"[0-9a-f]{32}", plan["nonce"]):
        raise ValueError("The exact admitted transfer nonce is required")
    if type(plan.get("file_timeout_seconds")) is not int or not 60 <= plan["file_timeout_seconds"] <= 43200:
        raise ValueError("A bounded per-file transfer deadline is required")
    if not isinstance(receipt_bytes, bytes) or not 0 < len(receipt_bytes) <= 1 << 20:
        raise ValueError("The complete bounded original receipt is required")
    receipt = json.loads(receipt_bytes)
    if (receipt.get("schema") != "ps5-qwen-bf16-conversion-v2" or "test_fixture_only" in receipt or
            receipt.get("original_shards_verified") is not True or receipt.get("outtype") != "bf16"):
        raise ValueError("A complete original BF16 receipt is required")
    rows = plan.get("files")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise ValueError("The bounded complete original file set is required")
    originals = [row["original"] for row in rows]
    names = [validate_file(row) for row in originals]
    total = sum(row["bytes"] for row in originals)
    if (len(set(names)) != len(names) or receipt.get("files") != originals or
            not 359235922432 <= total <= 512 << 30 or plan.get("total_bytes") != total):
        raise ValueError("Transfer file identities differ from the complete original receipt")
    native = plan.get("native_receipt_gate", {})
    if native.get("native_receipt_gate_passed") is not True or native.get("mapped_file_bytes") != total:
        raise ValueError("The actual native receipt gate must have passed")
    if hashlib.sha256(receipt_bytes).hexdigest() != plan["original_receipt"]["sha256"]:
        raise ValueError("Original receipt bytes differ from their admitted identity")
    directory = Path(plan["source_directory"]).resolve()
    for row in rows:
        path = Path(row["source"])
        if path.is_symlink() or path.resolve() != directory / row["original"]["path"]:
            raise ValueError("An admitted regular original source path is required")
        if path.stat().st_size != row["original"]["bytes"] or tuple(row["source_identity"]) != source_identity(path.stat()):
            raise ValueError("Original file identity changed after planning")
    return total


def publish_receipt_once(connection, receipt_bytes, out, nonce, guard):
    out = Path(out); intent = out / "receipt-publication.intent.private.json"
    complete = out / "receipt-publication.complete.private.json"
    if intent.exists() or complete.exists(): raise ValueError("Receipt publication already has an attempt")
    target = REMOTE_ROOT + "/model-receipt.json"; partial = target + ".partial-" + nonce
    guard(); connection.absent(target); connection.absent(partial)
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    exclusive_json(intent, dict(target=target, partial=partial, bytes=len(receipt_bytes), sha256=digest,
        automatic_retries=0, native_payload_SHA_verified=False, GPU_calls=0))
    try:
        with connection.ftp() as ftp:
            guard()
            response = ftp.storbinary("STOR " + partial, io.BytesIO(receipt_bytes), blocksize=1 << 20)
            if not response.startswith("226 "): raise ValueError("Positive receipt transfer completion is required")
            if connection.model_get(partial, 1 << 20) != receipt_bytes:
                raise ValueError("Original receipt full readback differs")
            guard()
            listing = connection.directory_metadata(ftp)
            matches = [row for row in listing if row["name"] == partial.rsplit("/", 1)[1]]
            if len(matches) != 1 or len(matches[0]["mode"]) != 10 or matches[0]["mode"][0] != "-" or matches[0]["mode"][7] != "r":
                raise ValueError("The original receipt must be a native-readable regular file")
            guard(); connection.absent(target)
            response = ftp.rename(partial, target)
            exclusive_json(out / "receipt-rename-response.private.json", dict(response=response))
            if not positive_FTP_completion(response): raise ValueError("Positive receipt rename completion is required")
            connection.absent(partial)
            if connection.model_get(target, 1 << 20) != receipt_bytes:
                raise ValueError("Published original receipt full readback differs")
            guard()
        value = dict(original_receipt_SHA_verified=True, sha256=digest, bytes=len(receipt_bytes),
            native_payload_SHA_verified=False, automatic_retries=0, GPU_calls=0)
        guard(); exclusive_json(complete, value)
        return value
    except BaseException as error:
        exclusive_json(out / "receipt-publication.failure.private.json", dict(error_type=type(error).__name__,
            remote_state="retained_for_review", automatic_retries=0, delete_calls=0, GPU_calls=0))
        raise


def run_batch(plan, receipt_bytes, connection, out, lease, *, guard, resume=False,
              timeout_seconds=86400, now=time.monotonic, file_uploader=upload_file_once):
    total = validate_plan(plan, receipt_bytes)
    if type(timeout_seconds) is not int or not 3600 <= timeout_seconds <= 172800:
        raise ValueError("An explicit bounded host transfer deadline is required")
    out = Path(out)
    if resume:
        if not out.is_dir(): raise ValueError("A positively recorded existing batch is required for resume")
    else: out.mkdir(parents=True, exist_ok=False)
    plan_sha = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    started = now()
    started_wall_ms = time.time_ns() // 1000000
    with writer_lease(lease):
        identity = dict(schema="ps5-qwen-model-transfer-batch-v1", plan_identity_sha256=plan_sha,
            nonce=plan["nonce"], total_bytes=total, original_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
            started_monotonic=started, started_wall_epoch_ms=started_wall_ms,
            timeout_seconds=timeout_seconds, maximum_upload_connections=1,
            native_payload_SHA_verified=False, GPU_calls=0)
        attempt = out / "batch.intent.private.json"
        if resume:
            prior = small_json(attempt)
            for key in identity:
                if key not in {"started_monotonic", "started_wall_epoch_ms"} and prior[key] != identity[key]:
                    raise ValueError("Batch resume differs from its original identity or deadline")
            started = prior["started_monotonic"]
            started_wall_ms = prior["started_wall_epoch_ms"]
            if now() < started: raise ValueError("The host monotonic clock changed across resume")
        else: exclusive_json(attempt, identity)
        deadline = started + timeout_seconds
        records = out / "files"; records.mkdir(exist_ok=True)
        confirmed = 0; completed_files = []; progress_path = out / "progress.private.json"
        last_progress = [started - 5]
        def checked_guard():
            observed = now()
            wall_elapsed = (time.time_ns() // 1000000 - started_wall_ms) / 1000
            if observed >= deadline or wall_elapsed >= timeout_seconds:
                raise TimeoutError("The whole model-transfer deadline expired")
            if observed < started or abs(wall_elapsed - (observed - started)) > 2:
                raise ValueError("Host clock continuity changed across the transfer batch")
            guard()
        def progress(index, count, force=False, phase="uploading"):
            observed = now()
            if not force and observed - last_progress[0] < 5: return
            last_progress[0] = observed
            elapsed = max(observed - started, 0)
            atomic_progress(progress_path, dict(schema="ps5-qwen-model-transfer-progress-v1", phase=phase,
                file_index=index, files_total=len(plan["files"]), file_sent_bytes=count,
                positively_completed_bytes=confirmed, total_bytes=total, elapsed_seconds=elapsed,
                overall_sent_or_completed_bytes=min(total, confirmed + count if phase == "uploading" else confirmed),
                native_payload_SHA_verified=False, GPU_calls=0))
        try:
            checked_guard()
            for row in plan["files"]:
                name = row["original"]["path"]
                if ((records / (name + ".failure.private.json")).exists() or
                        (records / (name + ".intent.private.json")).exists() and
                        not (records / (name + ".complete.private.json")).exists()):
                    raise ValueError("A file has an uncertain prior attempt; no automatic resume")
            for index, row in enumerate(plan["files"], 1):
                name = row["original"]["path"]
                intent = records / (name + ".intent.private.json")
                complete = records / (name + ".complete.private.json")
                failed = records / (name + ".failure.private.json")
                checked_guard()
                if failed.exists() or intent.exists() and not complete.exists():
                    raise ValueError("A file has an uncertain prior attempt; no automatic resume")
                was_recorded = complete.exists()
                if was_recorded:
                    value = small_json(complete)
                    if (not resume or value["original"] != row["original"] or
                            value["destination"] != REMOTE_ROOT + "/" + name or
                            any(value.get(field) is not True for field in ("source_stream_SHA_verified",
                                "source_identity_stable", "FTP_226", "remote_size_verified", "world_readable")) or
                            not positive_rename_record(value, row["original"], REMOTE_ROOT + "/" + name, out)):
                        raise ValueError("A positively recorded original file is required for resume")
                    with connection.ftp() as ftp:
                        ftp.voidcmd("TYPE I")
                        if ftp.size(value["destination"]) != row["original"]["bytes"]:
                            raise ValueError("Previously completed remote file size changed")
                        matches = [entry for entry in connection.directory_metadata(ftp) if entry["name"] == name]
                        if len(matches) != 1 or len(matches[0]["mode"]) != 10 or matches[0]["mode"][0] != "-" or matches[0]["mode"][7] != "r":
                            raise ValueError("Previously completed remote file readability changed")
                else:
                    capacity = connection.capacity(out / ("capacity-" + str(index) + "-" + secrets.token_hex(8)))
                    if not capacity["capture_completion_proven"]:
                        raise ValueError("Fresh completed filesystem capacity is required")
                    age = time.time_ns() // 1000000 - capacity["host_after_epoch_ms"]
                    if not 0 <= age <= 30000: raise ValueError("Fresh filesystem capacity is required")
                    require_storage(capacity, total - confirmed, len(receipt_bytes))
                    remaining_seconds = int(deadline - now())
                    if remaining_seconds < 60: raise TimeoutError("Insufficient remaining upload deadline")
                    with connection.ftp() as ftp:
                        value = file_uploader(ftp, plan["source_directory"], row["original"], records, plan["nonce"],
                            guard=checked_guard, absent=connection.absent,
                            timeout_seconds=min(plan["file_timeout_seconds"], remaining_seconds),
                            progress=lambda count: progress(index, count))
                completed_files.append(value); confirmed += row["original"]["bytes"]
                progress(index, row["original"]["bytes"], force=True,
                    phase="previously_recorded_file_size_checked" if was_recorded else "file_transfer_recorded")
            if confirmed != total: raise ValueError("The complete original model byte count differs")
            checked_guard()
            publication = publish_receipt_once(connection, receipt_bytes, out, plan["nonce"], checked_guard)
            checked_guard()
            value = dict(schema="ps5-qwen-model-transfer-complete-v1", state="awaiting_native_SHA_admission",
                complete_original_payload_bytes=confirmed, positively_completed_files=len(completed_files),
                original_receipt_publication=publication, native_payload_SHA_verified=False,
                model_loaded=False, full_model_inference=False, automatic_retries=0, GPU_calls=0)
            exclusive_json(out / "complete.private.json", value)
            atomic_progress(progress_path, value)
            return value
        except BaseException as error:
            failure = dict(phase="failed_retained_for_review", error_type=type(error).__name__,
                positively_completed_bytes=confirmed, total_bytes=total,
                native_payload_SHA_verified=False, automatic_retries=0, GPU_calls=0)
            exclusive_json(out / ("batch-failure-" + secrets.token_hex(8) + ".private.json"), failure)
            atomic_progress(progress_path, failure)
            raise
