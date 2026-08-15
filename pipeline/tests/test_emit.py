import json

from kra_predict.api.client import KraClient
from kra_predict.emit import (
    emit_races,
    now_kst_iso,
    race_path,
    rebuild_meet_and_index,
    validate_tree,
)
from kra_predict.features import assemble_races
from kra_predict.fetch import fetch_meet_bundle
from kra_predict.score import build_prediction

DATE = "2026-08-15"


def _build_races():
    client = KraClient(offline=True)
    try:
        bundle = fetch_meet_bundle(client, DATE)
    finally:
        client.close()
    races = assemble_races(bundle)
    generated_at = now_kst_iso()
    for race in races:
        if race["entries"]:
            race["prediction"] = build_prediction(
                race["entries"], race_date=race["date"], generated_at=generated_at
            )
    return races


def test_emit_and_rebuild_and_validate(tmp_path):
    races = _build_races()
    assert len(races) == 3  # 서울 2 + 제주 1

    written, skipped, changed = emit_races(races, data_dir=tmp_path)
    assert len(written) == 3 and skipped == []
    assert changed == 3

    # accuracy.json은 검증 대상이므로 최소 골격을 둔다
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    zero = {
        "races": 0, "winHits": 0, "winRate": 0,
        "placeHits": 0, "placeRate": 0, "top3ExactHits": 0,
    }
    (stats_dir / "accuracy.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "updatedAt": now_kst_iso(),
                "overall": zero,
                "byTrack": {"seoul": zero, "busan": zero, "jeju": zero},
                "history": [],
            },
            ensure_ascii=False,
        ),
        "utf-8",
    )

    rebuild_meet_and_index(data_dir=tmp_path)
    assert validate_tree(data_dir=tmp_path) == []

    index = json.loads((tmp_path / "index.json").read_text("utf-8"))
    assert index["meetDates"] == [DATE]

    meet = json.loads((tmp_path / "meets" / DATE / "meet.json").read_text("utf-8"))
    tracks = {t["track"]: t for t in meet["tracks"]}
    assert set(tracks) == {"seoul", "jeju"}
    assert all(r["hasPrediction"] for r in tracks["seoul"]["races"])


def test_result_protected_without_force(tmp_path):
    races = _build_races()
    emit_races(races, data_dir=tmp_path)

    # 서울 1경주에 결과를 심는다
    path = race_path(tmp_path, DATE, "seoul", 1)
    race = json.loads(path.read_text("utf-8"))
    race["result"] = {
        "fetchedAt": now_kst_iso(),
        "order": [
            {"finishPos": 1, "gateNo": 2, "horseName": "황금돌풍", "timeSec": 73.7, "margin": None}
        ],
        "payouts": None,
    }
    original_prediction = race["prediction"]
    path.write_text(json.dumps(race, ensure_ascii=False), "utf-8")

    # force 없이 재-emit → 건너뛰고 파일 불변
    modified = [dict(r) for r in races if r["track"] == "seoul" and r["raceNo"] == 1]
    modified[0]["prediction"] = None
    written, skipped, changed = emit_races(modified, data_dir=tmp_path)
    assert written == [] and skipped == ["seoul 1경주"] and changed == 0
    after = json.loads(path.read_text("utf-8"))
    assert after["prediction"] == original_prediction
    assert after["result"] is not None

    # force면 덮어쓰되 새 조립본에 결과가 없으면 기존 결과 보존
    written, skipped, changed = emit_races(modified, data_dir=tmp_path, force=True)
    assert written == ["seoul 1경주"] and changed == 1
    after = json.loads(path.read_text("utf-8"))
    assert after["prediction"] is None
    assert after["result"] is not None  # 기존 결과 보존
