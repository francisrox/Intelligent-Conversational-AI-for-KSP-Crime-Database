import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_connection

JWT_SECRET = os.getenv("JWT_SECRET", "ksp_dev_secret_change_before_any_real_deployment")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 120

VALID_ROLES = ["Admin", "Supervisor", "Investigator", "Analyst", "Viewer"]

security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def authenticate_user(username: str, password: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    _id, uname, pw_hash, role = row
    if not verify_password(password, pw_hash):
        return None
    return {"username": uname, "role": role}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency: any endpoint that takes this just requires a valid,
    unexpired token — doesn't check role."""
    payload = decode_access_token(credentials.credentials)
    return {"username": payload["sub"], "role": payload["role"]}


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: use as Depends(require_role("Admin", "Supervisor"))
    to restrict an endpoint to specific roles, on top of just being logged in."""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' cannot access this resource. Requires one of: {list(allowed_roles)}",
            )
        return user

    return checker


def log_audit(user: dict, action: str, endpoint: str, detail: str = ""):
    """Never let audit logging itself break the actual request it's logging."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log (username, action, endpoint, detail) VALUES (%s, %s, %s, %s)",
            (user.get("username"), action, endpoint, detail),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass
