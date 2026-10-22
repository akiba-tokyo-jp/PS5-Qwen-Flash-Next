#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain structurally complete GGUF splits without re-materializing their tensors.

This is a writer adapter, not model admission. The caller must positively stop
the old writer, bind unchanged original sources and independently audit every
retained/new tensor plus all final file hashes before publishing a receipt.
No previous output is overwritten or removed.
"""
import hashlib
import io
import os
from pathlib import Path
import re
import stat


def identity(path):
    value = Path(path).stat()
    return dict(device=value.st_dev, inode=value.st_ino, bytes=value.st_size,
        modified_ns=value.st_mtime_ns, created_ns=value.st_ctime_ns)


class BoundedHeader(io.BytesIO):
    def write(self, data):
        if self.tell() + len(data) > 32 << 20:
            raise ValueError("The generated GGUF split header exceeds its fixed bound")
        return super().write(data)


def install(writer_class, states, previous, destination, persist):
    previous, destination = Path(previous), Path(destination)
    if previous.is_symlink() or destination.is_symlink():
        raise ValueError("Resume directories must not be symlinks")
    previous, destination = previous.resolve(), destination.resolve()
    if previous == destination or not previous.is_dir() or not destination.is_dir():
        raise ValueError("Distinct existing original/new output directories are required")
    if any(destination.iterdir()):
        raise ValueError("Resume output must be a fresh empty directory")
    original_open, original_write = writer_class.open_output_file, writer_class.write_tensors_to_file
    outcome = dict(retained=[], written=[], retained_tensors=[], written_tensors=[],
        retained_payload_bytes=0, newly_written_payload_bytes=0, all_splits_written=False)
    opened = False
    payload_handles = []

    def open_output(self, path=None):
        nonlocal opened
        if opened or self.fout is not None or self.state != states.NO_FILE or self.dry_run:
            raise ValueError("Exactly one ordinary GGUF writer is admitted for a resumed text conversion")
        if path is not None: self.path = path
        paths = self.print_plan()
        if not 1 <= len(paths) <= 256 or len(paths) != len(self.tensors):
            raise ValueError("The complete bounded original split plan is required")
        for name in paths:
            candidate = Path(name).resolve()
            if candidate.parent != destination or not re.fullmatch(r"[A-Za-z0-9_.-]+\.gguf", candidate.name):
                raise ValueError("A resumed split escaped its exact output directory")
        self._qwen_resume_paths = paths
        self.fout = [BoundedHeader() for _ in paths]
        self.state = states.EMPTY; opened = True

    def write_tensors_impl(self, *, progress=False):
        del progress
        if not opened or self.temp_file is not None or self.state != states.KV_DATA:
            raise ValueError("The unchanged in-memory lazy tensor writer is required")
        self.write_ti_data_to_file()
        if sum(fp.tell() for fp in self.fout) > 64 << 20:
            raise ValueError("Aggregate split headers exceed their fixed memory bound")
        for index, (header_file, tensors, target) in enumerate(zip(list(self.fout), self.tensors, self._qwen_resume_paths), 1):
            self.write_padding(header_file, header_file.tell())
            header = header_file.getvalue()
            expected_size = len(header) + sum(self.ggml_pad(ti.nbytes, self.data_alignment) for ti in tensors.values())
            old = previous / Path(target).name
            retained = False; before = None
            if old.exists():
                if old.is_symlink() or not stat.S_ISREG(old.stat(follow_symlinks=False).st_mode):
                    raise ValueError("A prior GGUF split is not a regular original output")
                before = identity(old)
                if before["bytes"] == expected_size:
                    with old.open("rb") as source:
                        retained = source.read(len(header)) == header
                if identity(old) != before:
                    raise ValueError("A previous output changed during resume classification")
            payload = sum(ti.nbytes for ti in tensors.values())
            if retained:
                # Same-volume hard links avoid copying hundreds of gigabytes.
                # Retained payload fidelity is still entirely unadmitted here.
                os.link(old, target)
                after = identity(old)
                if any(after[key] != before[key] for key in ("device", "inode", "bytes", "modified_ns")):
                    raise ValueError("Retained GGUF payload identity changed while linking")
                output = Path(target).open("rb"); output.seek(expected_size)
                payload_handles.append(output)
                outcome["retained"].append(dict(path=str(target), source=str(old), bytes=expected_size,
                    header_sha256=hashlib.sha256(header).hexdigest(), source_identity_before_link=before,
                    source_identity_after_link=after, payload_audited=False))
                outcome["retained_tensors"].extend(tensors)
                outcome["retained_payload_bytes"] += payload
                for ti in tensors.values(): ti.tensor = None
            else:
                output = Path(target).open("xb"); payload_handles.append(output); output.write(header)
                for name, ti in tensors.items():
                    if ti.tensor is None or ti.tensor.nbytes != ti.nbytes:
                        raise ValueError("A new original tensor escaped its planned byte count")
                    start = output.tell(); ti.tensor.tofile(output)
                    if output.tell() - start != ti.nbytes:
                        raise ValueError("A resumed original tensor did not complete its exact byte count")
                    self.write_padding(output, ti.nbytes); ti.tensor = None
                    outcome["written_tensors"].append(name)
                output.flush(); os.fsync(output.fileno())
                if output.tell() != expected_size or Path(target).stat().st_size != expected_size:
                    raise ValueError("A resumed GGUF split has an incomplete final size")
                outcome["written"].append(dict(path=str(target), bytes=expected_size, payload_audited=False))
                outcome["newly_written_payload_bytes"] += payload
            header_file.close(); self.fout[index - 1] = output
            persist(dict(split=index, splits=len(self.fout), retained=retained,
                retained_payload_bytes=outcome["retained_payload_bytes"],
                newly_written_payload_bytes=outcome["newly_written_payload_bytes"]))
        self.state = states.WEIGHTS; outcome["all_splits_written"] = True

    def write_tensors(self, *, progress=False):
        # A failed host conversion must release its file handles before the
        # caller records failure. Keep every partial file for inspection.
        try:
            return write_tensors_impl(self, progress=progress)
        except BaseException:
            for handle in [*(self.fout or []), *payload_handles]:
                handle.close()
            raise

    writer_class.open_output_file, writer_class.write_tensors_to_file = open_output, write_tensors
    def restore():
        writer_class.open_output_file, writer_class.write_tensors_to_file = original_open, original_write
    return outcome, restore
