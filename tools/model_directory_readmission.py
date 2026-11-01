# SPDX-License-Identifier: MIT
"""Rebind only directory timestamps after complete current-boot native proof."""
import copy
import hashlib
import json

def rebind_directory(gate, proof, boot):
    def require(value, message):
        if not value:
            raise ValueError(message)
    require(proof.get('completed') is True and proof.get('current_boot') == boot,
            'A complete proof from the actual current boot is required')
    require(proof.get('full_native_SHA256_identity_EOF_files') == 11 and
            proof.get('complete_unchanged_file_metadata') == 518 and
            proof.get('double_directory_snapshot_equal') is True and
            proof.get('only_directory_times_require_rebinding') is True and
            proof.get('source_payloads_changed') is False and
            proof.get('GPU_calls') == proof.get('title_launches') == 0,
            'Whole certificates, unchanged sources and two directory snapshots are required')
    policy = gate['precision_source_integrity']
    raw = policy['raw']
    require(hashlib.sha256(raw.encode()).hexdigest() == policy['sha256'],
            'The original embedded source certificate changed')
    seal = json.loads(raw)
    previous = seal['directory_identity']
    current = proof['canonical_directory']
    application = proof['application_directory']
    require(previous == proof['previous_directory'] and len(previous) == len(current) == len(application) == 10,
            'The exact original certificate directory is required')
    require(current[:6] == previous[:6] and current[1:] == application[1:],
            'Device, inode, mode, owner and length must remain exact across both namespaces')
    require(all(type(value) is int and value >= 0 for value in current) and
            current[7] < 1000000000 and current[9] < 1000000000,
            'Complete native timestamps are required')
    require(seal['model_receipt_sha256'] == gate['model_receipt_sha256'],
            'The model recipe must remain exact')
    updated = copy.deepcopy(gate)
    seal['directory_identity'] = current
    sealed = json.dumps(seal, ensure_ascii=True, indent=2) + '\n'
    updated['precision_source_integrity'] = dict(policy, raw=sealed,
        sha256=hashlib.sha256(sealed.encode()).hexdigest())
    return updated
