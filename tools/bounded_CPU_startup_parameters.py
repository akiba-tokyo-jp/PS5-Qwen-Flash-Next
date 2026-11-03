#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bound only the separate full-link CPU startup fixture's private libc heap."""
import hashlib
import struct

from libc_parameter_policy import bind_heap
from native_libc_parameters import verify_data_only


def bind(control,heap_bytes):
    if type(heap_bytes) is not int or heap_bytes not in (4<<20,8<<20):
        raise ValueError('Only the separate4/8MiB full-link CPU startup experiments are admitted')
    bounded,layout=bind_heap(control,8<<20);output=bytearray(bounded)
    struct.pack_into('<Q',output,layout['heap_size_file_offset'],heap_bytes)
    struct.pack_into('<I',output,layout['heap_size_file_offset']+8,0)
    notes=[]
    for name,size,count in ((b'GNU\0',0x14,16),(b'SIE\0',8,8)):
        prefix=struct.pack('<III',4,size,3)+name
        if control.count(prefix)!=1:raise ValueError('One original build-ID note required')
        offset=control.index(prefix)+16;notes.append((offset,count));output[offset:offset+count]=bytes(count)
    digest=hashlib.sha1(output).digest()
    for offset,count in notes:output[offset:offset+count]=digest[:count]
    output=bytes(output);proof=verify_data_only(control,output,heap_bytes)
    proof.update(original_heap_size=(1<<64)-1,original_extension=1,selected_heap_size=heap_bytes,
        CPU_only_before_model_source_and_GPU=True,measured_kernel_memory_saving=False,
        universal_kernel_allocation_bound_claimed=False,model_launch_admission_granted=False)
    return output,proof
