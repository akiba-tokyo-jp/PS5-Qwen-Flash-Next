#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Require real linked destinations, and reject a preserved failed final image."""
import argparse,json
from pathlib import Path
from driver_table_storage import audit_linked_storage
from shader_storage import record
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('image','manifest','reject-image','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.manifest.read_text());good=audit_linked_storage(a.image,m)
    try:audit_linked_storage(a.reject_image,m)
    except ValueError as e:rejected=str(e)
    else:raise ValueError('The real failed final image was incorrectly admitted')
    a.out.mkdir(parents=True,exist_ok=False)
    result=dict(passed=True,actual_final_ELF_geometry=good,failed_final_ELF=record(a.reject_image),
        failed_final_ELF_rejected=True,rejection_reason=rejected,manifest=record(a.manifest),
        audit_source=record(Path(__file__).with_name('driver_table_storage.py')),PS5_operations=0)
    (a.out/'complete.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(actual_final_ELF_geometry_passed=True,table_count=good['table_count'],
        historical_empty_range_image_rejected=True,PS5_operations=0)))
if __name__=='__main__':main()
