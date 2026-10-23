# SPDX-License-Identifier: MIT
"""Keep the SDK runtime intact except its payload-only mmap/mprotect member."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from model_transport import exclusive_json
from native_driver import read_archive

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def title_libc(original,out,ar):
    original=Path(original).resolve();out=Path(out).resolve();ar=Path(ar).resolve()
    source_sha=digest(original);tool_sha=digest(Path(__file__))
    folder=out/('libc-title-'+source_sha[:16]+'-'+tool_sha[:12]);artifact=folder/'libc.title.a'
    before=read_archive(original)
    removed=[key for key in before if key[0]=='mman.o']
    if removed!=[('mman.o',0)]:raise ValueError('One exact SDK mman.o member is required')
    expected={key:row['sha256'] for key,row in before.items() if key!=removed[0]}
    recipe=dict(original_path=str(original),original_sha256=source_sha,tool_sha256=tool_sha,
        archiver_path=str(ar),archiver_sha256=digest(ar),removed_member='mman.o',
        reason='Native titles import mmap from libkernel; SDK mman.o executes payload syscalls')
    if folder.exists():
        value=json.loads((folder/'complete.private.json').read_text())
        if value['recipe']!=recipe or value['sha256']!=digest(artifact):raise ValueError('The completed native runtime changed')
    else:
        folder.mkdir(parents=True);exclusive_json(folder/'intent.private.json',recipe)
        shutil.copyfile(original,artifact)
        result=subprocess.run([str(ar),'d',str(artifact),'mman.o'],capture_output=True,timeout=60)
        (folder/'archiver.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Native SDK runtime preparation failed')
        after=read_archive(artifact)
        if {key:row['sha256'] for key,row in after.items()}!=expected:raise ValueError('An unrelated SDK archive member changed')
        exclusive_json(folder/'complete.private.json',dict(recipe=recipe,sha256=digest(artifact),members_retained=len(after),
            all_other_member_occurrences_identical=True,console_access=False))
    if {key:row['sha256'] for key,row in read_archive(artifact).items()}!=expected:raise ValueError('Native SDK member preservation failed')
    return artifact,dict(path=str(folder/'complete.private.json'),sha256=digest(folder/'complete.private.json'),
        source_sha256=source_sha,members_retained=len(expected),payload_mmap_member_removed=True)
