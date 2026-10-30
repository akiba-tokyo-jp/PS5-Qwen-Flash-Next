# SPDX-License-Identifier: MIT
"""Reject drift that could reopen the tenth-request evidence overwrite."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from finite_route_capacity import bind_route_capacity

class FiniteRouteCapacityTests(unittest.TestCase):
    def source(self,count):
        return f'''std::array<CompletedRouteEvidence,9> routes;
const unsigned request_count={count};
routes[ordinal]=capture();use(routes[ordinal-1],routes[ordinal]);
for(unsigned i=0;i<request_count;++i)save(routes[i]);'''

    def test_tenth_and_twelfth_record_have_declared_storage(self):
        for count in (2,8,10,12):
            text=bind_route_capacity(self.source(count),count)
            self.assertLess(text.index('constexpr unsigned request_count='),text.index('std::array<CompletedRouteEvidence,request_count>'))
            self.assertNotIn('routes[',text)
            self.assertIn('routes.at(ordinal)',text)
            self.assertIn('routes.at(i)',text)

    def test_wrong_count_and_unchecked_access_are_rejected(self):
        for source,count in ((self.source(10),12),(self.source(10)+'routes[other];',10),(self.source(13),13)):
            with self.assertRaises((ValueError,RuntimeError)):bind_route_capacity(source,count)

if __name__=='__main__':unittest.main()
