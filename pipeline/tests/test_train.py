import json

import numpy as np
import pytest

from kra_predict import score
from kra_predict.train import (
    FEATURES,
    build_training_blocks,
    evaluate,
    fit_conditional_logit,
    make_weights_doc,
)


def _synthetic_blocks(n_races=300, seed=7):
    """첫 피처가 승자를 결정하는 합성 데이터."""
    rng = np.random.default_rng(seed)
    blocks = []
    for _ in range(n_races):
        X = rng.random((8, len(FEATURES)))
        u = 3.0 * X[:, 0] + 0.5 * X[:, 1]
        p = np.exp(u - u.max())
        p /= p.sum()
        winner = int(rng.choice(8, p=p))
        blocks.append((X, winner))
    return blocks


def test_fit_recovers_signal_direction():
    blocks = _synthetic_blocks()
    beta = fit_conditional_logit(blocks, l2=0.01)
    # 지배 피처의 계수가 가장 크고 양수여야 한다
    assert beta[0] > 0
    assert beta[0] == max(beta)
    metrics = evaluate(blocks, beta)
    # 학습된 모델이 무작위(1/8)보다 확실히 좋아야 한다
    assert metrics["winRate"] > 0.25
    assert metrics["logLoss"] < np.log(8)


def test_build_training_blocks_from_harness_shape():
    entries = []
    results = {}
    for gate in range(1, 6):
        entries.append(
            {
                "gateNo": gate,
                "rating": 40 + gate,
                "jockey": {"winRate1y": 0.1},
                "trainer": {"winRate1y": None},
                "bodyWeightDiffKg": 2,
                "record1y": {"starts": 5, "wins": gate % 3, "seconds": 1, "thirds": 0},
                "recentRuns": [],
                "scratched": False,
            }
        )
        results[gate] = {"ord": 6 - gate, "winOdds": 3.0, "plcOdds": 1.5}
    races = [
        {"track": "seoul", "date": "2026-05-03", "raceNo": 1, "entries": entries, "results": results}
    ]
    blocks = build_training_blocks(races)
    assert len(blocks) == 1
    X, winner = blocks[0]
    assert X.shape == (5, len(FEATURES))
    assert entries[winner]["gateNo"] == 5  # ord==1 은 gate 5
    assert not np.isnan(X).any()  # 결측은 대치됨


def test_score_race_uses_learned_model(monkeypatch):
    doc = make_weights_doc(
        np.array([5.0, 0, 0, 0, 0, 0, 0]),
        train_from="2025-07",
        train_to="2026-06",
        train_races=100,
        l2=0.01,
        in_sample={"races": 100, "logLoss": 2.0, "winRate": 0.3},
    )
    monkeypatch.setattr(score, "load_learned_model", lambda: doc)

    def entry(gate, wins):
        return {
            "gateNo": gate,
            "rating": None,
            "jockey": {"winRate1y": None},
            "trainer": {"winRate1y": None},
            "bodyWeightDiffKg": None,
            "record1y": {"starts": 10, "wins": wins, "seconds": 0, "thirds": 0},
            "recentRuns": [],
            "scratched": False,
        }

    rows = score.score_race([entry(1, 8), entry(2, 1)], "2026-08-16")
    by_gate = {r["gateNo"]: r for r in rows}
    # winRate1y 계수만 큰 모델 → 승률 높은 1번의 winProb가 커야 한다
    assert by_gate[1]["winProb"] > by_gate[2]["winProb"]
    assert abs(sum(r["winProb"] for r in rows) - 1.0) < 0.01

    pred = score.build_prediction(
        [entry(1, 8), entry(2, 1)],
        race_date="2026-08-16",
        generated_at="t",
    )
    assert pred["model"]["statVersion"] == "v2"


def test_weights_doc_roundtrip(tmp_path):
    doc = make_weights_doc(
        np.array([0.1] * len(FEATURES)),
        train_from="2025-07",
        train_to="2026-06",
        train_races=10,
        l2=0.01,
        in_sample={"races": 10, "logLoss": 2.0, "winRate": 0.2},
    )
    path = tmp_path / "w.json"
    path.write_text(json.dumps(doc), "utf-8")
    loaded = json.loads(path.read_text("utf-8"))
    assert loaded["features"] == FEATURES
    assert set(loaded["beta"]) == set(FEATURES)
