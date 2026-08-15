from kra_predict.score import build_prediction, score_race


def _entry(gate, *, wins=0, starts=0, seconds=0, thirds=0, rating=None, scratched=False):
    return {
        "gateNo": gate,
        "horseName": f"말{gate}",
        "rating": rating,
        "jockey": {"id": "", "name": "미정", "winRate1y": None},
        "trainer": {"id": "", "name": "미정", "winRate1y": None},
        "bodyWeightDiffKg": None,
        "record1y": {"starts": starts, "wins": wins, "seconds": seconds, "thirds": thirds}
        if starts
        else None,
        "recentRuns": [],
        "scratched": scratched,
    }


def test_score_deterministic_and_prob_sums_to_one():
    entries = [
        _entry(1, wins=3, starts=10, rating=50),
        _entry(2, wins=1, starts=10, rating=40),
        _entry(3, wins=0, starts=8, rating=30),
    ]
    first = score_race(entries, "2026-08-15")
    second = score_race(entries, "2026-08-15")
    assert first == second
    assert abs(sum(r["winProb"] for r in first) - 1.0) < 0.01
    by_gate = {r["gateNo"]: r for r in first}
    assert by_gate[1]["winProb"] > by_gate[2]["winProb"] > by_gate[3]["winProb"]


def test_score_handles_missing_features():
    entries = [_entry(1), _entry(2)]  # 피처 전무 → 균등 배분
    rows = score_race(entries, None)
    assert rows[0]["winProb"] == rows[1]["winProb"]


def test_scratched_excluded():
    entries = [_entry(1, wins=2, starts=5), _entry(2, scratched=True)]
    rows = score_race(entries, None)
    assert [r["gateNo"] for r in rows] == [1]


def test_build_prediction_shape():
    entries = [
        _entry(1, wins=5, starts=10, rating=60),
        _entry(2, wins=1, starts=10, rating=45),
        _entry(3, wins=0, starts=6, rating=30),
    ]
    pred = build_prediction(
        entries, race_date="2026-08-15", generated_at="2026-08-14T21:00:00+09:00"
    )
    assert pred is not None
    assert pred["model"] == {"statVersion": "v1", "aiModel": None}
    assert [r["predictedRank"] for r in pred["rankings"]] == [1, 2, 3]
    assert pred["topPicks"]["win"] == pred["rankings"][0]["gateNo"]
    assert pred["topPicks"]["place"] == [r["gateNo"] for r in pred["rankings"][:3]]
    assert pred["confidence"] in {"high", "medium", "low"}


def test_build_prediction_empty():
    assert build_prediction([], race_date=None, generated_at="x") is None
