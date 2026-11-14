"""Host security observation — never a self-signed OS isolation certificate.

Probe records the effective OS identity, not whether an untrusted model can
escape a sandbox. A trusted Windows host must be provisioned independently
under a restricted SID and accepted with real DEV/SEALED ACL tests.
"""
from __future__ import annotations

import os
import sys


def current_os_identity() -> dict:
    if os.name == "posix":
        return {"status": "IDENTITY_OBSERVED",
                "principal": f"uid:{os.geteuid()}",
                "isolation_verified": False}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        TOKEN_QUERY = 0x0008
        TOKEN_USER = 1
        token = wintypes.HANDLE()
        adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.HANDLE)]
        adv.OpenProcessToken.restype = wintypes.BOOL
        adv.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        adv.GetTokenInformation.restype = wintypes.BOOL
        adv.ConvertSidToStringSidW.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        adv.ConvertSidToStringSidW.restype = wintypes.BOOL
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.LocalFree.argtypes = [wintypes.HLOCAL]
        kernel.LocalFree.restype = wintypes.HLOCAL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(),
                                    TOKEN_QUERY, ctypes.byref(token)):
            return {"status": "IDENTITY_UNOBSERVABLE", "isolation_verified": False}
        try:
            size = wintypes.DWORD()
            adv.GetTokenInformation(token, TOKEN_USER, None, 0, ctypes.byref(size))
            if not size.value or size.value > 4096:
                return {"status": "IDENTITY_UNOBSERVABLE",
                        "isolation_verified": False}
            buf = ctypes.create_string_buffer(size.value)
            if not adv.GetTokenInformation(token, TOKEN_USER, buf, size,
                                           ctypes.byref(size)):
                return {"status": "IDENTITY_UNOBSERVABLE",
                        "isolation_verified": False}
            sid_pointer = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
            sid_text = wintypes.LPWSTR()
            if not adv.ConvertSidToStringSidW(sid_pointer,
                                               ctypes.byref(sid_text)):
                return {"status": "IDENTITY_UNOBSERVABLE",
                        "isolation_verified": False}
            try:
                return {"status": "IDENTITY_OBSERVED",
                        "principal": sid_text.value,
                        "isolation_verified": False}
            finally:
                kernel.LocalFree(ctypes.cast(sid_text, wintypes.HLOCAL))
        finally:
            kernel.CloseHandle(token)
    return {"status": "IDENTITY_UNOBSERVABLE",
            "isolation_verified": False}


def assess_host_isolation() -> dict:
    identity = current_os_identity()
    return {
        "status": "HOST_OS_ISOLATION_NOT_ATTESTED",
        "identity": identity,
        "restricted_os_account_verified": False,
        "dev_sealed_acl_verified": False,
        "trusted_authorization_store_verified": False,
        "trusted_runner_catalog_acl_verified": False,
        "network_isolation_verified": False,
        "gpu_limits_enforced": False,
        "execution_authorized": False,
        "note": "An observed SID/UID is not proof of a restricted host or user grant.",
    }
