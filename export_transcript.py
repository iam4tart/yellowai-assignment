import json
import re
import os

SOURCE_PATH = r"C:\Users\4TT4\.gemini\antigravity\brain\ae14fa44-2826-47ec-8736-2d3050658585\.system_generated\logs\transcript_full.jsonl"
OUTPUT_PATH = r"d:\Hackaton\yellow.ai\conversation_transcript.jsonl"

def clean_user_prompt(raw_text: str) -> str:
    matches = re.findall(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_text, re.DOTALL)
    if matches:
        return "\n\n".join(m.strip() for m in matches).strip()
    return raw_text.strip()

def export_transcript():
    if not os.path.exists(SOURCE_PATH):
        raise FileNotFoundError(f"Source transcript not found at {SOURCE_PATH}")

    entries = []
    current_turn = 0

    with open(SOURCE_PATH, "r", encoding="utf-8") as infile:
        for line in infile:
            if not line.strip():
                continue
            data = json.loads(line)
            record_type = data.get("type")
            source = data.get("source")
            content = data.get("content", "")
            timestamp = data.get("created_at")

            if record_type == "USER_INPUT" and source == "USER_EXPLICIT":
                current_turn += 1
                prompt = clean_user_prompt(content)
                entries.append({
                    "turn": current_turn,
                    "role": "user",
                    "timestamp": timestamp,
                    "content": prompt
                })

            elif record_type == "PLANNER_RESPONSE" and source == "MODEL" and content:
                entries.append({
                    "turn": current_turn,
                    "role": "assistant",
                    "timestamp": timestamp,
                    "content": content.strip()
                })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:
        for entry in entries:
            outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Exported {len(entries)} conversation turns to {OUTPUT_PATH}")

if __name__ == "__main__":
    export_transcript()
