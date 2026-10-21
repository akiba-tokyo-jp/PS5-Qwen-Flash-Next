#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Acquire the pinned MIT engine source, without building or running inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())["llama_cpp"]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_relative(name, prefix):
    parts = PurePosixPath(name).parts
    if (not parts or parts[0] != prefix or ".." in parts or "\\" in name
            or ":" in name or PurePosixPath(name).is_absolute()):
        raise ValueError("Archive member escapes its pinned source root")
    return Path(*parts[1:])


def acquire(cache):
    cache.mkdir(parents=True, exist_ok=True)
    revision = LOCK["revision"]
    prefix = "llama.cpp-" + revision
    archive = cache / ("llama-" + revision + ".zip")
    if not archive.exists():
        partial = archive.with_suffix(".zip.partial")
        url = "https://codeload.github.com/" + LOCK["repository"] + "/zip/" + revision
        request = urllib.request.Request(url, headers={"User-Agent": "ps5-qwen-flash-next/1"})
        with urllib.request.urlopen(request, timeout=30) as response, partial.open("wb") as stream:
            remaining = LOCK["archive_bytes"]
            while remaining:
                block = response.read(min(1 << 20, remaining))
                if not block:
                    raise ValueError("Source archive was truncated")
                stream.write(block)
                remaining -= len(block)
            if response.read(1):
                raise ValueError("Source archive exceeds its pinned size")
        if digest(partial) != LOCK["archive_sha256"]:
            raise ValueError("Source archive digest mismatch")
        os.replace(partial, archive)
    if archive.stat().st_size != LOCK["archive_bytes"] or digest(archive) != LOCK["archive_sha256"]:
        raise ValueError("Cached source archive differs from the dependency lock")
    upstream = cache / "upstream"
    upstream.mkdir(exist_ok=True)
    source = upstream / prefix
    receipt_path = upstream / "source-receipt.json"
    if source.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt["revision"] != revision or receipt["archive_sha256"] != LOCK["archive_sha256"]:
            raise ValueError("Existing source receipt differs from the dependency lock")
        print(json.dumps({"source": str(source), "archive_verified": True, "existing_source_retained": True}))
        return
    temporary = upstream / (prefix + ".partial")
    temporary.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        rows = bundle.infolist()
        if sum(row.file_size for row in rows) > 512 * 1024**2:
            raise ValueError("Source archive exceeds the extraction bound")
        for row in rows:
            relative = source_relative(row.filename, prefix)
            if stat.S_ISLNK(row.external_attr >> 16):
                raise ValueError("Source archive contains an unexpected symbolic link")
            target = temporary / relative
            if temporary.resolve() not in (target.resolve(), *target.resolve().parents):
                raise ValueError("Extraction target escapes the new source directory")
            if row.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(row) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
    os.replace(temporary, source)
    receipt = {"revision": revision, "archive_sha256": LOCK["archive_sha256"], "source": str(source)}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source": str(source), "archive_verified": True, "extracted": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    acquire(parser.parse_args().cache.resolve())
