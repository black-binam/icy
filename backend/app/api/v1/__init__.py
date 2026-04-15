"""API v1 aggregate router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, caregivers, patients, pathologies, routes, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(caregivers.router)
api_router.include_router(pathologies.router)
api_router.include_router(routes.router)

__all__ = ["api_router"]
