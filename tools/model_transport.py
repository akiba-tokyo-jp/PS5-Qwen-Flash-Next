#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Single-writer, one-attempt model transport; native SHA admission is separate.

The caller must first admit the complete v2 receipt, fresh idle session,
reservation, available storage and an owned, readable destination directory.
This module never starts a title, initializes Vulkan, deletes remote files,
reads credentials, or retries an ambiguous write.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import time

REMOTE_ROOT = "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/model"
CHUNK_BYTES = 1 << 20


def exclusive_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def atomic_progress(path, value):
    path = Path(path); temporary = path.with_suffix(path.suffix + ".next")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def writer_lease(path):
    """An OS-released lock; a stale file never grants permission to retry."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    locked = False
    try:
        stream.seek(0, 2)
        if stream.tell() == 0: stream.write(b"0"); stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt": msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()


def validate_file(row):
    name = row["path"]
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,235}\.gguf", name):
        raise ValueError("A plain relative GGUF basename is required")
    if type(row["bytes"]) is not int or not 0 < row["bytes"] <= 512 << 30:
        raise ValueError("A bounded original model split size is required")
    if not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
        raise ValueError("A complete original split SHA256 is required")
    return name


def source_identity(info):
    # Windows pathname stat and descriptor fstat can expose different deprecated
    # ctime meanings. Pin file ID, size and last-write time, plus the full stream
    # SHA below; creation/change-time is not an interchangeable identity field.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


class _HashingReader:
    def __init__(self, stream, expected_bytes, deadline, progress):
        self.stream = stream; self.expected_bytes = expected_bytes
        self.deadline = deadline; self.progress = progress
        self.count = 0; self.digest = hashlib.sha256()

    def read(self, size):
        if time.monotonic() >= self.deadline: raise TimeoutError("Model file upload deadline exceeded")
        if not 0 < size <= CHUNK_BYTES: raise ValueError("Bounded sequential transport reads are required")
        data = self.stream.read(size)
        self.count += len(data)
        if self.count > self.expected_bytes: raise ValueError("Source grew during model transfer")
        self.digest.update(data); self.progress(self.count)
        return data


def upload_file_once(ftp, source_directory, row, record_directory, nonce, *,
                     guard, absent, timeout_seconds=21600, progress=lambda count: None):
    """Upload one new partial, check source/226/size/mode, then rename it once.

    Hold writer_lease for the whole model, not just this call. guard checks the
    reservation and idle owner before each mutation; absent must distinguish a
    positive absence response from network failure. Neither is inferred here.
    A recorded success may be skipped by a separately reviewed resume caller.
    An intent without success always requires review, even after a timeout.
    """
    name = validate_file(row)
    if not re.fullmatch(r"[0-9a-f]{32}", nonce): raise ValueError("A fresh transfer nonce is required")
    if type(timeout_seconds) is not int or not 60 <= timeout_seconds <= 43200:
        raise ValueError("An explicit bounded file deadline is required")
    source_directory = Path(source_directory).resolve()
    source = source_directory / name
    if source.is_symlink() or source.resolve().parent != source_directory:
        raise ValueError("A regular original file in the admitted source directory is required")
    info = source.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]:
        raise ValueError("Original split metadata changed before upload")
    record_directory = Path(record_directory)
    record_directory.mkdir(parents=True, exist_ok=True)
    stem = record_directory / name
    intent = stem.with_name(stem.name + ".intent.private.json")
    complete = stem.with_name(stem.name + ".complete.private.json")
    failure = stem.with_name(stem.name + ".failure.private.json")
    if intent.exists() or complete.exists() or failure.exists():
        raise ValueError("This file already has an attempt; no automatic transfer retry")
    destination = str(PurePosixPath(REMOTE_ROOT) / name)
    partial = destination + ".partial-" + nonce
    guard(); absent(destination); absent(partial)
    started = time.monotonic()
    exclusive_json(intent, dict(schema="ps5-qwen-model-file-transfer-intent-v1",
        source=str(source), original=row, destination=destination, partial=partial,
        source_identity=source_identity(info), timeout_seconds=timeout_seconds,
        automatic_retries=0, native_SHA_verified=False, GPU_calls=0))
    try:
        guard()
        with source.open("rb") as stream:
            if source_identity(os.fstat(stream.fileno())) != source_identity(info):
                raise ValueError("Source identity changed before the first upload read")
            reader = _HashingReader(stream, row["bytes"], started + timeout_seconds, progress)
            response = ftp.storbinary("STOR " + partial, reader, blocksize=CHUNK_BYTES)
            if not isinstance(response, str) or not response.startswith("226 "):
                raise ValueError("Positive FTP transfer completion is required")
            if reader.count != row["bytes"] or reader.digest.hexdigest() != row["sha256"]:
                raise ValueError("Transferred source bytes differ from the original receipt")
            if source_identity(os.fstat(stream.fileno())) != source_identity(info):
                raise ValueError("Open source changed during transfer")
        if source_identity(source.stat()) != source_identity(info):
            raise ValueError("Source pathname changed during transfer")
        if time.monotonic() >= started + timeout_seconds:
            raise TimeoutError("Model file verification deadline exceeded")
        ftp.voidcmd("TYPE I")
        if ftp.size(partial) != row["bytes"]: raise ValueError("Remote partial size differs")
        listing = []; ftp.retrlines("LIST " + partial, listing.append)
        if len(listing) != 1: raise ValueError("One regular remote split is required")
        mode = listing[0].split()[0]
        if len(mode) != 10 or mode[0] != "-" or mode[7] != "r":
            raise ValueError("The native title must be able to read the remote regular file")
        guard(); absent(destination)
        renamed = ftp.rename(partial, destination)
        if not isinstance(renamed, str) or not renamed.startswith("250 "):
            raise ValueError("Positive FTP rename completion is required")
        if ftp.size(destination) != row["bytes"]: raise ValueError("Published remote split size differs")
        if time.monotonic() >= started + timeout_seconds:
            raise TimeoutError("Model file publication deadline exceeded")
        result = dict(schema="ps5-qwen-model-file-transfer-v1", source=str(source), original=row,
            destination=destination, source_stream_SHA_verified=True, source_identity_stable=True,
            FTP_226=True, FTP_250=True, remote_size_verified=True, world_readable=True,
            native_SHA_verified=False, state="awaiting_native_SHA_admission",
            elapsed_seconds=time.monotonic() - started, automatic_retries=0, GPU_calls=0)
        exclusive_json(complete, result)
        return result
    except BaseException as error:
        exclusive_json(failure, dict(error_type=type(error).__name__,
            remote_state="retained_for_review", automatic_retries=0,
            native_SHA_verified=False, delete_calls=0, GPU_calls=0))
        raise
