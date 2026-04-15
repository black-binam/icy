"""Audit helpers: IP anonymization, user-agent hashing, log writer."""
from __future__ import annotations

import hashlib
import ipaddress
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def anonymize_ip(ip: str | None) -> str | None:
    """Truncate an IP: /24 for IPv4, /48 for IPv6."""
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if isinstance(addr, ipaddress.IPv4Address):
        net = ipaddress.ip_network(f"{ip}/24", strict=False)
    else:
        net = ipaddress.ip_network(f"{ip}/48", strict=False)
    return str(net.network_address)


def hash_user_agent(user_agent: str | None) -> str | None:
    """Return first 16 hex chars of SHA-256(user_agent)."""
    if not user_agent:
        return None
    return hashlib.sha256(user_agent.encode("utf-8", errors="replace")).hexdigest()[:16]


def write_audit(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    extra: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist an audit row. Never store business payloads."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_anonymized=anonymize_ip(ip),
        user_agent_hash=hash_user_agent(user_agent),
    )
    if extra is not None:
        # extra is tolerated for lightweight metadata only (never raw patient data).
        entry.extra = extra  # type: ignore[attr-defined]
    db.add(entry)
    db.flush()
    return entry
