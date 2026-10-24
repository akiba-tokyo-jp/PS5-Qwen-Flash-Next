#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise only a local demo process; never connect to a console or model."""
import argparse
import base64
import http.client
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid

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
    monitor_log = out / ("monitor-observer-" + uuid.uuid4().hex + ".private.jsonl")
    process = subprocess.Popen([str(out / "app-demo.exe"), "--demo", str(ROOT / "web"),
        str(a.cache / "model/chat_template.jinja"), str(port), str(monitor_log)], env=env,
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
        # No HTTP request is issued until two independent observer ticks exist.
        for _ in range(100):
            rows = [json.loads(line) for line in monitor_log.read_text().splitlines()] if monitor_log.exists() else []
            if len(rows) >= 2: break
            if process.poll() is not None: raise RuntimeError(process.stderr.read().decode())
            time.sleep(.1)
        else: raise RuntimeError("Monitor observer did not update independently")
        assert rows[1]["epoch_ms"] > rows[0]["epoch_ms"] and not any(row["model_loaded"] for row in rows)
        for _ in range(100):
            try:
                initial = status(); break
            except OSError:
                if process.poll() is not None: raise RuntimeError(process.stderr.read().decode())
                time.sleep(.1)
        else: raise RuntimeError("Local preview did not become ready")
        assert initial["backend"] == "demo" and not initial["model_loaded"]
        assert initial["process_id"] == process.pid
        assert abs(initial["server_epoch_ms"] - time.time() * 1000) < 5000
        assert initial["clock"] == {"source": "device time (unverified)", "calibrated": False,
                                    "initial_uncertainty_ms": None}
        assert initial["hardware"]["cpu"]["app_usage_percent"] is None
        assert initial["hardware"]["gpu"]["usage_percent"] is None and initial["expert_cache"] is None
        connection, response = request("GET", "/")
        html = response.read().decode()
        assert response.status == 200 and "Inference monitor" in html
        class DisplayParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                assert tag not in {"form", "input", "textarea", "button", "select"}, "Monitor contains a control"
        DisplayParser().feed(html)
        connection.close()
        connection, response = request("GET", "/app.js")
        script = response.read().decode(); connection.close()
        assert "/api/status" in script and "/api/generate" not in script and "/api/cancel" not in script
        for name, mime in (("index.html", "text/html"), ("app.js", "text/javascript"), ("style.css", "text/css")):
            connection, response = request("GET", "/" + name)
            assert response.status == 200 and response.getheader("Content-Type").startswith(mime)
            assert response.read() == (ROOT / "web" / name).read_bytes(); connection.close()
        for path in ("/AGENTS.md", "/appXjs", "/missing.css"):
            connection, response = request("GET", path)
            assert response.status == 404; response.read(); connection.close()
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
        completed = status()["request"]
        assert completed["state"] == "completed" and completed["live_tokens_per_second"] is None
        assert completed["metrics"] == received[-1]["metrics"]
        connection, response = request("POST", "/api/generate", payload("cancel"))
        assert response.status == 200
        iterator = events(response)
        token_count = 0
        while token_count < 3:
            if next(iterator)["type"] == "token": token_count += 1
        live = status()
        assert live["busy"] and live["request"]["live_tokens_per_second"] > 0
        assert live["request"]["metrics"]["generated_tokens"] >= 3
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
                   "model_loaded": False, "tests": ["read_only_assets", "time_and_unknown_hardware", "live_and_completed_metrics",
                       "request_validation", "streaming", "busy", "cancel", "invalid_chat_recovery", "observer_without_browser"]}
        (out / "http-check.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        process.stderr.close()

    # The native no-model mode uses this same route guard. Verify it never
    # reaches the demo engine, including for a syntactically valid request.
    process = subprocess.Popen([str(out / "app-demo.exe"), "--monitor-demo", str(ROOT / "web"),
        str(a.cache / "model/chat_template.jinja"), str(port)], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(100):
            try: initial = status(); break
            except OSError: time.sleep(.1)
        else: raise RuntimeError("Monitor-only host fixture did not start")
        connection, response = request("POST", "/api/generate", payload("must-not-execute"))
        assert response.status == 503 and json.loads(response.read())["error"] == "inference_not_loaded"
        connection.close()
        assert not status()["busy"] and not status()["model_loaded"]
        print("No-model generation rejection passed; host fixture only")
    finally:
        process.terminate(); process.wait(timeout=10); process.stderr.close()


if __name__ == "__main__":
    main()
