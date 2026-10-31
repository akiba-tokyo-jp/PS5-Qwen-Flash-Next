# SPDX-License-Identifier: MIT
"""Retire the completed upload's file cache before mandatory native hashing."""
import json,re,subprocess,sys
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]

def prepare_closed_upload(capture,remote,out,lan):
 out=Path(out);intent=json.loads((out/'intent.json').read_text());returned=json.loads((out/'transfer-returned.json').read_text())
 require(intent['SELF']==capture and intent['remote']==remote and returned['FTP_completed']and returned['bytes']==capture['bytes']and returned['sha256']==capture['sha256'],'Exact completed owned transfer required')
 build=out/'cache-control-build';template=out.parent/'fresh-current/build/manifest.private.json'
 command=[sys.executable,'-X','utf8','-B',str(ROOT/'tools/build_closed_pack_cache_reclaim.py'),'--template',str(template),'--pending-upload',str(out/'intent.json'),'--out',str(build)]
 result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180);(out/'cache-control-build.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-2000:])
 manifest=json.loads((build/'manifest.private.json').read_text())
 for row in manifest['inputs']+[manifest['artifact']]:require(record(row['path'])==row,'Cache control source changed')
 raw=lan.execute_once(manifest['artifact']['path'],manifest['artifact']['sha256'],manifest['argument'],manifest['remote_elf'],manifest['remote_log'],out/'cache-control',60)
 require(b'END success=1'in raw and ('nonce='+manifest['nonce']).encode()in raw and b'PENDING_SELF_FLUSH returned=1 rc=0 errno=0'in raw and b'PACK_CACHE_INVALIDATE returned=1 rc=0 errno=0'in raw and b'virtual_mapping_released=1 descriptor_closed=1 sealed_identity_unchanged=1'in raw,'Positive file synchronization, cache invalidation and own mapping retirement required')
 rows=[dict(re.findall(r'(\w+)=([^ ]+)',x))for x in raw.decode().splitlines()if x.startswith('PACK_CACHE_MEMORY')]
 require(len(rows)==5 and all(x['queries_ok']=='1'for x in rows),'Complete actual memory observations required')
 write_json(out/'cache-control-complete.private.json',dict(completed=True,manifest=record(build/'manifest.private.json'),raw=record(out/'cache-control/console.private.log'),memory=rows,
  observed_free_page_change=int(rows[-1]['free'])-int(rows[0]['free']),source_write_calls=0,GPU_calls=0,OS_counter_writes=0,mandatory_native_integrity_still_required=True))

def bind_pending_cache_control(source):
 marker='    def verify_native(candidate,remote):\n'
 require(source.count(marker)==1,'One exact pending native verifier required')
 return source.replace(marker,marker+'        from self_upload_cache import prepare_closed_upload\n        prepare_closed_upload(candidate,remote,R/\'pending-SELF-upload\',lan)\n')
