#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the qualified new-only publisher ABI for an explicit precision overlay."""
from pathlib import Path

def main():
    path=Path(__file__).with_name('build_resident_all_q8_publication.py');text=path.read_text()
    def once(old,new):
        nonlocal text
        if text.count(old)!=1:raise ValueError('Exact publisher boundary required: '+old[:100])
        text=text.replace(old,new)
    once("prep['selected_tensors']==544", "prep['selected_tensors']in(48,96,108)")
    once("audit['resident_BF16_tensors_remaining']==1", "audit['all_unselected_tensor_payloads_shapes_and_types_unchanged']and audit['original_PLE_convolution_preserved']")
    once("receipt['resident_all_Q8_overlay']['headers']", "receipt['precision_overlay']['headers']")
    once(r'resident-all-Q8\.part[0-9]+\.bin',r'precision\.part[0-9]+\.bin')
    once("previous=[dict(path=parent_seal['pack']['path'],identity=parent_seal['pack']['identity']),dict(path=parent_seal['source_directory']+'/model-receipt.json',identity=parent_seal['receipt_identity']),*parent_seal['headers']]",
         "previous=[*parent_seal['parts'],dict(path=parent_seal['source_directory']+'/model-receipt.json',identity=parent_seal['receipt_identity']),*parent_seal['headers']]")
    once("inputs=[record(x) for x in (Path(__file__),", "inputs=[record(x) for x in (Path(__file__),Path(__file__).with_name('build_resident_all_q8_publication.py'),")
    namespace={'__file__':__file__,'__name__':'__main__'}
    exec(compile(text,__file__+'#qualified-CPU-publisher','exec'),namespace)

if __name__=='__main__':main()
