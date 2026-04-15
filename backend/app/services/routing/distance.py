"""Distance / duration providers for the routing solver.

Each provider exposes an asynchronous :meth:`matrix` method returning a
pair ``(distance_m, duration_s)`` as NxN lists of floats. The default
:class:`HaversineProvider` requires no external service and no network.

OSRM and OpenRouteService providers are lazily importing :mod:`httpx`;
if ``httpx`` is not available, :func:`get_provider` transparently falls
back to :class:`HaversineProvider` with a runtime warning.
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.services.routing.models import Coordinate

logger = logging.getLogger(__name__)

EARTH_RADIUS_M: float = 6_371_000.0


# --------------------------------------------------------------------------- #
# Core geometric helpers
# --------------------------------------------------------------------------- #


def haversine(a: Coordinate, b: Coordinate) -> float:
    """Great-circle distance between two WGS-84 coordinates, in meters."""
    phi1 = math.radians(a.lat)
    phi2 = math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlambda = math.radians(b.lon - a.lon)

    sin_dphi = math.sin(dphi / 2.0)
    sin_dlambda = math.sin(dlambda / 2.0)
    inner = sin_dphi * sin_dphi + math.cos(phi1) * math.cos(phi2) * sin_dlambda * sin_dlambda
    inner = min(1.0, max(0.0, inner))
    c = 2.0 * math.asin(math.sqrt(inner))
    return EARTH_RADIUS_M * c


# --------------------------------------------------------------------------- #
# Provider protocol
# --------------------------------------------------------------------------- #


@runtime_checkable
class DistanceProvider(Protocol):
    """Protocol for synchronous matrix providers.

    Implementations must return two NxN matrices (meters and seconds).
    Although some implementations do I/O, we keep the interface
    synchronous so that the OR-Tools solver (also sync) can use it
    directly. Async implementations wrap their calls via
    :func:`_run_sync`.
    """

    def matrix(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]: ...


# --------------------------------------------------------------------------- #
# Haversine fallback
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HaversineProvider:
    """Offline great-circle provider.

    Travel time is derived from a constant ``speed_kmh`` (default 30 km/h,
    roughly urban average for home-care deliveries).
    """

    speed_kmh: float = 30.0

    def matrix(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]:
        n = len(coords)
        dist: list[list[float]] = [[0.0] * n for _ in range(n)]
        dur: list[list[float]] = [[0.0] * n for _ in range(n)]
        speed_mps = max(self.speed_kmh, 0.1) * 1000.0 / 3600.0
        for i in range(n):
            for j in range(i + 1, n):
                d = haversine(coords[i], coords[j])
                dist[i][j] = d
                dist[j][i] = d
                t = d / speed_mps
                dur[i][j] = t
                dur[j][i] = t
        return dist, dur


# --------------------------------------------------------------------------- #
# OSRM provider (async httpx under the hood, sync wrapper)
# --------------------------------------------------------------------------- #


def _run_sync(coro: Any) -> Any:
    """Run an ``async def`` coroutine from sync code.

    Uses a fresh event loop so that it works whether or not the caller
    is already inside a running loop. We explicitly *do not* reuse a
    running loop: OR-Tools calls us synchronously from a worker thread.
    """
    import asyncio

    return asyncio.new_event_loop().run_until_complete(coro)


@dataclass(frozen=True, slots=True)
class OSRMProvider:
    """OSRM ``/table/v1`` client.

    The ``base_url`` should point to the public entry, e.g.
    ``http://localhost:5000`` or ``https://router.project-osrm.org``.
    """

    base_url: str
    timeout_seconds: float = 15.0

    def matrix(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]:
        return _run_sync(self._matrix_async(coords))

    async def _matrix_async(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - guarded by factory
            raise RuntimeError(
                "httpx is required for OSRMProvider. Install `httpx` or switch "
                "ROUTING_PROVIDER to `haversine`."
            ) from exc

        coord_str = ";".join(f"{c.lon:.6f},{c.lat:.6f}" for c in coords)
        url = f"{self.base_url.rstrip('/')}/table/v1/driving/{coord_str}"
        params = {"annotations": "distance,duration"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        distances = data.get("distances")
        durations = data.get("durations")
        if distances is None or durations is None:
            raise RuntimeError("OSRM response missing distances/durations")
        return (
            [[float(x) for x in row] for row in distances],
            [[float(x) for x in row] for row in durations],
        )


# --------------------------------------------------------------------------- #
# OpenRouteService provider
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class OpenRouteServiceProvider:
    """OpenRouteService ``/v2/matrix/driving-car`` client."""

    api_key: str
    base_url: str = "https://api.openrouteservice.org"
    timeout_seconds: float = 20.0

    def matrix(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]:
        return _run_sync(self._matrix_async(coords))

    async def _matrix_async(
        self, coords: list[Coordinate]
    ) -> tuple[list[list[float]], list[list[float]]]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - guarded by factory
            raise RuntimeError(
                "httpx is required for OpenRouteServiceProvider."
            ) from exc

        url = f"{self.base_url.rstrip('/')}/v2/matrix/driving-car"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "locations": [[c.lon, c.lat] for c in coords],
            "metrics": ["distance", "duration"],
            "units": "m",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        distances = data.get("distances")
        durations = data.get("durations")
        if distances is None or durations is None:
            raise RuntimeError("ORS response missing distances/durations")
        return (
            [[float(x) for x in row] for row in distances],
            [[float(x) for x in row] for row in durations],
        )


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def _httpx_available() -> bool:
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


def get_provider(settings: Any) -> DistanceProvider:
    """Return a provider instance chosen from ``settings``.

    ``settings`` is expected to expose the attributes:

    * ``ROUTING_PROVIDER`` — ``"haversine" | "osrm" | "openrouteservice"``.
    * ``OSRM_BASE_URL`` — used when provider is ``osrm``.
    * ``OPENROUTESERVICE_API_KEY`` — used when provider is
      ``openrouteservice``.

    When an HTTP-based provider is selected but ``httpx`` is missing,
    or the necessary config is empty, we warn and fall back to
    :class:`HaversineProvider` rather than crashing the solver.
    """
    provider = getattr(settings, "ROUTING_PROVIDER", "haversine") or "haversine"
    provider = provider.lower()
    speed = float(getattr(settings, "ROUTING_SPEED_KMH", 30.0) or 30.0)

    if provider == "haversine":
        return HaversineProvider(speed_kmh=speed)

    if provider == "osrm":
        base_url = getattr(settings, "OSRM_BASE_URL", None)
        if not base_url:
            warnings.warn(
                "ROUTING_PROVIDER=osrm but OSRM_BASE_URL is empty; "
                "falling back to HaversineProvider.",
                RuntimeWarning,
                stacklevel=2,
            )
            return HaversineProvider(speed_kmh=speed)
        if not _httpx_available():
            warnings.warn(
                "httpx not installed; OSRM provider unavailable. "
                "Falling back to HaversineProvider.",
                RuntimeWarning,
                stacklevel=2,
            )
            return HaversineProvider(speed_kmh=speed)
        return OSRMProvider(base_url=str(base_url))

    if provider == "openrouteservice":
        key = getattr(settings, "OPENROUTESERVICE_API_KEY", None)
        if not key:
            warnings.warn(
                "ROUTING_PROVIDER=openrouteservice but key is empty; "
                "falling back to HaversineProvider.",
                RuntimeWarning,
                stacklevel=2,
            )
            return HaversineProvider(speed_kmh=speed)
        if not _httpx_available():
            warnings.warn(
                "httpx not installed; ORS provider unavailable. "
                "Falling back to HaversineProvider.",
                RuntimeWarning,
                stacklevel=2,
            )
            return HaversineProvider(speed_kmh=speed)
        return OpenRouteServiceProvider(api_key=str(key))

    warnings.warn(
        f"Unknown ROUTING_PROVIDER={provider!r}; falling back to HaversineProvider.",
        RuntimeWarning,
        stacklevel=2,
    )
    return HaversineProvider(speed_kmh=speed)


__all__ = [
    "DistanceProvider",
    "HaversineProvider",
    "OSRMProvider",
    "OpenRouteServiceProvider",
    "get_provider",
    "haversine",
]
