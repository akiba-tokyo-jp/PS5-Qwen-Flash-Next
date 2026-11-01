# SPDX-License-Identifier: MIT
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from model_directory_readmission import rebind_directory

class DirectoryReadmissionTests(unittest.TestCase):
    def setUp(self):
        old = [123, 7, 0o40755, 0, 0, 65536, 100, 0, 100, 0]
        raw = json.dumps(dict(directory_identity=old, model_receipt_sha256='a' * 64,
                              parts=[dict(identity=[123, 8], sha256='b' * 64)]))
        self.gate = dict(model_receipt_sha256='a' * 64,
            precision_source_integrity=dict(raw=raw, sha256=hashlib.sha256(raw.encode()).hexdigest()),
            physical_floor=512, GPU_completion_required=True)
        current = old[:6] + [95, 0, 95, 0]
        self.proof = dict(completed=True, current_boot=[1234, 5678], full_native_SHA256_identity_EOF_files=11,
            complete_unchanged_file_metadata=518, double_directory_snapshot_equal=True,
            only_directory_times_require_rebinding=True, source_payloads_changed=False,
            GPU_calls=0, title_launches=0, previous_directory=old, canonical_directory=current,
            application_directory=[456] + current[1:])

    def test_only_directory_times_change(self):
        before = copy.deepcopy(self.gate)
        updated = rebind_directory(self.gate, self.proof, [1234, 5678])
        old = json.loads(before['precision_source_integrity']['raw'])
        new = json.loads(updated['precision_source_integrity']['raw'])
        self.assertEqual(self.gate, before)
        self.assertEqual(new.pop('directory_identity'), self.proof['canonical_directory'])
        old.pop('directory_identity')
        self.assertEqual(new, old)
        updated.pop('precision_source_integrity'); before.pop('precision_source_integrity')
        self.assertEqual(updated, before)

    def test_changed_ownership_inode_size_or_source_device_refused(self):
        for field in range(6):
            proof = copy.deepcopy(self.proof)
            proof['canonical_directory'][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                rebind_directory(self.gate, proof, [1234, 5678])

    def test_other_boot_or_missing_native_proof_refused(self):
        for field, value in [('current_boot', [1234, 0]), ('completed', False),
                             ('complete_unchanged_file_metadata', 517),
                             ('double_directory_snapshot_equal', False), ('source_payloads_changed', True)]:
            proof = dict(self.proof, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                rebind_directory(self.gate, proof, [1234, 5678])

    def test_application_alias_or_recipe_change_refused(self):
        proof = copy.deepcopy(self.proof); proof['application_directory'][1] += 1
        with self.assertRaises(ValueError): rebind_directory(self.gate, proof, [1234, 5678])
        gate = dict(self.gate, model_receipt_sha256='c' * 64)
        with self.assertRaises(ValueError): rebind_directory(gate, self.proof, [1234, 5678])

if __name__ == '__main__': unittest.main()
