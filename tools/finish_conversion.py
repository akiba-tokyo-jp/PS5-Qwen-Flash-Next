#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finish a completed writer's interrupted audit without rewriting its outputs.

Every payload is independently compared again. Old progress is evidence of an
interruption, never admission. This finite host job cannot access the console.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import os
from pathlib import Path
import time

from resume_conversion import (ORIGINAL_TOOLS, RESUME_TOOLS, LOCK, ROOT, read,
    record, tool_hashes, process_library, validate_checkpoint, read_only_leases)
from resume_provenance import validate_adapter
from resumable_gguf import identity
from convert_model import converter_sources, digest
from qwen_flash_next import writer_lease, json_write


def run(args):
    cache, out = args.cache.resolve(), args.out.resolve()
    source, attempt = args.source_attempt.resolve(), args.attempt.resolve()
    if (any(path.parent != cache or path.is_symlink() for path in (out, source, attempt)) or
            len({out, source, attempt, args.previous.resolve()}) != 4):
        raise ValueError("Distinct exact cache directories are required")
    if attempt.exists() or (out / "model-receipt.json").exists():
        raise ValueError("A new audit attempt and an unpublished model are required")
    psutil = process_library(cache)
    old_intent, old_state = read(source / "intent.private.json"), read(source / "status.private.json")
    waiter = cache / "model-data-waiter-003"
    waiter_intent, waiter_state = read(waiter / "intent.private.json"), read(waiter / "status.private.json")
    if (old_state["pid"] != old_intent["pid"] or old_state["phase"] != "verifying_original_PLE_payload" or
            old_state.get("console_access") is not False or
            waiter_state.get("console_access_started") is not False or
            any(psutil.pid_exists(pid) for pid in (old_intent["pid"], waiter_intent["pid"])) or
            (cache / "model-data-continuation-003").exists()):
        raise ValueError("The interrupted host-only processes must be positively absent before any new attempt")
    names = (*ORIGINAL_TOOLS, *RESUME_TOOLS)
    frozen = tool_hashes(names)
    if old_intent["frozen_sources"] != frozen:
        raise ValueError("The completed writer's sources changed")
    for row in waiter_intent["sources"] + [waiter_intent["context"], waiter_intent["reservation"]]:
        if record(row["path"]) != row:
            raise ValueError("The interrupted data waiter's frozen inputs changed")
    adapter = read(source / "resumed-copy-receipt.private.json")
    validate_adapter(adapter, {name: frozen[name] for name in ORIGINAL_TOOLS},
        {name: frozen[name] for name in RESUME_TOOLS})
    retention = read(adapter["retention_record"]["path"])
    rows = retention["retained"] + retention["written"]
    files = sorted(out.glob("*.gguf"))
    if (len(files) != 76 or {p.resolve() for p in files} != {Path(r["path"]).resolve() for r in rows} or
            any(Path(r["path"]).stat().st_size != r["bytes"] for r in rows)):
        raise ValueError("The exact complete writer outputs are required")
    attempt.mkdir()
    evidence = [source / name for name in ("intent.private.json", "status.private.json",
        "resumed-copy-receipt.private.json", "retention.private.json", "resume-writer-progress.private.json")]
    evidence += [waiter / "intent.private.json", waiter / "status.private.json", out / "conversion-status.private.json"]
    for index, path in enumerate(evidence):
        (attempt / (str(index) + "-prior-" + path.name)).write_bytes(path.read_bytes())
    original_evidence = [record(path) for path in evidence if path != out / "conversion-status.private.json"]
    started = time.monotonic()
    def status(phase, **fields):
        value = dict(schema="ps5-qwen-conversion-status-v1", phase=phase, pid=os.getpid(),
            updated_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
            console_access=False, learned_inference_performed=False, **fields)
        json_write(attempt / "status.private.json", value)
        json_write(out / "conversion-status.private.json", value)
        print(__import__("json").dumps(value), flush=True)
    own_source = record(Path(__file__))
    try:
        with writer_lease(cache / "model-preparation.lock.private"), writer_lease(cache / "model-download.lock.private"), ExitStack() as leases:
            checkpoint_value = validate_checkpoint(args, leases)
            read_only_leases(files, leases)
            identities = {p.name: identity(p) for p in files}
            json_write(attempt / "intent.private.json", dict(schema="ps5-qwen-audit-restart-intent-v1",
                pid=os.getpid(), created_epoch=psutil.Process().create_time(), frozen_sources=frozen,
                audit_source=own_source, prior_evidence=original_evidence, output_identities=identities,
                prior_processes_positively_absent=True, writer_repeated=False,
                complete_payload_audit_restarted=True, audit_timeout_seconds=86400,
                hashing_timeout_seconds=43200, automatic_retries=0, console_access=False,
                learned_inference_performed=False))
            status("planning_complete_payload_audit")
            from audit_conversion import audit_conversion, inputs
            _, _, _, manifest, _, sources = inputs(cache)
            audit = audit_conversion(cache, out, files, status, 86400)
            outputs = []
            deadline = time.monotonic() + 43200
            for index, path in enumerate(files):
                status("hashing_converted_files", verified=index, total=len(files))
                outputs.append(dict(path=path.name, bytes=path.stat().st_size, sha256=digest(path, deadline)))
                json_write(attempt / "completed-hashes.private.json", dict(files=outputs, complete=False))
            validate_checkpoint(args, None)
            if (identities != {p.name: identity(p) for p in files} or
                    frozen != tool_hashes(names) or record(Path(__file__)) != own_source or
                    original_evidence != [record(r["path"]) for r in original_evidence]):
                raise ValueError("A frozen audit input changed")
            if sources != converter_sources(cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip"),
                    cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])):
                raise ValueError("The pinned converter source changed")
            receipt = dict(schema="ps5-qwen-bf16-conversion-v2", original_revision=manifest["revision"],
                upstream_revision=LOCK["llama_cpp"]["revision"], outtype="bf16", original_shards_verified=True,
                files=outputs, converter_sources=sources, conversion_audit=audit, conversion_adapter=adapter,
                preparation_tool_sources={name: frozen[name] for name in ORIGINAL_TOOLS},
                resume_tool_sources={name: frozen[name] for name in RESUME_TOOLS},
                original_source_verification=checkpoint_value, audit_restart=record(attempt / "intent.private.json"),
                console_access=False, learned_inference_performed=False)
            json_write(out / "model-receipt.json", receipt)
            json_write(attempt / "completed-hashes.private.json", dict(files=outputs, complete=True))
            status("completed", verified=len(files), total=len(files), receipt="model-receipt.json")
    except BaseException as error:
        if (out / "model-receipt.json").exists():
            (out / "model-receipt.json").rename(attempt / "model-receipt.not-admitted.private.json")
        status("failed", error_type=type(error).__name__, receipt_published=False)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cache", "previous", "checkpoint", "out", "source-attempt", "attempt"):
        parser.add_argument("--" + name, required=True, type=Path)
    run(parser.parse_args())


if __name__ == "__main__": main()
