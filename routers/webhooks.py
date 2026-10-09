import os
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Response, status
from database import get_db
from schemas import InboundWebhookPayload, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "whsec_yellow_test_secret")

@router.post(
    "/inbound",
    response_model=WebhookResponse,
    summary="Ingest inbound messages from channel provider"
)
def handle_inbound_webhook(
    payload: InboundWebhookPayload,
    response: Response,
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret")
):
    # 1. Enforce Webhook Secret Authentication
    if not x_webhook_secret or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid X-Webhook-Secret header"
        )

    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # 2. Verify workspace exists
        cursor.execute("SELECT id FROM workspaces WHERE id = ?", (payload.workspace,))
        ws = cursor.fetchone()
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workspace '{payload.workspace}' does not exist"
            )

        # 3. Upsert Conversation (create as 'unassigned' if new, touch updated_at if existing)
        cursor.execute(
            """
            INSERT INTO conversations (id, workspace_id, customer_name, status, assigned_agent_id, created_at, updated_at)
            VALUES (?, ?, ?, 'unassigned', NULL, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (payload.conversation_id, payload.workspace, payload.customer_name, now, now)
        )

        # 4. Atomic Deduplication for Message
        # INSERT OR IGNORE leverages SQLite's PRIMARY KEY constraint on messages.id
        cursor.execute(
            """
            INSERT OR IGNORE INTO messages 
            (id, conversation_id, workspace_id, sender_type, sender_name, text, sent_at, created_at)
            VALUES (?, ?, ?, 'customer', ?, ?, ?, ?)
            """,
            (
                payload.message_id,
                payload.conversation_id,
                payload.workspace,
                payload.customer_name,
                payload.text,
                payload.sent_at,
                now
            )
        )

        is_new_message = cursor.rowcount > 0
        conn.commit()

        # 5. Return 201 for fresh message, 200 for idempotent duplicate
        if is_new_message:
            response.status_code = status.HTTP_201_CREATED
            return WebhookResponse(
                status="created",
                message_id=payload.message_id,
                conversation_id=payload.conversation_id,
                deduplicated=False
            )
        else:
            response.status_code = status.HTTP_200_OK
            return WebhookResponse(
                status="ignored_duplicate",
                message_id=payload.message_id,
                conversation_id=payload.conversation_id,
                deduplicated=True
            )
