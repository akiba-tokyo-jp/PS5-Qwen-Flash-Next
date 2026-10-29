#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain normal ownership/stream/frame checks with the sealed I/O winner scope."""
import argparse,json,sys
from pathlib import Path
from expert_q4 import require,record
from build_expert_q2_io_monitor import monitor_scope
import observe_expert_q2_optimized_monitor as qualified
def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--IO-native-receipt',type=Path,required=True);a,remaining=p.parse_known_args()
 receipt=json.loads(a.IO_native_receipt.read_text());scope=receipt['all_Q2_optimized_monitor']['scope'];require(scope==monitor_scope(receipt['all_Q2_IO_normal']['flags']),'Exact scoped I/O winners required')
 require(receipt['input_hashes_stable']and receipt['native_dispatch_audit']['passed']and not receipt['real_module_import_audit']['missing'],'Qualified native inputs/dispatch required')
 selection=receipt['all_Q2_IO_normal']['selection'];require(record(selection['path'])==selection and json.loads(Path(selection['path']).read_text())['completed'],'Closed comparison selection required')
 qualified.SCOPE=scope;sys.argv=[sys.argv[0],*remaining];qualified.main()
if __name__=='__main__':main()
