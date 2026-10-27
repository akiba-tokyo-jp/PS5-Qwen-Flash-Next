#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail closed on stale boot, missing counters and changed process owners."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from kernel_vm_preflight import decode_dump, review, session_boot, load_qualified_session
from rebind_cpu_context import headers, current_processes, launcher_header, ROLES


def dump(data):
    return b'00000000  ' + b' '.join(f'{v:02x}'.encode() for v in data) + b'  | value\n/$ DONE\n/$ '


def values():
    return dict(boot_before=[100, 12], boot_after=[100, 12], page_bytes=16384,
                total=138739, minimum=898, reserved=206, target=2974,
                free_first=1060, free_last=1017, active=18526, inactive=89190,
                wired=29997, cache=0)


def context():
    processes = [dict(label=label, name=name, pid=20+i, ppid=1, uid=0,
                      start_sec=100+i, start_usec=20) for i, (label, name) in enumerate(ROLES)]
    processes[-1]['ppid'] = processes[4]['pid']
    processes[6]['ppid'] = processes[5]['pid']
    compat = dict(processes[-1], self=False)
    session = dict(state='fresh_readonly_context_verified', boot=[100, 12],
                   double_snapshot_equal=True, native_eboot_count=0, runningBigApp=-1,
                   old_session_or_synthetic_owner_used=False, kstuff_query_raw=0,
                   services=processes[:5], parent=processes[5], shellcore=processes[6],
                   compat_candidates=[compat])
    runtime = dict(state='unchanged_runtime_ready', boot=[100, 12], kernel_loaded=True,
                   runtime_pid=processes[-1]['pid'], ELF_requests=1, automatic_retries=0)
    return session, runtime


class CPUPreflightTests(unittest.TestCase):
    def test_actual_dump_ABI_and_errors(self):
        self.assertEqual(decode_dump(dump((16384).to_bytes(4, 'little')), 4), 16384)
        self.assertEqual(decode_dump(dump((100).to_bytes(8, 'little') + (12).to_bytes(8, 'little')), 16), [100, 12])
        good = dump(b'\x01\x00\x00\x00')
        for raw in (b'sysctl: No such file or directory\n/$ ',
                    b'sysctl: Permission denied\n' + good,
                    good.replace(b'00000000', b'00000004'),
                    good + good, dump(b'\x00'), good.replace(b'01 ', b'0x ')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_dump(raw, 4)

    def test_low_free_refuses_before_any_preparation(self):
        result = review(values(), [100, 12], 10142)
        self.assertEqual(result['state'], 'refused_before_staging')
        self.assertEqual(result['operational_floor_pages'], 1154)
        self.assertFalse(result['may_prepare_new_case'])
        self.assertFalse(result['native_admission_granted'])
        self.assertFalse(result['inactive_counted_as_free'])

    def test_pass_cannot_grant_native_admission(self):
        value = values()
        value.update(free_first=12000, free_last=10142)
        result = review(value, [100, 12], 10142)
        self.assertTrue(result['may_prepare_new_case'])
        self.assertFalse(result['native_admission_granted'])
        value['free_last'] = 10141
        self.assertFalse(review(value, [100, 12], 10142)['may_prepare_new_case'])

    def test_counter_geometry_boot_and_reserve_refusals(self):
        for key, changed in (('boot_before', [99, 12]), ('boot_after', [101, 12]),
                             ('page_bytes', 4096), ('reserved', 0), ('target', 898),
                             ('free_first', True), ('active', 138740), ('wired', -1)):
            value = values()
            value[key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                review(value, [100, 12], 10142)
        with self.assertRaises(ValueError):
            review(values(), [100, 12], 1153)
        value = values()
        value.pop('free_last')
        with self.assertRaises(ValueError):
            review(value, [100, 12], 10142)

    def test_complete_CPU_identity_cannot_be_synthetic_or_live(self):
        for key, changed in (('double_snapshot_equal', False), ('old_session_or_synthetic_owner_used', True),
                             ('native_eboot_count', 1), ('native_eboot_count', False),
                             ('runningBigApp', 9), ('kstuff_query_raw', 89)):
            session, _ = context()
            session[key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                session_boot(session)

    def test_current_headers_bind_all_eight_actual_owners(self):
        session, runtime = context()
        generated = headers(session, runtime, 'a'*32)
        self.assertEqual(len(current_processes(session, runtime)), 8)
        self.assertIn('#define BOOT_SEC 100LL', generated['observer_context.h'])
        for _, name in ROLES:
            self.assertEqual(generated['observer_context.h'].count('"'+name+'"'), 1)
            self.assertEqual(generated['close_context.h'].count('"'+name+'"'), 1)
        self.assertIn('"compat",27,"payload",24,0U,107LL,20LL', generated['observer_context.h'])

    def test_runtime_and_ancestry_changes_cannot_borrow_old_headers(self):
        edits = (
            lambda s, r: r.update(boot=[99, 12]),
            lambda s, r: r.update(runtime_pid=900),
            lambda s, r: r.update(kernel_loaded=False),
            lambda s, r: r.update(ELF_requests=2),
            lambda s, r: s['compat_candidates'].append(copy.deepcopy(s['compat_candidates'][0])),
            lambda s, r: s['compat_candidates'][0].update(ppid=1),
            lambda s, r: s['services'][0].update(start_sec=99),
            lambda s, r: s['services'][0].update(start_usec=11),
            lambda s, r: s['services'][0].update(uid=1),
            lambda s, r: s['services'][0].update(pid=s['services'][1]['pid']),
            lambda s, r: s['services'][0].update(pid=True),
            lambda s, r: s['services'].pop(),
        )
        for edit in edits:
            session, runtime = context()
            edit(session, runtime)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                headers(session, runtime, 'a'*32)
        with self.assertRaises(ValueError):
            headers(*context(), 'stale')

    def test_ordinary_launcher_rebind_changes_only_actual_identity_data(self):
        template='\n'.join('#define '+key+' 1'for key in ('BOOT_SEC','BOOT_USEC','COMPATIBILITY_PID',
            'COMPATIBILITY_START_SEC','COMPATIBILITY_START_USEC'))+'\n#define MOSS_CONFIG_SHA "unchanged"\n'
        template+='static const struct expected_service expected_services[]={\n'
        template+='\n'.join('{"'+name+'",1,1,0U,1LL,1LL},'for _,name in ROLES)+'\n};\n'
        session,runtime=context();out=launcher_header(session,runtime,template)
        self.assertIn('#define BOOT_SEC 100LL',out);self.assertIn('#define COMPATIBILITY_PID 27',out)
        self.assertIn('#define MOSS_CONFIG_SHA "unchanged"',out)
        self.assertIn('{"payload",27,24,0U,107LL,20LL},',out)
        for bad in (template+'#define BOOT_SEC 9\n',template.replace('"payload"','"foreign"'),
                    template.replace('COMPATIBILITY_START_SEC','MISSING'),template+'\0'):
            with self.subTest(template=bad),self.assertRaises(ValueError):launcher_header(session,runtime,bad)

    def test_completed_evidence_cannot_be_substituted_or_edited(self):
        test_root = Path(__file__).resolve().parents[1]/'.test-tmp'
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cpu-evidence-', dir=test_root) as folder:
            root = Path(folder)
            session, runtime = context()
            session['FW'] = '0x12400009'
            binary = root/'observer.elf'
            binary.write_bytes(b'host-only synthetic observer artifact')
            artifact = dict(path=str(binary), bytes=binary.stat().st_size,
                            sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
            manifest = dict(expected_boot=session['boot'], expected_firmware=session['FW'],
                            nonce='a'*32, artifact=artifact, expected_processes=current_processes(session, runtime))
            manifest_path = root/'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            log = root/'console.log'
            log.write_bytes(b'END success=1 log_healthy=1 nonce='+b'a'*32+b' metadata_queries_only=1\n')
            session['evidence'] = dict(path=str(log), bytes=log.stat().st_size,
                sha256=hashlib.sha256(log.read_bytes()).hexdigest(), manifest_path=str(manifest_path),
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                boot=session['boot'], nonce=manifest['nonce'], observer_artifact=artifact)
            path = root/'session.json'
            path.write_text(json.dumps(session))
            self.assertEqual(load_qualified_session(path)[0]['boot'], [100, 12])
            changed = copy.deepcopy(session)
            changed['services'][0]['pid'] = 700
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                load_qualified_session(path)
            path.write_text(json.dumps(session))
            binary.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                load_qualified_session(path)
            binary.write_bytes(b'host-only synthetic observer artifact')
            log.write_bytes(log.read_bytes().replace(b'success=1', b'success=0'))
            changed = copy.deepcopy(session)
            changed['evidence']['sha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                load_qualified_session(path)


if __name__ == '__main__':
    unittest.main()
