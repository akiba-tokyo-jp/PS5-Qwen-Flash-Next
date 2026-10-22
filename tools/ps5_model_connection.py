#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded data-only transport; no title/GPU actions or existing credential reads."""
from contextlib import contextmanager
import ftplib
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import secrets
import socket
import time
import urllib.error
import urllib.request
from model_transport import REMOTE_ROOT, exclusive_json
from storage_capacity import data_capacity


class PS5ModelConnection:
    def __init__(self, host):
        if not isinstance(host, str): raise ValueError("An explicit console address string is required")
        address = ipaddress.ip_address(host)
        networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        if address.version != 4 or not any(address in ipaddress.ip_network(network) for network in networks):
            raise ValueError("An explicit private-LAN IPv4 console address is required")
        self.host = str(address)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def model_get(self, remote, limit):
        if (remote != REMOTE_ROOT and not remote.startswith(REMOTE_ROOT + "/")) or any(x in remote for x in ("..", "\\", "\r", "\n", "?", "#")):
            raise ValueError("Only the admitted model directory may be read")
        if type(limit) is not int or not 0 <= limit <= 1 << 20:
            raise ValueError("Bounded model metadata reads are required")
        with self.opener.open("http://" + self.host + ":8080/fs" + remote, timeout=8) as response:
            data = response.read(limit + 1)
        if len(data) > limit: raise ValueError("Bounded model metadata read exceeded")
        return data

    def absent(self, remote):
        try: self.model_get(remote, 0)
        except urllib.error.HTTPError as error:
            if error.code == 404: return
            raise
        raise ValueError("New model destination already exists")

    def idle_guard(self, expected_services):
        with self.opener.open("http://" + self.host + ":8084/processes_list", timeout=8) as response:
            raw = response.read((1 << 20) + 1)
        if len(raw) > 1 << 20: raise ValueError("Process metadata exceeded its bound")
        rows = json.loads(raw)["processes"]
        if any(row["name"] == "eboot.bin" for row in rows):
            raise ValueError("A native title is active; model transfer is not admitted")
        if not expected_services or any(sum(row["pid"] == expected["pid"] and row["name"] == expected["name"]
                for row in rows) != 1 for expected in expected_services):
            raise ValueError("Console management service identity changed")

    @contextmanager
    def ftp(self):
        with ftplib.FTP() as ftp:
            ftp.connect(self.host, 2121, timeout=30)
            ftp.login()
            yield ftp

    @staticmethod
    def directory_metadata(ftp):
        rows = []
        def receive(line):
            if len(rows) >= 1024 or len(line) > 4096:
                raise ValueError("Model directory metadata exceeded its bound")
            fields = line.split()
            if len(fields) < 9: raise ValueError("Complete model directory metadata is required")
            if fields[-1] not in {".", ".."}: rows.append(dict(name=fields[-1], mode=fields[0]))
        ftp.retrlines("LIST " + REMOTE_ROOT, receive)
        if len({row["name"] for row in rows}) != len(rows):
            raise ValueError("Duplicate remote model directory entries")
        return rows

    def capacity(self, out):
        """Read only df and an exact completion marker, with fixed bounds."""
        out = Path(out); out.mkdir(parents=True, exist_ok=False)
        marker = ("QWEN_CAPACITY_DONE_" + secrets.token_hex(12)).encode("ascii")
        exclusive_json(out / "intent.private.json", dict(command="df", read_only=True,
            capture_limit_bytes=1 << 20, connect_timeout_seconds=5,
            prompt_deadline_seconds=5, command_deadline_seconds=6, automatic_retries=0,
            title_launches=0, GPU_calls=0))
        captured = bytearray(); before = time.time_ns() // 1000000; steady = time.monotonic()
        completed = False
        try:
            with socket.create_connection((self.host, 2323), 5) as connection:
                connection.settimeout(0.5); initial = b""; deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try: part = connection.recv(65536)
                    except socket.timeout: continue
                    if not part: break
                    initial = (initial + part)[-65536:]
                    if initial.endswith(b"$ "): break
                if not initial.endswith(b"$ "): raise ValueError("The read-only console prompt was not admitted")
                prompt = initial.rsplit(b"\n", 1)[-1]
                if not 2 <= len(prompt) <= 256 or b"\r" in prompt:
                    raise ValueError("A bounded exact console prompt is required")
                connection.sendall(b"df\necho " + marker + b"\n")
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    try: part = connection.recv(65536)
                    except socket.timeout: continue
                    if not part: break
                    if len(captured) + len(part) > 1 << 20:
                        raise ValueError("Filesystem capacity capture exceeded its bound")
                    captured.extend(part)
                    # This shell can print echo output after its already emitted
                    # prompt. Match that exact prompt, never an echoed command.
                    done = rb"(?m)^(?:" + re.escape(prompt) + rb")?" + re.escape(marker) + rb"[ \t]*\r?$"
                    if re.search(done, captured) and captured.endswith(prompt):
                        completed = True; break
            if not completed: raise TimeoutError("The bounded read-only capacity command did not complete")
            capacity = data_capacity(bytes(captured))
            after = time.time_ns() // 1000000
            elapsed = time.monotonic() - steady
            if after < before or abs((after - before) / 1000 - elapsed) > 1:
                raise ValueError("The host clock changed during capacity observation")
            capacity.update(capture_completion_proven=True, host_before_epoch_ms=before,
                host_after_epoch_ms=after, host_elapsed_seconds=elapsed,
                capture_bytes=len(captured), capture_sha256=hashlib.sha256(captured).hexdigest(),
                freshness_proven=False, title_launches=0, GPU_calls=0)
            exclusive_json(out / "receipt.private.json", capacity)
            return capacity
        except BaseException as error:
            exclusive_json(out / "failure.private.json", dict(error_type=type(error).__name__,
                command_completed=completed, automatic_retries=0, title_launches=0, GPU_calls=0))
            raise
        finally:
            with (out / "capture.private.log").open("xb") as stream: stream.write(captured)
