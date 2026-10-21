#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise only a local demo process; never connect to a console or model."""
import argparse
import base64
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
    a = parser.parse_args()
    out = a.cache / "build/application-preview"
    env = os.environ.copy()
    env["PATH"] = str(a.workspace / "toolchain/msys-clang64/clang64/bin") + os.pathsep + env.get("PATH", "")
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0)); port = reserved.getsockname()[1]
    process = subprocess.Popen([str(out / "app-demo.exe"), "--demo", str(ROOT / "web"),
        str(a.cache / "model/chat_template.jinja"), str(port)], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)

    def request(method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
        data = json.dumps(body) if body is not None else None
        connection.request(method, path, data, {"Content-Type": "application/json"})
        return connection, connection.getresponse()

    def events(response):
        for raw in response:
            if raw.startswith(b"data: "):
                yield json.loads(raw[6:])

    def payload(identifier):
        return {"id": identifier, "messages": [{"role": "user", "content": "Hello"}],
                "max_output_tokens": 256, "context_tokens": 4096, "enable_thinking": True}

    def status():
        connection, response = request("GET", "/api/status")
        data = json.loads(response.read()); connection.close(); return data

    try:
        for _ in range(100):
            try:
                initial = status(); break
            except OSError:
                if process.poll() is not None: raise RuntimeError(process.stderr.read().decode())
                time.sleep(.1)
        else: raise RuntimeError("Local preview did not become ready")
        assert initial["backend"] == "demo" and not initial["model_loaded"]
        connection, response = request("GET", "/")
        assert response.status == 200 and b"Application preview" in response.read()
        connection.close()
        connection, response = request("POST", "/api/generate", {"id": "bad"})
        assert response.status == 400; response.read(); connection.close()
        for field, value in (("tools", []), ("context_tokens", 8192)):
            invalid = payload("unsupported"); invalid[field] = value
            connection, response = request("POST", "/api/generate", invalid)
            assert response.status == 400; response.read(); connection.close()
        connection, response = request("POST", "/api/generate", payload("full"))
        assert response.status == 200
        received = list(events(response)); connection.close()
        assert received[-1]["state"] == "completed" and received[-1]["type"] == "finished"
        text = b"".join(base64.b64decode(row["piece_b64"]) for row in received if row["type"] == "token").decode()
        assert text.startswith("Demo only:") and "No model is loaded" in text
        assert received[-1]["metrics"]["ttft_ms"] is not None
        for _ in range(100):
            if not status()["busy"]: break
            time.sleep(.01)
        connection, response = request("POST", "/api/generate", payload("cancel"))
        assert response.status == 200
        iterator = events(response)
        while next(iterator)["type"] != "token": pass
        second, rejected = request("POST", "/api/generate", payload("busy"))
        assert rejected.status == 409; rejected.read(); second.close()
        second, cancelled = request("POST", "/api/cancel", {"id": "cancel"})
        assert cancelled.status == 202; cancelled.read(); second.close()
        remainder = list(iterator); connection.close()
        assert remainder[-1]["state"] == "cancelled" and remainder[-1]["type"] == "finished"
        for _ in range(100):
            current = status()
            if not current["busy"]: break
            time.sleep(.01)
        invalid = payload("invalid-chat")
        invalid["messages"].append({"role": "system", "content": "Invalid system placement"})
        connection, response = request("POST", "/api/generate", invalid)
        rows = list(events(response)); connection.close()
        assert rows[-1]["state"] == "failed" and rows[-1]["error"] == "invalid_chat"
        for _ in range(100):
            if not status()["busy"]: break
            time.sleep(.01)
        assert not status()["quarantined"], "Invalid user input quarantined a healthy backend"
        receipt = {"demo_http_scenarios_passed": True, "console_access": False,
                   "model_loaded": False, "tests": ["assets", "request_validation", "streaming", "busy", "cancel", "invalid_chat_recovery"]}
        (out / "http-check.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        process.stderr.close()


if __name__ == "__main__":
    main()
