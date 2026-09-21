import importlib
import json

import pytest


@pytest.fixture
def svc(tmp_path, monkeypatch):
    # 指向临时库并重载持有 DB 路径/connect 绑定的模块，保证用例间隔离
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    config = importlib.import_module("app.config")
    db = importlib.import_module("app.db")
    importlib.reload(config)
    importlib.reload(db)
    seed = importlib.import_module("app.seed")
    importlib.reload(seed)
    seed.init_db()
    svc_mod = importlib.import_module("app.services.taxi_service")
    importlib.reload(svc_mod)
    s = svc_mod.TaxiService()
    # 专用行程：10km、低速 5 分、白天；不使用种子自带的那条记录
    s._c.execute(
        "INSERT INTO trips(label,distance_km,slow_min,night) VALUES ('用例行',10.0,5,0)"
    )
    s._c.commit()
    yield s
    s.close()


def count_runs(s, trip_id):
    return s._c.execute(
        "SELECT COUNT(*) c FROM calc_runs WHERE trip_id=?", (trip_id,)
    ).fetchone()["c"]


def load_runs(s, trip_id):
    rows = s._c.execute(
        "SELECT input_json, result_json FROM calc_runs WHERE trip_id=? ORDER BY id",
        (trip_id,),
    ).fetchall()
    return [
        (json.loads(r["input_json"]), json.loads(r["result_json"])) for r in rows
    ]


def test_persist_uses_trip_km_ignoring_larger_body_km(svc):
    # 请求体塞更大的公里数：回包与落表均须按行程当时 10km 计算
    tid = svc._c.execute("SELECT id FROM trips WHERE label='用例行'").fetchone()["id"]
    r = svc.fare(999, 0, True, tid, True)
    assert r["run_id"] is not None
    assert r["distance_km"] == 10.0
    assert r["slow_min"] == 5
    assert r["night"] is False
    # 10km: 11 + (10-3)*2.5 + 5*0.8 = 32.5
    assert r["total"] == 32.5

    inp, res = load_runs(svc, tid)[0]
    assert inp == {"distance_km": 10.0, "slow_min": 5, "night": False}
    assert res["distance_km"] == 10.0
    assert res["total"] == 32.5
    row = svc._c.execute("SELECT trip_id FROM calc_runs WHERE id=?", (r["run_id"],)).fetchone()
    assert row["trip_id"] == tid


def test_repeat_persist_same_trip_keeps_snapshot(svc):
    tid = svc._c.execute("SELECT id FROM trips WHERE label='用例行'").fetchone()["id"]
    svc.fare(999, 0, True, tid, True)
    svc.fare(12345, 0, True, tid, True)
    runs_ = load_runs(svc, tid)
    assert len(runs_) == 2
    for inp, res in runs_:
        assert inp["distance_km"] == 10.0
        assert res["distance_km"] == 10.0
        assert res["total"] == 32.5


def test_old_runs_frozen_after_trip_distance_change(svc):
    tid = svc._c.execute("SELECT id FROM trips WHERE label='用例行'").fetchone()["id"]
    old = svc.fare(999, 0, True, tid, True)
    assert old["total"] == 32.5

    svc.update_trip_distance(tid, 20.0)

    # 旧记录的输入与拆解仍是写入当时那一版
    inp, res = load_runs(svc, tid)[0]
    assert inp["distance_km"] == 10.0
    assert res["distance_km"] == 10.0
    assert res["total"] == 32.5

    # 重新打开旧记录（按 id 直读）结果同样不变
    row = svc._c.execute(
        "SELECT input_json, result_json FROM calc_runs WHERE id=?", (old["run_id"],)
    ).fetchone()
    assert json.loads(row["input_json"])["distance_km"] == 10.0
    assert json.loads(row["result_json"])["total"] == 32.5

    # 改公里后再落表：新记录按行程新版 20km 计算
    new = svc.fare(999, 0, True, tid, True)
    # 20km: 11 + (20-3)*2.5 + 5*0.8 = 57.5
    assert new["distance_km"] == 20.0
    assert new["total"] == 57.5
    runs_ = load_runs(svc, tid)
    assert [i["distance_km"] for i, _ in runs_] == [10.0, 20.0]


def test_readonly_does_not_insert(svc):
    tid = svc._c.execute("SELECT id FROM trips WHERE label='用例行'").fetchone()["id"]
    before = count_runs(svc, tid)
    r1 = svc.fare(999, 0, True, tid, False)
    r2 = svc.fare(999, 0, True, tid, False)
    after = count_runs(svc, tid)
    assert r1["run_id"] is None and r2["run_id"] is None
    assert after == before
    # 只读回包仍按行程当时公里
    assert r1["distance_km"] == 10.0
    assert r1["total"] == 32.5
