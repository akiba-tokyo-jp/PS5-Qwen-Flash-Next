#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen GPU-generated dispatch feasibility against the exact selected driver."""
import argparse,json,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--driver',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.driver,text=True).strip()
 require(revision=='872cc1264ad8ba5d6b888b092968fa5858a38c58','Exact selected driver revision required')
 source=a.driver/'driver/ps5vk_compute.c';s=source.read_text();start=s.index('ps5vk_CmdDispatchIndirect(');end=s.index('\n}',start)+2;body=s[start:end]
 required=['ps5vk_cmd_buffer_writes_range(cmd_buffer, address, command_bytes)','ps5vk_cmd_buffer_refuse(',
  'ps5vk_cmd_buffer_wait_submitted(cmd_buffer)','memcpy(counts, (const void *)(uintptr_t)address, command_bytes)',
  'ps5vk_dispatch(cmd_buffer, counts[0], counts[1], counts[2])']
 require(all(x in body for x in required),'Known indirect implementation changed; reassess rather than infer support')
 line=s[:start].count('\n')+1
 write_json(a.out,dict(completed=True,kind='selected_driver_indirect_dispatch_feasibility',driver_revision=revision,
  source=record(source),function='ps5vk_CmdDispatchIndirect',line=line,parameters_read_on_CPU_at_recording_time=True,
  same_command_buffer_GPU_written_arguments_explicitly_refused=True,GPU_generated_indirect_dispatch_not_available=True,
  proposed_indirect_variant='implementation-unavailable-on-selected-driver',physical_PS5_incapability_established=False,
  no_futile_native_refusal_probe_performed=True,driver_changed=False,PS5_operations=0,CI_runs=0,
  retest_condition='A qualified GPU-executed indirect dispatch implementation, or a separately designed fully predicated graph with correct state ownership.',
  fully_predicated_alternative='not yet implemented or natively validated; this screen does not establish its impossibility'))
 print(json.dumps(dict(completed=True,selected_driver_GPU_generated_indirect=False,physical_incapability_claimed=False,PS5_operations=0)))
if __name__=='__main__':main()
