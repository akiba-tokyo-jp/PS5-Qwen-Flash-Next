#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit real static Vulkan callback values, without executing native code."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from driver_inputs import sha

REQUIRED = ("GetPhysicalDeviceProperties2", "GetPhysicalDeviceMemoryProperties",
            "GetPhysicalDeviceQueueFamilyProperties", "GetPhysicalDeviceProperties",
            "GetPhysicalDeviceExternalSemaphoreProperties", "GetPhysicalDeviceFeatures2")


class ELF:
    def __init__(self, path):
        if not 64 <= path.stat().st_size <= 512 << 20:
            raise ValueError("Native ELF size is outside the audit bound")
        self.data = path.read_bytes()
        if self.data[:7] != b"\x7fELF\x02\x01\x01" or struct.unpack_from("<H", self.data, 18)[0] != 62:
            raise ValueError("The audit requires little-endian x86-64 ELF")
        offset = struct.unpack_from("<Q", self.data, 40)[0]
        size, count = struct.unpack_from("<HH", self.data, 58)
        if size != 64 or not 0 < count <= 4096:
            raise ValueError("Unsupported ELF section table")
        self.sections = [struct.unpack("<IIQQQQIIQQ", self.read(offset + i * size, size)) for i in range(count)]
        self.symbols = {}
        symbol_tables = {}
        for index, section in enumerate(self.sections):
            if section[1] not in (2, 11):
                continue
            if section[9] != 24 or section[5] % 24 or section[5] > 48 << 20:
                raise ValueError("Invalid native symbol table")
            strings = self.section_data(self.sections[section[6]])
            rows = []
            for at in range(section[4], section[4] + section[5], 24):
                name, info, other, shndx, value, length = struct.unpack("<IBBHQQ", self.read(at, 24))
                end = strings.find(b"\0", name)
                if end < name:
                    raise ValueError("Unterminated ELF symbol name")
                row = dict(name=strings[name:end].decode("utf-8"), section=shndx, value=value, size=length)
                rows.append(row)
                if section[1] == 2 and shndx:
                    self.symbols[row["name"]] = row
            symbol_tables[index] = rows
        self.relocations = {}
        for section in self.sections:
            if section[1] != 4:
                continue
            if section[9] != 24 or section[5] % 24:
                raise ValueError("Invalid ELF relocation table")
            for at in range(section[4], section[4] + section[5], 24):
                address, info, addend = struct.unpack("<QQq", self.read(at, 24))
                kind, index = info & 0xffffffff, info >> 32
                if kind == 8 and index == 0:
                    self.relocations[address] = addend
                elif kind == 1:
                    symbol = symbol_tables[section[6]][index]
                    self.relocations[address] = symbol["value"] + addend if symbol["section"] else 0
                else:
                    self.relocations[address] = None

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset > len(self.data) - size:
            raise ValueError("Native ELF range is incomplete")
        return self.data[offset:offset + size]

    def section_data(self, section):
        if section[1] == 8:
            raise ValueError("A file-backed section is required")
        return self.read(section[4], section[5])

    def symbol_data(self, name):
        symbol = self.symbols[name]
        section = self.sections[symbol["section"]]
        return self.read(section[4] + symbol["value"] - section[3], symbol["size"])

    def pointer(self, address):
        if address in self.relocations:
            if self.relocations[address] is None:
                raise ValueError("Unsupported relocation on a required dispatch pointer")
            return self.relocations[address]
        for section in self.sections:
            if section[1] != 8 and section[3] <= address and address + 8 <= section[3] + section[5]:
                return struct.unpack("<Q", self.read(section[4] + address - section[3], 8))[0]
        raise ValueError("Native dispatch pointer is not file backed")


def audit(workspace, driver_root, image, out):
    receipt = out / "receipt.private.json"
    if receipt.is_file():
        previous = json.loads(receipt.read_text())
        if (previous.get("audit_tool_sha256") != sha(Path(__file__)) or
            previous.get("image_sha256") != sha(image) or
            any(sha(Path(p)) != digest for p, digest in previous.get("layout_inputs", {}).items())):
            raise ValueError("Immutable static-dispatch audit inputs changed")
        return previous
    out.mkdir(parents=True, exist_ok=False)
    database = workspace / "build/gpu_probe/radv-ps5-windows/compile_commands.json"
    rows = json.loads(database.read_text())
    recipe, = [r for r in rows if r["file"].replace("\\", "/").endswith("vk_common_entrypoints.c")]
    sys.path.insert(0, str(driver_root / "driver/mesa"))
    from build_idle_marker import windows_argv
    command = windows_argv(recipe["command"])
    compiler = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe"
    command[0] = str(compiler)
    if "--target=x86_64-sie-ps5" not in command:
        raise ValueError("The actual native table layout recipe is required")
    source, obj = out / "dispatch-layout.c", out / "dispatch-layout.o"
    source.write_text('#include <stddef.h>\n#include <stdint.h>\n#include "vk_dispatch_table.h"\n'
        'const uint64_t qwen_dispatch_offsets[] = {\n' + ",\n".join(
            "offsetof(struct vk_physical_device_entrypoint_table," + name + ")" for name in REQUIRED) + '\n};\n')
    command[command.index("-c") + 1] = str(source)
    command[command.index("-o") + 1] = str(obj)
    for flag in ("-MF", "-MQ"):
        if flag in command:
            command[command.index(flag) + 1] = str(out / ("layout.d" if flag == "-MF" else "dispatch-layout.o"))
    header = workspace / "build/gpu_probe/radv-ps5-windows/src/vulkan/util/vk_dispatch_table.h"
    inputs = {str(p): sha(p) for p in (database, compiler, header, source)}
    result = subprocess.run(command, cwd=recipe["directory"], capture_output=True, timeout=120)
    (out / "compile.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Actual native dispatch layout compilation failed")
    if inputs != {p: sha(Path(p)) for p in inputs}:
        raise ValueError("Native dispatch layout inputs changed")
    layout = ELF(obj).symbol_data("qwen_dispatch_offsets")
    if len(layout) != 8 * len(REQUIRED):
        raise ValueError("Actual native callback layout is incomplete")
    offsets = struct.unpack("<" + "Q" * len(REQUIRED), layout)
    native = ELF(image)
    table = native.symbols.get("vk_common_physical_device_entrypoints")
    checks = []
    for name, offset in zip(REQUIRED, offsets):
        symbol = native.symbols.get("vk_common_" + name)
        valid_slot = table is not None and offset + 8 <= table["size"]
        target = native.pointer(table["value"] + offset) if valid_slot else 0
        checks.append(dict(callback=name, offset=offset, implementation_present=symbol is not None,
                           table_pointer_nonzero=target != 0,
                           table_matches_implementation=symbol is not None and target == symbol["value"]))
    report = dict(schema="ps5-qwen-native-dispatch-audit-v1", image_sha256=sha(image), audit_tool_sha256=sha(Path(__file__)),
                  passed=all(c["implementation_present"] and c["table_pointer_nonzero"] and
                             c["table_matches_implementation"] for c in checks),
                  required_physical_callbacks=checks, layout_inputs=inputs, compile_command=command,
                  layout_object_sha256=sha(obj), console_access=False, GPU_calls=0)
    (out / "receipt.private.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--driver-root", type=Path, required=True)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = audit(a.workspace, a.driver_root, a.image, a.out)
    print(json.dumps({"static_dispatch_passed": report["passed"], "callbacks": report["required_physical_callbacks"], "GPU_calls": 0}))
    raise SystemExit(0 if report["passed"] else 1)

if __name__ == "__main__":
    main()
