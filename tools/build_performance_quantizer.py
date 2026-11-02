#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build only the pinned host quantization reference; never evaluate a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def record(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('workspace', 'upstream', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = args.out / 'source'
    source.mkdir()
    # A parent project avoids standalone packaging of an unneeded ggml.pc file.
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.18)\nproject(qwen_quantization_reference C CXX ASM)\n'
        'add_subdirectory(' + json.dumps(str(args.upstream / 'ggml').replace('\\', '/')) + ' ggml)\n',
        encoding='utf-8', newline='\n')
    cmake = args.workspace / 'toolchain/pydeps/cmake/data/bin/cmake.exe'
    tools = args.workspace / 'toolchain/msys-clang64/clang64/bin'
    build = args.out / 'build'
    command = [str(cmake), '-S', str(source), '-B', str(build), '-G', 'Ninja',
               '-DCMAKE_MAKE_PROGRAM=' + str(args.workspace / 'toolchain/pydeps/bin/ninja.exe'),
               '-DCMAKE_C_COMPILER=' + str(tools / 'clang.exe'),
               '-DCMAKE_CXX_COMPILER=' + str(tools / 'clang++.exe'),
               '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON', '-DGGML_CPU=OFF',
               '-DGGML_VULKAN=OFF', '-DGGML_OPENMP=OFF', '-DGGML_NATIVE=OFF', '-DGGML_CCACHE=OFF',
               '-DGGML_BUILD_TESTS=OFF', '-DGGML_BUILD_EXAMPLES=OFF']
    jobs = [command, [str(cmake), '--build', str(build), '--target', 'ggml-base', '--parallel', '4']]
    environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ.get('PATH', ''))
    for i, job in enumerate(jobs):
        with (args.out / f'{i}.private.log').open('xb') as stream:
            result = subprocess.run(job, stdout=stream, stderr=subprocess.STDOUT, timeout=600, env=environment)
        if result.returncode:
            raise RuntimeError(f'Quantizer build failed; inspect {args.out / str(i)}.private.log')
    libraries = list(build.rglob('ggml-base.dll'))
    assert len(libraries) == 1
    inputs = [args.upstream / 'ggml/src/ggml-quants.c', args.upstream / 'ggml/src/ggml-common.h',
              args.upstream / 'ggml/src/ggml.c', args.upstream / 'ggml/include/ggml.h', Path(__file__)]
    manifest = dict(completed=True, purpose='weight_quantization_and_offline_numerics_only',
                    commands=jobs, library=record(libraries[0]), inputs=[record(p) for p in inputs],
                    host_model_inference=False, console_operations=0, production_adopted=False)
    (args.out / 'manifest.private.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(quantization_reference_built=True, model_inference=False)), flush=True)


if __name__ == '__main__':
    main()
