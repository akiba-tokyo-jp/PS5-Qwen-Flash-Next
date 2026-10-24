#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual once-only stream consumer with synthetic transports."""
import ast
import http.client
import io
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import time
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from first_generation_result import require

class NativeStreamFailure(unittest.TestCase):
    def setUp(self):
        root=ROOT/'.test-tmp';root.mkdir(exist_ok=True)
        self.directory=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.directory.cleanup)
        self.out=Path(self.directory.name);self.body={'id':'synthetic-1'};self.calls=0
    def consumer(self,events):
        payload=b''.join(b'data: '+json.dumps(e).encode()+b'\n\n' for e in events)
        owner=self
        class Connection:
            def __init__(self,*args,**kwargs):self.sock=types.SimpleNamespace(settimeout=lambda _:None)
            def connect(self):pass
            def request(self,*args,**kwargs):owner.calls+=1
            def getresponse(self):
                stream=io.BytesIO(payload);stream.status=200;return stream
            def close(self):pass
        source=(ROOT/'tools/observe_native_plan.py').read_text()
        node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='post')
        actual=ast.get_source_segment(source,node)
        wrapper='def setup():\n    posts=0\n    class NativeRequestFailed(RuntimeError): pass\n'+textwrap.indent(actual,'    ')+'\n    return post, NativeRequestFailed, lambda: posts\n'
        def exclusive(path,value):
            with path.open('x') as f:json.dump(value,f)
        scope=dict(out=self.out,started=time.monotonic(),host='synthetic',time=time,json=json,require=require,
            exclusive=exclusive,http=types.SimpleNamespace(client=types.SimpleNamespace(HTTPConnection=Connection)))
        exec(compile(wrapper,'actual_native_stream_consumer','exec'),scope)
        return scope['setup']()
    def test_explicit_failure_is_saved_without_uncertain_or_retry(self):
        event=dict(id=self.body['id'],type='finished',state='failed',error=4,quarantined=True,resource_graph_retained=True,GPU_completion_qualified=False)
        post,failed,posts=self.consumer([event])
        with self.assertRaises(failed):post('/api/generate',self.body,'request',streamed=True)
        self.assertEqual((self.calls,posts()),(1,1))
        saved=json.loads((self.out/'request.failed.private.json').read_text())
        self.assertEqual(saved['terminal_event'],event)
        self.assertFalse((self.out/'request.uncertain.private.json').exists())
        self.assertTrue((self.out/'request.stream.private.log').stat().st_size)
    def test_empty_stream_remains_uncertain_without_retry(self):
        post,_,posts=self.consumer([])
        with self.assertRaises(ValueError):post('/api/generate',self.body,'request',streamed=True)
        self.assertEqual((self.calls,posts()),(1,1))
        self.assertTrue((self.out/'request.uncertain.private.json').exists())
        self.assertFalse((self.out/'request.failed.private.json').exists())
    def test_complete_stream_still_passes(self):
        events=[dict(id=self.body['id'],type='token',state='generating',error=0,ordinal=i) for i in [1,2]]
        events.append(dict(id=self.body['id'],type='finished',state='completed',error=0))
        post,_,posts=self.consumer(events)
        self.assertEqual(post('/api/generate',self.body,'request',streamed=True),events)
        self.assertEqual((self.calls,posts()),(1,1))
        self.assertTrue((self.out/'request.positive.private.json').exists())
if __name__=='__main__':unittest.main()
