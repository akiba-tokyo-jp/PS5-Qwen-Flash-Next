#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect the native owner, or close it once using the ordinary OS API.

Host/address, captures and helper binaries are supplied locally. No force-kill,
GPU reset, title installation, credential output or execution retry is used.
"""
import argparse
import ftplib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("inspect", "close"))
    p.add_argument("--host", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--owner-receipt", type=Path)
    a = p.parse_args()
    policy = json.loads((ROOT / "config/development.json").read_text())
    if not policy["console_operations_enabled"]:
        p.error("Console operations are disabled for this application integration phase")
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    workspace = a.workspace.resolve()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(path, limit=1 << 20, timeout=6):
        with opener.open("http://" + a.host + path, timeout=timeout) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Bounded console response exceeded")
        return data

    before = json.loads(get(":8084/processes_list"))["processes"]
    owners = [row for row in before if row["name"] == "eboot.bin"]
    (out / "before.private.json").write_text(json.dumps(before, indent=2))
    if not owners:
        receipt = {"state": "native_already_absent", "native_owners": 0, "close_calls": 0,
                   "signals": 0, "GPU_calls": 0, "automatic_retries": 0}
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
        return
    if len(owners) != 1:
        raise ValueError("Exactly one native owner is required")
    pid = owners[0]["pid"]
    prior = None
    if a.command == "close":
        if a.owner_receipt is None:
            p.error("close requires a fresh --owner-receipt")
        prior = json.loads(a.owner_receipt.read_text())
        if prior["pid"] != pid or prior.get("state") != "owner_inspected":
            raise ValueError("Current process differs from the inspected owner")
    llvm = workspace / "toolchain/fast/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = workspace / "toolchain/ps5-payload-sdk"
    crt = workspace / "build/gpu_probe/credential-preserving-crt/crt1-credential-preserving.o"
    patch = crt.with_name("patch-syscall-only.o")
    if digest(crt) != "8e81fa5b9b8afef702dfd0f7000c908692653e3f5948d69069b5b7c63350e415" or digest(patch) != "096a53aae0289fd7395d8795804cb4de1af1b3407ffc1d58b642ffa7685fc6f1":
        raise ValueError("Expected credential-preserving helper CRT differs")
    overlay = workspace / "build/gpu_probe/sd-pid807-signal-state/overlay"
    obj, elf = out / "owner.o", out / "console-owner.elf"
    commands = [
        [llvm / "clang.exe", "--no-default-config", "--target=x86_64-sie-ps5", "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-O2", "-Wall", "-Wextra", "-Werror", "-std=gnu11", "-D_BSD_SOURCE", "-isystem", sdk / "target/include", "-I", overlay, "-c", ROOT / "native/qwen_flash_next/console_owner.c", "-o", obj],
        [llvm / "ld.lld.exe", "-m", "elf_x86_64", "-pie", "-T", sdk / "ldscripts/elf_x86_64.x", "--eh-frame-hdr", "-z", "max-page-size=0x4000", "--hash-style=gnu", "-L", sdk / "target/lib", "-o", elf, obj, crt, patch, "--as-needed", "-lc", "-lkernel_web", "-lSceLibcInternal", "-lSceSystemService"]]
    for command in commands:
        result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
    imports = subprocess.check_output([str(llvm / "llvm-nm.exe"), "--undefined-only", str(obj)], text=True)
    if re.search(r"\b(kill|ptrace|sceAgc\w*|sceKernelRelease\w*|sceSystemServiceLaunchApp)\b", imports):
        raise ValueError("Unexpected process/GPU operation in helper")
    (out / "imports.private.txt").write_text(imports)
    nonce = uuid.uuid4().hex
    remote = "/data/ai/qwen-owner-" + nonce + ".elf"
    log = "/data/ai/qwen-owner-" + nonce + ".log"
    for path in (remote, log):
        try:
            get(":8080/fs" + path, 1)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                continue
            raise
        raise ValueError("New remote helper path already exists")
    with ftplib.FTP() as ftp:
        ftp.connect(a.host, 2121, timeout=15); ftp.login()
        with elf.open("rb") as stream:
            ftp.storbinary("STOR " + remote, stream, 262144)
    if get(":8080/fs" + remote, elf.stat().st_size) != elf.read_bytes():
        raise ValueError("Helper full readback mismatch")
    arguments = ["--inspect", str(pid), log] if prior is None else ["--close", str(pid), str(prior["start_sec"]), str(prior["start_usec"]), prior["title"], str(prior["app_id"]), log, log + ".once"]
    query = urllib.parse.urlencode({"elf": remote, "cwd": "/data/ai", "args": remote.rsplit("/", 1)[1] + " " + " ".join(arguments), "pipe": "0"})
    (out / "execution.once.private.json").write_text(json.dumps({"command": a.command, "pid": pid, "helper_sha256": digest(elf), "remote_log": log, "automatic_retries": 0}, indent=2))
    try:
        response = get(":8080/elfldr?" + query, 65536, 8)
        (out / "response.private.txt").write_bytes(response)
    except Exception as error:
        (out / "request-uncertain.private.txt").write_text(type(error).__name__)
    data = b""
    for _ in range(20):
        try:
            data = get(":8080/fs" + log)
            (out / "console.private.log").write_bytes(data)
            if b"\nEND " in data:
                break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        time.sleep(1)
    text = data.decode("utf-8", "replace")
    if "END success=1" not in text:
        raise RuntimeError("Helper did not confirm success; execution was not retried: " + text)
    m = re.search(r"OWNER pid=(\d+) start_sec=(\d+) start_usec=(\d+) app_id=(\d+) title=(PPSA\d{5})", text)
    if not m:
        raise RuntimeError("Missing exact native owner")
    receipt = dict(zip(("pid", "start_sec", "start_usec", "app_id"), map(int, m.groups()[:4])), title=m.group(5),
                   state="owner_inspected", signals=0, GPU_calls=0, automatic_retries=0)
    if a.command == "close":
        for _ in range(30):
            after = json.loads(get(":8084/processes_list"))["processes"]
            if not any(row["pid"] == pid or row["name"] == "eboot.bin" for row in after):
                break
            time.sleep(1)
        else:
            raise RuntimeError("OS accepted close but PID absence is unproved; no retry")
        (out / "after.private.json").write_text(json.dumps(after, indent=2))
        receipt.update(state="normally_closed_and_native_PID_absent", close_calls=1)
    (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
