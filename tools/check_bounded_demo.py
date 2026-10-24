#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the finite API with synthetic events on host loopback, never a model."""
import argparse
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reuse-executable", type=Path,
        help="Reuse this session's unchanged host-only transport fixture after a network-sandbox refusal")
    parser.add_argument("--reuse-sha256")
    a = parser.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    source = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    files = [ROOT / "native/app/bounded_demo.cpp", ROOT / "tests/bounded_demo.cpp",
        source / "vendor/cpp-httplib/httplib.cpp"]
    dependencies = [*files, *[ROOT / "native/app" / name for name in (
        "bounded_demo.h", "http_app.h", "first_generation.h", "monitor.h", "monitor_clock.h", "session.h")],
        source / "vendor/cpp-httplib/httplib.h", source / "vendor/nlohmann/json.hpp"]
    source_digests = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}
    executable = a.out / "bounded-demo-transport.exe"
    command = [host / "clang++.exe", "-std=c++17", "-O0", "-I", ROOT / "native/app",
        "-I", source / "vendor", "-I", source / "vendor/cpp-httplib", *files, "-lws2_32", "-o", executable]
    reused = None
    if a.reuse_executable:
        original = a.reuse_executable.resolve()
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        if digest != a.reuse_sha256 or any(p.stat().st_mtime_ns > original.stat().st_mtime_ns for p in files):
            raise ValueError("The retained host fixture differs or its sources were subsequently changed")
        executable = original
        reused = dict(path=str(original), sha256=digest, scope="host transport fixture only")
    else:
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, timeout=240)
        (a.out / "compile.private.log").write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode("utf-8", "replace")[-5000:])
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0)); port = candidate.getsockname()[1]
    stdout = (a.out / "run.stdout.private.log").open("xb")
    stderr = (a.out / "run.stderr.private.log").open("xb")
    process = subprocess.Popen([str(executable), str(port), str(ROOT / "web")], env=env, stdout=stdout, stderr=stderr)
    def request(method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request(method, path, json.dumps(body) if body is not None else None,
                {"Content-Type": "application/json"} if body is not None else {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()
    try:
        started = time.monotonic()
        while True:
            if process.poll() is not None: raise RuntimeError("Synthetic transport exited before readiness")
            try:
                status, payload = request("GET", "/api/status")
                if status == 200: break
            except PermissionError:
                raise RuntimeError("The host loopback test was refused by the network sandbox; reuse the built fixture with network permission")
            except OSError:
                pass
            if time.monotonic() - started > 15: raise RuntimeError("Synthetic listener readiness deadline")
            time.sleep(0.05)
        valid = dict(id="a"*32 + "-1", messages=[dict(role="user", content="Count from 1 to 8, separated by commas. Reply with only the sequence.")],
            context_tokens=256, max_output_tokens=32, enable_thinking=False)
        mutations = [dict(max_output_tokens=33), dict(context_tokens=2048), dict(enable_thinking=True),
            dict(id="a"*32 + "-2"), dict(extra=True), dict(messages=[dict(role="user", content="Different prompt")]),
            dict(context_tokens=256.0), dict(max_output_tokens=True)]
        for changes in mutations:
            body = dict(copy.deepcopy(valid), **changes)
            status, _ = request("POST", "/api/generate", body)
            if status != 400: raise AssertionError("A request outside the fixed scope was admitted")
        if request("POST", "/api/validation/finish", dict(run_id="a"*32))[0] != 409:
            raise AssertionError("Incomplete execution was accepted as finished")
        for ordinal in (1, 2):
            body = dict(valid, id="a"*32 + "-" + str(ordinal))
            status, response = request("POST", "/api/generate", body)
            events = [json.loads(line[6:]) for line in response.decode().splitlines() if line.startswith("data: ")]
            if status != 200 or [e["type"] for e in events] != ["token", "token", "finished"]:
                raise AssertionError("Token streaming or positive terminal response differs")
            if events[-1]["state"] != "completed": raise AssertionError("Missing completed stream")
        if request("POST", "/api/generate", valid)[0] != 409:
            raise AssertionError("A third request was admitted")
        for path in ("/", "/app.js", "/style.css"):
            if request("GET", path)[0] != 200: raise AssertionError("A fixed passive asset is unavailable")
        time.sleep(1.1)
        status, payload = request("GET", "/api/status")
        observed = json.loads(payload)
        if status != 200 or observed["validation"]["completed_requests"] != 2:
            raise AssertionError("Passive status differs from the completed requests")
        status, payload = request("POST", "/api/validation/finish", dict(run_id="a"*32))
        if status != 200 or json.loads(payload) != dict(state="accepted"):
            raise AssertionError("Positive finish acknowledgement was not delivered")
        if process.wait(timeout=15) != 0: raise RuntimeError("Synthetic transport failed during completed shutdown")
        for failure_mode in ["--fail-request", "--fail-before-request"]:
            stdout.close(); stderr.close()
            with socket.socket() as candidate:
                candidate.bind(("127.0.0.1", 0)); port = candidate.getsockname()[1]
            stem = failure_mode[2:]
            stdout = (a.out / (stem + ".stdout.private.log")).open("xb")
            stderr = (a.out / (stem + ".stderr.private.log")).open("xb")
            process = subprocess.Popen([str(executable), str(port), str(ROOT / "web"), failure_mode],
                env=env, stdout=stdout, stderr=stderr)
            began = time.monotonic()
            while True:
                try:
                    if request("GET", "/api/status")[0] == 200: break
                except OSError:
                    pass
                if process.poll() is not None or time.monotonic() - began > 15:
                    raise RuntimeError("Synthetic failure listener did not start")
                time.sleep(.05)
            status, payload = request("POST", "/api/generate", valid)
            events = [json.loads(line[6:]) for line in payload.splitlines() if line.startswith(b"data: ")]
            if status != 200 or len(events) != (2 if failure_mode == "--fail-request" else 1):
                raise AssertionError("Failed owner did not deliver its bounded terminal event")
            terminal = events[-1]
            if (terminal.get("id") != valid["id"] or terminal.get("type") != "finished" or
                terminal.get("state") != "failed" or not terminal.get("error") or
                terminal.get("quarantined") is not True or terminal.get("resource_graph_retained") is not True or
                terminal.get("GPU_completion_qualified") is not False):
                raise AssertionError("Failed owner claimed success or lost resource-retention evidence")
            if process.wait(timeout=15) != 1:
                raise RuntimeError("Failure shutdown did not terminate its synthetic host worker/listener")
        receipt = dict(schema="ps5-qwen-bounded-demo-host-check-v1", state="passed", malformed_requests_rejected=len(mutations),
            streamed_requests=2, extra_request_rejected=True, premature_finish_rejected=True,
            assets_and_status_passed=True, finish_delivered_and_listener_stopped=True,
            owner_failure_does_not_hang_listener_shutdown=True,
            failed_terminal_events_received=2, failure_before_first_token_is_explicit=True,
            console_access=False, learned_host_inference=False,
            reused_host_fixture=reused,
            source_sha256=source_digests)
        if source_digests != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}:
            raise RuntimeError("A transport-check input changed during compilation/execution")
        (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({k: v for k, v in receipt.items() if k != "source_sha256"}))
    finally:
        # This is a disposable host transport fixture with no backend resources.
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
        stdout.close(); stderr.close()


if __name__ == "__main__":
    main()
