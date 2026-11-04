# SPDX-License-Identifier: MIT
"""Recover only the hash-bound current pure-C main-entry SELF reader."""
import ast
import hashlib
from pathlib import Path

from start_success_route import load,need

ROOT=Path(__file__).resolve().parents[1]


def generate(current):
    native=load(Path(current)/'provenance/native-link.receipt.private.json');selected=native['resident_main_SELF']
    template=ROOT/'native/app/resident_early_SELF.c';raw=template.read_text(encoding='utf-8').encode()
    need(len(raw)==selected['pure_C_template']['bytes'] and hashlib.sha256(raw).hexdigest()==selected['pure_C_template']['sha256'],
         'The selected pure-C template changed beyond working-tree line endings')
    generator=ROOT/'tools/build_main_SELF.py';tree=ast.parse(generator.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');prefix=[]
    for node in function.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='needle' for t in node.targets):break
        prefix.append(node)
    module=ast.Module(body=prefix,type_ignores=[]);ast.fix_missing_locations(module)
    namespace=dict(ROOT=ROOT,__file__=str(generator));exec(compile(module,str(generator)+'#source-only','exec'),namespace)
    source=namespace['source'];raw=source.encode();expected=selected['pure_C_source']
    need(len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256'],
         'The actual selected C reader must be reconstructed byte-for-byte')
    return source,selected
