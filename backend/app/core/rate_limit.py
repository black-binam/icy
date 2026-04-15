"""Rate-limit plumbing via slowapi."""
from __future__ import annotations

import ipaddress

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def _trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in settings.trusted_proxy_cidrs_list:
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            # Silently skip malformed entries; they would be a config bug,
            # not a request to deny.
            continue
    return nets


_TRUSTED_NETS = _trusted_networks()


def _peer_in_trusted_networks(peer: str | None) -> bool:
    if not peer or not _TRUSTED_NETS:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in net for net in _TRUSTED_NETS)


def client_ip(request: Request) -> str:
    """Return the real client IP.

    Only honours `X-Forwarded-For` if the immediate peer is in a configured
    trusted-proxy CIDR. Otherwise the header is ignored to prevent spoofing
    of rate-limit keys and audit-log IPs.
    """
    peer = request.client.host if request.client else None
    if _peer_in_trusted_networks(peer):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            # Take the leftmost (original client) entry.
            return fwd.split(",")[0].strip()
    return peer or get_remote_address(request)


def _key_func(request: Request) -> str:
    return client_ip(request)


limiter = Limiter(key_func=_key_func, default_limits=[], headers_enabled=False)

LOGIN_LIMIT = settings.LOGIN_RATE_LIMIT
