import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, responses
from database import get_db
from dependencies import get_current_agent
from schemas import (
    ConversationSummary,
    ConversationDetail,
    MessageOut,
    OutboundMessageCreate,
    ClaimResponse
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

def parse_iso(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)

@router.get("", response_model=List[ConversationSummary])
def list_conversations(
    view: str = Query("unassigned", pattern="^(unassigned|mine)$"),
    agent: dict = Depends(get_current_agent)
):
    workspace_id = agent["workspace_id"]
    agent_id = agent["id"]
    now = datetime.now(timezone.utc)

    with get_db() as conn:
        cursor = conn.cursor()

        # Build filter according to view
        if view == "unassigned":
            filter_sql = "c.workspace_id = ? AND c.assigned_agent_id IS NULL"
            params = (workspace_id,)
        else:
            filter_sql = "c.workspace_id = ? AND c.assigned_agent_id = ?"
            params = (workspace_id, agent_id)

        query = f"""
            SELECT 
                c.id,
                c.customer_name,
                c.status,
                c.assigned_agent_id,
                a.name AS assigned_agent_name,
                c.created_at,
                (SELECT text FROM messages WHERE conversation_id = c.id ORDER BY sent_at DESC LIMIT 1) AS last_message_text,
                (SELECT sent_at FROM messages WHERE conversation_id = c.id ORDER BY sent_at DESC LIMIT 1) AS last_message_sent_at
            FROM conversations c
            LEFT JOIN agents a ON c.assigned_agent_id = a.id
            WHERE {filter_sql}
            ORDER BY c.created_at ASC
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            waiting_ref = row["last_message_sent_at"] or row["created_at"]
            ref_dt = parse_iso(waiting_ref)
            waiting_secs = max(0, int((now - ref_dt).total_seconds()))

            results.append(
                ConversationSummary(
                    id=row["id"],
                    customer_name=row["customer_name"],
                    status=row["status"],
                    assigned_agent_id=row["assigned_agent_id"],
                    assigned_agent_name=row["assigned_agent_name"],
                    last_message_text=row["last_message_text"],
                    last_message_sent_at=row["last_message_sent_at"],
                    waiting_since=waiting_ref,
                    waiting_seconds=waiting_secs
                )
            )

        return results

@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: str,
    agent: dict = Depends(get_current_agent)
):
    workspace_id = agent["workspace_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Tenant boundary enforcement: must match workspace_id
        cursor.execute(
            """
            SELECT c.id, c.customer_name, c.status, c.assigned_agent_id, a.name AS assigned_agent_name
            FROM conversations c
            LEFT JOIN agents a ON c.assigned_agent_id = a.id
            WHERE c.id = ? AND c.workspace_id = ?
            """,
            (conversation_id, workspace_id)
        )
        conv = cursor.fetchone()

        if not conv:
            # Strictly return 404 to avoid cross-tenant enumeration
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # 2. Fetch messages ordered strictly by sent_at ASC (chronological customer timeline)
        cursor.execute(
            """
            SELECT id, conversation_id, sender_type, sender_name, text, sent_at
            FROM messages
            WHERE conversation_id = ? AND workspace_id = ?
            ORDER BY sent_at ASC
            """,
            (conversation_id, workspace_id)
        )
        messages_rows = cursor.fetchall()

        messages = [
            MessageOut(
                id=m["id"],
                conversation_id=m["conversation_id"],
                sender_type=m["sender_type"],
                sender_name=m["sender_name"],
                text=m["text"],
                sent_at=m["sent_at"]
            )
            for m in messages_rows
        ]

        return ConversationDetail(
            id=conv["id"],
            customer_name=conv["customer_name"],
            status=conv["status"],
            assigned_agent_id=conv["assigned_agent_id"],
            assigned_agent_name=conv["assigned_agent_name"],
            messages=messages
        )

@router.post("/{conversation_id}/claim")
def claim_conversation(
    conversation_id: str,
    agent: dict = Depends(get_current_agent)
):
    workspace_id = agent["workspace_id"]
    agent_id = agent["id"]
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # Atomic conditional update: locks and claims only if unassigned in this tenant
        cursor.execute(
            """
            UPDATE conversations
            SET assigned_agent_id = ?, status = 'assigned', updated_at = ?
            WHERE id = ? AND workspace_id = ? AND assigned_agent_id IS NULL
            """,
            (agent_id, now, conversation_id, workspace_id)
        )
        conn.commit()

        if cursor.rowcount == 1:
            return {
                "status": "claimed",
                "conversation_id": conversation_id,
                "assigned_to": {"id": agent_id, "name": agent["name"]}
            }

        # If 0 rows updated, inspect reason
        cursor.execute(
            """
            SELECT c.id, c.assigned_agent_id, a.name AS agent_name
            FROM conversations c
            LEFT JOIN agents a ON c.assigned_agent_id = a.id
            WHERE c.id = ? AND c.workspace_id = ?
            """,
            (conversation_id, workspace_id)
        )
        conv = cursor.fetchone()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # It was already claimed by another agent
        return responses.JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "ALREADY_CLAIMED",
                "message": "Conversation is already claimed by another agent.",
                "claimed_by": {
                    "id": conv["assigned_agent_id"],
                    "name": conv["agent_name"] or "Another Agent"
                }
            }
        )

@router.post("/{conversation_id}/messages", status_code=status.HTTP_201_CREATED, response_model=MessageOut)
def send_reply(
    conversation_id: str,
    body: OutboundMessageCreate,
    agent: dict = Depends(get_current_agent)
):
    workspace_id = agent["workspace_id"]
    agent_id = agent["id"]
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Verify existence & ownership
        cursor.execute(
            "SELECT assigned_agent_id FROM conversations WHERE id = ? AND workspace_id = ?",
            (conversation_id, workspace_id)
        )
        conv = cursor.fetchone()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # 2. Rule: Only the assigned agent can reply
        if conv["assigned_agent_id"] != agent_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only the assigned agent can reply to this conversation"
            )

        # 3. Store outbound message
        out_msg_id = f"msg_out_{uuid.uuid4().hex[:12]}"
        cursor.execute(
            """
            INSERT INTO messages 
            (id, conversation_id, workspace_id, sender_type, sender_name, text, sent_at, created_at)
            VALUES (?, ?, ?, 'agent', ?, ?, ?, ?)
            """,
            (out_msg_id, conversation_id, workspace_id, agent["name"], body.text, now, now)
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        conn.commit()

        return MessageOut(
            id=out_msg_id,
            conversation_id=conversation_id,
            sender_type="agent",
            sender_name=agent["name"],
            text=body.text,
            sent_at=now
        )
