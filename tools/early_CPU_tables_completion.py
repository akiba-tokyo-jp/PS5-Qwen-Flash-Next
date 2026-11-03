#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recognize only the source-bound returned pre-application CPU table failure."""
from pathlib import Path
import re
from native_dispatch import ELF
from start_success_route import need

FATAL=b'fatal_operation=early_CPU_tables_returned_failure_before_original_CXX_GPU_not_started\n'


def review(raw,image):
    need(raw.endswith(FATAL) and b'CXX_initializers_completed' not in raw and
        all(marker not in raw for marker in (b'configuration_read',b'model_mapping_',b'native_GPU_initialize',b'inference_before_')),
        'Only the exact returned failure before original application constructors is admitted')
    entered=[(int(i,16),int(p,16)) for i,p in re.findall(rb'initializer_enter index=0x([0-9a-f]+) address=0x([0-9a-f]+)',raw)]
    returned=[(int(i,16),int(p,16)) for i,p in re.findall(rb'initializer_return index=0x([0-9a-f]+) address=0x([0-9a-f]+)',raw)]
    need([i for i,_ in entered] in ([0,1,2],[0,1,2,3]) and returned==entered[:-1],
        'Only original platform initialization and a parked returned CPU prelude may exist')
    elf=image if isinstance(image,ELF) else ELF(Path(image));names=('__cpu_indicator_init','_GLOBAL__I_000100','early_CPU_tables_map','early_CPU_tables_check')
    base=entered[0][1]-elf.symbols[names[0]]['value']
    need(base>0 and base%16384==0 and all(address==base+elf.symbols[names[index]]['value'] for index,address in entered),
        'Every observed initializer must belong to the exact accepted native image')
    rows=re.findall(rb'early_CPU_tables_returned status=(\d+) mapped=(\d) zeroed=(\d) checksum=(\d) mapping_bytes=(\d+) allocation_bytes=(\d+) minimum_free=(\d+) CPU_IO_returned=1 model_GPU_calls=0\n',raw)
    need(len(rows)==len(entered)-2,'Every returned prelude boundary must be present exactly once')
    status,mapped,zeroed,checksum,mapping,allocation,minimum=map(int,rows[-1])
    need(1<=status<=6 and mapped in (0,1) and zeroed<=mapped and checksum==0 and
        mapping in (0,9502720) and allocation in (0,9502720) and mapping<=allocation and 0<=minimum<=138739,
        'Exact returned CPU status and retained application-owned allocation geometry required')
    if len(rows)==2:need(int(rows[0][0])==0 and status==6 and mapped==zeroed==1,'Only the subsequent zero-check failure is admitted')
    return dict(completed=True,active_initializer=entered[-1][0],status=status,load_base=base,
        mapped_CPU_bytes=mapping,allocated_CPU_bytes=allocation,all_CPU_operations_returned=True,
        source_payload_IO=0,application_CXX_initializers_started=0,model_GPU_calls=0)
