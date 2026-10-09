from pydantic import BaseModel, Field
from typing import Optional, List

# Webhook Models
class InboundWebhookPayload(BaseModel):
    workspace: str
    conversation_id: str
    message_id: str
    customer_name: str
    text: str
    sent_at: str

class WebhookResponse(BaseModel):
    status: str
    message_id: str
    conversation_id: str
    deduplicated: bool

# Conversation Models
class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_name: str
    text: str
    sent_at: str

class OutboundMessageCreate(BaseModel):
    text: str

class ConversationSummary(BaseModel):
    id: str
    customer_name: str
    status: str
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    last_message_text: Optional[str] = None
    last_message_sent_at: Optional[str] = None
    waiting_since: str
    waiting_seconds: int

class ConversationDetail(BaseModel):
    id: str
    customer_name: str
    status: str
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    messages: List[MessageOut]

class ClaimResponse(BaseModel):
    status: str
    conversation_id: str
    assigned_to: dict
