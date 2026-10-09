# Yellow.ai Agent Inbox — Implementation Plan

> **Tech Stack**: Python (FastAPI + Uvicorn), SQLite (native `sqlite3`), Plain HTML/JS frontend.  
> **Progress Tracker**: Check off each step upon completion and verification.

---

### Progress

- [x] **Step 1: Database Schema & Seeding**
  - **Files**: `database.py`, `seed.py`
  - **Deliverables**: SQLite schema (`workspaces`, `agents`, `conversations`, `messages`), indices for performance, and seed script creating `acme` & `globex` with 2 agents each + fixed bearer tokens.
  - **Verification**: Run `python seed.py`, assert records exist in SQLite DB.

- [x] **Step 2: Inbound Webhook & Deduplication**
  - **Files**: `routers/webhooks.py`, `schemas.py`
  - **Deliverables**: `POST /webhooks/inbound` endpoint verifying `X-Webhook-Secret`. Upserts conversation and inserts messages using atomic `INSERT OR IGNORE`.
  - **Verification**: Test duplicate payload submissions; ensure exact single record is stored and `200/201` returned.

- [x] **Step 3: Agent Authentication & Queue Views**
  - **Files**: `dependencies.py`, `routers/conversations.py`
  - **Deliverables**: Bearer token authentication middleware; `GET /conversations?view=unassigned|mine` scoped to workspace; `GET /conversations/:id` with strict tenant boundary (returns 404 on cross-tenant access) and messages ordered chronologically by `sent_at ASC`.
  - **Verification**: Query conversations with `token_acme_1` vs `token_globex_1`; verify tenant isolation.

- [x] **Step 4: Atomic Claiming & Reply Handling**
  - **Files**: `routers/conversations.py`
  - **Deliverables**: 
    - `POST /conversations/:id/claim` using atomic `UPDATE ... WHERE assigned_agent_id IS NULL` (returns `200` on success, `409 Conflict` with current owner details if already claimed).
    - `POST /conversations/:id/messages` to post outbound agent replies (enforce only assigned agent can reply; returns `403` otherwise).
  - **Verification**: Verify claim locking and reject unauthorized replies.

- [x] **Step 5: Automated Test Suite (The Proofs)**
  - **Files**: `test_suite.py`
  - **Deliverables**: Standalone automated test script proving:
    - (a) Two concurrent claims $\rightarrow$ exactly one wins (`200`), one conflicts (`409`).
    - (b) Same `message_id` posted twice $\rightarrow$ exactly 1 message stored.
    - (c) Cross-tenant request (Acme agent accessing Globex conversation) $\rightarrow$ `404 Not Found`.
  - **Verification**: Run `python test_suite.py` with all assertions passing.

- [x] **Step 6: Frontend UI (Polling & Live Inbox)**
  - **Files**: `ui/index.html`, `ui/app.js`, `ui/style.css`
  - **Deliverables**: Clean, responsive UI with:
    - Agent switch dropdown (test between Acme 1, Acme 2, Globex 1, Globex 2).
    - Queue sidebar (`Unassigned` vs `Mine`, customer name, snippet, waiting timer).
    - Conversation thread pane (chat bubbles sorted by `sent_at`, claim button, reply input).
    - Polling interval (2s) to fetch new inbound messages without page reload.
  - **Verification**: Load app in browser, trigger inbound webhook, observe real-time updates and claim flow.

- [x] **Step 7: README & Observability**
  - **Files**: `README.md`
  - **Deliverables**: Complete documentation on running, seeding, architecture rationale, and observability/diagnostics ("how you tell it's broken").
  - **Verification**: Clean setup reproduction from README commands.