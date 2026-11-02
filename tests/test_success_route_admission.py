# SPDX-License-Identifier: MIT
"""Refuse stale or mounted inputs before any successful-route initialization."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from start_success_route import admission,NAMES


class SuccessRouteAdmission(unittest.TestCase):
    def setUp(self):
        row=dict(phase='1',firmware=str(0x12400009),title_mounts='0',owned_mounts='0',
                 exact_title_alias='0',source_directory='1',page_size='16384',reads_only='1',mount_fingerprint='42')
        self.good=dict(completed=True,runtime_loaded=False,native_owners=0,helper_exited=True,
                       helper_files_removed=True,boot=[1000,1],
                       success_route_prerequisites=[row,dict(row,phase='2')],
                       processes=[dict(name=name,pid=str(i+10),uid='0') for i,name in enumerate(NAMES)])

    def test_complete_pre_mount_context(self):
        boot,services=admission(self.good);self.assertEqual(boot,[1000,1]);self.assertEqual(len(services),7)

    def test_no_implicit_reentry_or_uncertain_owner(self):
        for key,value in (('completed',False),('runtime_loaded',True),('native_owners',1),
                          ('helper_exited',False),('helper_files_removed',False)):
            bad=copy.deepcopy(self.good);bad[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):admission(bad)

    def test_refuse_alias_or_wrong_source_in_either_phase(self):
        for phase in (0,1):
            for key,value in (('firmware','0'),('title_mounts','1'),('owned_mounts','1'),
                              ('exact_title_alias','1'),('source_directory','0'),('page_size','4096'),('reads_only','0')):
                bad=copy.deepcopy(self.good);bad['success_route_prerequisites'][phase][key]=value
                with self.subTest(phase=phase,key=key),self.assertRaises(RuntimeError):admission(bad)

    def test_refuse_changed_namespace_or_missing_duplicate_service(self):
        bad=copy.deepcopy(self.good);bad['success_route_prerequisites'][1]['mount_fingerprint']='43'
        with self.assertRaises(RuntimeError):admission(bad)
        for change in ('missing','duplicate','aliased','nonroot'):
            bad=copy.deepcopy(self.good)
            if change=='missing':bad['processes'].pop()
            if change=='duplicate':bad['processes'].append(dict(bad['processes'][0]))
            if change=='aliased':bad['processes'][1]['pid']=bad['processes'][0]['pid']
            if change=='nonroot':bad['processes'][0]['uid']='1'
            with self.subTest(change=change),self.assertRaises(RuntimeError):admission(bad)


if __name__=='__main__':unittest.main()
