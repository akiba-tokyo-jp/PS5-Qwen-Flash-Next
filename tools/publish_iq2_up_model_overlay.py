#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish new IQ2 parts/headers while retaining already sealed selected parts."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import time
import urllib.parse
from build_performance_quantizer import record
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, complete, current_files, execute, lan_module


def verify_input(file):
    row=file['local']
    if 'encoder_completion' in file:
        marker=file['encoder_completion'];pack=Path(row['path'])
        need(record(marker['path'])==marker and load(marker['path'])['pack']==row and
             pack.stat().st_size==row['bytes'] and pack.stat().st_mtime_ns<=Path(marker['path']).stat().st_mtime_ns,
             'The completed immutable encoder payload changed before native whole-file sealing')
    else:
        need(record(row['path'])==row,'An exact publication input changed')


def finish(out, preparation, publication, result, native_result_path=None, source_handoff=None):
    prep = load(preparation)
    files = publication['files']
    raw = Path(result['raw']['path']).read_bytes()
    matches = re.findall(rb'SHARED_Q4_ID kind=(file|directory) index=(\d+) values=([0-9,]+)', raw)
    identities = {int(i): list(map(int, v.split(b','))) for kind, i, v in matches if kind == b'file'}
    directories = [list(map(int, v.split(b','))) for kind, i, v in matches if kind == b'directory' and i == b'0']
    count, parents = len(files), publication['parent_source_count']
    need(set(identities) == set(range(count)) and len(directories) == 1 and
         all(len(v) == 10 for v in identities.values()), 'Every newly sealed canonical identity is required')
    expected = ('SHARED_Q4_SEALED new_files=' + str(count) +
        ' complete_physical_and_alias_SHA256_EOF=1 parent_sources=' + str(parents) +
        ' parent_identities_and_directory_snapshots_unchanged=1 original_source_writes=0').encode()
    need(expected in raw and result['operation_calls'] == 2 * count + 2,
         'Every new file and unchanged selected parent must positively complete')
    observed = [dict(path=r['application'], bytes=r['local']['bytes'], sha256=r['local']['sha256'],
                     identity=identities[i]) for i, r in enumerate(files)]
    n = publication.get('new_part_count',len(prep['new_parts']))
    parts = publication['retained_parts'] + observed[:n]
    seal = dict(schema='ps5-qwen-precision-native-source-v1', completed=True,
        model_receipt_sha256=prep['candidate']['sha256'], parent_model_receipt_sha256=prep['parent_model_sha256'],
        selected_previous_model_sha256=prep['selected_model_sha256'], source_directory=publication['application_directory'],
        canonical_source_directory=publication['directory'], directory_identity=directories[0], receipt_identity=identities[n],
        parts=parts, headers=[dict(r, file=PurePosixPath(r['path']).name) for r in observed[n+1:]],
        all_new_parts_complete_Direct_SHA256_readback=True, all_parts_unchanged_since_readback=True,
        CPU_owners_positively_closed=True, all_original_sources_preserved=True, header_prefixes_extracted_and_sealed=True,
        previous_pack_and_receipt_identities_unchanged=True, GPU_calls=0, title_launches=0, automatic_retries=0,
        original_source_writes=0, production_permission_changes=0, mount_changes=0,
        retained_parts_reused_without_copy=True, selected_parent_source_count=parents)
    seal_path = out / 'source-integrity.private.json'
    save(seal_path, seal)
    text = seal_path.read_text()
    save(out / 'result.private.json', dict(completed=True, preparation=record(preparation), source_integrity=record(seal_path),
        policy=dict(schema='ps5-qwen-precision-source-policy-v1', raw=text, sha256=hashlib.sha256(text.encode()).hexdigest()),
        native_result=record(native_result_path or out / 'native/result.private.json'), new_files=count,
        source_window_handoff=record(source_handoff) if source_handoff else None,
        retained_parts=len(publication['retained_parts']), retained_parts_copied=0,
        whole_new_bytes_and_all_parent_identities_qualified=True, PS5_model_inference=False, production_adopted=False))
    print(json.dumps(dict(completed=True, new_files=count, retained_parts_copied=0, GPU_calls=0, title_launches=0)))


def submit(a, publication, plan):
    state = load(a.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'], 'Positive idle current ownership required')
    need(not state.get('CPU_source_seal_owner') and not state.get('source_publication_owner'),
         'The prior source IO owner must positively finish before a new publication')
    need(not (a.out / 'upload-intent.private.json').exists() and
         not (a.out / 'native/execution/execution.once.private.json').exists(), 'Never repeat an upload or native submission')
    files, root = publication['files'], publication['directory']
    lan = lan_module()
    state['source_publication_owner']=dict(publication=str(a.out),plan=record(a.out/'plan.private.json'),
        phase='whole-file-transfers',GPU_calls=0,title_launches=0)
    (a.current/'active-console.private.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    save(a.out / 'upload-intent.private.json', dict(files=files, directory=root, automatic_retries=0))
    lan.absent(root)
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST, 2121, timeout=30)
        ftp.login()
        need(ftp.sendcmd('SELF') == '226 SELF transfer mode disabled', 'Raw transfer mode required')
        reply = ftp.sendcmd('MKD ' + root)
        save(a.out / 'MKD-reply.private.json', dict(directory=root, reply=reply))
        need(reply.startswith(('226 ', '250 ', '257 ')), 'The new owned namespace creation must complete')
        for i, f in enumerate(files):
            verify_input(f)
            lan.absent(f['physical'])
            with Path(f['local']['path']).open('rb') as stream:
                reply = ftp.storbinary('STOR ' + f['physical'], stream, 65536)
            need(reply.startswith(('226 ', '250 ')), 'One complete new-file transfer required')
            print(json.dumps(dict(uploaded_file=i+1, total=len(files), bytes=f['local']['bytes'])), flush=True)
    try:
        result = execute(lan, plan, a.out / 'native')
    except RuntimeError:
        need(not (a.out / 'native/result.private.json').exists() and
             (a.out / 'native/execution/execution.once.private.json').exists(), 'Only collect the same durable native helper')
        deadline = time.monotonic() + 600
        while True:
            raw = lan.web('/fs' + urllib.parse.quote(plan['log'], safe='/'), 64 << 20)
            if re.search(rb'\nEND success=\d+ operation_calls=\d+ app_id=-?\d+ log_healthy=\d+ GPU_calls=0 initializer_requests=0 mount_calls=0\n$', raw):
                path = a.out / 'native/late-console.private.log'
                path.write_bytes(raw)
                result = complete(lan, plan, a.out / 'native', raw, path)
                break
            need(time.monotonic() < deadline, 'Same helper completion remains unknown; never resubmit')
            time.sleep(2)
    finish(a.out, a.preparation, publication, result)
    state=load(a.current/'active-console.private.json')
    need(state['source_publication_owner']['plan']==record(a.out/'plan.private.json'),'The exact source owner must retire')
    state.pop('source_publication_owner')
    (a.current/'active-console.private.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'preparation', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--collect', action='store_true')
    p.add_argument('--submit-prepared', action='store_true', help='Submit the exact prepared but never uploaded scope once')
    p.add_argument('--retained-Up-publication',type=Path,
        help='Reuse the sealed whole-weight prefix from a completed preparation without uploading it again')
    p.add_argument('--source-seal-window-proof',type=Path,
        help='Use the completed262KiB Direct integrity control for large new source sets')
    a = p.parse_args()
    need(sum((a.execute, a.collect, a.submit_prepared)) <= 1, 'One explicit publication phase required')
    if a.collect or a.submit_prepared:
        publication = load(a.out / 'plan.private.json')
        need(publication['preparation'] == record(a.preparation), 'The exact original IQ2 preparation is required')
        plan = load(a.out / 'native/plan.private.json')
        need(record(a.out / 'native/plan.private.json') == publication['native_plan'] and
             record(plan['artifact']['path']) == plan['artifact'], 'The exact prepared native scope must be unchanged')
        if a.submit_prepared:
            submit(a, publication, plan)
            return
        need((a.out / 'native/execution/execution.once.private.json').exists(), 'Collect only the same submitted helper')
        lan = lan_module()
        raw = lan.web('/fs' + urllib.parse.quote(plan['log'], safe='/'), 64 << 20)
        path = a.out / 'native/collected-console.private.log'
        path.write_bytes(raw)
        finish(a.out, a.preparation, publication, complete(lan, plan, a.out / 'native', raw, path))
        return
    prep = load(a.preparation)
    down=bool(prep.get('IQ2_Down_layers'))
    Gate_layers=prep.get('IQ2_Gate_layers',[])
    layers=prep['IQ2_Down_layers'] if down else prep['IQ2_Up_layers']
    need(prep['completed'] and prep['all_changed_headers_independently_parsed'] and layers and
         prep['selected_tensors'] == 109 + len(layers)+len(Gate_layers), 'One explicitly prepared complete IQ2 overlay required')
    if Gate_layers:
        from iq2_up_model_scope import require_gate_input_qualification
        need(not down and Gate_layers==layers==list(range(48)), 'Only a uniform complete Gate/Up overlay is permitted')
        require_gate_input_qualification(prep['Gate_input_identity'])
    if down:
        from iq2_up_model_scope import require_down_qualification
        native=load(prep['native_operator_proof']['path'])
        provider=load(load(native['package']['path'])['relink']['path'])['model_resource_provider']
        need(layers==list(range(48)) and not prep['IQ2_Up_layers'] and not a.retained_Up_publication,
             'Only the complete uniform Down source may use its carrier resources')
        require_down_qualification(prep['native_operator_proof'],provider)
    candidate = load(prep['candidate']['path'])
    need(record(prep['candidate']['path']) == prep['candidate'], 'The complete candidate metadata changed')
    state = load(a.current / 'active-console.private.json')
    if a.execute:
        need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
             not state['unknown_completion'], 'Positive idle current ownership required')
    current = load(a.current / 'qwen-runtime/development.json')
    gate = current['native_first_generation_validation']
    need(gate['model_receipt_sha256'] == prep['selected_model_sha256'], 'The selected admitted model must be the same parent')
    old = json.loads(gate['precision_source_integrity']['raw'])
    retained = []
    for index, part in enumerate(prep['retained_precision_parts']):
        prior = old['parts'][index]
        need((part['bytes'], part['sha256']) == (prior['bytes'], prior['sha256']), 'An exact selected retained part is required')
        retained.append(prior)
    sources = load(a.current / 'provenance/model-source-plan.private.json')
    parents = sources['physical'] + sources['backing']
    need(sources['completed'] and len(parents) == 518, 'The complete current source identity plan is required')
    for part in retained:
        need(any(r['path'] == part['path'] and r['bytes'] == part['bytes'] and r['identity'] == part['identity']
                 for r in parents), 'Every retained part must be in the complete actual selected source plan')
    reused_Up=0
    retained_Up=None
    if a.retained_Up_publication:
        previous=load(a.retained_Up_publication)
        need(previous['completed'] and previous['whole_new_bytes_and_all_parent_identities_qualified'] and
             record(previous['preparation']['path'])==previous['preparation'] and
             record(previous['source_integrity']['path'])==previous['source_integrity'],
             'Only a completed whole-file sealed publication may supply a retained prefix')
        old_prep=load(previous['preparation']['path']);old_seal=load(previous['source_integrity']['path'])
        reused_Up=len(old_prep['IQ2_Up_layers'])
        need(0<reused_Up<=len(prep['IQ2_Up_layers']) and not old_prep.get('IQ2_Gate_layers') and
             (reused_Up<len(prep['IQ2_Up_layers']) or Gate_layers==list(range(48))) and
             old_prep['IQ2_Up_layers']==prep['IQ2_Up_layers'][:reused_Up] and
             old_prep['retained_precision_parts']==prep['retained_precision_parts'] and
             old_prep['new_parts'][:reused_Up]==prep['new_parts'][:reused_Up] and
             old_prep['selected_model_sha256']==prep['selected_model_sha256'] and
             old_seal['model_receipt_sha256']==old_prep['candidate']['sha256'] and
             old_seal['CPU_owners_positively_closed'],
             'The same selected model and exact complete IQ2 weight prefix are required')
        prefix=old_seal['parts'][len(retained):len(retained)+reused_Up]
        need(len(prefix)==reused_Up and all((r['bytes'],r['sha256'])==(p['bytes'],p['sha256'])
             for r,p in zip(prefix,prep['new_parts'])), 'Every retained whole layer must match its prepared bytes')
        retained+=prefix
        parents+=prefix
        retained_Up=record(a.retained_Up_publication)
    a.out.mkdir(parents=True, exist_ok=False)
    nonce = secrets.token_hex(16)
    root, alias, application = PHYSICAL + '/expert-q2-' + nonce, ALIAS + '/expert-q2-' + nonce, '/app0/expert-q2-' + nonce
    files = []
    completed_packs={}
    for marker in prep.get('completed_encoding_receipts',[]):
        need(record(marker['path'])==marker,'A completed encoding receipt changed')
        completed=load(marker['path']);completed_packs[completed['pack']['path']]=marker
    def add(row, name):
        need(0 < row['bytes'] <= 512 << 20, 'Exact bounded new publication input required')
        file=dict(local=row, physical=root + '/' + name, alias=alias + '/' + name, application=application + '/' + name)
        if row['path'] in completed_packs:
            file['encoder_completion']=completed_packs[row['path']]
        verify_input(file)
        files.append(file)
    for i, part in enumerate(prep['new_parts'][reused_Up:], len(retained)):
        add(part, 'precision.part' + str(i) + '.bin')
    add(prep['candidate'], 'model-receipt.json')
    for h in candidate['precision_overlay']['headers']:
        source = candidate['precision_overlay']['parts'][h['part']]
        with Path(source['path']).open('rb') as stream:
            stream.seek(h['pack_offset'])
            raw = stream.read(h['bytes'])
        need(hashlib.sha256(raw).hexdigest() == h['sha256'] and
             re.fullmatch(r'qwen-flash-next-bf16-\d{5}-of-00076\.gguf', h['file']), 'One complete serialized model header required')
        path = a.out / h['file']
        path.write_bytes(raw)
        add(record(path), h['file'])
    need(0 < len(files) <= 128 and len({f['physical'] for f in files}) == len(files), 'Bounded unique new file set required')
    context = '#define SHARED_Q4_FILE_COUNT ' + str(len(files)) + 'u\n#define SHARED_Q4_PARENT_COUNT ' + str(len(parents)) + 'u\n'
    context += '#define SHARED_Q4_DIRECTORY ' + json.dumps(root) + '\n#define SHARED_Q4_ALIAS ' + json.dumps(alias) + '\n'
    context += 'struct shared_Q4_file{const char*physical,*alias;uint64_t bytes;const char*sha;};\n'
    context += 'static const struct shared_Q4_file shared_Q4_files[]={' + ','.join('{' + json.dumps(f['physical']) + ',' +
        json.dumps(f['alias']) + ',' + str(f['local']['bytes']) + 'ULL,' + json.dumps(f['local']['sha256']) + '}' for f in files) + '};\n'
    context += 'struct shared_Q4_parent{const char*physical,*alias;uint64_t expected[10];};\nstatic const struct shared_Q4_parent shared_Q4_parent_files[]={\n'
    directories = set()
    for row in parents:
        path = row['path']
        need(path.startswith('/app0/') and '..' not in PurePosixPath(path).parts, 'Exact parent source paths required')
        physical, mounted = PHYSICAL + path[5:], ALIAS + path[5:]
        directories.add(str(PurePosixPath(physical).parent))
        context += '{' + json.dumps(physical) + ',' + json.dumps(mounted) + ',{' + ','.join(str(v) + 'ULL' for v in row['identity']) + '}},\n'
    context += '};\n#define SHARED_Q4_DIRECTORY_COUNT ' + str(len(directories)) + 'u\n'
    context += 'static const char*shared_Q4_directories[]={' + ','.join(map(json.dumps, sorted(directories))) + '};\n'
    rows = current_files(a.current)
    need(sum(f['local']['bytes'] for f in files)<=512<<20 or a.source_seal_window_proof is not None,
         'Large source sets require the qualified larger integrity window before any upload')
    plan = build(a.workspace, a.mount_plan, rows, rows, [], 'seal-shared-Q4', a.out / 'native',
        source_seal_context=context,source_seal_window_proof=a.source_seal_window_proof)
    publication = dict(preparation=record(a.preparation), files=files, directory=root, application_directory=application,
        retained_parts=retained, parent_source_count=len(parents), native_plan=record(a.out / 'native/plan.private.json'),
        new_part_count=len(prep['new_parts'])-reused_Up,retained_Up_publication=retained_Up,
        retained_Up_layers=reused_Up,automatic_retries=0)
    save(a.out / 'plan.private.json', publication)
    if not a.execute:
        print(json.dumps(dict(prepared=True, PS5_operations=0, new_files=len(files), retained_parts_copied=0)))
        return
    submit(a, publication, plan)


if __name__ == '__main__':
    main()
