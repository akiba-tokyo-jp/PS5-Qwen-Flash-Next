#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check and build a bounded synthetic CPU probe with the exact native SHA object."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from build_model_directory import QUALIFIED_SOURCE, QUALIFIED_COMMAND_TEMPLATE, command_template, record
from model_transport import exclusive_json
from transfer_model import ROOT, bounded_json, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("workspace","cache","qualified_reference","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    a=p.parse_args();workspace=a.workspace.resolve();cache=a.cache.resolve();out=a.out.resolve()
    reference_path=a.qualified_reference.resolve();reference=reference_path.parent;old=bounded_json(reference_path)
    if (not reference_path.is_relative_to(cache) or sha(old["source_path"])!=QUALIFIED_SOURCE or
        command_template(old["commands"],reference,workspace)!=QUALIFIED_COMMAND_TEMPLATE):
        raise ValueError("The exact qualified CPU build recipe is required")
    if not out.is_relative_to(cache):raise ValueError("A fresh data-disk build directory is required")
    link_path=cache / "build/application-native/receipt.private.json";linked=bounded_json(link_path,8<<20)
    if linked["artifact"]["sha256"]!="78b087402539d0551067e1494965d6fa43fd96f4d0e6373aba60c82442478768":
        raise ValueError("The physically qualified original SHA provider reference is required")
    wrapper=ROOT / "native/app/sha256_backend.cpp"
    original_sources=[row for row in linked["application_sources"] if Path(row["path"]).resolve()==wrapper]
    if len(original_sources)!=1 or sha(wrapper)!=original_sources[0]["sha256"]:
        raise ValueError("The qualified SHA provider wrapper changed")
    commands=[command for command in linked["compile_commands"] if "-c" in command and
        Path(command[command.index("-c")+1]).resolve()==wrapper]
    if len(commands)!=1:raise ValueError("The exact existing SHA provider object is required")
    provider=Path(commands[0][commands[0].index("-o")+1])
    originals=[row for row in linked["inputs_before"] if Path(row["path"]).resolve()==provider.resolve()]
    if len(originals)!=1 or sha(provider)!=originals[0]["sha256"]:
        raise ValueError("The physically linked SHA provider object changed")
    lock=bounded_json(ROOT / "native/qwen_flash_next/dependencies.lock.json")
    upstream=cache / "upstream" / ("llama.cpp-"+lock["llama_cpp"]["revision"])
    hash_sources=[upstream / "vendor/hash" / name for name in ("sha256/sha256.c","sha256/sha256.h","sha256/LICENSE","rotate-bits/rotate-bits.h")]
    for path in hash_sources:
        prior=[row for row in linked["application_headers"] if Path(row["path"]).resolve()==path.resolve()]
        if len(prior)!=1 or sha(path)!=prior[0]["sha256"]:
            raise ValueError("The unchanged qualified public-domain SHA source is required")
    out.mkdir(parents=True,exist_ok=False);(out / "tmp").mkdir()
    nonce=secrets.token_hex(16);log="/data/ai/moss-qwen-cpu-hash-"+nonce+".log"
    digest=hashlib.sha256(bytes(range(256))*4096).hexdigest()
    header=out / "model_hash_probe_context.h"
    header.write_text('#define PROBE_NONCE '+json.dumps(nonce)+'\n#define PROBE_LOG_PATH '+json.dumps(log)+
        '\n#define PROBE_SHA256 '+json.dumps(digest)+'\n',newline="\n")
    source=ROOT / "native/qwen_flash_next/model_hash_probe.c";test=ROOT / "tests/model_hash_probe.c"
    stub=ROOT / "tests/stubs/model_hash_probe_stubs.h"
    native=[value.replace(str(reference),str(out)) for value in old["commands"][0]]
    native[native.index("-c")+1]=str(source);native_object=out / "model-hash-probe.o"
    native[native.index("-o")+1]=str(native_object);native += ["-I",str(upstream / "vendor")]
    artifact=out / "model-hash-probe.elf"
    link=[value.replace(str(reference),str(out)) for value in old["commands"][1]]
    link[link.index("-o")+1]=str(artifact)
    prior_object=Path(old["commands"][0][old["commands"][0].index("-o")+1])
    new_object=next(i for i,value in enumerate(link) if Path(value).name==prior_object.name)
    link[new_object]=str(native_object);link.insert(new_object+1,str(provider))
    host=workspace / "toolchain/msys-clang64/clang64/bin";executable=out / "model-hash-host.exe"
    host_command=[str(host / "clang.exe"),"-std=c11","-O2","-Wall","-Wextra","-Werror",
        "-I",str(ROOT / "tests/stubs"),"-I",str(upstream / "vendor"),"-I",str(upstream / "vendor/hash"),"-I",str(out),
        str(test),str(hash_sources[0]),"-o",str(executable)]
    modules=[Path(row["path"]) for row in linked["inputs_before"] if row["path"].endswith(".so") and
        not Path(row["path"]).name.endswith("_stub_weak.so")]
    inputs=[reference_path,link_path,source,test,stub,header,wrapper,provider,prior_object,
        Path(native[0]),Path(link[0]),Path(host_command[0]),*hash_sources,*modules]
    inputs += [Path(value) for value in link[1:] if value.endswith((".o",".a")) and Path(value).exists()]
    if "-T" in link:inputs.append(Path(link[link.index("-T")+1]))
    before=[record(path) for path in inputs]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get("PATH",""),TMP=str(out / "tmp"),TEMP=str(out / "tmp"))
    for name,command in (("host-compile",host_command),("host-API",[str(executable)]),
                         ("native-compile",native),("native-link",link)):
        result=subprocess.run(command,capture_output=True,env=env,timeout=120)
        (out / (name+".private.log")).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError("CPU hash probe check/build failed: "+name)
    llvm=Path(native[0]).parent;nm=llvm / "llvm-nm.exe";readelf=llvm / "llvm-readelf.exe"
    required=subprocess.check_output([str(nm),"-D","--undefined-only","--format=posix",str(artifact)],text=True,timeout=30)
    names={line.split()[0] for line in required.splitlines() if line.split()}
    if any(re.search(r"(sceAgc|sceSystemService|ptrace|mmap|mprotect|kernel_set_|kernel_copy|chown|chmod|setuid|seteuid)",name) for name in names):
        raise ValueError("The CPU hash probe added an out-of-scope operation")
    exports={}
    for module in modules:
        prior=next(row for row in linked["inputs_before"] if Path(row["path"]).resolve()==module.resolve())
        if sha(module)!=prior["sha256"]:raise ValueError("An actual runtime provider changed")
        dynamic=subprocess.check_output([str(readelf),"--dynamic",str(module)],text=True,timeout=30)
        soname=re.search(r"Library soname: \[([^\]]+)\]",dynamic)[1]
        if soname not in linked["runtime_providers"]:continue
        output=subprocess.check_output([str(nm),"-D","--defined-only","--format=posix",str(module)],text=True,timeout=30)
        for line in output.splitlines():
            if line.split():exports.setdefault(line.split()[0],soname)
    if names-exports.keys():raise ValueError("The actual qualified runtime modules do not export every CPU probe import")
    (out / "dynamic-imports.private.txt").write_text(required)
    if before!=[record(path) for path in inputs]:raise ValueError("A CPU hash probe build input changed")
    exclusive_json(out / "manifest.private.json",dict(schema="ps5-qwen-cpu-hash-probe-v1",nonce=nonce,
        artifact=record(artifact),object=record(native_object),header=record(header),source=record(source),
        exact_native_SHA_object=record(provider),unchanged_SHA_provider=True,source_inputs=before,
        commands=[host_command,native,link],remote_log=log,remote_elf=log.removesuffix(".log")+".elf",
        argument="--cpu-hash",buffer_bytes=1<<20,maximum_passes=512,synthetic_sha256=digest,
        target_elapsed_ns=10000000000,deadline_ns=15000000000,
        actual_runtime_imports={name:exports[name] for name in sorted(names)},missing_runtime_imports=[],
        only_synthetic_memory=True,disk_IO_measured=False,console_access=False,title_launches=0,GPU_calls=0,
        input_hashes_stable=True))
    print(json.dumps(dict(CPU_hash_probe="built",host_API_checks="passed",exact_native_SHA_object=True,
        actual_runtime_imports=len(names),console_access=False,title_launches=0,GPU_calls=0)))


if __name__=="__main__":main()
