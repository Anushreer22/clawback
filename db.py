"""
SQLite database for logging events, claims, and approvals.
This provides the audit trail and live trace for the dashboard.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


DB_PATH = Path(__file__).parent / "clawback.db"


def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Events table - logs all tool calls and decisions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            input TEXT,
            output TEXT,
            step_number INTEGER
        )
    """)

    # Claims table - tracks claim status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            vendor TEXT NOT NULL,
            incident_id TEXT,
            status TEXT NOT NULL,
            amount REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Approvals table - claims requiring human approval
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            claim_value REAL,
            confidence REAL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT
        )
    """)

    conn.commit()
    conn.close()


def log_event(claim_id: str, event_type: str, input_data: Any, output_data: Any, step_number: int = None) -> int:
    """
    Log an event to the database.

    Args:
        claim_id: The claim ID this event belongs to
        event_type: Type of event (e.g., "tool_call", "decision", "vendor_response")
        input_data: Input data (will be JSON serialized)
        output_data: Output data (will be JSON serialized)
        step_number: Optional step number in the agent loop

    Returns:
        The event ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO events (claim_id, timestamp, type, input, output, step_number)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        claim_id,
        timestamp,
        event_type,
        json.dumps(input_data, default=str),
        json.dumps(output_data, default=str),
        step_number
    ))

    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return event_id


def create_claim(claim_id: str, vendor: str, incident_id: str = None, amount: float = None) -> int:
    """
    Create a new claim record.

    Args:
        claim_id: Unique claim ID
        vendor: Vendor name
        incident_id: Optional incident ID
        amount: Optional claim amount

    Returns:
        The claim record ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    try:
        cursor.execute("""
            INSERT INTO claims (claim_id, vendor, incident_id, status, amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (claim_id, vendor, incident_id, "pending", amount, now, now))

        claim_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return claim_db_id
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        # Claim already exists, update it
        return update_claim(claim_id, status="pending", amount=amount)


def update_claim(claim_id: str, status: str = None, amount: float = None) -> int:
    """
    Update an existing claim.

    Args:
        claim_id: Claim ID to update
        status: New status
        amount: New amount

    Returns:
        The claim record ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    updates = []
    params = []

    if status:
        updates.append("status = ?")
        params.append(status)

    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)

    updates.append("updated_at = ?")
    params.append(now)
    params.append(claim_id)

    cursor.execute(f"""
        UPDATE claims
        SET {', '.join(updates)}
        WHERE claim_id = ?
    """, params)

    conn.commit()
    conn.close()

    return cursor.rowcount


def get_events(claim_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve events from the database.

    Args:
        claim_id: Optional claim ID to filter by
        limit: Maximum number of events to return

    Returns:
        List of event dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if claim_id:
        cursor.execute("""
            SELECT id, claim_id, timestamp, type, input, output, step_number
            FROM events
            WHERE claim_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (claim_id, limit))
    else:
        cursor.execute("""
            SELECT id, claim_id, timestamp, type, input, output, step_number
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "claim_id": row[1],
            "timestamp": row[2],
            "type": row[3],
            "input": json.loads(row[4]) if row[4] else None,
            "output": json.loads(row[5]) if row[5] else None,
            "step_number": row[6]
        }
        for row in rows
    ]


def get_claims(vendor: str = None, status: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve claims from the database.

    Args:
        vendor: Optional vendor to filter by
        status: Optional status to filter by

    Returns:
        List of claim dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT id, claim_id, vendor, incident_id, status, amount, created_at, updated_at FROM claims WHERE 1=1"
    params = []

    if vendor:
        query += " AND vendor = ?"
        params.append(vendor)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "claim_id": row[1],
            "vendor": row[2],
            "incident_id": row[3],
            "status": row[4],
            "amount": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
        for row in rows
    ]


def create_approval(claim_id: str, claim_value: float, confidence: float, reason: str) -> int:
    """
    Create an approval request for a claim.

    Args:
        claim_id: Claim ID requiring approval
        claim_value: Value of the claim
        confidence: Agent's confidence level (0-1)
        reason: Reason for requiring approval

    Returns:
        The approval record ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    try:
        cursor.execute("""
            INSERT INTO approvals (claim_id, claim_value, confidence, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (claim_id, claim_value, confidence, reason, "pending", now))

        approval_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return approval_id
    except sqlite3.IntegrityError:
        conn.close()
        return None  # Already exists


def get_approvals(status: str = "pending") -> List[Dict[str, Any]]:
    """
    Retrieve approval requests.

    Args:
        status: Status to filter by (default: "pending")

    Returns:
        List of approval dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, claim_id, claim_value, confidence, reason, status, created_at, reviewed_at, reviewed_by
        FROM approvals
        WHERE status = ?
        ORDER BY created_at ASC
    """, (status,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "claim_id": row[1],
            "claim_value": row[2],
            "confidence": row[3],
            "reason": row[4],
            "status": row[5],
            "created_at": row[6],
            "reviewed_at": row[7],
            "reviewed_by": row[8]
        }
        for row in rows
    ]


def update_approval(approval_id: int, status: str, reviewed_by: str = None) -> bool:
    """
    Update an approval request status.

    Args:
        approval_id: Approval record ID
        status: New status ("approved" or "rejected")
        reviewed_by: Optional reviewer name

    Returns:
        True if successful
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE approvals
        SET status = ?, reviewed_at = ?, reviewed_by = ?
        WHERE id = ?
    """, (status, now, reviewed_by, approval_id))

    conn.commit()
    conn.close()

    return cursor.rowcount > 0


if __name__ == "__main__":
    # Initialize the database
    init_db()
    print("Database initialized successfully")
