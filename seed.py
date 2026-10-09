from datetime import datetime, timezone
from database import init_db, get_db

def seed_database():
    init_db()
    
    now = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Seed Workspaces
        workspaces = [
            ("acme", "Acme Corp"),
            ("globex", "Globex Corp")
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO workspaces (id, name) VALUES (?, ?)",
            workspaces
        )
        
        # 2. Seed Agents (2 per workspace with fixed tokens)
        agents = [
            ("agent_acme_1", "acme", "Alice (Acme)", "token_acme_1"),
            ("agent_acme_2", "acme", "Bob (Acme)", "token_acme_2"),
            ("agent_globex_1", "globex", "Charlie (Globex)", "token_globex_1"),
            ("agent_globex_2", "globex", "Dana (Globex)", "token_globex_2"),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO agents (id, workspace_id, name, token) VALUES (?, ?, ?, ?)",
            agents
        )
        
        # 3. Seed Initial Sample Conversations
        conversations = [
            ("conv_acme_1", "acme", "Sarah Connor", "unassigned", None, now, now),
            ("conv_acme_2", "acme", "John Doe", "assigned", "agent_acme_1", now, now),
            ("conv_globex_1", "globex", "Bruce Wayne", "unassigned", None, now, now)
        ]
        cursor.executemany(
            """
            INSERT OR REPLACE INTO conversations 
            (id, workspace_id, customer_name, status, assigned_agent_id, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            conversations
        )
        
        # 4. Seed Initial Messages
        messages = [
            ("msg_seed_1", "conv_acme_1", "acme", "customer", "Sarah Connor", "Where is my order #1001?", now, now),
            ("msg_seed_2", "conv_acme_2", "acme", "customer", "John Doe", "Need return policy details.", now, now),
            ("msg_seed_3", "conv_acme_2", "acme", "agent", "Alice (Acme)", "Hello John, our return window is 30 days.", now, now),
            ("msg_seed_4", "conv_globex_1", "globex", "customer", "Bruce Wayne", "Can you deliver to Gotham City?", now, now)
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO messages 
            (id, conversation_id, workspace_id, sender_type, sender_name, text, sent_at, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            messages
        )
        
        conn.commit()
        print("Database seeded successfully:")
        print("  - Workspaces: acme, globex")
        print("  - Agents: Alice & Bob (Acme), Charlie & Dana (Globex)")
        print("  - Initial Conversations: conv_acme_1 (unassigned), conv_acme_2 (Alice), conv_globex_1 (unassigned)")

if __name__ == "__main__":
    seed_database()
