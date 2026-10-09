import concurrent.futures
import threading
import sqlite3
from fastapi.testclient import TestClient
from main import app
from seed import seed_database

client = TestClient(app)

# 1. Tests that identical message_id retries are stored only once (idempotent).
def test_webhook_deduplication():
    headers = {"X-Webhook-Secret": "whsec_yellow_test_secret"}
    payload = {
        "workspace": "acme", "conversation_id": "c_dedup", "message_id": "m_dedup",
        "customer_name": "Alice", "text": "Hi", "sent_at": "2026-10-09T00:00:00Z"
    }

    res1 = client.post("/webhooks/inbound", json=payload, headers=headers)
    res2 = client.post("/webhooks/inbound", json=payload, headers=headers)

    conn = sqlite3.connect("agent_inbox.db")
    count = conn.execute("SELECT COUNT(*) FROM messages WHERE id = 'm_dedup'").fetchone()[0]
    conn.close()

    assert res1.status_code == 201 and res1.json()["deduplicated"] is False
    assert res2.status_code == 200 and res2.json()["deduplicated"] is True
    assert count == 1
    print("PASS: test_webhook_deduplication")

# 2. Tests that an agent cannot view or act on another workspace's conversations (returns 404).
def test_tenant_isolation():
    acme_auth = {"Authorization": "Bearer token_acme_1"}
    globex_auth = {"Authorization": "Bearer token_globex_1"}

    assert client.get("/conversations/conv_globex_1", headers=acme_auth).status_code == 404
    assert client.post("/conversations/conv_globex_1/claim", headers=acme_auth).status_code == 404
    assert client.get("/conversations/conv_globex_1", headers=globex_auth).status_code == 200
    print("PASS: test_tenant_isolation")

# 3. Tests that simultaneous claims result in exactly one winner (200) and one conflict (409).
def test_concurrent_claims():
    barrier = threading.Barrier(2)

    def claim(token):
        barrier.wait()
        return client.post("/conversations/conv_acme_1/claim", headers={"Authorization": f"Bearer {token}"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(claim, "token_acme_1")
        f2 = pool.submit(claim, "token_acme_2")
        statuses = [f1.result().status_code, f2.result().status_code]

    assert sorted(statuses) == [200, 409]
    print("PASS: test_concurrent_claims")

# 4. Tests that only the assigned agent can reply to a conversation.
def test_reply_authorization():
    alice_auth = {"Authorization": "Bearer token_acme_1"}
    bob_auth = {"Authorization": "Bearer token_acme_2"}

    assert client.post("/conversations/conv_acme_2/messages", headers=alice_auth, json={"text": "Hello"}).status_code == 201
    assert client.post("/conversations/conv_acme_2/messages", headers=bob_auth, json={"text": "Interfere"}).status_code == 403
    print("PASS: test_reply_authorization")

# 5. Tests that messages are returned in chronological order (sent_at ASC).
def test_chronological_ordering():
    auth = {"Authorization": "Bearer token_acme_1"}
    res = client.get("/conversations/conv_acme_2", headers=auth)
    timestamps = [m["sent_at"] for m in res.json()["messages"]]

    assert timestamps == sorted(timestamps)
    print("PASS: test_chronological_ordering")

if __name__ == "__main__":
    seed_database()
    print("------------------------------------------")
    test_webhook_deduplication()
    test_tenant_isolation()
    test_concurrent_claims()
    test_reply_authorization()
    test_chronological_ordering()
    print("------------------------------------------")
    print("ALL 5 CORE TESTS PASSED")
