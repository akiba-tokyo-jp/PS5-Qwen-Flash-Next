# SPDX-License-Identifier: MIT
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_preservation_integrity as build


class PreservedArtifacts(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.test-tmp'
        base.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.tmp.name).resolve()
        self.root.relative_to(base.resolve())
        self.addCleanup(self.tmp.cleanup)
        self.file = self.root / 'capture.bmp'
        self.file.write_bytes(b'original captured bytes')
        self.row = dict(remote_path='/data/ai/moss-proof-0123456789abcdef.bmp',
                        capture=build.record(self.file), producer_positively_closed=True)
        self.manifest = dict(schema='ps5-qwen-closed-artifacts-v1', sources=[self.row])

    def test_closed_captured_bytes_and_literal_paths(self):
        rows = build.sources(self.manifest)
        text = build.context_header(rows, 'f' * 32)
        self.assertIn(json.dumps(self.row['remote_path']), text)
        self.assertIn(self.row['capture']['sha256'], text)
        self.assertIn('"' + 'f' * 32 + '"', text)
        self.assertIn('0123456789abcdef', text)
        self.file.write_bytes(b'changed after capture')
        with self.assertRaises(ValueError):
            build.sources(self.manifest)

    def test_refuses_unclosed_unowned_or_injected_sources(self):
        for key, value in [('producer_positively_closed', False), ('producer_positively_closed', 1),
                           ('remote_path', '/data/ai/moss-x/../other.bmp'),
                           ('remote_path', '/system/file'), ('remote_path', '/data/ai/moss-";code'),
                           ('remote_path', '/data/ai/moss-x//file')]:
            altered = copy.deepcopy(self.manifest)
            altered['sources'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                build.sources(altered)
        for key, value in [('bytes', True), ('bytes', 0), ('bytes', build.MAX_FILE + 1), ('sha256', 'X' * 64)]:
            altered = copy.deepcopy(self.manifest)
            altered['sources'][0]['capture'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                build.sources(altered)
        for rows in ([], [self.row, self.row], [self.row] * 65):
            with self.assertRaises(ValueError):
                build.sources(dict(self.manifest, sources=rows))
        rows = [dict(self.row, remote_path=f'/data/ai/moss-{i}', capture=dict(self.row['capture'], bytes=build.MAX_FILE)) for i in range(3)]
        with patch.object(build, 'record', return_value=rows[0]['capture']), self.assertRaises(ValueError):
            build.sources(dict(self.manifest, sources=rows))

    def test_qualification_requires_the_executed_image_and_positive_terminal(self):
        artifact = build.record(self.file)
        manifest = dict(CPU_probe=artifact, nonce='a' * 32, CPU_probe_commands=[['compile'], ['link']])
        execution = dict(artifact=artifact, automatic_retries=0)
        intent = self.root / 'execution.once.private.json'
        log = self.root / 'console.private.log'
        intent.write_text(json.dumps(execution))
        good = 'BEGIN CPU_only=1 title_launches=0 GPU_calls=0\nEND success=1 nonce=' + 'a' * 32 + ' no_retry=1\n'
        log.write_text(good)
        build.qualified_base(manifest, intent)
        for text in (good.replace('success=1', 'success=0'), good + good,
                     good.replace('CPU_only=1', 'CPU_only=0'), good.replace('a' * 32, 'b' * 32)):
            log.write_text(text)
            with self.assertRaises(ValueError):
                build.qualified_base(manifest, intent)
        log.write_text(good)
        execution['artifact'] = dict(artifact, sha256='0' * 64)
        intent.write_text(json.dumps(execution))
        with self.assertRaises(ValueError):
            build.qualified_base(manifest, intent)


if __name__ == '__main__':
    unittest.main()
