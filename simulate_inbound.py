import time
import uuid
from datetime import datetime, timezone
import httpx

API_URL = "http://127.0.0.1:8000/webhooks/inbound"
SECRET = "whsec_yellow_test_secret"

SIMULATED_MESSAGES = [
    ("acme", "Tony Stark", "Where is my arc reactor order?"),
    ("acme", "Peter Parker", "Can I return the spider suit?"),
    ("globex", "Clark Kent", "Delivery to Daily Planet is delayed."),
    ("acme", "Natasha Romanoff", "Package delivered to wrong address."),
    ("globex", "Diana Prince", "Need express shipping to Themyscira."),
    ("acme", "Bruce Banner", "Item arrived damaged, please replace."),
    ("acme", "Stephen Strange", "Refund status on Eye of Agamotto."),
    ("globex", "Barry Allen", "Order was supposed to arrive in a flash."),
    ("acme", "Wanda Maximoff", "How do I cancel my subscription?"),
    ("globex", "Arthur Curry", "Do you deliver offshore to Atlantis?"),
    ("acme", "Thor Odinson", "Payment went through twice for Mjolnir."),
    ("globex", "Hal Jordan", "Need warranty details on the ring."),
]

def run_simulation(duration_seconds=60):
    interval = duration_seconds / len(SIMULATED_MESSAGES)
    print("==================================================")
    print(f"  LIVE WEBHOOK SIMULATOR STARTED")
    print(f"  Sending {len(SIMULATED_MESSAGES)} messages over {duration_seconds} seconds (~{interval:.1f}s each)")
    print(f"  Watch your browser at http://127.0.0.1:8000 !")
    print("==================================================\n")

    client = httpx.Client()

    for idx, (ws, customer, text) in enumerate(SIMULATED_MESSAGES, 1):
        conv_id = f"conv_sim_{idx}"
        msg_id = f"msg_sim_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "workspace": ws,
            "conversation_id": conv_id,
            "message_id": msg_id,
            "customer_name": customer,
            "text": text,
            "sent_at": now
        }

        try:
            res = client.post(
                API_URL,
                json=payload,
                headers={"X-Webhook-Secret": SECRET}
            )
            print(f"[{idx}/{len(SIMULATED_MESSAGES)}] [{ws.upper()}] Sent: {customer} -> '{text}' (HTTP {res.status_code})")
        except Exception as e:
            print(f"[{idx}] Failed to connect to server: {e}")
            print("Make sure the server is running on http://127.0.0.1:8000")
            break

        time.sleep(interval)

    print("\nSimulation complete! All messages injected.")

if __name__ == "__main__":
    run_simulation(duration_seconds=60)
