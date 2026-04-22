import sqlite3
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

class AgentTracer:
    """
    SQLite-based tracer for recording Agno agent activities.
    Supports recording agent starts, tool calls, and results.
    """
    
    def __init__(self, db_path: str = "data/traces.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    agent_name TEXT,
                    event_type TEXT,
                    payload TEXT
                )
            """)
            conn.commit()

    def record_event(self, event_type: str, agent_name: str, payload: Dict[str, Any], session_id: Optional[str] = None):
        """
        Records an event in the trace database.
        
        event_type: 'agent_start' | 'tool_call' | 'tool_result' | 'agent_stop'
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO traces (session_id, agent_name, event_type, payload) VALUES (?, ?, ?, ?)",
                (session_id or "default", agent_name, event_type, json.dumps(payload))
            )
            conn.commit()

    def get_traces(self, limit: int = 50):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM traces ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Singleton instance
tracer = AgentTracer()
