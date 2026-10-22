#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a private full-plan case after packaging and positive data transfer.

This performs offline input checks, emits the exact native admission scope and
preserves restoration inputs. It has no network client or console operations.
Fresh CPU/session/clock observations and ordinary launch remain separate gates.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from driver_inputs import sha
from qwen_flash_next import ROOT


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def bound(row):
    if record(row["path"]) != row: raise ValueError("A private input binding changed")
    return Path(row["path"])


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, indent=2) + "\n"); output.flush(); os.fsync(output.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "package", "data-completion", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(); cache, out = args.cache.resolve(), args.out.resolve()
    if out.parent != cache or out.exists(): raise ValueError("A fresh separate physical case in the data cache is required")
    package = read(args.package)
    if (package.get("integrity_verified") is not True or package.get("roundtrip_segments_verified") != 6 or
            package.get("real_module_import_audit", {}).get("missing") != []):
        raise ValueError("A packaged candidate with successful native imports and SELF roundtrip is required")
    candidate = bound(package["SELF"])
    complete = read(args.data_completion)
    if (complete.get("schema") != "ps5-qwen-model-data-continuation-complete-v1" or
            complete.get("native_SHA_verified") is not False or complete.get("model_loaded") is not False or
            complete.get("full_inference_qualified") is not False or complete.get("GPU_calls") != 0):
        raise ValueError("Complete data-only transfer evidence is required")
    transfer = read(bound(complete["transfer"]))
    plan_path = args.data_completion.parent / "plan/plan.private.json"; plan = read(plan_path)
    if (transfer.get("schema") != "ps5-qwen-model-transfer-complete-v1" or
            transfer.get("state") != "awaiting_native_SHA_admission" or
            transfer.get("positively_completed_files") != len(plan["files"]) or
            transfer.get("complete_original_payload_bytes") != plan["total_bytes"] or
            transfer.get("native_payload_SHA_verified") is not False or transfer.get("model_loaded") is not False):
        raise ValueError("Every original data file must have one positive completed transfer")
    receipt = bound(plan["original_receipt"])
    if transfer["original_receipt_publication"]["sha256"] != sha(receipt):
        raise ValueError("The published full-model receipt differs")
    reservation = args.workspace / "driver-work/PS5-Vulkan-Inference/.local/gpu-development-20261021/active-context.private.json"
    context_path = Path(read(reservation)["context"]); context = read(context_path)
    if (context.get("original_restored") is not True or context.get("original_numerical_re_admission") != "passed" or
            context.get("complete_original_SELF_readback_after_shutdown") is not True or
            context.get("native_running") is not False or context.get("gateway_running") is not False or
            context.get("model_loaded") is not False or context.get("original_moe_admitted") is not True):
        raise ValueError("The completed original restoration and indexed-MoE context is required")
    original = bound(context["original_SELF"])
    if sha(original) != "2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d":
        raise ValueError("The exact preserved original SELF differs")
    policy = read(ROOT / "config/development.json")
    if any(policy[key] is not False for key in ("console_operations_enabled", "deployment_enabled", "console_validation_enabled", "validation_deployment_enabled")) or policy["allowed_modes"] != []:
        raise ValueError("Committed execution/deployment controls must remain disabled")
    out.mkdir(); (out / "private-policy").mkdir()
    binding = dict(candidate_SELF_sha256=sha(candidate), candidate_SELF_bytes=candidate.stat().st_size,
        model_receipt_sha256=sha(receipt), model_receipt_bytes=receipt.stat().st_size, run_id=secrets.token_hex(16))
    binding_path = out / "policy-binding.private.json"; write(binding_path, binding)
    host = args.workspace / "toolchain/msys-clang64/clang64/bin"
    upstream = cache / "upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569"
    executable = out / "native-policy.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
        str(ROOT / "tools/first_generation_policy.cpp"), "-o", str(executable)]
    environment = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    result = subprocess.run(command, env=environment, capture_output=True, timeout=120)
    (out / "policy-compile.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError("The actual native admission-scope emitter failed to compile")
    result = subprocess.run([str(executable), str(binding_path)], env=environment, capture_output=True, timeout=30)
    (out / "policy-run.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise ValueError("The actual native gate rejected the case binding")
    policy.update(phase="bounded-full-model-plan", console_operations_enabled=True, console_validation_enabled=True,
        validation_deployment_enabled=True, deployment_enabled=False, allowed_modes=["first-generation-validation"],
        native_first_generation_validation=json.loads(result.stdout))
    write(out / "private-policy/development.json", policy)
    write(out / "preflight-complete.private.json", dict(state="original_normally_closed_source_SELF_preserved",
        SELF=record(original), prior_completed_context=record(context_path), console_connections=0, GPU_calls=0))
    write(out / "case-inputs.private.json", dict(schema="ps5-qwen-first-case-inputs-v1", binding=binding,
        package=record(args.package), candidate=record(candidate), original=record(original),
        model_receipt=record(receipt), transfer=record(complete["transfer"]["path"]), data_completion=record(args.data_completion),
        data_plan=record(plan_path), prior_context=record(context_path), reservation=record(reservation),
        native_policy_emitter=record(executable), policy_command=command,
        native_policy_sources=[record(ROOT / "tools/first_generation_policy.cpp"), record(ROOT / "native/app/first_generation_policy.h")],
        fresh_session_required_before_mutation=True, console_access=False, learned_host_inference=False))
    shutil.copyfile(args.package, out / "candidate-package.private.json")
    print(json.dumps(dict(private_case_prepared=True, native_policy_gate_passed=True, console_connections=0, GPU_calls=0)))


if __name__ == "__main__": main()
