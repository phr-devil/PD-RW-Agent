"""Windows Job Object child containment for fixed host diagnostic workers.

CreateProcessW is suspended; assign to a Job with KILL_ON_JOB_CLOSE *before*
resuming the initial thread. This avoids Popen's create/assign race. A Job
Object is process containment, NOT filesystem/credential/network isolation.
"""
from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path

from ..schemas import AgentError

CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
WAIT_TIMEOUT = 0x00000102
STILL_ACTIVE = 259


class LARGE_INTEGER(ctypes.Structure):
    _fields_ = [("QuadPart", ctypes.c_longlong)]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", LARGE_INTEGER),
        ("PerJobUserTimeLimit", LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(key, ctypes.c_ulonglong) for key in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_EXTENDED_LIMIT_INFO(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


def _cleanup_failed_launch(kernel, job, process, thread):
    """Kill a suspended child even when Job assignment itself has failed.

    Without TerminateProcess an unassigned suspended child could outlive
    this host after AssignProcessToJobObject raises.
    """
    if process:
        kernel.TerminateProcess(process, 1)
    if thread:
        kernel.CloseHandle(thread)
    if process:
        kernel.CloseHandle(process)
    if job:
        kernel.CloseHandle(job)


class WinJobProcess:
    def __init__(self, process, job, pid: int, kernel):
        self._process = process
        self._job = job
        self.pid = pid
        self._kernel = kernel
        self.returncode = None
        self._closed = False

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        code = wintypes.DWORD()
        if not self._kernel.GetExitCodeProcess(self._process, ctypes.byref(code)):
            raise AgentError("HOST_PROCESS_QUERY_FAILED", "GetExitCodeProcess failed")
        if code.value == STILL_ACTIVE:
            return None
        value = ctypes.c_int32(code.value).value
        self.returncode = value
        self.close()
        return value

    def terminate(self):
        if self.poll() is None:
            if not self._kernel.TerminateJobObject(self._job, 1):
                raise AgentError("HOST_TERMINATE_FAILED", "TerminateJobObject failed")

    def close(self):
        if not self._closed:
            self._closed = True
            # Job close is kill-on-close even when the host loses its handle.
            self._kernel.CloseHandle(self._job)
            self._kernel.CloseHandle(self._process)


def launch_windows_job(argv: list[str], cwd: Path) -> WinJobProcess:
    if not hasattr(ctypes, "WinDLL"):
        raise AgentError("WINDOWS_ONLY", "Job Object requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
    kernel.CreateProcessW.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise AgentError("HOST_JOB_CREATE_FAILED", "Cannot create Windows Job Object")
    process = None
    thread = None
    try:
        info = JOBOBJECT_EXTENDED_LIMIT_INFO()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(
                job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
                ctypes.sizeof(info)):
            raise AgentError("HOST_JOB_CONFIG_FAILED", "Cannot set kill-on-close")
        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(startup)
        pi = PROCESS_INFORMATION()
        # Only package-defined fixed worker commands reach this function.
        cmd = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        if not kernel.CreateProcessW(
                None, cmd, None, None, False,
                CREATE_SUSPENDED | CREATE_NO_WINDOW,
                None, str(cwd), ctypes.byref(startup), ctypes.byref(pi)):
            raise AgentError("HOST_PROCESS_CREATE_FAILED", "CreateProcessW failed")
        process, thread = pi.hProcess, pi.hThread
        if not kernel.AssignProcessToJobObject(job, process):
            raise AgentError("HOST_JOB_ASSIGN_FAILED", "Cannot assign child to Job Object")
        if kernel.ResumeThread(thread) == 0xFFFFFFFF:
            raise AgentError("HOST_PROCESS_RESUME_FAILED", "Cannot resume suspended child")
        kernel.CloseHandle(thread)
        thread = None
        return WinJobProcess(process, job, int(pi.dwProcessId), kernel)
    except Exception:
        # When Job assignment failed, KILL_ON_JOB_CLOSE does not apply to
        # the newly created suspended process. Terminate it explicitly first.
        _cleanup_failed_launch(kernel, job, process, thread)
        raise
