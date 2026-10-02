"""Minimal role-based access (viewer < analyst < admin) using static bearer tokens from settings.

API_TOKENS="token1:admin:alice,token2:analyst:bob". Personal data (employees, contacts, raw rows of personal-data
modules) requires admin. In development with no tokens configured the caller is a local admin; outside
development, no tokens configured means every request is refused (fail closed). Replace with SSO later.
"""
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from app.config import get_settings

LEVEL = {"viewer": 1, "analyst": 2, "admin": 3}


@dataclass(frozen=True)
class Principal:
    name: str
    role: str

    def at_least(self, role: str) -> bool:
        return LEVEL[self.role] >= LEVEL[role]


def _tokens() -> dict[str, Principal]:
    out: dict[str, Principal] = {}
    for item in filter(None, (t.strip() for t in get_settings().api_tokens.split(","))):
        parts = item.split(":")
        if len(parts) >= 2 and parts[1] in LEVEL:
            out[parts[0]] = Principal(parts[2] if len(parts) > 2 else parts[1], parts[1])
    return out


def get_principal(request: Request) -> Principal:
    settings = get_settings()
    tokens = _tokens()
    if not tokens:
        if settings.app_env == "development":
            return Principal("local-dev", "admin")
        raise HTTPException(401, "Authentication is not configured")
    header = request.headers.get("authorization", "")
    supplied = header[7:] if header.lower().startswith("bearer ") else ""
    for token, principal in tokens.items():
        if supplied and secrets.compare_digest(supplied, token):
            return principal
    raise HTTPException(401, "Invalid or missing bearer token")


def require(role: str):
    def dep(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.at_least(role):
            raise HTTPException(403, f"Requires role '{role}'")
        return principal
    return dep
