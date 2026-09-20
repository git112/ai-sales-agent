from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.core.config import settings
from app.core.security import decode_token
from app.store import get_all, get_by_id

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    authorization: str | None = Header(default=None),
):
    token = None
    if creds:
        token = creds.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = get_by_id("users", payload.get("sub"))
    if not user:
        raise HTTPException(401, "User not found")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Account suspended")
    return user


def require_admin(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return user


def workspace_id(user=Depends(current_user), x_workspace_id: str | None = Header(default=None)):
    wid = x_workspace_id or user.get("workspace_id")
    if user.get("role") == "admin":
        if not wid:
            workspaces = get_all("workspaces")
            if not workspaces:
                raise HTTPException(400, "Workspace required")
            wid = workspaces[0]["id"]
        ws = get_by_id("workspaces", wid)
        if not ws:
            raise HTTPException(404, "Workspace not found")
        return wid
    if not wid:
        raise HTTPException(400, "Workspace required")
    if user.get("workspace_id") and wid != user.get("workspace_id"):
        raise HTTPException(404, "Not found")
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return wid
