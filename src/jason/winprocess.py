"""Owned Job Objects; lifecycle supervision, not a security sandbox."""
import ctypes
from ctypes import wintypes
import os
import struct

class Job:
    def __init__(self, pid):
        if os.name != "nt": raise RuntimeError("Windows is required.")
        k = self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p,wintypes.LPCWSTR]
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        for name, args in {
            "SetInformationJobObject":[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],
            "AssignProcessToJobObject":[wintypes.HANDLE,wintypes.HANDLE],
            "TerminateJobObject":[wintypes.HANDLE,wintypes.UINT],
            "CloseHandle":[wintypes.HANDLE],
            "QueryInformationJobObject":[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p],
        }.items():
            getattr(k,name).argtypes=args
            getattr(k,name).restype=wintypes.BOOL
        self.handle = k.CreateJobObjectW(None,None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        info = ctypes.create_string_buffer(144 if ctypes.sizeof(ctypes.c_void_p)==8 else 112)
        struct.pack_into("I",info,16,0x2000) # KILL_ON_JOB_CLOSE
        proc = k.OpenProcess(0x101,False,pid)
        try:
            if not k.SetInformationJobObject(self.handle,9,info,len(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not proc or not k.AssignProcessToJobObject(self.handle,proc):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            k.CloseHandle(self.handle)
            self.handle=None
            raise
        finally:
            if proc: k.CloseHandle(proc)
    def count(self):
        info = ctypes.create_string_buffer(48)
        if not self.k.QueryInformationJobObject(self.handle,1,info,len(info),None):
            raise ctypes.WinError(ctypes.get_last_error())
        return struct.unpack_from("I",info,36)[0] # ActiveProcesses after four LARGE_INTEGERs + TotalProcesses
    def close(self):
        if self.handle:
            self.k.TerminateJobObject(self.handle,1)
            self.k.CloseHandle(self.handle)
            self.handle=None

