import json

import pytest

import app.db as dbmod
from app import seed
from app.services.taxi_service import TaxiService

# 种子行程 1：白天短途，5.0km / 低速2分
# calc_fare(5, 2, False) → 11 + (5-3)*2.5 + 2*0.8 = 17.6
TRIP_1_TOTAL = 17.6


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "DB_PATH", tmp_path / "test.db")
    seed.init_db()
    with TaxiService() as s:
        yield s


def _run_count(s) -> int:
    return s._c.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]


def _get_run(s, run_id) -> dict:
    row = s._c.execute("SELECT * FROM calc_runs WHERE id=?", (run_id,)).fetchone()
    d = dict(row)
    d["input"] = json.loads(d.pop("input_json"))
    d["result"] = json.loads(d.pop("result_json"))
    return d


def test_persist_with_trip_uses_trip_km_and_tags_run(svc):
    # 请求体塞了更大的公里，落表仍须按行程当时 5.0km 计算
    out = svc.fare(distance_km=999.0, slow_min=99, night=True, trip_id=1, persist=True)
    assert out["run_id"] is not None
    assert out["distance_km"] == 5.0
    assert out["slow_min"] == 2
    assert out["night"] is False
    assert out["total"] == TRIP_1_TOTAL

    run = _get_run(svc, out["run_id"])
    assert run["trip_id"] == 1
    assert run["input"]["distance_km"] == 5.0
    assert run["result"]["total"] == TRIP_1_TOTAL


def test_repeat_persist_with_same_trip_and_larger_km_still_snapshots_trip(svc):
    first = svc.fare(distance_km=5.0, slow_min=2, night=False, trip_id=1, persist=True)
    second = svc.fare(distance_km=999.0, slow_min=99, night=True, trip_id=1, persist=True)
    for rid in (first["run_id"], second["run_id"]):
        run = _get_run(svc, rid)
        assert run["input"]["distance_km"] == 5.0
        assert run["result"]["total"] == TRIP_1_TOTAL
        assert run["trip_id"] == 1


def test_readonly_fare_does_not_insert(svc):
    before = _run_count(svc)
    out1 = svc.fare(distance_km=5.0, slow_min=2, night=False, trip_id=1, persist=False)
    out2 = svc.fare(distance_km=9.0, slow_min=4, night=True, trip_id=1, persist=False)
    after = _run_count(svc)
    assert out1["run_id"] is None
    assert out2["run_id"] is None
    # 连续两次只读之间记录条数不得增加（含种子那条共 before 条）
    assert after == before


def test_changing_trip_km_keeps_old_runs_frozen(svc):
    saved = svc.fare(distance_km=5.0, slow_min=2, night=False, trip_id=1, persist=True)
    old = _get_run(svc, saved["run_id"])

    svc.update_trip_distance(1, 20.0)

    # 行程本身已改
    assert svc.trip(1)["distance_km"] == 20.0
    # 旧记录的公里、拆解仍是写入当时那一版
    again = _get_run(svc, saved["run_id"])
    assert again["input"] == old["input"]
    assert again["result"] == old["result"]
    assert again["input"]["distance_km"] == 5.0
    assert again["result"]["total"] == TRIP_1_TOTAL


def test_persist_after_km_change_snapshots_new_trip_km(svc):
    svc.update_trip_distance(1, 20.0)
    out = svc.fare(distance_km=5.0, slow_min=2, night=False, trip_id=1, persist=True)
    # 11 + (20-3)*2.5 + 2*0.8 = 55.1
    assert out["distance_km"] == 20.0
    assert out["total"] == 55.1
