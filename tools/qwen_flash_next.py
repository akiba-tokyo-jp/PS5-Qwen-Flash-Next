#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Acquire and inspect the pinned original BF16 checkpoint without inference.

Metadata inspection uses HTTP ranges, never downloads a whole shard as a header,
and verifies the original tensor index. Weight downloads require the explicit
download command. Model data and temporary files belong on a spacious data disk.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
MODEL = LOCK["model"]["repository"]
REVISION = LOCK["model"]["revision"]
BASE = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/"
MAX_HEADER = 8 * 1024 * 1024
WIDTH = {"BF16": 2, "F32": 4, "I64": 8}


def atomic_replace(source: Path, destination: Path) -> None:
    """Bound retries to transient Windows file sharing/permission conflicts."""
    for attempt in range(5):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            if os.name != "nt" or getattr(error, "winerror", None) not in (5, 32, 33) or attempt == 4:
                raise
            time.sleep(0.05 * 2 ** attempt)


def json_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    atomic_replace(temporary, path)


@contextmanager
def writer_lease(path: Path):
    """Hold a nonblocking OS lock; process exit releases it without stale-lock deletion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if not stream.seek(0, os.SEEK_END):
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Another host writer owns the model preparation lease") from error
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError("Another host writer owns the model preparation lease") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def safe_name(name: str) -> str:
    p = PurePosixPath(name)
    if p.is_absolute() or len(p.parts) != 1 or name in ("", ".", "..") or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe model file name: {name!r}")
    return name


def request(url: str, start: int | None = None, end: int | None = None):
    headers = {"User-Agent": "ps5-qwen-flash-next/1", "Accept-Encoding": "identity"}
    if start is not None:
        headers["Range"] = f"bytes={start}-" + (str(end) if end is not None else "")
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)


def fetch_small(url: str, maximum: int) -> bytes:
    with request(url) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Metadata exceeds the bounded download size")
    return data


def fetch_range(url: str, start: int, length: int) -> bytes:
    if start < 0 or not 0 < length <= MAX_HEADER:
        raise ValueError("Invalid bounded range")
    end = start + length - 1
    with request(url, start, end) as response:
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if response.status != 206 or not match or tuple(map(int, match.groups()[:2])) != (start, end):
            raise ValueError("Server did not honor the exact HTTP range")
        data = response.read(length + 1)
    if len(data) != length:
        raise ValueError("Truncated or oversized HTTP range")
    return data


def tensor_header(name: str, file_bytes: int) -> tuple[dict, int, bytes]:
    prefix = fetch_range(BASE + safe_name(name), 0, 8)
    header_bytes, = struct.unpack("<Q", prefix)
    if not 2 <= header_bytes <= MAX_HEADER or 8 + header_bytes > file_bytes:
        raise ValueError(f"Invalid safetensors header: {name}")
    raw = fetch_range(BASE + name, 8, header_bytes)
    header = json.loads(raw)
    if not isinstance(header, dict):
        raise ValueError("Safetensors header is not an object")
    intervals = []
    for key, value in header.items():
        if key == "__metadata__":
            continue
        dtype, shape, span = value["dtype"], value["shape"], value["data_offsets"]
        if dtype not in WIDTH or not all(type(x) is int and x >= 0 for x in shape):
            raise ValueError(f"Unexpected original tensor format: {key}")
        if len(span) != 2 or any(type(x) is not int for x in span):
            raise ValueError(f"Invalid tensor offset: {key}")
        begin, end = span
        if begin < 0 or end - begin != math.prod(shape) * WIDTH[dtype] or 8 + header_bytes + end > file_bytes:
            raise ValueError(f"Tensor exceeds its original shard: {key}")
        intervals.append((begin, end))
    intervals.sort()
    if any(right[0] != left[1] for left, right in zip(intervals, intervals[1:])):
        raise ValueError(f"Overlapping or discontinuous tensor data: {name}")
    if intervals and (intervals[0][0] != 0 or intervals[-1][1] + 8 + header_bytes != file_bytes):
        raise ValueError(f"Unindexed shard bytes: {name}")
    return header, 8 + header_bytes, raw


def prepare(cache: Path, jobs: int) -> None:
    destination = cache / "model"
    destination.mkdir(parents=True, exist_ok=True)
    api = f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true"
    metadata = json.loads(fetch_small(api, 4 * 1024 * 1024))
    if metadata.get("sha") != REVISION:
        raise ValueError("Model revision changed")
    json_write(cache / "metadata/repository.json", metadata)
    siblings = {safe_name(row["rfilename"]): row for row in metadata["siblings"]}
    files = ["LICENSE", "config.json", "generation_config.json", "model.safetensors.index.json",
             "tokenizer.json", "tokenizer_config.json", "chat_template.jinja"]
    for name in files:
        path = destination / name
        expected = siblings[name]["size"]
        if expected > 32 * 1024 * 1024:
            raise ValueError(f"Unexpected metadata size: {name}")
        data = fetch_small(BASE + name, expected)
        if len(data) != expected:
            raise ValueError(f"Metadata size mismatch: {name}")
        sha = siblings[name].get("lfs", {}).get("sha256")
        if sha and hashlib.sha256(data).hexdigest() != sha:
            raise ValueError(f"Metadata digest mismatch: {name}")
        path.write_bytes(data)
    config = json.loads((destination / "config.json").read_text())
    if config["text_config"]["dtype"] != "bfloat16" or config.get("quantization_config"):
        raise ValueError("The checkpoint is not the requested unquantized BF16 model")
    index = json.loads((destination / "model.safetensors.index.json").read_text())
    names = sorted(set(index["weight_map"].values()))
    tensor_rows, file_rows = {}, []
    header_dir = cache / "metadata/headers"
    header_dir.mkdir(parents=True, exist_ok=True)

    def one(name):
        row = siblings[safe_name(name)]
        lfs = row.get("lfs", {})
        if not re.fullmatch(r"[0-9a-f]{64}", lfs.get("sha256", "")):
            raise ValueError(f"Missing original shard SHA256: {name}")
        header_path = header_dir / (name + ".json")
        # Fetching headers again is intentional: the revision is immutable and bounded.
        header, offset, raw = tensor_header(name, row["size"])
        header_path.write_bytes(raw)
        return name, header, offset, {"name": name, "bytes": row["size"], "sha256": lfs["sha256"],
                                     "data_offset": offset, "header_sha256": hashlib.sha256(raw).hexdigest()}

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(one, name) for name in names]
        for number, future in enumerate(as_completed(futures), 1):
            name, header, offset, row = future.result()
            file_rows.append(row)
            for key, value in header.items():
                if key == "__metadata__":
                    continue
                if key in tensor_rows or index["weight_map"].get(key) != name:
                    raise ValueError(f"Index/header disagreement: {key}")
                tensor_rows[key] = dict(value, file=name, file_offset=offset + value["data_offsets"][0])
            if number % 16 == 0 or number == len(names):
                print(f"Checked original BF16 shard headers: {number}/{len(names)}", flush=True)
    if set(tensor_rows) != set(index["weight_map"]):
        raise ValueError("The original index has missing tensor data")
    dtype_bytes = Counter()
    for row in tensor_rows.values():
        dtype_bytes[row["dtype"]] += math.prod(row["shape"]) * WIDTH[row["dtype"]]
    if set(dtype_bytes) - {"BF16", "I64"}:
        raise ValueError("Original checkpoint contains an unexpected reduced precision")
    if sum(dtype_bytes.values()) != index["metadata"]["total_size"]:
        raise ValueError("Original tensor byte count differs from model index")
    manifest = {"schema": "ps5-qwen-original-bf16-v1", "repository": MODEL, "revision": REVISION,
                "quantization": False, "dtype_bytes": dict(dtype_bytes), "files": sorted(file_rows, key=lambda x: x["name"]),
                "tensors": dict(sorted(tensor_rows.items()))}
    json_write(cache / "metadata/checkpoint.json", manifest)
    print(json.dumps({"manifest": str(cache / "metadata/checkpoint.json"), "tensors": len(tensor_rows),
                      "shards": len(file_rows), "dtype_bytes": dict(dtype_bytes)}, indent=2), flush=True)


def download(cache: Path, jobs: int, timeout_seconds: int = 43200, *, verify_existing: bool = True) -> None:
    if not 1 <= timeout_seconds <= 86400:
        raise ValueError("Invalid host acquisition deadline")
    with writer_lease(cache / "model-download.lock.private"):
        _download(cache, jobs, timeout_seconds, verify_existing)


def _download(cache: Path, jobs: int, timeout_seconds: int, verify_existing: bool) -> None:
    manifest = json.loads((cache / "metadata/checkpoint.json").read_text())
    if manifest["revision"] != REVISION or manifest["quantization"]:
        raise ValueError("Checkpoint identity mismatch")
    destination = cache / "model"
    rows = manifest["files"]
    missing = sum(max(0, row["bytes"] - ((destination / (row["name"] + ".partial")).stat().st_size
                   if (destination / (row["name"] + ".partial")).exists() else 0))
                  for row in rows if not (destination / row["name"]).exists())
    if shutil.disk_usage(destination).free < missing + 32 * 1024**3:
        raise ValueError("Insufficient data-disk space with 32 GiB headroom")
    started = time.monotonic()
    stopped = threading.Event()

    def boundary():
        if stopped.is_set():
            raise RuntimeError("Download stopped; verified ranges retained for resume")
        if time.monotonic() - started >= timeout_seconds:
            raise TimeoutError("Host acquisition deadline exceeded; partial files retained")

    def verify(path, expected):
        result = hashlib.sha256()
        with path.open("rb") as stream:
            while True:
                boundary()
                block = stream.read(1 << 20)
                if not block:
                    break
                result.update(block)
        if result.hexdigest() != expected:
            raise ValueError("SHA256 mismatch, source retained: " + path.name)

    def one(row):
        target = destination / safe_name(row["name"])
        temporary = target.with_name(target.name + ".partial")
        if target.exists():
            if target.stat().st_size != row["bytes"]:
                raise ValueError(f"Existing shard size mismatch: {target.name}")
            if verify_existing:
                verify(target, row["sha256"])
            return target.name, 0, verify_existing
        offset = temporary.stat().st_size if temporary.exists() else 0
        if offset > row["bytes"]:
            raise ValueError("Partial file is larger than the original shard")
        if offset < row["bytes"]:
            with temporary.open("ab" if offset else "wb", buffering=0) as stream:
                position = offset
                while position < row["bytes"]:
                    boundary()
                    length = min(MAX_HEADER, row["bytes"] - position)
                    for attempt in range(4):
                        boundary()
                        try:
                            block = fetch_range(BASE + row["name"], position, length)
                            break
                        except (OSError, TimeoutError) as error:
                            if attempt == 3 or stopped.wait(min(2 ** attempt, 4)):
                                raise RuntimeError(f"Download range failed: {target.name} at {position}") from error
                    written = stream.write(block)
                    if written != length:
                        raise OSError("Incomplete local shard write")
                    position += length
                os.fsync(stream.fileno())
        verify(temporary, row["sha256"])
        os.replace(temporary, target)
        json_write(cache / "receipts" / (target.name + ".json"), row)
        return target.name, row["bytes"] - offset, True

    verified = 0
    processed = 0

    def local_bytes():
        total = 0
        for row in rows:
            target = destination / row["name"]
            try:
                total += target.stat().st_size
            except FileNotFoundError:
                try:
                    total += target.with_name(target.name + ".partial").stat().st_size
                except FileNotFoundError:
                    # A worker can atomically publish between these two reads.
                    if target.exists():
                        total += target.stat().st_size
        return total

    initial_bytes = local_bytes()
    def report(phase, **fields):
        value = {"schema": "ps5-qwen-download-progress-v2", "phase": phase, "pid": os.getpid(),
                 "updated_at": datetime.now(timezone.utc).isoformat(), "verified_shards": verified,
                 "processed_shards": processed, "reused_unverified_shards": processed - verified,
                 "existing_shards_reverified": verify_existing,
                 "original_shards_verified": phase == "completed" and verified == len(rows),
                 "total_shards": len(rows), "local_bytes": local_bytes(),
                 "received_bytes_this_run": max(0, local_bytes() - initial_bytes),
                 "elapsed_seconds": time.monotonic() - started, "deadline_seconds": timeout_seconds,
                 "complete": phase == "completed", "console_access": False,
                 "learned_inference_performed": False, **fields}
        json_write(cache / "download-progress.json", value)
        return value

    report("downloading")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = {pool.submit(one, row) for row in rows}
        try:
            while pending:
                boundary()
                done, pending = wait(pending, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    name, _, checked = future.result()
                    processed += 1
                    verified += int(checked)
                    print(f"{'Verified' if checked else 'Retained for conversion verification'} {processed}/{len(rows)} shards; {name}", flush=True)
                current = report("downloading" if pending else "completed")
                print(f"Progress: {verified}/{len(rows)} verified; {current['received_bytes_this_run']/1e9:.2f} GB received", flush=True)
        except BaseException as error:
            report("failed", error_type=type(error).__name__)
            raise
        finally:
            stopped.set()
            for future in pending:
                future.cancel()


def sample(cache: Path, name: str, expert: int, out: Path) -> None:
    manifest = json.loads((cache / "metadata/checkpoint.json").read_text())
    row = manifest["tensors"][name]
    shape = row["shape"]
    if row["dtype"] != "BF16" or len(shape) != 3 or not 0 <= expert < shape[0]:
        raise ValueError("A BF16 expert-major tensor and a valid expert ID are required")
    length = math.prod(shape[1:]) * 2
    offset = row["file_offset"] + expert * length
    # Larger expert spans are split into independently checked bounded ranges.
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise ValueError("Sample output already exists")
    temporary = out.with_name(out.name + ".partial")
    if temporary.exists():
        raise ValueError("Sample partial output already exists")
    digest = hashlib.sha256()
    with temporary.open("xb") as stream:
        for done in range(0, length, MAX_HEADER):
            block = fetch_range(BASE + row["file"], offset + done, min(MAX_HEADER, length - done))
            stream.write(block)
            digest.update(block)
    os.replace(temporary, out)
    receipt = {"repository": MODEL, "revision": REVISION, "tensor": name, "expert": expert,
               "source_file": row["file"], "source_offset": offset, "shape": shape[1:], "dtype": "BF16",
               "bytes": length, "sha256": digest.hexdigest(), "inference_performed": False}
    json_write(out.with_name(out.name + ".json"), receipt)
    print(json.dumps(receipt, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "download", "sample"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=43200)
    parser.add_argument("--tensor")
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 8:
        parser.error("jobs must be between 1 and 8")
    if args.command == "prepare":
        prepare(args.cache.resolve(), args.jobs)
    elif args.command == "download":
        download(args.cache.resolve(), args.jobs, args.timeout_seconds)
    else:
        if not args.tensor or args.out is None:
            parser.error("sample requires --tensor and --out")
        sample(args.cache.resolve(), args.tensor, args.expert, args.out.resolve())


if __name__ == "__main__":
    main()
