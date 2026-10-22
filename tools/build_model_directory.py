#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build, but never execute, a CPU-only controller for one original-model plan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from model_transport import REMOTE_ROOT, exclusive_json
from model_transfer_batch import validate_plan
from plan_model_transfer import preparation_gate
from transfer_model import bounded_json, record_bytes, sha

ROOT = Path(__file__).resolve().parents[1]
QUALIFIED_SOURCE = "322795370f188ea60f861e7b1da2ab27899899e89ac25a22bf2d8f9132f78c85"
QUALIFIED_COMMAND_TEMPLATE = "72218a88aaf0acbba705193dc1abfa775420260cf778d7d769b8e3d41aa9afef"


def command_template(commands, reference, workspace):
    def normalize(value):
        if "${" in value: raise ValueError("Literal template placeholders are not build arguments")
        return value.replace("\\", "/").replace(reference.as_posix(), "${BUILD}").replace(workspace.as_posix(), "${WORKSPACE}")
    normalized = [[normalize(value) for value in command] for command in commands]
    return hashlib.sha256(json.dumps(normalized, separators=(",", ":")).encode()).hexdigest()


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "plan", "qualified_reference", "out"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    a = p.parse_args(); cache = a.cache.resolve(); workspace = a.workspace.resolve()
    plan = bounded_json(a.plan)
    receipt = record_bytes(plan["receipt_copy"], cache)
    validate_plan(plan, receipt)
    preparation_gate(json.loads(receipt), bounded_json(Path(plan["source_directory"]) / "conversion-status.private.json"))
    reference_path = a.qualified_reference.resolve(); reference = reference_path.parent
    if not reference_path.is_relative_to(cache): raise ValueError("The task's qualified controller reference is required")
    old = bounded_json(reference_path)
    if sha(old["source_path"]) != QUALIFIED_SOURCE or sha(old["elf"]) != old["sha256"]:
        raise ValueError("The qualified ownership controller changed")
    if command_template(old["commands"], reference, workspace) != QUALIFIED_COMMAND_TEMPLATE:
        raise ValueError("The exact qualified CPU build recipe is required")
    if any(not Path(command[0]).resolve().is_relative_to(workspace / "toolchain") for command in old["commands"]):
        raise ValueError("Only the known local compiler/linker may run")
    owner_nonce = old["nonce"]
    if not re.fullmatch(r"[0-9a-f]{32}", owner_nonce): raise ValueError("The existing local directory-owner nonce is required")
    header_path = reference / "display_control_context.h"
    if sha(header_path) != old["header_sha256"] or ('#define OWNER_NONCE ' + json.dumps(owner_nonce)) not in header_path.read_text():
        raise ValueError("The qualified local owner header differs")
    out = a.out.resolve()
    if not out.is_relative_to(cache) or out.is_relative_to(Path(plan["source_directory"]).resolve()):
        raise ValueError("A separate fresh data-disk build directory is required")
    out.mkdir(parents=True, exist_ok=False); (out / "tmp").mkdir()
    marker = dict(schema="ps5-qwen-model-directory-owner-v1", nonce=plan["nonce"],
        original_receipt_sha256=plan["original_receipt"]["sha256"])
    marker_bytes = (json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(marker_bytes) > 4096: raise ValueError("The exact bounded owner marker is required")
    marker_path = out / "owner-marker.private.json"; marker_path.write_bytes(marker_bytes)
    prefix = "/data/ai/moss-qwen-model-directory-" + secrets.token_hex(16)
    header = out / "model_directory_context.h"
    header.write_text('#define OWNER_NONCE ' + json.dumps(owner_nonce) + '\n#define MODEL_MARKER ' +
        json.dumps(marker_bytes.decode("ascii")) + '\n#define LOG_PREFIX ' + json.dumps(prefix) + '\n', newline="\n")
    source = ROOT / "native/qwen_flash_next/model_directory_control.c"
    if '#define APP "' + REMOTE_ROOT.rsplit("/", 1)[0] + '"' not in source.read_text():
        raise ValueError("The controller must stay in this application's model namespace")
    commands = [[value.replace(str(reference), str(out)) for value in command] for command in old["commands"]]
    commands[0][commands[0].index("-c") + 1] = str(source)
    commands[0] += ["-Wall", "-Wextra", "-Werror"]
    artifact = out / "model-directory-control.elf"
    commands[1][commands[1].index("-o") + 1] = str(artifact)
    object_path = Path(commands[0][commands[0].index("-o") + 1])
    original_object = old["commands"][0][old["commands"][0].index("-o") + 1]
    inputs = [source, header, reference_path, Path(old["source_path"]), header_path,
              Path(old["elf"]), Path(original_object), *[Path(command[0]) for command in commands]]
    inputs += [Path(value) for value in commands[1][1:] if value.endswith((".o", ".a", ".so")) and Path(value).exists()]
    if "-T" in commands[1]: inputs.append(Path(commands[1][commands[1].index("-T") + 1]))
    before = [record(path) for path in inputs]
    env = dict(os.environ, TMP=str(out / "tmp"), TEMP=str(out / "tmp"))
    object_before_link = None
    for index, command in enumerate(commands):
        if index == 1 and sha(object_path) != object_before_link:
            raise ValueError("The CPU controller object changed before link")
        result = subprocess.run(command, capture_output=True, env=env, timeout=120)
        (out / ("build-" + str(index) + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError("CPU directory controller compilation/link failed")
        if index == 0: object_before_link = sha(object_path)
    nm = Path(commands[0][0]).with_name("llvm-nm.exe")
    imported = subprocess.check_output([str(nm), "--undefined-only", str(object_path)], text=True, timeout=30)
    prior = subprocess.check_output([str(nm), "--undefined-only", original_object], text=True, timeout=30)
    names = lambda raw: {line.split()[-1] for line in raw.splitlines() if line.split()}
    if names(imported) - names(prior) or any(value in imported for value in
            ("sceAgc", "sceSystemService", "ptrace", "mmap", "mprotect", "kernel_set_", "kernel_copy")):
        raise ValueError("The metadata controller added an unqualified operation")
    if before != [record(path) for path in inputs]: raise ValueError("A CPU controller build input changed")
    if sha(object_path) != object_before_link: raise ValueError("The CPU controller object changed during link")
    manifest = dict(schema="ps5-qwen-model-directory-controller-v1", source=record(source),
        artifact=record(artifact), object=record(object_path), header=record(header), marker=record(marker_path),
        source_inputs=before, qualified_source_sha256=QUALIFIED_SOURCE,
        qualified_command_template_sha256=QUALIFIED_COMMAND_TEMPLATE,
        plan_sha256=sha(a.plan), owner_nonce=plan["nonce"], remote_root=REMOTE_ROOT,
        prefix=prefix, allowed_actions=["prepare", "finalize", "verify"], commands=commands,
        input_hashes_stable=True, imports_subset_of_qualified_controller=True,
        console_access=False, title_launches=0, GPU_calls=0)
    exclusive_json(out / "manifest.private.json", manifest)
    print(json.dumps(dict(CPU_model_directory_controller="built", console_access=False,
        title_launches=0, GPU_calls=0)))


if __name__ == "__main__": main()
