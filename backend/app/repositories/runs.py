import json, sqlite3
from datetime import datetime, timezone

def insert(conn, kind, payload, result, trip_id=None):
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO calc_runs(kind,trip_id,input_json,result_json,created_at) VALUES (?,?,?,?,?)",
        (kind, trip_id, json.dumps(payload, ensure_ascii=False), json.dumps(result, ensure_ascii=False), now),
    )
    conn.commit()
    return int(cur.lastrowid)

def list_recent(conn, limit=50):
    rows = conn.execute(
        """SELECT r.*, t.label AS trip_label
           FROM calc_runs r LEFT JOIN trips t ON t.id = r.trip_id
           ORDER BY r.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["input"] = json.loads(d.pop("input_json"))
        d["result"] = json.loads(d.pop("result_json"))
        items.append(d)
    return items
