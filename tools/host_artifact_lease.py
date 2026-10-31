#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain Windows read-only handles so unchanged link artifacts need one full hash."""
import ctypes,hashlib,os
from pathlib import Path

class ArtifactLease:
    """A failed exclusive read lease never authorizes a cached digest."""
    def __init__(self,rows):
        if os.name!='nt':raise ValueError('Windows file-sharing enforcement required')
        from ctypes import wintypes
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        self.kernel.CreateFileW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE];self.kernel.CloseHandle.restype=wintypes.BOOL
        self.handles=[];self.rows={};self.hits=0
        try:
            for row in rows:
                path=Path(row['path']).resolve();key=os.path.normcase(str(path))
                if key in self.rows:
                    if self.rows[key][0]!=row['sha256']:raise ValueError('Ambiguous immutable artifact digest')
                    continue
                h=self.kernel.CreateFileW(str(path),0x80000000,1,None,3,0x08000000,None)
                if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
                self.handles.append(h);before=self.identity(path)
                with path.open('rb')as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
                if before!=self.identity(path)or before[2]!=row['bytes']or digest!=row['sha256']:raise ValueError('Leased full artifact hash or identity differs')
                self.rows[key]=(digest,before)
        except BaseException:self.close();raise
    @staticmethod
    def identity(path):
        s=path.stat();return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    def digest(self,path,fallback):
        resolved=Path(path).resolve();row=self.rows.get(os.path.normcase(str(resolved)))
        if row is None:return fallback(path)
        if self.identity(resolved)!=row[1]:raise ValueError('Leased immutable artifact identity changed')
        self.hits+=1;return row[0]
    def close(self):
        failed=False
        while self.handles:
            if not self.kernel.CloseHandle(self.handles.pop()):failed=True
        if failed:raise ctypes.WinError(ctypes.get_last_error())
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
