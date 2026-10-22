#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Parse a complete bounded v2 stage capture; byte progress is not SHA admission.

The caller must bind the private journal to the exact admitted title/source and
owner. This module performs no network access, receipt admission or execution.
Only a separate final native integrity/mapping report can establish completion.
"""
import re

PROGRESS=re.compile(rb"model_file_integrity_progress file=(\d{1,3}) files=(\d{1,3}) verified_file_bytes=(\d{1,20}) file_bytes=(\d{1,20}) total_verified_bytes=(\d{1,20}) total_bytes=(\d{1,20}) elapsed_ms=(\d{1,20}) deadline_seconds=7200")
COMPLETED=re.compile(rb"model_file_integrity_completed file=(\d{1,3}) bytes=(\d{1,20}) total_verified_bytes=(\d{1,20}) SHA256_matched=1")


def integrity_progress(raw,expected_files,expected_bytes):
    if not isinstance(raw,bytes) or len(raw)>8<<20:
        raise ValueError("A bounded complete private stage capture is required")
    if (type(expected_files) is not int or not 0<expected_files<=256 or
        type(expected_bytes) is not int or not 0<expected_bytes<=512<<30):
        raise ValueError("Admitted file and byte totals are required")
    # A live read can end between writes. Only newline-terminated records count.
    lines=raw.split(b"\n")[:-1]
    active=0;file_bytes=0;file_hashed=0;hashed=0;confirmed=0;confirmed_bytes=0;elapsed=0;events=0
    for line in lines:
        if line.startswith(b"model_file_integrity_progress"):
            match=PROGRESS.fullmatch(line)
            if not match:raise ValueError("Malformed or legacy native integrity progress")
            index,files,count,size,total,maximum,time_ms=map(int,match.groups())
            if (files!=expected_files or maximum!=expected_bytes or not 1<=index<=files or
                not 0<size<=expected_bytes or not 0<=count<=size or total!=confirmed_bytes+count or
                total>expected_bytes or total<hashed or time_ms<elapsed or time_ms>(1<<63)-1):
                raise ValueError("Native integrity progress escaped admitted monotonic byte/time bounds")
            if index==active:
                if active<=confirmed or size!=file_bytes or count<file_hashed:
                    raise ValueError("A finished or changed native file was reused")
            elif index==confirmed+1 and (active==0 or active==confirmed):
                if count!=0:raise ValueError("Each admitted file must start with its zero progress record")
                active=index;file_bytes=size
            else:raise ValueError("Native integrity file sequencing skipped a SHA completion")
            file_hashed=count;hashed=total;elapsed=time_ms;events+=1
        elif line.startswith(b"model_file_integrity_completed"):
            match=COMPLETED.fullmatch(line)
            if not match:raise ValueError("Malformed or legacy native SHA completion")
            index,size,total=map(int,match.groups())
            if (index!=active or index!=confirmed+1 or file_hashed!=file_bytes or size!=file_bytes or
                total!=confirmed_bytes+size or total!=hashed or total>expected_bytes):
                raise ValueError("Native SHA completion does not match the preceding complete file")
            confirmed=index;confirmed_bytes=total
    return dict(schema="ps5-qwen-native-integrity-progress-v2",file_index=active,expected_files=expected_files,
        current_file_bytes=file_bytes,current_file_hashed_bytes=file_hashed,
        total_hashed_bytes=hashed,total_bytes=expected_bytes,elapsed_ms=elapsed,
        maximum_verification_seconds=7200,deadline_reached=elapsed>=7200000,
        SHA_matched_file_markers=confirmed,SHA_matched_bytes=confirmed_bytes,
        all_file_SHA_markers_seen=confirmed==expected_files and confirmed_bytes==expected_bytes,
        progress_events=events,final_native_integrity_and_mapping_reports_required=True,
        model_loaded=False,full_model_inference=False)
