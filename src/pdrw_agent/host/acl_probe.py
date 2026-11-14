"""Operator-only synthetic ACL fixture probe.

An independently provisioned restricted account must run this on the real
Windows host. This observes whether the *current* OS principal can read one
synthetic DEV marker and is denied one synthetic SEALED marker; it never opens
real project data and NEVER grants a research execution permission.

This diagnostic is not a sandbox, grant verifier, or OS-level attestation.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..config import Settings
from ..schemas import AgentError
from .isolation import current_os_identity

DEV_NAME = "dev-readable.fixture"
DENIED_NAME = "sealed-denied.fixture"
DEV_MARKER = b"PDRW_ACL_PROBE_V1_DEV\n"


def _bounded_fixture_path(settings: Settings, project_id: str, raw: str,
                          expected_name: str) -> Path:
    if not isinstance(raw, str) or not raw or len(raw) > 2048:
        raise AgentError("ACL_FIXTURE_PATH_INVALID", "Expected a bounded absolute path")
    original = Path(raw).expanduser()
    if not original.is_absolute() or original.name != expected_name:
        raise AgentError("ACL_FIXTURE_PATH_INVALID",
                         "Only named synthetic fixture paths are permitted")
    # Reject symlinked lexical components, including a symlink that resolves
    # to an apparently innocuous path. No real SEALED files are permissible.
    cursor = original
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise AgentError("ACL_FIXTURE_SYMLINK", "Symlinked fixture paths not permitted")
        cursor = cursor.parent
    resolved = original.resolve(strict=False)
    project, _ = settings.project(project_id)
    for forbidden in (project, settings.workflow_root, settings.project_map.parent):
        anchor = forbidden.resolve()
        if resolved == anchor or anchor in resolved.parents:
            raise AgentError("ACL_FIXTURE_IN_PROTECTED_TREE",
                             "Use isolated synthetic fixtures outside all research roots")
    return original


def probe_host_fixture_acl(settings: Settings, project_id: str,
                           dev_fixture: str, denied_fixture: str) -> dict:
    """Read no more than one synthetic DEV marker and 1 denied-fixture byte.

    Only current-account observations are returned. Denial may mean a missing
    path component or policy other than the intended ACL; independent host
    account and fixture provisioning must be verified out of band.
    """
    allowed = _bounded_fixture_path(settings, project_id, dev_fixture, DEV_NAME)
    denied = _bounded_fixture_path(settings, project_id, denied_fixture, DENIED_NAME)
    if allowed.parent.resolve() != denied.parent.resolve():
        raise AgentError("ACL_FIXTURE_SCOPE_MISMATCH",
                         "The two synthetic fixtures must share one parent")
    base = {
        "project_id": project_id, "identity_observation": current_os_identity(),
        "execution_authorized": False,
        "trusted_host_authenticated": False,
        "original_user_grant_verified": False,
        "real_dev_sealed_access_verified": False,
        "synthetic_fixture_only": True,
    }
    try:
        with allowed.open("rb") as handle:
            marker = handle.read(len(DEV_MARKER) + 1)
    except (OSError, ValueError):
        return {**base, "status": "HOST_DEV_FIXTURE_UNREADABLE",
                "dev_marker_matched": False, "denied_fixture_checked": False}
    if marker != DEV_MARKER:
        return {**base, "status": "HOST_DEV_FIXTURE_MARKER_INVALID",
                "dev_marker_matched": False, "denied_fixture_checked": False}
    try:
        with denied.open("rb") as handle:
            handle.read(1)
    except PermissionError:
        return {**base, "status": "HOST_FIXTURE_ACL_DENIAL_OBSERVED_ONLY",
                "dev_marker_matched": True,
                "denied_fixture_checked": True,
                "denied_fixture_os_access": "PERMISSION_DENIED",
                "next": "VERIFY_RESTRICTED_OS_SID_AND_ORIGINAL_POLICY_OUT_OF_BAND"}
    except (OSError, ValueError):
        return {**base, "status": "HOST_DENIED_FIXTURE_INCONCLUSIVE",
                "dev_marker_matched": True,
                "denied_fixture_checked": False}
    return {**base, "status": "HOST_FIXTURE_ACL_GAP",
            "dev_marker_matched": True,
            "denied_fixture_checked": True,
            "denied_fixture_os_access": "READ_SUCCEEDED",
            "next": "CONFIGURE_SYNTHETIC_FIXTURE_ACL_BEFORE_REAL_DEV"}
