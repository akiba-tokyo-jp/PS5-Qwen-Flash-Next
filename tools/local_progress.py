# SPDX-License-Identifier: MIT
"""Bounded local progress observations during Windows file replacement.

Only idempotent local metadata access is repeated. Execution intents, console
requests, data uploads and model operations must never use these helpers.
"""
import json
from pathlib import Path
import time


def read_progress(path, timeout_seconds=5.0, limit=1 << 20):
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with Path(path).open("rb") as stream:
                raw = stream.read(limit + 1)
            if not 0 < len(raw) <= limit:
                raise ValueError("Local progress exceeds its metadata bound")
            return json.loads(raw)
        except (PermissionError, FileNotFoundError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(.025)


def publish_progress(path, value, timeout_seconds=5.0):
    from model_transport import atomic_progress
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            atomic_progress(path, value)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.025)
