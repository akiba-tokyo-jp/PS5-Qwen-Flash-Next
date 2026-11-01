#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Interpret observed APIs and lossless chunks without claiming model speedups."""
import argparse,json,re
from pathlib import Path

APR=('sceKernelAprResolveFilepathsToIds','sceKernelAprGetFileSize','sceKernelAprGetFileStat',
     'sceKernelAprSubmitCommandBuffer','sceKernelAprSubmitCommandBufferAndGetResult','sceKernelAprWaitCommandBuffer')
def fields(text,prefix):
    return[dict(re.findall(r'(\w+)=([^ ]+)',s))for s in text.splitlines()if s.startswith(prefix)]
def capability(text):
    if not re.search(r'^END .* success=1 current_file_hashes=6 ',text,re.M):raise ValueError('positive native completion required')
    symbols=fields(text,'SYMBOL ');modules=fields(text,'MODULE ')
    if len(symbols)!=14 or len(modules)!=3:raise ValueError('complete observed surface required')
    by_name={r['name']:r for r in symbols}
    kernel={name:any(by_name[name].get(k)=='1'for k in('SDK_found','kernel_web_found','kernel_found'))for name in APR}
    return dict(APR_symbols_resolved=kernel,all_APR_symbols_resolved=all(kernel.values()),
        module_handle_lookup_inconclusive=any(r['rc']=='-1'and r['errno']=='22'for r in modules),
        loaded_writer_symbols=sum(r.get('SDK_found')=='1'or r.get('AMPR_found')=='1'for r in symbols[8:]),
        symbol_presence_proves_callable_backend=False)
def paths(text):
    if not re.search(r'^END .* success=1 samples=16 ',text,re.M):raise ValueError('positive native sample completion required')
    rows=fields(text,'APR_RESOLVE ')
    if len(rows)!=3 or {r['index']for r in rows}!={'0','1','2'}or any(r['canaries']!='1'for r in rows):
        raise ValueError('three intact independent path results required')
    available=all(r['rc']=='0'for r in rows)
    unsupported=all(r['rc']=='-1'and r['errno']=='45'for r in rows)
    return dict(path_results=[{k:r[k]for k in('index','rc','errno','canaries')}for r in rows],
        current_paths_usable=available,current_path_backend_unsupported=unsupported,
        system_wide_hardware_absence_proven=False,APR_read_submissions=0,GPU_calls=0)
def chunks(rows):
    if not rows or len({r['sample']for r in rows})!=len(rows):raise ValueError('unique sample results required')
    if any(not r['round_trip_exact']or r['hardware_decoder_tested']for r in rows):raise ValueError('host-only exact round trips required')
    old=sum(r['original_padded_bytes']for r in rows);new=sum(r['padded_bytes']for r in rows)
    if not old or not new:raise ValueError('positive physical byte counts required')
    return dict(samples=len(rows),chunk_bytes=rows[0]['chunk'],original_padded_bytes=old,compressed_padded_bytes=new,
        raw_bytes=sum(r['logical_bytes']for r in rows),compressed_payload_bytes=sum(r['compressed_payload_bytes']for r in rows),
        physical_saving_percent=100*(1-new/old),decode_calls=sum(r['block_count']for r in rows),
        proposed_Expert_read_commands=sum(r['independent_Expert_read_commands']for r in rows),
        host_decode_ms=sum(r['host_decode_ms']for r in rows),all_round_trips_exact=True,
        ideal_sample_bandwidth_only_gain_percent=100*(old/new-1),PS5_decode_or_model_speed_measured=False)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capability-log',type=Path,required=True)
    p.add_argument('--path-log',type=Path,required=True);p.add_argument('--chunks',type=Path,nargs='+',required=True);a=p.parse_args()
    print(json.dumps(dict(capability=capability(a.capability_log.read_text()),path_test=paths(a.path_log.read_text()),
        chunk_tests=[chunks([json.loads(s)for s in f.read_text().splitlines()])for f in a.chunks]),indent=2))
if __name__=='__main__':main()
