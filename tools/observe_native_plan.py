#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe one already launched native owner and issue exactly two fixed API requests.

No launch, installation, title close, model conversion, credential extraction or
learned host inference occurs. Every POST has an exclusive durable intent and
is never retried, including connection failures. Physical restoration is a
separate required step after this observer's positive native result.
"""
import argparse
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import re
import struct
import time
from urllib.parse import quote

from first_generation_result import read_record, validate, require, integer, number

MODEL_ROOT = "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/"
PROMPT = "Count from 1 to 8, separated by commas. Reply with only the sequence."


def exclusive(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False); stream.write("\n"); stream.flush()
        import os
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True,
        help="Private owner/digest/endpoint binding prepared after fresh native owner admission")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    binding = read_record(args.binding)
    require(binding.get("schema") == "ps5-qwen-native-plan-observer-v1", "Unknown observer binding")
    expected = binding["native_binding"]
    require(expected.get("schema") == "ps5-qwen-first-generation-binding-v1" and
        re.fullmatch("[0-9a-f]{32}", expected.get("run_id", "")) and integer(expected.get("pid"), 1, 2**31-1),
        "A fresh exact native owner and run are required")
    host = binding["host"]
    address = ipaddress.ip_address(host)
    require(address.version == 4 and address.is_private and not address.is_loopback and
        not address.is_unspecified and not address.is_multicast, "Only the task's private physical console is admitted")
    remote = MODEL_ROOT + "plan-" + expected["run_id"] + ".json"
    require(binding.get("report_remote") == remote and binding.get("port") == 8086 and
        binding.get("automatic_retries") == 0, "The exact bounded report/API binding is required")
    assets = binding["monitor_assets"]
    require(set(assets) == {"/", "/app.js", "/style.css"} and
        all(type(v) is str and re.fullmatch("[0-9a-f]{64}", v) for v in assets.values()), "The three exact monitor assets are required")
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    result_path = out / "native-result.private.json"
    exclusive(out / "intent.private.json", dict(binding_sha256=hashlib.sha256(args.binding.read_bytes()).hexdigest(),
        run_id=expected["run_id"], pid=expected["pid"], maximum_generation_POSTs=2, maximum_finish_POSTs=1,
        maximum_ready_wait_seconds=13260, maximum_total_seconds=25200, automatic_retries=0,
        console_launches=0, learned_host_inference=False))
    started = time.monotonic()

    def get(port, path, limit):
        connection = http.client.HTTPConnection(host, port, timeout=5)
        try:
            connection.request("GET", path, headers={"Connection": "close"})
            response = connection.getresponse(); raw = response.read(limit + 1)
            require(len(raw) <= limit, "A native observation exceeded its byte bound")
            if response.status == 404: return None
            require(response.status == 200, "A native observation returned an unexpected status")
            return raw
        finally:
            connection.close()

    def download(suffix, optional=False):
        raw = get(8080, "/fs" + quote(remote + suffix, safe="/"), (9 << 20) if suffix.endswith(".bmp") else (1 << 20))
        if raw is None:
            require(optional, "Required native evidence is missing: " + suffix); return None
        target = Path(str(result_path) + suffix)
        if target.exists():
            require(target.read_bytes() == raw, "Previously observed native evidence changed")
        else:
            with target.open("xb") as stream: stream.write(raw)
        return raw

    def failure_check():
        for suffix in (".failure", ".fatal"):
            require(download(suffix, optional=True) is None, "Native failure/fatal evidence prevents further requests")
        require(time.monotonic() - started <= 25200, "The independent native observation deadline expired")

    def status():
        raw = get(8086, "/api/status", 1 << 20)
        require(raw is not None, "The admitted native API is absent")
        data = json.loads(raw)
        require(data.get("process_id") == expected["pid"] and data.get("run_id") == expected["run_id"] and
            data.get("backend") == "model" and data.get("model_loaded") is True and data.get("quarantined") is False,
            "The external API does not match the admitted native owner")
        clock = data.get("clock", {})
        require(clock.get("calibrated") is True and clock.get("source") == "host-calibrated UTC" and
            integer(clock.get("initial_uncertainty_ms"), 0, 5000), "Calibrated monitor time is absent")
        hardware = data.get("hardware", {})
        require(type(hardware.get("cpu", {}).get("name")) is str and hardware["cpu"]["name"] and
            integer(hardware["cpu"].get("logical_threads"), 1, 256) and
            type(hardware.get("gpu", {}).get("name")) is str and hardware["gpu"]["name"],
            "CPU/GPU identity is absent from the passive monitor")
        return data

    posts = 0
    def post(path, body, stem, streamed=False):
        nonlocal posts
        exclusive(out / (stem + ".once.private.json"), dict(path=path, body=body, automatic_retries=0,
            elapsed_seconds=time.monotonic() - started))
        connection = http.client.HTTPConnection(host, 8086, timeout=10)
        try:
            posts += 1
            connection.connect()
            transport = connection.sock
            require(transport is not None, "The once-only native transport did not connect")
            transport.settimeout(3630 if streamed else 10)
            request_started = time.monotonic()
            connection.request("POST", path, json.dumps(body), {"Content-Type": "application/json", "Connection": "close"})
            response = connection.getresponse()
            require(response.status == 200, "The once-only native request was not accepted")
            if not streamed:
                raw = response.read(4097); require(len(raw) <= 4096, "The finish response exceeded its bound")
                require(json.loads(raw) == {"state": "accepted"}, "The native finish acknowledgement differs")
                exclusive(out / (stem + ".positive.private.json"), dict(HTTP_status=200, response=json.loads(raw)))
                return []
            events = []; received = 0; first_token_received = None
            with (out / (stem + ".stream.private.log")).open("xb") as stream:
                while True:
                    remaining = 3630 - (time.monotonic() - request_started)
                    require(remaining > 0, "The once-only native response deadline expired")
                    transport.settimeout(remaining)
                    line = response.readline((256 << 10) + 1)
                    require(len(line) <= (256 << 10), "An SSE line exceeded its bound")
                    if not line: break
                    received += len(line); require(received <= (8 << 20), "The native token stream exceeded its bound")
                    stream.write(line); stream.flush()
                    if line.startswith(b"data: "):
                        event = json.loads(line[6:]); events.append(event)
                        if event.get("type") == "token" and first_token_received is None:
                            first_token_received = time.monotonic()
                        require(len(events) <= 33 and event.get("id") == body["id"] and event.get("error") == 0,
                            "Unexpected native stream event")
            require(3 <= len(events) <= 33 and events[-1].get("type") == "finished" and
                events[-1].get("state") == "completed", "A complete measurable native response is required")
            require(all(e.get("type") == "token" and e.get("ordinal") == i for i, e in enumerate(events[:-1], 1)),
                "The external token stream has missing or additional events")
            require(first_token_received is not None, "A completed native token must reach the external observer")
            exclusive(out / (stem + ".positive.private.json"), dict(HTTP_status=200, events=events,
                host_POST_to_first_token_seconds=first_token_received - request_started,
                host_POST_to_response_end_seconds=time.monotonic() - request_started,
                host_timings_include_queue_and_network=True))
            return events
        except BaseException as error:
            exclusive(out / (stem + ".uncertain.private.json"), dict(error_type=type(error).__name__, automatic_retries=0))
            raise
        finally:
            connection.close()

    try:
        next_update = 0
        while download(".demo.ready", optional=True) is None:
            failure_check()
            require(time.monotonic() - started <= 13260, "The native ready deadline expired")
            if time.monotonic() >= next_update:
                stages = get(8080, "/fs" + MODEL_ROOT + "entry-" + str(expected["pid"]) + ".stages", 1 << 20)
                if stages is not None:
                    (out / "native-stages.latest.private.txt").write_bytes(stages)
                lines = stages.decode("utf-8", errors="replace").splitlines() if stages else []
                print(json.dumps(dict(phase="waiting_for_native_integrity_load_and_first_request", pid=expected["pid"],
                    elapsed_seconds=round(time.monotonic() - started),
                    last_native_stage=lines[-1] if lines else None)), flush=True); next_update = time.monotonic() + 60
            time.sleep(5)
        ready = read_record(Path(str(result_path) + ".demo.ready"))
        require(ready.get("pid") == expected["pid"] and ready.get("run_id") == expected["run_id"] and
            ready.get("listener_bind") == "0.0.0.0", "Native readiness differs from the independent binding")
        first_status = status(); exclusive(out / "monitor-first.private.json", first_status)
        for path, digest in assets.items():
            raw = get(8086, path, 256 << 10)
            require(raw is not None and hashlib.sha256(raw).hexdigest() == digest, "A served passive monitor asset differs")
        observed_streams = []
        for ordinal in (1, 2):
            failure_check()
            observed_streams.append(post("/api/generate", dict(id=expected["run_id"] + "-" + str(ordinal),
                messages=[dict(role="user", content=PROMPT)], context_tokens=256, max_output_tokens=32,
                enable_thinking=False), "request-" + str(ordinal), streamed=True))
            deadline = time.monotonic() + 30
            while True:
                data = status()
                if data.get("busy") is False and data.get("validation", {}).get("completed_requests") == ordinal: break
                require(time.monotonic() < deadline, "Completed response did not reach positive idle ownership")
                failure_check(); time.sleep(.2)
            exclusive(out / ("monitor-request-" + str(ordinal) + ".private.json"), data)
            print(json.dumps(dict(phase="native_external_request_observed", ordinal=ordinal,
                generated_tokens=observed_streams[-1][-1]["metrics"]["generated_tokens"])), flush=True)
        while True:
            final_status = status()
            if final_status["server_epoch_ms"] - first_status["server_epoch_ms"] >= 1000: break
            time.sleep(.2)
        exclusive(out / "monitor-last.private.json", final_status)
        post("/api/validation/finish", {"run_id": expected["run_id"]}, "finish")
        deadline = time.monotonic() + 60
        while download("", optional=True) is None:
            failure_check(); require(time.monotonic() < deadline, "The terminal native resource-retirement result is missing")
            time.sleep(1)
        result = read_record(result_path)
        require(type(result.get("token_ids")) is list and len(result["token_ids"]) <= 32 and
            type(result.get("demonstration", {}).get("requests")) is list and len(result["demonstration"]["requests"]) == 2,
            "Native terminal counts exceed the fixed observation scope")
        for suffix in (".first.start", ".first.intent", ".integrity", ".mapping", ".memory", ".source", ".first.result", ".demo.cache", ".demo.result"):
            download(suffix)
        for index in range(1, len(result.get("token_ids", [])) + 1): download(".first.token-" + str(index))
        for ordinal in (1, 2):
            prefix = ".demo" + str(ordinal)
            download(prefix + ".intent"); download(prefix + ".result"); download(prefix + ".display.json")
            frame = download(prefix + ".display.bmp")
            require(len(frame) == 8294454 and frame[:2] == b"BM" and struct.unpack_from("<II", frame, 18) == (1920, 1080),
                "The completed native scanout-source frame differs")
            tokens = result["demonstration"]["requests"][ordinal-1]["token_ids"]
            require(type(tokens) is list and 2 <= len(tokens) <= 32, "External native token counts exceed their scope")
            for index in range(1, len(tokens) + 1): download(prefix + ".token-" + str(index))
            native = [read_record(Path(str(result_path) + prefix + ".token-" + str(i))) for i in range(1, len(tokens)+1)]
            require(native == observed_streams[ordinal-1][:-1], "External token events differ from native durable records")
        failure_check()
        review = validate(result_path, expected)
        exclusive(out / "native-review.private.json", review)
        exclusive(out / "complete.private.json", dict(state="native_requests_verified_restoration_required",
            native_result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(), pid=expected["pid"],
            generation_POSTs=2, finish_POSTs=1, automatic_retries=0, model_resources_positively_retired=True,
            ordinary_close_and_original_restoration_verified=False, full_plan_completed=False))
        require(posts == 3, "Unexpected native POST count")
        print(json.dumps(dict(phase="native_requests_verified_restoration_required", ordinary_close_and_original_restoration_verified=False)), flush=True)
    except BaseException as error:
        exclusive(out / "failed.private.json", dict(error_type=type(error).__name__, message=str(error),
            native_POST_attempts=posts, automatic_retries=0, full_plan_completed=False))
        raise


if __name__ == "__main__":
    main()
