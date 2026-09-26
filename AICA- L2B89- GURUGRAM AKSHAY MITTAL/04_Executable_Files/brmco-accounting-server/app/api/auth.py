"""/api/v1/auth — user and Local Host authentication (Phase 5).

Planned endpoints:
    POST /api/v1/auth/token          user login -> short-lived access token
    POST /api/v1/auth/device         register a Local Host installation -> device token
    POST /api/v1/auth/refresh
"""
from app.api._placeholder import placeholder_router

router = placeholder_router("auth", 5, "User, client and Local Host device authentication.")
