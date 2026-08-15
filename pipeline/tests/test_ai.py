import json

import pytest

from kra_predict.ai import MAX_DELTA, _parse_analysis, enrich_predictions
from kra_predict.api.client import KraClient
from kra_predict.emit import now_kst_iso
from kra_predict.features import assemble_races
from kra_predict.fetch import fetch_meet_bundle
from kra_predict.score import build_prediction

DATE = "2026-08-15"


def _races():
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
    return races


def _analysis_json(gate, delta):
    return json.dumps(
        {
            "commentary": "테스트 총평입니다.",
            "confidence": "high",
            "perHorse": [{"gateNo": gate, "briefComment": "AI 한줄평"}],
            "adjustments": [{"gateNo": gate, "delta": delta, "reason": "테스트"}],
        },
        ensure_ascii=False,
    )


def test_parse_analysis_strips_code_fence():
    text = "```json\n" + _analysis_json(1, 0.05) + "\n```"
    data = _parse_analysis(text)
    assert data["commentary"] == "테스트 총평입니다."


def test_parse_analysis_rejects_garbage():
    with pytest.raises(Exception):
        _parse_analysis("JSON 아님")


def test_enrich_applies_clamped_delta_and_reranks():
    races = _races()
    race = next(r for r in races if r["track"] == "seoul" and r["raceNo"] == 5)
    before = {r["gateNo"]: r["score"] for r in race["prediction"]["rankings"]}
    last_gate = race["prediction"]["rankings"][-1]["gateNo"]

    # 과도한 보정(+0.5)은 MAX_DELTA로 클램핑되어야 한다
    ok, fallback = enrich_predictions(
        races, runner=lambda prompt, model: _analysis_json(last_gate, 0.5)
    )
    assert ok >= 1 and fallback == 0

    pred = race["prediction"]
    after = {r["gateNo"]: r["score"] for r in pred["rankings"]}
    assert after[last_gate] == pytest.approx(before[last_gate] + MAX_DELTA, abs=1e-4)
    assert pred["aiCommentary"] == "테스트 총평입니다."
    assert pred["model"]["aiModel"] == "claude-cli"
    assert abs(sum(r["winProb"] for r in pred["rankings"]) - 1.0) < 0.01
    assert [r["predictedRank"] for r in pred["rankings"]] == list(
        range(1, len(pred["rankings"]) + 1)
    )
    assert pred["topPicks"]["win"] == pred["rankings"][0]["gateNo"]


def test_enrich_falls_back_on_failure():
    races = _races()

    def failing_runner(prompt, model):
        raise RuntimeError("claude 없음")

    ok, fallback = enrich_predictions(races, runner=failing_runner, retries=1)
    assert ok == 0 and fallback >= 1
    for race in races:
        if race["prediction"]:
            assert race["prediction"]["aiCommentary"] is None
            assert race["prediction"]["model"]["aiModel"] is None
