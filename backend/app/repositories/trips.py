import sqlite3

def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM trips ORDER BY id").fetchall()]

def get(conn: sqlite3.Connection, trip_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
    return dict(row) if row else None

def update_distance(conn: sqlite3.Connection, trip_id: int, distance_km: float) -> None:
    conn.execute("UPDATE trips SET distance_km=? WHERE id=?", (distance_km, trip_id))
    conn.commit()
