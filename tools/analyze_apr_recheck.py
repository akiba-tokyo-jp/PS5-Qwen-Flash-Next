#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Separate title visibility, APR support, packet construction and actual I/O."""
import argparse,json,re
from pathlib import Path
def fields(text,prefix):
    return[dict(re.findall(r'(\w+)=([^ ]+)',s))for s in text.splitlines()if s.startswith(prefix)]
def analyze(text):
    begin=fields(text,'BEGIN ');end=fields(text,'END ');returned=fields(text,'RETURN ')
    if len(begin)!=1 or len(end)!=1 or len(returned)!=1 or begin[0]['nonce']!=end[0]['nonce']:
        raise ValueError('Matching native BEGIN, END and ordinary return required')
    if end[0]['success']!='1'or returned[0]['result']!='0'or returned[0]['ordinary_exit']!='1':raise ValueError('Native scope did not pass')
    if end[0]['APR_read_submits']!='0'or end[0]['GPU_calls']!='0':raise ValueError('This interpretation is for prerequisite-only observations')
    reads=fields(text,'POSIX_ACCESS ');resolved=fields(text,'RESOLVE ');writer=fields(text,'WRITER ')
    if len(reads)!=3 or len(resolved)!=3 or len(writer)!=1:raise ValueError('All three independent file roles required')
    if {r['index']for r in reads}!={'0','1','2'}or {r['index']for r in resolved}!={'0','1','2'}:raise ValueError('Unique file roles required')
    rows=[]
    for index in range(3):
        read=next(r for r in reads if r['index']==str(index));apr=next(r for r in resolved if r['index']==str(index))
        if apr['canaries']!='1'or apr['errno_measured']!='1':raise ValueError('Intact outputs and measured native errno required')
        visible=read['opened']=='1'and read['read_bytes']=='16'and read['close_rc']=='0'
        if index==1 and visible and read['control_bytes_exact']!='1':raise ValueError('Control bytes differ')
        rows.append(dict(role=('program','control','Expert')[index],ordinary_read_passed=visible,ordinary_read_bytes=int(read['read_bytes']),
            APR_return=int(apr['rc']),APR_errno=int(apr['errno']),APR_file_ID_valid=apr['rc']=='0'))
    w=writer[0]
    encoded=w['backend']=='public_source'and w['exact']=='1'and w['commands']=='2'and w['bytes']=='32'
    if not encoded:raise ValueError('Public command-construction observation did not pass')
    all_visible=all(r['ordinary_read_passed']for r in rows)
    unsupported=all_visible and all(r['APR_return']==-1 and r['APR_errno']==25 for r in rows)
    return dict(native_scope_passed=True,files=rows,all_three_files_visible=all_visible,
        readable_files_rejected_with_ENOTTY=unsupported,public_command_construction_passed=encoded,
        synthetic_ID_used=w['synthetic_ID']=='1',APR_read_submissions=0,GPU_calls=0,
        native_IO_speed_measured=False,model_tokens_per_second_measured=False,hardware_absence_proven=False)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);a=p.parse_args()
    print(json.dumps(analyze(a.log.read_text()),indent=2))
if __name__=='__main__':main()
