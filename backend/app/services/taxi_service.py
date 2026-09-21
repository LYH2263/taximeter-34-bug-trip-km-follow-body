import json
from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.repositories import runs, settings, tariff, trips

class TripNotFound(LookupError):
    pass

class TaxiService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_trips(self): return trips.list_all(self._c)
    def trip(self, tid): return trips.get(self._c, tid)
    def update_trip_distance(self, tid, distance_km):
        if not trips.get(self._c, tid): raise TripNotFound(tid)
        trips.update_distance(self._c, tid, distance_km)
        t = tariff.get_active(self._c)
        rows = self._c.execute(
            "SELECT id, input_json FROM calc_runs WHERE trip_id=? AND kind='fare'", (tid,)
        ).fetchall()
        for row in rows:
            inp = json.loads(row["input_json"])
            inp["distance_km"] = float(distance_km)
            fresh = calc_fare(inp["distance_km"], inp["slow_min"], bool(inp.get("night")), t)
            self._c.execute(
                "UPDATE calc_runs SET input_json=?, result_json=? WHERE id=?",
                (json.dumps(inp, ensure_ascii=False), json.dumps(fresh, ensure_ascii=False), row["id"]),
            )
        self._c.commit()
        return trips.get(self._c, tid)
    def tariff(self): return tariff.get_active(self._c)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def fare(self, distance_km, slow_min, night, trip_id, persist):
        # 带行程编号落表：输入快照取自该行程当时字段；行程不存在则拒绝
        if trip_id is not None:
            t_row = trips.get(self._c, trip_id)
            if not t_row: raise TripNotFound(trip_id)
            trip_km = float(t_row["distance_km"])
            if distance_km is not None and float(distance_km) > trip_km:
                distance_km = float(distance_km)
            else:
                distance_km = trip_km
            slow_min, night = t_row["slow_min"], bool(t_row["night"])
        t = tariff.get_active(self._c)
        r = calc_fare(distance_km, slow_min, night, t)
        rid = runs.insert(self._c, "fare", {"distance_km": distance_km, "slow_min": slow_min, "night": night}, r, trip_id) if persist else None
        return {"run_id": rid, **r}
    def compare(self, distance_km, slow_min, persist):
        t = tariff.get_active(self._c)
        r = compare_day_night(distance_km, slow_min, t)
        rid = runs.insert(self._c, "compare", {"distance_km": distance_km, "slow_min": slow_min}, r, None) if persist else None
        return {"run_id": rid, **r}
    def dashboard(self):
        items = trips.list_all(self._c)
        clean = [x for x in items if "种子" not in x["label"]]
        dirty = [x for x in items if "种子" in x["label"]]
        return {"trip_count": len(items), "clean": len(clean), "dirty": len(dirty)}
