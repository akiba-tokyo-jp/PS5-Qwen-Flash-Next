#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise changed host transport geometry, tails and returned failures."""
import hashlib
from pathlib import Path
import socket
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from model_part_payload import send_payload, WINDOW


class Channel:
    def __init__(self, fail=False):
        self.parts=[]; self.options=[]; self.fail=fail
    def setsockopt(self,*args): self.options.append(args)
    def sendall(self,data):
        if self.fail: raise OSError('Returned fixture send failure')
        self.parts.append(data)


with tempfile.TemporaryDirectory() as root:
    source=Path(root)/'part.bin'
    for size in (1,16383,16384,WINDOW,WINDOW+619):
        data=bytes((i*17)%256 for i in range(size));source.write_bytes(data)
        channel=Channel();seen=[];result=send_payload(channel,source,size,seen.append)
        assert b''.join(channel.parts)==data and max(map(len,channel.parts))<=WINDOW
        assert result['bytes']==size and result['sha256']==hashlib.sha256(data).hexdigest()
        assert seen[-1]==size and channel.options==[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)]
    for size,fail in ((618,False),(620,False),(619,True)):
        source.write_bytes(bytes(619));channel=Channel(fail)
        try: send_payload(channel,source,size,lambda _:None)
        except (RuntimeError,OSError): pass
        else: raise AssertionError('A changed extent or failed send must refuse')
print('{"completed":true,"positive_controls":5,"negative_controls":3,"PS5_operations":0}')
