import json

from kra_predict.accuracy import recompute_accuracy
from kra_predict.api.client import KraClient
from kra_predict.emit import emit_races, now_kst_iso, race_path, rebuild_meet_and_index
from kra_predict.features import assemble_races
from kra_predict.fetch import fetch_meet_bundle
from kra_predict.results import (
    apply_results,
    parse_body_weight,
    parse_race_time,
)
from kra_predict.score import build_prediction

DATE = "2026-08-15"


def test_parse_race_time():
    assert parse_race_time("73.7") == 73.7
    assert parse_race_time("1:13.7") == 73.7
    assert parse_race_time("") is None
    assert parse_race_time(None) is None


def test_parse_body_weight():
    assert parse_body_weight("478(+4)") == (478.0, 4.0)
    assert parse_body_weight("492(-2)") == (492.0, -2.0)
    assert parse_body_weight("478") == (478.0, None)
    assert parse_body_weight("") == (None, None)


def _seed_data(tmp_path):
    client = KraClient(offline=True)
    try:
        bundle = fetch_meet_bundle(client, DATE)
    finally:
        client.close()
    races = assemble_races(bundle)
    for race in races:
        if race["entries"]:
            race["prediction"] = build_prediction(
                race["entries"], race_date=race["date"], generated_at=now_kst_iso()
            )
    emit_races(races, data_dir=tmp_path)
    return races


def _result_row(rc_no, chul_no, name, ord_, **extra):
    row = {
        "rcNo": rc_no,
        "chulNo": chul_no,
        "hrName": name,
        "ord": ord_,
        "rcTime": "87.1",
        "diffUnit": "",
        "noraceFlag": "0",
        "winOdds": "3.4" if ord_ == 1 else "",
        "plcOdds": "1.5",
        "wgHr": "480(+2)",
        "wgBudam": "56",
        "jkName": "기수", "jkNo": "1", "trName": "조교사", "trNo": "2",
        "jkRcCntY": 100, "jkOrd1CntY": 12, "trRcCntY": 200, "trOrd1CntY": 20,
        "age": 4, "sex": "수", "rating": "50", "hrNo": "0000001",
        "rcDist": 1400, "rank": "국4", "schStTime": "13:05",
    }
    row.update(extra)
    return row


def test_apply_results_sets_result_and_keeps_prediction(tmp_path):
    races = _seed_data(tmp_path)
    r05 = next(r for r in races if r["track"] == "seoul" and r["raceNo"] == 5)
    original_prediction = json.loads(json.dumps(r05["prediction"]))
    gates = [e["gateNo"] for e in r05["entries"]]

    bundle = {
        "date": DATE,
        "results": {
            "seoul": [
                _result_row(5, gate, f"말{gate}", pos)
                for pos, gate in enumerate(gates, start=1)
            ]
        },
    }
    applied, canceled = apply_results(bundle, data_dir=tmp_path)
    assert applied == 1 and canceled == 0

    saved = json.loads(race_path(tmp_path, DATE, "seoul", 5).read_text("utf-8"))
    assert saved["prediction"] == original_prediction  # prediction 불변
    assert saved["result"]["order"][0]["finishPos"] == 1
    assert saved["result"]["payouts"]["win"] == 3.4


def test_apply_results_cancel_flag(tmp_path):
    _seed_data(tmp_path)
    bundle = {
        "date": DATE,
        "results": {
            "seoul": [_result_row(5, 1, "말1", 1, noraceFlag="1")]
        },
    }
    applied, canceled = apply_results(bundle, data_dir=tmp_path)
    assert applied == 0 and canceled == 1
    saved = json.loads(race_path(tmp_path, DATE, "seoul", 5).read_text("utf-8"))
    assert saved["canceled"] is True
    assert saved["result"] is None


def test_apply_results_backfills_unknown_race(tmp_path):
    _seed_data(tmp_path)
    # 사전 데이터가 전혀 없던 부경 3경주
    bundle = {
        "date": DATE,
        "results": {
            "busan": [
                _result_row(3, 1, "부경말1", 1),
                _result_row(3, 2, "부경말2", 2),
            ]
        },
    }
    applied, _ = apply_results(bundle, data_dir=tmp_path)
    assert applied == 1
    saved = json.loads(race_path(tmp_path, DATE, "busan", 3).read_text("utf-8"))
    assert len(saved["entries"]) == 2
    assert saved["entries"][0]["bodyWeightKg"] == 480.0
    assert saved["entries"][0]["jockey"]["winRate1y"] == 0.12
    assert saved["prediction"] is None


def test_recompute_accuracy(tmp_path):
    races = _seed_data(tmp_path)
    r05 = next(r for r in races if r["track"] == "seoul" and r["raceNo"] == 5)
    win_pick = r05["prediction"]["topPicks"]["win"]
    gates = [e["gateNo"] for e in r05["entries"]]
    # 단승 픽이 실제 1위가 되도록 결과 구성 → winHit
    ordered = [win_pick] + [g for g in gates if g != win_pick]
    bundle = {
        "date": DATE,
        "results": {
            "seoul": [
                _result_row(5, gate, f"말{gate}", pos)
                for pos, gate in enumerate(ordered, start=1)
            ]
        },
    }
    apply_results(bundle, data_dir=tmp_path)
    rebuild_meet_and_index(data_dir=tmp_path)
    stats = recompute_accuracy(data_dir=tmp_path)

    assert stats["overall"]["races"] == 1
    assert stats["overall"]["winHits"] == 1
    assert stats["byTrack"]["seoul"]["winRate"] == 1.0
    assert stats["history"] == [
        {"date": DATE, "races": 1, "winHits": 1, "placeHits": 1}
    ]
