#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Partition a growing rollback inventory without widening native read bounds."""
from build_preservation_integrity import MAX_FILE,MAX_TOTAL
def partition_closed_artifacts(rows):
 if not rows:raise ValueError('A nonempty exact closed-artifact inventory is required')
 paths=[r['remote_path']for r in rows]
 if len(set(paths))!=len(paths):raise ValueError('Every owned artifact must occur exactly once')
 result=[];batch=[];total=0
 for row in rows:
  size=row['capture']['bytes']
  if type(size)is not int or not 0<size<=MAX_FILE:raise ValueError('Original per-file bound must be retained')
  if batch and(total+size>MAX_TOTAL or len(batch)==64):result.append(batch);batch=[];total=0
  batch.append(row);total+=size
 result.append(batch)
 assert [r for b in result for r in b]==rows
 return result
