#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish only new compact headers for already sealed native Expert payloads."""
import json,sys
from pathlib import Path
from expert_q4 import require,record

def main():
    prep_path=Path(sys.argv[sys.argv.index('--preparation')+1]);prep=json.loads(prep_path.read_text());done=json.loads(Path(prep['native_generation']['path']).read_text())
    require(record(prep['native_generation']['path'])==prep['native_generation']and done['completed']and done['CPU_owners_positively_closed'],'Completed native data ownership required')
    text=Path(__file__).with_name('build_resident_all_q8_publication.py').read_text()
    def once(old,new):
        nonlocal text
        require(text.count(old)==1,'Exact metadata publisher boundary required: '+old[:100]);text=text.replace(old,new)
    once("prep['selected_tensors']==544","prep['selected_tensors']==96")
    once("audit['resident_BF16_tensors_remaining']==1","audit['all_native_output_whole_SHA256_and_EOF_passed']and audit['all_current_input_whole_SHA256_passed']and audit['all_unselected_tensor_payloads_shapes_and_types_unchanged']and audit['original_PLE_convolution_preserved']")
    once("receipt['resident_all_Q8_overlay']['headers']","receipt['precision_overlay']['headers']")
    once(r'resident-all-Q8\.part[0-9]+\.bin',r'precision\.part[0-9]+\.bin')
    once("local=[*prep['parts'],prep['candidate'],*local_headers]","host_parts=[row for row in prep['parts']if row.get('host_generated')];local=[*host_parts,prep['candidate'],*local_headers]")
    once("root=TITLE+'/expert-q2-'+nonce","root="+repr(done['new_directory']))
    once("previous=[dict(path=parent_seal['pack']['path'],identity=parent_seal['pack']['identity']),dict(path=parent_seal['source_directory']+'/model-receipt.json',identity=parent_seal['receipt_identity']),*parent_seal['headers']]",
         "previous=[*parent_seal['parts'],dict(path=parent_seal['source_directory']+'/model-receipt.json',identity=parent_seal['receipt_identity']),*parent_seal['headers'],*"+repr(done['parts'])+"]")
    marker="    actual=a.out/'publication.private.cpp';actual.write_text(source,newline='\\n')"
    extra="    expected_directory="+repr(done['directory_identity'])+"\n    identity_literal='{'+','.join(str(v)+'ULL'for v in expected_directory)+'}'\n"
    extra+="    source=once(source,'need(lstat(output_Q8_directory,&absent)&&errno==ENOENT,\\\"Fresh Q8 directory required\\\");','need(named(output_Q8_directory,true)==std::array<std::uint64_t,10>'+identity_literal+',\\\"Owned native repack directory changed\\\");')\n".replace('\\\"','"')
    extra+="    source=once(source,'need(!mkdir(output_Q8_directory,0755),\\\"Exclusive new Q8 directory creation failed\\\");const auto root=named(output_Q8_directory,true);','const auto root=named(output_Q8_directory,true);')\n".replace('\\\"','"')
    once(marker,extra+marker)
    once("part_count=len(prep['parts'])","part_count=len(host_parts),native_parts="+repr(done['parts'])+",native_generation=prep['native_generation']")
    once("inputs=[record(x) for x in (Path(__file__),","inputs=[record(x) for x in (Path(__file__),Path(__file__).with_name('build_resident_all_q8_publication.py'),Path(prep['native_generation']['path']),")
    exec(compile(text,__file__+'#bounded-metadata-publication','exec'),{'__file__':__file__,'__name__':'__main__'})

if __name__=='__main__':main()
