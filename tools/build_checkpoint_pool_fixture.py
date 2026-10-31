#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test growing device state with2MiB capacity buckets and reusable GGML arenas."""
from pathlib import Path
import build_checkpoint_device_fixture as base
from build_speculative_batch_probe import once
from expert_q4 import record
ROOT=Path(__file__).resolve().parents[1]
original_transform=base.transform;original_link=base.link;original_seal=base.seal
base.SCOPE=dict(base.SCOPE,capacity_bucket_bytes=2<<20,maximum_saved_capacity_bytes=136<<20,
               monotonically_growing_state=True,GGML_metadata_arena_and_vector_capacity_reuse=True)
def transform(text,fixture_api=False):
 text=original_transform(text,fixture_api).replace('#include "checkpoint_device_trial.h"','#include "checkpoint_device_pool_trial.h"')
 return once(text,'ggml_backend_alloc_ctx_tensors_from_buft(mbuf_cur.ctx.get(), buft)','qwen_checkpoint_trial::allocate(mbuf_cur,buft)')
def link(parent,out,variants,inputs):
 fixture=(ROOT/'native/app/checkpoint_device_fixture.h').read_text()
 fixture=once(fixture,'const auto bytes=event==1||event==2?small:large;',
     'const auto bytes=event<3?small+event*16384:large;')
 generated=out/'checkpoint_growing_fixture.private.h';generated.write_text(fixture,newline='\n')
 cmd,text=variants['entry'];variants['entry']=(cmd,text.replace('#include "checkpoint_device_fixture.h"','#include "checkpoint_growing_fixture.private.h"'))
 return original_link(parent,out,variants,[*inputs,Path(__file__),ROOT/'native/app/checkpoint_device_pool_trial.h',generated])
def seal(result,workspace,cache,out):
 result['checkpoint_device_fixture']['growing_pool']=dict(header=record(ROOT/'native/app/checkpoint_device_pool_trial.h'),fixture=record(out/'checkpoint_growing_fixture.private.h'),bucket_bytes=2<<20,original_136MiB_cap=True)
 original_seal(result,workspace,cache,out)
base.transform=transform;base.link=link;base.seal=seal
if __name__=='__main__':base.main()
