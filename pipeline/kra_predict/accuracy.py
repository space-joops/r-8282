"""data/ 전체를 스캔해 예측 적중률(accuracy.json)을 재계산한다.

지표 정의:
- winHit: 단승 픽(topPicks.win)이 1위로 결승선 통과
- placeHit: 단승 픽이 3위 안(연승 기준)
- top3ExactHit: 예측 1~3위가 실제 1~3위와 순서까지 일치
취소 경주와 예측/결과가 없는 경주는 집계에서 제외한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from kra_predict.config import DATA_DIR, TRACKS
from kra_predict.emit import now_kst_iso, validation_errors, write_json_if_changed


def _race_files(data_dir: Path):
    meets_dir = data_dir / "meets"
    if not meets_dir.is_dir():
        return
    for date_dir in sorted(meets_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        for slug in TRACKS:
            track_dir = date_dir / slug
            if not track_dir.is_dir():
                continue
            for f in sorted(track_dir.glob("r[0-9][0-9].json")):
                yield json.loads(f.read_text("utf-8"))


def _judge(race: dict) -> dict | None:
    pred, result = race.get("prediction"), race.get("result")
    if race.get("canceled") or not pred or not result:
        return None
    order = sorted(result["order"], key=lambda o: o["finishPos"])
    if not order:
        return None
    winner_gate = order[0]["gateNo"]
    top3_actual = [o["gateNo"] for o in order[:3]]
    predicted = sorted(pred["rankings"], key=lambda r: r["predictedRank"])
    top3_predicted = [r["gateNo"] for r in predicted[:3]]
    win_pick = pred["topPicks"]["win"]
    return {
        "date": race["date"],
        "track": race["track"],
        "winHit": win_pick == winner_gate,
        "placeHit": win_pick in top3_actual,
        "top3Exact": top3_predicted == top3_actual and len(top3_actual) == 3,
    }


def _bucket(judged: list[dict]) -> dict:
    races = len(judged)
    win_hits = sum(1 for j in judged if j["winHit"])
    place_hits = sum(1 for j in judged if j["placeHit"])
    return {
        "races": races,
        "winHits": win_hits,
        "winRate": round(win_hits / races, 4) if races else 0,
        "placeHits": place_hits,
        "placeRate": round(place_hits / races, 4) if races else 0,
        "top3ExactHits": sum(1 for j in judged if j["top3Exact"]),
    }


def recompute_accuracy(*, data_dir: Path = DATA_DIR) -> dict:
    judged = [j for race in _race_files(data_dir) if (j := _judge(race))]

    by_track = {
        slug: _bucket([j for j in judged if j["track"] == slug]) for slug in TRACKS
    }
    history = []
    for date in sorted({j["date"] for j in judged}):
        day = [j for j in judged if j["date"] == date]
        history.append(
            {
                "date": date,
                "races": len(day),
                "winHits": sum(1 for j in day if j["winHit"]),
                "placeHits": sum(1 for j in day if j["placeHit"]),
            }
        )

    stats = {
        "schemaVersion": 1,
        "updatedAt": now_kst_iso(),
        "overall": _bucket(judged),
        "byTrack": by_track,
        "history": history,
    }
    errors = validation_errors("accuracy", stats)
    if errors:
        raise ValueError(f"accuracy 스키마 오류: {errors[:3]}")
    write_json_if_changed(data_dir / "stats" / "accuracy.json", stats)
    return stats
