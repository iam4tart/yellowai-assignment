from fastapi import Header, HTTPException, status
from database import get_db

def get_current_agent(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'"
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, workspace_id, name FROM agents WHERE token = ?", (token,))
        agent = cursor.fetchone()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent token"
            )

        return {
            "id": agent["id"],
            "workspace_id": agent["workspace_id"],
            "name": agent["name"]
        }
