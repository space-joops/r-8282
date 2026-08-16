"""통계 스코어링 — v1(수작업 가중) + v2(학습 가중, 조건부 로짓).

공통: 엔트리별 피처를 경주 내 min-max 정규화 후 선형 결합 → softmax로 winProb.
- v1: 결측 피처는 가중치 재정규화로 제외, 고정 온도 softmax
- v2: weights_v2.json(조건부 로짓 MLE 학습 계수)이 존재하면 자동 활성.
  결측은 0.5(중립) 대치, 계수에 온도가 흡수됨. 파일이 없으면 v1 폴백
"""

from __future__ import annotations

import json
import math
from datetime import date as date_cls
from functools import lru_cache
from pathlib import Path

STAT_VERSION = "v1"

WEIGHTS = {
    "winRate1y": 0.30,
    "placeRate1y": 0.20,
    "rating": 0.25,
    "jockeyWinRate": 0.10,
    "trainerWinRate": 0.05,
    "bodyWeightStability": 0.05,
    "rest": 0.05,
}

SOFTMAX_TEMP = 0.28

MODEL_PATH = Path(__file__).parent / "weights_v2.json"

# "v1"이면 학습 가중치를 무시하고 v1로 동작 (백테스트의 버전별 재생성용)
_MODEL_OVERRIDE: str | None = None


def set_model_override(version: str | None) -> None:
    """None=자동(파일 있으면 v2) · "v1"=강제 v1."""
    global _MODEL_OVERRIDE
    _MODEL_OVERRIDE = version
    load_learned_model.cache_clear()


@lru_cache(maxsize=1)
def load_learned_model() -> dict | None:
    """학습된 v2 가중치. 없으면(또는 v1 강제 시) None → v1 동작."""
    if _MODEL_OVERRIDE == "v1":
        return None
    if not MODEL_PATH.exists():
        return None
    return json.loads(MODEL_PATH.read_text("utf-8"))


def model_version() -> str:
    model = load_learned_model()
    return model["version"] if model else STAT_VERSION


def _rest_score(rest_days: int | None) -> float | None:
    """휴양일 피처: 2~6주가 최적, 과소/과다 휴양은 감점."""
    if rest_days is None:
        return None
    if rest_days < 10:
        return 0.4
    if rest_days <= 42:
        return 1.0
    if rest_days <= 90:
        return 0.6
    return 0.3


def _body_weight_stability(diff: float | None) -> float | None:
    """마체중 급변(±8kg 초과)은 컨디션 리스크로 감점."""
    if diff is None:
        return None
    return 1.0 if abs(diff) <= 8 else 0.5


def extract_features(entry: dict, race_date: str | None = None) -> dict[str, float | None]:
    rec = entry.get("record1y")
    win_rate = place_rate = None
    if rec and rec["starts"] > 0:
        win_rate = rec["wins"] / rec["starts"]
        place_rate = (rec["wins"] + rec["seconds"] + rec["thirds"]) / rec["starts"]

    rest_days = None
    runs = entry.get("recentRuns") or []
    if runs and race_date:
        try:
            last = date_cls.fromisoformat(runs[0]["date"])
            rest_days = (date_cls.fromisoformat(race_date) - last).days
        except ValueError:
            rest_days = None

    return {
        "winRate1y": win_rate,
        "placeRate1y": place_rate,
        "rating": entry.get("rating"),
        "jockeyWinRate": entry["jockey"].get("winRate1y"),
        "trainerWinRate": entry["trainer"].get("winRate1y"),
        "bodyWeightStability": _body_weight_stability(entry.get("bodyWeightDiffKg")),
        "rest": _rest_score(rest_days),
    }


def _minmax_normalize(values: list[float | None]) -> list[float | None]:
    present = [v for v in values if v is not None]
    if not present:
        return values
    lo, hi = min(present), max(present)
    if hi == lo:
        return [0.5 if v is not None else None for v in values]
    return [(v - lo) / (hi - lo) if v is not None else None for v in values]


def score_race(entries: list[dict], race_date: str | None = None) -> list[dict]:
    """entries → [{gateNo, score, winProb, briefComment}] (점수 내림차순 아님, 입력 순서)."""
    active = [e for e in entries if not e.get("scratched")]
    if not active:
        return []

    features = [extract_features(e, race_date) for e in active]
    # 경주 내 정규화 (피처별)
    normalized: list[dict[str, float | None]] = [dict(f) for f in features]
    for key in WEIGHTS:
        column = _minmax_normalize([f[key] for f in features])
        for row, value in zip(normalized, column):
            row[key] = value

    model = load_learned_model()
    if model:
        # v2: 학습된 조건부 로짓 — 결측은 중립값 대치, 계수에 온도 흡수됨
        impute = model.get("impute", 0.5)
        beta = model["beta"]
        utilities = [
            sum(
                beta[k] * (row[k] if row[k] is not None else impute)
                for k in model["features"]
            )
            for row in normalized
        ]
        peak = max(utilities)
        exps = [math.exp(u - peak) for u in utilities]
        scores = _minmax_display(utilities)
    else:
        # v1: 결측 피처는 가중치 재정규화로 제외
        scores = []
        for row in normalized:
            total_weight = sum(w for k, w in WEIGHTS.items() if row[k] is not None)
            if total_weight == 0:
                scores.append(0.5)
                continue
            scores.append(
                sum(w * row[k] for k, w in WEIGHTS.items() if row[k] is not None)
                / total_weight
            )
        exps = [math.exp(s / SOFTMAX_TEMP) for s in scores]
    denom = sum(exps)

    results = []
    for entry, feats, score, exp in zip(active, features, scores, exps):
        results.append(
            {
                "gateNo": entry["gateNo"],
                "score": round(score, 4),
                "winProb": round(exp / denom, 4),
                "briefComment": _brief_comment(feats),
            }
        )
    return results


def _minmax_display(values: list[float]) -> list[float]:
    """표시용 score(0..1) — 유틸리티를 경주 내 min-max로 눌러 담는다."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _brief_comment(feats: dict[str, float | None]) -> str | None:
    parts = []
    if feats["winRate1y"] is not None:
        parts.append(f"1년 승률 {feats['winRate1y'] * 100:.0f}%")
    if feats["placeRate1y"] is not None:
        parts.append(f"입상률 {feats['placeRate1y'] * 100:.0f}%")
    if feats["rating"] is not None:
        parts.append(f"레이팅 {feats['rating']:.0f}")
    return " · ".join(parts) or None


def build_prediction(
    entries: list[dict],
    *,
    race_date: str | None,
    generated_at: str,
    ai_model: str | None = None,
    ai_commentary: str | None = None,
) -> dict | None:
    """rankings·topPicks·confidence를 채운 Prediction dict."""
    scored = score_race(entries, race_date)
    if not scored:
        return None
    ranked = sorted(scored, key=lambda r: r["winProb"], reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["predictedRank"] = rank

    gap = ranked[0]["winProb"] - ranked[1]["winProb"] if len(ranked) > 1 else 1.0
    confidence = "high" if gap > 0.10 else "low" if gap < 0.03 else "medium"

    return {
        "generatedAt": generated_at,
        "model": {"statVersion": model_version(), "aiModel": ai_model},
        "rankings": ranked,
        "aiCommentary": ai_commentary,
        "confidence": confidence,
        "topPicks": {
            "win": ranked[0]["gateNo"],
            "place": [r["gateNo"] for r in ranked[:3]],
            "exacta": [ranked[0]["gateNo"], ranked[1]["gateNo"]]
            if len(ranked) > 1
            else None,
        },
    }
