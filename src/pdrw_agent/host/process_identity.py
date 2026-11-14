"""Best-effort, read-only OS process identity observation.

PID alone is not a durable identity. Start token includes Linux /proc
start ticks or Win32 process creation FILETIME. Observation is not job
ownership, authorization or a sandbox. A missing token is UNKNOWN.
"""
from __future__ import annotations

import os
import sys


def observe_process(pid: int) -> dict:
    base = {"pid": pid, "status": "UNKNOWN", "start_token": None,
            "liveness_verified": False, "host_ownership_verified": False}
    if type(pid) is not int or not 1 <= pid <= 0x7FFFFFFF:
        return {**base, "reason": "INVALID_PID"}
    if sys.platform.startswith("linux"):
        try:
            # /proc/pid/stat has a free-text '(comm)' field; rsplit after the
            # final ')' before taking field 22 (index 19 from field 3).
            raw = open(f"/proc/{pid}/stat", encoding="utf-8").read(8192)
            after = raw.rsplit(")", 1)[1].split()
            token = after[19]
            if after[0] in {"Z", "X"}:
                return {**base, "status": "EXITED", "reason": "ZOMBIE_OR_DEAD"}
            return {**base, "status": "OBSERVED",
                    "start_token": f"linux-proc:{token}",
                    "liveness_verified": True}
        except (OSError, IndexError, ValueError):
            return {**base, "reason": "PROCESS_NOT_OBSERVABLE"}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME)]
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return {**base, "reason": "PROCESS_NOT_OBSERVABLE"}
        try:
            values = [wintypes.FILETIME() for _ in range(4)]
            ok = kernel.GetProcessTimes(handle, *(ctypes.byref(x) for x in values))
            if not ok:
                return {**base, "reason": "PROCESS_TIMES_NOT_AVAILABLE"}
            birth = (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
            return {**base, "status": "OBSERVED",
                    "start_token": f"win-filetime:{birth}",
                    "liveness_verified": False,
                    "reason": "IDENTITY_OBSERVED_EXIT_STATUS_NOT_CHECKED"}
        finally:
            kernel.CloseHandle(handle)
    return {**base, "reason": "PROCESS_IDENTITY_PLATFORM_UNSUPPORTED"}


def compare_process_identity(pid: int, expected_start_token: str) -> dict:
    observed = observe_process(pid)
    matched = (isinstance(expected_start_token, str) and
               bool(expected_start_token) and
               observed["start_token"] == expected_start_token)
    return {
        "pid": pid, "identity_matched": matched,
        "status": "SAME_PID_AND_START_TOKEN_OBSERVED" if matched else
                  "PROCESS_IDENTITY_NOT_ESTABLISHED",
        "liveness_verified": bool(matched and observed["liveness_verified"]),
        "host_ownership_verified": False,
        "execution_authorized": False,
    }
