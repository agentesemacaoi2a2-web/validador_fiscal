import os
import json
from datetime import datetime

HISTORY_DIR = os.path.join('data', 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)

def save_chat_message(session_id: str, role: str, content: str):
    path = os.path.join(HISTORY_DIR, f'{session_id}.jsonl')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'ts': datetime.utcnow().isoformat(),
            'role': role,
            'content': content
        }, ensure_ascii=False) + "\n")

def load_chat_history(session_id: str, limit: int = 50):
    path = os.path.join(HISTORY_DIR, f'{session_id}.jsonl')
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f.readlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except:
                pass
    return rows
